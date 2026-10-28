from pathlib import Path

import pandas as pd

from src.spread_engine import calculate_calendar_spreads
from src.spread_intelligence import calculate_spread_intelligence


DATA_PATH = Path(
    "data/processed/historical_gold_futures.csv"
)

df = pd.read_csv(DATA_PATH)

# Select the instrument to test.
symbol = "GOLDGUINEA"

# Calculate calendar spreads.
spreads = calculate_calendar_spreads(
    df=df,
    symbol=symbol,
)

# Select one expiry pair.
pair = spreads[
    (spreads["near_expiry"] == pd.Timestamp("2026-07-31"))
    & (spreads["far_expiry"] == pd.Timestamp("2026-08-31"))
].copy()

# Calculate spread intelligence.
intelligence = calculate_spread_intelligence(pair)

print("\nSPREAD INTELLIGENCE TEST")
print("-----------------------")

print("Instrument:", symbol)
print("Expiry pair: 31 Jul 2026 - 31 Aug 2026")
print("Observations:", len(intelligence))

print("\nLatest 10 observations:")

print(
    intelligence[
        [
            "trade_date",
            "calendar_spread",
            "spread_change",
            "spread_direction",
            "spread_percentile",
            "spread_zscore",
        ]
    ].tail(10).to_string(index=False)
)

print("\nMissing values:")

print(
    intelligence[
        [
            "spread_change",
            "spread_percentile",
            "spread_zscore",
        ]
    ].isna().sum()
)