"""
tests/test_risk_analysis.py
----------------------------
Unit tests for the financial risk analysis module (risk_analysis.py).
"""

import numpy as np
import pandas as pd
import pytest
from risk_analysis import (
    analyse_risk,
    classify_risk,
    compute_daily_returns,
    compute_volatility,
    RiskLevel,
    TRADING_DAYS_PER_YEAR,
)


def test_compute_daily_returns_math():
    """Verify log return calculation ln(P_t / P_{t-1})."""
    prices = pd.Series([100.0, 110.0, 104.5])
    returns = compute_daily_returns(prices)

    expected_r1 = np.log(110.0 / 100.0)
    expected_r2 = np.log(104.5 / 110.0)

    assert len(returns) == 2
    assert returns.iloc[0] == pytest.approx(expected_r1, 1e-6)
    assert returns.iloc[1] == pytest.approx(expected_r2, 1e-6)


def test_compute_volatility_zero_for_constant_prices():
    """Verify zero volatility for constant price series."""
    prices = pd.Series([100.0, 100.0, 100.0, 100.0])
    returns = compute_daily_returns(prices)
    vol = compute_volatility(returns)
    assert vol == 0.0


def test_compute_volatility_annualization_scaling():
    """Verify annualization scaling by sqrt(252)."""
    returns = pd.Series([0.01, -0.01, 0.015, -0.005, 0.02])
    daily_std = np.std(returns, ddof=1)
    expected_annual = round(float(daily_std * np.sqrt(TRADING_DAYS_PER_YEAR)), 6)

    vol = compute_volatility(returns, trading_days=252)
    assert vol == expected_annual


def test_classify_risk_tiers():
    """Test risk classification thresholds (LOW < 0.20, MEDIUM 0.20-0.40, HIGH >= 0.40)."""
    assert classify_risk(0.15) == RiskLevel.LOW
    assert classify_risk(0.1999) == RiskLevel.LOW
    assert classify_risk(0.20) == RiskLevel.MEDIUM
    assert classify_risk(0.35) == RiskLevel.MEDIUM
    assert classify_risk(0.3999) == RiskLevel.MEDIUM
    assert classify_risk(0.40) == RiskLevel.HIGH
    assert classify_risk(0.85) == RiskLevel.HIGH


def test_classify_risk_negative_volatility_raises_error():
    """Verify ValueError when volatility is negative."""
    with pytest.raises(ValueError, match="Volatility must be non-negative"):
        classify_risk(-0.05)


def test_analyse_risk_pipeline():
    """Test full analyse_risk pipeline end-to-end on simulated GBM prices."""
    prices = [100.0, 101.5, 99.8, 102.3, 101.1, 103.0, 102.5]
    result = analyse_risk(prices)

    assert "volatility" in result
    assert "risk_level" in result
    assert isinstance(result["volatility"], float)
    assert result["risk_level"] in ["LOW", "MEDIUM", "HIGH"]


def test_analyse_risk_insufficient_prices_raises_error():
    """Verify ValueError when fewer than 2 price observations are provided."""
    with pytest.raises(ValueError, match="valid price observations are required"):
        analyse_risk([100.0])

    with pytest.raises(ValueError, match="valid price observations are required"):
        analyse_risk([])


def test_analyse_risk_non_positive_prices_raises_error():
    """Verify ValueError when price series contains zero or negative values."""
    with pytest.raises(ValueError, match="All prices must be strictly positive"):
        analyse_risk([100.0, 0.0, 102.0])

    with pytest.raises(ValueError, match="All prices must be strictly positive"):
        analyse_risk([100.0, -15.5, 102.0])


def test_analyse_risk_invalid_types_raises_error():
    """Verify TypeError for non-iterable or invalid input types."""
    with pytest.raises(TypeError, match="Expected a list or array-like"):
        analyse_risk("AAPL")

    with pytest.raises(TypeError, match="Expected a list or array-like"):
        analyse_risk({"price": 100})


def test_analyse_risk_infinite_prices_raises_error():
    """Verify ValueError when price series contains infinite values."""
    with pytest.raises(ValueError, match="infinite values"):
        analyse_risk([100.0, float("inf"), 102.0])

    with pytest.raises(ValueError, match="infinite values"):
        analyse_risk([100.0, float("-inf"), 102.0])
