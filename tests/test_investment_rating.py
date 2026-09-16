"""
tests/test_investment_rating.py
--------------------------------
Unit tests for the investment rating decision engine (investment_rating.py).
"""

import pytest
from investment_rating import (
    generate_investment_rating,
    Rating,
    RiskLevel,
    ESGTier,
    _classify_esg,
    _validate_esg_score,
    _validate_risk_level,
)


def test_classify_esg_tiers():
    """Verify ESG score classification thresholds (HIGH >= 70, MEDIUM >= 40, LOW < 40)."""
    assert _classify_esg(85.0) == ESGTier.HIGH
    assert _classify_esg(70.0) == ESGTier.HIGH
    assert _classify_esg(69.9) == ESGTier.MEDIUM
    assert _classify_esg(40.0) == ESGTier.MEDIUM
    assert _classify_esg(39.9) == ESGTier.LOW
    assert _classify_esg(0.0) == ESGTier.LOW


@pytest.mark.parametrize(
    "esg_score, risk_level, expected_rating, max_expected_score",
    [
        # 9 Decision Matrix Grid Combinations
        (85.0, "LOW",    "High Sustainability", 100),
        (75.0, "MEDIUM", "Sustainable Growth",  100),
        (72.0, "HIGH",   "High Risk",           49),   # High Risk score capped at 49
        (60.0, "LOW",    "Sustainable Growth",  100),
        (55.0, "MEDIUM", "Sustainable Growth",  100),
        (50.0, "HIGH",   "High Risk",           49),   # High Risk score capped at 49
        (35.0, "LOW",    "High Risk",           49),   # High Risk score capped at 49
        (30.0, "MEDIUM", "High Risk",           49),   # High Risk score capped at 49
        (20.0, "HIGH",   "High Risk",           49),   # High Risk score capped at 49
    ],
)
def test_decision_matrix_grid(esg_score, risk_level, expected_rating, max_expected_score):
    """Test all 9 ESG x Risk decision matrix combinations."""
    result = generate_investment_rating(esg_score, risk_level)
    assert result["rating"] == expected_rating
    assert result["investment_score"] <= max_expected_score


def test_high_risk_rating_consistency_cap():
    """Explicitly verify that High Risk ratings cap the numerical score at 49."""
    # ESG 90 (High) + Risk HIGH -> would produce raw score 62, but rating is High Risk
    result = generate_investment_rating(90.0, "HIGH")
    assert result["rating"] == "High Risk"
    assert result["investment_score"] == 49


def test_validate_esg_score_inputs():
    """Verify ESG score validation for invalid types and out-of-range values."""
    assert _validate_esg_score(75) == 75.0
    assert _validate_esg_score(75.5) == 75.5

    with pytest.raises(TypeError, match="esg_score must be a numeric value"):
        generate_investment_rating("HIGH_SCORE", "LOW")

    with pytest.raises(ValueError, match="esg_score must be in the range"):
        generate_investment_rating(150.0, "LOW")

    with pytest.raises(ValueError, match="esg_score must be in the range"):
        generate_investment_rating(-10.0, "MEDIUM")


def test_validate_risk_level_inputs():
    """Verify risk level validation for case-insensitivity, invalid strings, and bad types."""
    assert _validate_risk_level("low") == RiskLevel.LOW
    assert _validate_risk_level("  MEDIUM ") == RiskLevel.MEDIUM
    assert _validate_risk_level("HIGH") == RiskLevel.HIGH

    with pytest.raises(TypeError, match="risk_level must be a string"):
        generate_investment_rating(75.0, 123)

    with pytest.raises(ValueError, match="Unrecognised risk_level 'EXTREME'"):
        generate_investment_rating(75.0, "EXTREME")
