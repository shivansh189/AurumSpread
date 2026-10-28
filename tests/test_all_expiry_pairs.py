from pathlib import Path

import pandas as pd

from src.spread_engine import calculate_calendar_spreads
from src.spread_intelligence import calculate_spread_intelligence
from src.backtest_engine import run_calendar_spread_backtest


# Load historical MCX data.
DATA_PATH = Path(
    "data/processed/historical_gold_futures.csv"
)

df = pd.read_csv(DATA_PATH)

# Generate all calendar spreads for GOLDGUINEA.
symbol = "GOLDGUINEA"

spread_data = calculate_calendar_spreads(
    df=df,
    symbol=symbol,
)

# Identify all available expiry pairs.
expiry_pairs = (
    spread_data[
        ["near_expiry", "far_expiry"]
    ]
    .drop_duplicates()
    .sort_values(
        ["near_expiry", "far_expiry"]
    )
)

results = []

print("\nBACKTEST ACROSS ALL EXPIRY PAIRS")
print("--------------------------------")

for _, pair in expiry_pairs.iterrows():

    near_expiry = pair["near_expiry"]
    far_expiry = pair["far_expiry"]

    # Select the current expiry pair.
    selected_spread = spread_data[
        (
            spread_data["near_expiry"]
            == near_expiry
        )
        &
        (
            spread_data["far_expiry"]
            == far_expiry
        )
    ].sort_values("trade_date")

    # Calculate spread intelligence.
    intelligence = calculate_spread_intelligence(
        selected_spread
    )

    # Run the backtest.
    backtest = run_calendar_spread_backtest(
        intelligence_data=intelligence,
        entry_zscore=2.0,
        exit_zscore=0.0,
        transaction_cost_per_leg=5.0,
        slippage_per_leg=2.0,
    )

    # Identify completed trades.
    exit_actions = [
        "Exit Long Spread",
        "Exit Short Spread",
        "Expiry Exit Long Spread",
        "Expiry Exit Short Spread",
        "End of Data Exit Long Spread",
        "End of Data Exit Short Spread",
    ]

    completed_trades = backtest[
        backtest["action"].isin(exit_actions)
    ]

    # Calculate trade-level performance.
    trade_data = backtest.dropna(
        subset=["trade_id"]
    )

    trade_pnl = (
        trade_data.groupby("trade_id")["daily_pnl"]
        .sum()
    )

    completed_trade_ids = (
        completed_trades["trade_id"]
        .dropna()
        .unique()
    )

    completed_trade_pnl = trade_pnl[
        trade_pnl.index.isin(
            completed_trade_ids
        )
    ]

    total_pnl = completed_trade_pnl.sum()

    total_trades = len(
        completed_trade_pnl
    )

    winning_trades = (
        completed_trade_pnl > 0
    ).sum()

    win_rate = (
        winning_trades / total_trades * 100
        if total_trades > 0
        else 0
    )

    results.append({
        "near_expiry": near_expiry,
        "far_expiry": far_expiry,
        "observations": len(backtest),
        "completed_trades": total_trades,
        "winning_trades": winning_trades,
        "win_rate": round(win_rate, 2),
        "net_pnl": round(total_pnl, 2),
    })


# Create comparison table.
results_df = pd.DataFrame(results)

print(
    results_df.to_string(
        index=False
    )
)

# -------------------------------------------------
# Overall performance summary
# -------------------------------------------------

total_expiry_pairs = len(results_df)

pairs_with_trades = (
    results_df["completed_trades"] > 0
).sum()

profitable_pairs = (
    results_df["net_pnl"] > 0
).sum()

losing_pairs = (
    results_df["net_pnl"] < 0
).sum()

total_completed_trades = (
    results_df["completed_trades"].sum()
)

total_winning_trades = (
    results_df["winning_trades"].sum()
)

total_losing_trades = (
    total_completed_trades
    - total_winning_trades
)

overall_win_rate = (
    total_winning_trades
    / total_completed_trades
    * 100
    if total_completed_trades > 0
    else 0
)

total_net_pnl = results_df["net_pnl"].sum()

print("\nOVERALL PERFORMANCE SUMMARY")
print("-------------------------")

print(
    f"Total expiry pairs tested: "
    f"{total_expiry_pairs}"
)

print(
    f"Expiry pairs with trades: "
    f"{pairs_with_trades}"
)

print(
    f"Profitable expiry pairs: "
    f"{profitable_pairs}"
)

print(
    f"Losing expiry pairs: "
    f"{losing_pairs}"
)

print(
    f"Total completed trades: "
    f"{total_completed_trades}"
)

print(
    f"Winning trades: "
    f"{total_winning_trades}"
)

print(
    f"Losing trades: "
    f"{total_losing_trades}"
)

print(
    f"Overall win rate: "
    f"{overall_win_rate:.2f}%"
)

print(
    f"Combined net P&L: "
    f"₹{total_net_pnl:.2f}"
)

print("\nExpiry pair comparison completed.")