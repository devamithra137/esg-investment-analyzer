"""
esg_scoring.py
--------------
Generates realistic ESG sub-scores and computes a weighted
composite ESG score for a given stock ticker and sector.

Scoring formula
---------------
    ESG = (Environment × 0.40) + (Social × 0.30) + (Governance × 0.30)

Sub-score range : 0 – 100
Composite range : 0 – 100 (clamped)

Author  : ESG Investment Analyzer
Version : 1.1.0
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

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
SCORE_MIN: float = 0.0
SCORE_MAX: float = 100.0

# Composite weighting — must sum to 1.0
WEIGHT_ENVIRONMENT: float = 0.40
WEIGHT_SOCIAL:      float = 0.30
WEIGHT_GOVERNANCE:  float = 0.30

# Sanity check at import time
assert abs((WEIGHT_ENVIRONMENT + WEIGHT_SOCIAL + WEIGHT_GOVERNANCE) - 1.0) < 1e-9, \
    "ESG weights must sum to 1.0"

# Sector base score profiles (E, S, G baselines)
ESG_SECTOR_PROFILES: dict[str, dict[str, float]] = {
    "Technology":              {"E": 68, "S": 72, "G": 80},
    "Healthcare":              {"E": 62, "S": 78, "G": 75},
    "Financial Services":      {"E": 55, "S": 65, "G": 82},
    "Consumer Cyclical":       {"E": 58, "S": 70, "G": 68},
    "Industrials":             {"E": 50, "S": 64, "G": 70},
    "Energy":                  {"E": 38, "S": 60, "G": 65},
    "Utilities":               {"E": 60, "S": 66, "G": 72},
    "Basic Materials":         {"E": 42, "S": 62, "G": 67},
    "Communication Services":  {"E": 63, "S": 68, "G": 76},
    "Real Estate":             {"E": 58, "S": 63, "G": 71},
    "Consumer Defensive":      {"E": 60, "S": 73, "G": 74},
}
ESG_DEFAULT_PROFILE: dict[str, float] = {"E": 55, "S": 65, "G": 68}
ESG_NOISE_RANGE: float = 12.0  # ± points of deterministic variation


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
# Helpers
# ---------------------------------------------------------------------------
def _ticker_seed(ticker: str) -> float:
    """
    Derive a stable float in [0, 1) from a ticker string via MD5.

    Using a deterministic hash ensures the same ticker always produces
    the same seed, making ESG scores reproducible across runs.
    """
    digest = hashlib.md5(ticker.encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


# ---------------------------------------------------------------------------
# Step 1 — Sub-score generation
# ---------------------------------------------------------------------------
def simulate_esg_scores(ticker: str, sector: str = "Unknown") -> dict[str, float]:
    """
    Generate deterministic ESG sub-scores for a given ticker and sector.

    Parameters
    ----------
    ticker : str   Stock ticker symbol.
    sector : str   GICS sector string.

    Returns
    -------
    dict with keys: "environment", "social", "governance", each in [0, 100].
    """
    profile = ESG_SECTOR_PROFILES.get(sector, ESG_DEFAULT_PROFILE)
    seed = _ticker_seed(ticker.strip().upper() if ticker else "UNKNOWN")

    rng = np.random.default_rng(int(seed * 1_000_000))
    offsets = rng.uniform(-ESG_NOISE_RANGE, ESG_NOISE_RANGE, size=3)

    return {
        "environment": round(float(np.clip(profile["E"] + offsets[0], SCORE_MIN, SCORE_MAX)), 2),
        "social":      round(float(np.clip(profile["S"] + offsets[1], SCORE_MIN, SCORE_MAX)), 2),
        "governance":  round(float(np.clip(profile["G"] + offsets[2], SCORE_MIN, SCORE_MAX)), 2),
    }


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


# Alias for backward compatibility
compute_esg_composite = compute_esg_score


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_esg_scores(ticker: Optional[str] = None, sector: str = "Unknown") -> dict:
    """
    Generate ESG sub-scores and compute composite for a given ticker and sector.

    Parameters
    ----------
    ticker : str, optional
        Stock ticker symbol.
    sector : str, optional
        GICS sector string.

    Returns
    -------
    dict with keys: "environment", "social", "governance", "esg_score", and optionally "ticker".
    """
    sym = ticker.strip().upper() if ticker else "UNKNOWN"
    logger.info("Generating ESG scores for '%s' (sector=%s)", sym, sector)

    sub_scores = simulate_esg_scores(sym, sector)
    env_score = sub_scores["environment"]
    soc_score = sub_scores["social"]
    gov_score = sub_scores["governance"]

    composite = compute_esg_score(env_score, soc_score, gov_score)

    metrics = ESGMetrics(
        environment = env_score,
        social      = soc_score,
        governance  = gov_score,
        esg_score   = composite,
        ticker      = sym if ticker else "",
    )

    logger.info(
        "ESG  E=%.2f  S=%.2f  G=%.2f  composite=%.2f",
        env_score, soc_score, gov_score, composite,
    )

    return metrics.to_dict()


# ---------------------------------------------------------------------------
# Smoke-test  (python esg_scoring.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    print("\n── Deterministic (same ticker → same scores) ─────────────────")
    for _ in range(3):
        result = get_esg_scores("AAPL", "Technology")
        print(json.dumps(result, indent=2))

    print("\n── Multiple tickers ──────────────────────────────────────────")
    tickers_sectors = [
        ("TSLA", "Consumer Cyclical"),
        ("MSFT", "Technology"),
        ("NVDA", "Technology"),
        ("JPM", "Financial Services"),
        ("XOM", "Energy"),
    ]
    for sym, sec in tickers_sectors:
        r = get_esg_scores(sym, sec)
        print(
            f"  {sym:<5}  E={r['environment']:5.1f}  "
            f"S={r['social']:5.1f}  G={r['governance']:5.1f}  "
            f"ESG={r['esg_score']:5.1f}"
        )

    print("\n── Weight check ─────────────────────────────────────────────")
    manual = compute_esg_score(80.0, 65.0, 75.0)
    expected = round((80 * 0.4) + (65 * 0.3) + (75 * 0.3), 2)
    print(f"  compute_esg_score(80, 65, 75) = {manual}")
    print(f"  Expected (80×0.4 + 65×0.3 + 75×0.3) = {expected}")
    assert manual == expected, "Weight formula mismatch!"
    print("  ✓ Formula verified")
