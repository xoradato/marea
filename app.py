"""Marea: sales copilot for small-scale fish sellers. Run: streamlit run app.py"""
import os

import pandas as pd
import streamlit as st

from core import analytics, copilot, guard, llm

st.set_page_config(page_title="Marea", page_icon="🐟", layout="wide")

# On Streamlit Cloud the key lives in Secrets; locally, export the env vars from .env
try:
    for key in llm.ENV_KEYS:
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = str(st.secrets[key])
except Exception:
    pass  # no secrets file when running locally

EXAMPLES = [
    "Buenas, ¿me deja 10 libras de camarón a 70 y me lo lleva mañana a Sambo Creek?",
    "Hola, ¿tiene pargo? Ocupo 5 libras para hoy aquí en La Ceiba.",
    "¿A cómo la jaiba? Quiero 20 libras.",
    "Necesito 40 libras de róbalo, ¿me lo puede llevar a San Pedro Sula el sábado? ¿Me da factura?",
]
EDITABLE = ["list_price", "floor_price", "unit_cost", "stock_lbs"]


@st.cache_data
def load():
    return analytics.load_data()


catalog, sales, inventory, settings = load()
as_of = pd.Timestamp(settings["as_of"])
names = dict(zip(catalog["product_id"], catalog["name"]))

if "log" not in st.session_state:
    st.session_state.log = []

with st.sidebar:
    st.title("🐟 Marea")
    st.caption("Sales copilot for small-scale fish sellers")
    if llm.is_configured():
        st.success(f"Model on AMD: {llm.model_name()}")
    else:
        st.warning("No AMD API key set. Using offline templates.")
    st.caption(f"Seller: {settings['business_name']} · Demo clock: {as_of:%a %d %b %Y, %H:%M}")
    settings["closed_season"] = st.multiselect(
        "Closed season (set by you)", list(names), format_func=names.get)
    st.divider()
    st.subheader("Time saved (estimate)")
    manual_s = st.number_input("Seconds to write a reply by hand", 10, 600, 90)
    review_s = st.number_input("Seconds to review a draft", 5, 300, 15)
    metrics_box = st.container()
    st.caption("Assumption-based estimate, not a measurement. All data is synthetic.")

tab_reply, tab_dash, tab_recs, tab_setup = st.tabs(
    ["1 · Reply to a buyer", "2 · Dashboard", "3 · What to do today", "⚙ Your catalog"])

# Rendered last in the tab bar, but runs first so every tab uses the edited values
with tab_setup:
    st.write("Your prices, floor prices and stock. Edit any cell; changes apply to this session only.")
    current = catalog.merge(inventory[["product_id", "stock_lbs"]], on="product_id")
    edited = st.data_editor(
        current[["product_id", "name"] + EDITABLE],
        hide_index=True,
        disabled=["product_id", "name"],
        column_config={c: st.column_config.NumberColumn(min_value=0) for c in EDITABLE},
        key="catalog_editor",
    )
    for _, r in edited[edited["floor_price"] > edited["list_price"]].iterrows():
        st.warning(f"{r['name']}: floor price is above list price.")
    zones = ", ".join(f"{z} (L {fee})" for z, fee in settings["delivery_zones"].items())
    st.markdown(f"**Delivery zones:** {zones}  \n**Delivery hours:** {settings['delivery_hours']}  \n"
                f"**Minimum order:** {settings['min_order_lbs']} lb  \n**Reply tone:** {settings['tone']}")

e = edited.set_index("product_id")
catalog = catalog.assign(**{c: catalog["product_id"].map(e[c]) for c in ["list_price", "floor_price", "unit_cost"]})
inventory = inventory.assign(stock_lbs=inventory["product_id"].map(e["stock_lbs"]))
table = analytics.product_table(catalog, sales, inventory, as_of)

with tab_reply:
    pick = st.selectbox("Example buyer message (synthetic)", EXAMPLES)
    msg = st.text_area("Buyer message (paste from WhatsApp or Marketplace)", value=pick, height=90)
    if st.button("Draft reply", type="primary"):
        if not msg.strip():
            st.info("Paste a buyer message first.")
        else:
            check = guard.check_message(msg, table, settings)
            with st.spinner("Drafting on AMD..."):
                draft = copilot.draft_reply(msg, check, table, settings)
            st.session_state.last = (check, draft)
            st.session_state.log.append({
                "message": msg if len(msg) <= 70 else msg[:67] + "...",
                "decide_tu": bool(check.flags or draft.review),
                "reasons": ", ".join(code for code, _ in check.flags) + (" REVIEW" if draft.review else ""),
                "source": draft.source,
            })

    if "last" in st.session_state:
        check, draft = st.session_state.last
        left, right = st.columns(2)
        with left:
            if check.flags or draft.review:
                st.error("**DECIDE TÚ**: this one needs you before sending.")
                for _, m in check.flags:
                    st.write(f"• {m}")
                if draft.review:
                    st.write("• The model marked this request as unusual.")
            else:
                st.success("No rule triggered. Read it and send.")
            offer = f"L {check.offer_per_lb:g}/lb" + (" (from total)" if check.offer_was_total else "") \
                if check.offer_per_lb is not None else "none"
            st.caption(
                f"Parsed by rules: products={[names[p] for p in check.product_ids] or 'none'} · "
                f"qty={check.qty_lbs or 'n/a'} lb · offer={offer} · zone={check.zone or 'n/a'} · "
                f"when={'n/a' if check.when_h is None else f'~{check.when_h} h'}")
        with right:
            st.text_area("Draft reply (edit before sending)", draft.text, height=130)
            if draft.english:
                st.caption(f"EN: {draft.english}")
            st.caption(f"Source: {draft.source}" + (f" · {draft.seconds:.1f} s" if draft.seconds else ""))
            if draft.error:
                st.warning(f"Model call failed, showing a template instead: {draft.error}")

    if st.session_state.log:
        st.subheader("Messages handled this session")
        st.dataframe(pd.DataFrame(st.session_state.log[::-1]), hide_index=True)

with tab_dash:
    revenue = table["revenue_30d"].sum()
    margin = table["margin_30d"].sum()
    k = st.columns(4)
    k[0].metric("Revenue, last 30 days", f"L {revenue:,.0f}")
    k[1].metric(f"Gross margin ({margin / revenue:.0%})", f"L {margin:,.0f}")
    k[2].metric("Stock at risk of spoiling", f"{table['at_risk_lbs'].sum():.0f} lb")
    k[3].metric("Products needing action", int((table["action"] != "OK").sum()))
    st.subheader("Daily revenue, last 30 days")
    st.line_chart(analytics.daily_revenue(sales))
    st.subheader("Products")
    st.dataframe(table[["name", "stock_lbs", "hours_left", "avg_daily_lbs", "trend_pct", "at_risk_lbs",
                        "days_of_cover", "margin_pct", "action"]], hide_index=True)
    st.caption("Computed with pandas, no LLM. Forecast = 14-day moving average of lb sold per day. "
               "At risk = stock − (avg lb/day × hours of freshness left ÷ 24).")

with tab_recs:
    st.write("Actions come from fixed rules in code. The model on AMD only explains them in plain words.")
    st.dataframe(table[["name", "action", "suggested_price", "reorder_lbs", "reason"]], hide_index=True)
    if st.button("Explain with AI"):
        with st.spinner("Asking the model on AMD..."):
            st.session_state.recs = copilot.recommendations(table)
    if "recs" in st.session_state:
        recs = st.session_state.recs
        st.markdown(recs.text)
        st.caption(f"Source: {recs.source}" + (f" · {recs.seconds:.1f} s" if recs.seconds else ""))
        if recs.error:
            st.warning(f"Model call failed, showing rule output instead: {recs.error}")

with metrics_box:
    drafted = len(st.session_state.log)
    st.metric("Replies drafted", drafted)
    st.metric("Estimated time saved", f"{drafted * max(manual_s - review_s, 0) / 60:.1f} min")

if llm.is_configured():
    st.caption("Demo with synthetic data. Language model inference runs on AMD GPUs via AMD Token Factory.")
else:
    st.caption("Demo with synthetic data. AMD model not connected yet: showing offline templates.")
