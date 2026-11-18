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
from src.parity_engine import calculate_landed_import_parity, generate_historical_parity_series
from src.order_ticket import generate_spread_order_ticket, export_order_ticket_csv
from src.copilot_engine import AurumCopilot


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


def test_landed_import_parity():
    res = calculate_landed_import_parity(
        comex_usd_per_oz=2650.0,
        usdinr_rate=84.0,
        customs_duty_pct=5.0,
        aidc_pct=1.0,
        swc_pct=10.0,
        gst_pct=3.0,
        domestic_mcx_price_per_g=7500.0,
    )
    assert res["landed_price_ex_gst_per_g"] > 0
    assert res["landed_price_inc_gst_per_g"] > res["landed_price_ex_gst_per_g"]
    assert res["basis_inr_per_g"] is not None
    assert "market_verdict" in res


def test_landed_parity_2026_duty_defaults():
    # 2026 duty structure: 10% BCD + 5% AIDC, no SWC, Rs 5/g handling
    res = calculate_landed_import_parity(
        comex_usd_per_oz=4016.69, usdinr_rate=95.15, domestic_mcx_price_per_g=14550.0
    )
    cif = 4016.69 / 31.1034768 * 95.15
    expected_ex_gst = cif * 1.15 + 5.0
    assert abs(res["landed_price_ex_gst_per_g"] - round(expected_ex_gst, 2)) < 0.01
    assert res["total_tariffs_pct"] == 15.0


def test_order_ticket_generation():
    ticket = generate_spread_order_ticket(
        symbol="GOLDM",
        near_expiry="2026-11-05",
        far_expiry="2026-12-04",
        strategy_type="Long Calendar Spread",
        lots=2,
        near_price=75000.0,
        far_price=75500.0,
    )
    assert len(ticket["legs"]) == 2
    assert ticket["legs"][0]["transaction_type"] == "SELL"
    assert ticket["legs"][1]["transaction_type"] == "BUY"
    assert ticket["margin_relief_pct"] == 75.0
    assert len(ticket["zerodha_kite_json"]) == 2

    csv_data = export_order_ticket_csv(ticket)
    assert "Near Month Leg" in csv_data


def test_aurum_copilot():
    data_path = Path("data/processed/historical_gold_futures.csv")
    if not data_path.exists():
        pytest.skip("Historical dataset not found")

    df = pd.read_csv(data_path)
    copilot = AurumCopilot(df)

    res_hedge = copilot.query("How to hedge 500 grams of gold?")
    assert "500" in res_hedge
    assert "GOLDM" in res_hedge

    res_parity = copilot.query("What is the COMEX import parity?")
    assert "COMEX Gold Benchmark" in res_parity

    res_specs = copilot.query("What are the contract specs and purities?")
    assert "GOLDM" in res_specs
    assert "995/1000" in res_specs


def test_walk_forward_validation_is_out_of_sample():
    from src.validation_engine import run_walk_forward_validation
    df = pd.read_csv("data/processed/historical_gold_futures.csv")
    v = run_walk_forward_validation(df, "2026-10-15", symbols=["GOLDM"])
    i, o = v["in_sample"], v["out_of_sample"]
    # the two windows must not overlap, so the test window is genuinely unseen
    assert i["end"] < o["start"]
    assert v["selected"]["entry_z"] in (1.5, 2.0, 2.5, 3.0)
    assert o["trades"] >= 0


def test_attribution_splits_gross_pnl():
    from src.validation_engine import attribute_pnl_vs_underlying
    df = pd.read_csv("data/processed/historical_gold_futures.csv")
    a = attribute_pnl_vs_underlying(df, symbols=["GOLDM"])
    assert a["observations"] > 0
    # directional + relative-value components must reconstruct gross P&L
    assert abs(a["directional_pnl"] + a["relative_value_pnl"] - a["gross_pnl"]) < 0.05


def test_agent_verification_matches_dataset():
    from src.agent_verification import parse_mcx_expiry, verify_against_dataset
    assert parse_mcx_expiry("04DEC2026") == pd.Timestamp("2026-12-04")
    assert parse_mcx_expiry("not a date") is None
    df = pd.read_csv("data/processed/historical_gold_futures.csv")
    r = verify_against_dataset(df)
    assert r["total"] > 0
    # every recorded agent observation must still agree with the dataset
    assert r["all_passed"], [c for c in r["checks"] if not c["passed"]]


def test_agent_verification_detects_a_wrong_row():
    from src.agent_verification import verify_against_dataset
    df = pd.read_csv("data/processed/historical_gold_futures.csv")
    bad = [{
        "kind": "row_integrity",
        "trade_date": "2026-11-17",
        "rows": [{"symbol": "GOLDM", "expiry_date": "04DEC2026",
                  "close": 1.0, "volume_lots": 1, "open_interest_lots": 1}],
    }]
    r = verify_against_dataset(df, runs=bad)
    assert r["failed"] == 1 and not r["all_passed"]
