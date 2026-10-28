import pandas as pd

from src.spread_intelligence import calculate_spread_intelligence


def create_test_data(spreads):
    dates = pd.date_range(
        start="2026-01-01",
        periods=len(spreads),
        freq="D",
    )

    return pd.DataFrame({
        "trade_date": dates,
        "near_expiry": "2026-02-27",
        "far_expiry": "2026-03-27",
        "calendar_spread": spreads,
        "spread_percent": [
            value / 100 for value in spreads
        ],
    })


def test_no_future_leakage():
    # Original dataset: 12 observations
    spreads = [
        100, 102, 101, 104, 103, 105,
        106, 104, 107, 108, 109, 110
    ]

    original_data = create_test_data(spreads)

    original_result = calculate_spread_intelligence(
        original_data
    )

    # Change only the final observation dramatically.
    modified_spreads = spreads.copy()
    modified_spreads[-1] = 10000

    modified_data = create_test_data(
        modified_spreads
    )

    modified_result = calculate_spread_intelligence(
        modified_data
    )

    # Earlier observations must remain unchanged.
    columns_to_check = [
        "spread_percentile",
        "spread_zscore",
    ]

    pd.testing.assert_frame_equal(
        original_result.loc[
            :-1, columns_to_check
        ],
        modified_result.loc[
            :-1, columns_to_check
        ],
    )

    print("PASS: No future data leakage detected.")


def test_zscore_warmup():
    spreads = list(range(100, 115))

    data = create_test_data(spreads)

    result = calculate_spread_intelligence(data)

    # First 10 rows have fewer than 10 prior observations.
    assert result.loc[:9, "spread_zscore"].isna().all()

    # Row 11 (index 10) has 10 prior observations.
    assert pd.notna(
        result.loc[10, "spread_zscore"]
    )

    print("PASS: Z-score warmup works correctly.")


if __name__ == "__main__":
    test_no_future_leakage()
    test_zscore_warmup()

    print("All tests passed.")