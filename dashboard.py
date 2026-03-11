"""
dashboard.py
------------
Real-Time ESG Investment Intelligence Platform
Bloomberg-style dark finance terminal built with Streamlit + Plotly.

Run
---
    streamlit run dashboard.py

Requires
--------
    streamlit, plotly, requests, pandas
    FastAPI backend running on http://localhost:8000
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ── Page configuration (must be first Streamlit call) ──────────────────────
st.set_page_config(
    page_title="ESG Intelligence Platform",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Constants ───────────────────────────────────────────────────────────────
API_BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 30

RATING_META = {
    "High Sustainability": {"color": "#00e5a0", "icon": "▲", "bg": "rgba(0,229,160,0.08)"},
    "Sustainable Growth":  {"color": "#00b4ff", "icon": "◆", "bg": "rgba(0,180,255,0.08)"},
    "High Risk":           {"color": "#ff4365", "icon": "▼", "bg": "rgba(255,67,101,0.08)"},
}

RISK_META = {
    "LOW":    {"color": "#00e5a0", "label": "LOW RISK",    "bar": 25},
    "MEDIUM": {"color": "#f5a623", "label": "MEDIUM RISK", "bar": 60},
    "HIGH":   {"color": "#ff4365", "label": "HIGH RISK",   "bar": 90},
}

ESG_COLORS = {
    "Environment": "#00e5a0",
    "Social":      "#00b4ff",
    "Governance":  "#a78bfa",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="'IBM Plex Mono', monospace", color="#8899aa"),
    margin=dict(l=10, r=10, t=30, b=10),
)


# ── Global CSS injection ─────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=Bebas+Neue&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

    /* ── Root reset ── */
    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
        background-color: #050810 !important;
        color: #c8d8e8;
    }

    .stApp { background-color: #050810; }
    .block-container { padding: 1.5rem 2rem 2rem; max-width: 1600px; }

    /* ── Hide Streamlit chrome ── */
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: #0a0f1a; }
    ::-webkit-scrollbar-thumb { background: #1e3045; border-radius: 2px; }

    /* ── Top header bar ── */
    .terminal-header {
        background: linear-gradient(135deg, #080e1c 0%, #0a1628 100%);
        border: 1px solid #1a2d45;
        border-top: 2px solid #00e5a0;
        border-radius: 0 0 8px 8px;
        padding: 18px 28px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .terminal-title {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 28px;
        letter-spacing: 0.12em;
        color: #eaf4ff;
        line-height: 1;
    }

    .terminal-title span { color: #00e5a0; }

    .terminal-subtitle {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        color: #445566;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        margin-top: 4px;
    }

    .terminal-clock {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        color: #445566;
        text-align: right;
    }

    .live-dot {
        display: inline-block;
        width: 6px; height: 6px;
        border-radius: 50%;
        background: #00e5a0;
        margin-right: 6px;
        animation: blink 1.4s infinite;
    }

    @keyframes blink {
        0%, 100% { opacity: 1; }
        50%       { opacity: 0.2; }
    }

    /* ── Search panel ── */
    .search-panel {
        background: #080e1c;
        border: 1px solid #1a2d45;
        border-radius: 8px;
        padding: 20px 24px;
        margin-bottom: 20px;
    }

    /* ── Input override ── */
    .stTextInput > div > div > input {
        background: #0a1628 !important;
        border: 1px solid #1a2d45 !important;
        border-radius: 6px !important;
        color: #eaf4ff !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 15px !important;
        letter-spacing: 0.08em !important;
        padding: 10px 16px !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #00e5a0 !important;
        box-shadow: 0 0 0 2px rgba(0,229,160,0.12) !important;
    }

    /* ── Button override ── */
    .stButton > button {
        background: linear-gradient(135deg, #00e5a0 0%, #00b4ff 100%) !important;
        color: #050810 !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        letter-spacing: 0.15em !important;
        text-transform: uppercase !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 10px 28px !important;
        width: 100% !important;
        transition: opacity 0.15s !important;
    }

    .stButton > button:hover { opacity: 0.88 !important; }

    /* ── Metric cards ── */
    .metric-card {
        background: #080e1c;
        border: 1px solid #1a2d45;
        border-radius: 8px;
        padding: 18px 20px;
        position: relative;
        overflow: hidden;
        height: 100%;
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
    }

    .metric-card.green::before  { background: #00e5a0; }
    .metric-card.blue::before   { background: #00b4ff; }
    .metric-card.orange::before { background: #f5a623; }
    .metric-card.purple::before { background: #a78bfa; }

    .metric-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        color: #445566;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .metric-value {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 40px;
        line-height: 1;
        margin-bottom: 6px;
        letter-spacing: 0.04em;
    }

    .metric-value.green  { color: #00e5a0; }
    .metric-value.blue   { color: #00b4ff; }
    .metric-value.orange { color: #f5a623; }
    .metric-value.purple { color: #a78bfa; }

    .metric-sub {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        color: #445566;
    }

    /* ── Section headers ── */
    .section-header {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        color: #445566;
        letter-spacing: 0.25em;
        text-transform: uppercase;
        border-bottom: 1px solid #1a2d45;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }

    .section-header span {
        color: #00e5a0;
        margin-right: 8px;
    }

    /* ── Chart containers ── */
    .chart-container {
        background: #080e1c;
        border: 1px solid #1a2d45;
        border-radius: 8px;
        padding: 20px;
        height: 100%;
    }

    /* ── Risk indicator ── */
    .risk-panel {
        background: #080e1c;
        border: 1px solid #1a2d45;
        border-radius: 8px;
        padding: 24px 20px;
        text-align: center;
    }

    .risk-badge {
        display: inline-block;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 22px;
        font-weight: 600;
        letter-spacing: 0.15em;
        padding: 14px 32px;
        border-radius: 6px;
        margin: 16px 0;
        border: 1px solid;
    }

    /* ── Rating badge ── */
    .rating-panel {
        background: #080e1c;
        border: 1px solid #1a2d45;
        border-radius: 8px;
        padding: 24px 20px;
        text-align: center;
    }

    /* ── Comparison table ── */
    .compare-row {
        display: flex;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid #0f1c2d;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
    }

    .compare-ticker {
        width: 60px;
        font-weight: 600;
        color: #eaf4ff;
        letter-spacing: 0.08em;
    }

    /* ── Spinner override ── */
    .stSpinner > div { border-top-color: #00e5a0 !important; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: #080e1c !important;
        border-bottom: 1px solid #1a2d45 !important;
        gap: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 11px !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        color: #445566 !important;
        background: transparent !important;
        border: none !important;
        padding: 8px 18px !important;
    }

    .stTabs [aria-selected="true"] {
        color: #00e5a0 !important;
        border-bottom: 2px solid #00e5a0 !important;
    }

    /* ── Selectbox ── */
    .stSelectbox > div > div {
        background: #0a1628 !important;
        border: 1px solid #1a2d45 !important;
        color: #eaf4ff !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 13px !important;
    }

    /* ── Info / warning boxes ── */
    .stAlert {
        background: #080e1c !important;
        border: 1px solid #1a2d45 !important;
        border-radius: 6px !important;
        color: #8899aa !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 12px !important;
    }

    /* ── Divider ── */
    hr { border-color: #1a2d45 !important; }

    /* ── Plotly chart centering fix ── */
    .js-plotly-plot { border-radius: 4px; }

    </style>
    """, unsafe_allow_html=True)


# ── API helpers ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def fetch_analysis(ticker: str) -> dict:
    """Call GET /analyze/{ticker} and return the JSON payload."""
    url = f"{API_BASE_URL}/analyze/{ticker.strip().upper()}"
    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# ── Chart builders ───────────────────────────────────────────────────────────
def build_esg_gauge(esg_score: float) -> go.Figure:
    color = (
        "#00e5a0" if esg_score >= 70
        else "#f5a623" if esg_score >= 40
        else "#ff4365"
    )
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=esg_score,
        number={"font": {"family": "Bebas Neue", "size": 52, "color": color},
                "suffix": ""},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickfont": {"family": "IBM Plex Mono", "size": 9, "color": "#334455"},
                "tickcolor": "#1a2d45",
                "tickwidth": 1,
                "nticks": 6,
            },
            "bar": {"color": color, "thickness": 0.22},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  40], "color": "rgba(255,67,101,0.07)"},
                {"range": [40, 70], "color": "rgba(245,166,35,0.07)"},
                {"range": [70,100], "color": "rgba(0,229,160,0.07)"},
            ],
            "threshold": {
                "line": {"color": color, "width": 2},
                "thickness": 0.8,
                "value": esg_score,
            },
        },
    ))
    fig.update_layout(
    height=230,
    margin=dict(l=20, r=20, t=20, b=0),
    )
    return fig


def build_esg_bar(environment: float, social: float, governance: float) -> go.Figure:
    categories = ["Environment", "Social", "Governance"]
    values     = [environment, social, governance]
    colors     = [ESG_COLORS[c] for c in categories]

    fig = go.Figure(go.Bar(
        x=categories,
        y=values,
        marker=dict(
            color=[f"rgba({int(c[1:3],16)},{int(c[3:5],16)},{int(c[5:7],16)},0.85)"
                   for c in colors],
            line=dict(color=colors, width=1.5),
        ),
        text=[f"{v:.1f}" for v in values],
        textposition="outside",
        textfont=dict(family="IBM Plex Mono", size=11, color=colors),
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=240,
        yaxis=dict(
            range=[0, 115],
            gridcolor="#0f1c2d",
            gridwidth=1,
            tickfont=dict(family="IBM Plex Mono", size=9),
            tickcolor="#1a2d45",
        ),
        xaxis=dict(
            tickfont=dict(family="IBM Plex Mono", size=11, color="#8899aa"),
            tickcolor="rgba(0,0,0,0)",
        ),
        bargap=0.35,
        showlegend=False,
    )
    return fig


def build_price_chart(historical_prices: list[dict]) -> go.Figure:
    df = pd.DataFrame(historical_prices)
    df["date"] = pd.to_datetime(df["date"])

    fig = go.Figure()

    # Filled area
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["close"],
        fill="tozeroy",
        fillcolor="rgba(0,180,255,0.06)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Price line
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["close"],
        line=dict(color="#00b4ff", width=1.8),
        name="Close",
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>$%{y:.2f}<extra></extra>",
    ))

    # 20-day MA
    df["ma20"] = df["close"].rolling(20).mean()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["ma20"],
        line=dict(color="#f5a623", width=1, dash="dot"),
        name="MA20",
        hovertemplate="MA20: $%{y:.2f}<extra></extra>",
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=300,
        yaxis=dict(
            gridcolor="#0d1a2a",
            gridwidth=1,
            tickfont=dict(family="IBM Plex Mono", size=9),
            tickprefix="$",
            tickcolor="#1a2d45",
            side="right",
        ),
        xaxis=dict(
            gridcolor="#0d1a2a",
            tickfont=dict(family="IBM Plex Mono", size=9),
            tickcolor="#1a2d45",
            showgrid=False,
        ),
        legend=dict(
            orientation="h",
            x=0, y=1.08,
            font=dict(family="IBM Plex Mono", size=9, color="#445566"),
            bgcolor="rgba(0,0,0,0)",
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#0a1628",
            bordercolor="#1a2d45",
            font=dict(family="IBM Plex Mono", size=11),
        ),
    )
    return fig


def build_comparison_radar(results: list[dict]) -> go.Figure:
    categories = ["Environment", "Social", "Governance", "ESG Score", "Inv. Score"]
    fig = go.Figure()

    palette = ["#00e5a0", "#00b4ff", "#a78bfa"]

    for i, r in enumerate(results):
        values = [
            r["environment"],
            r["social"],
            r["governance"],
            r["esg_score"],
            r["investment_score"],
        ]
        values_closed = values + [values[0]]
        cats_closed   = categories + [categories[0]]

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=cats_closed,
            fill="toself",
            fillcolor=f"rgba({int(palette[i][1:3],16)},{int(palette[i][3:5],16)},{int(palette[i][5:7],16)},0.10)",
            line=dict(color=palette[i], width=2),
            name=r["ticker"],
            hovertemplate=f"<b>{r['ticker']}</b><br>%{{theta}}: %{{r:.1f}}<extra></extra>",
        ))

    fig.update_layout(
    height=360,
    polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(
            visible=True,
            range=[0, 100],
            tickfont=dict(family="IBM Plex Mono", size=8, color="#334455"),
            gridcolor="#1a2d45",
            linecolor="#1a2d45",
        ),
        angularaxis=dict(
            tickfont=dict(family="IBM Plex Mono", size=10, color="#8899aa"),
            gridcolor="#1a2d45",
            linecolor="#1a2d45",
        ),
    ),
    legend=dict(
        orientation="h",
        x=0.5,
        y=-0.05,
        xanchor="center",
        font=dict(family="IBM Plex Mono", size=10, color="#8899aa"),
        bgcolor="rgba(0,0,0,0)",
    ),
    margin=dict(l=60, r=60, t=30, b=40),
)
    return fig


def build_comparison_bar(results: list[dict]) -> go.Figure:
    tickers    = [r["ticker"] for r in results]
    palette    = ["#00e5a0", "#00b4ff", "#a78bfa"]
    metrics    = ["environment", "social", "governance", "esg_score"]
    labels     = ["Environment", "Social", "Governance", "ESG Score"]
    bar_colors = ["#00e5a0", "#00b4ff", "#a78bfa", "#f5a623"]

    fig = go.Figure()
    x = list(range(len(tickers)))
    bar_width = 0.18

    for mi, (metric, label, col) in enumerate(zip(metrics, labels, bar_colors)):
        offsets = [xi + (mi - 1.5) * bar_width for xi in x]
        vals    = [r[metric] for r in results]
        fig.add_trace(go.Bar(
            x=offsets, y=vals,
            width=bar_width,
            name=label,
            marker=dict(
                color=f"rgba({int(col[1:3],16)},{int(col[3:5],16)},{int(col[5:7],16)},0.82)",
                line=dict(color=col, width=1),
            ),
            hovertemplate=f"<b>%{{text}}</b><br>{label}: %{{y:.1f}}<extra></extra>",
            text=tickers,
        ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=300,
        barmode="overlay",
        xaxis=dict(
            tickvals=list(range(len(tickers))),
            ticktext=tickers,
            tickfont=dict(family="IBM Plex Mono", size=12, color="#eaf4ff"),
            tickcolor="rgba(0,0,0,0)",
            gridcolor="rgba(0,0,0,0)",
        ),
        yaxis=dict(
            range=[0, 110],
            gridcolor="#0d1a2a",
            tickfont=dict(family="IBM Plex Mono", size=9),
        ),
        legend=dict(
            orientation="h",
            x=0.5, y=1.12,
            xanchor="center",
            font=dict(family="IBM Plex Mono", size=9, color="#8899aa"),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


# ── Reusable UI components ────────────────────────────────────────────────────
def render_metric_card(label: str, value: str, sub: str, color_class: str):
    st.markdown(f"""
    <div class="metric-card {color_class}">
        <div class="metric-label">{label}</div>
        <div class="metric-value {color_class}">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


def render_section_header(icon: str, title: str):
    st.markdown(
        f'<div class="section-header"><span>{icon}</span>{title}</div>',
        unsafe_allow_html=True,
    )


def render_risk_badge(risk_level: str):
    meta  = RISK_META.get(risk_level, RISK_META["MEDIUM"])
    color = meta["color"]
    label = meta["label"]
    bar   = meta["bar"]
    st.markdown(f"""
    <div class="risk-panel">
        <div class="metric-label">FINANCIAL RISK TIER</div>
        <div class="risk-badge" style="
            color:{color};
            border-color:{color};
            background:rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.08);">
            {label}
        </div>
        <div style="background:#0f1c2d;border-radius:4px;height:4px;margin-top:8px;overflow:hidden;">
            <div style="background:{color};height:100%;width:{bar}%;border-radius:4px;
                        transition:width 0.8s ease;"></div>
        </div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                    color:#445566;margin-top:8px;letter-spacing:0.1em;">
            VOLATILITY RISK METER
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_rating_badge(rating: str, score: int):
    meta  = RATING_META.get(rating, RATING_META["Sustainable Growth"])
    color = meta["color"]
    icon  = meta["icon"]
    bg    = meta["bg"]
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    st.markdown(f"""
    <div class="rating-panel">
        <div class="metric-label">INVESTMENT SUSTAINABILITY RATING</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:52px;
                    color:{color};letter-spacing:0.04em;line-height:1;margin:12px 0 8px;">
            {icon} {score}
        </div>
        <div style="display:inline-block;font-family:'IBM Plex Mono',monospace;
                    font-size:13px;font-weight:600;letter-spacing:0.1em;
                    color:{color};background:{bg};border:1px solid rgba({r},{g},{b},0.25);
                    padding:8px 20px;border-radius:5px;">
            {rating.upper()}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Main app ─────────────────────────────────────────────────────────────────
def main():
    inject_css()

    # ── Header ────────────────────────────────────────────────────────────
    now = datetime.now().strftime("%a %b %d, %Y  %H:%M:%S")
    st.markdown(f"""
    <div class="terminal-header">
        <div>
            <div class="terminal-title">ESG <span>Investment Intelligence</span> Platform</div>
            <div class="terminal-subtitle">
                Real-Time Analytics · ESG Risk · Sustainability Rating
            </div>
        </div>
        <div class="terminal-clock">
            <span class="live-dot"></span>LIVE DATA FEED<br><br>{now}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Search bar ────────────────────────────────────────────────────────
    with st.container():
        st.markdown('<div class="search-panel">', unsafe_allow_html=True)
        sc1, sc2, sc3 = st.columns([2, 1, 4])
        with sc1:
            ticker_input = st.text_input(
                "TICKER SYMBOL",
                value="",
                placeholder="e.g. AAPL, TSLA, MSFT",
                label_visibility="visible",
                key="ticker_main",
            )
        with sc2:
            st.markdown("<br>", unsafe_allow_html=True)
            analyze_clicked = st.button("▶  ANALYZE", key="btn_analyze")
        with sc3:
            st.markdown("""
            <div style="padding-top:8px;font-family:'IBM Plex Mono',monospace;
                        font-size:10px;color:#334455;line-height:1.8;">
                PIPELINE: MARKET DATA → ESG SIMULATION → RISK ANALYSIS → INVESTMENT RATING<br>
                COVERAGE: NYSE · NASDAQ · LSE · TSX  |  DATA: Yahoo Finance  |  ESG: Simulated
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Session state ─────────────────────────────────────────────────────
    if "result" not in st.session_state:
        st.session_state.result = None
    if "error"  not in st.session_state:
        st.session_state.error  = None

    if analyze_clicked and ticker_input.strip():
        with st.spinner(f"Fetching analysis for {ticker_input.upper()} …"):
            try:
                st.session_state.result = fetch_analysis(ticker_input)
                st.session_state.error  = None
            except requests.exceptions.ConnectionError:
                st.session_state.error  = "Cannot connect to API server at localhost:8000. Is the FastAPI backend running?"
                st.session_state.result = None
            except requests.exceptions.HTTPError as exc:
                code = exc.response.status_code
                st.session_state.error  = (
                    f"Ticker '{ticker_input.upper()}' not found (HTTP {code}). "
                    "Check the symbol and try again."
                )
                st.session_state.result = None
            except Exception as exc:
                st.session_state.error  = f"Unexpected error: {exc}"
                st.session_state.result = None

    if st.session_state.error:
        st.error(f"⚠  {st.session_state.error}")

    # ── Results ───────────────────────────────────────────────────────────
    if st.session_state.result:
        d = st.session_state.result

        # ── Metrics row ───────────────────────────────────────────────────
        render_section_header("◈", "KEY METRICS")
        mc1, mc2, mc3, mc4 = st.columns(4)

        with mc1:
            render_metric_card(
                "CURRENT PRICE",
                f"${d['price']:,.2f}",
                f"{d['ticker']} · {d['sector']}",
                "blue",
            )
        with mc2:
            esg_tier = "HIGH" if d["esg_score"] >= 70 else "MEDIUM" if d["esg_score"] >= 40 else "LOW"
            render_metric_card(
                "ESG COMPOSITE SCORE",
                f"{d['esg_score']:.1f}",
                f"ESG TIER — {esg_tier}",
                "green",
            )
        with mc3:
            render_metric_card(
                "ANNUALISED VOLATILITY",
                f"{d['volatility']:.4f}",
                f"RISK LEVEL — {d['risk_level']}",
                "orange",
            )
        with mc4:
            render_metric_card(
                "INVESTMENT SCORE",
                str(d["investment_score"]),
                d["rating"].upper(),
                "purple",
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Charts row 1: gauge + ESG bar + risk + rating ─────────────────
        render_section_header("◈", "ESG ANALYSIS")
        ch1, ch2, ch3, ch4 = st.columns([1.2, 1.5, 1, 1])

        with ch1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="section-header" style="margin-bottom:8px">ESG GAUGE</div>', unsafe_allow_html=True)
            st.plotly_chart(build_esg_gauge(d["esg_score"]), use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        with ch2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="section-header" style="margin-bottom:8px">SUB-SCORE BREAKDOWN</div>', unsafe_allow_html=True)
            st.plotly_chart(
                build_esg_bar(d["environment"], d["social"], d["governance"]),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with ch3:
            render_risk_badge(d["risk_level"])

        with ch4:
            render_rating_badge(d["rating"], d["investment_score"])

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Price history chart ────────────────────────────────────────────
        render_section_header("◈", "PRICE HISTORY  —  1 YEAR")
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)

        if d.get("historical_prices"):
            df_hist = pd.DataFrame(d["historical_prices"])
            price_change = (
                (df_hist["close"].iloc[-1] - df_hist["close"].iloc[0])
                / df_hist["close"].iloc[0] * 100
            )
            hi = df_hist["high"].max()
            lo = df_hist["low"].min()

            p1, p2, p3, p4 = st.columns(4)
            with p1:
                delta_col = "#00e5a0" if price_change >= 0 else "#ff4365"
                sign      = "+" if price_change >= 0 else ""
                st.markdown(f"""
                <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                            color:#445566;letter-spacing:0.15em;margin-bottom:4px;">
                    1Y RETURN</div>
                <div style="font-family:'Bebas Neue',sans-serif;font-size:24px;
                            color:{delta_col};">{sign}{price_change:.2f}%</div>
                """, unsafe_allow_html=True)
            with p2:
                st.markdown(f"""
                <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                            color:#445566;letter-spacing:0.15em;margin-bottom:4px;">
                    52W HIGH</div>
                <div style="font-family:'Bebas Neue',sans-serif;font-size:24px;
                            color:#eaf4ff;">${hi:.2f}</div>
                """, unsafe_allow_html=True)
            with p3:
                st.markdown(f"""
                <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                            color:#445566;letter-spacing:0.15em;margin-bottom:4px;">
                    52W LOW</div>
                <div style="font-family:'Bebas Neue',sans-serif;font-size:24px;
                            color:#eaf4ff;">${lo:.2f}</div>
                """, unsafe_allow_html=True)
            with p4:
                st.markdown(f"""
                <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                            color:#445566;letter-spacing:0.15em;margin-bottom:4px;">
                    DATA POINTS</div>
                <div style="font-family:'Bebas Neue',sans-serif;font-size:24px;
                            color:#eaf4ff;">{len(df_hist)} days</div>
                """, unsafe_allow_html=True)

            st.plotly_chart(
                build_price_chart(d["historical_prices"]),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        else:
            st.markdown(
                '<div style="color:#445566;font-family:IBM Plex Mono;'
                'font-size:12px;padding:40px;text-align:center;">NO HISTORICAL DATA AVAILABLE</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Default state ─────────────────────────────────────────────────────
    else:
        st.markdown("""
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:center;padding:80px 0;text-align:center;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:80px;
                        color:#0f1c2d;letter-spacing:0.1em;line-height:1;">ESG</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:12px;
                        color:#334455;letter-spacing:0.25em;margin-top:-8px;">
                ENTER A TICKER SYMBOL TO BEGIN ANALYSIS
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # COMPANY COMPARISON TOOL
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<hr style="border-color:#0f1c2d;margin:8px 0 24px;">', unsafe_allow_html=True)
    render_section_header("◈", "MULTI-COMPANY ESG COMPARISON")

    with st.expander("▶  CONFIGURE COMPARISON  —  Compare ESG profiles of up to 3 companies", expanded=False):
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            t1 = st.text_input("COMPANY 1", value="AAPL", key="cmp1",
                               placeholder="e.g. AAPL")
        with cc2:
            t2 = st.text_input("COMPANY 2", value="TSLA", key="cmp2",
                               placeholder="e.g. TSLA")
        with cc3:
            t3 = st.text_input("COMPANY 3", value="MSFT", key="cmp3",
                               placeholder="e.g. MSFT")

        cmp_btn = st.button("▶  RUN COMPARISON", key="btn_compare")

    if "cmp_results" not in st.session_state:
        st.session_state.cmp_results = None
    if "cmp_error"   not in st.session_state:
        st.session_state.cmp_error   = None

    if cmp_btn:
        tickers_to_compare = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]
        if len(tickers_to_compare) < 2:
            st.session_state.cmp_error = "Enter at least 2 ticker symbols to compare."
        else:
            results_list = []
            errors_list  = []
            progress_bar = st.progress(0, text="Fetching comparison data …")
            for i, sym in enumerate(tickers_to_compare):
                try:
                    results_list.append(fetch_analysis(sym))
                except Exception as exc:
                    errors_list.append(f"{sym}: {exc}")
                progress_bar.progress((i + 1) / len(tickers_to_compare))
                time.sleep(0.1)
            progress_bar.empty()

            st.session_state.cmp_results = results_list or None
            st.session_state.cmp_error   = (
                "Failed to fetch: " + ", ".join(errors_list) if errors_list else None
            )

    if st.session_state.cmp_error:
        st.error(f"⚠  {st.session_state.cmp_error}")

    if st.session_state.cmp_results and len(st.session_state.cmp_results) >= 2:
        cmp_data = st.session_state.cmp_results

        # ── Summary table ─────────────────────────────────────────────────
        pal = ["#00e5a0", "#00b4ff", "#a78bfa"]
        cols_header = st.columns([1, 1.2, 1, 1, 1, 1, 1, 1.5])
        headers = ["TICKER", "SECTOR", "PRICE", "ENV", "SOC", "GOV", "ESG", "RATING"]
        for col, hdr in zip(cols_header, headers):
            col.markdown(
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:9px;'
                f'color:#334455;letter-spacing:0.15em;padding-bottom:6px;'
                f'border-bottom:1px solid #1a2d45;">{hdr}</div>',
                unsafe_allow_html=True,
            )

        for i, r in enumerate(cmp_data):
            row_cols = st.columns([1, 1.2, 1, 1, 1, 1, 1, 1.5])
            color    = pal[i % len(pal)]
            values   = [
                r["ticker"], r["sector"][:16],
                f"${r['price']:,.2f}",
                f"{r['environment']:.1f}", f"{r['social']:.1f}",
                f"{r['governance']:.1f}", f"{r['esg_score']:.1f}",
                r["rating"],
            ]
            for j, (col, val) in enumerate(zip(row_cols, values)):
                text_color = color if j in (0, 7) else "#c8d8e8"
                col.markdown(
                    f'<div style="font-family:IBM Plex Mono,monospace;font-size:11px;'
                    f'color:{text_color};padding:8px 0;border-bottom:1px solid #0f1c2d;">'
                    f'{val}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Radar + bar charts ─────────────────────────────────────────────
        viz1, viz2 = st.columns(2)

        with viz1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="section-header">RADAR — ESG PROFILE</div>', unsafe_allow_html=True)
            st.plotly_chart(
                build_comparison_radar(cmp_data),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with viz2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="section-header">GROUPED BAR — SCORE BREAKDOWN</div>', unsafe_allow_html=True)
            st.plotly_chart(
                build_comparison_bar(cmp_data),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────────────────
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="border-top:1px solid #0f1c2d;padding-top:16px;
                display:flex;justify-content:space-between;align-items:center;
                font-family:'IBM Plex Mono',monospace;font-size:10px;color:#223344;">
        <div>ESG INVESTMENT INTELLIGENCE PLATFORM · v1.0.0</div>
        <div>DATA: YAHOO FINANCE · ESG: SIMULATED · FOR EDUCATIONAL USE ONLY</div>
        <div>API: localhost:8000 · DASHBOARD: localhost:8501</div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
