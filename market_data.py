"""
market_data.py
--------------
Fetches real-time and historical stock market data using yfinance.
Computes daily returns and annualized volatility.

Author  : ESG Investment Analyzer
Version : 1.0.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
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
# Constants
# ---------------------------------------------------------------------------
HISTORY_PERIOD: str = "1y"          # yfinance period string for 1 year
TRADING_DAYS_PER_YEAR: int = 252    # standard annualisation factor


# ---------------------------------------------------------------------------
# Internal data container
# ---------------------------------------------------------------------------
@dataclass
class MarketData:
    """Strongly-typed container for all fetched and computed market data."""

    ticker: str
    price: float
    volatility: float
    sector: str
    historical_prices: list[dict]
    daily_returns: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return the canonical output dict expected by downstream modules."""
        return {
            "ticker": self.ticker,
            "price": self.price,
            "volatility": self.volatility,
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

    Tries the fast_info shortcut first; falls back to the last close
    in the trailing 5-day history if fast_info is unavailable.

    Returns
    -------
    float
        Latest available price, rounded to 4 decimal places.

    Raises
    ------
    ValueError
        If no price can be determined.
    """
    try:
        price = ticker_obj.fast_info.get("last_price") or ticker_obj.fast_info.get("previousClose")
        if price:
            return round(float(price), 4)
    except Exception:
        pass

    # Fallback: last close from short history window
    hist = ticker_obj.history(period="5d")
    if hist.empty:
        raise ValueError(
            f"Could not retrieve current price for ticker '{ticker_obj.ticker}'."
        )
    return round(float(hist["Close"].iloc[-1]), 4)


def fetch_sector(ticker_obj: yf.Ticker) -> str:
    """
    Return the sector string from company info.

    Returns 'Unknown' if the field is missing or the info call fails.
    """
    try:
        info = ticker_obj.info
        return info.get("sector") or "Unknown"
    except Exception as exc:
        logger.warning("Could not fetch sector info: %s", exc)
        return "Unknown"


def fetch_historical_ohlcv(ticker_obj: yf.Ticker, period: str = HISTORY_PERIOD) -> pd.DataFrame:
    """
    Download OHLCV history for the requested period.

    Parameters
    ----------
    ticker_obj : yf.Ticker
    period     : str  yfinance period string, e.g. '1y', '6mo'

    Returns
    -------
    pd.DataFrame
        DataFrame with columns [Open, High, Low, Close, Volume].
        Index is a timezone-naive DatetimeIndex (UTC dates).

    Raises
    ------
    ValueError
        If the returned DataFrame is empty.
    """
    logger.info("Fetching %s OHLCV history for '%s'", period, ticker_obj.ticker)
    df = ticker_obj.history(period=period)

    if df.empty:
        raise ValueError(
            f"No historical data returned for '{ticker_obj.ticker}' "
            f"with period='{period}'."
        )

    # Normalise index to timezone-naive UTC dates
    df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
    return df[["Open", "High", "Low", "Close", "Volume"]]


# ---------------------------------------------------------------------------
# Step 2 — Compute derived metrics
# ---------------------------------------------------------------------------
def compute_daily_returns(close_series: pd.Series) -> pd.Series:
    """
    Calculate percentage daily returns from a closing price series.

    Uses log returns (ln(P_t / P_{t-1})) which are additive over time
    and better suited for volatility estimation than simple returns.

    Parameters
    ----------
    close_series : pd.Series  Closing prices, chronologically ordered.

    Returns
    -------
    pd.Series  Log returns, NaN-dropped.
    """
    log_returns = np.log(close_series / close_series.shift(1))
    return log_returns.dropna()


def compute_annualized_volatility(
    daily_returns: pd.Series,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """
    Compute annualized historical volatility (σ) from daily log returns.

    Formula: σ_annual = σ_daily × √(trading_days)

    Parameters
    ----------
    daily_returns : pd.Series
    trading_days  : int  Defaults to 252 (NYSE standard).

    Returns
    -------
    float  Annualized volatility rounded to 4 decimal places.
    """
    if daily_returns.empty:
        logger.warning("Empty returns series — volatility defaulting to 0.0")
        return 0.0

    daily_std = float(np.std(daily_returns, ddof=1))
    annualized = daily_std * np.sqrt(trading_days)
    return round(annualized, 4)


# ---------------------------------------------------------------------------
# Step 3 — Serialise historical prices
# ---------------------------------------------------------------------------
def serialise_price_history(ohlcv_df: pd.DataFrame) -> list[dict]:
    """
    Convert OHLCV DataFrame into a JSON-serialisable list of dicts.

    Each record has the shape::

        {
            "date":   "2024-01-15",
            "open":   183.92,
            "high":   185.10,
            "low":    182.73,
            "close":  184.40,
            "volume": 67_432_100
        }

    Parameters
    ----------
    ohlcv_df : pd.DataFrame  Output of fetch_historical_ohlcv().

    Returns
    -------
    list[dict]
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
# Public API — single entry point
# ---------------------------------------------------------------------------
def get_market_data(ticker: str) -> dict:
    """
    Fetch and compute all market data for a single stock ticker.

    This is the primary public interface for this module.

    Parameters
    ----------
    ticker : str
        Stock ticker symbol (case-insensitive), e.g. ``"AAPL"``.

    Returns
    -------
    dict with the following keys:

    .. code-block:: python

        {
            "ticker":            str,   # Normalised uppercase ticker
            "price":             float, # Latest available closing price
            "volatility":        float, # Annualised historical volatility (σ)
            "sector":            str,   # GICS sector or "Unknown"
            "historical_prices": list,  # 1-year OHLCV records
        }

    Raises
    ------
    ValueError
        If the ticker is invalid or data cannot be retrieved.
    """
    ticker = ticker.strip().upper()
    logger.info("── Starting market data fetch for '%s' ──", ticker)

    # 1. Initialise yfinance object
    ticker_obj = _fetch_ticker_object(ticker)

    # 2. Fetch raw data
    current_price = fetch_current_price(ticker_obj)
    sector = fetch_sector(ticker_obj)
    ohlcv_df = fetch_historical_ohlcv(ticker_obj)

    # 3. Compute derived metrics
    daily_returns = compute_daily_returns(ohlcv_df["Close"])
    volatility = compute_annualized_volatility(daily_returns)

    # 4. Serialise history
    price_history = serialise_price_history(ohlcv_df)

    # 5. Assemble result
    result = MarketData(
        ticker=ticker,
        price=current_price,
        volatility=volatility,
        sector=sector,
        historical_prices=price_history,
        daily_returns=daily_returns.tolist(),
    )

    logger.info(
        "Done — price=%.2f  volatility=%.4f  sector=%s  history=%d days",
        result.price,
        result.volatility,
        result.sector,
        len(result.historical_prices),
    )

    return result.to_dict()


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
            # Print summary without flooding the terminal with 252 price rows
            summary = {k: v for k, v in data.items() if k != "historical_prices"}
            summary["historical_prices"] = f"[{len(data['historical_prices'])} records]"
            print(json.dumps(summary, indent=2))
        except ValueError as err:
            print(f"  ERROR: {err}")
