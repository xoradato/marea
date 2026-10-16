"""Coastal look for the Streamlit app: wave header, alert cards and table labels. Presentation only."""
from html import escape

import streamlit as st

ACTION_LABELS = {
    "OK": "✅ OK",
    "Mark down": "🏷️ Mark down",
    "Restock": "📦 Restock",
    "Restock soon": "📦 Restock soon",
    "Discard": "🗑️ Discard",
}

CSS = """
<style>
.marea-hero {
  position: relative; overflow: hidden; color: #fff;
  background: linear-gradient(120deg, #0B3C5D 0%, #0F7C8C 55%, #1B998B 100%);
  border-radius: 20px; padding: 26px 30px 64px; margin-bottom: 6px;
}
.marea-hero h1 { color: #fff; font-size: 2.6rem; margin: 0; padding: 0; letter-spacing: -0.5px; }
.marea-hero p { color: #DDF1EE; margin: 6px 0 14px; max-width: 760px; font-size: 1.05rem; }
.marea-kicker { font-size: 0.75rem; letter-spacing: 1.5px; text-transform: uppercase; color: #9FE3D8; }
.marea-pill {
  display: inline-block; margin: 0 8px 6px 0; padding: 4px 12px; border-radius: 999px;
  background: rgba(255,255,255,0.14); border: 1px solid rgba(255,255,255,0.25); font-size: 0.85rem;
}
.marea-wave { position: absolute; left: 0; bottom: -1px; width: 100%; height: 56px; }
.marea-card { border-radius: 14px; padding: 14px 18px; margin-bottom: 10px; }
.marea-card .title { font-weight: 800; font-size: 1.15rem; }
.marea-card ul { margin: 8px 0 0 0; padding-left: 18px; }
.marea-card li { margin-bottom: 3px; }
.marea-decide { background: #FDECE6; border-left: 6px solid #E4572E; color: #6B1F0B; }
.marea-safe { background: #E3F4F1; border-left: 6px solid #1B998B; color: #0B4A43; }
[data-testid="stMain"] [data-testid="stMetric"] {
  background: #FFFFFF; border: 1px solid #E4D8C3; border-radius: 14px;
  padding: 12px 16px; box-shadow: 0 1px 3px rgba(19, 41, 61, 0.06);
}
[data-baseweb="tab"] { font-weight: 600; }
</style>
"""

WAVE = ('<svg class="marea-wave" viewBox="0 0 1440 90" preserveAspectRatio="none">'
        '<path d="M0,50 C180,90 360,10 540,40 C720,70 900,20 1080,45 C1260,70 1350,40 1440,50 L1440,90 L0,90 Z" '
        'fill="#FBF7F0" opacity="0.35"/>'
        '<path d="M0,60 C200,30 400,90 620,60 C840,30 1040,85 1240,60 C1340,48 1400,55 1440,62 L1440,90 L0,90 Z" '
        'fill="#FBF7F0"/></svg>')


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(model_status, seller):
    pills = "".join(f'<span class="marea-pill">{escape(p)}</span>'
                    for p in (model_status, seller, "Synthetic demo data"))
    st.markdown(
        f'<div class="marea-hero"><div class="marea-kicker">Sales copilot · Honduran coast</div>'
        f'<h1>🌊 Marea</h1><p>Drafts replies to buyers on WhatsApp and Marketplace, flags the deals you should '
        f'decide yourself, and tells you what to sell before it spoils.</p>{pills}{WAVE}</div>',
        unsafe_allow_html=True)


def decide_card(reasons):
    items = "".join(f"<li>{escape(r)}</li>" for r in reasons)
    st.markdown(f'<div class="marea-card marea-decide"><div class="title">⚓ DECIDE TÚ</div>'
                f'This one needs you before sending.<ul>{items}</ul></div>', unsafe_allow_html=True)


def safe_card():
    st.markdown('<div class="marea-card marea-safe"><div class="title">✅ Ready to send</div>'
                'No rule triggered. Read the draft and send it.</div>', unsafe_allow_html=True)
