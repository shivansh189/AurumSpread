
import pandas as pd
import numpy as np

from src.backtest_engine import run_calendar_spread_backtest


# ==========================================
# CONFIGURATION
# ==========================================

SYMBOL = "GOLDGUINEA"

NEAR_EXPIRY = "2026-10-30"
FAR_EXPIRY = "2026-11-30"

ENTRY_THRESHOLDS = [1.0, 1.25, 1.5, 1.75, 2.0]

EXIT_ZSCORE = 0.0
LOTS = 1

# Keep these at zero for the initial comparison.
# Later, test realistic costs and slippage.
# Estimated cost per leg, per lot, in INR
TRANSACTION_COST_PER_LEG = 10.0

# Estimated slippage per leg, per lot, in INR
SLIPPAGE_PER_LEG = 5.0


# ==========================================
# LOAD DATA
# ==========================================

print("\nLoading spread intelligence data...")

data = pd.read_csv(
    "data/processed/spread_intelligence.csv"
)

data["trade_date"] = pd.to_datetime(
    data["trade_date"]
)

data["near_expiry"] = pd.to_datetime(
    data["near_expiry"]
)

data["far_expiry"] = pd.to_datetime(
    data["far_expiry"]
)

near_expiry = pd.to_datetime(NEAR_EXPIRY)
far_expiry = pd.to_datetime(FAR_EXPIRY)


# ==========================================
# FILTER SELECTED SYMBOL AND EXPIRY PAIR
# ==========================================

selected_data = data[
    (data["symbol"] == SYMBOL)
    & (data["near_expiry"] == near_expiry)
    & (data["far_expiry"] == far_expiry)
].copy()

selected_data = selected_data.sort_values(
    "trade_date"
).reset_index(drop=True)


if selected_data.empty:
    raise ValueError(
        "No data found for the selected symbol and expiry pair. "
        "Check SYMBOL, NEAR_EXPIRY, and FAR_EXPIRY."
    )


print("\nSelected configuration:")
print(f"Symbol: {SYMBOL}")
print(f"Near expiry: {NEAR_EXPIRY}")
print(f"Far expiry: {FAR_EXPIRY}")
print(f"Rows: {len(selected_data)}")

print(
    f"Date range: "
    f"{selected_data['trade_date'].min().date()} to "
    f"{selected_data['trade_date'].max().date()}"
)


# ==========================================
# HELPER: CALCULATE PERFORMANCE METRICS
# ==========================================

def calculate_metrics(results):

    if results.empty:
        return {
            "trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "avg_pnl_per_trade": 0.0,
        }

    # Ensure results are chronological
    results = results.sort_values(
        "trade_date"
    ).reset_index(drop=True)

    # --------------------------------------
    # Total P&L
    # --------------------------------------

    daily_pnl = results["daily_pnl"].fillna(0)

    total_pnl = daily_pnl.sum()

    # --------------------------------------
    # Maximum drawdown
    # --------------------------------------

    cumulative_pnl = daily_pnl.cumsum()

    running_peak = cumulative_pnl.cummax()

    # Include initial capital/P&L baseline of zero
    running_peak = running_peak.clip(lower=0)

    drawdown = cumulative_pnl - running_peak

    max_drawdown = drawdown.min()

    # --------------------------------------
    # Trade-level P&L and win rate
    # --------------------------------------

    trade_pnls = []

    current_trade_pnl = 0.0
    trade_open = False

    for _, row in results.iterrows():

        action = str(row.get("action", ""))

        pnl = float(row.get("daily_pnl", 0.0) or 0.0)

        # Start accumulating when a position is entered
        if "Entry" in action:

            # If a previous trade was left open,
            # finalize it before starting another.
            if trade_open:
                trade_pnls.append(
                    current_trade_pnl
                )

            current_trade_pnl = pnl
            trade_open = True

        elif trade_open:

            current_trade_pnl += pnl

        # Finalize when a position exits
        if "Exit" in action and trade_open:

            trade_pnls.append(
                current_trade_pnl
            )

            current_trade_pnl = 0.0
            trade_open = False

    # Include any trade still open at end of data
    if trade_open:
        trade_pnls.append(
            current_trade_pnl
        )

    number_of_trades = len(trade_pnls)

    if number_of_trades > 0:

        winning_trades = sum(
            pnl > 0 for pnl in trade_pnls
        )

        win_rate = (
            winning_trades / number_of_trades
        ) * 100

        average_pnl = np.mean(trade_pnls)

    else:

        win_rate = 0.0
        average_pnl = 0.0

    return {
        "trades": number_of_trades,
        "total_pnl": round(float(total_pnl), 2),
        "win_rate": round(float(win_rate), 2),
        "max_drawdown": round(float(max_drawdown), 2),
        "avg_pnl_per_trade": round(
            float(average_pnl), 2
        ),
    }


# ==========================================
# RUN BACKTEST FOR EACH THRESHOLD
# ==========================================

comparison_results = []

print("\nRunning threshold comparison...\n")

for threshold in ENTRY_THRESHOLDS:

    print(
        f"Testing entry threshold: {threshold}"
    )

    backtest_results = run_calendar_spread_backtest(
        data=selected_data,
        entry_zscore=threshold,
        exit_zscore=EXIT_ZSCORE,
        transaction_cost_per_leg=TRANSACTION_COST_PER_LEG,
        slippage_per_leg=SLIPPAGE_PER_LEG,
        lots=LOTS,
    )

    metrics = calculate_metrics(
        backtest_results
    )

    metrics["entry_threshold"] = threshold

    comparison_results.append(metrics)


# ==========================================
# DISPLAY RESULTS
# ==========================================

comparison_df = pd.DataFrame(
    comparison_results
)

comparison_df = comparison_df[
    [
        "entry_threshold",
        "trades",
        "total_pnl",
        "win_rate",
        "max_drawdown",
        "avg_pnl_per_trade",
    ]
]

print("\n" + "=" * 80)
print("AURUMSPREAD - ENTRY THRESHOLD COMPARISON")
print("=" * 80)

print(
    comparison_df.to_string(
        index=False
    )
)


# ==========================================
# SAVE RESULTS
# ==========================================

output_path = (
    "data/processed/threshold_comparison.csv"
)

comparison_df.to_csv(
    output_path,
    index=False
)

print("\nComparison saved to:")
print(output_path)


# ==========================================
# BEST THRESHOLD BY TOTAL P&L
# ==========================================

best_result = comparison_df.sort_values(
    "total_pnl",
    ascending=False
).iloc[0]

print("\nBest threshold by historical total P&L:")
print(
    f"Entry threshold: "
    f"{best_result['entry_threshold']}"
)

print(
    f"Total P&L: "
    f"{best_result['total_pnl']}"
)

print(
    f"Trades: "
    f"{best_result['trades']}"
)

print(
    f"Win rate: "
    f"{best_result['win_rate']}%"
)

print("\nDone!")
