
from pathlib import Path

import pandas as pd

from src.spread_engine import calculate_calendar_spreads
from src.spread_intelligence import calculate_spread_intelligence
from src.backtest_engine import run_calendar_spread_backtest

def calculate_backtest_summary(backtest_results):

    # Keep only rows belonging to a trade.
    trade_data = backtest_results.dropna(
        subset=["trade_id"]
    ).copy()

    if trade_data.empty:
        print("\nNo completed trades found.")
        return

    # Group daily P&L by trade ID.
    trade_pnl = (
        trade_data.groupby("trade_id")["daily_pnl"]
        .sum()
    )

    # Identify all completed trade exit actions.
    completed_exit_actions = [
        "Exit Long Spread",
        "Exit Short Spread",
        "Expiry Exit Long Spread",
        "Expiry Exit Short Spread",
        "End of Data Exit Long Spread",
        "End of Data Exit Short Spread",
    ]

    completed_trade_ids = (
        trade_data[
            trade_data["action"].isin(
                completed_exit_actions
            )
        ]["trade_id"]
        .dropna()
        .unique()
    )

    # Keep only completed trades.
    completed_trades = trade_pnl[
        trade_pnl.index.isin(
            completed_trade_ids
        )
    ]

    if completed_trades.empty:
        print("\nNo completed trades found.")
        return

    # Performance metrics.
    total_trades = len(completed_trades)

    winning_trades = (
        completed_trades > 0
    ).sum()

    losing_trades = (
        completed_trades < 0
    ).sum()

    win_rate = (
        winning_trades / total_trades
    ) * 100

    total_pnl = completed_trades.sum()

    average_trade_pnl = (
        completed_trades.mean()
    )

    # Maximum drawdown.
    cumulative_pnl = (
        backtest_results["daily_pnl"].cumsum()
    )

    running_peak = (
        cumulative_pnl.cummax()
    )

    drawdown = (
        cumulative_pnl - running_peak
    )

    maximum_drawdown = drawdown.min()

    # Display summary.
    print("\nBACKTEST PERFORMANCE SUMMARY")
    print("------------------------")

    print(f"Completed trades: {total_trades}")
    print(f"Winning trades: {winning_trades}")
    print(f"Losing trades: {losing_trades}")
    print(f"Win rate: {win_rate:.2f}%")

    print(f"Total net P&L: ₹{total_pnl:.2f}")

    print(
        f"Average P&L per trade: "
        f"₹{average_trade_pnl:.2f}"
    )

    print(
        f"Maximum drawdown: "
        f"₹{maximum_drawdown:.2f}"
    )
    
DATA_PATH = Path(
    "data/processed/historical_gold_futures.csv"
)

# Load historical data.
df = pd.read_csv(DATA_PATH)

# Choose an instrument and expiry pair.
symbol = "GOLDGUINEA"
near_expiry = "2026-07-31"
far_expiry = "2026-08-31"

# Generate calendar spreads.
spread_data = calculate_calendar_spreads(
    df=df,
    symbol=symbol,
)

# Select the chosen expiry pair.
selected_spread = spread_data[
    (spread_data["near_expiry"] == pd.Timestamp(near_expiry))
    & (spread_data["far_expiry"] == pd.Timestamp(far_expiry))
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
    transaction_cost_per_leg=0.0,
    slippage_per_leg=0.0,
)

print("\nCALENDAR SPREAD BACKTEST TEST")
print("----------------------------")

print("Instrument:", symbol)
print("Expiry pair:", near_expiry, "-", far_expiry)
print("Observations:", len(backtest))

print("\nBacktest actions:")
print(backtest["action"].value_counts())

print("\nFirst 10 observations:")
print(
    backtest[
        [
            "trade_date",
            "calendar_spread",
            "spread_zscore",
            "position",
            "action",
            "daily_pnl",
        ]
    ].head(10).to_string(index=False)
)

print("\nTotal simulated P&L:")
print(round(backtest["daily_pnl"].sum(), 4))

print("\nMissing values:")
print(backtest.isna().sum())

calculate_backtest_summary(backtest)

def test_expiry_exit():
    import pandas as pd
    from src.backtest_engine import run_calendar_spread_backtest

    test_data = pd.DataFrame({
        "trade_date": [
            "2026-09-28",
            "2026-09-29",
        ],
        "near_expiry": [
            "2026-09-30",
            "2026-09-30",
        ],
        "far_expiry": [
            "2026-10-30",
            "2026-10-30",
        ],
        "near_price": [100, 101],
        "far_price": [110, 111],
        "calendar_spread": [10, 10],
        "spread_zscore": [-2.5, -1.5],
    })

    results = run_calendar_spread_backtest(
        test_data,
        entry_zscore=2.0,
        exit_zscore=0.0,
    )

    print("\nEXPIRY EXIT TEST")
    print(results[[
        "trade_date",
        "spread_zscore",
        "position",
        "action",
        "trade_id",
    ]])

    assert results.iloc[0]["action"] == "Enter Long Spread"
    assert results.iloc[1]["action"] == "Expiry Exit Long Spread"
    assert results.iloc[1]["position"] == 0
    assert results.iloc[1]["trade_id"] == 1

test_expiry_exit()