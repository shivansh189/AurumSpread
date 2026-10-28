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

    data["trade_date"] = pd.to_datetime(
        data["trade_date"],
        errors="coerce",
    )

    data["near_expiry"] = pd.to_datetime(
        data["near_expiry"],
        errors="coerce",
    )

    data["far_expiry"] = pd.to_datetime(
        data["far_expiry"],
        errors="coerce",
    )

    data["calendar_spread"] = pd.to_numeric(
        data["calendar_spread"],
        errors="coerce",
    )

    data = data.dropna(
        subset=[
            "trade_date",
            "near_expiry",
            "far_expiry",
            "calendar_spread",
        ]
    )

    data = data.sort_values("trade_date").reset_index(drop=True)

    # Daily change in the calendar spread.
    data["spread_change"] = data["calendar_spread"].diff()

    # Spread widening or narrowing.
    data["spread_direction"] = data["spread_change"].apply(
        lambda change: (
            "Widening"
            if change > 0
            else "Narrowing"
            if change < 0
            else "Unchanged"
            if pd.notna(change)
            else None
        )
    )

    # Historical percentile using prior observations only.
    def calculate_prior_percentile(series):
        result = []

        for i, current_value in enumerate(series):
            history = series.iloc[:i]

            if history.empty:
                result.append(float("nan"))
            else:
                percentile = (
                    (history < current_value).sum()
                    + 0.5 * (history == current_value).sum()
                ) / len(history) * 100

                result.append(percentile)

        return pd.Series(result, index=series.index)

    data["spread_percentile"] = calculate_prior_percentile(
        data["calendar_spread"]
    )

    # Expanding historical mean and standard deviation,
    # shifted by one observation to exclude the current value.

    # Calculate historical mean using only prior observations.
    historical_mean = (
        data["calendar_spread"]
        .expanding()
        .mean()
        .shift(1)
    )

    # Calculate historical standard deviation using only prior observations.
    historical_std = (
        data["calendar_spread"]
        .expanding()
        .std()
        .shift(1)
    )

    # Count how many prior observations are available.
    prior_observation_count = (
        data["calendar_spread"]
        .expanding()
        .count()
        .shift(1)
    )

    # Calculate z-score.
    data["spread_zscore"] = (
        data["calendar_spread"] - historical_mean
    ) / historical_std

    # Require at least 10 prior observations before producing a z-score.
    data.loc[
        prior_observation_count < 10,
        "spread_zscore"
    ] = float("nan")

    return data