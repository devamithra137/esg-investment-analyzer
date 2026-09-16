"""
tests/test_api.py
------------------
Integration tests for FastAPI endpoints (main.py) using TestClient and mocked market data.
Fully deterministic and offline.
"""

from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest
from main import app
from market_data import clear_cache

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_cache():
    clear_cache()
    yield
    clear_cache()


def test_root_endpoint():
    """Test hidden health index GET /."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ESG Investment Analyzer"
    assert data["status"] == "healthy"
    assert "X-Process-Time" in response.headers


def test_health_check_endpoint():
    """Test system liveness probe GET /health."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("main.get_market_data")
def test_analyze_ticker_success(mock_get_market_data):
    """Test successful GET /analyze/{ticker} endpoint call with mocked market data."""
    mock_get_market_data.return_value = {
        "ticker": "AAPL",
        "price": 189.40,
        "sector": "Technology",
        "volatility": 0.2312,
        "historical_prices": [
            {"date": "2024-01-01", "open": 185.0, "high": 190.0, "low": 184.0, "close": 185.0, "volume": 1000},
            {"date": "2024-01-02", "open": 185.0, "high": 190.0, "low": 184.0, "close": 186.5, "volume": 1050},
            {"date": "2024-01-03", "open": 186.5, "high": 191.0, "low": 185.0, "close": 184.2, "volume": 1100},
            {"date": "2024-01-04", "open": 184.2, "high": 189.0, "low": 183.0, "close": 187.8, "volume": 1150},
            {"date": "2024-01-05", "open": 187.8, "high": 191.0, "low": 187.0, "close": 189.4, "volume": 1200},
        ],
    }

    response = client.get("/analyze/AAPL")
    assert response.status_code == 200

    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["price"] == 189.40
    assert data["sector"] == "Technology"
    assert "environment" in data
    assert "social" in data
    assert "governance" in data
    assert "esg_score" in data
    assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert "investment_score" in data
    assert "rating" in data


@pytest.mark.parametrize("invalid_ticker", ["AAPL!!!", "INVALID@TICKER", "<script>", "TOOLONGTICKER"])
def test_analyze_ticker_invalid_regex_format_returns_422(invalid_ticker):
    """Test Pydantic regex pattern validation rejection (HTTP 422)."""
    response = client.get(f"/analyze/{invalid_ticker}")
    assert response.status_code == 422


@patch("main.get_market_data")
def test_analyze_ticker_not_found_returns_404(mock_get_market_data):
    """Test ticker data unavailable handling (HTTP 404)."""
    mock_get_market_data.side_effect = ValueError("No market data found for ticker 'NOTFOUND'")

    response = client.get("/analyze/NOTFOUND")
    assert response.status_code == 404
    data = response.json()
    assert "No market data found" in data["detail"]


@patch("main.get_market_data")
def test_analyze_ticker_upstream_error_returns_502(mock_get_market_data):
    """Test upstream yfinance failure handling (HTTP 502)."""
    mock_get_market_data.side_effect = RuntimeError("Upstream connection timeout")

    response = client.get("/analyze/AAPL")
    assert response.status_code == 502
    data = response.json()
    assert "Failed to retrieve market data" in data["detail"]
