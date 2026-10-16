"""Marea: sales copilot for small-scale fish sellers. Run: streamlit run app.py"""
import os

import pandas as pd
import streamlit as st

from core import analytics, benchmark, copilot, guard, llm, ui

st.set_page_config(page_title="Marea", page_icon=":material/waves:", layout="wide")
ui.inject_css()

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
    "vecino aparteme tres libras de camaron para hoy y se las pago el viernes q me caiga la quincena",
    "buenas ocupo 8 libras de camaron, 6 de jaiba y cuatro de robalo, le doy 1100 lps por todo puesto mañana en sambo creek",
]
EDITABLE = ["list_price", "floor_price", "unit_cost", "stock_lbs"]


def files_version():
    """Changes when data, rules or test cases change, so a redeploy never serves stale cached results."""
    root = analytics.DATA_DIR.parent
    return max(p.stat().st_mtime for d in ("data", "core", "tests") for p in (root / d).glob("*.*"))


@st.cache_data
def load(version):
    return analytics.load_data()


@st.cache_data
def parser_benchmark(version):
    """Scored on the shipped synthetic data, not on the seller's edits or the simulated clock."""
    catalog, sales, inventory, settings = load(version)
    base = analytics.product_table(catalog, sales, inventory, pd.Timestamp(settings["as_of"]))
    return pd.DataFrame(benchmark.run(base, settings))


def describe_items(check):
    parts = []
    for it in check.items:
        part = names[it.pid] + (f" {it.qty_lbs:g} lb" if it.qty_lbs else "")
        if it.offer_per_lb is not None:
            part += f" @ L {it.offer_per_lb:g}/lb" + (" (from total)" if it.offer_was_total else "")
        parts.append(part)
    if check.bundle_offer is not None:
        parts.append(f"L {check.bundle_offer:g} for everything")
    return "; ".join(parts) or "no product"


FILES_VERSION = files_version()
catalog, sales, inventory, settings = load(FILES_VERSION)
as_of = pd.Timestamp(settings["as_of"])
names = dict(zip(catalog["product_id"], catalog["name"]))

if "log" not in st.session_state:
    st.session_state.log = []

ui.hero(llm.is_configured(),
        f"Model on AMD: {llm.model_name()}" if llm.is_configured() else "AMD model not connected: offline templates",
        f"Seller: {settings['business_name']}")

with st.sidebar:
    st.subheader(":material/tune: Controls")
    hours_ahead = st.slider("Simulate time: hours from now", 0, 36, 0, step=3,
                            help="Stock sells at the 14-day average and every lot ages. No restocking.")
    st.caption(f"Demo clock: {as_of + pd.Timedelta(hours=hours_ahead):%a %d %b %Y, %H:%M}"
               + (" (simulated)" if hours_ahead else ""))
    settings["closed_season"] = st.multiselect(
        "Closed season (set by you)", list(names), format_func=names.get)
    st.divider()
    st.subheader(":material/timer: Time saved (estimate)")
    manual_s = st.number_input("Seconds to write a reply by hand", 10, 600, 90)
    review_s = st.number_input("Seconds to review a draft", 5, 300, 15)
    metrics_box = st.container()
    st.caption("Assumption-based estimate, not a measurement. All data is synthetic.")

tab_reply, tab_dash, tab_recs, tab_setup = st.tabs(
    [":material/chat: Reply to a buyer", ":material/monitoring: Dashboard",
     ":material/checklist: What to do today", ":material/inventory_2: Your catalog"])

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
    with st.expander("Parser benchmark: how well the rules read buyer messages"):
        bench = parser_benchmark(FILES_VERSION)
        st.metric("Synthetic messages parsed correctly", f"{int(bench['ok'].sum())}/{len(bench)}")
        for _, r in bench[~bench["ok"]].iterrows():
            st.markdown(f"- **Fails:** *{r['message']}*  \n  {r['problems']}")
        st.dataframe(bench, hide_index=True)
        st.caption("Checks product, pounds, offer, date, zone and DECIDE TÚ flags against hand-reviewed labels "
                   "(tests/*.jsonl). Messages are synthetic, written in Honduran WhatsApp style.")

e = edited.set_index("product_id")
catalog = catalog.assign(**{c: catalog["product_id"].map(e[c]) for c in ["list_price", "floor_price", "unit_cost"]})
inventory = inventory.assign(stock_lbs=inventory["product_id"].map(e["stock_lbs"]))
table = analytics.product_table(catalog, sales, inventory, as_of, hours_ahead)

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
                ui.decide_card([m for _, m in check.flags]
                               + (["The model marked this request as unusual."] if draft.review else []))
            else:
                ui.safe_card()
            st.caption(
                f"Parsed by rules: {describe_items(check)} · zone={check.zone or 'n/a'} · "
                f"when={'n/a' if check.when_h is None else f'~{check.when_h} h'}")
        with right:
            st.text_area("Draft reply (edit before sending)", draft.text, height=130)
            if draft.english:
                st.caption(f"EN: {draft.english}")
            st.caption(f"Source: {draft.source}" + (f" · {draft.seconds:.1f} s" if draft.seconds else ""))
            if draft.error:
                st.warning(f"Model call failed, showing a template instead: {draft.error}")

        deal = analytics.deal_summary(check, table, settings)
        if deal:
            st.markdown("**If you accept as written**")
            d = st.columns(4)
            d[0].metric("Order value", f"L {deal['revenue']:,.0f}")
            d[1].metric("Product cost", f"L {deal['cost']:,.0f}")
            d[2].metric(f"Gross profit ({deal['margin']:.0%} margin)", f"L {deal['profit']:,.0f}")
            d[3].metric("vs. your list price", f"L {deal['vs_list']:,.0f}")
            fee = deal["delivery_fee"]
            st.caption("Computed with code from the parsed offer (list price where no offer was given). "
                       + (f"Delivery to {check.zone}: L {fee}, charged to the buyer." if fee is not None
                          else "No delivery fee included."))

    if st.session_state.log:
        st.subheader("Messages handled this session")
        st.dataframe(pd.DataFrame(st.session_state.log[::-1]), hide_index=True)

with tab_dash:
    revenue = table["revenue_30d"].sum()
    margin = table["margin_30d"].sum()
    k = st.columns(4)
    k[0].metric("Revenue, last 30 days", f"L {revenue:,.0f}")
    k[1].metric(f"Gross margin ({margin / revenue:.0%})", f"L {margin:,.0f}")
    k[2].metric(f"At risk of spoiling (L {table['value_at_risk'].sum():,.0f} at cost)",
                f"{table['at_risk_lbs'].sum():.0f} lb")
    k[3].metric("Products needing action", int((table["action"] != "OK").sum()))
    st.subheader("Daily revenue, last 30 days")
    st.area_chart(analytics.daily_revenue(sales), color="#0F7C8C")
    st.subheader("Lots on ice")
    st.dataframe(
        table[
            ["name", "stock_lbs", "hours_left", "avg_daily_lbs", "trend_pct", "at_risk_lbs",
             "days_of_cover", "margin_pct", "action"]],
        hide_index=True,
        column_config={
            "name": "Product",
            "stock_lbs": st.column_config.NumberColumn("Stock", format="%.1f lb"),
            "hours_left": st.column_config.ProgressColumn("Freshness left", min_value=0, max_value=72, format="%d h"),
            "avg_daily_lbs": st.column_config.NumberColumn("Sells / day", format="%.1f lb"),
            "trend_pct": st.column_config.NumberColumn("Trend", format="%+d%%"),
            "at_risk_lbs": st.column_config.NumberColumn("At risk", format="%.1f lb"),
            "days_of_cover": st.column_config.NumberColumn("Days of stock", format="%.1f"),
            "margin_pct": st.column_config.NumberColumn("Margin", format="%d%%"),
            "action": "Action",
        })
    st.caption("Computed with pandas, no LLM. Forecast = 14-day moving average of lb sold per day. "
               "At risk = stock − (avg lb/day × hours of freshness left ÷ 24).")

with tab_recs:
    st.write("Actions come from fixed rules in code. The model on AMD only explains them in plain words.")
    st.dataframe(
        table[
            ["name", "action", "suggested_price", "reorder_lbs", "reason"]],
        hide_index=True,
        column_config={
            "name": "Product",
            "action": "Action",
            "suggested_price": st.column_config.NumberColumn("Price today", format="L %d"),
            "reorder_lbs": st.column_config.NumberColumn("Buy", format="%d lb"),
            "reason": st.column_config.TextColumn("Why (rule)", width="large"),
        })
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
