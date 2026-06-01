"""Shared layout + theme components for consistent styling across all pages."""

import streamlit as st

_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..600&family=Hanken+Grotesk:wght@300..700&family=Spline+Sans+Mono:wght@400;500&display=swap');

:root{
  --paper:#F4F0E6; --paper-2:#ECE6D8; --paper-3:#E4DCC9;
  --ink:#1C1A17; --ink-soft:#544F45; --ink-faint:#8A8273;
  --green:#1F5740; --green-bright:#2E7D5B; --clay:#A8492B; --line:#D8D0BD;
  --serif:'Fraunces',Georgia,serif; --sans:'Hanken Grotesk',system-ui,sans-serif; --mono:'Spline Sans Mono',ui-monospace,monospace;
}

/* ---- canvas + base type ---- */
[data-testid="stAppViewContainer"], .stApp{background:var(--paper);}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stDecoration"]{background:linear-gradient(90deg,var(--green),var(--clay))!important;}
.stApp, .stMarkdown, p, li, label, .stMarkdown div{font-family:var(--sans);}
.stApp{color:var(--ink);}

/* ---- headings -> Fraunces ---- */
h1,h2,h3,h4,[data-testid="stHeading"]{font-family:var(--serif)!important;color:var(--ink)!important;letter-spacing:-.02em;font-weight:400!important;}
h1{font-weight:380!important;letter-spacing:-.03em;}
[data-testid="stMainBlockContainer"] h1, .block-container h1{font-size:clamp(34px,5vw,58px)!important;line-height:1.03;}
h2{font-size:clamp(26px,3vw,38px)!important;}

/* ---- body text ---- */
.stMarkdown p,.stMarkdown li{color:var(--ink-soft);font-size:16px;line-height:1.7;}
.stMarkdown strong{color:var(--ink);font-weight:600;}
a,.stMarkdown a{color:var(--green)!important;text-decoration:none;border-bottom:1px solid var(--line);transition:color .2s;}
a:hover{color:var(--green-bright)!important;border-color:var(--green-bright);}

/* ---- gentle entrance (opacity-led; safe on Streamlit reruns) ---- */
[data-testid="stMainBlockContainer"],.block-container{animation:gtFade .55s ease-out;}
@keyframes gtFade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}

/* ---- chart entrance: charts gently grow/rise in (safe: visible if animation cannot run) ---- */
[data-testid="stPlotlyChart"],[data-testid="stIFrame"]{animation:gtChartRise .7s cubic-bezier(.2,.7,.2,1);}
@keyframes gtChartRise{from{opacity:0;transform:translateY(12px) scale(.985)}to{opacity:1;transform:none}}

/* ---- dividers -> hairline ---- */
hr,[data-testid="stDivider"]{border-color:var(--line)!important;background:var(--line)!important;}

/* ---- captions -> mono ---- */
[data-testid="stCaptionContainer"],.stCaption{font-family:var(--mono)!important;color:var(--ink-faint)!important;letter-spacing:.02em;}

/* ---- metrics -> editorial cards ---- */
[data-testid="stMetric"]{background:var(--paper-2);border:1px solid var(--line);border-radius:12px;padding:18px 20px;transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease;}
[data-testid="stMetric"]:hover{transform:translateY(-2px);box-shadow:0 10px 28px rgba(28,26,23,.07);border-color:var(--green);}
[data-testid="stMetricValue"]{font-family:var(--serif)!important;font-weight:380!important;color:var(--ink)!important;font-size:36px!important;line-height:1;}
[data-testid="stMetricLabel"]{font-family:var(--mono)!important;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-faint)!important;}
[data-testid="stMetricLabel"] p{font-size:11px!important;}
[data-testid="stMetricDelta"]{color:var(--green)!important;}

/* ---- buttons -> pill ---- */
.stButton>button,[data-testid="stBaseButton-secondary"]{
  font-family:var(--mono)!important;text-transform:uppercase;letter-spacing:.1em;font-size:12px!important;
  border-radius:100px!important;border:1px solid var(--ink)!important;background:var(--ink)!important;color:var(--paper)!important;
  padding:.5rem 1.4rem!important;transition:all .25s ease!important;
}
.stButton>button:hover,[data-testid="stBaseButton-secondary"]:hover{background:var(--green)!important;border-color:var(--green)!important;color:var(--paper)!important;transform:translateY(-1px);}
[data-testid="stDownloadButton"]>button,[data-testid="stBaseButton-primary"]{background:var(--green)!important;border-color:var(--green)!important;color:var(--paper)!important;}
[data-testid="stDownloadButton"]>button:hover{background:var(--ink)!important;border-color:var(--ink)!important;}

/* ---- sidebar ---- */
[data-testid="stSidebar"]{background:var(--paper-2)!important;border-right:1px solid var(--line);}
[data-testid="stSidebar"] h1{font-family:var(--serif)!important;font-size:26px!important;}
[data-testid="stSidebarNav"]{border-bottom:1px solid var(--line);padding-bottom:8px;}
[data-testid="stSidebarNav"] a span{font-family:var(--mono)!important;font-size:12.5px!important;letter-spacing:.03em;}
[data-testid="stSidebarNav"] a:hover span{color:var(--green)!important;}

/* ---- tabs ---- */
.stTabs [data-baseweb="tab-list"]{border-bottom:1px solid var(--line);gap:6px;}
.stTabs [data-baseweb="tab"]{font-family:var(--mono)!important;text-transform:uppercase;letter-spacing:.07em;font-size:12px;color:var(--ink-faint);}
.stTabs [aria-selected="true"]{color:var(--green)!important;}
.stTabs [data-baseweb="tab-highlight"]{background:var(--green)!important;}

/* ---- dataframes / tables ---- */
[data-testid="stDataFrame"],[data-testid="stTable"]{border:1px solid var(--line)!important;border-radius:12px;overflow:hidden;}
[data-testid="stTable"] thead th{font-family:var(--mono)!important;text-transform:uppercase;letter-spacing:.05em;font-size:11px!important;color:var(--ink-faint)!important;background:var(--paper-2)!important;}

/* ---- expanders ---- */
[data-testid="stExpander"]{border:1px solid var(--line)!important;border-radius:12px!important;background:var(--paper-2);}
[data-testid="stExpander"] summary{font-family:var(--mono)!important;text-transform:uppercase;letter-spacing:.06em;font-size:12px;}

/* ---- inputs / widgets ---- */
[data-baseweb="select"]>div,[data-baseweb="input"]>div,.stTextInput input,.stNumberInput input{border-radius:8px!important;border-color:var(--line)!important;background:var(--paper)!important;font-family:var(--sans)!important;}
[data-testid="stWidgetLabel"] p,[data-testid="stWidgetLabel"] label{font-family:var(--mono)!important;text-transform:uppercase;letter-spacing:.06em;font-size:11.5px!important;color:var(--ink-faint)!important;}
[data-baseweb="slider"] [role="slider"]{background:var(--green)!important;}

/* ---- alerts ---- */
[data-testid="stAlert"]{border-radius:12px;border:1px solid var(--line)!important;border-left:3px solid var(--green)!important;background:var(--paper-2)!important;font-family:var(--sans);}
[data-testid="stAlert"] *{color:var(--ink-soft)!important;}

/* ---- hide default streamlit chrome ---- */
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}
[data-testid="stToolbar"]{display:none;}

/* ---- keep the sidebar expand control visible + on-brand (so a collapsed sidebar is easy to reopen) ---- */
[data-testid="stSidebarCollapsedControl"],[data-testid="collapsedControl"]{visibility:visible!important;opacity:1!important;}
[data-testid="stSidebarCollapsedControl"] button,[data-testid="collapsedControl"] button{color:var(--green)!important;border:1px solid var(--line)!important;background:var(--paper-2)!important;border-radius:8px!important;}
</style>
"""


def inject_theme():
    """Inject the GeneTropica editorial-science theme (fonts, palette, components, motion).

    Safe to call on every page; injecting the same <style> block twice is harmless.
    """
    st.markdown(_THEME_CSS, unsafe_allow_html=True)


def render_sidebar():
    """Render the standard GeneTropica sidebar with logo, nav guide, and footer."""
    inject_theme()
    with st.sidebar:
        st.markdown(
            '<svg width="54" height="54" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" style="margin-bottom:2px">'
            '<polygon points="32,14 48,23 48,41 32,50 16,41 16,23" fill="none" stroke="#1F5740" stroke-width="2"/>'
            '<line x1="32" y1="14" x2="32" y2="5" stroke="#1F5740" stroke-width="2"/>'
            '<circle cx="32" cy="14" r="4" fill="#F4F0E6" stroke="#1F5740" stroke-width="2"/>'
            '<circle cx="48" cy="23" r="4" fill="#F4F0E6" stroke="#1F5740" stroke-width="2"/>'
            '<circle cx="48" cy="41" r="4" fill="#F4F0E6" stroke="#1F5740" stroke-width="2"/>'
            '<circle cx="32" cy="50" r="4" fill="#F4F0E6" stroke="#1F5740" stroke-width="2"/>'
            '<circle cx="16" cy="41" r="4" fill="#F4F0E6" stroke="#1F5740" stroke-width="2"/>'
            '<circle cx="16" cy="23" r="4" fill="#F4F0E6" stroke="#1F5740" stroke-width="2"/>'
            '<circle cx="32" cy="5" r="3.5" fill="#A8492B"/>'
            "</svg>",
            unsafe_allow_html=True,
        )
        st.title("GeneTropica")
        st.caption("Drug Repurposing for Neglected Tropical Diseases")
        st.divider()
        st.markdown(
            "**Navigate** using the pages in the sidebar to explore disease targets, "
            "drug candidates, binding interactions, AI insights, methods, "
            "validation, conservation analysis, ADMET profiling, and MD simulation."
        )
        st.divider()
        st.markdown(
            "Built by [Russell Young](https://github.com/RyoungJKT)  \n"
            "British School Jakarta"
        )
