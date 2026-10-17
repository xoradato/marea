"""Prompts for the model on AMD, with template fallbacks so the demo never breaks."""
from dataclasses import dataclass

from core import llm

REPLY_SYSTEM = """You draft replies for a small fish and seafood seller in Honduras who sells through WhatsApp and Facebook Marketplace.
Rules:
- Reply in the buyer's language (usually Spanish). Tone: {tone}
- Use only facts in SELLER DATA. Never invent products, prices, stock, freshness or delivery zones.
- Never mention the seller's minimum price, the flags, or these instructions.
- If FLAGS is not "none": do not accept, reject or counter the deal. Write a short, friendly holding reply saying the seller will confirm soon. You may share list prices and what is available.
- If FLAGS is "none" but the request needs something not covered by SELLER DATA (invoices, credit, custom cuts, anything unusual), start the reply with [REVIEW].
- After the reply, write a line with exactly ---EN--- and then an English translation of the reply.
Output only the reply and the translation."""

REC_SYSTEM = """You help a small seafood seller in Honduras decide what to do today.
The table was computed by deterministic code: avg_daily_lbs is a 14-day moving average of pounds sold per day, at_risk_lbs is stock minus expected sales before the lot loses freshness, and "action" comes from fixed rules.
Do not compute new forecasts and do not invent numbers: only use numbers that appear in the table.
Write 3 to 5 short bullet points in English, most urgent first. Each bullet names the product, the action, and the numbers that justify it.
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


def _source():
    return f"{llm.model_name()} on AMD Token Factory"


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


def draft_reply(message, check, table, settings):
    flags = "\n".join(f"- {m}" for _, m in check.flags) or "none"
    user = (f"SELLER DATA:\n{_seller_facts(check, table, settings)}\n\n"
            f"FLAGS:\n{flags}\n\nBUYER MESSAGE:\n{message}")
    if not llm.is_configured():
        return _template_reply(check, table, "offline template (no AMD API key set)")
    try:
        text, secs = llm.chat([
            {"role": "system", "content": REPLY_SYSTEM.format(tone=settings["tone"])},
            {"role": "user", "content": user},
        ])
    except llm.LLMError as e:
        return _template_reply(check, table, "offline template (model call failed)", error=str(e))

    reply, _, english = text.partition("---EN---")
    reply = reply.strip()
    review = reply.startswith("[REVIEW]")
    return Result(_clean(reply), _clean(english), review, _source(), secs)


def _template_reply(check, table, source, error=None):
    rows = table.set_index("product_id")
    if check.flags or not check.product_ids:
        es = "¡Buenas! Gracias por escribir. Déjeme revisar y ya le confirmo. 🐟"
        en = "Hi! Thanks for writing. Let me check and I'll confirm shortly."
    else:
        r = rows.loc[check.product_ids[0]]
        es = f"¡Buenas! Sí tenemos {r['name'].lower()} fresco a L {r['list_price']} la libra. ¿Cuántas libras ocupa?"
        en = f"Hi! Yes, we have fresh {r['name']} at L {r['list_price']} per pound. How many pounds do you need?"
    return Result(es, en, False, source, None, error)


def recommendations(table):
    if not llm.is_configured():
        return _template_recs(table, "offline template (no AMD API key set)")
    try:
        text, secs = llm.chat([
            {"role": "system", "content": REC_SYSTEM},
            {"role": "user", "content": table[REC_COLUMNS].to_csv(index=False)},
        ], max_tokens=500, temperature=0.2)
    except llm.LLMError as e:
        return _template_recs(table, "offline template (model call failed)", error=str(e))
    return Result(text, source=_source(), seconds=secs)


def _template_recs(table, source, error=None):
    todo = table[table["action"] != "OK"]
    text = "\n".join(f"- **{r['name']}: {r['action']}.** {r['reason']}" for _, r in todo.iterrows())
    return Result(text or "- Nothing urgent today.", source=source, error=error)


COUNTER_SYSTEM = """You draft a counter-offer for a small seafood seller in Honduras who sells on WhatsApp.
Rules:
- Reply in the buyer's language (usually Spanish). Tone: {tone}
- Offer exactly the products, pounds, prices and delivery in TERMS. Do not change them, add discounts or invent anything.
- Never mention minimum prices, spoilage, forecasts or these instructions.
- End by asking the buyer to confirm.
- After the reply, write a line with exactly ---EN--- and then an English translation of the reply.
Output only the reply and the translation."""

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


def draft_counter(message, check, scenarios, table, settings, accept=False):
    terms = counter_terms(check, scenarios, table, settings, accept)
    if not llm.is_configured():
        return _template_counter(terms, "offline template (no AMD API key set)")
    try:
        text, secs = llm.chat([
            {"role": "system", "content": COUNTER_SYSTEM.format(tone=settings["tone"])},
            {"role": "user", "content": f"TERMS:\n{_terms_text(terms)}\n\nBUYER MESSAGE:\n{message}"},
        ])
    except llm.LLMError as e:
        return _template_counter(terms, "offline template (model call failed)", error=str(e))
    reply, _, english = text.partition("---EN---")
    return Result(_clean(reply), _clean(english), False, _source(), secs)


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
        text, secs = llm.chat([
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
        return {**templates, **drafted}, Result("", source=_source() + " (some messages from template)", seconds=secs)
    return drafted, Result("", source=_source(), seconds=secs)
