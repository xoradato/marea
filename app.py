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
def buyers_list(version):
    return analytics.load_buyers()


DAYS_ES = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MONTHS_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def receipt_text(order, business):
    t = order["time"]
    lines = [f"*{business}* · Nota de pedido #{order['n']}",
             f"{DAYS_ES[t.weekday()]} {t.day} {MONTHS_ES[t.month - 1]} {t.year}, {t:%H:%M}", ""]
    lines += [f"- {ln['lbs']:g} lb {ln['product']} × L {ln['price']:g} = L {ln['lbs'] * ln['price']:,.0f}"
              for ln in order["lines"]]
    if order["fee"]:
        lines.append(f"Envío a {order['zone']}: L {order['fee']}")
    lines += [f"*Total: L {order['revenue'] + (order['fee'] or 0):,.0f}*",
              f"Entrega: {order['when'] or 'por confirmar'}", "", "¡Gracias por su compra!"]
    return "\n".join(lines)


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

for name, empty in (("log", []), ("sold", {}), ("orders", []), ("flash", {})):
    if name not in st.session_state:
        st.session_state[name] = empty

ui.header(llm.is_configured(), llm.model_name(), settings["business_name"])

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
    st.write("Your prices, floor prices and stock at the start of the day. Edit any cell; "
             "changes apply to this session only.")
    if st.session_state.sold:
        st.caption("Sold through Marea this session (already taken off the stock everywhere else): "
                   + ", ".join(f"{names[p]} {lbs:g} lb" for p, lbs in st.session_state.sold.items()))
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
sold = inventory["product_id"].map(st.session_state.sold).fillna(0)
inventory = inventory.assign(stock_lbs=(inventory["product_id"].map(e["stock_lbs"]) - sold).clip(lower=0))
table = analytics.product_table(catalog, sales, inventory, as_of, hours_ahead)
rows = table.set_index("product_id")

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
            st.session_state.receipt = None
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
            d = st.columns(2) + st.columns(2)
            d[0].metric("Order value", f"L {deal['revenue']:,.0f}")
            d[1].metric("Product cost", f"L {deal['cost']:,.0f}")
            d[2].metric(f"Gross profit ({deal['margin']:.0%} margin)", f"L {deal['profit']:,.0f}")
            d[3].metric("vs. your list price", f"L {deal['vs_list']:,.0f}")
            fee = deal["delivery_fee"]
            st.caption("Computed with code from the parsed offer (list price where no offer was given). "
                       + (f"Delivery to {check.zone}: L {fee}, charged to the buyer." if fee is not None
                          else "No delivery fee included."))

        sc = analytics.offer_scenarios(check, table)
        if sc:
            st.subheader("Sell now or wait?")
            s = st.columns(3)
            s[0].metric("Accept offer", f"L {sc['accept']:,.0f}")
            s[0].caption(f"{sc['spoil_accept_lbs']:.0f} lb would still spoil")
            s[1].metric("Counter-offer", f"L {sc['counter']:,.0f}")
            s[1].caption("if the buyer takes it")
            s[2].metric("Reject and wait", f"L {sc['wait']:,.0f}")
            s[2].caption(f"{sc['spoil_wait_lbs']:.0f} lb spoil (L {sc['spoil_wait_cost']:,.0f} at cost)")
            ln = sc["lines"]
            walk = "; ".join(f"{p} L {w:g}/lb" for p, w in zip(ln["product"], ln["walk_away"]))
            if sc["accept"] >= sc["wait"]:
                verdict = f"Selling now at the buyer's price brings **L {sc['accept'] - sc['wait']:,.0f} more** than waiting. "
                verdict += ("Every pound in this order would otherwise spoil, so any price beats waiting."
                            if (ln["walk_away"] == 0).all() else f"Selling now beats waiting at any price above: {walk}.")
                if (ln["offer"] < ln["floor"]).any():
                    verdict += " The offer is below your floor price, but the numbers favor selling. Your call."
            else:
                verdict = (f"Waiting brings **L {sc['wait'] - sc['accept']:,.0f} more** than this offer. "
                           f"Below {walk}, selling now loses against waiting.")
            st.markdown(verdict)
            with st.expander("How this is calculated"):
                st.markdown(
                    "Lempiras each option brings in from the lots involved. Other buyers take the 14-day average "
                    "(lb/day) until the lot's freshness runs out; whatever is left then spoils. Fish already on ice "
                    "is a sunk cost, so the options are compared on money in. The counter-offer splits the "
                    "difference between the offer and your list price, never below the walk-away price.")
                st.dataframe(ln.drop(columns=["pid", "unit_cost"]), hide_index=True)
            if st.button("Draft the counter-offer (you decide whether to send it)"):
                with st.spinner("Drafting on AMD..."):
                    st.session_state.counter = (check.text, copilot.draft_counter(msg, check, sc, table, settings))
            if st.session_state.get("counter", (None,))[0] == check.text:
                cdraft = st.session_state.counter[1]
                st.text_area("Counter-offer draft (edit before sending)", cdraft.text, height=110)
                if cdraft.english:
                    st.caption(f"EN: {cdraft.english}")
                st.caption(f"Source: {cdraft.source}" + (f" · {cdraft.seconds:.1f} s" if cdraft.seconds else ""))

        if check.items:
            st.subheader("Close the order")
            offered = analytics.offer_prices(check, table)
            cart = pd.DataFrame([{
                "product": names[it.pid],
                "lbs": float(min(it.qty_lbs or 0, rows.loc[it.pid, "stock_lbs"])),
                "price_per_lb": float(round(offered.get(it.pid, rows.loc[it.pid, "list_price"]))),
            } for it in check.items])
            cart = st.data_editor(
                cart, hide_index=True, num_rows="dynamic", key=f"cart_{abs(hash(check.text))}",
                column_config={
                    "product": st.column_config.SelectboxColumn("Product", options=list(names.values()), required=True),
                    "lbs": st.column_config.NumberColumn("Pounds", min_value=0, format="%.1f"),
                    "price_per_lb": st.column_config.NumberColumn("Price / lb", min_value=0, format="L %d"),
                })
            st.caption("Prefilled with what the buyer asked for, capped at your stock. Edit pounds and prices "
                       "to what you agreed before confirming.")
            if st.button("Confirm order and update stock", type="primary"):
                ids = {v: k for k, v in names.items()}
                cart = cart.dropna(subset=["product"])
                cart = cart[cart["lbs"].fillna(0) > 0]
                errors = [f"{r['product']}: only {rows.loc[ids[r['product']], 'stock_lbs']:g} lb on ice."
                          for _, r in cart.iterrows() if r["lbs"] > rows.loc[ids[r["product"]], "stock_lbs"]]
                if cart.empty:
                    st.error("Add at least one product with pounds before confirming.")
                elif errors:
                    st.error("Not enough stock. " + " ".join(errors))
                else:
                    for _, r in cart.iterrows():
                        pid = ids[r["product"]]
                        st.session_state.sold[pid] = st.session_state.sold.get(pid, 0) + float(r["lbs"])
                    today = any(code == "FRESHNESS" for code, _ in check.flags)
                    order = {
                        "n": len(st.session_state.orders) + 1,
                        "time": as_of + pd.Timedelta(hours=hours_ahead),
                        "lines": [{"product": r["product"], "lbs": float(r["lbs"]), "price": float(r["price_per_lb"])}
                                  for _, r in cart.iterrows()],
                        "revenue": float((cart["lbs"] * cart["price_per_lb"]).sum()),
                        "cost": float(sum(r["lbs"] * rows.loc[ids[r["product"]], "unit_cost"]
                                          for _, r in cart.iterrows())),
                        "zone": check.zone,
                        "fee": settings["delivery_zones"].get(check.zone) if check.zone else None,
                        "when": {0: "hoy", 24: "mañana", 48: "pasado mañana"}.get(0 if today else check.when_h),
                    }
                    st.session_state.orders.append(order)
                    st.session_state.receipt = receipt_text(order, settings["business_name"])
                    st.rerun()
        if st.session_state.get("receipt"):
            st.success("Order confirmed. Stock, dashboard and today's actions are updated.")
            st.code(st.session_state.receipt, language=None, wrap_lines=True)
            st.caption("WhatsApp receipt: copy it with the button in the corner.")

    if st.session_state.log:
        st.subheader("Messages handled this session")
        st.dataframe(pd.DataFrame(st.session_state.log[::-1]), hide_index=True)

with tab_dash:
    revenue = table["revenue_30d"].sum()
    margin = table["margin_30d"].sum()
    k = st.columns(2) + st.columns(2)  # 2x2 so values never truncate on narrow screens
    k[0].metric("Revenue, last 30 days", f"L {revenue:,.0f}")
    k[1].metric(f"Gross margin ({margin / revenue:.0%})", f"L {margin:,.0f}")
    k[2].metric(f"At risk of spoiling (L {table['value_at_risk'].sum():,.0f} at cost)",
                f"{table['at_risk_lbs'].sum():.0f} lb")
    k[3].metric("Products needing action", int((table["action"] != "OK").sum()))
    if st.session_state.orders:
        orders = st.session_state.orders
        o_rev = sum(o["revenue"] for o in orders)
        o_profit = o_rev - sum(o["cost"] for o in orders)
        st.subheader("Confirmed in Marea this session")
        o = st.columns(3)
        o[0].metric("Orders", len(orders))
        o[1].metric("Sales", f"L {o_rev:,.0f}")
        o[2].metric("Gross profit", f"L {o_profit:,.0f}")
    st.subheader("Daily revenue, last 30 days")
    st.bar_chart(analytics.daily_revenue(sales), color="#0C6E7A")
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

    lots = table[table["action"] == "Mark down"]
    if not lots.empty:
        st.subheader("Who to offer it to")
        st.caption("Regular buyers ranked by code: buys this species 50 pts, usual order size against the pounds "
                   "at risk 30, delivery zone 10, ordered in the last week 10. Buyers are fictional.")
        buyers = buyers_list(FILES_VERSION)
        for _, lot in lots.iterrows():
            pid = lot["product_id"]
            ranked = analytics.match_buyers(lot, buyers, settings)
            st.markdown(f"**{lot['name']}**: {lot['at_risk_lbs']:g} lb at risk, today's price "
                        f"L {lot['suggested_price']}/lb")
            st.dataframe(
                ranked[["name", "type", "zone", "typical_lbs", "last_order_days_ago", "match", "offer_lbs"]],
                hide_index=True,
                column_config={
                    "name": "Buyer", "type": "Type", "zone": "Zone",
                    "typical_lbs": st.column_config.NumberColumn("Usual order", format="%d lb"),
                    "last_order_days_ago": st.column_config.NumberColumn("Last order", format="%d days ago"),
                    "match": st.column_config.ProgressColumn("Match", min_value=0, max_value=100, format="%d"),
                    "offer_lbs": st.column_config.NumberColumn("Offer", format="%d lb"),
                })
            if st.button("Draft flash-sale messages for these buyers", key=f"flash_{pid}"):
                with st.spinner("Drafting on AMD..."):
                    st.session_state.flash[pid] = copilot.flash_sale_messages(lot, ranked)
            if pid in st.session_state.flash:
                msgs, res = st.session_state.flash[pid]
                for _, b in ranked.iterrows():
                    if b["buyer_id"] in msgs:
                        st.markdown(f"To **{b['name']}**")
                        st.code(msgs[b["buyer_id"]], language=None, wrap_lines=True)
                st.caption(f"Source: {res.source}" + (f" · {res.seconds:.1f} s" if res.seconds else "")
                           + ". Nothing is sent automatically: copy each message into WhatsApp.")
                if res.error:
                    st.warning(f"Model call failed, showing templates instead: {res.error}")

with metrics_box:
    drafted = len(st.session_state.log)
    st.metric("Replies drafted", drafted)
    st.metric("Estimated time saved", f"{drafted * max(manual_s - review_s, 0) / 60:.1f} min")

if llm.is_configured():
    st.caption("Demo with synthetic data. Language model inference runs on AMD GPUs via AMD Token Factory.")
else:
    st.caption("Demo with synthetic data. AMD model not connected yet: showing offline templates.")
