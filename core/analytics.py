"""Deterministic sales math. The LLM never computes or forecasts any of these numbers."""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from core import i18n

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MA_DAYS = 14             # forecast = average lb/day over the last 14 days
MARKDOWN_SHELF_SHARE = 0.5  # only mark down lots with half or less of their shelf life left
RESTOCK_COVER_DAYS = 2   # perishable stock: buy only enough for 2 days of demand


def load_data(data_dir=DATA_DIR):
    catalog = pd.read_csv(data_dir / "catalog.csv")
    sales = pd.read_csv(data_dir / "sales.csv", parse_dates=["date"])
    inventory = pd.read_csv(data_dir / "inventory.csv", parse_dates=["caught_at"])
    settings = json.loads((data_dir / "settings.json").read_text(encoding="utf-8"))
    return catalog, sales, inventory, settings


def load_buyers(data_dir=DATA_DIR):
    return pd.read_csv(data_dir / "buyers.csv")


def _lbs_by_product(sales, days, offset_days=0):
    end = sales["date"].max() - pd.Timedelta(days=offset_days)
    start = end - pd.Timedelta(days=days)
    window = sales[(sales["date"] > start) & (sales["date"] <= end)]
    return window.groupby("product_id")


def product_table(catalog, sales, inventory, as_of, hours_ahead=0, lang="en"):
    """One row per product with demand, margin, freshness and the rule-based action.

    hours_ahead simulates the clock moving forward: stock drops at the 14-day average
    sales rate and every lot ages by the same hours. No restocking is simulated.
    """
    t = catalog.merge(inventory, on="product_id", how="left").set_index("product_id")
    t["stock_lbs"] = t["stock_lbs"].fillna(0)

    recent = _lbs_by_product(sales, MA_DAYS)["lbs"].sum().reindex(t.index, fill_value=0) / MA_DAYS
    if hours_ahead:
        t["stock_lbs"] = (t["stock_lbs"] - recent * hours_ahead / 24).clip(lower=0).round(1)
        as_of = as_of + pd.Timedelta(hours=hours_ahead)
    previous = _lbs_by_product(sales, MA_DAYS, MA_DAYS)["lbs"].sum().reindex(t.index, fill_value=0) / MA_DAYS
    t["avg_daily_lbs"] = recent.round(1)
    t["trend_pct"] = ((recent - previous) / previous.replace(0, np.nan) * 100).round(0)

    last30 = _lbs_by_product(sales, 30)
    lbs_30 = last30["lbs"].sum().reindex(t.index, fill_value=0)
    t["revenue_30d"] = last30["revenue"].sum().reindex(t.index, fill_value=0).round(0)
    t["margin_30d"] = (t["revenue_30d"] - lbs_30 * t["unit_cost"]).round(0)
    t["margin_pct"] = (t["margin_30d"] / t["revenue_30d"].replace(0, np.nan) * 100).round(0)

    # A lot with no catch time (e.g. stock just added in the app) is treated as fresh
    age_h = ((as_of - t["caught_at"]).dt.total_seconds() / 3600).fillna(0)
    hours_left = (t["shelf_life_h"] - age_h).clip(lower=0)
    t["hours_left"] = hours_left.where(t["stock_lbs"] > 0, 0).round(0)
    t["expected_sales_lbs"] = (recent * t["hours_left"] / 24).round(1)
    t["at_risk_lbs"] = (t["stock_lbs"] - t["expected_sales_lbs"]).clip(lower=0).round(1)
    t["days_of_cover"] = (t["stock_lbs"] / recent.replace(0, np.nan)).round(1)
    t["value_at_risk"] = (t["at_risk_lbs"] * t["unit_cost"]).round(0)

    actions = pd.DataFrame(
        [_action(row, lang) for row in t.itertuples()],
        index=t.index,
        columns=["action", "suggested_price", "reorder_lbs", "reason"],
    )
    return t.join(actions).reset_index()


def _action(r, lang="en"):
    """Fixed rules. Order matters: out of stock, spoiled, spoilage risk, then low cover."""
    if r.stock_lbs <= 0:
        qty = math.ceil(r.avg_daily_lbs * RESTOCK_COVER_DAYS)
        return ("Restock", r.list_price, qty,
                i18n.reason("Restock", lang, avg=r.avg_daily_lbs, qty=qty, days=RESTOCK_COVER_DAYS))
    if r.hours_left <= 0:
        return ("Discard", r.list_price, 0,
                i18n.reason("Discard", lang, shelf=f"{r.shelf_life_h:.0f}", stock=f"{r.stock_lbs:g}",
                            loss=f"{r.stock_lbs * r.unit_cost:,.0f}"))
    if r.hours_left <= r.shelf_life_h * MARKDOWN_SHELF_SHARE and r.at_risk_lbs > 0:
        pct = 0.15 if r.at_risk_lbs / r.stock_lbs > 0.4 else 0.10
        price = max(r.floor_price, round(r.list_price * (1 - pct)))
        return ("Mark down", price, 0,
                i18n.reason("Mark down", lang, risk=f"{r.at_risk_lbs:g}", stock=f"{r.stock_lbs:g}",
                            hours=f"{r.hours_left:.0f}", pct=f"{pct:.0%}", price=price, floor=r.floor_price))
    if r.days_of_cover < 1:
        qty = math.ceil(r.avg_daily_lbs * RESTOCK_COVER_DAYS - r.stock_lbs)
        return ("Restock soon", r.list_price, qty,
                i18n.reason("Restock soon", lang, cover=r.days_of_cover, avg=r.avg_daily_lbs, qty=qty))
    return ("OK", r.list_price, 0, i18n.reason("OK", lang))


def deal_summary(check, table, settings):
    """Profit of one buyer request if the seller accepts it as written. None if a quantity is missing."""
    if not check.items or any(i.qty_lbs is None for i in check.items):
        return None
    rows = table.set_index("product_id")
    lines = []
    for it in check.items:
        r = rows.loc[it.pid]
        price = it.offer_per_lb if it.offer_per_lb is not None else r["list_price"]
        lines.append({"product": r["name"], "lbs": it.qty_lbs, "price": price,
                      "revenue": it.qty_lbs * price, "cost": it.qty_lbs * r["unit_cost"],
                      "list_revenue": it.qty_lbs * r["list_price"]})
    lines = pd.DataFrame(lines)
    revenue = check.bundle_offer if check.bundle_offer is not None else lines["revenue"].sum()
    cost = lines["cost"].sum()
    return {
        "lines": lines,
        "revenue": revenue,
        "cost": cost,
        "profit": revenue - cost,
        "margin": (revenue - cost) / revenue if revenue else 0,
        "vs_list": revenue - lines["list_revenue"].sum(),
        "delivery_fee": settings["delivery_zones"].get(check.zone) if check.zone else None,
    }


def offer_prices(check, table):
    """Offered price per lb for each item with a quantity. A whole-order offer is split by list value."""
    rows = table.set_index("product_id")
    items = [it for it in check.items if it.qty_lbs]
    if check.bundle_offer is not None and items:
        list_total = sum(it.qty_lbs * rows.loc[it.pid, "list_price"] for it in items)
        return {it.pid: check.bundle_offer * rows.loc[it.pid, "list_price"] / list_total for it in items}
    return {it.pid: it.offer_per_lb for it in items if it.offer_per_lb is not None}


def offer_scenarios(check, table):
    """Accept the offer, counter it, or reject and wait: lempiras each option brings in from the lots involved.

    Uses the same forecast as the dashboard: other buyers take avg_daily_lbs per day until the lot's
    freshness runs out; whatever is left then spoils. Fish already bought is a sunk cost, so options
    are compared on the money they bring in. None when the message has no offer below list price.
    """
    rows = table.set_index("product_id")
    qty = {it.pid: it.qty_lbs for it in check.items}
    lines = []
    for pid, offer in offer_prices(check, table).items():
        r = rows.loc[pid]
        if r["stock_lbs"] <= 0 or offer >= r["list_price"]:
            continue
        lbs = min(qty[pid], r["stock_lbs"])
        others = r["avg_daily_lbs"] * r["hours_left"] / 24      # lb other buyers take before it spoils
        rest = min(others, r["stock_lbs"] - lbs)                 # sold to others if this deal closes
        waited = min(others, r["stock_lbs"])                     # sold to others if it does not
        lp = r["list_price"]
        walk_away = (waited - rest) * lp / lbs                   # lowest price/lb that still beats waiting
        counter = int(min(lp, max((offer + lp) / 2, walk_away)) + 0.5)
        lines.append({
            "pid": pid, "product": r["name"], "lbs": lbs, "offer": round(offer, 2), "list": lp,
            "floor": r["floor_price"], "walk_away": round(walk_away, 1), "counter": counter,
            "accept": lbs * offer + rest * lp, "counter_value": lbs * counter + rest * lp, "wait": waited * lp,
            "spoil_accept": r["stock_lbs"] - lbs - rest, "spoil_wait": r["stock_lbs"] - waited,
            "unit_cost": r["unit_cost"],
        })
    if not lines:
        return None
    lines = pd.DataFrame(lines)
    return {
        "lines": lines,
        "accept": lines["accept"].sum(),
        "counter": lines["counter_value"].sum(),
        "wait": lines["wait"].sum(),
        "spoil_accept_lbs": lines["spoil_accept"].sum(),
        "spoil_wait_lbs": lines["spoil_wait"].sum(),
        "spoil_wait_cost": (lines["spoil_wait"] * lines["unit_cost"]).sum(),
    }


def match_buyers(lot, buyers, settings, top=3):
    """Rank regular buyers for a lot at risk: species 50, volume fit 30, zone 10, recent order 10."""
    zones = settings["delivery_zones"]
    max_fee = max(zones.values()) or 1

    def score(b):
        species = 50 if lot["product_id"] in b["preferred_products"].split("|") else 0
        volume = 30 * min(b["typical_lbs"], lot["at_risk_lbs"]) / lot["at_risk_lbs"] if lot["at_risk_lbs"] else 0
        zone = 10 * (1 - zones[b["zone"]] / max_fee) if b["zone"] in zones else 0
        recent = 10 if b["last_order_days_ago"] <= 7 else 5 if b["last_order_days_ago"] <= 14 else 0
        return round(species + volume + zone + recent)

    ranked = buyers.assign(match=buyers.apply(score, axis=1)).sort_values("match", ascending=False)
    ranked["offer_lbs"] = ranked["typical_lbs"].clip(upper=lot["at_risk_lbs"]).round(0)
    return ranked.head(top)


def daily_revenue(sales, days=30):
    daily = sales.groupby("date")["revenue"].sum()
    return daily[daily.index > daily.index.max() - pd.Timedelta(days=days)].rename("Revenue (L)")
