import pandas as pd


def calculate_calendar_spreads(
    df: pd.DataFrame,
    symbol: str,
) -> pd.DataFrame:
    """
    Calculate calendar spreads for one gold instrument.

    Calendar spread = far-expiry normalized price
                     - near-expiry normalized price

    Raw MCX close prices are retained separately for P&L.
    """

    required_columns = [
        "trade_date",
        "symbol",
        "expiry_date",
        "close",
        "normalized_price_per_gram",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    data = df[df["symbol"] == symbol].copy()

    if data.empty:
        raise ValueError(f"No data found for symbol: {symbol}")

    data["trade_date"] = pd.to_datetime(
        data["trade_date"], errors="coerce", format="mixed"
    )

    data["expiry_date"] = pd.to_datetime(
        data["expiry_date"], errors="coerce", format="mixed"
    )

    for column in ["close", "normalized_price_per_gram"]:
        data[column] = pd.to_numeric(
            data[column], errors="coerce"
        )

    data = data.dropna(
        subset=[
            "trade_date",
            "expiry_date",
            "close",
            "normalized_price_per_gram",
        ]
    )

    data = data.drop_duplicates(
        subset=["trade_date", "symbol", "expiry_date"],
        keep="last",
    )

    data = data.sort_values(["trade_date", "expiry_date"])

    results = []

    for trade_date, daily_data in data.groupby("trade_date"):
        contracts = daily_data.sort_values("expiry_date").to_dict(
            "records"
        )

        for i in range(len(contracts)):
            for j in range(i + 1, len(contracts)):
                near = contracts[i]
                far = contracts[j]

                near_price = near["normalized_price_per_gram"]
                far_price = far["normalized_price_per_gram"]

                spread = far_price - near_price

                results.append({
                    "trade_date": trade_date,
                    "symbol": symbol,
                    "near_expiry": near["expiry_date"],
                    "far_expiry": far["expiry_date"],

                    # Normalized prices for spread signals.
                    "near_price": near_price,
                    "far_price": far_price,

                    # Raw MCX close prices for contract P&L.
                    "near_raw_price": near["close"],
                    "far_raw_price": far["close"],

                    "calendar_spread": spread,
                    "spread_percent": (
                        spread / near_price * 100
                        if near_price != 0
                        else None
                    ),
                })

    spread_df = pd.DataFrame(results)

    if spread_df.empty:
        return spread_df

    return spread_df.sort_values(
        ["trade_date", "near_expiry", "far_expiry"]
    ).reset_index(drop=True)
