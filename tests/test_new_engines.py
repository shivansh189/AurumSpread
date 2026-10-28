"""Unit tests for newly added AurumSpread analytical engines."""

from pathlib import Path
import pandas as pd
import pytest

from src.normalize import normalize_gold_prices, CONTRACT_SPECS
from src.carry_engine import calculate_term_structure, decompose_carry_and_mispricing, calculate_retail_micro_premium
from src.liquidity_engine import is_tender_period, calculate_liquidity_depth, estimate_fill_slippage
from src.hedge_optimizer import calculate_optimal_hedge
from src.data_doctor import audit_dataset_health
from src.quiet_alerts import scan_quiet_alerts


def test_normalize_formulas():
    df = pd.DataFrame({
        "symbol": ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"],
        "close": [75000.0, 75000.0, 60000.0, 7500.0],
    })
    res = normalize_gold_prices(df)
    # GOLDM: 75000 / 10 * (999 / 995)
    expected_goldm = 75000.0 / 10.0 * (999.0 / 995.0)
    assert abs(res.loc[0, "normalized_price_per_gram"] - expected_goldm) < 1e-4

    # GOLDTEN: 75000 / 10 = 7500
    assert abs(res.loc[1, "normalized_price_per_gram"] - 7500.0) < 1e-4

    # GOLDGUINEA: 60000 / 8 = 7500
    assert abs(res.loc[2, "normalized_price_per_gram"] - 7500.0) < 1e-4

    # GOLDPETAL: 7500 / 1 = 7500
    assert abs(res.loc[3, "normalized_price_per_gram"] - 7500.0) < 1e-4


def test_tender_period_detection():
    # 3 days before expiry is tender period
    assert is_tender_period("2026-10-27", "2026-10-30", tender_days=5) is True
    # 15 days before expiry is NOT tender period
    assert is_tender_period("2026-10-15", "2026-10-30", tender_days=5) is False
    # Negative days (after expiry)
    assert is_tender_period("2026-11-02", "2026-10-30", tender_days=5) is False


def test_liquidity_haircut():
    # High volume gets base slippage
    slip, fillable = estimate_fill_slippage(base_slippage_inr=2.0, volume_lots=100.0, oi_lots=500.0)
    assert slip == 2.0
    assert fillable is True

    # Low volume gets penalized haircut
    slip_penalized, fillable2 = estimate_fill_slippage(base_slippage_inr=2.0, volume_lots=10.0, oi_lots=50.0)
    assert slip_penalized > 2.0
    assert fillable2 is True

    # Zero volume is unfillable
    _, fillable_zero = estimate_fill_slippage(base_slippage_inr=2.0, volume_lots=1.0, oi_lots=2.0)
    assert fillable_zero is False


def test_hedge_optimizer():
    # GOLDM (100g) vs GOLDTEN (10g)
    hedge = calculate_optimal_hedge("GOLDM", "GOLDTEN", lots_a=1)
    assert hedge["lots_b"] == 10
    assert hedge["residual_mismatch_grams"] == 0
    assert hedge["hedge_efficiency_pct"] == 100.0

    # GOLDGUINEA (8g) vs GOLDTEN (10g)
    hedge2 = calculate_optimal_hedge("GOLDGUINEA", "GOLDTEN", lots_a=1)
    # 1 lot of 8g -> 1 lot of 10g (residual mismatch = 2g)
    assert hedge2["residual_mismatch_grams"] == 2
    assert "5 GOLDGUINEA : 4 GOLDTEN" in hedge2["exact_zero_delta_ratio"]


def test_data_doctor_audit():
    df = pd.DataFrame({
        "symbol": ["GOLDM", "GOLDTEN"],
        "trade_date": ["2026-10-01", "2026-10-01"],
        "expiry_date": ["2026-11-05", "2026-11-30"],
        "close": [75000, 75200],
        "normalized_price_per_gram": [7530.15, 7520.0],
        "volume_lots": [50, 100],
    })
    report = audit_dataset_health(df)
    assert report["health_score"] >= 90
    assert report["status"] == "EXCELLENT"


def test_carry_and_micro_premium():
    data_path = Path("data/processed/historical_gold_futures.csv")
    if not data_path.exists():
        pytest.skip("Historical dataset not found")

    df = pd.read_csv(data_path)
    curve = calculate_term_structure(df, symbol="GOLDM")
    assert not curve.empty
    assert "annualized_carry_pct" in curve.columns

    prem = calculate_retail_micro_premium(df)
    assert not prem.empty
    assert "premium_inr_per_g" in prem.columns
