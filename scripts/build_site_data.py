"""Build the data block embedded in landing_page/index.html.

The website is a static page, so its charts read a `const DATA = {...};`
object embedded in the HTML. This script rebuilds that object from
data/processed/historical_gold_futures.csv with the same engines the Python
backend uses, and writes it back into the page.

Usage:
    python scripts/build_site_data.py            # rebuild and write the page
    python scripts/build_site_data.py --check    # only print the JSON summary
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.carry_engine import calculate_retail_micro_premium, calculate_term_structure  # noqa: E402
from src.data_doctor import audit_dataset_health  # noqa: E402
from src import parity_engine  # noqa: E402
from src.liquidity_engine import calculate_liquidity_depth  # noqa: E402
from src.spread_engine import calculate_calendar_spreads  # noqa: E402
from src.spread_intelligence import calculate_spread_intelligence  # noqa: E402
from src.agent_verification import verify_against_dataset  # noqa: E402
from src.validation_engine import attribute_pnl_vs_underlying, run_walk_forward_validation  # noqa: E402

DATA_PATH = ROOT / "data" / "processed" / "historical_gold_futures.csv"
PAGE_PATH = ROOT / "landing_page" / "index.html"
SYMBOLS = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]
DMY = "%d %b %Y"


def r2(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 2)


def load() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df = df[df["symbol"].isin(SYMBOLS)].copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="mixed")
    df["expiry_date"] = pd.to_datetime(df["expiry_date"], format="mixed")
    return df.sort_values(["trade_date", "symbol", "expiry_date"]).reset_index(drop=True)


def build(df: pd.DataFrame) -> dict:
    latest = df["trade_date"].max()
    today = df[df["trade_date"] == latest].sort_values(["symbol", "expiry_date"])

    audit_in = df.assign(
        trade_date=df["trade_date"].dt.strftime("%Y-%m-%d"),
        expiry_date=df["expiry_date"].dt.strftime("%Y-%m-%d"),
    )
    audit = audit_dataset_health(audit_in)
    audit_out = {
        "health_score": audit["health_score"],
        "status": audit["status"],
        "total_rows": audit["total_rows"],
        "unique_symbols": audit["unique_symbols"],
        "trading_days": audit["trading_days"],
        "diagnostics": audit["diagnostics"],
    }

    latest_records = [
        {
            "symbol": r.symbol,
            "expiry_date": r.expiry_date.strftime(DMY),
            "close": float(r.close),
            "norm_price": r2(r.normalized_price_per_gram),
            "volume_lots": int(r.volume_lots),
            "oi_lots": int(r.open_interest_lots),
        }
        for r in today.itertuples()
    ]

    hist_series = {}
    for sym in SYMBOLS:
        s = df[df["symbol"] == sym].groupby("trade_date")["normalized_price_per_gram"].mean()
        hist_series[sym] = {
            "dates": [d.strftime("%Y-%m-%d") for d in s.index],
            "prices": [r2(v) for v in s.values],
        }

    # Spread intelligence per symbol (all expiry pairs, expanding-window z-scores)
    intel = {}
    for sym in SYMBOLS:
        spreads = calculate_calendar_spreads(df, symbol=sym)
        intel[sym] = calculate_spread_intelligence(spreads)

    quiet_alerts_raw = []
    for sym in SYMBOLS:
        it = intel[sym]
        li = it[it["trade_date"] == latest].sort_values(["near_expiry", "far_expiry"])
        for r in li.itertuples():
            near = today[(today["symbol"] == sym) & (today["expiry_date"] == r.near_expiry)]
            if pd.isna(r.spread_zscore):
                continue
            quiet_alerts_raw.append({
                "trade_date": latest.strftime(DMY),
                "symbol": sym,
                "near_expiry": r.near_expiry.strftime(DMY),
                "far_expiry": r.far_expiry.strftime(DMY),
                "dte": int((r.near_expiry - latest).days),
                "zscore": r2(r.spread_zscore),
                "spread": r2(r.calendar_spread),
                "mean_spread": r2(r.historical_mean),
                "gross_edge": r2(abs(r.calendar_spread - r.historical_mean)),
                "volume_lots": int(near["volume_lots"].iloc[0]) if not near.empty else 0,
                "oi_lots": int(near["open_interest_lots"].iloc[0]) if not near.empty else 0,
            })

    curves = {}
    for sym in SYMBOLS:
        ts = calculate_term_structure(df, trade_date=latest, symbol=sym)
        curves[sym] = [
            {
                "expiry": r["expiry_date"].strftime(DMY),
                "dte": int(r["days_to_expiry"]),
                "close": float(r["close"]),
                "norm_price": r2(r["normalized_price_per_gram"]),
                "spread_vs_front": r2(r["spread_vs_front_inr"]),
                "carry_pct": r2(r["annualized_carry_pct"]),
                "regime": r["market_regime"],
            }
            for _, r in ts.iterrows()
        ]

    mp = calculate_retail_micro_premium(df)
    micro_premium = {}
    for sym in ["GOLDPETAL", "GOLDGUINEA", "GOLDTEN"]:
        m = mp[mp["symbol"] == sym].sort_values("trade_date")
        micro_premium[sym] = {
            "dates": [d.strftime("%Y-%m-%d") for d in m["trade_date"]],
            "premium_inr": [r2(v) for v in m["premium_inr_per_g"]],
        }

    liq = calculate_liquidity_depth(today)
    liquidity = [
        {
            "symbol": r["symbol"],
            "expiry": r["expiry_date"].strftime(DMY),
            "dte": int(r["days_to_expiry"]),
            "volume": int(r["volume_lots"]),
            "oi": int(r["open_interest_lots"]),
            "turnover_cr": r2(r["turnover_crores"]),
            "is_tender": bool(r["is_in_tender"]),
            "tier": r["liquidity_tier"],
        }
        for _, r in liq.sort_values(["symbol", "expiry_date"]).iterrows()
    ]

    backtest_data = {}
    for sym in ["GOLDGUINEA", "GOLDM", "GOLDTEN", "GOLDPETAL"]:
        it = intel[sym]
        out = {}
        for (ne, fe), g in it.groupby(["near_expiry", "far_expiry"], sort=True):
            g = g.dropna(subset=["spread_zscore"]).sort_values("trade_date")
            if len(g) < 5:  # too few z-scored days to replay a backtest
                continue
            out[f"{ne.strftime(DMY)} ➔ {fe.strftime(DMY)}"] = {
                "dates": [d.strftime("%Y-%m-%d") for d in g["trade_date"]],
                "dte": [int((ne - d).days) for d in g["trade_date"]],
                "spread": [r2(v) for v in g["calendar_spread"]],
                "zscore": [r2(v) for v in g["spread_zscore"]],
                "near_raw": [float(v) for v in g["near_raw_price"]],
                "far_raw": [float(v) for v in g["far_raw_price"]],
            }
        backtest_data[sym] = out

    # Hero chart: two GOLDM calendar spreads with their expanding historical mean,
    # plus the GOLDM forward curve on the latest date
    def hero_pair(near_month, far_month):
        it = intel["GOLDM"]
        g = it[(it["near_expiry"].dt.strftime("%Y-%m") == near_month)
               & (it["far_expiry"].dt.strftime("%Y-%m") == far_month)].sort_values("trade_date")
        if g.empty:
            return None, None
        ne, fe = g["near_expiry"].iloc[0], g["far_expiry"].iloc[0]
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in g["trade_date"]],
            "spread": [r2(v) for v in g["calendar_spread"]],
            "mean": [r2(v) for v in g["historical_mean"]],
            "label": f"GOLDM {ne:%b %y} ➔ {fe:%b %y} Spread (₹/g)",
        }, (r2(g["calendar_spread"].iloc[-1]) if g["trade_date"].iloc[-1] == latest else None)

    dec_feb, dec_feb_last = hero_pair("2026-12", "2027-02")
    feb_apr, feb_apr_last = hero_pair("2027-02", "2027-04")
    hero_curves = {
        "Dec-Feb": dec_feb,
        "Feb-Apr": feb_apr,
        "Term-Structure": {
            "dates": [c["expiry"] for c in curves["GOLDM"]],
            "spread": [c["norm_price"] for c in curves["GOLDM"]],
            "mean": None,
            "label": "GOLDM Forward Term Structure (₹/1g 999 Gold)",
        },
    }

    carries = [c["carry_pct"] for c in curves["GOLDM"][1:]]
    kpi = {
        "cost_of_carry": f"{np.mean(carries):.2f}" if carries else "—",
        "max_arb_profit": f"₹{max(a['gross_edge'] for a in quiet_alerts_raw):.2f}" if quiet_alerts_raw else "—",
        "dec_feb_val": f"₹{dec_feb_last:.1f}" if dec_feb_last is not None else "—",
        "feb_apr_val": f"₹{feb_apr_last:.1f}" if feb_apr_last is not None else "—",
    }

    # Out-of-sample validation at several split dates, plus P&L attribution.
    # Precomputed here because the static page cannot run the Python engines.
    validation = {}
    for split in ["2026-09-15", "2026-10-01", "2026-10-15", "2026-11-01"]:
        if not (df["trade_date"].min() < pd.Timestamp(split) < latest):
            continue
        v = run_walk_forward_validation(df, split)
        validation[split] = {
            "selected": v["selected"],
            "verdict": v["verdict"],
            "in_sample": v["in_sample"],
            "out_of_sample": v["out_of_sample"],
        }
    attribution = attribute_pnl_vs_underlying(df)
    agent_verification = verify_against_dataset(df)

    return {
        "latest_date": latest.strftime(DMY),
        "avg_norm_price": r2(today["normalized_price_per_gram"].mean()),
        "audit": audit_out,
        "latest_records": latest_records,
        "hist_series": hist_series,
        "quiet_alerts_raw": quiet_alerts_raw,
        "curves": curves,
        "micro_premium": micro_premium,
        "liquidity": liquidity,
        "backtest_data": backtest_data,
        "hero_curves": hero_curves,
        "kpi": kpi,
        # COMEX and USD/INR reference for the latest date (see src/parity_engine.py)
        "validation": validation,
        "agent_verification": agent_verification,
        "attribution": attribution,
        "parity_ref": {
            "date": parity_engine.REFERENCE_DATE,
            "comex_usd_per_oz": parity_engine.REFERENCE_COMEX_USD_PER_OZ,
            "usdinr": parity_engine.REFERENCE_USDINR,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    data = build(load())
    if data["parity_ref"]["date"] != data["latest_date"]:
        print(f"WARNING: parity reference is for {data['parity_ref']['date']} but data ends "
              f"{data['latest_date']}; update REFERENCE_* in src/parity_engine.py")
    if args.check:
        print(json.dumps(data)[:2000])
        return
    html = PAGE_PATH.read_text(encoding="utf-8")
    new = "const DATA = " + json.dumps(data, ensure_ascii=True) + ";"
    html, n = re.subn(r"const DATA = \{.*?\};(?=\s*\n)", lambda _m: new, html, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("Could not find the DATA block in the page")
    PAGE_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote DATA for {data['latest_date']} into {PAGE_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
