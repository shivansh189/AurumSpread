

from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw")
OUTPUT_DIR = Path("data/processed")
OUTPUT_FILE = OUTPUT_DIR / "BhavCopyDateWise_23102026_gold.csv"

TARGET_SYMBOLS = {
    "GOLDM",
    "GOLDTEN",
    "GOLDGUINEA",
    "GOLDPETAL",
}


def main():
    files = sorted(RAW_DIR.glob("*.csv"))

    if not files:
        raise SystemExit("No CSV files found in data/raw.")

    source = next(
        (
            path for path in files
            if path.name == "BhavCopyDateWise_23102026.csv"
        ),
        files[0],
    )

    df = pd.read_csv(source, low_memory=False)
    df.columns = df.columns.astype(str).str.strip()

    required = [
        "Symbol",
        "Instrument Name",
        "Option Type",
        "Strike Price",
    ]
    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Standardize fields before filtering.
    for column in ["Symbol", "Instrument Name", "Option Type"]:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    df["Strike Price"] = pd.to_numeric(
        df["Strike Price"], errors="coerce"
    )

    # Keep futures only; exclude options.
    futures = df[
        df["Symbol"].isin(TARGET_SYMBOLS)
        & df["Instrument Name"].eq("FUTCOM")
        & df["Option Type"].eq("-")
        & df["Strike Price"].eq(0)
    ].copy()

    if futures.empty:
        raise SystemExit(
            "No matching futures rows found. Check the source columns."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    futures.to_csv(OUTPUT_FILE, index=False)

    print(f"Source: {source.name}")
    print(f"Futures rows saved: {len(futures)}")
    print("\nRows by symbol:")
    print(futures["Symbol"].value_counts().sort_index().to_string())

    print("\nRows by symbol and expiry:")
    print(
        futures.groupby(["Symbol", "Expiry Date"], dropna=False)
        .size()
        .to_string()
    )

    print(f"\nSaved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
