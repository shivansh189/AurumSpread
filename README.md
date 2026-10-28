# AurumSpread
### Commodity Derivatives Intelligence for MCX Gold Futures

AurumSpread is a data-driven commodity derivatives intelligence platform designed to analyze MCX gold futures, explore calendar spreads across contract expiries, and evaluate spread-based trading strategies through historical backtesting.

The project transforms historical MCX Bhavcopy data into normalized gold prices and provides interactive dashboards for spread analysis, market insights, and strategy evaluation.

---

## Problem Statement

Commodity futures with different expiry dates can trade at different prices. Understanding the relationship between these contracts helps analyze market structure, calendar spreads, and changes in futures pricing.

AurumSpread aims to make this analysis easier by:

- Processing historical MCX gold futures data.
- Normalizing gold prices across different contract types.
- Calculating calendar spreads between expiry contracts.
- Analyzing spread movements and historical behavior.
- Simulating spread-based strategies with configurable transaction costs and slippage.

---

## Key Features

### 1. Market Overview
Provides a consolidated view of historical gold futures data and available instruments.

### 2. Spread Explorer
- Compare gold futures contracts with different expiry dates.
- Calculate calendar spreads.
- Explore spread movements across historical dates.
- Analyze spread behavior using normalized prices.

### 3. Spread Intelligence
- Track spread widening and narrowing.
- Calculate historical spread percentiles.
- Analyze spread Z-scores using past observations.
- Identify spread deviations from historical behavior.

### 4. Backtesting
- Simulate long and short calendar spread strategies.
- Configure entry and exit Z-score thresholds.
- Include transaction costs and slippage.
- Track gross and net P&L.
- Analyze completed trades, win rate, and maximum drawdown.
- Compare different exit Z-score strategies.

### 5. Data Quality
Provides checks and validation for the processed historical dataset.

---

## Technology Stack

- Python
- Streamlit
- Pandas
- NumPy
- Plotly
- Pytest

---

## Project Structure

```text
AurumSpread/
├── app.py
├── build_historical_dataset.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── ingest.py
│   ├── normalize.py
│   ├── spread_engine.py
│   ├── spread_intelligence.py
│   └── backtest_engine.py
│
├── data/
│   ├── raw/
│   └── processed/
│       └── historical_gold_futures.csv
│
└── tests/
```

---

## Installation

### Prerequisites

- Python 3.10 or later
- Git
- Visual Studio Code (recommended)

### 1. Clone the repository

```bash
cd AurumSpread
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the environment

Windows:

```bash
.venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Dataset Preparation

AurumSpread uses historical MCX Bhavcopy data for gold futures.

The dataset preparation pipeline:

1. Loads historical raw MCX data.
2. Filters relevant gold futures contracts.
3. Standardizes column names and formats.
4. Normalizes prices into a common price-per-gram representation.
5. Validates and saves the processed dataset.

To build the historical dataset:

```bash
python build_historical_dataset.py
```

The processed dataset is expected at:

```text
data/processed/historical_gold_futures.csv
```

---

## Run the Dashboard

Start the Streamlit application:

```bash
streamlit run app.py
```

Open the local URL provided by Streamlit in your browser.

---

## Backtesting Methodology

AurumSpread uses historical calendar spread observations to simulate spread-based strategies.

### Long Calendar Spread

A long spread is entered when the spread Z-score falls below the negative entry threshold.

### Short Calendar Spread

A short spread is entered when the spread Z-score exceeds the positive entry threshold.

### Exit Conditions

Positions can exit when:

- The spread Z-score returns to the configured exit threshold.
- The near-expiry contract approaches expiry.
- The available historical data ends.

### Performance Metrics

The dashboard displays metrics such as:

- Gross P&L
- Net P&L
- Transaction costs
- Completed trades
- Win rate
- Average P&L per trade
- Maximum drawdown

---

## Important Limitations

AurumSpread is a historical research and simulation project.

- Backtesting uses normalized spread changes, not actual MCX lot-level contract P&L.
- Results do not represent live trading performance.
- Transaction costs and slippage are configurable assumptions.
- Brokerage, exchange charges, taxes, margin requirements, and market impact may not be fully represented.
- Historical results do not guarantee future outcomes.

The project is intended for educational, analytical, and research purposes.

---

## Future Scope

- Incorporate additional commodity futures.
- Improve liquidity and volume analysis.
- Add more robust walk-forward backtesting.
- Introduce contract-level P&L calculations.
- Improve risk analysis and strategy evaluation.
- Expand historical data coverage.

---

## Acknowledgements

Historical market data is sourced from MCX Bhavcopy files.

**AurumSpread — Commodity Derivatives Intelligence**
