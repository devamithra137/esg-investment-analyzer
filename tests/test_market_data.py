"""
tests/test_market_data.py
--------------------------
Unit tests for market_data.py using mocked yfinance objects.
Runs completely offline without network dependencies.
"""

from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
from market_data import (
    clear_cache,
    fetch_current_price,
    fetch_historical_ohlcv,
    fetch_sector,
    get_market_data,
    _CACHE,
)


@pytest.fixture(autouse=True)
def reset_market_data_cache():
    """Clear market data cache before each test."""
    clear_cache()
    yield
    clear_cache()


def test_fetch_current_price_fast_info_success():
    """Test extracting price via yfinance fast_info shortcut."""
    mock_ticker = MagicMock()
    mock_ticker.ticker = "AAPL"
    mock_ticker.fast_info = {"last_price": 185.50}

    price = fetch_current_price(mock_ticker)
    assert price == 185.50


def test_fetch_current_price_fallback_to_history():
    """Test fallback to last close from short history when fast_info is missing."""
    mock_ticker = MagicMock()
    mock_ticker.ticker = "AAPL"
    mock_ticker.fast_info = {}

    mock_hist = pd.DataFrame({"Close": [180.0, 182.5, 184.20]})
    mock_ticker.history.return_value = mock_hist

    price = fetch_current_price(mock_ticker)
    assert price == 184.20


def test_fetch_current_price_failure_raises_value_error():
    """Test ValueError when neither fast_info nor short history delivers a price."""
    mock_ticker = MagicMock()
    mock_ticker.ticker = "INVALID"
    mock_ticker.fast_info = {}
    mock_ticker.history.return_value = pd.DataFrame()

    with pytest.raises(ValueError, match="Could not retrieve current price"):
        fetch_current_price(mock_ticker)


def test_fetch_sector_success():
    """Test sector retrieval from ticker info dictionary."""
    mock_ticker = MagicMock()
    mock_ticker.info = {"sector": "Technology"}

    sector = fetch_sector(mock_ticker)
    assert sector == "Technology"


def test_fetch_sector_failure_fallback_unknown():
    """Test fallback to 'Unknown' when info fails or lacks sector field."""
    mock_ticker = MagicMock()
    mock_ticker.info = {}
    assert fetch_sector(mock_ticker) == "Unknown"

    mock_ticker_err = MagicMock()
    type(mock_ticker_err).info = pytest.raises(Exception, match="Network error")
    assert fetch_sector(mock_ticker_err) == "Unknown"


def test_fetch_historical_ohlcv_chronological_ordering():
    """Test that historical OHLCV data is sorted chronologically (oldest to newest)."""
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    df_unordered = pd.DataFrame(
        {
            "Open": [100, 102, 101, 104, 103],
            "High": [105, 106, 105, 108, 107],
            "Low": [99, 101, 100, 103, 102],
            "Close": [101, 103, 102, 105, 104],
            "Volume": [1000, 1100, 1050, 1200, 1150],
        },
        index=reversed(dates),  # Newest to oldest
    )

    mock_ticker = MagicMock()
    mock_ticker.ticker = "AAPL"
    mock_ticker.history.return_value = df_unordered

    ohlcv = fetch_historical_ohlcv(mock_ticker)

    # Check dates are sorted ascending
    assert list(ohlcv.index) == list(dates)


def test_fetch_historical_ohlcv_empty_raises_value_error():
    """Test ValueError when history returns an empty DataFrame."""
    mock_ticker = MagicMock()
    mock_ticker.ticker = "EMPTY"
    mock_ticker.history.return_value = pd.DataFrame()

    with pytest.raises(ValueError, match="No historical data returned"):
        fetch_historical_ohlcv(mock_ticker)


def test_fetch_historical_ohlcv_multiindex_columns_flattened():
    """Test that MultiIndex columns returned by yfinance are flattened successfully."""
    dates = pd.date_range("2024-01-01", periods=3, freq="D")
    tuples = [("Open", "AAPL"), ("High", "AAPL"), ("Low", "AAPL"), ("Close", "AAPL"), ("Volume", "AAPL")]
    multi_cols = pd.MultiIndex.from_tuples(tuples)
    df_multi = pd.DataFrame(
        [
            [100, 105, 99, 101, 1000],
            [102, 106, 101, 103, 1100],
            [101, 105, 100, 102, 1050],
        ],
        index=dates,
        columns=multi_cols,
    )

    mock_ticker = MagicMock()
    mock_ticker.ticker = "AAPL"
    mock_ticker.history.return_value = df_multi

    ohlcv = fetch_historical_ohlcv(mock_ticker)
    assert list(ohlcv.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(ohlcv) == 3


@patch("market_data._fetch_ticker_object")
def test_get_market_data_ttl_cache_isolation(mock_fetch):
    """Test that TTL cache serves repeated calls and isolates different tickers."""
    # Setup mock ticker
    mock_ticker_aapl = MagicMock()
    mock_ticker_aapl.ticker = "AAPL"
    mock_ticker_aapl.fast_info = {"last_price": 180.0}
    mock_ticker_aapl.info = {"sector": "Technology"}

    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {
            "Open": [175, 176, 177, 178, 179],
            "High": [180, 181, 182, 183, 184],
            "Low": [174, 175, 176, 177, 178],
            "Close": [178, 179, 180, 181, 182],
            "Volume": [1000, 1000, 1000, 1000, 1000],
        },
        index=dates,
    )
    mock_ticker_aapl.history.return_value = df

    mock_fetch.return_value = mock_ticker_aapl

    # 1. First fetch for AAPL
    data1 = get_market_data("AAPL")
    assert data1["ticker"] == "AAPL"
    assert mock_fetch.call_count == 1

    # 2. Second fetch for AAPL (should be served from cache, no new yfinance call)
    data2 = get_market_data("AAPL")
    assert data2["ticker"] == "AAPL"
    assert mock_fetch.call_count == 1  # Call count remains 1!

    # 3. Fetch for MSFT (different ticker, should fetch fresh)
    mock_ticker_msft = MagicMock()
    mock_ticker_msft.ticker = "MSFT"
    mock_ticker_msft.fast_info = {"last_price": 400.0}
    mock_ticker_msft.info = {"sector": "Technology"}
    mock_ticker_msft.history.return_value = df
    mock_fetch.return_value = mock_ticker_msft

    data_msft = get_market_data("MSFT")
    assert data_msft["ticker"] == "MSFT"
    assert mock_fetch.call_count == 2
