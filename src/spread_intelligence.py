import pandas as pd


def calculate_spread_intelligence(
    spread_data: pd.DataFrame,
) -> pd.DataFrame:

    required_columns = [
        "trade_date",
        "near_expiry",
        "far_expiry",
        "calendar_spread",
        "spread_percent",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in spread_data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    data = spread_data.copy()

# Preserve actual MCX contract prices
    near_candidates = [
        "near_raw_price",
        "near_price",
        "near_close",
    ]

    far_candidates = [
        "far_raw_price",
        "far_price",
        "far_close",
    ]

    near_col = next(
        (c for c in near_candidates if c in data.columns),
        None,
    )

    far_col = next(
        (c for c in far_candidates if c in data.columns),
        None,
    )

    if near_col:
        data["near_raw_price"] = pd.to_numeric(
            data[near_col], errors="coerce"
        )

    if far_col:
        data["far_raw_price"] = pd.to_numeric(
            data[far_col], errors="coerce"
        )

    # Parse and validate data
    for col in [
        "trade_date",
        "near_expiry",
        "far_expiry",
    ]:
        data[col] = pd.to_datetime(
            data[col], errors="coerce"
        )

    for col in [
        "calendar_spread",
        "spread_percent",
    ]:
        data[col] = pd.to_numeric(
            data[col], errors="coerce"
        )

    data = data.dropna(
        subset=[
            "trade_date",
            "near_expiry",
            "far_expiry",
            "calendar_spread",
        ]
    )

    # Group statistics independently by symbol and expiry pair
    group_columns = []

    if "symbol" in data.columns:
        group_columns.append("symbol")

    group_columns.extend([
        "near_expiry",
        "far_expiry",
    ])

    data = data.sort_values(
        group_columns + ["trade_date"]
    ).reset_index(drop=True)

    # Spread changes and direction
    data["spread_change"] = (
        data.groupby(group_columns)["calendar_spread"]
        .diff()
    )

    data["spread_direction"] = data["spread_change"].apply(
        lambda x: (
            "Widening" if x > 0
            else "Narrowing" if x < 0
            else "Unchanged" if pd.notna(x)
            else None
        )
    )

    # Historical percentile: only prior observations
    def prior_percentile(series):
        values = series.to_numpy()
        result = []

        for i, value in enumerate(values):
            history = values[:i]

            if len(history) == 0:
                result.append(float("nan"))
            else:
                percentile = (
                    (history < value).sum()
                    + 0.5 * (history == value).sum()
                ) / len(history) * 100

                result.append(percentile)

        return pd.Series(
            result,
            index=series.index,
        )

    data["spread_percentile"] = (
        data.groupby(group_columns)["calendar_spread"]
        .transform(prior_percentile)
    )

    # Historical mean/std/count: use prior observations only
    grouped_spread = data.groupby(
        group_columns
    )["calendar_spread"]

    data["historical_mean"] = (
        grouped_spread
        .transform(lambda s: s.expanding().mean().shift(1))
    )

    data["historical_std"] = (
        grouped_spread
        .transform(lambda s: s.expanding().std().shift(1))
    )

    data["prior_observation_count"] = (
        grouped_spread
        .transform(lambda s: s.expanding().count().shift(1))
    )

    # Z-score
    data["spread_zscore"] = (
        data["calendar_spread"]
        - data["historical_mean"]
    ) / data["historical_std"]

    # Require at least 10 prior observations
    data.loc[
        data["prior_observation_count"] < 10,
        "spread_zscore",
    ] = float("nan")

    return data
