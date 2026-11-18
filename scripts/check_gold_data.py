
from pathlib import Path

import pandas as pd


path = Path("data/processed/BhavCopyDateWise_23102026_gold.csv")

if not path.exists():
    raise SystemExit(f"File not found: {path}")

df = pd.read_csv(path, parse_dates=["trade_date", "expiry_date"])

print("\n--- ROW COUNTS BY CONTRACT ---")
print(df.groupby("symbol").size().to_string())

print("\n--- ROW COUNTS BY CONTRACT AND EXPIRY ---")
print(
    df.groupby(["symbol", "expiry_date"])
    .size()
    .to_string()
)

print("\n--- DATE RANGE BY CONTRACT ---")
print(
    df.groupby("symbol")["trade_date"]
    .agg(["min", "max", "count"])
    .to_string()
)

print("\n--- SAMPLE RECORDS ---")
columns = [
    "trade_date",
    "symbol",
    "expiry_date",
    "close",
    "volume_lots",
    "open_interest_lots",
]
columns = [c for c in columns if c in df.columns]
print(df[columns].head(15).to_string(index=False))
