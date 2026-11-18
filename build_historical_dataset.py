from pathlib import Path
import pandas as pd
from src.normalize import normalize_gold_prices
from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
OUTPUT_FILE = PROCESSED_DIR / "historical_gold_futures.csv"

TARGET_SYMBOLS = {
    "GOLDM",
    "GOLDTEN",
    "GOLDGUINEA",
    "GOLDPETAL",
}


def load_all_csv_files():
    csv_files = sorted(RAW_DIR.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {RAW_DIR}"
        )

    dataframes = []

    
    for file_path in csv_files:
        print(f"Reading: {file_path.name}")

        df = pd.read_csv(file_path, low_memory=False)

        # Show the actual trading date stored in each source file.
        if "Date" in df.columns:
            dates = df["Date"].astype("string").dropna().unique()
            print("  Dates in file:", dates[:5].tolist())

        df["source_file"] = file_path.name
        dataframes.append(df)


    return dataframes



if __name__ == "__main__":
    files = load_all_csv_files()

    print(f"\nTotal files loaded: {len(files)}")

    for df in files:
        print(f"Rows loaded: {len(df)}")

    combined = pd.concat(files, ignore_index=True)

    
    # Standardize column names used for filtering.
    for column in [
        "Symbol",
        "Instrument Name",
        "Option Type",
    ]:
        combined[column] = (
            combined[column]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    combined["Strike Price"] = pd.to_numeric(
        combined["Strike Price"],
        errors="coerce",
    )

    # Keep only our four gold futures contracts.
    gold_futures = combined[
        combined["Symbol"].isin(TARGET_SYMBOLS)
        & combined["Instrument Name"].eq("FUTCOM")
        & combined["Option Type"].eq("-")
        & combined["Strike Price"].eq(0)
    ].copy()

    print(f"\nGold futures rows: {len(gold_futures)}")
    print("\nRows by symbol and trading date:")

    print(
        gold_futures.groupby(
            ["Symbol", "Date"],
            dropna=False,
        ).size().to_string()
    )


    print(f"\nTotal combined rows: {len(combined)}")
    print(f"Columns available: {len(combined.columns)}")


    # Convert dates into a standard format.
    gold_futures["Date"] = pd.to_datetime(
        gold_futures["Date"],
        format="%d %b %Y",
        errors="coerce",
    )

    gold_futures["expiry_date"] = pd.to_datetime(
        gold_futures["Expiry Date"],
        format="%d%b%Y",
        errors="coerce",
    )



    # Keep the original MCX columns needed for processing.
    gold_futures = gold_futures.loc[
        :,
        [
            "Symbol",
            "Date",
            "Expiry Date",
            "Close",
            "Volume(Lots)",
            "Open Interest(Lots)",
        ],
    ].copy()

    # Rename columns once, using a single mapping.
    gold_futures.columns = [
        "symbol",
        "trade_date",
        "expiry_date",
        "close",
        "volume_lots",
        "open_interest_lots",
    ]

    print("\nColumn names after renaming:")
    print(gold_futures.columns.tolist())


    # Confirm column names are unique.
    if not gold_futures.columns.is_unique:
        raise ValueError(
            "Duplicate columns remain: "
            + str(
                gold_futures.columns[
                    gold_futures.columns.duplicated()
                ].tolist()
            )
        )


    # Normalize each contract to ₹ per gram.
    gold_futures = normalize_gold_prices(gold_futures)

    print("\nNormalized prices (sample):")
    print(
        gold_futures[
            [
                "symbol",
                "trade_date",
                "expiry_date",
                "close",
                "normalized_price_per_gram",
            ]
        ].head(10).to_string(index=False)
    )

    # Sort records for easier analysis.
    gold_futures = gold_futures.sort_values(
        ["symbol", "trade_date", "expiry_date"]
    )

    # Create the output folder if it does not exist.
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Save all historical futures records.
    gold_futures.to_csv(OUTPUT_FILE, index=False)

    print(f"\nSaved historical dataset to: {OUTPUT_FILE}")
    print(f"Total saved records: {len(gold_futures)}")
    print(
        "Trading dates:",
        gold_futures["trade_date"].dt.strftime("%Y-%m-%d")
        .drop_duplicates()
        .tolist(),
    )
