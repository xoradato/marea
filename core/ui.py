"""Presentation helpers: the sea header (waves, bubbles, a sea turtle) and the two reply status panels.

Design rules applied (impeccable / taste-skill / ui-ux-pro-max, Operate mode): one accent (sea teal) used
for actions and state, tone steps instead of borders and shadows, one icon family (Material Symbols),
no eyebrow labels, status always carries text, WCAG AA contrast on every text/background pair.
Custom colors are translucent tints, so the same CSS works in the light and the dark theme; the header
keeps its own deep-sea colors in both.
"""
from urllib.parse import quote

import streamlit as st

from core.i18n import t

# Abstract sea: two organic swells and two current lines, stretched to the header size
WAVES = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 260' preserveAspectRatio='none'>
<path d='M640,0 C820,40 900,150 1110,168 C1250,180 1360,132 1440,118 L1440,0 Z' fill='#0C6E7A' opacity='.35'/>
<path d='M0,260 L0,176 C250,126 430,228 710,192 C960,158 1130,70 1440,96 L1440,260 Z' fill='#0E5E73' opacity='.55'/>
<path d='M0,236 C300,204 520,252 820,218 C1080,188 1260,216 1440,202 L1440,260 L0,260 Z' fill='#0C6E7A' opacity='.45'/>
<path d='M0,146 C300,104 600,196 900,146 S1300,112 1440,152' fill='none' stroke='#8FD3C9' stroke-opacity='.22' stroke-width='1.5'/>
<path d='M0,168 C320,132 610,214 930,170 S1310,140 1440,176' fill='none' stroke='#8FD3C9' stroke-opacity='.14' stroke-width='1.2'/>
</svg>"""

# Minimal line-art sea turtle swimming up-left, with a trail of bubbles. Decorative only.
TURTLE = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 320 200'>
<g fill='#8FD3C9' fill-opacity='.35'>
<circle cx='96' cy='44' r='4'/><circle cx='118' cy='24' r='2.6'/><circle cx='74' cy='70' r='3'/>
<circle cx='132' cy='52' r='1.8'/><circle cx='60' cy='36' r='2.2'/><circle cx='104' cy='88' r='1.6'/>
<circle cx='40' cy='60' r='1.4'/><circle cx='146' cy='14' r='1.6'/>
</g>
<g transform='translate(118 6) rotate(-28 100 95)' fill='none' stroke='#CDEFE9' stroke-width='2.4'
   stroke-linejoin='round' stroke-linecap='round'>
<path d='M66 66 C40 50 22 60 18 74 C34 74 52 76 68 84 Z' fill='#8FD3C9' fill-opacity='.14'/>
<path d='M134 66 C160 50 178 60 182 74 C166 74 148 76 132 84 Z' fill='#8FD3C9' fill-opacity='.14'/>
<path d='M72 124 C58 132 52 144 56 152 C66 148 76 140 82 130 Z' fill='#8FD3C9' fill-opacity='.14'/>
<path d='M128 124 C142 132 148 144 144 152 C134 148 124 140 118 130 Z' fill='#8FD3C9' fill-opacity='.14'/>
<path d='M95 139 L100 152 L105 139'/>
<ellipse cx='100' cy='28' rx='13' ry='16' fill='#0B3C5D'/>
<circle cx='94.5' cy='23' r='1.8' fill='#CDEFE9' stroke='none'/>
<ellipse cx='100' cy='90' rx='40' ry='50' fill='#8FD3C9' fill-opacity='.18'/>
<path d='M100 70 L114 80 L114 100 L100 110 L86 100 L86 80 Z' stroke-opacity='.8'/>
<path d='M100 70 V41 M114 80 L136 69 M114 100 L136 111 M100 110 V139 M86 100 L64 111 M86 80 L64 69' stroke-opacity='.6'/>
</g>
</svg>"""


def _uri(svg):
    return "data:image/svg+xml," + quote(" ".join(svg.split()))


CSS = f"""
<style>
::selection {{ background: rgba(79, 184, 194, 0.35); }}
.st-key-hero {{
  background-color: #0B3C5D;
  background-image: url("{_uri(TURTLE)}"), url("{_uri(WAVES)}");
  background-repeat: no-repeat, no-repeat;
  background-position: right 2% center, center;
  background-size: auto 92%, 100% 100%;
  border-radius: 16px; padding: 6px 24px 22px;
}}
.st-key-hero h1 {{ color: #FFFFFF; font-weight: 800; font-size: 2.1rem; letter-spacing: -0.02em; }}
.st-key-hero p {{ color: #D5EAE7; margin: 0; max-width: 60ch; }}
.st-key-hero [data-testid="stIconMaterial"] {{ color: #8FD3C9; }}
@media (max-width: 760px) {{
  .st-key-hero {{ background-image: url("{_uri(WAVES)}"); background-size: 100% 100%; }}
}}
.st-key-decide {{ background: rgba(228, 87, 46, 0.14); border-radius: 12px; padding: 14px 18px; }}
.st-key-decide [data-testid="stIconMaterial"] {{ color: #D9583A; }}
.st-key-safe {{ background: rgba(27, 153, 139, 0.14); border-radius: 12px; padding: 14px 18px; }}
.st-key-safe [data-testid="stIconMaterial"] {{ color: #17897C; }}
[data-testid="stMain"] [data-testid="stMetric"] {{
  background: rgba(128, 160, 170, 0.12); border-radius: 12px; padding: 12px 16px;
}}
[data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; }}
[data-baseweb="tab"] {{ font-weight: 700; }}
[data-baseweb="tab"][aria-selected="true"] p {{ color: inherit; }}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def header(model_connected, model_name, seller, lang="en"):
    with st.container(key="hero"):
        st.title(":material/waves: Marea", anchor=False)
        st.markdown(t("tagline", lang))
        status = (":material/memory: " + t("model_on", lang, model=model_name) if model_connected
                  else ":material/cloud_off: " + t("model_off", lang))
        st.markdown(f"{status} {t('demo_seller', lang, seller=seller)}")


def decide_card(reasons, lang="en"):
    with st.container(key="decide"):
        st.markdown(":material/front_hand: " + t("decide_title", lang))
        st.markdown("\n".join(f"- {r}" for r in reasons))


def safe_card(lang="en"):
    with st.container(key="safe"):
        st.markdown(":material/check_circle: " + t("safe_title", lang))
