
from pathlib import Path
import pandas as pd

path = Path(
    "data/processed/BhavCopyDateWise_23102026_gold.csv"
)

df = pd.read_csv(path)

df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
df["Volume(Lots)"] = pd.to_numeric(
    df["Volume(Lots)"], errors="coerce"
)
df["Open Interest(Lots)"] = pd.to_numeric(
    df["Open Interest(Lots)"], errors="coerce"
)

print("TOTAL FUTURES ROWS:", len(df))
print("\nPRICE VALIDATION:")
print("Missing close prices:", df["Close"].isna().sum())
print("Zero or negative prices:", (df["Close"] <= 0).sum())

print("\nCONTRACT DETAILS:")
columns = [
    "Date",
    "Symbol",
    "Expiry Date",
    "Close",
    "Volume(Lots)",
    "Open Interest(Lots)",
]

print(
    df[columns]
    .sort_values(["Symbol", "Expiry Date"])
    .to_string(index=False)
)

print("\nDUPLICATE SYMBOL + EXPIRY PAIRS:")
print(
    df.duplicated(["Symbol", "Expiry Date"]).sum()
)
