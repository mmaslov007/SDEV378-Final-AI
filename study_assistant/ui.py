"""Visual design system for the AI Study Assistant Streamlit app.

Centralizes the warm-light emerald/black theme, typography, and the reusable
HTML/CSS components (full-bleed sticky nav, hero, section cards, footer) so the
page logic in ``app.py`` stays focused on behavior. Streamlit can't be styled
like a React app, so we lean on one curated stylesheet plus small HTML helpers
rendered through ``st.markdown(..., unsafe_allow_html=True)``.

The layout is a single, centered, scrollable column — a conventional landing
page: a sticky top nav (logo + StudyAI at the far right, live status to its
left), a hero with one "Generate Quiz" call to action, and the former sidebar
controls folded into the page as a step-by-step flow.
"""

from __future__ import annotations

import streamlit as st


# Palette --------------------------------------------------------------------
EMERALD = "#059669"
EMERALD_LIGHT = "#10B981"
INK = "#17181A"
MUTED = "#6E6A62"


# Graduation-cap logo mark used in the nav brand.
_LOGO_SVG = """
<svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="24" height="24" rx="7" fill="url(#sa_g)"/>
  <path d="M12 6 4 9.3 12 12.6 20 9.3 12 6Z" fill="white"/>
  <path d="M7.6 11.2v3.1c0 1 2 1.9 4.4 1.9s4.4-.9 4.4-1.9v-3.1" stroke="white" stroke-width="1.3" fill="none" stroke-linecap="round"/>
  <path d="M19.4 9.6v3.4" stroke="white" stroke-width="1.2" stroke-linecap="round"/>
  <defs>
    <linearGradient id="sa_g" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse">
      <stop stop-color="#10B981"/><stop offset="1" stop-color="#047857"/>
    </linearGradient>
  </defs>
</svg>
"""


def inject_global_styles() -> None:
    """Inject fonts and the global stylesheet. Call once near the top of the page."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def render_nav(status_items: list[tuple[str, str, str]]) -> None:
    """Render the full-bleed sticky top nav: status cluster, then logo + brand.

    ``status_items`` is a list of ``(label, value, state)`` where ``state`` is
    one of ``"ok"`` (emerald), ``"off"`` (muted) or ``"neutral"`` (ink).
    """
    stats = "".join(
        f'<div class="nav-stat"><span class="ns-k">{label}</span>'
        f'<span class="ns-v {state}">{value}</span></div>'
        for label, value, state in status_items
    )
    st.markdown(
        f"""
        <div class="topnav">
          <a class="nav-brand" href="#home">{_LOGO_SVG}<span>StudyAI</span></a>
          <div class="nav-stats">{stats}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    """Render the landing hero with a single 'Generate Quiz' call to action."""
    st.markdown(
        """
        <div class="hero">
          <div class="hero-content">
            <span class="hero-badge">✦ Source-grounded study tool</span>
            <h1 class="hero-title">Study smarter from<br><span class="grad">your own material</span></h1>
            <p class="hero-subtitle">
              Upload your notes, slides, or readings and turn them into quizzes,
              flashcards, explanations, and Q&amp;A — every answer traced straight
              back to the source.
            </p>
            <div class="hero-actions">
              <a class="btn-primary" href="#material">Generate Quiz</a>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def anchor(anchor_id: str) -> None:
    """Drop an invisible scroll anchor so links can jump to a section."""
    st.markdown(f'<div id="{anchor_id}" class="anchor"></div>', unsafe_allow_html=True)


def section_header(icon: str, title: str, subtitle: str = "") -> None:
    """Render a consistent card section header with an icon chip."""
    sub_html = f'<span class="section-sub">{subtitle}</span>' if subtitle else ""
    st.markdown(
        f"""
        <div class="section-head">
          <span class="section-icon">{icon}</span>
          <span class="section-titles">
            <span class="section-title">{title}</span>
            {sub_html}
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chips(label: str, values: list[str]) -> None:
    """Render a labeled row of pill-shaped tags (e.g. detected topics)."""
    if not values:
        return
    tags = "".join(f'<span class="chip">{value}</span>' for value in values)
    st.markdown(
        f'<div class="chip-row"><span class="chip-label">{label}</span>{tags}</div>',
        unsafe_allow_html=True,
    )


def empty_hint(title: str, message: str) -> None:
    """Render a soft, centered placeholder for empty panel states."""
    st.markdown(
        f"""
        <div class="empty-hint">
          <div class="empty-title">{title}</div>
          <div class="empty-msg">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    """Render the page footer."""
    st.markdown(
        """
        <div class="footer">
          <span>StudyAI</span>
          <span>Source-grounded study generation · SDEV378 Applied AI</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


_GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

:root {
  --emerald: #059669;
  --emerald-light: #10B981;
  --ink: #17181A;
  --muted: #6E6A62;
  --bg: #FAF6EF;
  --card: #FFFFFF;
  --card-2: #FBF8F2;
  --border: #EAE3D6;
  --ring: rgba(5, 150, 105, 0.22);
  --shadow: 0 10px 28px -18px rgba(23, 24, 26, 0.30);
}

html, body, [class*="css"], .stApp, .stMarkdown, p, span, div, label, input, textarea {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
/* Kill any sideways scroll */
html, body, .stApp, [data-testid="stMain"], [data-testid="stAppViewContainer"] { overflow-x: hidden !important; max-width: 100%; }
.stApp {
  background:
    radial-gradient(1000px 480px at 12% -10%, rgba(16, 185, 129, 0.10), transparent 60%),
    radial-gradient(900px 460px at 100% 0%, rgba(5, 150, 105, 0.06), transparent 55%),
    var(--bg);
}
h1, h2, h3, h4 { font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; color: var(--ink); letter-spacing: -0.01em; }

/* Smooth in-page anchor scrolling, with offset so the fixed nav never covers a section */
html { scroll-behavior: smooth; }
[data-testid="stMain"], section.main { scroll-behavior: smooth; }
.anchor { position: relative; top: -88px; visibility: hidden; height: 0; }

/* Hide the Streamlit sidebar + header chrome — our nav and controls live in the page */
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"], [data-testid="stSidebarCollapseButton"] { display: none !important; }
[data-testid="stHeader"] { display: none; }
[data-testid="stToolbar"] { display: none; }

/* Push page content below the fixed nav */
.block-container { padding-top: 5.5rem !important; padding-bottom: 4rem; max-width: 940px; }

/* Fixed full-width top nav ------------------------------------------ */
.topnav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
  display: flex; align-items: center; gap: 1.5rem;
  height: 68px; padding: 0 clamp(1.1rem, 5vw, 3rem);
  background: rgba(255, 253, 249, 0.92); backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--border);
  box-shadow: 0 4px 22px -16px rgba(23, 24, 26, 0.4);
}
.nav-brand {
  display: inline-flex; align-items: center; gap: 0.55rem; text-decoration: none !important;
  font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 800; font-size: 1.2rem; color: var(--ink) !important;
  cursor: pointer;
}
.nav-brand:hover { opacity: 0.85; }
.nav-stats { display: flex; align-items: center; gap: 1.5rem; margin-left: auto; }
.nav-stat { display: flex; flex-direction: column; line-height: 1.15; }
.ns-k { font-size: 0.62rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: var(--muted); }
.ns-v { font-size: 0.82rem; font-weight: 700; color: var(--ink); }
.ns-v.ok { color: var(--emerald); }
.ns-v.off { color: var(--muted); }
.ns-v.neutral { color: var(--ink); }
@media (max-width: 720px) {
  .nav-stats { gap: 0.9rem; }
  .nav-stat:nth-child(3) { display: none; }
}

/* Hero --------------------------------------------------------------- */
.hero {
  position: relative; overflow: hidden; border-radius: 26px;
  padding: 3.2rem 2.6rem; margin-bottom: 1.8rem; text-align: center;
  background:
    radial-gradient(620px 300px at 50% -25%, rgba(16, 185, 129, 0.16), transparent 70%),
    linear-gradient(180deg, #FFFFFF 0%, #FBF8F2 100%);
  border: 1px solid var(--border); box-shadow: var(--shadow);
}
.hero-content { position: relative; z-index: 1; }
.hero-badge {
  display: inline-block; font-size: 0.78rem; font-weight: 600; letter-spacing: 0.03em;
  color: var(--emerald); background: rgba(5, 150, 105, 0.08);
  border: 1px solid rgba(5, 150, 105, 0.25); padding: 0.32rem 0.85rem; border-radius: 999px;
}
.hero-title { color: var(--ink) !important; font-size: 3rem; font-weight: 800; margin: 1rem 0 0.7rem; line-height: 1.06; }
.hero-title .grad {
  background: linear-gradient(120deg, var(--emerald-light), var(--emerald));
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.hero-subtitle {
  color: var(--muted); font-size: 1.06rem; max-width: 580px;
  margin: 0 auto !important; line-height: 1.6; text-align: center;
}
.hero-actions { display: flex; justify-content: center; margin-top: 1.7rem; }
.hero-actions a, .btn-primary { text-decoration: none !important; }
.btn-primary {
  font-weight: 700; color: #FFFFFF !important;
  padding: 0.8rem 1.8rem; border-radius: 13px;
  background: linear-gradient(135deg, var(--emerald-light), var(--emerald));
  box-shadow: 0 12px 24px -10px rgba(5, 150, 105, 0.7); transition: all 0.16s ease;
}
.btn-primary:hover { filter: brightness(1.05); transform: translateY(-1px); }

/* Section headers ---------------------------------------------------- */
.section-head { display: flex; align-items: center; gap: 0.7rem; margin: 0.1rem 0 0.9rem; }
.section-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 40px; height: 40px; border-radius: 12px; font-size: 1.15rem;
  background: rgba(5, 150, 105, 0.09); border: 1px solid rgba(5, 150, 105, 0.22);
}
.section-titles { display: flex; flex-direction: column; line-height: 1.2; }
.section-title { font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; font-size: 1.15rem; color: var(--ink); }
.section-sub { font-size: 0.82rem; color: var(--muted); margin-top: 2px; }

/* Cards (bordered containers) --------------------------------------- */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--card); border: 1px solid var(--border) !important;
  border-radius: 18px !important; padding: 1.5rem 1.6rem !important;
  box-shadow: var(--shadow); margin-bottom: 0.4rem;
}

/* Buttons ------------------------------------------------------------ */
.stButton > button, .stFormSubmitButton > button {
  border-radius: 12px; font-weight: 600; border: 1px solid var(--border);
  padding: 0.55rem 1rem; transition: all 0.18s ease; background: var(--card-2); color: var(--ink);
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
  border-color: var(--emerald); color: var(--emerald); transform: translateY(-1px);
}
.stButton > button[kind="primary"], .stFormSubmitButton > button {
  background: linear-gradient(135deg, var(--emerald-light), var(--emerald));
  color: #FFFFFF !important; border: none; font-weight: 700;
  box-shadow: 0 8px 18px -8px rgba(5, 150, 105, 0.6);
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button:hover {
  color: #FFFFFF !important; filter: brightness(1.05);
}
.stButton > button:disabled { opacity: 0.45; transform: none; box-shadow: none; }

/* Inputs ------------------------------------------------------------- */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div {
  border-radius: 11px !important; border-color: var(--border) !important;
  background: var(--card-2) !important; color: var(--ink) !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: var(--emerald) !important; box-shadow: 0 0 0 3px var(--ring) !important;
}
[data-testid="stFileUploaderDropzone"] {
  border-radius: 14px; border: 1.5px dashed var(--border);
  background: rgba(5, 150, 105, 0.025); transition: all 0.18s ease;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--emerald); background: rgba(5, 150, 105, 0.05); }

/* Metrics ------------------------------------------------------------ */
[data-testid="stMetric"] {
  background: var(--card-2); border: 1px solid var(--border); border-radius: 14px; padding: 0.85rem 1rem;
}
[data-testid="stMetricLabel"] { color: var(--muted); font-weight: 500; }
[data-testid="stMetricValue"] { font-family: 'Plus Jakarta Sans', sans-serif; color: var(--ink); }

/* Expanders ---------------------------------------------------------- */
[data-testid="stExpander"] {
  border: 1px solid var(--border) !important; border-radius: 14px !important;
  overflow: hidden; background: var(--card-2);
}
[data-testid="stExpander"] summary { font-weight: 600; }
[data-testid="stExpander"] summary:hover { color: var(--emerald); }

/* Chips -------------------------------------------------------------- */
.chip-row { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem; margin: 0.15rem 0 0.55rem; }
.chip-label { font-size: 0.72rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-right: 0.2rem; }
.chip {
  font-size: 0.8rem; font-weight: 600; color: var(--emerald);
  background: rgba(5, 150, 105, 0.08); border: 1px solid rgba(5, 150, 105, 0.25);
  padding: 0.22rem 0.62rem; border-radius: 999px;
}

/* Empty states ------------------------------------------------------- */
.empty-hint {
  text-align: center; padding: 1.4rem 1rem; margin: 0.4rem 0;
  border: 1px dashed var(--border); border-radius: 14px; background: rgba(5, 150, 105, 0.02);
}
.empty-title { font-weight: 600; color: var(--ink); margin-bottom: 0.2rem; }
.empty-msg { font-size: 0.86rem; color: var(--muted); }

/* Footer ------------------------------------------------------------- */
.footer {
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;
  margin-top: 2.5rem; padding-top: 1.2rem; border-top: 1px solid var(--border);
  color: var(--muted); font-size: 0.82rem;
}
.footer span:first-child { font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 800; color: var(--emerald); }

[data-testid="stRadio"] label { font-size: 0.95rem; }
hr { margin: 1rem 0; border-color: var(--border); }
[data-testid="stCaptionContainer"], .stCaption { color: var(--muted); }
</style>
"""
