
import pandas as pd
import pytest

from src.ingest import (
    clean_contract_data,
    load_csv,
    split_valid_invalid,
)


def test_load_sample_csv():
    df = load_csv("data/samples/sample_contracts.csv")
    assert len(df) == 6


def test_symbols_are_trimmed_and_uppercase():
    df = pd.DataFrame({
        "trade_date": ["2026-01-05"],
        "symbol": [" goldpetal "],
        "expiry_date": ["2026-02-27"],
        "close": ["1460"],
    })

    result = clean_contract_data(df)
    assert result.loc[0, "symbol"] == "GOLDPETAL"


def test_invalid_expiry_is_flagged():
    df = pd.DataFrame({
        "trade_date": ["2026-01-05"],
        "symbol": ["GOLDTEN"],
        "expiry_date": ["not-a-date"],
        "close": ["14600"],
    })

    result = clean_contract_data(df)
    assert result.loc[0, "validation_error"] == "invalid_expiry_date;"


def test_missing_required_column_raises():
    df = pd.DataFrame({
        "trade_date": ["2026-01-05"],
        "symbol": ["GOLDTEN"],
        "close": [14600],
    })

    with pytest.raises(ValueError):
        clean_contract_data(df)



def test_valid_and_invalid_rows_are_separated():
    df = load_csv("data/samples/sample_contracts.csv")
    cleaned = clean_contract_data(df)

    valid, invalid = split_valid_invalid(cleaned)

    assert len(valid) == 5
    assert len(invalid) == 1
    assert invalid["validation_error"].str.contains(
        "invalid_expiry_date"
    ).all()
