import pandas as pd
from src.backtest_engine import run_calendar_spread_backtest

SYMBOL = "GOLDGUINEA"
ENTRY_THRESHOLDS = [1.0, 1.25, 1.5, 1.75, 2.0]
EXIT_ZSCORE = 0.0
LOTS = 1

# Illustrative per-leg, per-lot assumptions. Verify before interpreting results.
TRANSACTION_COST_PER_LEG = 10.0
SLIPPAGE_PER_LEG = 5.0
EXPIRY_EXIT_DAYS = 2

print("\\nLoading spread intelligence data...")
data = pd.read_csv("data/processed/spread_intelligence.csv")
for col in ["trade_date", "near_expiry", "far_expiry"]:
    data[col] = pd.to_datetime(data[col], errors="coerce")

data = data[data["symbol"] == SYMBOL].copy()
if data.empty:
    raise ValueError(f"No data found for symbol {SYMBOL}")

expiry_pairs = (
    data[["near_expiry", "far_expiry"]]
    .drop_duplicates()
    .sort_values(["near_expiry", "far_expiry"])
    .reset_index(drop=True)
)
print(f"Symbol: {SYMBOL}")
print(f"Expiry pairs found: {len(expiry_pairs)}")


def calculate_metrics(results):
    if results.empty:
        return {
            "trades": 0, "total_pnl": 0.0, "win_rate": 0.0,
            "max_drawdown": 0.0, "avg_pnl_per_trade": 0.0,
            "end_of_data_exits": 0,
        }

    daily = (
        results.groupby("trade_date", as_index=False)["daily_pnl"]
        .sum().sort_values("trade_date")
    )
    daily_pnl = daily["daily_pnl"].fillna(0.0)
    total_pnl = float(daily_pnl.sum())
    cumulative = daily_pnl.cumsum()
    running_peak = cumulative.cummax().clip(lower=0.0)
    max_drawdown = float((cumulative - running_peak).min())

    completed = results[results["trade_completed"].fillna(False)]
    trade_pnls = pd.to_numeric(
        completed["completed_trade_pnl"], errors="coerce"
    ).dropna()
    n_trades = int(len(trade_pnls))
    win_rate = float((trade_pnls > 0).mean() * 100.0) if n_trades else 0.0
    avg_pnl = float(trade_pnls.mean()) if n_trades else 0.0

    return {
        "trades": n_trades,
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 2),
        "max_drawdown": round(max_drawdown, 2),
        "avg_pnl_per_trade": round(avg_pnl, 2),
        "end_of_data_exits": int(results["action"].eq("End Of Data Exit").sum()),
    }


all_results = []
total_runs = len(expiry_pairs) * len(ENTRY_THRESHOLDS)
run_number = 0
print(f"\\nStarting {total_runs} backtests...")

for _, pair in expiry_pairs.iterrows():
    near_expiry = pair["near_expiry"]
    far_expiry = pair["far_expiry"]
    pair_data = data[
        (data["near_expiry"] == near_expiry)
        & (data["far_expiry"] == far_expiry)
    ].copy().sort_values("trade_date").reset_index(drop=True)

    if len(pair_data) < 15:
        continue

    for threshold in ENTRY_THRESHOLDS:
        run_number += 1
        print(
            f"Run {run_number}/{total_runs}: {near_expiry.date()} -> "
            f"{far_expiry.date()}, threshold={threshold}"
        )
        results = run_calendar_spread_backtest(
            data=pair_data,
            entry_zscore=threshold,
            exit_zscore=EXIT_ZSCORE,
            transaction_cost_per_leg=TRANSACTION_COST_PER_LEG,
            slippage_per_leg=SLIPPAGE_PER_LEG,
            lots=LOTS,
            expiry_exit_days=EXPIRY_EXIT_DAYS,
        )
        metrics = calculate_metrics(results)
        metrics.update({
            "symbol": SYMBOL,
            "near_expiry": near_expiry.date(),
            "far_expiry": far_expiry.date(),
            "entry_threshold": threshold,
            "observations": len(pair_data),
            "pnl_basis": results["pnl_basis"].iloc[0],
        })
        all_results.append(metrics)

comparison_df = pd.DataFrame(all_results)
if comparison_df.empty:
    raise ValueError("No backtests completed. Check data and expiry pairs.")

columns = [
    "symbol", "near_expiry", "far_expiry", "entry_threshold",
    "observations", "trades", "total_pnl", "win_rate",
    "max_drawdown", "avg_pnl_per_trade", "end_of_data_exits", "pnl_basis",
]
comparison_df = comparison_df[columns]

print("\\n" + "=" * 110)
print("AURUMSPREAD - EXPIRY PAIR COMPARISON")
print("=" * 110)
print(comparison_df.to_string(index=False))

comparison_path = "data/processed/expiry_pair_comparison.csv"
comparison_df.to_csv(comparison_path, index=False)
print(f"\\nResults saved to: {comparison_path}")

# These summarize independent pair tests; they are NOT portfolio performance.
summary = (
    comparison_df.groupby("entry_threshold")
    .agg(
        expiry_pair_tests=("near_expiry", "count"),
        total_completed_trades=("trades", "sum"),
        sum_of_pair_test_pnl=("total_pnl", "sum"),
        mean_pair_test_pnl=("total_pnl", "mean"),
        mean_pair_win_rate=("win_rate", "mean"),
        mean_pair_max_drawdown=("max_drawdown", "mean"),
        end_of_data_exits=("end_of_data_exits", "sum"),
    )
    .reset_index()
)

print("\\n" + "=" * 110)
print("SUMMARY BY ENTRY THRESHOLD")
print("NOTE: Aggregates independent expiry-pair backtests; not portfolio performance.")
print("=" * 110)
print(summary.to_string(index=False))

summary_path = "data/processed/expiry_pair_threshold_summary.csv"
summary.to_csv(summary_path, index=False)
print(f"\\nSummary saved to: {summary_path}")
print("\\nAll backtests completed.")