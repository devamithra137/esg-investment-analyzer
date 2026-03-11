<div align="center">

# Real-Time ESG Investment Analyzer

Financial Analytics · ESG Risk · Sustainability Rating

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.33+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-00D4AA?style=flat-square)](LICENSE)

A modular Python fintech analytics platform that evaluates companies using ESG metrics and financial risk indicators.

</div>

---

# Overview

The **Real-Time ESG Investment Analyzer** is a financial analytics platform that combines **Environmental, Social, and Governance (ESG) scoring** with **traditional financial risk analysis**.

The system fetches live market data, computes sustainability metrics, evaluates financial volatility, and produces an **Investment Sustainability Rating (ISR)**.

The platform exposes:

- a **REST API** built with FastAPI
- an **interactive analytics dashboard** built with Streamlit
- a **CLI reporting tool** for terminal-based analysis

This project demonstrates how ESG indicators can be integrated with quantitative financial analysis.

---

# Features

| Category | Capability |
|--------|-------------|
| Market Data | Real-time price quotes and 1-year price history via Yahoo Finance |
| ESG Scoring | Environmental, Social, and Governance sub-scores |
| Risk Analysis | Annualized volatility and three-tier risk classification |
| Investment Rating | Combined ESG + financial risk sustainability score |
| REST API | FastAPI service with OpenAPI documentation |
| Dashboard | Interactive Streamlit analytics dashboard |
| CLI Tool | Terminal-based investment report |
| Comparison Tool | Multi-company ESG comparison with radar charts |

---

# System Architecture

```
User Input (Ticker)
        │
        ▼
FastAPI API Layer
(main.py)
        │
        ▼
Core Analytics Pipeline
 ├── market_data.py
 ├── risk_analysis.py
 ├── investment_rating.py
        │
        ▼
ESG Scoring Engine
(Environment / Social / Governance)
        │
        ▼
Investment Sustainability Rating
        │
        ▼
Streamlit Dashboard / CLI Output
```

---

# Data Flow

```
Ticker Symbol
    │
    ├─► Fetch market data (yfinance)
    │
    ├─► Generate ESG scores
    │
    ├─► Calculate volatility and financial risk
    │
    └─► Compute investment sustainability rating
```

---

# ESG Decision Matrix

| ESG Tier | Risk Level | Rating |
|---------|------------|--------|
| High | Low | High Sustainability |
| High | Medium | Sustainable Growth |
| Medium | Low | Sustainable Growth |
| Medium | Medium | Sustainable Growth |
| Medium | High | High Risk |
| Low | Any | High Risk |

---

# Tech Stack

| Layer | Technology |
|------|-------------|
| Language | Python |
| API Framework | FastAPI |
| Dashboard | Streamlit |
| Visualization | Plotly |
| Market Data | yfinance |
| Data Processing | Pandas / NumPy |
| HTTP Client | Requests |
| Server | Uvicorn |

---

# Project Structure

```
esg-investment-analyzer
│
├── main.py
├── dashboard.py
├── market_data.py
├── risk_analysis.py
├── investment_rating.py
├── test_analysis.py
├── requirements.txt
└── README.md
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/devamithra137/esg-investment-analyzer.git
cd esg-investment-analyzer
```

## Create Virtual Environment

```bash
python -m venv .venv
```

Activate:

Windows

```bash
.venv\Scripts\activate
```

Mac / Linux

```bash
source .venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Running the Application

## Start API

```bash
uvicorn main:app --reload --port 8000
```

API endpoints:

```
http://localhost:8000/analyze/{ticker}
http://localhost:8000/docs
```

---

## Start Dashboard

Open a new terminal:

```bash
streamlit run dashboard.py
```

Dashboard:

```
http://localhost:8501
```

---

# CLI Analysis

Run analysis directly from terminal:

```bash
python test_analysis.py AAPL
```

Multiple companies:

```bash
python test_analysis.py TSLA MSFT NVDA
```

---

# Example API Response

```json
{
 "ticker": "AAPL",
 "price": 189.40,
 "sector": "Technology",
 "environment": 71.3,
 "social": 74.8,
 "governance": 83.5,
 "esg_score": 75.8,
 "volatility": 0.2312,
 "risk_level": "MEDIUM",
 "investment_score": 69,
 "rating": "Sustainable Growth"
}
```

---

# Methodology

## Volatility Calculation

Annualized volatility is calculated using log returns:

```
σ = std(log(Pt / Pt-1)) × √252
```

This reflects the annualized variability of stock returns.

---

## ESG Scores

ESG scores are **simulated using deterministic sector-based models**.

Real ESG data providers typically include:

- MSCI ESG
- Sustainalytics
- Refinitiv

The simulation ensures reproducibility while demonstrating ESG integration in analytics pipelines.

---

# Future Improvements

Possible extensions include:

- Real ESG data integration
- Portfolio-level ESG analysis
- ESG screening for multiple tickers
- Database storage for historical analysis
- Docker deployment
- CI/CD automation
- Live ESG news sentiment analysis

---

# Disclaimer

This project is for **educational purposes only**.

- ESG scores are simulated.
- Market data comes from Yahoo Finance.
- This platform does **not provide financial advice**.

---

# License

MIT License

---

<div align="center">

Real-Time ESG Investment Analyzer

Built for learning financial analytics and sustainable investment systems.

</div>