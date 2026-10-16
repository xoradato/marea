"""Presentation helpers: compact header with a tide line, and the two reply status panels.

Design rules applied (impeccable / taste-skill, Operate mode): one accent (sea teal) used only for
actions and state, tone steps instead of borders and shadows, one icon family (Material Symbols),
no eyebrow labels, status always carries text, WCAG AA contrast on every text/background pair.
"""
import streamlit as st

# Tide line: two offset waves in the page colour along the bottom edge of the header
TIDE = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 40' "
        "preserveAspectRatio='none'><path d='M0,22 C240,40 480,4 720,22 C960,40 1200,4 1440,22 L1440,40 L0,40 Z' "
        "fill='%23F4F7F6' opacity='0.4'/><path d='M0,30 C200,16 420,40 640,28 C860,16 1080,38 1300,28 "
        "C1370,25 1410,27 1440,30 L1440,40 L0,40 Z' fill='%23F4F7F6'/></svg>")

CSS = f"""
<style>
::selection {{ background: #BFE0DB; color: #10262F; }}
.st-key-hero {{
  background: #0B3C5D url("{TIDE}") bottom / 100% 34px no-repeat;
  border-radius: 14px; padding: 6px 24px 44px;
}}
.st-key-hero h1 {{ color: #FFFFFF; font-weight: 800; font-size: 2.1rem; letter-spacing: -0.02em; }}
.st-key-hero p {{ color: #D5EAE7; margin: 0; max-width: 70ch; }}
.st-key-hero [data-testid="stIconMaterial"] {{ color: #8FD3C9; }}
.st-key-decide {{ background: #FBE9E5; color: #6E1E10; border-radius: 12px; padding: 14px 18px; }}
.st-key-decide [data-testid="stIconMaterial"] {{ color: #B03A24; }}
.st-key-safe {{ background: #E1F1EE; color: #0B4A43; border-radius: 12px; padding: 14px 18px; }}
.st-key-safe [data-testid="stIconMaterial"] {{ color: #0C6E7A; }}
[data-testid="stMain"] [data-testid="stMetric"] {{
  background: #E8EFED; border-radius: 12px; padding: 12px 16px;
}}
[data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; }}
[data-baseweb="tab"] {{ font-weight: 700; }}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def header(model_connected, model_name, seller):
    with st.container(key="hero"):
        st.title(":material/waves: Marea", anchor=False)
        st.markdown("Drafts replies to buyers on WhatsApp and Marketplace, flags the deals you should "
                    "decide yourself, and tells you what to sell before it spoils.")
        status = (f":material/memory: Replies drafted by **{model_name}** on AMD GPUs." if model_connected
                  else ":material/cloud_off: AMD model not connected yet: replies use offline templates.")
        st.markdown(f"{status} Demo seller: {seller}. All data is synthetic.")


def decide_card(reasons):
    with st.container(key="decide"):
        st.markdown(":material/front_hand: **DECIDE TÚ.** This one needs you before sending.")
        st.markdown("\n".join(f"- {r}" for r in reasons))


def safe_card():
    with st.container(key="safe"):
        st.markdown(":material/check_circle: **Ready to send.** No rule triggered. Read the draft and send it.")
