import pandas as pd

from src.backtest_engine import run_calendar_spread_backtest


def test_short_spread_entry_and_exit():
    test_data = pd.DataFrame({
        "trade_date": [
            "2026-09-01",
            "2026-09-02",
            "2026-09-03",
            "2026-09-04",
        ],
        "near_expiry": [
            "2026-09-30",
            "2026-09-30",
            "2026-09-30",
            "2026-09-30",
        ],
        "far_expiry": [
            "2026-10-30",
            "2026-10-30",
            "2026-10-30",
            "2026-10-30",
        ],
        "near_price": [100, 101, 102, 103],
        "far_price": [110, 111, 112, 113],
        "calendar_spread": [10, 10, 10, 10],
        "spread_zscore": [2.5, 1.5, 0.5, 0.0],
    })

    results = run_calendar_spread_backtest(
        test_data,
        entry_zscore=2.0,
        exit_zscore=0.0,
    )

    print("\nSHORT SPREAD TEST")
    print(results[[
        "trade_date",
        "spread_zscore",
        "position",
        "action",
        "trade_id",
        "daily_pnl",
    ]])

    assert results.iloc[0]["action"] == "Enter Short Spread"
    assert results.iloc[0]["position"] == -1

    assert results.iloc[-1]["action"] == "Exit Short Spread"
    assert results.iloc[-1]["position"] == 0

    assert results.iloc[0]["trade_id"] == results.iloc[-1]["trade_id"]

    print("\nShort-spread entry and exit test passed!")


if __name__ == "__main__":
    test_short_spread_entry_and_exit()