
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "trade_date",
    "symbol",
    "expiry_date",
    "close",
}


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load a CSV without modifying the source file."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    return pd.read_csv(path)


def clean_contract_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean standardized contract data."""
    df = df.copy()

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    df["symbol"] = (
        df["symbol"].astype("string").str.strip().str.upper()
    )

    # Sample dates use ISO format: YYYY-MM-DD.
    df["trade_date"] = pd.to_datetime(
        df["trade_date"], errors="coerce", format="mixed"
    )
    df["expiry_date"] = pd.to_datetime(
        df["expiry_date"], errors="coerce", format="mixed"
    )

    df["close"] = pd.to_numeric(df["close"], errors="coerce")

    df["validation_error"] = ""

    df.loc[
        df["trade_date"].isna(), "validation_error"
    ] += "invalid_trade_date;"

    df.loc[
        df["expiry_date"].isna(), "validation_error"
    ] += "invalid_expiry_date;"

    df.loc[
        df["symbol"].isna() | df["symbol"].eq(""),
        "validation_error",
    ] += "missing_symbol;"

    df.loc[
        df["close"].isna() | df["close"].le(0),
        "validation_error",
    ] += "invalid_close;"

    # Print diagnostic information only when debugging is needed.
    # Keep the function's return value as a DataFrame.
    print("\n--- DEBUG: Validation results ---")
    print(
        df[
            [
                "trade_date",
                "symbol",
                "expiry_date",
                "close",
                "validation_error",
            ]
        ].to_string(index=False)
    )

    df = df.drop_duplicates().reset_index(drop=True)

    return df


def split_valid_invalid(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate valid records from records needing review."""
    valid_mask = df["validation_error"].eq("")

    valid = df.loc[valid_mask].copy()
    invalid = df.loc[~valid_mask].copy()

    return valid, invalid


def adapt_mcx_bhavcopy(df: pd.DataFrame) -> pd.DataFrame:
    """Convert actual MCX Bhavcopy columns to AurumSpread's schema."""

    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()

    column_map = {
        "Date": "trade_date",
        "Symbol": "symbol",
        "Expiry Date": "expiry_date",
        "Close": "close",
        "Volume(Lots)": "volume_lots",
        "Open Interest(Lots)": "open_interest_lots",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Previous Close": "previous_close",
        "Instrument Name": "instrument_name",
    }

    missing = {"Date", "Symbol", "Expiry Date", "Close"} - set(df.columns)
    if missing:
        raise ValueError(
            f"Expected MCX columns not found: {sorted(missing)}. "
            f"Available columns: {df.columns.tolist()}"
        )

    df = df.rename(columns=column_map)

    # Examples: 23 Oct 2026 and 29JAN2027
    df["trade_date"] = pd.to_datetime(
        df["trade_date"].astype("string").str.strip(),
        format="%d %b %Y",
        errors="coerce",
    )

    expiry_text = (
        df["expiry_date"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # Try the format shown in the screenshot first.
    expiry = pd.to_datetime(
        expiry_text, format="%d%b%Y", errors="coerce"
    )

    # Fallback for expiry dates written with spaces.
    fallback = expiry.isna()
    expiry.loc[fallback] = pd.to_datetime(
        expiry_text.loc[fallback],
        format="%d %b %Y",
        errors="coerce",
    )

    df["expiry_date"] = expiry

    for column in [
        "close",
        "open",
        "high",
        "low",
        "previous_close",
        "volume_lots",
        "open_interest_lots",
    ]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df
