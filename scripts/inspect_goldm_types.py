
from pathlib import Path
import pandas as pd

raw_dir = Path("data/raw")
files = sorted(raw_dir.glob("*.csv"))

if not files:
    raise SystemExit("No CSV files found in data/raw.")

# Use the same source file we processed earlier.
path = next(
    (p for p in files if p.name == "BhavCopyDateWise_23102026.csv"),
    files[0],
)

df = pd.read_csv(path, low_memory=False)
df.columns = df.columns.astype(str).str.strip()

print("SOURCE FILE:", path.name)

for col in ["Instrument Name", "Symbol", "Option Type"]:
    if col in df.columns:
        df[col] = df[col].astype("string").str.strip().str.upper()
        print(f"\n--- VALUES IN {col} ---")
        print(df[col].value_counts(dropna=False).head(20).to_string())

if "Strike Price" in df.columns:
    df["Strike Price"] = pd.to_numeric(
        df["Strike Price"], errors="coerce"
    )
    print("\n--- STRIKE PRICE COUNTS FOR GOLDM ---")
    goldm = df[df["Symbol"].eq("GOLDM")]
    print(
        goldm["Strike Price"]
        .value_counts(dropna=False)
        .head(15)
        .to_string()
    )

    print("\n--- GOLDM INSTRUMENT / OPTION TYPE COMBINATIONS ---")
    print(
        goldm.groupby(
            ["Instrument Name", "Option Type", "Strike Price"],
            dropna=False,
        ).size().sort_values(ascending=False).head(20).to_string()
    )
