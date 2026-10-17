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


def _contested(checks, rows):
    """The lot(s) the queue is about: products other buyers name, else everything on ice."""
    named = list(dict.fromkeys(it.pid for *_, c in checks for it in c.items))
    return named or [pid for pid, r in rows.iterrows() if r["stock_lbs"] > 0]


def _lines(text, table, settings, lang):
    rows = table.set_index("product_id")
    checks = [(arrival, buyer, msg, guard.check_message(msg, table, settings, lang))
              for arrival, (buyer, msg) in enumerate(split_messages(text))]
    lines = []
    for arrival, buyer, msg, c in checks:
        codes = {code for code, _ in c.flags}
        prices = analytics.offer_prices(c, table)
        base = {"arrival": arrival, "buyer": buyer, "message": msg, "zone": c.zone, "when_h": c.when_h,
                "credit": "PAY_LATER" in codes, "outside_zone": "ZONE_UNKNOWN" in codes, "takes_all": False}
        items = [(it.pid, float(it.qty_lbs or 0), prices.get(it.pid)) for it in c.items]
        if not items and guard.asks_for_everything(msg):
            # "Quiero todo su producto disponible": all the pounds on ice of the lot, at list price
            base["takes_all"] = True
            if base["when_h"] is None and guard.SOON_RE.search(c.text):
                base["when_h"] = 0
            items = [(pid, float(max(rows.loc[pid, "stock_lbs"], 0)), None) for pid in _contested(checks, rows)]
        if not items:
            lines.append({**base, "pid": None, "product": None, "lbs": 0.0, "price": 0.0, "tier": 3,
                          "needs_today": False, "unavailable": True})
            continue
        for pid, lbs, offer in items:
            r = rows.loc[pid]
            unavailable = r["stock_lbs"] <= 0 or pid in settings.get("closed_season", [])
            needs_today = bool(base["when_h"]) and r["hours_left"] < base["when_h"] + guard.FRESHNESS_BUFFER_H
            tier = 3 if (unavailable or base["outside_zone"]) else 2 if base["credit"] else 1 if needs_today else 0
            lines.append({**base, "pid": pid, "product": r["name"], "lbs": lbs,
                          "price": round(float(offer if offer is not None else r["list_price"]), 2), "tier": tier,
                          "needs_today": needs_today, "unavailable": unavailable})
    return pd.DataFrame(lines)


def other_catch(text, table, settings):
    """Spanish list of what else is on ice today (not the contested lot), for buyers who want everything."""
    rows = table.set_index("product_id")
    checks = [(0, b, m, guard.check_message(m, table, settings)) for b, m in split_messages(text)]
    lot = set(_contested(checks, rows))
    specials, regular = [], []
    for pid, r in rows.iterrows():
        if pid in lot or r["stock_lbs"] <= 0:
            continue
        if r["action"] == "Mark down":  # today's specials first, like the menu reply
            specials.append(f"{r['name'].lower()} a L {r['suggested_price']:g} (precio especial)")
        else:
            regular.append(f"{r['name'].lower()} a L {r['list_price']:g}")
    out = specials + regular
    return out[0] if len(out) == 1 else ", ".join(out[:-1]) + " y " + out[-1] if out else ""


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


def reply(ln, others=""):
    """Short Spanish reply for one buyer, from the allocation (template, no LLM).
    others: what else is on ice today, offered to buyers who asked for everything."""
    if ln["pid"] is None:
        return "¡Buenas! ¿Qué producto busca? Hoy tengo camarón, pargo, róbalo, langosta y macarela."
    name = ln["product"].lower()
    if ln.get("takes_all") and ln["gets"] > 0 and not ln["unavailable"] and not ln["outside_zone"]:
        text = f"¡Buenas! De {name} tengo {ln['gets']:g} lb a L {ln['price']:g} la libra y se las aparto todas."
        if others:
            text += f" También tengo hoy {others}, todo por libra."
        if ln["credit"]:
            text += " Por ser producto fresco, el pago sería al recibir."
        return text + " ¿Le confirmo?"
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
