"""
market_data.py
--------------
Fetches real-time and historical stock market data using yfinance.
Computes daily returns and annualized volatility.
Includes thread-safe in-memory TTL caching (10 minutes) for fast repeat queries.

Author  : ESG Investment Analyzer
Version : 1.1.0
"""

from __future__ import annotations

import copy
import logging
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & Cache Configuration
# ---------------------------------------------------------------------------
HISTORY_PERIOD: str = "1y"          # yfinance period string for 1 year
TRADING_DAYS_PER_YEAR: int = 252    # standard annualisation factor
CACHE_TTL_SECONDS: int = 600        # 10 minutes cache TTL

# Thread-safe in-memory cache: ticker -> (timestamp, data_dict)
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_LOCK: Lock = Lock()


def clear_cache() -> None:
    """Clear all cached market data entries."""
    with _CACHE_LOCK:
        _CACHE.clear()
        logger.info("Market data cache cleared.")


# ---------------------------------------------------------------------------
# Internal data container
# ---------------------------------------------------------------------------
@dataclass
class MarketData:
    """Strongly-typed container for all fetched and parsed market data."""

    ticker: str
    price: float
    sector: str
    historical_prices: list[dict]

    def to_dict(self) -> dict:
        """Return the canonical output dict expected by downstream modules."""
        return {
            "ticker": self.ticker,
            "price": self.price,
            "sector": self.sector,
            "historical_prices": self.historical_prices,
        }


# ---------------------------------------------------------------------------
# Step 1 — Fetch raw yfinance data
# ---------------------------------------------------------------------------
def _fetch_ticker_object(ticker: str) -> yf.Ticker:
    """Return a yfinance Ticker object for the given symbol."""
    ticker = ticker.strip().upper()
    logger.info("Initialising yfinance Ticker for '%s'", ticker)
    return yf.Ticker(ticker)


def fetch_current_price(ticker_obj: yf.Ticker) -> float:
    """
    Extract the most recent closing price.

    Tries fast_info first; falls back to the last close in trailing history.
    """
    try:
        price = ticker_obj.fast_info.get("last_price") or ticker_obj.fast_info.get("previousClose")
        if price and not np.isnan(price):
            return round(float(price), 4)
    except Exception as exc:
        logger.debug("fast_info retrieval failed for '%s': %s", getattr(ticker_obj, "ticker", "?"), exc)

    # Fallback: last close from short history window
    hist = ticker_obj.history(period="5d")
    if hist.empty or "Close" not in hist or hist["Close"].dropna().empty:
        raise ValueError(
            f"Could not retrieve current price for ticker '{getattr(ticker_obj, 'ticker', '?')}'."
        )
    return round(float(hist["Close"].dropna().iloc[-1]), 4)


def fetch_sector(ticker_obj: yf.Ticker) -> str:
    """
    Return the sector string from company info.

    Returns 'Unknown' if the field is missing or the info call fails.
    """
    try:
        info = ticker_obj.info
        if isinstance(info, dict):
            return info.get("sector") or "Unknown"
        return "Unknown"
    except Exception as exc:
        logger.warning("Could not fetch sector info: %s", exc)
        return "Unknown"


def fetch_historical_ohlcv(ticker_obj: yf.Ticker, period: str = HISTORY_PERIOD) -> pd.DataFrame:
    """
    Download OHLCV history for the requested period.

    Ensures chronological date ordering (oldest -> newest).
    """
    symbol = getattr(ticker_obj, "ticker", "?")
    logger.info("Fetching %s OHLCV history for '%s'", period, symbol)
    df = ticker_obj.history(period=period)

    if df.empty:
        raise ValueError(
            f"No historical data returned for '{symbol}' with period='{period}'."
        )

    # Handle MultiIndex columns if returned by yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Sort chronologically (oldest to newest)
    df = df.sort_index(ascending=True)

    # Normalise index to timezone-naive UTC dates
    df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Historical data for '{symbol}' missing required column '{col}'.")

    return df[required_cols].dropna(subset=["Close"])


# ---------------------------------------------------------------------------
# Step 2 — Serialise historical prices
# ---------------------------------------------------------------------------
def serialise_price_history(ohlcv_df: pd.DataFrame) -> list[dict]:
    """
    Convert OHLCV DataFrame into a JSON-serialisable list of dicts.
    """
    records = []
    for date, row in ohlcv_df.iterrows():
        records.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            }
        )
    return records


# ---------------------------------------------------------------------------
# Public API — single entry point with TTL Cache
# ---------------------------------------------------------------------------
def get_market_data(ticker: str) -> dict:
    """
    Fetch and parse all market data for a single stock ticker with TTL caching.

    Parameters
    ----------
    ticker : str
        Stock ticker symbol (case-insensitive), e.g. ``"AAPL"``.

    Returns
    -------
    dict with keys: ticker, price, sector, historical_prices.
    """
    ticker = ticker.strip().upper()
    now = time.time()

    # Check cache first
    with _CACHE_LOCK:
        if ticker in _CACHE:
            cached_time, cached_data = _CACHE[ticker]
            if now - cached_time < CACHE_TTL_SECONDS:
                logger.info("Serving market data for '%s' from TTL cache", ticker)
                return copy.deepcopy(cached_data)

    logger.info("── Starting market data fetch for '%s' ──", ticker)

    # 1. Initialise yfinance object
    ticker_obj = _fetch_ticker_object(ticker)

    # 2. Fetch raw data
    current_price = fetch_current_price(ticker_obj)
    sector = fetch_sector(ticker_obj)
    ohlcv_df = fetch_historical_ohlcv(ticker_obj)

    # 3. Serialise history
    price_history = serialise_price_history(ohlcv_df)

    # 4. Assemble result
    result = MarketData(
        ticker=ticker,
        price=current_price,
        sector=sector,
        historical_prices=price_history,
    )

    result_dict = result.to_dict()

    # Store in cache
    with _CACHE_LOCK:
        _CACHE[ticker] = (now, copy.deepcopy(result_dict))

    logger.info(
        "Done — price=%.2f  sector=%s  history=%d days",
        result.price,
        result.sector,
        len(result.historical_prices),
    )

    return result_dict


# ---------------------------------------------------------------------------
# Quick smoke-test (run directly: python market_data.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    TEST_TICKERS = ["AAPL", "TSLA", "INVALID_XYZ"]

    for sym in TEST_TICKERS:
        print(f"\n{'─' * 50}")
        print(f"  Testing ticker: {sym}")
        print("─" * 50)
        try:
            data = get_market_data(sym)
            summary = {k: v for k, v in data.items() if k != "historical_prices"}
            summary["historical_prices"] = f"[{len(data['historical_prices'])} records]"
            print(json.dumps(summary, indent=2))
        except ValueError as err:
            print(f"  ERROR: {err}")
