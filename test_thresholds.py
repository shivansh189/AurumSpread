
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent

path = ROOT / "data" / "processed" / "spread_intelligence.csv"

df = pd.read_csv(path)

# Use only the expiry pair selected for our current backtest
df["near_expiry"] = pd.to_datetime(df["near_expiry"])
df["far_expiry"] = pd.to_datetime(df["far_expiry"])

df = df[
    (df["near_expiry"] == "2026-10-30")
    & (df["far_expiry"] == "2026-11-30")
].copy()

df = df.sort_values("trade_date")

print("\n========== THRESHOLD ANALYSIS ==========")
print("Selected pair: Oct 30 -> Nov 30, 2026")
print("Trading days:", len(df))

print("\nEntry threshold | Long signals | Short signals")

for threshold in [0.5, 1.0, 1.25, 1.5, 1.75, 2.0]:
    long_signals = (
        df["spread_zscore"] <= -threshold
    ).sum()

    short_signals = (
        df["spread_zscore"] >= threshold
    ).sum()

    print(
        f"{threshold:14.2f} | "
        f"{long_signals:12} | "
        f"{short_signals:13}"
    )

print("\nZ-score range:")
print("Minimum:", df["spread_zscore"].min())
print("Maximum:", df["spread_zscore"].max())
