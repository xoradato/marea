"""Presentation helpers: the sea header (waves, bubbles, a sea turtle) and the two reply status panels.

Design rules applied (impeccable / taste-skill / ui-ux-pro-max, Operate mode): one accent (sea teal) used
for actions and state, tone steps instead of borders and shadows, one icon family (Material Symbols),
no eyebrow labels, status always carries text, WCAG AA contrast on every text/background pair.
Custom colors are translucent tints, so the same CSS works in the light and the dark theme; the header
keeps its own deep-sea colors in both.
"""
import base64
from html import escape
from pathlib import Path
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

# A trail of bubbles to the left of the turtle. Decorative only.
BUBBLES = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 320 200'>
<g fill='#8FD3C9' fill-opacity='.35'>
<circle cx='96' cy='44' r='4'/><circle cx='118' cy='24' r='2.6'/><circle cx='74' cy='70' r='3'/>
<circle cx='132' cy='52' r='1.8'/><circle cx='60' cy='36' r='2.2'/><circle cx='104' cy='88' r='1.6'/>
<circle cx='40' cy='60' r='1.4'/><circle cx='146' cy='14' r='1.6'/>
</g>
</svg>"""

# Sea turtle silhouette from iconsdb.com (CC0 1.0), alpha faded to 45%. Hosted in the repo, not hotlinked.
TURTLE_PNG = Path(__file__).resolve().parent.parent / "assets" / "turtle-faded.png"


def _uri(svg):
    return "data:image/svg+xml," + quote(" ".join(svg.split()))


def _png_uri(path):
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


CSS = f"""
<style>
::selection {{ background: rgba(79, 184, 194, 0.35); }}
.st-key-hero {{
  background-color: #0B3C5D;
  background-image: url("{_png_uri(TURTLE_PNG)}"), url("{_uri(BUBBLES)}"), url("{_uri(WAVES)}");
  background-repeat: no-repeat, no-repeat, no-repeat;
  background-position: right 4% center, right 9% center, center;
  background-size: auto 78%, auto 92%, 100% 100%;
  border-radius: 16px; padding: 8px 28px 24px; gap: 0.35rem;
}}
.st-key-hero h1 {{ color: #FFFFFF; font-weight: 800; font-size: 1.9rem; letter-spacing: -0.02em; padding-bottom: 0.2rem; }}
.st-key-hero p {{ color: #D5EAE7; max-width: 60ch; }}
.st-key-hero p.marea-tagline {{ margin: 0 0 18px; }}
.marea-pills {{ display: flex; flex-wrap: wrap; gap: 10px 12px; max-width: 70%; }}
.marea-pill {{
  display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 999px;
  background: rgba(4, 22, 36, 0.45); color: #F4FBFA; font-size: 0.85rem; font-variant-numeric: tabular-nums;
}}
.marea-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
@media (max-width: 760px) {{ .marea-pills {{ max-width: 100%; }} }}
.st-key-hero [data-testid="stIconMaterial"] {{ color: #8FD3C9; }}
@media (max-width: 760px) {{
  .st-key-hero {{ background-image: url("{_uri(WAVES)}"); background-size: 100% 100%; }}
}}
.st-key-decide, .st-key-safe, .st-key-info {{ border-radius: 12px; padding: 20px 24px; gap: 0.5rem; }}
.st-key-decide {{ background: rgba(228, 87, 46, 0.14); }}
.st-key-decide [data-testid="stIconMaterial"] {{ color: #D9583A; }}
.st-key-decide li {{ margin-bottom: 6px; }}
.st-key-safe {{ background: rgba(27, 153, 139, 0.14); }}
.st-key-safe [data-testid="stIconMaterial"] {{ color: #17897C; }}
.st-key-info {{ background: rgba(61, 90, 128, 0.14); }}
.st-key-info [data-testid="stIconMaterial"] {{ color: #3D7BB0; }}
/* Spacing rhythm (8 px grid): 16 between related items, 24-32 between groups */
.st-key-hero {{ margin-bottom: 8px; }}
[data-baseweb="tab-list"] {{ gap: 28px; }}
[data-baseweb="tab-panel"] {{ padding-top: 20px; }}
[data-testid="stMain"] [data-testid="stVerticalBlock"] {{ gap: 1.1rem; }}
[data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"] {{ gap: 10px; }}
[data-testid="stMain"] [data-testid="stMetric"] {{
  background: rgba(128, 160, 170, 0.12); border-radius: 12px; padding: 12px 16px;
}}
[data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; }}
/* Layout (minimalist-ui): readable width, calm heading scale, room between sections */
[data-testid="stMainBlockContainer"] {{ max-width: 1120px; }}
[data-testid="stMain"] h3 {{ font-size: 1.3rem; font-weight: 800; padding-top: 1.4rem; }}
[data-testid="stMain"] h4 {{ font-size: 1.05rem; font-weight: 800; padding-top: 0.6rem; }}
[data-testid="stHeaderActionElements"] {{ display: none; }}
[data-baseweb="tab"] {{ font-weight: 700; }}
[data-baseweb="tab"][aria-selected="true"] p {{ color: inherit; }}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def header(box, pills, lang="en"):
    """Compact header. pills: [(dot color or None, text)], live numbers from the session."""
    spans = "".join(
        f'<span class="marea-pill">'
        + (f'<span class="marea-dot" style="background:{dot}"></span>' if dot else "")
        + f"{escape(text)}</span>"
        for dot, text in pills)
    with box.container(key="hero"):
        st.title(":material/waves: Marea", anchor=False)
        # Tagline and pills in one block, so Streamlit's spacing between blocks cannot overlap them
        st.markdown(f'<p class="marea-tagline">{escape(t("tagline", lang))}</p>'
                    f'<div class="marea-pills">{spans}</div>', unsafe_allow_html=True)


def decide_card(reasons, lang="en"):
    with st.container(key="decide"):
        st.markdown(":material/front_hand: " + t("decide_title", lang))
        st.markdown("\n".join(f"- {r}" for r in reasons))


def info_card(text):
    with st.container(key="info"):
        st.markdown(":material/storefront: " + text)


def safe_card(lang="en"):
    with st.container(key="safe"):
        st.markdown(":material/check_circle: " + t("safe_title", lang))
