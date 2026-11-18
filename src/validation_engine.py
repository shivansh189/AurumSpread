"""Out-of-sample validation and P&L attribution.

Addresses two requirements of the Hack in Hills '26 Track 03 challenge:

1. "validates the approach using unseen historical data" — parameters are
   chosen on an in-sample window only, then applied unchanged to a later
   out-of-sample window the selection never saw.
2. "clearly separate strategy performance from the impact of the underlying
   gold price" — realised P&L is decomposed into the part explained by the
   move in the underlying and the residual spread (relative-value) part.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.backtest_engine import calculate_backtest_summary, run_calendar_spread_backtest
from src.spread_engine import calculate_calendar_spreads
from src.spread_intelligence import calculate_spread_intelligence

DEFAULT_ENTRY_GRID = (1.5, 2.0, 2.5, 3.0)
DEFAULT_EXIT_GRID = (0.0, 0.25, 0.5)


def _pair_frames(df: pd.DataFrame, symbols: Optional[List[str]] = None) -> List[pd.DataFrame]:
    """One intelligence frame per (symbol, expiry pair), z-scores computed on full history."""
    frames: List[pd.DataFrame] = []
    syms = symbols or sorted(df["symbol"].unique())
    for sym in syms:
        spreads = calculate_calendar_spreads(df, symbol=sym)
        if spreads.empty:
            continue
        intel = calculate_spread_intelligence(spreads)
        for _, g in intel.groupby(["near_expiry", "far_expiry"], sort=True):
            g = g.dropna(subset=["spread_zscore"]).sort_values("trade_date")
            if len(g) >= 5:
                frames.append(g.reset_index(drop=True))
    return frames


def _run_window(
    frames: List[pd.DataFrame],
    start: pd.Timestamp,
    end: pd.Timestamp,
    entry_z: float,
    exit_z: float,
    cost_per_leg: float,
    lots: int,
    tender_days: int,
) -> Dict[str, Any]:
    """Backtest every pair inside [start, end] and aggregate the summaries."""
    totals = {"trades": 0, "wins": 0, "net": 0.0, "gross": 0.0, "costs": 0.0}
    curves = []
    for g in frames:
        w = g[(g["trade_date"] >= start) & (g["trade_date"] <= end)]
        if len(w) < 5:
            continue
        res = run_calendar_spread_backtest(
            w,
            entry_zscore=entry_z,
            exit_zscore=exit_z,
            transaction_cost_per_leg=cost_per_leg,
            slippage_per_leg=0.0,
            lots=lots,
            expiry_exit_days=tender_days,
        )
        s = calculate_backtest_summary(res)
        totals["trades"] += s["total_trades"]
        totals["wins"] += s["winning_trades"]
        totals["net"] += s["total_net_pnl"]
        totals["gross"] += s["total_gross_pnl"]
        totals["costs"] += s["total_costs"]
        if s["total_trades"]:
            curves.append(res[["trade_date", "daily_pnl"]])

    daily = (
        pd.concat(curves).groupby("trade_date")["daily_pnl"].sum().sort_index()
        if curves else pd.Series(dtype=float)
    )
    equity = daily.cumsum()
    drawdown = float((equity - equity.cummax()).min()) if not equity.empty else 0.0
    return {
        "start": start.strftime("%Y-%m-%d"),
        "end": end.strftime("%Y-%m-%d"),
        "trades": totals["trades"],
        "win_rate": round(totals["wins"] / totals["trades"] * 100.0, 2) if totals["trades"] else 0.0,
        "gross_pnl": round(totals["gross"], 2),
        "costs": round(totals["costs"], 2),
        "net_pnl": round(totals["net"], 2),
        "net_per_trade": round(totals["net"] / totals["trades"], 2) if totals["trades"] else 0.0,
        "max_drawdown": round(drawdown, 2),
        "equity_dates": [d.strftime("%Y-%m-%d") for d in equity.index],
        "equity_net": [round(float(v), 2) for v in equity.values],
    }


def run_walk_forward_validation(
    df: pd.DataFrame,
    split_date: Any,
    entry_grid: tuple = DEFAULT_ENTRY_GRID,
    exit_grid: tuple = DEFAULT_EXIT_GRID,
    cost_per_leg: float = 7.0,
    lots: int = 1,
    tender_days: int = 5,
    symbols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Select (entry_z, exit_z) on data before split_date, then test after it.

    The out-of-sample window is never used for selection, so its result is an
    honest estimate of what the strategy would have done on unseen data.
    """
    data = df.copy()
    data["trade_date"] = pd.to_datetime(data["trade_date"], errors="coerce", format="mixed")
    data["expiry_date"] = pd.to_datetime(data["expiry_date"], errors="coerce", format="mixed")
    split = pd.to_datetime(split_date)

    frames = _pair_frames(data, symbols)
    first, last = data["trade_date"].min(), data["trade_date"].max()
    if not (first < split < last):
        raise ValueError("split_date must fall inside the dataset's date range")

    grid: List[Dict[str, Any]] = []
    for e in entry_grid:
        for x in exit_grid:
            r = _run_window(frames, first, split - pd.Timedelta(days=1), e, x, cost_per_leg, lots, tender_days)
            grid.append({"entry_z": e, "exit_z": x, **{k: r[k] for k in
                        ("trades", "win_rate", "gross_pnl", "costs", "net_pnl", "net_per_trade", "max_drawdown")}})

    tradeable = [g for g in grid if g["trades"] >= 5] or grid
    best = max(tradeable, key=lambda g: g["net_pnl"])

    in_sample = _run_window(frames, first, split - pd.Timedelta(days=1), best["entry_z"], best["exit_z"],
                            cost_per_leg, lots, tender_days)
    out_sample = _run_window(frames, split, last, best["entry_z"], best["exit_z"],
                             cost_per_leg, lots, tender_days)

    if out_sample["trades"] == 0:
        verdict = "No trades out-of-sample: the tuned thresholds never triggered on unseen data."
    elif out_sample["net_pnl"] > 0 and in_sample["net_pnl"] > 0:
        verdict = (
            f"Edge survived out-of-sample: Rs {out_sample['net_per_trade']:.2f} net per trade on unseen data "
            f"vs Rs {in_sample['net_per_trade']:.2f} in-sample."
        )
    elif out_sample["net_pnl"] <= 0 < in_sample["net_pnl"]:
        verdict = (
            f"Edge did NOT survive out-of-sample: Rs {in_sample['net_per_trade']:.2f} net per trade in-sample "
            f"became Rs {out_sample['net_per_trade']:.2f} on unseen data. The in-sample result was selection bias."
        )
    else:
        verdict = "No post-cost edge in either window."

    return {
        "split_date": split.strftime("%Y-%m-%d"),
        "cost_per_leg": cost_per_leg,
        "selected": {"entry_z": best["entry_z"], "exit_z": best["exit_z"]},
        "grid": grid,
        "in_sample": in_sample,
        "out_of_sample": out_sample,
        "verdict": verdict,
    }


def attribute_pnl_vs_underlying(
    df: pd.DataFrame,
    entry_zscore: float = 2.0,
    exit_zscore: float = 0.0,
    cost_per_leg: float = 7.0,
    lots: int = 1,
    tender_days: int = 5,
    symbols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Split realised P&L into the part explained by the underlying and the rest.

    Each day a spread is held, the two legs move together with gold. Regressing
    daily spread P&L on the daily move of the near leg gives:
        beta  = sensitivity to the underlying (directional exposure)
        beta * underlying move = directional component
        residual = relative-value component (the strategy's own contribution)
    """
    data = df.copy()
    data["trade_date"] = pd.to_datetime(data["trade_date"], errors="coerce", format="mixed")
    data["expiry_date"] = pd.to_datetime(data["expiry_date"], errors="coerce", format="mixed")

    rows = []
    for g in _pair_frames(data, symbols):
        res = run_calendar_spread_backtest(
            g,
            entry_zscore=entry_zscore,
            exit_zscore=exit_zscore,
            transaction_cost_per_leg=cost_per_leg,
            slippage_per_leg=0.0,
            lots=lots,
            expiry_exit_days=tender_days,
        )
        held = res[res["position"] != 0].copy()
        if held.empty:
            continue
        held["underlying_change"] = held["near_raw_price"].diff().fillna(0.0)
        rows.append(held[["trade_date", "gross_daily_pnl", "underlying_change"]])

    if not rows:
        return {"trades_analysed": 0, "beta": 0.0, "r_squared": 0.0,
                "directional_pnl": 0.0, "relative_value_pnl": 0.0, "gross_pnl": 0.0,
                "verdict": "No positions were held, so there is nothing to attribute."}

    obs = pd.concat(rows, ignore_index=True)
    x = obs["underlying_change"].to_numpy(dtype=float)
    y = obs["gross_daily_pnl"].to_numpy(dtype=float)

    if np.allclose(x.var(), 0.0):
        beta, r2 = 0.0, 0.0
    else:
        beta = float(np.cov(x, y, ddof=0)[0, 1] / np.var(x))
        corr = float(np.corrcoef(x, y)[0, 1]) if np.std(y) > 0 else 0.0
        r2 = round(corr ** 2, 4)

    directional = float(beta * x.sum())
    gross = float(y.sum())
    residual = gross - directional
    share = abs(directional) / (abs(directional) + abs(residual)) * 100.0 if (directional or residual) else 0.0

    return {
        "observations": int(len(obs)),
        "beta": round(beta, 4),
        "r_squared": r2,
        "underlying_move": round(float(x.sum()), 2),
        "gross_pnl": round(gross, 2),
        "directional_pnl": round(directional, 2),
        "relative_value_pnl": round(residual, 2),
        "directional_share_pct": round(share, 2),
        "verdict": (
            f"{round(100 - share, 1)}% of gross P&L came from the spread itself; "
            f"{round(share, 1)}% is explained by the move in the underlying gold price "
            f"(beta {beta:.4f}, R-squared {r2:.3f})."
        ),
    }
