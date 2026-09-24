"""
risk_analysis.py
----------------
Analyses financial risk from a historical price series.
Computes daily log returns, annualised volatility, and classifies
risk into three tiers: LOW / MEDIUM / HIGH.

Author  : ESG Investment Analyzer
Version : 1.0.0
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Union

import numpy as np
import pandas as pd

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
TRADING_DAYS_PER_YEAR: int = 252   # NYSE / NASDAQ standard annualisation factor
MIN_OBSERVATIONS: int = 2          # Minimum prices needed to compute one return


# ---------------------------------------------------------------------------
# Risk classification — enum + threshold table
# ---------------------------------------------------------------------------
class RiskLevel(str, Enum):
    """
    Three-tier risk classification.
    Inherits from str so values serialise directly to JSON.
    """
    LOW    = "LOW"      # σ < 0.20  — stable blue-chips, utilities
    MEDIUM = "MEDIUM"   # 0.20 ≤ σ < 0.40  — typical large-cap equities
    HIGH   = "HIGH"     # σ ≥ 0.40  — small-caps, speculative assets


# Ordered table: (upper_bound_exclusive, label)
# Add or adjust tiers here without touching any other function.
_RISK_THRESHOLDS: list[tuple[float, RiskLevel]] = [
    (0.20, RiskLevel.LOW),
    (0.40, RiskLevel.MEDIUM),
    (float("inf"), RiskLevel.HIGH),
]


# ---------------------------------------------------------------------------
# Step 1 — Input validation & normalisation
# ---------------------------------------------------------------------------
def _validate_prices(prices: list[Union[int, float]]) -> pd.Series:
    """
    Validate and coerce the raw price list to a clean float Series.

    Validations
    -----------
    - Must be a non-empty list or 1-D array-like (not a string / dict).
    - After dropping NaN, must have >= MIN_OBSERVATIONS values.
    - All values must be strictly positive.

    Parameters
    ----------
    prices : list[int | float]

    Returns
    -------
    pd.Series  Clean, reset-indexed float series.

    Raises
    ------
    TypeError   If the input is not iterable or has the wrong shape.
    ValueError  If the series is too short or contains non-positive values.
    """
    if not hasattr(prices, "__iter__") or isinstance(prices, (str, dict)):
        raise TypeError(
            f"Expected a list or array-like of numeric prices, "
            f"got {type(prices).__name__}."
        )

    series = pd.Series(prices, dtype=float).dropna().reset_index(drop=True)

    if len(series) < MIN_OBSERVATIONS:
        raise ValueError(
            f"At least {MIN_OBSERVATIONS} valid price observations are required; "
            f"received {len(series)}."
        )

    if np.isinf(series).any():
        raise ValueError("Price series contains infinite values.")

    non_positive = series[series <= 0]
    if not non_positive.empty:
        raise ValueError(
            f"All prices must be strictly positive. "
            f"Non-positive values found at indices {non_positive.index.tolist()}: "
            f"{non_positive.tolist()}"
        )

    return series


# ---------------------------------------------------------------------------
# Step 2 — Daily log returns
# ---------------------------------------------------------------------------
def compute_daily_returns(prices: pd.Series) -> pd.Series:
    """
    Compute daily log returns from a validated price series.

    Log returns are chosen over simple returns because they are:
    - Time-additive   (multi-period return = sum of daily log returns)
    - Symmetric       (equal magnitude up/down moves → equal |return|)
    - Statistically better suited for volatility estimation

    Formula: r_t = ln(P_t / P_{t-1})

    Parameters
    ----------
    prices : pd.Series  Validated, strictly positive closing prices.

    Returns
    -------
    pd.Series  Log return series (len = len(prices) - 1).
    """
    log_returns = np.log(prices / prices.shift(1)).dropna()
    logger.debug("Computed %d daily log returns.", len(log_returns))
    return log_returns


# ---------------------------------------------------------------------------
# Step 3 — Annualised volatility
# ---------------------------------------------------------------------------
def compute_volatility(
    daily_returns: pd.Series,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """
    Annualise the standard deviation of daily log returns.

    Formula: σ_annual = σ_daily × √trading_days

    Uses ddof=1 (unbiased / sample std dev), which is standard for
    any finite observation window in financial time-series analysis.

    Parameters
    ----------
    daily_returns : pd.Series
    trading_days  : int  Annualisation factor (default 252).

    Returns
    -------
    float  Annualised volatility, rounded to 6 decimal places.
    """
    if daily_returns.empty:
        logger.warning("Empty returns series — volatility defaulting to 0.0")
        return 0.0

    sigma_daily  = float(np.std(daily_returns, ddof=1))
    sigma_annual = sigma_daily * np.sqrt(trading_days)
    return round(sigma_annual, 6)


# ---------------------------------------------------------------------------
# Step 4 — Risk classification
# ---------------------------------------------------------------------------
def classify_risk(volatility: float) -> RiskLevel:
    """
    Map annualised volatility to a discrete risk tier.

    Thresholds
    ----------
    - LOW    : σ < 0.20
    - MEDIUM : 0.20 ≤ σ < 0.40
    - HIGH   : σ ≥ 0.40

    Parameters
    ----------
    volatility : float  Must be ≥ 0.

    Returns
    -------
    RiskLevel

    Raises
    ------
    ValueError  If volatility is negative.
    """
    if volatility < 0:
        raise ValueError(
            f"Volatility must be non-negative; received {volatility}."
        )

    for upper_bound, level in _RISK_THRESHOLDS:
        if volatility < upper_bound:
            return level

    return RiskLevel.HIGH  # safety fallback; logically unreachable


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def analyse_risk(prices: list[Union[int, float]]) -> dict:
    """
    Full risk-analysis pipeline for a historical price series.

    Parameters
    ----------
    prices : list[int | float]
        Ordered sequence of historical closing prices (oldest → newest).
        Accepts any numeric 1-D sequence: list, tuple, or numpy array.

    Returns
    -------
    dict::

        {
            "volatility": float,   # Annualised σ, e.g. 0.28
            "risk_level": str,     # "LOW" | "MEDIUM" | "HIGH"
        }

    Raises
    ------
    TypeError   On invalid input type.
    ValueError  On insufficient or non-positive price data.

    Examples
    --------
    >>> analyse_risk([100, 101.5, 99.8, 102.3, 100.9])
    {'volatility': ..., 'risk_level': 'LOW'}
    """
    logger.info(
        "── Starting risk analysis  |  %d price observations ──",
        len(prices) if hasattr(prices, "__len__") else "?",
    )

    clean_prices  = _validate_prices(prices)             # 1. validate
    daily_returns = compute_daily_returns(clean_prices)  # 2. returns
    volatility    = compute_volatility(daily_returns)    # 3. volatility
    risk_level    = classify_risk(volatility)            # 4. classify

    result = {
        "volatility": round(volatility, 4),
        "risk_level": risk_level.value,
    }

    logger.info(
        "Done  |  volatility=%.4f  risk_level=%s",
        result["volatility"],
        result["risk_level"],
    )
    return result


# ---------------------------------------------------------------------------
# Smoke-test  (python risk_analysis.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    import random

    random.seed(42)

    def _gbm_prices(start: float, n: int, daily_vol: float) -> list[float]:
        """Simulate a Geometric Brownian Motion price series."""
        px = [start]
        for _ in range(n - 1):
            px.append(round(px[-1] * np.exp(random.gauss(0, daily_vol)), 4))
        return px

    scenarios: list[tuple[str, list]] = [
        ("LOW    — σ_daily ≈ 0.8 %",  _gbm_prices(100, 252, 0.008)),
        ("MEDIUM — σ_daily ≈ 1.6 %",  _gbm_prices(100, 252, 0.016)),
        ("HIGH   — σ_daily ≈ 3.2 %",  _gbm_prices(100, 252, 0.032)),
        ("Edge   — only 3 prices",     [100.0, 98.5, 101.2]),
    ]

    for label, px in scenarios:
        print(f"\n{'─' * 54}")
        print(f"  {label}  ({len(px)} obs)")
        print("─" * 54)
        print(json.dumps(analyse_risk(px), indent=2))

    # ── Error paths ──────────────────────────────────────────────────────
    error_cases: list[tuple[str, object]] = [
        ("Single price",    [150.0]),
        ("Negative price",  [100.0, -5.0, 102.0]),
        ("Wrong type",      "AAPL"),
    ]

    for label, bad_input in error_cases:
        print(f"\n{'─' * 54}")
        print(f"  Error case: {label}")
        print("─" * 54)
        try:
            analyse_risk(bad_input)
        except (TypeError, ValueError) as exc:
            print(f"  Caught {type(exc).__name__}: {exc}")
