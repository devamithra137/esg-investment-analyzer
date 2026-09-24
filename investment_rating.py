"""
investment_rating.py
--------------------
Combines an ESG composite score and a financial risk level into a
single Investment Sustainability Rating (ISR) with a numeric score.

Decision matrix
---------------
  ESG Tier  │  Risk Level  │  Rating
  ──────────┼──────────────┼──────────────────────
  HIGH      │  LOW         │  High Sustainability
  HIGH      │  MEDIUM      │  Sustainable Growth
  MEDIUM    │  LOW         │  Sustainable Growth
  MEDIUM    │  MEDIUM      │  Sustainable Growth
  MEDIUM    │  HIGH        │  High Risk
  LOW       │  any         │  High Risk
  any       │  HIGH        │  High Risk

Author  : ESG Investment Analyzer
Version : 1.0.0
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Union

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain enums
# ---------------------------------------------------------------------------
class ESGTier(str, Enum):
    """Categorical bucket for a raw 0-100 ESG score."""
    HIGH   = "HIGH"    # score >= 70
    MEDIUM = "MEDIUM"  # score >= 40
    LOW    = "LOW"     # score <  40


class RiskLevel(str, Enum):
    """Matches the output of risk_analysis.analyse_risk()."""
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"


class Rating(str, Enum):
    """Three possible Investment Sustainability Ratings."""
    HIGH_SUSTAINABILITY = "High Sustainability"
    SUSTAINABLE_GROWTH  = "Sustainable Growth"
    HIGH_RISK           = "High Risk"


# ---------------------------------------------------------------------------
# ESG score thresholds
# ---------------------------------------------------------------------------
ESG_HIGH_THRESHOLD:   float = 70.0   # score >= 70  → HIGH ESG tier
ESG_MEDIUM_THRESHOLD: float = 40.0   # score >= 40  → MEDIUM ESG tier
                                      # score <  40  → LOW ESG tier

# ---------------------------------------------------------------------------
# Score weights
# ---------------------------------------------------------------------------
ESG_WEIGHT:  float = 0.60   # ESG score drives 60 % of investment score
RISK_WEIGHT: float = 0.40   # Risk penalty drives 40 %

# Risk-level → numeric penalty factor (higher = safer)
_RISK_SCORE_MAP: dict[RiskLevel, float] = {
    RiskLevel.LOW:    100.0,
    RiskLevel.MEDIUM:  60.0,
    RiskLevel.HIGH:    20.0,
}

# ---------------------------------------------------------------------------
# Decision matrix
# ---------------------------------------------------------------------------
# Maps (ESGTier, RiskLevel) → Rating
_DECISION_MATRIX: dict[tuple[ESGTier, RiskLevel], Rating] = {
    (ESGTier.HIGH,   RiskLevel.LOW):    Rating.HIGH_SUSTAINABILITY,
    (ESGTier.HIGH,   RiskLevel.MEDIUM): Rating.SUSTAINABLE_GROWTH,
    (ESGTier.HIGH,   RiskLevel.HIGH):   Rating.HIGH_RISK,
    (ESGTier.MEDIUM, RiskLevel.LOW):    Rating.SUSTAINABLE_GROWTH,
    (ESGTier.MEDIUM, RiskLevel.MEDIUM): Rating.SUSTAINABLE_GROWTH,
    (ESGTier.MEDIUM, RiskLevel.HIGH):   Rating.HIGH_RISK,
    (ESGTier.LOW,    RiskLevel.LOW):    Rating.HIGH_RISK,
    (ESGTier.LOW,    RiskLevel.MEDIUM): Rating.HIGH_RISK,
    (ESGTier.LOW,    RiskLevel.HIGH):   Rating.HIGH_RISK,
}


# ---------------------------------------------------------------------------
# Step 1 — Validate inputs
# ---------------------------------------------------------------------------
def _validate_esg_score(esg_score: Union[int, float]) -> float:
    """
    Coerce and range-check the ESG score.

    Parameters
    ----------
    esg_score : int | float  Must be in the closed interval [0, 100].

    Returns
    -------
    float

    Raises
    ------
    TypeError   If the value is not numeric.
    ValueError  If the value is outside [0, 100].
    """
    if not isinstance(esg_score, (int, float)):
        raise TypeError(
            f"esg_score must be a numeric value (int or float); "
            f"got {type(esg_score).__name__}."
        )
    score = float(esg_score)
    if not (0.0 <= score <= 100.0):
        raise ValueError(
            f"esg_score must be in the range [0, 100]; received {score}."
        )
    return score


def _validate_risk_level(risk_level: str) -> RiskLevel:
    """
    Coerce and validate the risk level string.

    Accepts the string values produced by risk_analysis.analyse_risk():
    ``"LOW"``, ``"MEDIUM"``, or ``"HIGH"`` (case-insensitive).

    Parameters
    ----------
    risk_level : str

    Returns
    -------
    RiskLevel

    Raises
    ------
    TypeError   If the value is not a string.
    ValueError  If the value is not a recognised risk level.
    """
    if not isinstance(risk_level, str):
        raise TypeError(
            f"risk_level must be a string; got {type(risk_level).__name__}."
        )
    try:
        return RiskLevel(risk_level.strip().upper())
    except ValueError:
        valid = [r.value for r in RiskLevel]
        raise ValueError(
            f"Unrecognised risk_level '{risk_level}'. "
            f"Valid values are: {valid}."
        )


# ---------------------------------------------------------------------------
# Step 2 — Classify ESG score into a tier
# ---------------------------------------------------------------------------
def _classify_esg(esg_score: float) -> ESGTier:
    """
    Map a numeric ESG score to a categorical tier.

    Thresholds
    ----------
    - HIGH   : score >= 70
    - MEDIUM : 40 <= score < 70
    - LOW    : score < 40

    Parameters
    ----------
    esg_score : float  Validated score in [0, 100].

    Returns
    -------
    ESGTier
    """
    if esg_score >= ESG_HIGH_THRESHOLD:
        return ESGTier.HIGH
    if esg_score >= ESG_MEDIUM_THRESHOLD:
        return ESGTier.MEDIUM
    return ESGTier.LOW


# ---------------------------------------------------------------------------
# Step 3 — Compute numeric investment score
# ---------------------------------------------------------------------------
def _compute_investment_score(esg_score: float, risk_level: RiskLevel) -> int:
    """
    Produce a single 0-100 investment score by blending the ESG score
    with a risk-derived penalty factor.

    Formula
    -------
    investment_score = (esg_score × ESG_WEIGHT) + (risk_factor × RISK_WEIGHT)

    Where risk_factor is:
    - LOW    → 100  (no penalty)
    - MEDIUM →  60  (moderate penalty)
    - HIGH   →  20  (severe penalty)

    Parameters
    ----------
    esg_score  : float
    risk_level : RiskLevel

    Returns
    -------
    int  Score clamped to [0, 100].
    """
    risk_factor = _RISK_SCORE_MAP[risk_level]
    raw_score   = (esg_score * ESG_WEIGHT) + (risk_factor * RISK_WEIGHT)
    return int(round(max(0.0, min(100.0, raw_score))))


# ---------------------------------------------------------------------------
# Step 4 — Lookup rating from decision matrix
# ---------------------------------------------------------------------------
def _lookup_rating(esg_tier: ESGTier, risk_level: RiskLevel) -> Rating:
    """
    Return the investment rating for the (ESGTier, RiskLevel) combination.

    Parameters
    ----------
    esg_tier   : ESGTier
    risk_level : RiskLevel

    Returns
    -------
    Rating
    """
    return _DECISION_MATRIX[(esg_tier, risk_level)]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_investment_rating(
    esg_score: Union[int, float],
    risk_level: str,
) -> dict:
    """
    Combine an ESG composite score and a financial risk level into a
    structured Investment Sustainability Rating.

    Parameters
    ----------
    esg_score  : int | float
        Composite ESG score in the range [0, 100].
        Typically produced by the ESG scoring engine.

    risk_level : str
        Risk classification string: ``"LOW"``, ``"MEDIUM"``, or ``"HIGH"``.
        Matches the output of ``risk_analysis.analyse_risk()``.

    Returns
    -------
    dict::

        {
            "investment_score": int,   # Blended 0-100 numeric score
            "rating":           str,   # "High Sustainability" | "Sustainable Growth" | "High Risk"
        }

    Raises
    ------
    TypeError   On invalid input types.
    ValueError  On out-of-range ESG score or unrecognised risk level.

    Examples
    --------
    >>> generate_investment_rating(85, "LOW")
    {'investment_score': 91, 'rating': 'High Sustainability'}

    >>> generate_investment_rating(55, "MEDIUM")
    {'investment_score': 57, 'rating': 'Sustainable Growth'}

    >>> generate_investment_rating(30, "HIGH")
    {'investment_score': 26, 'rating': 'High Risk'}
    """
    logger.info(
        "── Generating investment rating  |  esg_score=%s  risk_level=%s ──",
        str(esg_score),
        risk_level,
    )

    # 1. Validate
    clean_esg  = _validate_esg_score(esg_score)
    clean_risk = _validate_risk_level(risk_level)

    # 2. Classify ESG into tier
    esg_tier = _classify_esg(clean_esg)

    # 3. Compute blended numeric score
    investment_score = _compute_investment_score(clean_esg, clean_risk)

    # 4. Lookup qualitative rating
    rating = _lookup_rating(esg_tier, clean_risk)

    # 5. Consistency check: Cap investment score for High Risk ratings
    # Ensures an asset classified as "High Risk" is not assigned a misleadingly
    # high numeric score (>= 50).
    if rating == Rating.HIGH_RISK and investment_score > 49:
        investment_score = 49

    result = {
        "investment_score": investment_score,
        "rating":           rating.value,
    }

    logger.info(
        "Done  |  esg_tier=%s  investment_score=%d  rating=%s",
        esg_tier.value,
        result["investment_score"],
        result["rating"],
    )
    return result


# ---------------------------------------------------------------------------
# Smoke-test  (python investment_rating.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    test_cases: list[tuple[str, float, str]] = [
        # label                         esg   risk
        ("High ESG   + Low Risk   ",    85.0, "LOW"),
        ("High ESG   + Medium Risk",    75.0, "MEDIUM"),
        ("High ESG   + High Risk  ",    72.0, "HIGH"),
        ("Medium ESG + Low Risk   ",    60.0, "LOW"),
        ("Medium ESG + Medium Risk",    55.0, "MEDIUM"),
        ("Medium ESG + High Risk  ",    50.0, "HIGH"),
        ("Low ESG    + Low Risk   ",    35.0, "LOW"),
        ("Low ESG    + High Risk  ",    20.0, "HIGH"),
        ("Boundary   ESG = 70     ",    70.0, "LOW"),
        ("Boundary   ESG = 40     ",    40.0, "MEDIUM"),
    ]

    print(f"\n{'═' * 66}")
    print(f"  {'Scenario':<32} {'Score':>6}  {'Rating'}")
    print(f"{'═' * 66}")

    for label, esg, risk in test_cases:
        result = generate_investment_rating(esg, risk)
        print(
            f"  {label:<32} {result['investment_score']:>6}  {result['rating']}"
        )

    print(f"{'═' * 66}")

    # ── Error paths ──────────────────────────────────────────────────────
    print("\n── Error cases ──────────────────────────────────────────────")
    errors = [
        ("ESG score out of range",   (150.0,  "LOW")),
        ("ESG score negative",       (-5.0,   "MEDIUM")),
        ("Invalid risk level",       (70.0,   "EXTREME")),
        ("Wrong ESG type",           ("high", "LOW")),
    ]
    for label, (esg, risk) in errors:
        try:
            generate_investment_rating(esg, risk)
        except (TypeError, ValueError) as exc:
            print(f"  ✓ [{label}] {type(exc).__name__}: {exc}")
