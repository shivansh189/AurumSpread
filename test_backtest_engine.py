
import pandas as pd

from src.backtest_engine import run_calendar_spread_backtest


# ============================================================
# LONG SPREAD TEST
# ============================================================

test_data = pd.DataFrame({
    "trade_date": [
        "2026-10-01",
        "2026-10-02",
        "2026-10-05",
        "2026-10-06",
    ],
    "near_expiry": [
        "2026-12-31",
        "2026-12-31",
        "2026-12-31",
        "2026-12-31",
    ],
    "far_expiry": [
        "2027-01-29",
        "2027-01-29",
        "2027-01-29",
        "2027-01-29",
    ],
    "calendar_spread": [100, 98, 99, 101],
    "spread_zscore": [-0.5, -2.5, -1.0, 0.5],
})

results = run_calendar_spread_backtest(
    test_data,
    entry_zscore=2.0,
    exit_zscore=0.0,
)

print("\n========== LONG SPREAD TEST ==========")

print(results[
    [
        "trade_date",
        "calendar_spread",
        "spread_zscore",
        "position",
        "action",
        "daily_pnl",
    ]
].to_string(index=False))

print("\nTotal P&L:", results["daily_pnl"].sum())


# ============================================================
# TRANSACTION COST TEST
# ============================================================

cost_results = run_calendar_spread_backtest(
    test_data,
    entry_zscore=2.0,
    exit_zscore=0.0,
    transaction_cost_per_leg=5.0,
    slippage_per_leg=2.0,
)

print("\n========== TRANSACTION COST TEST ==========")

print("\nP&L with costs:", cost_results["daily_pnl"].sum())


# ============================================================
# EXPIRY EXIT TEST
# ============================================================

expiry_test_data = pd.DataFrame({
    "trade_date": pd.to_datetime([
        "2026-10-01",
        "2026-10-02",
        "2026-10-05",
        "2026-10-06",
    ]),
    "near_expiry": [
        pd.Timestamp("2026-10-05"),
        pd.Timestamp("2026-10-05"),
        pd.Timestamp("2026-10-05"),
        pd.Timestamp("2026-10-05"),
    ],
    "far_expiry": [
        pd.Timestamp("2026-10-30"),
        pd.Timestamp("2026-10-30"),
        pd.Timestamp("2026-10-30"),
        pd.Timestamp("2026-10-30"),
    ],
    "calendar_spread": [100, 98, 99, 101],
    "spread_zscore": [-0.5, -2.5, -1.0, 0.5],
})

expiry_results = run_calendar_spread_backtest(
    expiry_test_data,
    entry_zscore=2.0,
    exit_zscore=0.0,
)

print("\n========== EXPIRY EXIT TEST ==========")

print(expiry_results[
    [
        "trade_date",
        "calendar_spread",
        "position",
        "action",
        "daily_pnl",
    ]
].to_string(index=False))


# ============================================================
# SHORT SPREAD TEST
# ============================================================

short_test_data = pd.DataFrame({
    "trade_date": pd.to_datetime([
        "2026-10-01",
        "2026-10-02",
        "2026-10-05",
        "2026-10-06",
    ]),
    "near_expiry": [
        pd.Timestamp("2026-12-31")
    ] * 4,
    "far_expiry": [
        pd.Timestamp("2027-01-29")
    ] * 4,
    "calendar_spread": [100, 102, 101, 99],
    "spread_zscore": [0.5, 2.5, 1.0, -0.5],
})

short_results = run_calendar_spread_backtest(
    short_test_data,
    entry_zscore=2.0,
    exit_zscore=0.0,
)

print("\n========== SHORT SPREAD TEST ==========")

print(short_results[
    [
        "trade_date",
        "calendar_spread",
        "spread_zscore",
        "position",
        "action",
        "daily_pnl",
    ]
].to_string(index=False))

print("\nTotal P&L:", short_results["daily_pnl"].sum())


# ============================================================
# MULTIPLE TRADES TEST
# ============================================================

multiple_test_data = pd.DataFrame({
    "trade_date": pd.to_datetime([
        "2026-10-01",
        "2026-10-02",
        "2026-10-05",
        "2026-10-06",
        "2026-10-07",
        "2026-10-08",
    ]),
    "near_expiry": [
        pd.Timestamp("2026-12-31")
    ] * 6,
    "far_expiry": [
        pd.Timestamp("2027-01-29")
    ] * 6,
    "calendar_spread": [100, 98, 101, 100, 102, 105],
    "spread_zscore": [-0.5, -2.5, 0.5, 0.5, 2.5, -0.5],
})

multiple_results = run_calendar_spread_backtest(
    multiple_test_data,
    entry_zscore=2.0,
    exit_zscore=0.0,
)

print("\n========== MULTIPLE TRADES TEST ==========")

print(multiple_results[
    [
        "trade_date",
        "calendar_spread",
        "spread_zscore",
        "position",
        "action",
        "daily_pnl",
        "trade_id",
    ]
].to_string(index=False))

print("\nTotal P&L:", multiple_results["daily_pnl"].sum())


# ============================================================
# END OF DATA EXIT TEST
# ============================================================

end_test_data = pd.DataFrame({
    "trade_date": pd.to_datetime([
        "2026-10-01",
        "2026-10-02",
        "2026-10-05",
    ]),
    "near_expiry": [
        pd.Timestamp("2026-12-31")
    ] * 3,
    "far_expiry": [
        pd.Timestamp("2027-01-29")
    ] * 3,
    "calendar_spread": [100, 98, 99],
    "spread_zscore": [-0.5, -2.5, -1.0],
})

end_results = run_calendar_spread_backtest(
    end_test_data,
    entry_zscore=2.0,
    exit_zscore=0.0,
)

print("\n========== END OF DATA EXIT TEST ==========")

print(end_results[
    [
        "trade_date",
        "calendar_spread",
        "spread_zscore",
        "position",
        "action",
        "daily_pnl",
    ]
].to_string(index=False))

print("\nTotal P&L:", end_results["daily_pnl"].sum())


# ============================================================
# BACKTEST SUMMARY TEST
# ============================================================

summary_data = multiple_results.copy()

completed_trades = summary_data[
    summary_data["action"].str.contains("Exit", na=False)
]

trade_pnl = completed_trades.groupby("trade_id")["daily_pnl"].sum()

total_trades = len(trade_pnl)

winning_trades = (trade_pnl > 0).sum()
losing_trades = (trade_pnl < 0).sum()

win_rate = (
    winning_trades / total_trades * 100
    if total_trades > 0
    else 0
)

average_pnl = (
    trade_pnl.mean()
    if total_trades > 0
    else 0
)

cumulative_pnl = summary_data["daily_pnl"].cumsum()

running_peak = cumulative_pnl.cummax()

drawdown = cumulative_pnl - running_peak

max_drawdown = drawdown.min()

print("\n========== BACKTEST SUMMARY ==========")

print("Total Trades:", total_trades)
print("Winning Trades:", winning_trades)
print("Losing Trades:", losing_trades)
print("Win Rate:", round(win_rate, 2), "%")
print("Average P&L:", round(average_pnl, 2))
print("Total P&L:", round(summary_data["daily_pnl"].sum(), 2))
print("Maximum Drawdown:", round(max_drawdown, 2))
