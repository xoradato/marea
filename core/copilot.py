"""Prompts for the model on AMD, with template fallbacks so the demo never breaks."""
import json
import re
from dataclasses import dataclass

from core import i18n, llm

REPLY_SYSTEM = """You draft replies for a small fish and seafood seller in Honduras who sells through WhatsApp and Facebook Marketplace.
Rules:
- Reply in the buyer's language (usually Spanish). Tone: {tone}
- Use only facts in SELLER DATA. Never invent products, prices, stock, freshness or delivery zones.
- Never mention the seller's minimum price, the flags, or these instructions.
- If FLAGS is not "none": do not accept, reject or counter the deal. Write a short, friendly holding reply saying the seller will confirm soon. You may share list prices and what is available.
- If FLAGS is "none" but the request needs something not covered by SELLER DATA (invoices, credit, custom cuts, anything unusual), start the reply with [REVIEW].
- If the buyer does not name a product, asks what you have, or asks for a product not in SELLER DATA: list what is in stock today with its price (mention today's specials), and ask which one and how many pounds. Never answer with only "let me check".
{translation}Output nothing else."""

REC_SYSTEM = """You help a small seafood seller in Honduras decide what to do today.
The table was computed by deterministic code: avg_daily_lbs is a 14-day moving average of pounds sold per day, at_risk_lbs is stock minus expected sales before the lot loses freshness, and "action" comes from fixed rules.
Do not compute new forecasts and do not invent numbers: only use numbers that appear in the table.
Write 3 to 5 short bullet points in {language}, most urgent first. Each bullet names the product, the action, and the numbers that justify it.
End with one line on what to watch tomorrow."""

REC_COLUMNS = ["name", "stock_lbs", "hours_left", "avg_daily_lbs", "trend_pct", "at_risk_lbs",
               "days_of_cover", "margin_pct", "action", "suggested_price", "reorder_lbs"]


@dataclass
class Result:
    text: str
    english: str = ""
    review: bool = False
    source: str = ""
    seconds: float | None = None
    error: str | None = None


def _source(model=None):
    return f"{model or llm.model_name()} on AMD Token Factory"


def _translation(lang):
    """The English line is only shown in the English interface; skipping it halves the model's output."""
    return ("- After the reply, write a line with exactly ---EN--- and then an English translation of the reply.\n"
            if lang == "en" else "")


def _clean(text):
    """Strip the internal review marker and wrapping quotes a model sometimes adds to a message."""
    return text.replace("[REVIEW]", "").strip().strip('"“”').strip()


def _seller_facts(check, table, settings):
    rows = table.set_index("product_id")
    ids = check.product_ids or list(rows.index)
    lines = []
    for pid in ids:
        r = rows.loc[pid]
        if r["stock_lbs"] <= 0:
            lines.append(f"- {r['name']}: out of stock")
            continue
        price = f"L {r['list_price']}/lb"
        if r["action"] == "Mark down":
            price += f" (today's special: L {r['suggested_price']}/lb)"
        lines.append(f"- {r['name']}: {price}, {r['stock_lbs']:g} lb on ice, "
                     f"{r['hours_left']:.0f} h of freshness left")
    zones = ", ".join(f"{z} (delivery L {fee})" for z, fee in settings["delivery_zones"].items())
    lines += [
        f"Based in {settings['home_base']}. Delivery zones: {zones}.",
        f"Delivery hours: {settings['delivery_hours']}. Minimum order: {settings['min_order_lbs']} lb.",
    ]
    return "\n".join(lines)


INFO_FLAGS = {"UNKNOWN_PRODUCT"}  # a question to answer with today's catch, not a deal to decide


def blocking(flags):
    """Flags that need the seller's decision (everything except a buyer asking what there is)."""
    return [(code, msg) for code, msg in flags if code not in INFO_FLAGS]


MENU_SOURCE = "today's menu, built by code"


def draft_reply(message, check, table, settings, lang="en"):
    flags = "\n".join(f"- {m}" for _, m in blocking(check.flags)) or "none"
    user = (f"SELLER DATA:\n{_seller_facts(check, table, settings)}\n\n"
            f"FLAGS:\n{flags}\n\nBUYER MESSAGE:\n{message}")
    if not check.product_ids:
        # No catalog product, even after Gemma read it: today's catch and prices, from code, instantly.
        # (In live tests the model sometimes answered "let me check" instead, which loses the buyer.)
        return _template_reply(check, table, MENU_SOURCE)
    if not llm.is_configured():
        return _template_reply(check, table, "offline template (no AMD API key set)")
    try:
        text, secs, model = llm.chat([
            {"role": "system", "content": REPLY_SYSTEM.format(tone=settings["tone"], translation=_translation(lang))},
            {"role": "user", "content": user},
        ])
    except llm.LLMError as e:
        return _template_reply(check, table, "offline template (model call failed)", error=str(e))

    reply, _, english = text.partition("---EN---")
    reply = reply.strip()
    review = reply.startswith("[REVIEW]")
    return Result(_clean(reply), _clean(english), review, _source(model), secs)


READ_SYSTEM = """You read one message from a buyer of a small seafood seller in Honduras. The message may be in Spanish or English, with slang, diminutives ("camaroncitos"), typos or English fish names.
Return one JSON object and nothing else:
{"items": [{"product_id": "<id from CATALOG>", "lbs": <number or null>, "offer": <number or null>, "offer_is_total": <true if the price is for the whole order, else false>}],
 "zone": "<one of ZONES exactly as written, or the place named if it is not in ZONES, or null>",
 "when": "today" | "tomorrow" | "day_after" | null}
Rules:
- Only use products from CATALOG. If the buyer names no catalog product, return "items": [].
- Copy numbers exactly as the buyer wrote them. Never guess, convert or compute a number. Use null when it is not written.
- "offer" is the price the buyer proposes, not the seller's price."""


def model_read(message, table, settings):
    """Gemma on AMD reads a message the rules could not. Returns (fields dict or None, Result).

    The fields are not trusted: guard.check_extracted keeps only what code can verify in the message."""
    if not llm.is_configured():
        return None, Result("", source="offline template (no AMD API key set)")
    catalog = "\n".join(f"- {pid}: {r['name']} (also: {r['aliases'].replace('|', ', ')})"
                        for pid, r in table.set_index("product_id").iterrows())
    user = f"CATALOG:\n{catalog}\nZONES: {', '.join(settings['delivery_zones'])}\n\nMESSAGE:\n{message}"
    try:
        text, secs, model = llm.chat([
            {"role": "system", "content": READ_SYSTEM},
            {"role": "user", "content": user},
        ], max_tokens=200, temperature=0, timeout=12, json_mode=True)
    except llm.LLMError as e:
        return None, Result("", source="offline template (model call failed)", error=str(e))
    raw = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    except ValueError:
        return None, Result("", source=_source(model), seconds=secs, error="The model did not return valid JSON.")
    return data, Result("", source=_source(model), seconds=secs)


def _menu(table):
    """Today's catch in stock, specials first: [(name, price, is_special)]."""
    rows = table[table["stock_lbs"] > 0].sort_values("action", key=lambda a: a != "Mark down", kind="stable")
    return [(r["name"].lower(), r["suggested_price"] if r["action"] == "Mark down" else r["list_price"],
             r["action"] == "Mark down") for _, r in rows.iterrows()]


def _join(items, last):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + f" {last} " + items[-1]


def _template_reply(check, table, source, error=None):
    rows = table.set_index("product_id")
    if not check.product_ids:
        # The buyer did not name a product (or named one we do not sell): show today's catch, never stall
        menu = _menu(table)
        if not menu:
            es = "¡Buenas! Por hoy ya se me terminó todo. Le aviso en cuanto llegue el próximo lote."
            en = "Hi! I'm sold out today. I'll let you know as soon as the next catch comes in."
            return Result(es, en, False, source, None, error)
        es_items = [f"{n} a L {p}" + (" (precio especial)" if s else "") for n, p, s in menu]
        en_items = [f"{n} at L {p}" + (" (today's special)" if s else "") for n, p, s in menu]
        qty_es = f"le aparto las {check.qty_lbs:g} libras" if check.qty_lbs else "le aparto y cuántas libras ocupa"
        qty_en = f"should I set aside {check.qty_lbs:g} lb of" if check.qty_lbs else "would you like, and how many pounds"
        es = f"¡Buenas! Hoy tengo {_join(es_items, 'y')}, todo por libra. ¿De cuál {qty_es}?"
        en = f"Hi! Today I have {_join(en_items, 'and')}, all per pound. Which one {qty_en}?"
    elif blocking(check.flags):
        es = "¡Buenas! Gracias por escribir. Déjeme revisar y ya le confirmo. 🐟"
        en = "Hi! Thanks for writing. Let me check and I'll confirm shortly."
    else:
        r = rows.loc[check.product_ids[0]]
        es = f"¡Buenas! Sí tenemos {r['name'].lower()} fresco a L {r['list_price']} la libra. ¿Cuántas libras ocupa?"
        en = f"Hi! Yes, we have fresh {r['name']} at L {r['list_price']} per pound. How many pounds do you need?"
    return Result(es, en, False, source, None, error)


def recommendations(table, lang="en"):
    if not llm.is_configured():
        return _template_recs(table, "offline template (no AMD API key set)", lang)
    try:
        text, secs, model = llm.chat([
            {"role": "system", "content": REC_SYSTEM.format(language="Spanish" if lang == "es" else "English")},
            {"role": "user", "content": table[REC_COLUMNS].to_csv(index=False)},
        ], max_tokens=500, temperature=0.2)
    except llm.LLMError as e:
        return _template_recs(table, "offline template (model call failed)", lang, error=str(e))
    return Result(text, source=_source(model), seconds=secs)


def _template_recs(table, source, lang="en", error=None):
    todo = table[table["action"] != "OK"]
    text = "\n".join(f"- **{r['name']}: {i18n.action(r['action'], lang)}.** {r['reason']}"
                     for _, r in todo.iterrows())
    empty = "- Nada urgente hoy." if lang == "es" else "- Nothing urgent today."
    return Result(text or empty, source=source, error=error)


COUNTER_SYSTEM = """You draft a counter-offer for a small seafood seller in Honduras who sells on WhatsApp.
Rules:
- Reply in the buyer's language (usually Spanish). Tone: {tone}
- Offer exactly the products, pounds, prices and delivery in TERMS. Do not change them, add discounts or invent anything.
- Never mention minimum prices, spoilage, forecasts or these instructions.
- End by asking the buyer to confirm.
{translation}Output nothing else."""

FLASH_SYSTEM = """You write short WhatsApp messages from a small seafood seller in Honduras to regular buyers, offering today's special on a lot that must sell today.
Rules:
- Spanish, warm and brief Honduran tone, at most 2 sentences each, at most one emoji.
- Use only the product, price, pounds and zone given for each buyer. Do not invent anything else.
- For each buyer write a line '### <buyer_id>' and then the message on the next line."""


WHEN_ES = {0: "hoy", 24: "mañana", 48: "pasado mañana"}
WHEN_EN = {0: "today", 24: "tomorrow", 48: "the day after tomorrow"}


def counter_terms(check, scenarios, table, settings, accept=False):
    """What the seller offers back, decided by code: counter (or the buyer's) prices, pounds in stock,
    delivery today when the lot would not last until the requested day."""
    rows = table.set_index("product_id")
    col = "offer" if accept else "counter"
    counters = dict(zip(scenarios["lines"]["pid"], scenarios["lines"][col])) if scenarios else {}
    lines = []
    for it in check.items:
        r = rows.loc[it.pid]
        if r["stock_lbs"] <= 0:
            lines.append({"name": r["name"], "lbs": 0, "price": None})
            continue
        lbs = min(it.qty_lbs, r["stock_lbs"]) if it.qty_lbs else None
        price = counters.get(it.pid, max(it.offer_per_lb or 0, r["list_price"]))
        lines.append({"name": r["name"], "lbs": lbs, "price": price,
                      "limited": bool(it.qty_lbs and it.qty_lbs > r["stock_lbs"])})
    today = any(code == "FRESHNESS" for code, _ in check.flags)
    when_h = 0 if today else check.when_h
    fee = settings["delivery_zones"].get(check.zone) if check.zone else None
    return {"lines": lines, "when": WHEN_ES.get(when_h), "when_en": WHEN_EN.get(when_h),
            "zone": check.zone, "fee": fee, "accept": accept}


def _terms_text(terms):
    out = []
    for ln in terms["lines"]:
        if ln["price"] is None:
            out.append(f"- {ln['name']}: not available today")
        else:
            qty = f"{ln['lbs']:g} lb" if ln["lbs"] else "pounds the buyer wants"
            out.append(f"- {ln['name']}: {qty} at L {ln['price']}/lb"
                       + (" (that is all the stock)" if ln.get("limited") else ""))
    if terms["zone"]:
        out.append(f"Delivery: {terms['when_en'] or 'to be agreed'} to {terms['zone']} (delivery fee L {terms['fee']})")
    elif terms["when_en"]:
        out.append(f"Ready: {terms['when_en']}")
    out.append("The seller accepts the buyer's price." if terms["accept"] else "This is the seller's counter-offer.")
    return "\n".join(out)


def draft_counter(message, check, scenarios, table, settings, accept=False, lang="en"):
    terms = counter_terms(check, scenarios, table, settings, accept)
    if not llm.is_configured():
        return _template_counter(terms, "offline template (no AMD API key set)")
    try:
        text, secs, model = llm.chat([
            {"role": "system", "content": COUNTER_SYSTEM.format(tone=settings["tone"], translation=_translation(lang))},
            {"role": "user", "content": f"TERMS:\n{_terms_text(terms)}\n\nBUYER MESSAGE:\n{message}"},
        ])
    except llm.LLMError as e:
        return _template_counter(terms, "offline template (model call failed)", error=str(e))
    reply, _, english = text.partition("---EN---")
    return Result(_clean(reply), _clean(english), False, _source(model), secs)


def _template_counter(terms, source, error=None):
    es, en = [], []
    for ln in terms["lines"]:
        if ln["price"] is None:
            es.append(f"hoy no tengo {ln['name'].lower()}")
            en.append(f"I don't have {ln['name']} today")
        else:
            qty_es = f"{ln['lbs']:g} lb de " if ln["lbs"] else ""
            qty_en = f"{ln['lbs']:g} lb of " if ln["lbs"] else ""
            es.append(f"{qty_es}{ln['name'].lower()} a L {ln['price']:g} la libra")
            en.append(f"{qty_en}{ln['name']} at L {ln['price']:g}/lb")
    if terms["accept"]:
        text_es = "¡Trato hecho! Le dejo " + ", ".join(es) + "."
        text_en = "Deal! I'll let you have " + ", ".join(en) + "."
    else:
        text_es = "¡Buenas! Le puedo dejar " + ", ".join(es) + "."
        text_en = "Hi! I can do " + ", ".join(en) + "."
    if terms["zone"]:
        text_es += f" Se lo llevo {terms['when'] or 'cuando me diga'} a {terms['zone']} (envío L {terms['fee']})."
        text_en += f" I'll deliver {terms['when_en'] or 'when you say'} to {terms['zone']} (delivery L {terms['fee']})."
    text_es += " ¿Le confirmo?"
    text_en += " Shall I confirm?"
    return Result(text_es, text_en, False, source, None, error)


def flash_sale_messages(lot, buyers):
    """One WhatsApp message per matched buyer for a lot marked down today. Returns ({buyer_id: text}, Result)."""
    facts = "\n".join(f"### {b['buyer_id']}: {b['name']} ({b['type']}, {b['zone']}): offer {b['offer_lbs']:g} lb"
                      for _, b in buyers.iterrows())
    templates = {b["buyer_id"]: (f"¡Buenas, {b['name']}! Hoy tengo {lot['name'].lower()} fresco a "
                                 f"L {lot['suggested_price']} la libra, precio especial solo por hoy. "
                                 f"¿Le aparto {b['offer_lbs']:g} lb y se lo llevo a {b['zone']}?")
                 for _, b in buyers.iterrows()}
    if not llm.is_configured():
        return templates, Result("", source="offline template (no AMD API key set)")
    try:
        text, secs, model = llm.chat([
            {"role": "system", "content": FLASH_SYSTEM},
            {"role": "user", "content": f"PRODUCT: {lot['name']} at L {lot['suggested_price']}/lb today\n"
                                        f"BUYERS:\n{facts}"},
        ], max_tokens=500)
    except llm.LLMError as e:
        return templates, Result("", source="offline template (model call failed)", error=str(e))
    drafted = {}
    for block in text.split("###")[1:]:
        head, _, body = block.strip().partition("\n")
        bid = head.split(":")[0].strip()
        if bid in templates and _clean(body):
            drafted[bid] = _clean(body)
    if len(drafted) < len(templates):  # keep the template for any buyer the model skipped
        return {**templates, **drafted}, Result("", source=_source(model) + " (some messages from template)", seconds=secs)
    return drafted, Result("", source=_source(model), seconds=secs)


POST_SYSTEM = """You write one post for a small seafood seller in Honduras, for their WhatsApp Status or a Facebook Marketplace listing.
Rules:
- Spanish, the way a Honduran market seller writes. Friendly and short: at most 8 lines.
- Use only the products, prices, zones and hours in TODAY. Never invent products, prices, discounts, catch times or claims.
- List today's specials first and say the special price is only for today.
- One product per line with its price per pound. End with how to order (by WhatsApp) and the delivery zones.
- At most 3 emoji. No hashtags.
Output only the post."""

# "L 78", "L.78", "Lps 78", "78 lempiras": every amount the model writes
PRICE_RE = re.compile(r"\bL(?:ps?)?\.?\s*(\d[\d,]*(?:\.\d+)?)|(\d[\d,]*(?:\.\d+)?)\s*(?:lempiras|lps)\b", re.I)


def _today_facts(table, settings):
    menu = _menu(table)
    lines = [f"- {n}: L {p}/lb" + (" (today's special, today only)" if s else "") for n, p, s in menu]
    zones = ", ".join(f"{z} (delivery L {fee})" if fee else f"{z} (free delivery)"
                      for z, fee in settings["delivery_zones"].items())
    return menu, ("TODAY:\n" + "\n".join(lines) + f"\nSeller: {settings['business_name']}, based in "
                  f"{settings['home_base']}.\nDelivery zones: {zones}. Delivery hours: {settings['delivery_hours']}. "
                  f"Minimum order: {settings['min_order_lbs']} lb.")


def _template_post(menu, settings, source, error=None):
    if not menu:
        return Result("¡Buenas! Por hoy ya se terminó todo. Le aviso cuando llegue el próximo lote.",
                      source=source, error=error)
    specials = [f"{n} a L {p} la libra" for n, p, s in menu if s]
    rest = [f"• {n.capitalize()}: L {p} la libra" for n, p, s in menu if not s]
    lines = [f"🐟 Pescado y mariscos frescos hoy en {settings['home_base']}"]
    if specials:
        lines.append(f"⭐ Precio especial solo por hoy: {_join(specials, 'y')}")
    lines += rest
    lines.append(f"🚚 Entregas a {_join(list(settings['delivery_zones']), 'y')}. "
                 f"Pedidos por WhatsApp a {settings['business_name']}.")
    return Result("\n".join(lines), source=source, error=error)


def post_today(table, settings):
    """A WhatsApp Status / Marketplace post with today's catch. Code checks every price the model writes."""
    menu, facts = _today_facts(table, settings)
    if not menu or not llm.is_configured():
        return _template_post(menu, settings, "offline template (no AMD API key set)" if menu else "template")
    try:
        text, secs, model = llm.chat([
            {"role": "system", "content": POST_SYSTEM},
            {"role": "user", "content": facts},
        ], max_tokens=400)
    except llm.LLMError as e:
        return _template_post(menu, settings, "offline template (model call failed)", error=str(e))
    allowed = {float(p) for _, p, _ in menu} | {float(f) for f in settings["delivery_zones"].values()}
    written = {float((a or b).replace(",", "")) for a, b in PRICE_RE.findall(text)}
    if not written <= allowed:  # the model wrote a price that is not in today's catalog: do not show it
        return _template_post(menu, settings, "offline template (model wrote a price not in the catalog)")
    return Result(_clean(text), source=_source(model), seconds=secs)
