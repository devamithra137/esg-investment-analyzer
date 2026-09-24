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

- a **REST API** built with FastAPI (with async threadpool execution & TTL caching)
- an **interactive analytics dashboard** built with Streamlit & Plotly
- a **CLI reporting tool** for terminal-based analysis
- a **comprehensive automated test suite** built with `pytest`

This project demonstrates how ESG indicators can be integrated with quantitative financial analysis.

---

# Features

| Category | Capability |
|--------|-------------|
| Market Data | Real-time price quotes and 1-year price history via Yahoo Finance with 10-minute TTL caching |
| ESG Scoring | Centralized Environmental, Social, and Governance sub-scores with sector baselines |
| Risk Analysis | Log returns, sample standard deviation, annualized volatility, and three-tier risk classification |
| Investment Rating | Combined ESG + financial risk sustainability score with score consistency capping for high-risk assets |
| REST API | FastAPI service with OpenAPI documentation and Pydantic validation |
| Dashboard | Interactive Streamlit analytics dashboard with environment-driven API configuration |
| CLI Tool | UTF-8 compatible terminal-based investment report generator |
| Testing Suite | Full offline `pytest` suite covering ESG, risk, rating, market data, and API endpoints |

---

# System Architecture

```
User Input (Ticker)
        │
        ▼
FastAPI API Layer (main.py)
        │
        ▼
Core Analytics Pipeline
 ├── market_data.py        ──► yfinance API + In-Memory TTL Cache
 ├── esg_scoring.py        ──► Centralized ESG Engine (Sector Profiles + Ticker MD5 Seed)
 ├── risk_analysis.py      ──► Log Returns & Annualized Volatility (σ)
 └── investment_rating.py ──► Blended Sustainability Rating Matrix & Capped Score
        │
        ▼
Streamlit Dashboard / CLI Output
```

---

# Data Flow

```
Ticker Symbol
    │
    ├─► Fetch market data (yfinance with TTL Cache & Chronological Date Order)
    │
    ├─► Generate ESG scores (Sector baselines + Ticker MD5 noise offset)
    │
    ├─► Calculate volatility and financial risk (ddof=1 sample std dev × √252)
    │
    └─► Compute investment sustainability rating (60% ESG + 40% Risk Factor, capped for High Risk)
```

---

# ESG Decision Matrix

| ESG Tier | Risk Level | Rating Label | Score Constraint |
|---------|------------|--------------|------------------|
| High ($\ge 70$) | Low ($< 0.20$) | High Sustainability | 0 – 100 |
| High ($\ge 70$) | Medium ($0.20 - 0.40$) | Sustainable Growth | 0 – 100 |
| High ($\ge 70$) | High ($\ge 0.40$) | High Risk | Capped $\le 49$ |
| Medium ($40 - 70$) | Low ($< 0.20$) | Sustainable Growth | 0 – 100 |
| Medium ($40 - 70$) | Medium ($0.20 - 0.40$) | Sustainable Growth | 0 – 100 |
| Medium ($40 - 70$) | High ($\ge 0.40$) | High Risk | Capped $\le 49$ |
| Low ($< 40$) | Any | High Risk | Capped $\le 49$ |

---

# Tech Stack

| Layer | Technology |
|------|-------------|
| Language | Python 3.11+ |
| API Framework | FastAPI, Starlette, Pydantic v2 |
| Dashboard | Streamlit |
| Visualization | Plotly (graph_objects) |
| Market Data | yfinance |
| Data Processing | Pandas, NumPy |
| HTTP Client | Requests, HTTPX |
| Testing | pytest, pytest-asyncio |
| Server | Uvicorn |

---

# Project Structure

```
esg-investment-analyzer
│
├── main.py                # FastAPI REST Service & API Routes
├── esg_scoring.py         # Centralized ESG Engine (Sector Profiles & Deterministic Seeding)
├── market_data.py         # Market Data Engine (yfinance Ingestion & 10-Min TTL Cache)
├── risk_analysis.py       # Financial Risk Engine (Log Returns & Annualized Volatility)
├── investment_rating.py  # Blended Investment Sustainability Rating Matrix
├── dashboard.py           # Interactive Streamlit Bloomberg-Style Dashboard
├── cli.py                 # Command-Line Report Generator (UTF-8 Windows Safe)
├── requirements.txt       # Pinned production runtime dependencies
├── requirements-dev.txt   # Development and testing dependencies
└── tests/                 # Automated Pytest Test Suite (100% Offline)
    ├── __init__.py
    ├── test_esg_scoring.py
    ├── test_risk_analysis.py
    ├── test_investment_rating.py
    ├── test_market_data.py
    └── test_api.py
```

---

# Environment Variables

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `API_BASE_URL` | `http://localhost:8000` | Backend API base URL used by Streamlit dashboard |
| `CORS_ORIGINS` | `http://localhost:8501` | Comma-separated CORS allowed origins for FastAPI |
| `CACHE_TTL_SECONDS` | `600` | In-memory market data TTL cache duration in seconds |
| `REQUEST_TIMEOUT` | `30` | HTTP request timeout in seconds for Streamlit dashboard API calls |

---

# Installation & Setup

## 1. Clone Repository

```bash
git clone https://github.com/devamithra137/esg-investment-analyzer.git
cd esg-investment-analyzer
```

## 2. Create Virtual Environment

```bash
python -m venv .venv
```

Activate:

Windows:

```bash
.venv\Scripts\activate
```

Mac / Linux:

```bash
source .venv/bin/activate
```

## 3. Install Dependencies

Production runtime dependencies:

```bash
pip install -r requirements.txt
```

Development and testing dependencies:

```bash
pip install -r requirements-dev.txt
```

---

# Running the Application

## Start API

```bash
uvicorn main:app --reload --port 8000
```

API endpoints:

```text
http://localhost:8000/          ← Service metadata
http://localhost:8000/health     ← Liveness check
http://localhost:8000/analyze/{ticker}  ← Full analysis
http://localhost:8000/docs      ← OpenAPI Swagger UI
```

## Start Dashboard

Open a new terminal:

```bash
streamlit run dashboard.py
```

Dashboard:

```text
http://localhost:8501
```

---

# CLI Analysis

Run investment report directly from terminal:

```bash
python cli.py AAPL
```

Multiple companies:

```bash
python cli.py TSLA MSFT NVDA
```

---

# Running Automated Tests

Run the full automated test suite offline:

```bash
pytest
```

Verbose test output:

```bash
pytest -v
```

---

# Example API Response

```json
{
  "ticker": "AAPL",
  "price": 332.23,
  "sector": "Technology",
  "environment": 70.64,
  "social": 64.16,
  "governance": 80.47,
  "esg_score": 71.64,
  "volatility": 0.2512,
  "risk_level": "MEDIUM",
  "investment_score": 67,
  "rating": "Sustainable Growth"
}
```

---

# Methodology & ESG Transparency

## Volatility Calculation

Annualized volatility ($\sigma$) is calculated using log returns:

$$\sigma = \text{std}\left(\ln\left(\frac{P_t}{P_{t-1}}\right), \text{ddof}=1\right) \times \sqrt{252}$$

This accurately reflects the annualized variability of stock returns over 252 trading days per year.

## ESG Scoring Methodology

> **Important ESG Transparency Notice**:  
> ESG metrics in this project are **simulated deterministically** using sector baseline profiles (e.g., Technology $E=68, S=72, G=80$; Energy $E=38, S=60, G=65$) combined with ticker MD5 hash-seeded uniform noise.  
> They are **NOT** sourced from commercial ESG data providers such as MSCI ESG, Sustainalytics, or Refinitiv. The simulation guarantees reproducibility across runs while demonstrating how ESG indicators integrate into quantitative analytics pipelines.

---

# Limitations

- **yfinance Dependency**: Market data is fetched via Yahoo Finance's un-official web scraping library, which lacks an official SLA.
- **Simulated ESG Data**: ESG scores are generated deterministically via sector profiles for educational/demo purposes rather than live commercial ESG APIs.
- **In-Memory Cache Scope**: Market data caching uses a single-node in-memory TTL dictionary rather than a distributed cache like Redis.

---

# Future Improvements

Possible extensions include:

- Integration with commercial ESG data provider APIs
- Distributed Redis caching and Celery background task processing
- Portfolio-level ESG aggregation and risk screening
- TimescaleDB / PostgreSQL database storage for historical price & rating tracking
- Docker containerization & GitHub Actions CI/CD pipeline

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