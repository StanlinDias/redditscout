"""UI primitives for RedditScout — Apple × Reddit aesthetic.

Centralizes the global stylesheet and reusable HTML components so
dashboard.py can stay focused on page logic.
"""

from __future__ import annotations

import html
from typing import Iterable

import streamlit as st


# --- Design tokens ----------------------------------------------------------

TEXT = "#2D3142"
TEXT_SECONDARY = "#6B7280"
TEXT_TERTIARY = "#9CA3AF"
BORDER = "#E8ECF1"
BORDER_STRONG = "#D1D5DB"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F3F4F8"
ACCENT = "#FF4500"
ACCENT_HOVER = "#E63E00"
ACCENT_TINT = "#FFF0EA"
GREEN = "#34C759"
AMBER = "#FF9500"
RED = "#FF3B30"


# --- Global stylesheet ------------------------------------------------------

_GLOBAL_CSS = f"""
<style>
  @import url('https://rsms.me/inter/inter.css');

  :root {{
    --text: {TEXT};
    --text-2: {TEXT_SECONDARY};
    --text-3: {TEXT_TERTIARY};
    --border: {BORDER};
    --border-strong: {BORDER_STRONG};
    --surface: {SURFACE};
    --surface-alt: {SURFACE_ALT};
    --accent: {ACCENT};
    --accent-hover: {ACCENT_HOVER};
    --accent-tint: {ACCENT_TINT};
    --green: {GREEN};
    --amber: {AMBER};
    --red: {RED};
    --font: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text",
            "Inter", "Helvetica Neue", Arial, sans-serif;
  }}

  html, body, [class*="stApp"] {{
    font-family: var(--font);
    color: var(--text);
    background: var(--surface) !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    font-feature-settings: "ss01", "cv11";
  }}

  /* Force light mode — soft warm-gray canvas */
  .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
  .main, section.main {{
    background: var(--surface-alt) !important;
    color: var(--text) !important;
  }}
  .stApp p, .stApp span, .stApp div, .stApp label,
  .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
    color: var(--text);
  }}
  .stMarkdown, .stMarkdown p {{ color: var(--text) !important; }}
  .stCaption, [data-testid="stCaptionContainer"] {{ color: var(--text-2) !important; }}

  /* Hide Streamlit chrome */
  #MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden; height: 0; }}
  [data-testid="stDeployButton"] {{ display: none; }}
  [data-testid="stToolbar"] {{ right: 1rem; }}

  /* Main container — generous spacing */
  .block-container {{
    max-width: 1040px;
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
  }}

  /* Sidebar — soft, clean */
  [data-testid="stSidebar"] {{
    background: var(--surface);
    border-right: none;
    box-shadow: 2px 0 12px rgba(0,0,0,0.04);
  }}
  [data-testid="stSidebar"] .block-container {{
    padding-top: 1.75rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
  }}
  [data-testid="stSidebar"] [data-testid="stSidebarNav"] {{ display: none; }}

  /* Sidebar radio → nav list */
  [data-testid="stSidebar"] [data-testid="stRadio"] > label {{
    display: none;  /* hide "Navigate" label */
  }}
  [data-testid="stSidebar"] [role="radiogroup"] {{
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }}
  [data-testid="stSidebar"] [role="radiogroup"] > label {{
    padding: 0.5rem 0.7rem !important;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.12s ease;
    margin: 0 !important;
    width: 100%;
    background: transparent;
  }}
  [data-testid="stSidebar"] [role="radiogroup"] > label:hover {{
    background: rgba(0,0,0,0.04);
  }}
  /* hide the radio circle, keep only label text */
  [data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {{
    display: none !important;
  }}
  [data-testid="stSidebar"] [role="radiogroup"] > label p {{
    font-size: 0.92rem !important;
    font-weight: 500 !important;
    color: var(--text) !important;
    letter-spacing: -0.01em;
    margin: 0 !important;
  }}
  /* Active nav item — soft accent tint bg */
  [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {{
    background: var(--accent-tint);
    box-shadow: 0 1px 4px rgba(255,69,0,0.08);
  }}
  [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p {{
    color: var(--accent) !important;
    font-weight: 600 !important;
  }}

  /* Typography */
  h1, h2, h3, h4 {{
    color: var(--text);
    letter-spacing: -0.02em;
    font-weight: 600;
  }}
  h1 {{ font-size: 2rem; }}
  h2 {{ font-size: 1.5rem; }}
  h3 {{ font-size: 1.15rem; }}

  /* Buttons — soft, rounded */
  .stButton > button {{
    border-radius: 12px;
    font-weight: 500;
    font-family: var(--font);
    letter-spacing: -0.01em;
    padding: 0.55rem 1.2rem;
    border: none;
    background: var(--surface);
    color: var(--text);
    transition: all 0.2s ease;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }}
  .stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  }}
  .stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 100%);
    border: none;
    color: white;
    box-shadow: 0 2px 10px rgba(255,69,0,0.25);
  }}
  .stButton > button[kind="primary"]:hover {{
    box-shadow: 0 4px 16px rgba(255,69,0,0.35);
    transform: translateY(-1px);
  }}

  /* Inputs — soft, borderless */
  .stTextInput input, .stNumberInput input, .stTextArea textarea {{
    border-radius: 12px !important;
    border: 1px solid transparent !important;
    background: var(--surface) !important;
    font-family: var(--font) !important;
    font-size: 0.95rem !important;
    padding: 0.65rem 0.9rem !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
    transition: box-shadow 0.2s, border-color 0.2s;
  }}
  .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {{
    border-color: var(--accent) !important;
    box-shadow: 0 2px 10px rgba(255,69,0,0.12) !important;
  }}
  .stTextInput label, .stNumberInput label, .stTextArea label {{
    color: var(--text) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
  }}

  /* Tabs — top nav */
  .stTabs [data-baseweb="tab-list"] {{
    gap: 0.25rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.5rem;
  }}
  .stTabs [data-baseweb="tab"] {{
    background: transparent;
    border: none;
    color: var(--text-2);
    font-family: var(--font);
    font-weight: 500;
    font-size: 0.9rem;
    padding: 0.6rem 0.9rem;
    border-radius: 8px 8px 0 0;
    transition: color 0.15s;
  }}
  .stTabs [data-baseweb="tab"]:hover {{ color: var(--text); }}
  .stTabs [aria-selected="true"] {{
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
  }}

  /* Alerts — soft */
  .stAlert {{
    border-radius: 14px;
    border: none;
    box-shadow: 0 1px 6px rgba(0,0,0,0.05);
  }}

  /* Dataframe — soft card */
  [data-testid="stDataFrame"] {{
    border: none;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  }}

  /* Metric cards — soft gradient tints */
  [data-testid="stMetric"] {{
    background: var(--surface);
    padding: 1.2rem 1.4rem;
    border-radius: 18px;
    border: none;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    transition: box-shadow 0.2s, transform 0.2s;
  }}
  [data-testid="stMetric"]:hover {{
    box-shadow: 0 6px 20px rgba(0,0,0,0.08);
    transform: translateY(-2px);
  }}
  [data-testid="stMetricLabel"] {{
    color: var(--text-3) !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase;
  }}
  [data-testid="stMetricValue"] {{
    font-weight: 800 !important;
    font-size: 2rem !important;
    letter-spacing: -0.03em !important;
    font-variant-numeric: tabular-nums;
    color: var(--text) !important;
  }}
  /* Gradient tint on metric cards — 1st, 2nd, 3rd, 4th */
  [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(1) [data-testid="stMetric"] {{
    background: linear-gradient(135deg, #FFF5F0 0%, #FFE0D1 100%);
  }}
  [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) [data-testid="stMetric"] {{
    background: linear-gradient(135deg, #EEFBF0 0%, #D1F5D9 100%);
  }}
  [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) [data-testid="stMetric"] {{
    background: linear-gradient(135deg, #EEF3FF 0%, #D5E0FF 100%);
  }}
  [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) [data-testid="stMetric"] {{
    background: linear-gradient(135deg, #F5EEFF 0%, #E3D5FF 100%);
  }}

  /* Expanders */
  [data-testid="stExpander"] {{
    border: none !important;
    border-radius: 16px !important;
    background: var(--surface);
    margin-bottom: 0.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  }}
  [data-testid="stExpander"] summary {{
    padding: 0.9rem 1.1rem !important;
    font-weight: 500;
  }}

  /* --- Custom components --- */

  .rs-hero {{
    padding: 0.75rem 0 1.75rem 0;
    border-bottom: none;
    margin-bottom: 1.5rem;
  }}
  .rs-hero-eyebrow {{
    color: var(--accent);
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
    display: inline-block;
    padding: 0.2rem 0.55rem;
    background: var(--accent-tint);
    border-radius: 6px;
  }}
  .rs-hero-title {{
    font-size: 2.25rem;
    font-weight: 600;
    letter-spacing: -0.03em;
    color: var(--text);
    margin: 0.4rem 0 0.5rem 0;
  }}
  .rs-hero-sub {{
    font-size: 1.05rem;
    color: var(--text-2);
    font-weight: 400;
    margin: 0;
  }}

  .rs-brand {{
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.5rem 0 1.25rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.25rem;
  }}
  .rs-brand-mark {{
    width: 36px; height: 36px;
    background: linear-gradient(135deg, var(--accent) 0%, #E63E00 100%);
    color: white;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800;
    font-size: 1.1rem;
    letter-spacing: -0.02em;
    box-shadow: 0 2px 8px rgba(255,69,0,0.25);
  }}
  .rs-brand-name {{
    font-weight: 700;
    font-size: 1.1rem;
    letter-spacing: -0.02em;
  }}

  .rs-pill {{
    display: inline-flex;
    align-items: center;
    padding: 0.22rem 0.55rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 500;
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }}
  .rs-pill-sub {{
    background: var(--surface-alt);
    color: var(--text);
    font-family: "SF Mono", ui-monospace, monospace;
    font-weight: 600;
    border: 1px solid var(--border);
  }}
  .rs-pill-muted {{
    background: var(--surface-alt);
    color: var(--text-2);
    border: 1px solid var(--border);
  }}
  .rs-pill-pattern {{
    background: var(--surface-alt);
    color: var(--text-2);
    border: 1px solid var(--border);
    font-style: italic;
  }}
  /* Velocity / trending pill — accent-tinted so it draws the eye */
  .rs-pill-velocity {{
    background: var(--accent-tint);
    color: var(--accent);
    font-weight: 600;
    border: 1px solid #FFD9C7;
  }}
  .rs-pill-ratio {{
    background: var(--surface-alt);
    color: var(--text-2);
    border: 1px solid var(--border);
    font-variant-numeric: tabular-nums;
  }}

  /* Score dots — subtle; the pill background stays neutral */
  .rs-pill-score {{
    background: var(--surface-alt);
    color: var(--text);
    border: 1px solid var(--border);
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-weight: 600;
  }}
  .rs-score-dot {{
    width: 7px; height: 7px; border-radius: 50%;
    display: inline-block;
  }}
  .rs-score-dot-high {{ background: var(--green); }}
  .rs-score-dot-mid  {{ background: var(--text-3); }}
  .rs-score-dot-low  {{ background: var(--red); }}

  .rs-card {{
    background: var(--surface);
    border: none;
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.7rem;
    transition: box-shadow 0.2s, transform 0.2s;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  }}
  .rs-card:hover {{
    box-shadow: 0 6px 20px rgba(0,0,0,0.08);
    transform: translateY(-2px);
  }}
  .rs-card-meta {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    color: var(--text-3);
    font-size: 0.82rem;
    margin-bottom: 0.55rem;
  }}
  .rs-card-meta-sep {{ color: var(--border-strong); }}
  .rs-card-title {{
    color: var(--text);
    font-weight: 500;
    font-size: 1.02rem;
    line-height: 1.4;
    letter-spacing: -0.01em;
    margin: 0 0 0.55rem 0;
  }}
  .rs-card-footer {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 0.75rem;
  }}
  .rs-card-link {{
    color: var(--accent);
    font-size: 0.88rem;
    font-weight: 500;
    text-decoration: none;
  }}
  .rs-card-link:hover {{ color: var(--accent-hover); text-decoration: none; }}

  .rs-score-header {{
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.75rem;
  }}
  .rs-score-big {{
    font-size: 1.75rem;
    font-weight: 600;
    letter-spacing: -0.03em;
    font-variant-numeric: tabular-nums;
    color: var(--text);
    line-height: 1;
  }}
  .rs-score-big-unit {{
    color: var(--text-3);
    font-size: 1rem;
    font-weight: 500;
  }}

  .rs-bar-row {{
    display: grid;
    grid-template-columns: 120px 1fr 36px;
    align-items: center;
    gap: 0.75rem;
    padding: 0.3rem 0;
  }}
  .rs-bar-label {{
    font-size: 0.85rem;
    color: var(--text-2);
    font-weight: 500;
  }}
  .rs-bar-track {{
    height: 6px;
    background: var(--surface-alt);
    border-radius: 999px;
    overflow: hidden;
  }}
  .rs-bar-fill {{
    height: 100%;
    background: var(--accent);
    border-radius: 999px;
    transition: width 0.3s ease;
  }}
  .rs-bar-value {{
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text);
    text-align: right;
    font-variant-numeric: tabular-nums;
  }}

  .rs-section-title {{
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--text-3);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin: 2rem 0 0.85rem 0;
  }}

  .rs-empty {{
    border: 2px dashed var(--border);
    border-radius: 18px;
    padding: 2.5rem 1.5rem;
    text-align: center;
    color: var(--text-2);
    background: var(--surface);
  }}
  .rs-empty-title {{
    font-weight: 500;
    color: var(--text);
    margin-bottom: 0.25rem;
  }}

  /* Onboarding */
  .rs-welcome {{
    border: none;
    border-radius: 20px;
    padding: 2rem 2.25rem;
    background: linear-gradient(135deg, var(--surface) 0%, #FFF3ED 50%, #FFE8DC 100%);
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  }}
  .rs-welcome-title {{
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--text);
    margin-bottom: 0.5rem;
  }}
  .rs-welcome-sub {{
    color: var(--text-2);
    font-size: 1rem;
    margin-bottom: 1.5rem;
    line-height: 1.6;
  }}
  .rs-step {{
    display: flex;
    align-items: flex-start;
    gap: 0.85rem;
    padding: 0.7rem 0;
    border-bottom: 1px solid rgba(0,0,0,0.04);
  }}
  .rs-step:last-child {{ border-bottom: none; }}
  .rs-step-num {{
    width: 30px; height: 30px; min-width: 30px;
    background: var(--accent);
    border: none;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.82rem;
    color: white;
    box-shadow: 0 2px 6px rgba(255,69,0,0.2);
  }}
  .rs-step-num.done {{
    background: var(--green);
    box-shadow: 0 2px 6px rgba(52,199,89,0.25);
  }}
  .rs-step-num.pending {{
    background: var(--surface-alt);
    border: 1.5px solid var(--border);
    color: var(--text-3);
    box-shadow: none;
  }}
  .rs-step-label {{
    font-weight: 600;
    color: var(--text);
    font-size: 0.95rem;
  }}
  .rs-step-desc {{
    color: var(--text-2);
    font-size: 0.85rem;
    margin-top: 0.15rem;
    line-height: 1.4;
  }}
  .rs-tip {{
    background: var(--surface);
    border: none;
    border-left: 3px solid var(--accent);
    border-radius: 12px;
    padding: 0.85rem 1.2rem;
    margin-bottom: 1.25rem;
    font-size: 0.88rem;
    color: var(--text-2);
    line-height: 1.55;
    box-shadow: 0 1px 6px rgba(0,0,0,0.04);
  }}
  .rs-tip strong {{ color: var(--text); }}

  .rs-connection {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.75rem;
    border-radius: 999px;
    background: var(--surface-alt);
    border: none;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    font-size: 0.82rem;
    color: var(--text-2);
  }}
  .rs-connection-dot {{
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--green);
  }}
</style>
"""


def inject_styles() -> None:
    """Inject the global stylesheet. Call once at the top of the app."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


# --- Components -------------------------------------------------------------


def brand_mark() -> None:
    """Sidebar brand lockup: orange R mark + wordmark."""
    st.markdown(
        """
        <div class="rs-brand">
          <div class="rs-brand-mark">R</div>
          <div class="rs-brand-name">RedditScout</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, eyebrow: str | None = None) -> None:
    """Page header — eyebrow / title / subtitle."""
    eyebrow_html = (
        f'<div class="rs-hero-eyebrow">{html.escape(eyebrow)}</div>' if eyebrow else ""
    )
    st.markdown(
        f"""
        <div class="rs-hero">
          {eyebrow_html}
          <h1 class="rs-hero-title">{html.escape(title)}</h1>
          <p class="rs-hero-sub">{html.escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def connection_status(username: str) -> None:
    """Green-dot pill for Reddit connection."""
    st.markdown(
        f"""
        <div class="rs-connection">
          <span class="rs-connection-dot"></span>
          Connected as <strong style="color: var(--text);">u/{html.escape(username)}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(label: str) -> None:
    st.markdown(
        f'<div class="rs-section-title">{html.escape(label)}</div>',
        unsafe_allow_html=True,
    )


def pill(text: str, variant: str = "muted") -> str:
    """Return HTML for a pill. variants: sub, muted, pattern, green, amber, red."""
    return (
        f'<span class="rs-pill rs-pill-{variant}">{html.escape(str(text))}</span>'
    )


def post_card(
    *,
    subreddit: str,
    title: str,
    url: str,
    age: str | None = None,
    score: int | None = None,
    comments: int | None = None,
    pattern: str | None = None,
    extra_pills: Iterable[str] = (),
) -> None:
    """Render a Reddit post as an Apple-style card."""
    meta_parts = [f'<span class="rs-pill rs-pill-sub">r/{html.escape(subreddit)}</span>']
    if age:
        meta_parts.append(f'<span class="rs-card-meta-sep">·</span><span>{html.escape(age)}</span>')
    if score is not None:
        meta_parts.append(f'<span class="rs-card-meta-sep">·</span><span>↑ {score:,}</span>')
    if comments is not None:
        meta_parts.append(f'<span class="rs-card-meta-sep">·</span><span>{comments:,} comments</span>')

    footer_pills = []
    if pattern:
        footer_pills.append(pill(f'"{pattern}"', "pattern"))
    footer_pills.extend(extra_pills)
    footer_html = "".join(footer_pills)

    st.markdown(
        f"""
        <div class="rs-card">
          <div class="rs-card-meta">{''.join(meta_parts)}</div>
          <div class="rs-card-title">{html.escape(title)}</div>
          <div class="rs-card-footer">
            <div>{footer_html}</div>
            <a class="rs-card-link" href="{html.escape(url)}" target="_blank">Open on Reddit →</a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def score_bar_row(label: str, value: float, max_value: float = 10.0) -> str:
    """Return HTML for one row of a horizontal score bar."""
    pct = max(0.0, min(100.0, (value / max_value) * 100.0))
    return f"""
    <div class="rs-bar-row">
      <div class="rs-bar-label">{html.escape(label)}</div>
      <div class="rs-bar-track"><div class="rs-bar-fill" style="width: {pct:.1f}%"></div></div>
      <div class="rs-bar-value">{value:.1f}</div>
    </div>
    """


def score_pill(composite: float) -> str:
    """Render a neutral score pill with a subtle colored dot."""
    if composite >= 7:
        tone = "high"
    elif composite >= 4:
        tone = "mid"
    else:
        tone = "low"
    return (
        f'<span class="rs-pill rs-pill-score">'
        f'<span class="rs-score-dot rs-score-dot-{tone}"></span>'
        f'{composite:.1f} / 10'
        f'</span>'
    )


def empty_state(title: str, detail: str = "") -> None:
    detail_html = f'<div>{html.escape(detail)}</div>' if detail else ""
    st.markdown(
        f"""
        <div class="rs-empty">
          <div class="rs-empty-title">{html.escape(title)}</div>
          {detail_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# --- Onboarding ---

_WORKFLOW_STEPS = [
    ("Discover", "discovered", "Find subreddits relevant to your niche or topic"),
    ("Save a list", "saved_list", "Save your best subreddits or keywords as a reusable list"),
    ("Scan or find opportunities", "scanned", "Search for posts matching your keywords or pain-point patterns"),
    ("Save to queue", "queued", "Bookmark interesting posts you want to comment on"),
    ("Comment and track", "found_opportunities", "Open posts on Reddit, comment, then mark as done in your Queue"),
    ("Score with AI", "scored", "Run AI analysis to rank posts by pain-point potential"),
]


def welcome_screen() -> None:
    """Full welcome for first-time users (no data in DB yet)."""
    steps_html = ""
    for i, (label, _, desc) in enumerate(_WORKFLOW_STEPS, 1):
        steps_html += f"""
        <div class="rs-step">
          <div class="rs-step-num">{i}</div>
          <div>
            <div class="rs-step-label">{html.escape(label)}</div>
            <div class="rs-step-desc">{html.escape(desc)}</div>
          </div>
        </div>
        """

    st.markdown(
        f"""
        <div class="rs-welcome">
          <div class="rs-welcome-title">Welcome to RedditScout</div>
          <div class="rs-welcome-sub">
            Find high-value Reddit posts, save them to a queue, comment to grow your
            presence, and track your progress — all from one dashboard.
          </div>
          {steps_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info("Start by going to **Discover** in the sidebar and searching for a topic related to your niche.")


def progress_tracker(progress: dict) -> None:
    """Show workflow steps with completion status."""
    steps_html = ""
    for i, (label, key, desc) in enumerate(_WORKFLOW_STEPS, 1):
        done = progress.get(key, False)
        num_class = "rs-step-num done" if done else "rs-step-num pending"
        marker = "✓" if done else str(i)
        steps_html += f"""
        <div class="rs-step">
          <div class="{num_class}">{marker}</div>
          <div>
            <div class="rs-step-label">{html.escape(label)}</div>
            <div class="rs-step-desc">{html.escape(desc)}</div>
          </div>
        </div>
        """

    completed = progress.get("completed", 0)
    total = progress.get("total", 6)

    st.markdown(
        f"""
        <div class="rs-welcome" style="padding: 1.5rem 1.75rem;">
          <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:0.75rem;">
            <div style="font-weight:600; font-size:1.05rem; color:var(--text);">Getting started</div>
            <div style="font-size:0.82rem; color:var(--text-3);">{completed} of {total} done</div>
          </div>
          {steps_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def tip(text: str) -> None:
    """Contextual tip shown at the top of a tab."""
    st.markdown(
        f'<div class="rs-tip">{text}</div>',
        unsafe_allow_html=True,
    )
