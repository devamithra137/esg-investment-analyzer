"""
tests/test_esg_scoring.py
--------------------------
Unit tests for the centralized ESG scoring engine (esg_scoring.py).
"""

import pytest
from esg_scoring import (
    compute_esg_composite,
    compute_esg_score,
    get_esg_scores,
    simulate_esg_scores,
    WEIGHT_ENVIRONMENT,
    WEIGHT_GOVERNANCE,
    WEIGHT_SOCIAL,
)


def test_esg_weights_sum_to_one():
    """Verify that composite ESG weights sum to 1.0."""
    total_weight = WEIGHT_ENVIRONMENT + WEIGHT_SOCIAL + WEIGHT_GOVERNANCE
    assert pytest.approx(total_weight, 1e-6) == 1.0


def test_compute_esg_score_valid():
    """Test composite score calculation formula with known values."""
    # (80 * 0.40) + (70 * 0.30) + (60 * 0.30) = 32 + 21 + 18 = 71.0
    score = compute_esg_score(80.0, 70.0, 60.0)
    assert score == 71.0


def test_compute_esg_composite_alias():
    """Verify compute_esg_composite function alias."""
    assert compute_esg_composite(80.0, 70.0, 60.0) == 71.0


def test_compute_esg_score_clamping_and_rounding():
    """Test rounding to 2 decimal places and clamping within [0, 100]."""
    score = compute_esg_score(85.333, 72.111, 90.999)
    # (85.333 * 0.4) + (72.111 * 0.3) + (90.999 * 0.3) = 34.1332 + 21.6333 + 27.2997 = 83.0662 -> 83.07
    assert score == round((85.333 * 0.4) + (72.111 * 0.3) + (90.999 * 0.3), 2)


def test_compute_esg_score_out_of_bounds_raises_value_error():
    """Verify ValueError when any sub-score is outside [0, 100]."""
    with pytest.raises(ValueError, match="Sub-score 'environment' must be in"):
        compute_esg_score(-5.0, 70.0, 70.0)

    with pytest.raises(ValueError, match="Sub-score 'social' must be in"):
        compute_esg_score(70.0, 105.0, 70.0)

    with pytest.raises(ValueError, match="Sub-score 'governance' must be in"):
        compute_esg_score(70.0, 70.0, 150.0)


def test_simulate_esg_scores_determinism():
    """Verify that the same ticker produces identical sub-scores across calls."""
    res1 = simulate_esg_scores("AAPL", "Technology")
    res2 = simulate_esg_scores("AAPL", "Technology")
    assert res1 == res2


def test_simulate_esg_scores_different_tickers():
    """Verify that different tickers produce distinct deterministic scores."""
    res_aapl = simulate_esg_scores("AAPL", "Technology")
    res_msft = simulate_esg_scores("MSFT", "Technology")
    assert res_aapl != res_msft


def test_simulate_esg_scores_bounds():
    """Verify sub-scores remain strictly within [0, 100]."""
    for ticker in ["AAPL", "TSLA", "XOM", "JPM", "UNKNOWN_SYM"]:
        scores = simulate_esg_scores(ticker, "Technology")
        for key in ["environment", "social", "governance"]:
            assert 0.0 <= scores[key] <= 100.0


def test_get_esg_scores_public_api():
    """Test get_esg_scores return dictionary payload structure."""
    result = get_esg_scores("AAPL", "Technology")
    assert "environment" in result
    assert "social" in result
    assert "governance" in result
    assert "esg_score" in result
    assert result["ticker"] == "AAPL"


def test_get_esg_scores_unknown_sector_fallback():
    """Verify smooth fallback when sector is unknown or missing."""
    result = get_esg_scores("XYZ", "NonExistentSector")
    assert 0.0 <= result["esg_score"] <= 100.0
