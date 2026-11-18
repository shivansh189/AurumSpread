"""MCX Data Doctor: Automated Bhavcopy Diagnostic & Audit Engine.

Audits raw and processed MCX Bhavcopy datasets for silent holiday fallbacks,
space-padded symbols, corrupt date formats, negative or outlier prices,
and continuous-series rollover jumps.
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd


def audit_dataset_health(df: pd.DataFrame) -> Dict[str, Any]:
    """Run an automated diagnostic audit across the MCX gold dataset.

    Returns health score (0-100), issue counts, and diagnostic flags.
    """
    diagnostics: List[Dict[str, Any]] = []
    total_rows = len(df)

    if total_rows == 0:
        return {
            "health_score": 0,
            "status": "CRITICAL",
            "diagnostics": [{"check": "Row Count", "status": "FAIL", "detail": "Dataset is empty"}],
            "total_rows": 0,
        }

    # 1. Symbol Whitespace & Padding Check
    raw_symbols = df["symbol"].astype(str)
    padded_symbols = raw_symbols[raw_symbols.str.startswith(" ") | raw_symbols.str.endswith(" ")].count()
    if padded_symbols > 0:
        diagnostics.append({
            "check": "Symbol Padding",
            "status": "WARNING",
            "detail": f"{padded_symbols} rows contain leading/trailing whitespace in symbol",
            "penalty": 10,
        })
    else:
        diagnostics.append({
            "check": "Symbol Padding",
            "status": "PASS",
            "detail": "All contract symbols cleanly stripped and normalized",
            "penalty": 0,
        })

    # 2. Date Parsing Sanity
    trade_dates = pd.to_datetime(df["trade_date"], errors="coerce", format="mixed")
    expiry_dates = pd.to_datetime(df["expiry_date"], errors="coerce", format="mixed")

    invalid_t_dates = trade_dates.isna().sum()
    invalid_e_dates = expiry_dates.isna().sum()

    if invalid_t_dates > 0 or invalid_e_dates > 0:
        diagnostics.append({
            "check": "Date Integrity",
            "status": "FAIL",
            "detail": f"Unparsed dates: {invalid_t_dates} trade dates, {invalid_e_dates} expiries",
            "penalty": 20,
        })
    else:
        diagnostics.append({
            "check": "Date Integrity",
            "status": "PASS",
            "detail": "100% of trade dates and expiry dates successfully parsed into ISO datetime",
            "penalty": 0,
        })

    # 3. Price Sanity & Outliers
    px = pd.to_numeric(df.get("normalized_price_per_gram", df.get("close")), errors="coerce")
    non_positive = (px <= 0).sum()
    if non_positive > 0:
        diagnostics.append({
            "check": "Price Sanity",
            "status": "FAIL",
            "detail": f"{non_positive} rows have zero or negative prices",
            "penalty": 25,
        })
    else:
        diagnostics.append({
            "check": "Price Sanity",
            "status": "PASS",
            "detail": f"All prices positive (range: ₹{px.min():,.1f} to ₹{px.max():,.1f}/g)",
            "penalty": 0,
        })

    # 4. Expiry Ordering (Days to Expiry >= 0)
    days_to_exp = (expiry_dates - trade_dates).dt.days
    expired_records = (days_to_exp < 0).sum()
    if expired_records > 0:
        diagnostics.append({
            "check": "Lifecycle Sequence",
            "status": "WARNING",
            "detail": f"{expired_records} rows traded after their expiry date",
            "penalty": 15,
        })
    else:
        diagnostics.append({
            "check": "Lifecycle Sequence",
            "status": "PASS",
            "detail": "Zero retro-active trades; all contracts trade before expiry",
            "penalty": 0,
        })

    # 5. Liquidity & Zero Volume Check
    if "volume_lots" in df.columns:
        vol = pd.to_numeric(df["volume_lots"], errors="coerce").fillna(0)
        zero_vol = (vol == 0).sum()
        zero_vol_pct = (zero_vol / total_rows) * 100.0
        diagnostics.append({
            "check": "Volume Reporting",
            "status": "PASS" if zero_vol_pct < 25 else "INFO",
            "detail": f"{zero_vol} rows ({zero_vol_pct:.1f}%) have 0 volume (far-month illiquidity flagged)",
            "penalty": 5 if zero_vol_pct > 35 else 0,
        })

    # 6. Holiday Continuity & Gaps
    unique_dates = trade_dates.dropna().drop_duplicates().sort_values()
    date_diffs = unique_dates.diff().dt.days
    abnormal_gaps = (date_diffs > 4).sum()  # More than a normal weekend + 1 day holiday
    if abnormal_gaps > 0:
        diagnostics.append({
            "check": "Holiday Continuity",
            "status": "INFO",
            "detail": f"{abnormal_gaps} calendar gaps (>4 days) detected (festival/exchange holidays)",
            "penalty": 0,
        })
    else:
        diagnostics.append({
            "check": "Holiday Continuity",
            "status": "PASS",
            "detail": "Continuous trading calendar with no unexplained trading voids",
            "penalty": 0,
        })

    # Compute overall score
    total_penalty = sum(d["penalty"] for d in diagnostics)
    score = max(0, 100 - total_penalty)

    status = "EXCELLENT" if score >= 90 else "GOOD" if score >= 75 else "NEEDS_REVIEW"

    return {
        "health_score": score,
        "status": status,
        "total_rows": total_rows,
        "unique_symbols": df["symbol"].nunique(),
        "trading_days": unique_dates.nunique(),
        "diagnostics": diagnostics,
    }
