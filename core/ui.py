"""Coastal look for the Streamlit app: wave header and alert cards. Presentation only.

Colors were checked for WCAG AA contrast (4.5:1 for body text). Icons are inline SVG
(Lucide, ISC license) instead of emoji, and every alert carries text, not only color.
"""
from html import escape

import streamlit as st

CSS = """
<style>
.marea-hero {
  position: relative; overflow: hidden; color: #FFFFFF;
  background: linear-gradient(120deg, #0B3C5D 0%, #0E5E73 55%, #0F7C8C 100%);
  border-radius: 20px; padding: 26px 30px 64px; margin-bottom: 6px;
}
.marea-hero h1 { color: #FFFFFF; font-size: 2.6rem; margin: 0; padding: 0; letter-spacing: -0.5px;
  display: flex; align-items: center; gap: 10px; }
.marea-hero p { color: #F4FBFA; margin: 6px 0 14px; max-width: 760px; font-size: 1.05rem; }
.marea-kicker { font-size: 0.75rem; letter-spacing: 1.5px; text-transform: uppercase; color: #9FE3D8; }
.marea-pill {
  display: inline-flex; align-items: center; gap: 6px; margin: 0 8px 6px 0; padding: 4px 12px;
  border-radius: 999px; background: rgba(11, 60, 93, 0.45); border: 1px solid rgba(255,255,255,0.3);
  font-size: 0.85rem; color: #FFFFFF;
}
.marea-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.marea-wave { position: absolute; left: 0; bottom: -1px; width: 100%; height: 56px; }
.marea-card { border-radius: 14px; padding: 14px 18px; margin-bottom: 10px; }
.marea-card .title { font-weight: 800; font-size: 1.15rem; display: flex; align-items: center; gap: 8px; }
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

WAVE = ('<svg class="marea-wave" viewBox="0 0 1440 90" preserveAspectRatio="none" aria-hidden="true">'
        '<path d="M0,50 C180,90 360,10 540,40 C720,70 900,20 1080,45 C1260,70 1350,40 1440,50 L1440,90 L0,90 Z" '
        'fill="#FBF7F0" opacity="0.35"/>'
        '<path d="M0,60 C200,30 400,90 620,60 C840,30 1040,85 1240,60 C1340,48 1400,55 1440,62 L1440,90 L0,90 Z" '
        'fill="#FBF7F0"/></svg>')


def _icon(paths, size=22):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths}</svg>')


ICON_WAVES = _icon('<path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>'
                   '<path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>'
                   '<path d="M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>',
                   size=34)
ICON_ALERT = _icon('<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>'
                   '<path d="M12 9v4"/><path d="M12 17h.01"/>')
ICON_CHECK = _icon('<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>')


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(model_connected, model_status, seller):
    dot = "#7FD1C7" if model_connected else "#F2A541"
    pills = (f'<span class="marea-pill"><span class="marea-dot" style="background:{dot}"></span>'
             f'{escape(model_status)}</span>'
             + "".join(f'<span class="marea-pill">{escape(p)}</span>' for p in (seller, "Synthetic demo data")))
    st.markdown(
        f'<div class="marea-hero"><div class="marea-kicker">Sales copilot · Honduran coast</div>'
        f'<h1>{ICON_WAVES}Marea</h1><p>Drafts replies to buyers on WhatsApp and Marketplace, flags the deals you '
        f'should decide yourself, and tells you what to sell before it spoils.</p>{pills}{WAVE}</div>',
        unsafe_allow_html=True)


def decide_card(reasons):
    items = "".join(f"<li>{escape(r)}</li>" for r in reasons)
    st.markdown(f'<div class="marea-card marea-decide" role="alert"><div class="title">{ICON_ALERT}DECIDE TÚ</div>'
                f'This one needs you before sending.<ul>{items}</ul></div>', unsafe_allow_html=True)


def safe_card():
    st.markdown(f'<div class="marea-card marea-safe"><div class="title">{ICON_CHECK}Ready to send</div>'
                'No rule triggered. Read the draft and send it.</div>', unsafe_allow_html=True)
