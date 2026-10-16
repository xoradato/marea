"""Rule-based checks on a buyer message.

These rules, not the LLM, decide when the seller sees "DECIDE TÚ".
"""
import re
import unicodedata
from dataclasses import dataclass, field

NUM = r"(\d+(?:[.,]\d+)?)"
QTY_RE = re.compile(rf"{NUM}\s*(?:lbs?|libras?)\b")
PRICE_RES = [
    re.compile(rf"\b(?:l|lps?)\.?\s*{NUM}"),                          # "L 60", "Lps. 60"
    re.compile(rf"{NUM}\s*(?:lempiras?|lps?)\b"),                     # "60 lempiras"
    re.compile(rf"\b(?:a|en|por)\s+{NUM}\b(?!\s*(?:lbs?|libras?))"),  # "a 60", "en 800"
    re.compile(rf"\b(?:doy|pago|ofrezco)\s+{NUM}\b(?!\s*(?:lbs?|libras?))"),  # "te doy 600"
]
DELIVERY_WORDS = ("llev", "entreg", "envi", "domicilio", "mand", "traer", "traig")
FRESHNESS_BUFFER_H = 6  # the lot must still be fresh 6 h after delivery


def normalize(text):
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _to_float(s):
    if re.fullmatch(r"\d{1,3},\d{3}", s):  # "1,200" is a thousands separator
        return float(s.replace(",", ""))
    return float(s.replace(",", "."))


@dataclass
class Check:
    product_ids: list = field(default_factory=list)
    qty_lbs: float | None = None
    offer_per_lb: float | None = None
    offer_was_total: bool = False
    zone: str | None = None
    delivery: bool = False
    when_h: int | None = None
    flags: list = field(default_factory=list)  # (code, message)


def check_message(text, table, settings):
    t = normalize(text)
    rows = table.set_index("product_id")
    c = Check()

    for pid, aliases in rows["aliases"].items():
        if any(re.search(rf"\b{a}\b", t) for a in aliases.split("|")):
            c.product_ids.append(pid)

    m = QTY_RE.search(t)
    if m:
        c.qty_lbs = _to_float(m.group(1))

    price_matches = [m for rx in PRICE_RES for m in rx.finditer(t)]
    if price_matches:
        offer = _to_float(min(price_matches, key=lambda m: m.start()).group(1))
        if c.product_ids and c.qty_lbs and offer > rows.loc[c.product_ids[0], "list_price"] * 1.5:
            offer, c.offer_was_total = offer / c.qty_lbs, True  # "10 libras por 700" is a total
        c.offer_per_lb = round(offer, 2)

    for zone in settings["delivery_zones"]:
        if normalize(zone) in t:
            c.zone = zone
    c.delivery = c.zone is not None or any(w in t for w in DELIVERY_WORDS)

    if "pasado manana" in t:
        c.when_h = 48
    elif "manana" in t:
        c.when_h = 24
    elif "hoy" in t:
        c.when_h = 0

    c.flags = _flags(c, rows, settings)
    return c


def _flags(c, rows, settings):
    flags = []
    if not c.product_ids:
        flags.append(("UNKNOWN_PRODUCT", "No product from your catalog was recognized."))
    for pid in c.product_ids:
        r = rows.loc[pid]
        if pid in settings.get("closed_season", []):
            flags.append(("CLOSED_SEASON", f"{r['name']} is marked by you as closed season."))
        if r["stock_lbs"] <= 0:
            flags.append(("OUT_OF_STOCK", f"{r['name']} is out of stock."))
        elif c.qty_lbs and c.qty_lbs > r["stock_lbs"]:
            flags.append(("OVER_STOCK", f"Asks for {c.qty_lbs:g} lb of {r['name']}; you have {r['stock_lbs']:g} lb on ice."))
        if c.when_h and r["stock_lbs"] > 0 and r["hours_left"] < c.when_h + FRESHNESS_BUFFER_H:
            flags.append(("FRESHNESS", f"Delivery in ~{c.when_h} h, but this {r['name']} lot has "
                                       f"{r['hours_left']:.0f} h of freshness left."))

    if c.offer_per_lb is not None and c.product_ids:
        r = rows.loc[c.product_ids[0]]
        if c.offer_per_lb < r["floor_price"]:
            flags.append(("BELOW_FLOOR", f"Offer L {c.offer_per_lb:g}/lb is below your floor "
                                         f"L {r['floor_price']}/lb (list L {r['list_price']})."))
        elif c.offer_per_lb < r["list_price"]:
            flags.append(("COUNTER_OFFER", f"Offer L {c.offer_per_lb:g}/lb is between your floor and list price. "
                                           "Accept or counter?"))

    if c.delivery and c.zone is None:
        zones = ", ".join(settings["delivery_zones"])
        flags.append(("ZONE_UNKNOWN", f"Delivery requested to a place outside your zones ({zones})."))
    return flags
