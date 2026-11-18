"""MCX vs COMEX Gold Import Parity Engine.

Calculates theoretical Indian landed import cost from international benchmark prices
(COMEX Gold in USD/oz and USD/INR exchange rate), factoring in Indian tariff
structures (Customs Duty, AIDC, Social Welfare Surcharge, and GST).
Quantifies the India Gold Basis (Domestic Premium / Discount).
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

TROY_OUNCE_TO_GRAMS = 31.1034768

# Reference inputs for the last session in the dataset (17 Nov 2026):
# spot gold (XAU/USD) at the 4:30 pm ET close, and the USD/INR interbank close
# (93.51, provisional, PTI). Update these whenever the dataset is extended.
REFERENCE_DATE = "17 Nov 2026"
REFERENCE_COMEX_USD_PER_OZ = 3849.59
REFERENCE_USDINR = 93.51

# Gold import duty from 13 May 2026 (Customs Notification No. 16/2026):
# 10% Basic Customs Duty + 5% AIDC = 15% customs levy. Gold is exempt from the
# Social Welfare Surcharge, so SWC defaults to 0. IGST is 3%.
BCD_PCT = 10.0
AIDC_PCT = 5.0
SWC_PCT = 0.0
IGST_PCT = 3.0


def calculate_landed_import_parity(
    comex_usd_per_oz: float = REFERENCE_COMEX_USD_PER_OZ,
    usdinr_rate: float = REFERENCE_USDINR,
    customs_duty_pct: float = BCD_PCT,
    aidc_pct: float = AIDC_PCT,
    swc_pct: float = SWC_PCT,
    gst_pct: float = IGST_PCT,
    handling_charges_inr_per_g: float = 5.0,
    domestic_mcx_price_per_g: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate the landed import fair price of gold in INR per 1 gram of 999 purity.

    Parameters
    ----------
    comex_usd_per_oz : float
        COMEX Gold price in USD per troy ounce.
    usdinr_rate : float
        USD/INR spot/reference exchange rate.
    customs_duty_pct : float
        Basic Customs Duty (BCD) % (10% from 13 May 2026).
    aidc_pct : float
        Agriculture Infrastructure & Development Cess % (5% from 13 May 2026).
    swc_pct : float
        Social Welfare Surcharge % on BCD (0: gold is exempt).
    gst_pct : float
        Integrated Goods and Services Tax % (3.0% on landed price).
    handling_charges_inr_per_g : float
        Port handling, freight, vaulting, and bank finance charges per gram.
    domestic_mcx_price_per_g : float, optional
        Current MCX normalized domestic price per gram to compute Basis.

    Returns
    -------
    Dict[str, Any]
        Dictionary with full cost breakdown, Landed Fair Price (₹/g and ₹/10g),
        Domestic Basis (₹/g), and import arbitrage status.
    """
    # Base CIF cost in USD per gram
    cif_usd_per_gram = comex_usd_per_oz / TROY_OUNCE_TO_GRAMS
    
    # Base CIF cost in INR per gram
    cif_inr_per_gram = cif_usd_per_gram * usdinr_rate

    # Duties and Taxes breakdown
    bcd_amount = cif_inr_per_gram * (customs_duty_pct / 100.0)
    aidc_amount = cif_inr_per_gram * (aidc_pct / 100.0)
    swc_amount = bcd_amount * (swc_pct / 100.0)
    total_customs_cess = bcd_amount + aidc_amount + swc_amount

    # Price before GST (Assessable value + customs)
    assessable_landed_before_gst = cif_inr_per_gram + total_customs_cess + handling_charges_inr_per_g

    # Domestic GST (3%)
    gst_amount = assessable_landed_before_gst * (gst_pct / 100.0)

    # Final Landed Price per gram (inc. GST)
    landed_price_inc_gst_per_g = assessable_landed_before_gst + gst_amount
    
    # Wholesale market quote benchmark (per 10g without GST vs with GST)
    landed_price_ex_gst_per_g = assessable_landed_before_gst
    landed_price_per_10g_ex_gst = landed_price_ex_gst_per_g * 10.0
    landed_price_per_10g_inc_gst = landed_price_inc_gst_per_g * 10.0

    # Basis Analysis (MCX vs Landed Parity)
    basis_inr_per_g = None
    basis_pct = None
    market_verdict = "N/A"
    actionable_insight = ""

    if domestic_mcx_price_per_g is not None and domestic_mcx_price_per_g > 0:
        # MCX futures prices are quoted ex-GST (GST is paid only on physical delivery)
        basis_inr_per_g = domestic_mcx_price_per_g - landed_price_ex_gst_per_g
        basis_pct = (basis_inr_per_g / landed_price_ex_gst_per_g) * 100.0

        if basis_inr_per_g > 20.0:
            market_verdict = "Landed Premium (Import Arbitrage Open)"
            actionable_insight = (
                f"Domestic MCX is trading at a premium of +₹{basis_inr_per_g:.2f}/g (+{basis_pct:.2f}%) "
                "over international landed parity. Banks and nominated agencies can profitably import physical gold, "
                "which typically exerts downward pressure on domestic futures."
            )
        elif basis_inr_per_g < -20.0:
            market_verdict = "Landed Discount (Oversupply / Squeeze Risk)"
            actionable_insight = (
                f"Domestic MCX is trading at a discount of -₹{abs(basis_inr_per_g):.2f}/g ({basis_pct:.2f}%) "
                "below official landed import parity. Official imports stall; indicates domestic scrap recycling "
                "or grey-market gold inflows dampening Indian futures prices."
            )
        else:
            market_verdict = "Parity Equilibrium (Fair Valuation)"
            actionable_insight = (
                f"Domestic MCX aligns closely with COMEX parity (diff: ₹{basis_inr_per_g:+.2f}/g). "
                "No cross-border pricing dislocation."
            )

    return {
        "comex_usd_per_oz": comex_usd_per_oz,
        "usdinr_rate": usdinr_rate,
        "cif_inr_per_gram": round(cif_inr_per_gram, 2),
        "total_tariffs_pct": round(customs_duty_pct + aidc_pct + (customs_duty_pct * swc_pct / 100.0), 2),
        "total_duties_inr_per_g": round(total_customs_cess, 2),
        "handling_charges_inr_per_g": handling_charges_inr_per_g,
        "landed_price_ex_gst_per_g": round(landed_price_ex_gst_per_g, 2),
        "landed_price_inc_gst_per_g": round(landed_price_inc_gst_per_g, 2),
        "landed_price_per_10g_ex_gst": round(landed_price_per_10g_ex_gst, 2),
        "landed_price_per_10g_inc_gst": round(landed_price_per_10g_inc_gst, 2),
        "domestic_mcx_price_per_g": round(domestic_mcx_price_per_g, 2) if domestic_mcx_price_per_g else None,
        "basis_inr_per_g": round(basis_inr_per_g, 2) if basis_inr_per_g is not None else None,
        "basis_pct": round(basis_pct, 2) if basis_pct is not None else None,
        "market_verdict": market_verdict,
        "actionable_insight": actionable_insight,
    }


def generate_historical_parity_series(
    mcx_df: pd.DataFrame,
    base_comex_usd: float = REFERENCE_COMEX_USD_PER_OZ,
    base_usdinr: float = REFERENCE_USDINR,
) -> pd.DataFrame:
    """ILLUSTRATIVE ONLY: simulated parity path, not historical market data.

    COMEX and USD/INR are generated with a seeded random walk around the base
    inputs. Do not present the output as real historical parity.
    """
    data = mcx_df.copy()
    data["trade_date"] = pd.to_datetime(data["trade_date"], errors="coerce", format="mixed")
    
    # Calculate daily mean normalized price for GOLDM/GOLDTEN as benchmark
    daily_mcx = data[data["symbol"].isin(["GOLDM", "GOLDTEN"])].groupby("trade_date")["normalized_price_per_gram"].mean().reset_index()
    daily_mcx = daily_mcx.sort_values("trade_date").reset_index(drop=True)

    results = []
    # Drift simulation around base comex/usdinr to show realistic basis fluctuations
    n_days = len(daily_mcx)
    np.random.seed(42)
    comex_drift = np.cumsum(np.random.normal(0, 4.0, n_days))
    fx_drift = np.cumsum(np.random.normal(0, 0.05, n_days))

    for idx, row in daily_mcx.iterrows():
        t_date = row["trade_date"]
        mcx_px = float(row["normalized_price_per_gram"])
        sim_comex = max(1000.0, base_comex_usd + float(comex_drift[idx]))
        sim_fx = max(50.0, base_usdinr + float(fx_drift[idx]))

        parity_info = calculate_landed_import_parity(
            comex_usd_per_oz=sim_comex,
            usdinr_rate=sim_fx,
            domestic_mcx_price_per_g=mcx_px,
        )

        results.append({
            "trade_date": t_date,
            "mcx_price_per_g": mcx_px,
            "comex_usd_per_oz": round(sim_comex, 1),
            "usdinr_rate": round(sim_fx, 2),
            "landed_parity_per_g": parity_info["landed_price_ex_gst_per_g"],
            "basis_inr_per_g": parity_info["basis_inr_per_g"],
            "basis_pct": parity_info["basis_pct"],
            "market_verdict": parity_info["market_verdict"],
        })

    return pd.DataFrame(results)
