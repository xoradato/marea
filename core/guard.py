"""Rule-based checks on a buyer message.

These rules, not the LLM, decide when the seller sees "DECIDE TÚ".
"""
import re
import unicodedata
from dataclasses import dataclass, field

NUM = r"(\d+(?:[.,]\d+)?)"
NUMBER_WORDS = {
    "media": 0.5, "un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
    "quince": 15, "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50,
}
NUM_OR_WORD = rf"(\d+(?:[.,]\d+)?|{'|'.join(NUMBER_WORDS)})"
UNIT = r"(?:lbs?|libras?)\b"
QTY_RE = re.compile(rf"\b{NUM_OR_WORD}\s*{UNIT}")                      # "10 lbs", "diez libras"
QTY_BEFORE_PRODUCT_RE = re.compile(                                      # "10 lbs de ", "6 de ", "cuatro de "
    rf"\b{NUM_OR_WORD}\s*(?P<unit>{UNIT})?\s*(?:de\s+)?(?:(?:la|el|los|las)\s+)?$")
PRICE_WORD_BEFORE_RE = re.compile(r"\b(?:a|en|por|x)\s*$")
PRICE_AFTER_PRODUCT_RE = re.compile(rf"\s+(?:\w+\s+){{0,2}}?(?:a|en)\s+{NUM}\b(?!\s*{UNIT})")  # "robalo a 85"
PRICE_BEFORE_PRODUCT_RE = re.compile(rf"\b(?:a|en)\s+{NUM}\s+(?:(?:el|la|los|las)\s+)?$")   # "a 70 el pargo"
PRICE_AFTER_QTY_RE = re.compile(rf"\s*a\s+{NUM}\b(?!\s*{UNIT})")                           # "10 lbs a 65"
PRICE_RES = [
    re.compile(rf"\b(?:l|lps?)\.?\s*{NUM}"),                          # "L 60", "Lps. 60"
    re.compile(rf"{NUM}\s*(?:lempiras?|lps?|pesos)\b"),               # "60 lempiras", "500 pesos"
    re.compile(rf"\b(?:a|en|por)\s+{NUM}\b(?!\s*{UNIT})"),            # "a 60", "en 800"
    re.compile(rf"\b(?:doy|pago|ofrezco)\s+{NUM}\b(?!\s*{UNIT})"),    # "le doy 600"
]
CANCELLED_RE = re.compile(r"\W*(?:pero\s+)?(?:mejor|ya)\s+no\b")       # "5 lbs de macarela pero mejor no"
DELIVERY_WORDS = ("llev", "entreg", "envi", "domicilio", "mand", "trae", "traig")
# Requests the seller must answer personally, even when price and stock are fine
SPECIAL_REQUESTS = [
    ("PAY_LATER", ("fiado", "credito", "se lo pago", "se las pago", "se los pago", "le pago el",
                   "pago despues", "quincena"), "Buyer wants to pay later."),
    ("INVOICE", ("factura", "rtn"), "Buyer asks for an invoice (factura)."),
    ("CUSTOM_PREP", ("filete", "escamad", "limpi", "sin tripa", "destripad"),
     "Buyer asks for cleaning or filleting."),
    ("FREEBIE", ("me regala", "regaleme", "gratis", "sin cobrar"),
     "Buyer asks for something free (extra product or delivery)."),
]
DISCOUNT_WORDS = ("lo menos", "rebaj", "descuento", "ultimo precio", "mas barato")
FRESHNESS_BUFFER_H = 6  # the lot must still be fresh 6 h after delivery


def normalize(text):
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _num(s):
    if s in NUMBER_WORDS:
        return NUMBER_WORDS[s]
    if re.fullmatch(r"\d{1,3},\d{3}", s):  # "1,200" is a thousands separator
        return float(s.replace(",", ""))
    return float(s.replace(",", "."))


@dataclass
class Item:
    pid: str
    qty_lbs: float | None = None
    offer_per_lb: float | None = None
    offer_was_total: bool = False


@dataclass
class Check:
    items: list = field(default_factory=list)
    bundle_offer: float | None = None  # one total price for several products
    loose_qty: float | None = None     # quantity found when no product was recognized
    zone: str | None = None
    delivery: bool = False
    when_h: int | None = None
    text: str = ""                     # normalized message
    flags: list = field(default_factory=list)  # (code, message)

    @property
    def product_ids(self):
        return [i.pid for i in self.items]

    @property
    def qty_lbs(self):
        return self.items[0].qty_lbs if self.items else self.loose_qty

    @property
    def offer_per_lb(self):
        return self.items[0].offer_per_lb if self.items else None


def check_message(text, table, settings):
    t = normalize(text)
    rows = table.set_index("product_id")
    c = Check(text=t)

    mentions = []  # (start, end, pid): first mention of each product, in message order
    for pid, aliases in rows["aliases"].items():
        m = re.search(rf"\b(?:{aliases})\b", t)
        if m:
            mentions.append((m.start(), m.end(), pid))
    mentions.sort()
    mentions = [m for i, m in enumerate(mentions)
                if not CANCELLED_RE.match(t[m[1]:mentions[i + 1][0] if i + 1 < len(mentions) else len(t)])]

    qty_tokens = [(m.start(), m.end(), _num(m.group(1))) for m in QTY_RE.finditer(t)]
    claimed = set()
    for start, end, pid in mentions:
        item = Item(pid)
        before = t[:start]
        m = QTY_BEFORE_PRODUCT_RE.search(before)
        if m and (m.group("unit") or not PRICE_WORD_BEFORE_RE.search(before[:m.start()])):
            item.qty_lbs = _num(m.group(1))
            claimed.add(m.start())
        if m := PRICE_AFTER_PRODUCT_RE.match(t[end:]):
            item.offer_per_lb = _num(m.group(1))
        elif m := PRICE_BEFORE_PRODUCT_RE.search(before):
            item.offer_per_lb = _num(m.group(1))
        c.items.append(item)

    # Quantities not written next to a product go to the nearest product mentioned before them
    for item, (start, end, _) in zip(c.items, mentions):
        if item.qty_lbs is not None:
            continue
        free = [tok for tok in qty_tokens if tok[0] not in claimed]
        tok = next((x for x in free if x[0] > end), None) or (free[0] if free else None)
        if tok:
            item.qty_lbs = tok[2]
            claimed.add(tok[0])
            if item.offer_per_lb is None and (m := PRICE_AFTER_QTY_RE.match(t[tok[1]:])):
                item.offer_per_lb = _num(m.group(1))
    if not c.items and qty_tokens:
        c.loose_qty = qty_tokens[0][2]

    # A price not tied to a product: per-pound offer for one product, or one total for several
    if c.items and all(i.offer_per_lb is None for i in c.items):
        price_matches = [m for rx in PRICE_RES for m in rx.finditer(t)]
        if price_matches:
            offer = _num(min(price_matches, key=lambda m: m.start()).group(1))
            if len(c.items) == 1:
                c.items[0].offer_per_lb = offer
            else:
                c.bundle_offer = offer
    for item in c.items:
        list_price = rows.loc[item.pid, "list_price"]
        if item.offer_per_lb and item.qty_lbs and item.offer_per_lb > list_price * 1.5:
            item.offer_per_lb, item.offer_was_total = item.offer_per_lb / item.qty_lbs, True  # "10 libras por 700"
        if item.offer_per_lb is not None:
            item.offer_per_lb = round(item.offer_per_lb, 2)

    for zone in settings["delivery_zones"]:
        places = [zone] + settings.get("zone_aliases", {}).get(zone, [])
        if any(re.search(rf"\b{re.escape(normalize(p))}\b", t) for p in places):
            c.zone = zone
    c.delivery = c.zone is not None or any(w in t for w in DELIVERY_WORDS)

    if "pasado manana" in t:  # with several dates, the latest one is checked (stricter on freshness)
        c.when_h = 48
    elif re.search(r"\b(?:hoy|ahorita)\b", t):  # "hoy en la mañana" means today
        c.when_h = 0
    elif "manana" in t:
        c.when_h = 24

    c.flags = _flags(c, rows, settings)
    return c


def _flags(c, rows, settings):
    flags = []
    if not c.items:
        flags.append(("UNKNOWN_PRODUCT", "No product from your catalog was recognized."))
    for it in c.items:
        r = rows.loc[it.pid]
        if it.pid in settings.get("closed_season", []):
            flags.append(("CLOSED_SEASON", f"{r['name']} is marked by you as closed season."))
        if r["stock_lbs"] <= 0:
            flags.append(("OUT_OF_STOCK", f"{r['name']} is out of stock."))
        elif it.qty_lbs and it.qty_lbs > r["stock_lbs"]:
            flags.append(("OVER_STOCK", f"Asks for {it.qty_lbs:g} lb of {r['name']}; you have {r['stock_lbs']:g} lb on ice."))
        if c.when_h and r["stock_lbs"] > 0 and r["hours_left"] < c.when_h + FRESHNESS_BUFFER_H:
            flags.append(("FRESHNESS", f"Delivery in ~{c.when_h} h, but this {r['name']} lot has "
                                       f"{r['hours_left']:.0f} h of freshness left."))
        if it.offer_per_lb is not None:
            if it.offer_per_lb < r["floor_price"]:
                flags.append(("BELOW_FLOOR", f"{r['name']}: offer L {it.offer_per_lb:g}/lb is below your floor "
                                             f"L {r['floor_price']}/lb (list L {r['list_price']})."))
            elif it.offer_per_lb < r["list_price"]:
                flags.append(("COUNTER_OFFER", f"{r['name']}: offer L {it.offer_per_lb:g}/lb is between your floor "
                                               "and list price. Accept or counter?"))

    if c.bundle_offer is not None:
        if all(it.qty_lbs for it in c.items):
            floor_total = sum(it.qty_lbs * rows.loc[it.pid, "floor_price"] for it in c.items)
            list_total = sum(it.qty_lbs * rows.loc[it.pid, "list_price"] for it in c.items)
            if c.bundle_offer < floor_total:
                flags.append(("BELOW_FLOOR", f"Offer L {c.bundle_offer:g} for the whole order is below your floor "
                                             f"total L {floor_total:g} (list L {list_total:g})."))
            elif c.bundle_offer < list_total:
                flags.append(("COUNTER_OFFER", f"Offer L {c.bundle_offer:g} for the whole order is between your floor "
                                               f"total L {floor_total:g} and list total L {list_total:g}."))
        else:
            flags.append(("BUNDLE_OFFER", f"Offers L {c.bundle_offer:g} for several products without saying how much of each."))

    has_offer = c.bundle_offer is not None or any(it.offer_per_lb is not None for it in c.items)
    if not has_offer and any(w in c.text for w in DISCOUNT_WORDS):
        flags.append(("DISCOUNT_ASK", "Buyer asks for a lower price without naming one."))

    for code, words, message in SPECIAL_REQUESTS:
        if any(w in c.text for w in words):
            flags.append((code, message))

    if c.delivery and c.zone is None:
        zones = ", ".join(settings["delivery_zones"])
        flags.append(("ZONE_UNKNOWN", f"Delivery requested to a place outside your zones ({zones})."))
    return flags
