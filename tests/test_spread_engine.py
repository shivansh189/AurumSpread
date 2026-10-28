from pathlib import Path

import pandas as pd

from src.spread_engine import calculate_calendar_spreads


# Load processed MCX historical data
DATA_PATH = Path(
    "data/processed/historical_gold_futures.csv"
)

df = pd.read_csv(DATA_PATH)

# Select one gold instrument
symbol = "GOLDGUINEA"

print("\nDATE FORMAT CHECK")
print(df["trade_date"].head().to_list())
print(df["expiry_date"].head().to_list())
print(df["trade_date"].dtype)
print(df["expiry_date"].dtype)

# Calculate calendar spreads
spreads = calculate_calendar_spreads(
    df=df,
    symbol=symbol,
)

# Display results
print("\nCALENDAR SPREAD ENGINE TEST")
print("--------------------------")

print("Selected instrument:", symbol)
print("Total spread observations:", len(spreads))

if not spreads.empty:

    print("\nFirst 10 spread observations:")

    print(
        spreads.head(10).to_string(
            index=False
        )
    )

    print("\nUnique trading dates:")
    print(
        spreads["trade_date"].nunique()
    )

    print("\nUnique expiry pairs:")
    print(
        spreads[
            ["near_expiry", "far_expiry"]
        ].drop_duplicates().shape[0]
    )

    print("\nMissing spread values:")
    print(
        spreads["calendar_spread"].isna().sum()
    )

    print("\nDuplicate spread observations:")
    print(
        spreads.duplicated(
            [
                "trade_date",
                "symbol",
                "near_expiry",
                "far_expiry",
            ]
        ).sum()
    )

else:
    print(
        "No calendar spreads were generated."
    )

pair = spreads[
    (spreads["near_expiry"] == pd.Timestamp("2026-07-31"))
    & (spreads["far_expiry"] == pd.Timestamp("2026-08-31"))
]

print("\nJULY-AUGUST EXPIRY PAIR")
print(pair.tail(5).to_string(index=False))    