import pandas as pd

from src.backtest_engine import run_calendar_spread_backtest


def test_multiple_trades():

    test_data = pd.DataFrame({
        "trade_date": [
            "2026-09-01",
            "2026-09-02",
            "2026-09-03",
            "2026-09-04",
            "2026-09-05",
            "2026-09-06",
        ],
        "near_expiry": ["2026-09-30"] * 6,
        "far_expiry": ["2026-10-30"] * 6,
        "near_price": [100, 101, 102, 103, 104, 105],
        "far_price": [110, 111, 112, 113, 114, 115],
        "calendar_spread": [10, 8, 7, 9, 12, 14],
        "spread_zscore": [-2.5, -1.0, 0.0, 2.5, 1.0, 0.0],
    })

    results = run_calendar_spread_backtest(
        test_data,
        entry_zscore=2.0,
        exit_zscore=0.0,
    )

    print("\nMULTIPLE TRADES TEST")
    print(results[[
        "trade_date",
        "calendar_spread",
        "spread_zscore",
        "position",
        "action",
        "trade_id",
        "daily_pnl",
        "cumulative_pnl",
    ]].to_string(index=False))

    assert results.iloc[0]["action"] == "Enter Long Spread"
    assert results.iloc[2]["action"] == "Exit Long Spread"

    assert results.iloc[3]["action"] == "Enter Short Spread"
    assert results.iloc[5]["action"] == "Exit Short Spread"

    assert results.iloc[0]["trade_id"] != results.iloc[3]["trade_id"]

    print("\nMultiple trades test passed!")


if __name__ == "__main__":
    test_multiple_trades()