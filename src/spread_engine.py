import pandas as pd


def calculate_calendar_spreads(
    df: pd.DataFrame,
    symbol: str,
) -> pd.DataFrame:
    """
    Calculate calendar spreads for one gold instrument.

    Calendar spread = Far-expiry price - Near-expiry price

    Only contracts observed on the same trading date
    are compared.
    """

    required_columns = [
        "trade_date",
        "symbol",
        "expiry_date",
        "normalized_price_per_gram",
    ]

    # Validate required columns
    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # Keep only the selected instrument
    data = df[
        df["symbol"] == symbol
    ].copy()

    if data.empty:
        raise ValueError(
            f"No data found for symbol: {symbol}"
        )

    # Convert dates and prices
    data["trade_date"] = pd.to_datetime(
    data["trade_date"],
    format="%Y-%m-%d",
    errors="coerce"
)

    data["expiry_date"] = pd.to_datetime(
    data["expiry_date"],
    format="%d%b%Y",
    errors="coerce"
)

    data["normalized_price_per_gram"] = pd.to_numeric(
        data["normalized_price_per_gram"],
        errors="coerce",
    )

    # Remove invalid records
    data = data.dropna(
        subset=[
            "trade_date",
            "expiry_date",
            "normalized_price_per_gram",
        ]
    )

    # Remove duplicate contract observations
    data = data.drop_duplicates(
        subset=[
            "trade_date",
            "symbol",
            "expiry_date",
        ],
        keep="last",
    )

    # Sort contracts by expiry
    data = data.sort_values(
        ["trade_date", "expiry_date"]
    )

    results = []

    # Process each trading date independently
    for trade_date, daily_data in data.groupby(
        "trade_date"
    ):

        daily_data = daily_data.sort_values(
            "expiry_date"
        )

        contracts = daily_data[
            [
                "expiry_date",
                "normalized_price_per_gram",
            ]
        ].to_dict("records")

        # Compare every available expiry pair
        for i in range(len(contracts)):

            for j in range(i + 1, len(contracts)):

                near_contract = contracts[i]
                far_contract = contracts[j]

                near_price = near_contract[
                    "normalized_price_per_gram"
                ]

                far_price = far_contract[
                    "normalized_price_per_gram"
                ]

                spread = far_price - near_price

                results.append({
                    "trade_date": trade_date,
                    "symbol": symbol,

                    "near_expiry": near_contract[
                        "expiry_date"
                    ],

                    "far_expiry": far_contract[
                        "expiry_date"
                    ],

                    "near_price": near_price,
                    "far_price": far_price,

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
        [
            "trade_date",
            "near_expiry",
            "far_expiry",
        ]
    ).reset_index(drop=True)