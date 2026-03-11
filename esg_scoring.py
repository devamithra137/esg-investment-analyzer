"""
esg_scoring.py
--------------
Generates realistic ESG sub-scores and computes a weighted
composite ESG score for a given stock ticker.

Scoring formula
---------------
    ESG = (Environment × 0.40) + (Social × 0.30) + (Governance × 0.30)

Sub-score range : 50 – 95  (realistic institutional ESG band)
Composite range : 0  – 100 (clamped)

Author  : ESG Investment Analyzer
Version : 1.0.0
"""

from __future__ import annotations

import hashlib
import logging
import random
from dataclasses import asdict, dataclass
from typing import Optional

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
SCORE_MIN: float = 50.0
SCORE_MAX: float = 95.0

# Composite weighting — must sum to 1.0
WEIGHT_ENVIRONMENT: float = 0.40
WEIGHT_SOCIAL:      float = 0.30
WEIGHT_GOVERNANCE:  float = 0.30

# Sanity check at import time
assert abs((WEIGHT_ENVIRONMENT + WEIGHT_SOCIAL + WEIGHT_GOVERNANCE) - 1.0) < 1e-9, \
    "ESG weights must sum to 1.0"


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------
@dataclass
class ESGMetrics:
    """
    Typed container for all ESG sub-scores and the composite.

    Attributes
    ----------
    environment  : float  Environmental sub-score  (0 – 100)
    social       : float  Social sub-score          (0 – 100)
    governance   : float  Governance sub-score      (0 – 100)
    esg_score    : float  Weighted composite score  (0 – 100)
    ticker       : str    Associated ticker symbol (optional)
    """
    environment: float
    social:      float
    governance:  float
    esg_score:   float
    ticker:      str = ""

    def to_dict(self) -> dict:
        """
        Return the canonical output dict.

        The ``ticker`` field is omitted when empty to keep the
        response payload clean for callers that do not pass one.
        """
        base = {
            "environment": self.environment,
            "social":      self.social,
            "governance":  self.governance,
            "esg_score":   self.esg_score,
        }
        if self.ticker:
            base["ticker"] = self.ticker
        return base


# ---------------------------------------------------------------------------
# Step 1 — Sub-score generation
# ---------------------------------------------------------------------------
def _ticker_seed(ticker: str) -> int:
    """
    Derive a stable integer seed from a ticker string via MD5.

    Using a deterministic hash means the same ticker always produces
    the same ESG scores within a session (or across restarts), making
    results reproducible for tests and demos.

    Parameters
    ----------
    ticker : str  Uppercase ticker symbol.

    Returns
    -------
    int  Seed value suitable for ``random.seed()``.
    """
    digest = hashlib.md5(ticker.encode()).hexdigest()
    return int(digest[:12], 16)


def generate_environment_score(rng: random.Random) -> float:
    """
    Generate a realistic Environmental sub-score in [SCORE_MIN, SCORE_MAX].

    Environmental metrics proxy: carbon emissions intensity, renewable
    energy usage, waste management, water stewardship, biodiversity impact.

    Parameters
    ----------
    rng : random.Random  Caller-supplied RNG for reproducibility.

    Returns
    -------
    float  Score rounded to 2 decimal places.
    """
    return round(rng.uniform(SCORE_MIN, SCORE_MAX), 2)


def generate_social_score(rng: random.Random) -> float:
    """
    Generate a realistic Social sub-score in [SCORE_MIN, SCORE_MAX].

    Social metrics proxy: labour standards, supply chain human rights,
    community engagement, product safety, diversity and inclusion.

    Parameters
    ----------
    rng : random.Random  Caller-supplied RNG for reproducibility.

    Returns
    -------
    float  Score rounded to 2 decimal places.
    """
    return round(rng.uniform(SCORE_MIN, SCORE_MAX), 2)


def generate_governance_score(rng: random.Random) -> float:
    """
    Generate a realistic Governance sub-score in [SCORE_MIN, SCORE_MAX].

    Governance metrics proxy: board independence, executive pay alignment,
    audit quality, shareholder rights, anti-corruption policies.

    Parameters
    ----------
    rng : random.Random  Caller-supplied RNG for reproducibility.

    Returns
    -------
    float  Score rounded to 2 decimal places.
    """
    return round(rng.uniform(SCORE_MIN, SCORE_MAX), 2)


# ---------------------------------------------------------------------------
# Step 2 — Composite score
# ---------------------------------------------------------------------------
def compute_esg_score(
    environment: float,
    social:      float,
    governance:  float,
) -> float:
    """
    Compute the weighted composite ESG score.

    Formula
    -------
    ESG = (Environment × 0.40) + (Social × 0.30) + (Governance × 0.30)

    Parameters
    ----------
    environment : float  Environmental sub-score (0 – 100).
    social      : float  Social sub-score         (0 – 100).
    governance  : float  Governance sub-score     (0 – 100).

    Returns
    -------
    float  Composite score clamped to [0, 100], rounded to 2 d.p.

    Raises
    ------
    ValueError  If any sub-score is outside [0, 100].
    """
    for name, val in (("environment", environment),
                      ("social",      social),
                      ("governance",  governance)):
        if not (0.0 <= val <= 100.0):
            raise ValueError(
                f"Sub-score '{name}' must be in [0, 100]; received {val}."
            )

    raw = (
        environment * WEIGHT_ENVIRONMENT
        + social    * WEIGHT_SOCIAL
        + governance * WEIGHT_GOVERNANCE
    )
    return round(max(0.0, min(100.0, raw)), 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_esg_scores(ticker: Optional[str] = None) -> dict:
    """
    Generate ESG sub-scores and compute the composite for a given ticker.

    When a ``ticker`` is supplied the scores are seeded deterministically
    so that repeated calls for the same symbol return identical results.
    When no ticker is provided, a fresh random seed is used each call.

    Parameters
    ----------
    ticker : str, optional
        Stock ticker symbol (case-insensitive), e.g. ``"AAPL"``.
        Pass ``None`` for a fully random (non-reproducible) result.

    Returns
    -------
    dict::

        {
            "environment": float,   # Environmental score  (50 – 95)
            "social":      float,   # Social score          (50 – 95)
            "governance":  float,   # Governance score      (50 – 95)
            "esg_score":   float,   # Weighted composite    (50 – 95+)
        }

    Examples
    --------
    >>> result = get_esg_scores("AAPL")
    >>> 50 <= result["environment"] <= 95
    True
    >>> result = get_esg_scores()
    >>> "esg_score" in result
    True
    """
    # Build a seeded (or random) RNG
    if ticker:
        ticker = ticker.strip().upper()
        seed   = _ticker_seed(ticker)
        logger.info("Generating ESG scores for '%s' (seed=%d)", ticker, seed)
    else:
        seed   = None
        logger.info("Generating ESG scores (unseeded / random)")

    rng = random.Random(seed)

    # Generate sub-scores
    env_score = generate_environment_score(rng)
    soc_score = generate_social_score(rng)
    gov_score = generate_governance_score(rng)

    # Compute composite
    esg_composite = compute_esg_score(env_score, soc_score, gov_score)

    metrics = ESGMetrics(
        environment = env_score,
        social      = soc_score,
        governance  = gov_score,
        esg_score   = esg_composite,
        ticker      = ticker or "",
    )

    logger.info(
        "ESG  E=%.2f  S=%.2f  G=%.2f  composite=%.2f",
        env_score, soc_score, gov_score, esg_composite,
    )

    return metrics.to_dict()


# ---------------------------------------------------------------------------
# Smoke-test  (python esg_scoring.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    # ── Reproducibility test ──────────────────────────────────────────────
    print("\n── Deterministic (same ticker → same scores) ─────────────────")
    for _ in range(3):
        result = get_esg_scores("AAPL")
        print(json.dumps(result, indent=2))

    # ── Various tickers ───────────────────────────────────────────────────
    print("\n── Multiple tickers ──────────────────────────────────────────")
    for sym in ["TSLA", "MSFT", "NVDA", "JPM", "XOM"]:
        r = get_esg_scores(sym)
        print(
            f"  {sym:<5}  E={r['environment']:5.1f}  "
            f"S={r['social']:5.1f}  G={r['governance']:5.1f}  "
            f"ESG={r['esg_score']:5.1f}"
        )

    # ── Random (no ticker) ────────────────────────────────────────────────
    print("\n── Random scores (no ticker) ────────────────────────────────")
    for i in range(3):
        r = get_esg_scores()
        print(
            f"  run {i+1}  E={r['environment']:5.1f}  "
            f"S={r['social']:5.1f}  G={r['governance']:5.1f}  "
            f"ESG={r['esg_score']:5.1f}"
        )

    # ── Weight validation ─────────────────────────────────────────────────
    print("\n── Weight check ─────────────────────────────────────────────")
    manual = compute_esg_score(80.0, 65.0, 75.0)
    expected = round((80 * 0.4) + (65 * 0.3) + (75 * 0.3), 2)
    print(f"  compute_esg_score(80, 65, 75) = {manual}")
    print(f"  Expected (80×0.4 + 65×0.3 + 75×0.3) = {expected}")
    assert manual == expected, "Weight formula mismatch!"
    print("  ✓ Formula verified")
