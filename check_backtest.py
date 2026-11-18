
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent

path = ROOT / "data" / "processed" / "backtest_results.csv"

df = pd.read_csv(path)

print("\n========== BACKTEST DIAGNOSTICS ==========")

print("\nTotal rows:", len(df))

print("\nZ-score statistics:")
print(df["spread_zscore"].describe())

print("\nMinimum z-score:", df["spread_zscore"].min())
print("Maximum z-score:", df["spread_zscore"].max())

print("\nActions:")
print(df["action"].value_counts())

print("\nEntry actions:")
print(
    df[df["action"].str.contains("Entry", case=False, na=False)]
    [["trade_date", "spread_zscore", "action"]]
)

print("\nExit actions:")
print(
    df[df["action"].str.contains("Exit", case=False, na=False)]
    [["trade_date", "spread_zscore", "action", "daily_pnl"]]
)

print("\nTotal P&L:", df["daily_pnl"].sum())
