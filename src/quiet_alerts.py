"""Quiet Alert Scanner & Signal Validation Engine.

Suppresses false-positive arbitrage noise by validating prospective calendar spread
signals against MCX tender windows, liquidity depth, and post-cost friction.
Alerts fire ONLY when an edge survives all realistic execution costs.
"""

from typing import Dict, Any, List
import pandas as pd
from src.spread_engine import calculate_calendar_spreads
from src.spread_intelligence import calculate_spread_intelligence
from src.liquidity_engine import is_tender_period, estimate_fill_slippage


def scan_quiet_alerts(
    df: pd.DataFrame,
    entry_zscore: float = 1.5,
    transaction_cost_per_leg: float = 5.0,
    slippage_per_leg: float = 2.0,
    min_volume: float = 30.0,
    tender_days: int = 5,
) -> Dict[str, Any]:
    """Scan latest market data across all MCX gold contracts for quiet alerts.

    Returns verified post-cost signals and full suppression audit.
    """
    data = df.copy()
    data["trade_date"] = pd.to_datetime(data["trade_date"], errors="coerce", format="mixed")
    data["expiry_date"] = pd.to_datetime(data["expiry_date"], errors="coerce", format="mixed")
    latest_date = data["trade_date"].max()

    all_alerts: List[Dict[str, Any]] = []
    symbols = sorted(data["symbol"].unique())

    total_pairs_evaluated = 0
    raw_signals_count = 0
    tender_suppressed_count = 0
    liquidity_suppressed_count = 0
    cost_suppressed_count = 0
    active_alerts_count = 0

    for symbol in symbols:
        sym_data = data[data["symbol"] == symbol]
        if sym_data.empty or sym_data["expiry_date"].nunique() < 2:
            continue

        try:
            spreads = calculate_calendar_spreads(data, symbol=symbol)
            if spreads.empty:
                continue

            intel = calculate_spread_intelligence(spreads)
            latest_intel = intel[intel["trade_date"] == latest_date].copy()

            for _, row in latest_intel.iterrows():
                total_pairs_evaluated += 1
                near_exp = pd.to_datetime(row["near_expiry"])
                far_exp = pd.to_datetime(row["far_expiry"])
                z = row.get("spread_zscore")
                spread = row.get("calendar_spread", 0.0)
                mean_spread = row.get("historical_mean", spread)
                std_spread = row.get("historical_std", 1.0)

                # Look up near-leg volume and OI
                near_rows = sym_data[
                    (sym_data["trade_date"] == latest_date)
                    & (sym_data["expiry_date"] == near_exp)
                ]
                near_vol = float(near_rows["volume_lots"].iloc[0]) if not near_rows.empty else 0.0
                near_oi = float(near_rows["open_interest_lots"].iloc[0]) if not near_rows.empty else 0.0

                penalized_slippage, is_fillable = estimate_fill_slippage(
                    base_slippage_inr=slippage_per_leg,
                    volume_lots=near_vol,
                    oi_lots=near_oi,
                    min_volume_threshold=min_volume,
                )

                round_trip_cost = 2.0 * (transaction_cost_per_leg + penalized_slippage)

                if pd.isna(z):
                    all_alerts.append({
                        "trade_date": latest_date.strftime("%d %b %Y"),
                        "symbol": symbol,
                        "near_expiry": near_exp.strftime("%d %b %Y"),
                        "far_expiry": far_exp.strftime("%d %b %Y"),
                        "signal_type": "Insufficient History",
                        "spread_zscore": None,
                        "calendar_spread_inr": round(float(spread), 2),
                        "gross_edge_inr": 0.0,
                        "round_trip_cost_inr": round(round_trip_cost, 2),
                        "net_edge_inr": 0.0,
                        "volume_lots": int(near_vol),
                        "status": "Inspecting (<10 prior obs)",
                        "badge_color": "gray",
                        "reason": "Requires at least 10 prior historical observations for Z-score convergence.",
                    })
                    continue

                is_raw_signal = abs(float(z)) >= entry_zscore
                gross_edge_inr = abs(float(spread) - float(mean_spread))
                net_edge_inr = gross_edge_inr - round_trip_cost

                # Tender period check
                in_tender = is_tender_period(latest_date, near_exp, tender_days=tender_days)

                if is_raw_signal:
                    raw_signals_count += 1
                    signal_type = "Long Spread (Undervalued)" if float(z) <= -entry_zscore else "Short Spread (Overvalued)"

                    if in_tender:
                        status = "Suppressed (Tender Lockout)"
                        reason = f"Near contract expires in {(near_exp - latest_date).days} days; MCX tender window active."
                        tender_suppressed_count += 1
                        badge_color = "red"
                    elif not is_fillable or near_vol < min_volume:
                        status = "Suppressed (Thin Liquidity)"
                        reason = f"Near contract volume is only {int(near_vol)} lots (min required: {int(min_volume)} lots)."
                        liquidity_suppressed_count += 1
                        badge_color = "orange"
                    elif net_edge_inr <= 0:
                        status = "Suppressed (Fee / Cost Trap)"
                        reason = f"Gross edge ₹{gross_edge_inr:.2f}/g is wiped out by ₹{round_trip_cost:.2f}/g total roundtrip costs."
                        cost_suppressed_count += 1
                        badge_color = "blue"
                    else:
                        status = "ACTIVE QUIET ALERT"
                        reason = f"Verified post-cost edge: ₹{net_edge_inr:.2f}/g net edge after all friction."
                        active_alerts_count += 1
                        badge_color = "green"
                else:
                    signal_type = "Fair Value / No Signal"
                    status = "Fair Value (Normal)"
                    reason = f"Spread Z-score ({float(z):.2f}) is within normal historical boundary (±{entry_zscore})."
                    badge_color = "gray"

                all_alerts.append({
                    "trade_date": latest_date.strftime("%d %b %Y"),
                    "symbol": symbol,
                    "near_expiry": near_exp.strftime("%d %b %Y"),
                    "far_expiry": far_exp.strftime("%d %b %Y"),
                    "signal_type": signal_type,
                    "spread_zscore": round(float(z), 2),
                    "calendar_spread_inr": round(float(spread), 2),
                    "gross_edge_inr": round(gross_edge_inr, 2),
                    "round_trip_cost_inr": round(round_trip_cost, 2),
                    "net_edge_inr": round(net_edge_inr, 2),
                    "volume_lots": int(near_vol),
                    "status": status,
                    "badge_color": badge_color,
                    "reason": reason,
                })
        except Exception:
            continue

    alerts_df = pd.DataFrame(all_alerts)

    return {
        "latest_date": latest_date,
        "total_pairs_evaluated": total_pairs_evaluated,
        "raw_signals_count": raw_signals_count,
        "tender_suppressed_count": tender_suppressed_count,
        "liquidity_suppressed_count": liquidity_suppressed_count,
        "cost_suppressed_count": cost_suppressed_count,
        "active_alerts_count": active_alerts_count,
        "alerts_df": alerts_df,
    }
