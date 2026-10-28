
from pathlib import Path
import pandas as pd

from src.normalize import normalize_gold_prices
from src.ingest import adapt_mcx_bhavcopy

path = Path(
    "data/processed/BhavCopyDateWise_23102026_gold.csv"
)

raw = pd.read_csv(path)
standardized = adapt_mcx_bhavcopy(raw)
normalized = normalize_gold_prices(standardized)

print(
    normalized[
        [
            "symbol",
            "expiry_date",
            "close",
            "normalized_price_per_gram",
        ]
    ].sort_values(["symbol", "expiry_date"]).to_string(index=False)
)

print("\nMissing normalized prices:",
      normalized["normalized_price_per_gram"].isna().sum())
