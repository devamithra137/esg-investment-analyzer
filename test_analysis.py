"""
test_analysis.py
----------------
Command-line investment report for the Real-Time ESG Investment Analyzer.
Runs the full pipeline — market data → ESG → risk → rating — and prints
a formatted terminal report without needing the dashboard or API server.

Usage
-----
    python test_analysis.py AAPL
    python test_analysis.py TSLA MSFT NVDA          # multiple tickers
    python test_analysis.py --help

Author  : ESG Investment Analyzer
Version : 1.0.0
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from datetime import datetime

from esg_scoring import compute_esg_composite, simulate_esg_scores
from investment_rating import generate_investment_rating
from market_data import get_market_data
from risk_analysis import analyse_risk

# ── ANSI colour palette ──────────────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    GREEN   = "\033[38;5;84m"
    BLUE    = "\033[38;5;75m"
    ORANGE  = "\033[38;5;214m"
    RED     = "\033[38;5;203m"
    PURPLE  = "\033[38;5;141m"
    CYAN    = "\033[38;5;51m"
    WHITE   = "\033[97m"
    GREY    = "\033[38;5;240m"
    BG_DARK = "\033[48;5;234m"


def _supports_color() -> bool:
    """Return True if the terminal supports ANSI colour codes."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


USE_COLOR = _supports_color()


def _c(code: str, text: str) -> str:
    """Wrap text in an ANSI code, or return plain text if colour unavailable."""
    return f"{code}{text}{C.RESET}" if USE_COLOR else text


# ── Report rendering helpers ─────────────────────────────────────────────────
WIDTH = 62

def _line(char: str = "─") -> str:
    return _c(C.GREY, char * WIDTH)


def _header_line(char: str = "═") -> str:
    return _c(C.CYAN, char * WIDTH)


def _kv(label: str, value: str, value_color: str = C.WHITE) -> str:
    label_col = _c(C.GREY, f"  {label:<24}")
    val_col   = _c(value_color, value)
    return f"{label_col}{val_col}"


def _score_bar(value: float, width: int = 24) -> str:
    """Render a compact ASCII progress bar for a 0–100 score."""
    filled    = int(round(value / 100 * width))
    bar_color = C.GREEN if value >= 70 else C.ORANGE if value >= 40 else C.RED
    bar       = _c(bar_color, "█" * filled) + _c(C.GREY, "░" * (width - filled))
    return f"{bar}  {_c(bar_color, f'{value:5.1f}')}"


def _risk_color(risk: str) -> str:
    return {"LOW": C.GREEN, "MEDIUM": C.ORANGE, "HIGH": C.RED}.get(risk, C.WHITE)


def _rating_color(rating: str) -> str:
    return {
        "High Sustainability": C.GREEN,
        "Sustainable Growth":  C.BLUE,
        "High Risk":           C.RED,
    }.get(rating, C.WHITE)


def _rating_icon(rating: str) -> str:
    return {
        "High Sustainability": "▲",
        "Sustainable Growth":  "◆",
        "High Risk":           "▼",
    }.get(rating, "•")


# ── Pipeline runner ───────────────────────────────────────────────────────────
def run_analysis(ticker: str) -> dict:
    """
    Execute the full analysis pipeline for a single ticker.

    Returns the assembled report dict, or raises on failure.
    """
    ticker = ticker.strip().upper()

    # Step 1 — Market data
    market = get_market_data(ticker)
    price   = market["price"]
    sector  = market["sector"]
    history = market["historical_prices"]

    if not history:
        raise ValueError(f"No historical price data returned for '{ticker}'.")

    # Step 2 — ESG simulation
    esg_sub   = simulate_esg_scores(ticker, sector)
    esg_score = compute_esg_composite(
        esg_sub["environment"], esg_sub["social"], esg_sub["governance"]
    )

    # Step 3 — Risk analysis
    close_prices = [day["close"] for day in history]
    risk = analyse_risk(close_prices)

    # Step 4 — Investment rating
    rating = generate_investment_rating(
        esg_score=esg_score,
        risk_level=risk["risk_level"],
    )

    return {
        "ticker":           ticker,
        "sector":           sector,
        "price":            price,
        "environment":      esg_sub["environment"],
        "social":           esg_sub["social"],
        "governance":       esg_sub["governance"],
        "esg_score":        esg_score,
        "volatility":       risk["volatility"],
        "risk_level":       risk["risk_level"],
        "investment_score": rating["investment_score"],
        "rating":           rating["rating"],
        "history_days":     len(history),
        "price_52w_high":   max(d["high"]  for d in history),
        "price_52w_low":    min(d["low"]   for d in history),
        "price_1y_ago":     history[0]["close"],
    }


# ── Report printer ────────────────────────────────────────────────────────────
def print_report(d: dict) -> None:
    """Print the full formatted investment report for one ticker."""

    pct_change  = (d["price"] - d["price_1y_ago"]) / d["price_1y_ago"] * 100
    pct_color   = C.GREEN if pct_change >= 0 else C.RED
    pct_sign    = "+" if pct_change >= 0 else ""
    esg_tier    = "HIGH" if d["esg_score"] >= 70 else "MEDIUM" if d["esg_score"] >= 40 else "LOW"
    rating_icon = _rating_icon(d["rating"])
    r_color     = _rating_color(d["rating"])
    risk_color  = _risk_color(d["risk_level"])

    print()
    print(_header_line())
    print(_c(C.CYAN + C.BOLD,
             f"  ◈  INVESTMENT ANALYSIS REPORT  —  {d['ticker']}".ljust(WIDTH)))
    print(_c(C.GREY, f"  {datetime.now().strftime('%A %B %d, %Y  %H:%M:%S')}".ljust(WIDTH)))
    print(_header_line())

    # ── Company overview ──────────────────────────────────────────────────
    print(_c(C.GREY + C.BOLD, "\n  COMPANY OVERVIEW\n"))
    print(_kv("Ticker",          d["ticker"],           C.CYAN))
    print(_kv("Sector",          d["sector"],           C.WHITE))
    print(_kv("Current Price",   f"${d['price']:,.2f}", C.WHITE))
    print(_kv("52-Week High",    f"${d['price_52w_high']:,.2f}", C.WHITE))
    print(_kv("52-Week Low",     f"${d['price_52w_low']:,.2f}",  C.WHITE))
    print(_kv("1Y Price Change",
              f"{pct_sign}{pct_change:.2f}%", pct_color))
    print(_kv("History Window",  f"{d['history_days']} trading days", C.GREY))

    # ── ESG analysis ──────────────────────────────────────────────────────
    print(_c(C.GREY, f"\n  {_line()}\n"))
    print(_c(C.GREY + C.BOLD, "  ESG ANALYSIS\n"))
    print(_kv("ESG Tier",        esg_tier,
              C.GREEN if esg_tier == "HIGH" else C.ORANGE if esg_tier == "MEDIUM" else C.RED))
    print()
    print(f"  {'Environment':<22} {_score_bar(d['environment'])}")
    print(f"  {'Social':<22} {_score_bar(d['social'])}")
    print(f"  {'Governance':<22} {_score_bar(d['governance'])}")
    print()
    print(f"  {'Composite ESG Score':<22} {_score_bar(d['esg_score'])}")
    print(_c(C.GREY, f"  {'':22} Weights: E=40%  S=30%  G=30%"))

    # ── Risk analysis ─────────────────────────────────────────────────────
    print(_c(C.GREY, f"\n  {_line()}\n"))
    print(_c(C.GREY + C.BOLD, "  FINANCIAL RISK ANALYSIS\n"))
    print(_kv("Annualised Volatility", f"{d['volatility']:.4f}  (σ)", C.WHITE))
    print(_kv("Risk Classification",
              f"{'▼  ' if d['risk_level']=='HIGH' else '–  ' if d['risk_level']=='MEDIUM' else '▲  '}{d['risk_level']}",
              risk_color))
    print()
    # visual risk meter
    risk_bar_fill = {"LOW": 8, "MEDIUM": 17, "HIGH": 26}.get(d["risk_level"], 13)
    bar  = _c(risk_color, "█" * risk_bar_fill)
    bar += _c(C.GREY,     "░" * (26 - risk_bar_fill))
    zones = _c(C.GREEN, "LOW") + _c(C.GREY, "  |  ") + _c(C.ORANGE, "MEDIUM") + _c(C.GREY, "  |  ") + _c(C.RED, "HIGH")
    print(f"  Risk Meter  {bar}")
    print(f"              {zones}")

    # ── Investment rating ─────────────────────────────────────────────────
    print(_c(C.GREY, f"\n  {_line()}\n"))
    print(_c(C.GREY + C.BOLD, "  INVESTMENT SUSTAINABILITY RATING\n"))

    # Score bar
    print(f"  {'Investment Score':<22} {_score_bar(d['investment_score'])}")
    print()

    # Rating badge  (prominent)
    badge_text = f"  {rating_icon}  {d['rating'].upper()}  {rating_icon}  "
    badge_pad  = (WIDTH - len(badge_text)) // 2
    print(_c(r_color + C.BOLD, " " * badge_pad + badge_text))
    print()

    # Rationale one-liner
    rationale = {
        "High Sustainability": "Strong ESG fundamentals combined with low financial risk — suitable for sustainable portfolios.",
        "Sustainable Growth":  "Balanced ESG profile with moderate risk — solid candidate for growth-oriented strategies.",
        "High Risk":           "Elevated financial risk or weak ESG fundamentals — caution advised; high speculative exposure.",
    }.get(d["rating"], "")
    # Wrap rationale at WIDTH-4 chars
    words, line_buf, lines = rationale.split(), [], []
    for w in words:
        if sum(len(x) + 1 for x in line_buf) + len(w) > WIDTH - 6:
            lines.append(" ".join(line_buf))
            line_buf = [w]
        else:
            line_buf.append(w)
    if line_buf:
        lines.append(" ".join(line_buf))
    for ln in lines:
        print(_c(C.GREY, f"  {ln}"))

    print()
    print(_header_line())
    print(_c(C.GREY, "  ⚠  For educational purposes only. Not financial advice."))
    print(_header_line())
    print()


# ── CLI entry point ───────────────────────────────────────────────────────────
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="test_analysis",
        description="Real-Time ESG Investment Analyzer — CLI Report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python test_analysis.py AAPL\n"
            "  python test_analysis.py TSLA MSFT NVDA\n"
        ),
    )
    parser.add_argument(
        "tickers",
        metavar="TICKER",
        nargs="+",
        help="One or more stock ticker symbols (e.g. AAPL TSLA MSFT)",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args   = parser.parse_args()

    tickers   = [t.strip().upper() for t in args.tickers]
    successes = 0
    failures  = 0

    for i, ticker in enumerate(tickers):
        if i > 0:
            time.sleep(0.5)   # brief pause between multiple tickers

        print(_c(C.GREY, f"\n  Fetching data for {ticker} …"), end="", flush=True)

        try:
            result = run_analysis(ticker)
            print(_c(C.GREEN, "  done"))
            print_report(result)
            successes += 1

        except ValueError as exc:
            print(_c(C.RED, f"  failed\n\n  ERROR: {exc}\n"))
            failures += 1
        except Exception as exc:
            print(_c(C.RED, f"  failed\n\n  UNEXPECTED ERROR: {exc}\n"))
            failures += 1

    # ── Summary when multiple tickers ────────────────────────────────────
    if len(tickers) > 1:
        print(_c(C.GREY, _line()))
        print(_c(C.GREY, f"  Analyzed {successes + failures} ticker(s) — "
                         f"{_c(C.GREEN, str(successes))} succeeded  "
                         f"{_c(C.RED, str(failures))} failed"))
        print(_c(C.GREY, _line()))
        print()

    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
