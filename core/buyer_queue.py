"""Several buyers asking for the same stock at once: who to serve first. Decided by code, not by the LLM.

Order of service:
  tier 0  pays today and can be served as asked
  tier 1  wants delivery after the lot loses freshness (only if they take it today)
  tier 2  wants to pay later (no cash today)
  tier 3  cannot be served: out of stock, closed season or outside the delivery zones
Within a tier: highest price per pound first, then the bigger order. Serving the highest price first is
what brings the most money for the pounds on ice (pounds can be split between buyers).
"""
import re

import pandas as pd

from core import analytics, guard

NAME_RE = re.compile(r"^\s*([^\d:]{1,40}):\s*(.+)$")  # "Comedor Doña Lety: ocupo 15 lbs..." (no digits in the name)


def split_messages(text):
    """One buyer per line. 'Name: message' keeps the name; otherwise buyers are numbered."""
    out = []
    for i, line in enumerate(ln for ln in text.splitlines() if ln.strip()):
        m = NAME_RE.match(line)
        out.append((m.group(1).strip(), m.group(2).strip()) if m else (f"#{i + 1}", line.strip()))
    return out


def _lines(text, table, settings, lang):
    rows = table.set_index("product_id")
    lines = []
    for arrival, (buyer, msg) in enumerate(split_messages(text)):
        c = guard.check_message(msg, table, settings, lang)
        codes = {code for code, _ in c.flags}
        prices = analytics.offer_prices(c, table)
        base = {"arrival": arrival, "buyer": buyer, "message": msg, "zone": c.zone, "when_h": c.when_h,
                "credit": "PAY_LATER" in codes, "outside_zone": "ZONE_UNKNOWN" in codes}
        if not c.items:
            lines.append({**base, "pid": None, "product": None, "lbs": 0.0, "price": 0.0, "tier": 3,
                          "needs_today": False, "unavailable": True})
            continue
        for it in c.items:
            r = rows.loc[it.pid]
            unavailable = r["stock_lbs"] <= 0 or it.pid in settings.get("closed_season", [])
            needs_today = bool(c.when_h) and r["hours_left"] < c.when_h + guard.FRESHNESS_BUFFER_H
            tier = 3 if (unavailable or base["outside_zone"]) else 2 if base["credit"] else 1 if needs_today else 0
            lines.append({**base, "pid": it.pid, "product": r["name"], "lbs": float(it.qty_lbs or 0),
                          "price": round(float(prices.get(it.pid, r["list_price"])), 2), "tier": tier,
                          "needs_today": needs_today, "unavailable": unavailable})
    return pd.DataFrame(lines)


def _allocate(ordered, stock):
    left = dict(stock)
    gets = []
    for _, ln in ordered.iterrows():
        give = 0.0 if ln["tier"] == 3 or ln["pid"] is None else min(ln["lbs"], left[ln["pid"]])
        if give:
            left[ln["pid"]] -= give
        gets.append(give)
    out = ordered.assign(gets=gets)
    out["cash_today"] = (out["gets"] * out["price"]).where(~out["credit"], 0.0)
    return out, left


def rank(text, table, settings, lang="en"):
    """Returns None for an empty queue, else the service order, the arrival-order baseline and stock left."""
    lines = _lines(text, table, settings, lang)
    if lines.empty:
        return None
    stock = table.set_index("product_id")["stock_lbs"].to_dict()
    ranked, left = _allocate(
        lines.sort_values(["tier", "price", "lbs"], ascending=[True, False, False], kind="stable"), stock)
    fifo, _ = _allocate(lines.sort_values("arrival", kind="stable"), stock)
    return {
        "ranked": ranked.reset_index(drop=True),
        "cash_marea": float(ranked["cash_today"].sum()),
        "cash_fifo": float(fifo["cash_today"].sum()),
        "left": {pid: lbs for pid, lbs in left.items() if pid in set(lines["pid"].dropna())},
    }


def reply(ln):
    """Short Spanish reply for one buyer, from the allocation (template, no LLM)."""
    if ln["pid"] is None:
        return "¡Buenas! ¿Qué producto busca? Hoy tengo camarón, pargo, róbalo, langosta y macarela."
    name = ln["product"].lower()
    if ln["unavailable"]:
        return f"¡Buenas! Por hoy ya no tengo {name}. Le aviso con el próximo lote."
    if ln["outside_zone"]:
        return f"¡Buenas! Por ahora no hago entregas hasta allá. Si puede recogerlo, le aparto el {name}."
    if ln["lbs"] <= 0:
        return f"¡Buenas! Sí tengo {name} a L {ln['price']:g} la libra. ¿Cuántas libras ocupa?"
    if ln["gets"] <= 0:
        return f"¡Buenas! Se me terminó el {name} por hoy. Le aviso con el próximo lote."
    text = (f"¡Buenas! Le aparto {ln['gets']:g} lb de {name} a L {ln['price']:g} la libra."
            if ln["gets"] >= ln["lbs"] else
            f"¡Buenas! Solo me quedan {ln['gets']:g} lb de {name}; se las aparto a L {ln['price']:g} la libra.")
    if ln["needs_today"]:
        text += " Se lo tendría que entregar hoy para que le llegue fresco."
    if ln["credit"]:
        text += " Por ser producto fresco, el pago sería al recibir."
    return text + " ¿Le confirmo?"
