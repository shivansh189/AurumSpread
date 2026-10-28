
from pathlib import Path
import pandas as pd

from src.ingest import adapt_mcx_bhavcopy
from src.normalize import normalize_gold_prices

path = Path(
    "data/processed/BhavCopyDateWise_23102026_gold.csv"
)

raw = pd.read_csv(path)
df = adapt_mcx_bhavcopy(raw)
df = normalize_gold_prices(df)

# Compare the contracts available on the same trading date.
pivot = df.pivot_table(
    index="trade_date",
    columns="symbol",
    values="normalized_price_per_gram",
    aggfunc="first",
)

print("NORMALIZED PRICE COMPARISON")
print(pivot.round(2).to_string())

# Pairwise differences for contracts on the same date.
pairs = [
    ("GOLDM", "GOLDTEN"),
    ("GOLDM", "GOLDGUINEA"),
    ("GOLDM", "GOLDPETAL"),
    ("GOLDTEN", "GOLDGUINEA"),
    ("GOLDTEN", "GOLDPETAL"),
    ("GOLDGUINEA", "GOLDPETAL"),
]

print("\nPAIRWISE PRICE DIFFERENCES (₹/gram)")
for first, second in pairs:
    if first in pivot.columns and second in pivot.columns:
        difference = pivot[first] - pivot[second]
        print(f"{first} - {second}:")
        print(difference.round(2).to_string())

print(
    "\nNote: These are raw normalized price differences, "
    "not confirmed trading opportunities."
)
