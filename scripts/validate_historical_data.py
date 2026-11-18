

from pathlib import Path
import pandas as pd

DATA_PATH = Path(
    "data/processed/historical_gold_futures.csv"
)


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    df["trade_date"] = pd.to_datetime(
        df["trade_date"], errors="coerce"
    )
    df["expiry_date"] = pd.to_datetime(
        df["expiry_date"], errors="coerce"
    )

    print("TOTAL ROWS:", len(df))
    print("\nUNIQUE TRADING DATES:")
    print(
        df["trade_date"]
        .dt.strftime("%Y-%m-%d")
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nDUPLICATES BY SYMBOL, DATE, AND EXPIRY:")
    duplicate_mask = df.duplicated(
        ["symbol", "trade_date", "expiry_date"],
        keep=False,
    )

    duplicates = df[duplicate_mask].sort_values(
        ["symbol", "trade_date", "expiry_date"]
    )

    print("Rows involved in duplicate groups:", len(duplicates))
    print(duplicates.head(20).to_string(index=False))

    print("\nRAW CSV FILE COUNT:")
    print(len(list(Path("data/raw").glob("*.csv"))))


if __name__ == "__main__":
    main()
