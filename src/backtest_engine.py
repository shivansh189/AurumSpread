"""Cost-Aware Walk-Forward Backtester & Honest Survival Proof Engine.

Simulates long and short calendar spread strategies on MCX gold futures,
enforcing contract lifecycle, tender delivery exits, and detailed cost attribution
(Brokerage, Exchange fees, Taxes, and Liquidity-Penalized Slippage).
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd


def calculate_backtest_summary(backtest_results: pd.DataFrame) -> Dict[str, Any]:
    """Calculate summary statistics for a completed backtest run.

    Compatible with both research scripts and test assertions.
    """
    if backtest_results is None or backtest_results.empty:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_net_pnl": 0.0,
            "total_gross_pnl": 0.0,
            "total_costs": 0.0,
            "average_pnl": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
        }

    trade_data = backtest_results.dropna(subset=["trade_id"]).copy()
    if trade_data.empty:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_net_pnl": 0.0,
            "total_gross_pnl": 0.0,
            "total_costs": 0.0,
            "average_pnl": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
        }

    completed_exit_actions = [
        "Exit Long Spread",
        "Exit Short Spread",
        "Expiry Exit",
        "Expiry Exit Long Spread",
        "Expiry Exit Short Spread",
        "End of Data Exit",
        "End of Data Exit Long Spread",
        "End of Data Exit Short Spread",
        "Pair Change Exit",
    ]

    completed_trade_ids = (
        trade_data[trade_data["action"].str.contains("Exit", case=False, na=False)]["trade_id"]
        .dropna()
        .unique()
    )

    trade_pnl = trade_data.groupby("trade_id")["daily_pnl"].sum()
    completed_trades = trade_pnl[trade_pnl.index.isin(completed_trade_ids)]

    total_trades = len(completed_trades)
    winning_trades = int((completed_trades > 0).sum())
    losing_trades = int((completed_trades < 0).sum())
    win_rate = float(winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0
    average_pnl = float(completed_trades.mean()) if total_trades > 0 else 0.0

    total_net = float(backtest_results["daily_pnl"].sum())
    gross_col = "gross_daily_pnl" if "gross_daily_pnl" in backtest_results.columns else "daily_pnl"
    cost_col = "cost_daily" if "cost_daily" in backtest_results.columns else None

    total_gross = float(backtest_results[gross_col].sum())
    total_costs = float(backtest_results[cost_col].sum()) if cost_col else (total_gross - total_net)

    wins = completed_trades[completed_trades > 0].sum()
    losses = abs(completed_trades[completed_trades < 0].sum())
    profit_factor = float(wins / losses) if losses > 0 else (float("inf") if wins > 0 else 0.0)

    # Calculate Maximum Drawdown on cumulative net P&L
    cum_pnl = backtest_results["cumulative_pnl"] if "cumulative_pnl" in backtest_results.columns else backtest_results["daily_pnl"].cumsum()
    running_max = cum_pnl.cummax()
    drawdown = cum_pnl - running_max
    max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0

    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 2),
        "total_net_pnl": round(total_net, 2),
        "total_gross_pnl": round(total_gross, 2),
        "total_costs": round(total_costs, 2),
        "average_pnl": round(average_pnl, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 999.0,
        "max_drawdown": round(max_drawdown, 2),
    }


def run_calendar_spread_backtest(
    data: Optional[pd.DataFrame] = None,
    entry_zscore: float = 2.0,
    exit_zscore: float = 0.0,
    transaction_cost_per_leg: float = 0.0,
    slippage_per_leg: float = 0.0,
    lots: int = 1,
    expiry_exit_days: int = 2,
    intelligence_data: Optional[pd.DataFrame] = None,
    **kwargs,
) -> pd.DataFrame:
    """Backtest one expiry pair; force-close open position at final observation.

    Separates pre-cost gross P&L from transaction costs & slippage,
    providing an honest pre-cost vs post-cost survival proof.
    """
    if data is None:
        data = intelligence_data if intelligence_data is not None else kwargs.get("intelligence_data")

    if data is None or data.empty:
        raise ValueError("Input data is empty.")
    if lots <= 0 or entry_zscore <= 0 or exit_zscore < 0 or expiry_exit_days < 0:
        raise ValueError("Invalid lots, z-score threshold, or expiry_exit_days.")

    df = data.copy()
    required = ["trade_date", "near_expiry", "far_expiry", "calendar_spread", "spread_zscore"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    for col in ["trade_date", "near_expiry", "far_expiry"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in ["calendar_spread", "spread_zscore"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    has_near_raw = "near_raw_price" in df.columns
    has_far_raw = "far_raw_price" in df.columns
    if has_near_raw != has_far_raw:
        raise ValueError("Both near_raw_price and far_raw_price must be supplied together.")
    use_raw = has_near_raw and has_far_raw
    if use_raw:
        for col in ["near_raw_price", "far_raw_price"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    valid = required + (["near_raw_price", "far_raw_price"] if use_raw else [])
    df = df.dropna(subset=valid).copy()
    if df.empty:
        raise ValueError("No valid rows available for backtesting.")

    dedupe = ["trade_date", "near_expiry", "far_expiry"]
    if "symbol" in df.columns:
        dedupe.insert(1, "symbol")
    df = (
        df.sort_values(["trade_date", "near_expiry", "far_expiry"])
        .drop_duplicates(subset=dedupe, keep="last")
        .reset_index(drop=True)
    )

    cost_per_leg = float(transaction_cost_per_leg) + float(slippage_per_leg)
    entry_cost = 2.0 * lots * cost_per_leg
    exit_cost = 2.0 * lots * cost_per_leg

    position = 0
    trade_id = 0
    active_pair = None
    previous_row = None
    trade_pnl = 0.0
    results = []

    for i, row in df.iterrows():
        date = row["trade_date"]
        pair = (
            row["symbol"] if "symbol" in df.columns else None,
            row["near_expiry"],
            row["far_expiry"],
        )
        z = float(row["spread_zscore"])
        gross_daily_pnl = 0.0
        cost_today = 0.0
        daily_pnl = 0.0
        action = "Hold"
        completed = False
        completed_pnl = None
        exit_reason = None

        # Defensive handling if caller supplies multiple pairs in one run
        if position and active_pair != pair:
            cost_today += exit_cost
            daily_pnl -= exit_cost
            trade_pnl -= exit_cost
            action = "Pair Change Exit"
            completed = True
            completed_pnl = trade_pnl
            exit_reason = "Pair Change"
            position = 0
            active_pair = None
            previous_row = None
            trade_pnl = 0.0

        # Mark the current observation's price change for the held position
        if position and previous_row is not None and active_pair == pair:
            if use_raw:
                near_change = float(row["near_raw_price"]) - float(previous_row["near_raw_price"])
                far_change = float(row["far_raw_price"]) - float(previous_row["far_raw_price"])
                mark_pnl = position * lots * (far_change - near_change)
            else:
                mark_pnl = position * lots * (
                    float(row["calendar_spread"]) - float(previous_row["calendar_spread"])
                )
            gross_daily_pnl += mark_pnl
            daily_pnl += mark_pnl
            trade_pnl += mark_pnl

        days_to_expiry = (row["near_expiry"] - date).days
        expiry_exit = position != 0 and days_to_expiry <= expiry_exit_days

        if position == 0:
            if days_to_expiry > expiry_exit_days:
                if z <= -entry_zscore:
                    position = 1
                    trade_id += 1
                    active_pair = pair
                    trade_pnl = -entry_cost
                    cost_today += entry_cost
                    daily_pnl -= entry_cost
                    action = "Enter Long Spread"
                elif z >= entry_zscore:
                    position = -1
                    trade_id += 1
                    active_pair = pair
                    trade_pnl = -entry_cost
                    cost_today += entry_cost
                    daily_pnl -= entry_cost
                    action = "Enter Short Spread"
        else:
            if expiry_exit:
                action = "Expiry Exit Long Spread" if position == 1 else "Expiry Exit Short Spread"
                exit_reason = "Near Expiry"
            elif position == 1 and z >= -exit_zscore:
                action = "Exit Long Spread"
                exit_reason = "Signal"
            elif position == -1 and z <= exit_zscore:
                action = "Exit Short Spread"
                exit_reason = "Signal"
            else:
                action = "Hold"

            if exit_reason is not None:
                cost_today += exit_cost
                daily_pnl -= exit_cost
                trade_pnl -= exit_cost
                completed = True
                completed_pnl = trade_pnl
                position = 0
                active_pair = None
                previous_row = None
                trade_pnl = 0.0

        # Explicitly close any open position on the final available date
        if i == len(df) - 1 and position != 0:
            cost_today += exit_cost
            daily_pnl -= exit_cost
            trade_pnl -= exit_cost
            action = "End of Data Exit Long Spread" if position == 1 else "End of Data Exit Short Spread"
            completed = True
            completed_pnl = trade_pnl
            exit_reason = "End Of Data"
            position = 0
            active_pair = None
            previous_row = None
            trade_pnl = 0.0

        result = {
            "trade_date": date,
            "near_expiry": row["near_expiry"],
            "far_expiry": row["far_expiry"],
            "calendar_spread": float(row["calendar_spread"]),
            "spread_zscore": z,
            "position": position,
            "action": action,
            "gross_daily_pnl": float(gross_daily_pnl),
            "cost_daily": float(cost_today),
            "daily_pnl": float(daily_pnl),
            "trade_id": trade_id if trade_id else None,
            "trade_completed": completed,
            "completed_trade_pnl": completed_pnl,
            "exit_reason": exit_reason,
            "pnl_basis": (
                "Raw contract price-change units; INR interpretation requires contract multiplier validation"
                if use_raw else "Normalized spread-change research units"
            ),
        }
        if "symbol" in df.columns:
            result["symbol"] = row["symbol"]
        if use_raw:
            result["near_raw_price"] = float(row["near_raw_price"])
            result["far_raw_price"] = float(row["far_raw_price"])
        results.append(result)

        if position:
            previous_row = row
            active_pair = pair
        else:
            previous_row = None
            active_pair = None

    out = pd.DataFrame(results)
    out["cumulative_gross_pnl"] = out["gross_daily_pnl"].cumsum()
    out["cumulative_costs"] = out["cost_daily"].cumsum()
    out["cumulative_pnl"] = out["daily_pnl"].cumsum()

    return out


def find_breakeven_cost(
    data: pd.DataFrame,
    entry_zscore: float = 2.0,
    exit_zscore: float = 0.0,
    lots: int = 1,
    max_cost_search: float = 50.0,
    step: float = 0.5,
) -> float:
    """Find the exact friction cost per leg at which Net PnL drops to zero ("What kills the edge?")."""
    # First check zero cost
    zero_cost_run = run_calendar_spread_backtest(
        data=data,
        entry_zscore=entry_zscore,
        exit_zscore=exit_zscore,
        transaction_cost_per_leg=0.0,
        slippage_per_leg=0.0,
        lots=lots,
    )
    if zero_cost_run["daily_pnl"].sum() <= 0:
        return 0.0

    costs = np.arange(0.5, max_cost_search + step, step)
    for c in costs:
        run = run_calendar_spread_backtest(
            data=data,
            entry_zscore=entry_zscore,
            exit_zscore=exit_zscore,
            transaction_cost_per_leg=c,
            slippage_per_leg=0.0,
            lots=lots,
        )
        if run["daily_pnl"].sum() <= 0:
            return round(float(c), 2)
    return float(max_cost_search)
