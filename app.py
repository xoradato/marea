"""Marea: sales copilot for small-scale fish sellers. Run: streamlit run app.py"""
import importlib
import os
from urllib.parse import quote

import pandas as pd
import streamlit as st

from core import analytics, benchmark, buyer_queue, copilot, guard, i18n, llm, ui

# Streamlit Cloud can keep an old copy of a changed module after a redeploy. Reload any module whose
# file changed since it was loaded (dependencies first, so later modules see the new versions).
for _module in (i18n, llm, guard, analytics, copilot, benchmark, buyer_queue, ui):
    _mtime = os.path.getmtime(_module.__file__)
    if getattr(_module, "_loaded_mtime", None) != _mtime:
        importlib.reload(_module)
        _module._loaded_mtime = _mtime

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
EDITABLE = ["list_price", "floor_price", "unit_cost", "stock_lbs", "shelf_life_h"]
WHEN_ES = {0: "hoy", 24: "mañana", 48: "pasado mañana"}


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


@st.cache_data
def parser_benchmark(version):
    """Scored on the shipped synthetic data, not on the seller's edits or the simulated clock."""
    catalog, sales, inventory, settings = load(version)
    base = analytics.product_table(catalog, sales, inventory, pd.Timestamp(settings["as_of"]))
    return pd.DataFrame(benchmark.run(base, settings))


PREP_ES = {"cleaned": "Limpieza y escamado", "fillet": "Fileteado"}
PAY_ES = {"cash": "Pago: efectivo al recibir.",
          "transfer": "Pago: transferencia antes del despacho. Envíe la captura y despachamos."}


def wa_link(text):
    """WhatsApp opens with the text ready and the seller picks the chat."""
    return "https://wa.me/?text=" + quote(text)


def receipt_text(order, business):
    """Always in Spanish: it goes to the buyer."""
    lines = [f"*{business}* · Nota de pedido #{order['n']}", i18n.stamp(order["time"], "es"), ""]
    lines += [f"- {ln['lbs']:g} lb {ln['product']} × L {ln['price']:g} = L {ln['lbs'] * ln['price']:,.0f}"
              for ln in order["lines"]]
    if order["prep_total"]:
        lbs = sum(ln["lbs"] for ln in order["lines"])
        lines.append(f"{PREP_ES[order['prep']]}: {lbs:g} lb × L {order['prep_fee']} = L {order['prep_total']:,.0f} "
                     "(se pesa entero, antes de limpiar)")
    if order["fee"]:
        lines.append(f"Envío a {order['zone']}: L {order['fee']}")
    lines += [f"*Total: L {order['revenue'] + (order['fee'] or 0):,.0f}*",
              f"Entrega: {order['when'] or 'por confirmar'}", PAY_ES[order["payment"]], "", "¡Gracias por su compra!"]
    return "\n".join(lines)


def describe_items(check, lang):
    parts = []
    for it in check.items:
        part = names[it.pid] + (f" {it.qty_lbs:g} lb" if it.qty_lbs else "")
        if it.offer_per_lb is not None:
            part += f" @ L {it.offer_per_lb:g}/lb" + (i18n.t("from_total", lang) if it.offer_was_total else "")
        parts.append(part)
    if check.bundle_offer is not None:
        parts.append(i18n.t("for_everything", lang, offer=f"{check.bundle_offer:g}"))
    return "; ".join(parts) or i18n.t("no_product", lang)


FILES_VERSION = files_version()
catalog, sales, inventory, settings = load(FILES_VERSION)
as_of = pd.Timestamp(settings["as_of"])
names = dict(zip(catalog["product_id"], catalog["name"]))

for name, empty in (("log", []), ("sold", {}), ("orders", []), ("flash", {})):
    if name not in st.session_state:
        st.session_state[name] = empty

with st.sidebar:
    lang = st.radio("Language / Idioma", list(i18n.LANGS), format_func=i18n.LANGS.get,
                    horizontal=True, key="lang")
    st.caption(":material/dark_mode: " + i18n.t("night_hint", lang))


def t(key, **kw):
    return i18n.t(key, lang, **kw)


header_box = st.container()  # filled at the end, once today's numbers are known

with st.sidebar:
    st.subheader(":material/tune: " + t("controls"))
    hours_ahead = st.slider(t("sim_slider"), 0, 36, 0, step=3, help=t("sim_help"), key="hours")
    st.caption(t("demo_clock", t=i18n.stamp(as_of + pd.Timedelta(hours=hours_ahead), lang))
               + (t("simulated") if hours_ahead else ""))
    settings["closed_season"] = st.multiselect(t("closed_season"), list(names), format_func=names.get,
                                               placeholder=t("choose_products"), key="closed")
    st.divider()
    st.subheader(":material/timer: " + t("time_saved"))
    metrics_box = st.container()
    with st.expander(t("assumptions")):
        manual_s = st.number_input(t("manual_s"), 10, 600, 90, key="manual_s")
        review_s = st.number_input(t("review_s"), 5, 300, 15, key="review_s")
        st.caption(t("time_note"))

tab_reply, tab_queue, tab_dash, tab_recs, tab_setup = st.tabs(
    [":material/chat: " + t("tab_reply"), ":material/groups: " + t("tab_queue"),
     ":material/monitoring: " + t("tab_dash"), ":material/checklist: " + t("tab_recs"),
     ":material/inventory_2: " + t("tab_catalog")])

# Rendered last in the tab bar, but runs first so every tab uses the edited values
with tab_setup:
    st.write(t("catalog_intro"))
    if st.session_state.sold:
        st.caption(t("sold_caption")
                   + ", ".join(f"{names[p]} {lbs:g} lb" for p, lbs in st.session_state.sold.items()))
    current = catalog.merge(inventory[["product_id", "stock_lbs"]], on="product_id")
    edited = st.data_editor(
        current[["product_id", "name"] + EDITABLE],
        hide_index=True,
        disabled=["product_id", "name"],
        column_order=["name"] + EDITABLE,
        column_config={
            "name": t("col_product"),
            "list_price": st.column_config.NumberColumn(t("col_list"), min_value=0, format="L %d"),
            "floor_price": st.column_config.NumberColumn(t("col_floor"), min_value=0, format="L %d"),
            "unit_cost": st.column_config.NumberColumn(t("col_cost"), min_value=0, format="L %d"),
            "stock_lbs": st.column_config.NumberColumn(t("col_stock_start"), min_value=0, format="%.1f lb"),
            "shelf_life_h": st.column_config.NumberColumn(t("col_shelf"), min_value=1, max_value=240, format="%d h"),
        },
        key="catalog_editor",
    )
    for _, r in edited.iterrows():
        vals = {"name": r["name"], "list": r["list_price"], "floor": r["floor_price"], "cost": r["unit_cost"]}
        if r["floor_price"] > r["list_price"]:
            st.warning(t("warn_floor_above", **vals))
        elif r["list_price"] > 3 * r["floor_price"]:
            st.warning(t("warn_typo", **vals))
        if r["unit_cost"] > r["floor_price"]:
            st.warning(t("warn_cost", **vals))
    zones = ", ".join(f"{z} (L {fee})" for z, fee in settings["delivery_zones"].items())
    st.markdown("  \n".join([t("zones", zones=zones), t("hours", hours=settings["delivery_hours"]),
                             t("min_order", lbs=settings["min_order_lbs"]), t("tone", tone=settings["tone"])]))
    with st.expander(t("bench_expander")):
        bench = parser_benchmark(FILES_VERSION)
        st.metric(t("bench_metric"), f"{int(bench['ok'].sum())}/{len(bench)}")
        for _, r in bench[~bench["ok"]].iterrows():
            st.markdown(f"- **{t('bench_fails')}:** *{r['message']}*  \n  {r['problems']}")
        st.dataframe(bench, hide_index=True)
        st.caption(t("bench_caption"))

e = edited.set_index("product_id")
catalog = catalog.assign(**{c: catalog["product_id"].map(e[c])
                            for c in ["list_price", "floor_price", "unit_cost", "shelf_life_h"]})
sold = inventory["product_id"].map(st.session_state.sold).fillna(0)
inventory = inventory.assign(stock_lbs=(inventory["product_id"].map(e["stock_lbs"]) - sold).clip(lower=0))
table = analytics.product_table(catalog, sales, inventory, as_of, hours_ahead, lang)
rows = table.set_index("product_id")
overhead = settings["daily_overhead"]
fish_capital = float((e["stock_lbs"] * e["unit_cost"]).sum())  # fish on ice this morning, at cost
capital = fish_capital + overhead["ice"] + overhead["fuel"]


def record_order(lines, zone, when, prep="whole", payment="cash"):
    """lines: [(pid, lbs, price per lb)]. Takes the pounds off the stock and adds the order to the session."""
    fee_per_lb = settings["prep_fees"][prep]
    prep_total = sum(lbs for _, lbs, _ in lines) * fee_per_lb
    for pid, lbs, _ in lines:
        st.session_state.sold[pid] = st.session_state.sold.get(pid, 0) + lbs
    order = {
        "n": len(st.session_state.orders) + 1,
        "time": as_of + pd.Timedelta(hours=hours_ahead),
        "lines": [{"product": names[pid], "lbs": lbs, "price": price} for pid, lbs, price in lines],
        "prep": prep, "prep_fee": fee_per_lb, "prep_total": prep_total, "payment": payment,
        "revenue": sum(lbs * price for _, lbs, price in lines) + prep_total,
        "cost": sum(lbs * rows.loc[pid, "unit_cost"] for pid, lbs, _ in lines),
        # pounds the forecast said would spoil, sold instead
        "rescued": sum(min(lbs, rows.loc[pid, "at_risk_lbs"]) * price for pid, lbs, price in lines),
        "zone": zone,
        "fee": settings["delivery_zones"].get(zone) if zone else None,
        "when": when,
    }
    st.session_state.orders.append(order)
    return order

with tab_reply:
    pick = st.selectbox(t("example_label"), EXAMPLES)
    msg = st.text_area(t("buyer_msg_label"), value=pick, height=90)
    if st.button(t("draft_btn"), type="primary"):
        if not msg.strip():
            st.info(t("paste_first"))
        else:
            check = guard.check_message(msg, table, settings, lang)
            with st.spinner(t("drafting")):
                draft = copilot.draft_reply(msg, check, table, settings)
            st.session_state.active = msg
            st.session_state.replies = {"hold": draft}
            st.session_state.receipt = None
            entry = {
                "message": msg if len(msg) <= 70 else msg[:67] + "...",
                "decide_tu": bool(copilot.blocking(check.flags) or draft.review),
                "reasons": ", ".join(code for code, _ in check.flags) + (" REVIEW" if draft.review else ""),
                "source": draft.source,
            }
            log = st.session_state.log
            if log and log[-1]["message"] == entry["message"]:
                log[-1] = entry  # same message drafted again: update the row instead of repeating it
            else:
                log.append(entry)

    mode = "hold"
    if st.session_state.get("active"):
        active = st.session_state.active
        # Rules run again on every render, so flags, freshness and prices follow the clock, stock and settings
        check = guard.check_message(active, table, settings, lang)
        hold = st.session_state.replies["hold"]
        sc = analytics.offer_scenarios(check, table)
        left, right = st.columns(2, gap="large")
        with left:
            to_decide = copilot.blocking(check.flags)
            if to_decide or hold.review:
                ui.decide_card([m for _, m in to_decide] + ([t("unusual")] if hold.review else []), lang)
            elif not check.items:
                ui.info_card(t("menu_title"))
            else:
                ui.safe_card(lang)
            st.caption(t("parsed", items=describe_items(check, lang), zone=check.zone or "n/a",
                         when="n/a" if check.when_h is None else f"~{check.when_h} h"))
        with right:
            if sc:
                ln = sc["lines"]
                counter_p = ", ".join(f"L {c:g}" for c in ln["counter"])
                offer_p = ", ".join(f"L {o:g}" for o in ln["offer"])
                options = {"hold": t("opt_hold"), "counter": t("opt_counter", p=counter_p),
                           "accept": t("opt_accept", p=offer_p)}
                captions = [t("cap_hold"),
                            t("cap_counter", v=f"{sc['counter']:,.0f}"),
                            t("cap_accept", v=f"{sc['accept']:,.0f}", d=f"{sc['accept'] - sc['wait']:+,.0f}")]
                mode = st.radio(t("decision"), list(options), format_func=options.get, captions=captions,
                                key=f"mode_{abs(hash(active))}")
                cache_key = f"{mode}:{counter_p if mode == 'counter' else offer_p}"
                if mode != "hold" and cache_key not in st.session_state.replies:
                    with st.spinner(t("drafting")):
                        st.session_state.replies[cache_key] = copilot.draft_counter(
                            active, check, sc, table, settings, accept=(mode == "accept"))
                draft = hold if mode == "hold" else st.session_state.replies[cache_key]
            else:
                draft = hold
            reply_text = st.text_area(t("reply_label"), draft.text, height=130)
            st.link_button(t("open_whatsapp"), wa_link(reply_text), icon=":material/send:")
            if draft.english and lang == "en":
                st.caption(f"EN: {draft.english}")
            st.caption(t("source", s=i18n.source(draft.source, lang))
                       + (f" · {draft.seconds:.1f} s" if draft.seconds else ""))
            if draft.error:
                st.warning(t("model_failed", e=draft.error))

        # One section for the money: the three options when there is an offer, then the deal in one line
        deal = analytics.deal_summary(check, table, settings)
        if deal or sc:
            st.subheader(t("sell_or_wait") if sc else t("numbers_title"))
        if sc:
            s = st.columns(3)
            s[0].metric(t("accept_offer"), f"L {sc['accept']:,.0f}")
            s[0].caption(t("still_spoil", lbs=f"{sc['spoil_accept_lbs']:.0f}"))
            s[1].metric(t("counter_offer"), f"L {sc['counter']:,.0f}")
            s[1].caption(t("if_takes"))
            s[2].metric(t("reject_wait"), f"L {sc['wait']:,.0f}")
            s[2].caption(t("spoil_cost", lbs=f"{sc['spoil_wait_lbs']:.0f}", cost=f"{sc['spoil_wait_cost']:,.0f}"))
            ln = sc["lines"]
            walk = "; ".join(f"{p} L {w:g}/lb" for p, w in zip(ln["product"], ln["walk_away"]))
            if sc["accept"] >= sc["wait"]:
                verdict = t("v_sell_more", diff=f"{sc['accept'] - sc['wait']:,.0f}")
                verdict += t("v_any_price") if (ln["walk_away"] == 0).all() else t("v_above", walk=walk)
                if (ln["offer"] < ln["floor"]).any():
                    verdict += t("v_below_floor")
            else:
                verdict = t("v_wait_more", diff=f"{sc['wait'] - sc['accept']:,.0f}", walk=walk)
            st.markdown(verdict)
        if deal:
            fee = deal["delivery_fee"]
            st.caption(t("deal_line", rev=f"{deal['revenue']:,.0f}", cost=f"{deal['cost']:,.0f}",
                         profit=f"{deal['profit']:,.0f}", m=f"{deal['margin']:.0%}", vs=f"{deal['vs_list']:,.0f}")
                       + " " + (t("fee_note", zone=check.zone, fee=fee) if fee is not None else t("no_fee")))
        if sc:
            with st.expander(t("how_calc")):
                st.markdown(t("how_calc_text"))
                st.dataframe(sc["lines"].drop(columns=["pid", "unit_cost"]), hide_index=True)

        if check.items:
            st.subheader(t("close_order"))
            offered = analytics.offer_prices(check, table)
            if mode == "counter":
                offered = dict(zip(sc["lines"]["pid"], sc["lines"]["counter"]))
            cart = pd.DataFrame([{
                "product": names[it.pid],
                "lbs": float(min(it.qty_lbs or 0, rows.loc[it.pid, "stock_lbs"])),
                "price_per_lb": float(round(offered.get(it.pid, rows.loc[it.pid, "list_price"]))),
            } for it in check.items])
            cart = st.data_editor(
                cart, hide_index=True, num_rows="dynamic", key=f"cart_{abs(hash(active))}_{mode}",
                column_config={
                    "product": st.column_config.SelectboxColumn(t("col_product"), options=list(names.values()),
                                                                required=True),
                    "lbs": st.column_config.NumberColumn(t("cart_pounds"), min_value=0, format="%.1f"),
                    "price_per_lb": st.column_config.NumberColumn(t("cart_price"), min_value=0, format="L %d"),
                })
            st.caption(t("cart_caption"))
            fees = settings["prep_fees"]
            prep_labels = {"whole": t("prep_whole"), "cleaned": t("prep_cleaned", fee=fees["cleaned"]),
                           "fillet": t("prep_fillet", fee=fees["fillet"])}
            p1, p2 = st.columns(2)
            prep = p1.radio(t("prep"), list(prep_labels), format_func=prep_labels.get,
                            key=f"prep_{abs(hash(active))}")
            if prep != "whole":
                p1.caption(t("prep_note"))
            pay_labels = {"cash": t("pay_cash"), "transfer": t("pay_transfer")}
            payment = p2.radio(t("payment"), list(pay_labels), format_func=pay_labels.get,
                               key=f"pay_{abs(hash(active))}")
            if st.button(t("confirm_btn"), type="primary"):
                ids = {v: k for k, v in names.items()}
                cart = cart.dropna(subset=["product"])
                cart = cart[cart["lbs"].fillna(0) > 0]
                errors = [t("only_x", product=r["product"], stock=f"{rows.loc[ids[r['product']], 'stock_lbs']:g}")
                          for _, r in cart.iterrows() if r["lbs"] > rows.loc[ids[r["product"]], "stock_lbs"]]
                if cart.empty:
                    st.error(t("err_empty"))
                elif errors:
                    st.error(t("err_stock") + " ".join(errors))
                else:
                    today = any(code == "FRESHNESS" for code, _ in check.flags)
                    order = record_order([(ids[r["product"]], float(r["lbs"]), float(r["price_per_lb"]))
                                          for _, r in cart.iterrows()],
                                         check.zone, WHEN_ES.get(0 if today else check.when_h), prep, payment)
                    st.session_state.receipt = receipt_text(order, settings["business_name"])
                    st.rerun()
        if st.session_state.get("receipt"):
            st.success(t("order_confirmed"))
            st.code(st.session_state.receipt, language=None, wrap_lines=True)
            st.link_button(t("open_whatsapp"), wa_link(st.session_state.receipt), icon=":material/send:")
            st.caption(t("receipt_caption"))

    if st.session_state.log:
        with st.expander(f"{t('log_title')} ({len(st.session_state.log)})"):
            log_df = pd.DataFrame(st.session_state.log[::-1])
            log_df["source"] = log_df["source"].map(lambda s: i18n.source(s, lang))
            st.dataframe(log_df, hide_index=True, column_config={
                "message": t("log_message"), "decide_tu": st.column_config.CheckboxColumn("DECIDE TÚ"),
                "reasons": t("log_reasons"), "source": t("log_source")})

QUEUE_EXAMPLE = "\n".join([
    "Ana: buenas, me deja 10 libras de camaron a 70 y me lo lleva mañana a sambo creek",
    "Comedor Doña Lety: ocupo 15 lbs de camaron a 82 para hoy al mediodia, se las pago el viernes",
    "Carlos: quiero 4 libras de camaron, paso hoy mismo y le pago en efectivo",
    "Restaurante Brisa Norte: 12 libras de camaron a 85 para hoy en zona viva",
    "Hotelito Las Palmas: ocupo 20 lbs de camaron a 90 para pasado mañana en Tela",
])

with tab_queue:
    st.write(t("queue_intro"))
    queue_text = st.text_area(t("queue_label"), value=QUEUE_EXAMPLE, height=150)
    if st.button(t("queue_btn"), type="primary"):
        st.session_state.queue = queue_text if queue_text.strip() else None
        st.session_state.queue_done = None
        if not queue_text.strip():
            st.info(t("queue_empty"))
    if st.session_state.get("queue"):
        # Ranked again on every render, so it follows the clock, stock and orders already confirmed
        q = buyer_queue.rank(st.session_state.queue, table, settings, lang)
        rk = q["ranked"]
        c = st.columns(2)
        c[0].metric(t("cash_marea"), f"L {q['cash_marea']:,.0f}")
        c[1].metric(t("cash_fifo"), f"L {q['cash_fifo']:,.0f}")
        diff = q["cash_marea"] - q["cash_fifo"]
        st.markdown(t("cash_diff", diff=f"{diff:,.0f}") if diff > 0 else t("cash_same"))

        def notes(ln):
            if ln["pid"] is None:
                return t("n_noproduct")
            out = [t("n_out")] if ln["unavailable"] else []
            out += [t("n_zone")] if ln["outside_zone"] else []
            out += [t("n_credit")] if ln["credit"] else []
            out += [t("n_today")] if ln["needs_today"] else []
            out += [t("n_noqty")] if ln["lbs"] <= 0 else []
            return ", ".join(out) or t("n_ok")

        view = rk.assign(
            rank=range(1, len(rk) + 1),
            asks=[f"{ln['lbs']:g} lb @ L {ln['price']:g}" if ln["pid"] else "—" for _, ln in rk.iterrows()],
            gets=rk["gets"], notes=[notes(ln) for _, ln in rk.iterrows()],
            product=rk["product"].fillna("—"))
        st.dataframe(view[["rank", "buyer", "product", "asks", "gets", "cash_today", "notes"]], hide_index=True,
                     column_config={
                         "rank": t("q_rank"), "buyer": t("col_buyer"), "product": t("col_product"),
                         "asks": t("q_asks"),
                         "gets": st.column_config.NumberColumn(t("q_gets"), format="%.1f lb"),
                         "cash_today": st.column_config.NumberColumn(t("q_cash"), format="L %d"),
                         "notes": st.column_config.TextColumn(t("q_notes"), width="medium")})
        st.caption(t("left_after", left=", ".join(f"{names[p]} {lbs:g} lb" for p, lbs in q["left"].items())))
        st.caption(t("queue_rule"))

        st.subheader(t("replies_title"))
        for _, ln in rk.drop_duplicates("buyer").iterrows():
            text = buyer_queue.reply(rk[rk["buyer"] == ln["buyer"]].iloc[0])
            st.markdown(f"**{ln['buyer']}**")
            st.code(text, language=None, wrap_lines=True)
            st.link_button(t("open_whatsapp"), wa_link(text), icon=":material/send:")

        served = rk[(rk["gets"] > 0) & (rk["tier"] < 3)]
        if not served.empty and st.button(t("reserve_btn")):
            for buyer, grp in served.groupby("buyer", sort=False):
                first = grp.iloc[0]
                when = WHEN_ES.get(0 if first["needs_today"] else first["when_h"])
                record_order([(r["pid"], float(r["gets"]), float(r["price"])) for _, r in grp.iterrows()],
                             first["zone"], when, payment="cash")
            st.session_state.queue_done = served["buyer"].nunique()
            st.session_state.queue = None
            st.rerun()
    if st.session_state.get("queue_done"):
        st.success(t("reserved", n=st.session_state.queue_done))

with tab_dash:
    # Most actionable first: the lots, then today's money, then the 30-day picture
    orders = st.session_state.orders
    st.subheader(t("lots"))
    st.dataframe(
        table.assign(action=table["action"].map(lambda a: i18n.action(a, lang)))[
            ["name", "stock_lbs", "hours_left", "avg_daily_lbs", "trend_pct", "at_risk_lbs",
             "days_of_cover", "margin_pct", "action"]],
        hide_index=True,
        column_config={
            "name": t("col_product"),
            "stock_lbs": st.column_config.NumberColumn(t("col_stock"), format="%.1f lb"),
            "hours_left": st.column_config.ProgressColumn(t("col_fresh"), min_value=0, max_value=72, format="%d h"),
            "avg_daily_lbs": st.column_config.NumberColumn(t("col_sells"), format="%.1f lb"),
            "trend_pct": st.column_config.NumberColumn(t("col_trend"), format="%+d%%"),
            "at_risk_lbs": st.column_config.NumberColumn(t("col_risk"), format="%.1f lb"),
            "days_of_cover": st.column_config.NumberColumn(t("col_days"), format="%.1f"),
            "margin_pct": st.column_config.NumberColumn(t("col_margin"), format="%d%%"),
            "action": t("col_action"),
        })
    st.caption(t("dash_caption"))

    st.subheader(t("session_title"))
    sold_today = sum(x["revenue"] for x in orders)
    parts = {"fish": f"{fish_capital:,.0f}", "ice": overhead["ice"], "fuel": overhead["fuel"]}
    st.progress(min(sold_today / capital, 1.0),
                text=t("cava_progress", sold=f"{sold_today:,.0f}", capital=f"{capital:,.0f}",
                       pct=f"{sold_today / capital:.0%}"))
    st.caption(t("cava_missing", missing=f"{capital - sold_today:,.0f}", **parts) if sold_today < capital
               else t("cava_done", **parts))
    o = st.columns(4)
    o[0].metric(t("orders"), len(orders))
    o[1].metric(t("sales"), f"L {sold_today:,.0f}")
    o[2].metric(t("rescued"), f"L {sum(x['rescued'] for x in orders):,.0f}")
    o[3].metric(t("flagged"), sum(1 for x in st.session_state.log if x["decide_tu"]))
    st.caption(t("session_caption"))

    st.subheader(t("kpi_title"))
    revenue = table["revenue_30d"].sum()
    margin = table["margin_30d"].sum()
    k = st.columns(4)
    k[0].metric(t("revenue_30d"), f"L {revenue:,.0f}")
    k[1].metric(t("gross_margin", m=f"{margin / revenue:.0%}"), f"L {margin:,.0f}")
    k[2].metric(t("at_risk", v=f"{table['value_at_risk'].sum():,.0f}"), f"{table['at_risk_lbs'].sum():.0f} lb")
    k[3].metric(t("need_action"), int((table["action"] != "OK").sum()))
    st.bar_chart(analytics.daily_revenue(sales).rename(t("revenue_series")), color="#0C6E7A", height=220)

with tab_recs:
    st.write(t("recs_intro"))
    todo = table[table["action"] != "OK"]
    fine = table[table["action"] == "OK"]
    buyers = buyers_list(FILES_VERSION)
    for _, lot in todo.iterrows():
        # One block per product that needs something: the action and its rule, readable in full
        price = f" · L {lot['suggested_price']}/lb" if lot["action"] == "Mark down" else ""
        buy = f" · {t('col_buy')} {lot['reorder_lbs']:g} lb" if lot["reorder_lbs"] else ""
        st.markdown(f"#### {lot['name']}: {i18n.action(lot['action'], lang)}{price}{buy}")
        st.markdown(lot["reason"])
        if lot["action"] == "Mark down":
            pid = lot["product_id"]
            ranked = analytics.match_buyers(lot, buyers, settings)
            st.caption(t("who_title") + ". " + t("who_caption"))
            st.dataframe(
                ranked.assign(type=ranked["type"].map(lambda x: i18n.buyer_type(x, lang)))[
                    ["name", "type", "zone", "typical_lbs", "last_order_days_ago", "match", "offer_lbs"]],
                hide_index=True,
                column_config={
                    "name": t("col_buyer"), "type": t("col_type"), "zone": t("col_zone"),
                    "typical_lbs": st.column_config.NumberColumn(t("col_usual"), format="%d lb"),
                    "last_order_days_ago": st.column_config.NumberColumn(t("col_last"), format=t("days_ago")),
                    "match": st.column_config.ProgressColumn(t("col_match"), min_value=0, max_value=100, format="%d"),
                    "offer_lbs": st.column_config.NumberColumn(t("col_offer"), format="%d lb"),
                })
            if st.button(t("flash_btn"), key=f"flash_{pid}"):
                with st.spinner(t("drafting")):
                    st.session_state.flash[pid] = copilot.flash_sale_messages(lot, ranked)
            if pid in st.session_state.flash:
                msgs, res = st.session_state.flash[pid]
                for _, b in ranked.iterrows():
                    if b["buyer_id"] in msgs:
                        st.markdown(t("to_buyer", name=b["name"]))
                        st.code(msgs[b["buyer_id"]], language=None, wrap_lines=True)
                        st.link_button(t("open_whatsapp"), wa_link(msgs[b["buyer_id"]]), icon=":material/send:")
                st.caption(t("source", s=i18n.source(res.source, lang))
                           + (f" · {res.seconds:.1f} s" if res.seconds else "") + t("flash_caption"))
                if res.error:
                    st.warning(t("flash_failed", e=res.error))
        st.divider()
    if not fine.empty:
        st.caption(t("ok_line", names=", ".join(fine["name"])))
    if st.button(t("explain_btn")):
        with st.spinner(t("asking")):
            st.session_state.recs = copilot.recommendations(table, lang)
    if "recs" in st.session_state:
        recs = st.session_state.recs
        st.markdown(recs.text)
        st.caption(t("source", s=i18n.source(recs.source, lang)) + (f" · {recs.seconds:.1f} s" if recs.seconds else ""))
        if recs.error:
            st.warning(t("rec_failed", e=recs.error))

sold_now = sum(x["revenue"] for x in st.session_state.orders)
lots_to_act = int((table["action"] != "OK").sum())
ui.header(header_box, [
    ("#7FD1C7", t("pill_model_on", model=llm.model_name())) if llm.is_configured()
    else ("#F2A541", t("pill_model_off")),
    (None, t("pill_cash", sold=f"{sold_now:,.0f}", capital=f"{capital:,.0f}", pct=f"{sold_now / capital:.0%}")),
    ("#F2A541", t("pill_lots", n=lots_to_act)) if lots_to_act else ("#7FD1C7", t("pill_lots_none")),
    (None, t("pill_demo", seller=settings["business_name"])),
], lang)

with metrics_box:
    drafted = len(st.session_state.log)
    st.metric(t("replies_drafted"), drafted)
    st.metric(t("est_time_saved"), f"{drafted * max(manual_s - review_s, 0) / 60:.1f} min")

st.caption(t("footer_on") if llm.is_configured() else t("footer_off"))
