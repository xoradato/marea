"""English / Spanish text for the interface, the DECIDE TÚ reasons and the rule explanations.

Buyer-facing messages (replies, receipts, flash sales) are always in Spanish; this file covers what the
seller reads. Codes and numbers stay the same in both languages, so tests and the benchmark do not change.
"""
LANGS = {"en": "English", "es": "Español"}

TEXT = {
    # Sidebar
    "language": ("Language", "Idioma"),
    "controls": ("Controls", "Controles"),
    "night_hint": ("Night mode: menu ⋮ (top right) → Settings → Dark. It also follows your phone's setting.",
                   "Modo noche: menú ⋮ (arriba a la derecha) → Settings → Dark. También sigue el ajuste de su "
                   "teléfono."),
    "sim_slider": ("Simulate time: hours from now", "Simular tiempo: horas desde ahora"),
    "sim_help": ("Stock sells at the 14-day average and every lot ages. No restocking.",
                 "El stock se vende al promedio de 14 días y cada lote envejece. Sin reabastecer."),
    "demo_clock": ("Demo clock: {t}", "Reloj del demo: {t}"),
    "simulated": (" (simulated)", " (simulado)"),
    "closed_season": ("Closed season (set by you)", "Veda (la define usted)"),
    "choose_products": ("Choose products", "Elija productos"),
    "time_saved": ("Time saved (estimate)", "Tiempo ahorrado (estimado)"),
    "manual_s": ("Seconds to write a reply by hand", "Segundos para escribir una respuesta a mano"),
    "review_s": ("Seconds to review a draft", "Segundos para revisar un borrador"),
    "time_note": ("Assumption-based estimate, not a measurement. All data is synthetic.",
                  "Estimación basada en supuestos, no una medición. Todos los datos son sintéticos."),
    "replies_drafted": ("Replies drafted", "Respuestas redactadas"),
    "est_time_saved": ("Estimated time saved", "Tiempo ahorrado estimado"),
    # Header
    "tagline": ("Drafts replies to buyers on WhatsApp and Marketplace, flags the deals you should decide "
                "yourself, and tells you what to sell before it spoils.",
                "Redacta respuestas a compradores de WhatsApp y Marketplace, le avisa qué tratos debe decidir "
                "usted y le dice qué vender antes de que se eche a perder."),
    "model_on": ("Replies drafted by **{model}** on AMD GPUs.", "Respuestas redactadas por **{model}** en GPUs AMD."),
    "model_off": ("AMD model not connected yet: replies use offline templates.",
                  "Modelo de AMD aún sin conectar: las respuestas usan plantillas."),
    "demo_seller": ("Demo seller: {seller} (fictional). All data is synthetic.",
                    "Vendedor de demostración: {seller} (ficticio). Todos los datos son sintéticos."),
    "decide_title": ("**DECIDE TÚ.** This one needs you before sending.",
                     "**DECIDE TÚ.** Este mensaje necesita su decisión antes de enviarlo."),
    "safe_title": ("**Ready to send.** No rule triggered. Read the draft and send it.",
                   "**Listo para enviar.** Ninguna regla se activó. Lea el borrador y envíelo."),
    # Tabs
    "tab_reply": ("Reply to a buyer", "Responder"),
    "tab_dash": ("Dashboard", "Panel"),
    "tab_recs": ("What to do today", "Qué hacer hoy"),
    "tab_catalog": ("Your catalog", "Su catálogo"),
    # Catalog
    "catalog_intro": ("Your prices, floor prices, stock and shelf life at the start of the day. Edit any cell; "
                      "changes apply to this session only.",
                      "Sus precios, precios mínimos, stock y vida útil al inicio del día. Puede editar cualquier "
                      "celda; los cambios valen solo para esta sesión."),
    "sold_caption": ("Sold through Marea this session (already taken off the stock everywhere else): ",
                     "Vendido con Marea en esta sesión (ya descontado del stock en toda la app): "),
    "col_product": ("Product", "Producto"),
    "col_list": ("List price", "Precio de lista"),
    "col_floor": ("Floor price", "Precio mínimo"),
    "col_cost": ("Unit cost", "Costo"),
    "col_stock_start": ("Stock at start", "Stock inicial"),
    "col_shelf": ("Shelf life", "Vida útil"),
    "warn_floor_above": ("{name}: the floor price (L {floor}) is above the list price (L {list}).",
                         "{name}: el precio mínimo (L {floor}) está arriba del precio de lista (L {list})."),
    "warn_typo": ("{name}: list price L {list} is more than 3 times the floor price L {floor}. Typo?",
                  "{name}: el precio de lista L {list} es más de 3 veces el mínimo L {floor}. ¿Error de dedo?"),
    "warn_cost": ("{name}: selling at the floor price (L {floor}) would not cover the cost (L {cost}).",
                  "{name}: vender al precio mínimo (L {floor}) no cubre el costo (L {cost})."),
    "zones": ("**Delivery zones:** {zones}", "**Zonas de entrega:** {zones}"),
    "hours": ("**Delivery hours:** {hours}", "**Horario de entrega:** {hours}"),
    "min_order": ("**Minimum order:** {lbs} lb", "**Pedido mínimo:** {lbs} lb"),
    "tone": ("**Reply tone:** {tone}", "**Tono de las respuestas:** {tone}"),
    "bench_expander": ("Parser benchmark: how well the rules read buyer messages",
                       "Prueba del lector: qué tan bien leen las reglas los mensajes"),
    "bench_metric": ("Synthetic messages parsed correctly", "Mensajes sintéticos leídos correctamente"),
    "bench_fails": ("Fails", "Falla"),
    "bench_caption": ("Checks product, pounds, offer, date, zone and DECIDE TÚ flags against hand-reviewed labels "
                      "(tests/*.jsonl). Messages are synthetic, written in Honduran WhatsApp style.",
                      "Compara producto, libras, oferta, día, zona y avisos de DECIDE TÚ con etiquetas revisadas "
                      "a mano (tests/*.jsonl). Los mensajes son sintéticos, al estilo de WhatsApp hondureño."),
    # Reply tab
    "example_label": ("Example buyer message (synthetic)", "Mensaje de ejemplo (sintético)"),
    "buyer_msg_label": ("Buyer message (paste from WhatsApp or Marketplace)",
                        "Mensaje del comprador (péguelo desde WhatsApp o Marketplace)"),
    "draft_btn": ("Draft reply", "Redactar respuesta"),
    "paste_first": ("Paste a buyer message first.", "Primero pegue el mensaje del comprador."),
    "drafting": ("Drafting on AMD...", "Redactando en AMD..."),
    "unusual": ("The model marked this request as unusual.", "El modelo marcó esta petición como inusual."),
    "parsed": ("Parsed by rules: {items} · zone={zone} · when={when}",
               "Leído por las reglas: {items} · zona={zone} · cuándo={when}"),
    "from_total": (" (from total)", " (del total)"),
    "for_everything": ("L {offer} for everything", "L {offer} por todo"),
    "no_product": ("no product", "sin producto"),
    "decision": ("Your decision", "Su decisión"),
    "opt_hold": ("Hold: ask to wait", "Esperar: pedir un momento"),
    "opt_counter": ("Counter at {p}/lb", "Contraofertar a {p}/lb"),
    "opt_accept": ("Accept {p}/lb", "Aceptar {p}/lb"),
    "reply_label": ("Reply to send (edit before sending)", "Respuesta para enviar (edítela antes de enviar)"),
    "source": ("Source: {s}", "Fuente: {s}"),
    "model_failed": ("Model call failed, showing a template instead: {e}",
                     "Falló la llamada al modelo, se muestra una plantilla: {e}"),
    "deal_title": ("**If you accept as written**", "**Si acepta tal como lo pide**"),
    "order_value": ("Order value", "Valor del pedido"),
    "product_cost": ("Product cost", "Costo del producto"),
    "gross_profit_m": ("Gross profit ({m} margin)", "Ganancia bruta ({m} de margen)"),
    "vs_list": ("vs. your list price", "vs. su precio de lista"),
    "deal_caption": ("Computed with code from the parsed offer (list price where no offer was given). ",
                     "Calculado con código a partir de la oferta leída (precio de lista donde no hubo oferta). "),
    "fee_note": ("Delivery to {zone}: L {fee}, charged to the buyer.",
                 "Envío a {zone}: L {fee}, lo paga el comprador."),
    "no_fee": ("No delivery fee included.", "Sin costo de envío incluido."),
    "sell_or_wait": ("Sell now or wait?", "¿Vender ahora o esperar?"),
    "accept_offer": ("Accept offer", "Aceptar oferta"),
    "counter_offer": ("Counter-offer", "Contraoferta"),
    "reject_wait": ("Reject and wait", "Rechazar y esperar"),
    "still_spoil": ("{lbs} lb would still spoil", "{lbs} lb se perderían igual"),
    "if_takes": ("if the buyer takes it", "si el comprador la acepta"),
    "spoil_cost": ("{lbs} lb spoil (L {cost} at cost)", "se pierden {lbs} lb (L {cost} a costo)"),
    "v_sell_more": ("Selling now at the buyer's price brings **L {diff} more** than waiting. ",
                    "Vender ahora al precio del comprador deja **L {diff} más** que esperar. "),
    "v_any_price": ("Every pound in this order would otherwise spoil, so any price beats waiting.",
                    "Cada libra de este pedido se perdería de todos modos, así que cualquier precio le gana a esperar."),
    "v_above": ("Selling now beats waiting at any price above: {walk}.",
                "Vender ahora le gana a esperar a cualquier precio arriba de: {walk}."),
    "v_below_floor": (" The offer is below your floor price, but the numbers favor selling. Your call.",
                      " La oferta está debajo de su precio mínimo, pero los números favorecen vender. Usted decide."),
    "v_wait_more": ("Waiting brings **L {diff} more** than this offer. Below {walk}, selling now loses against waiting.",
                    "Esperar deja **L {diff} más** que esta oferta. Debajo de {walk}, vender ahora pierde contra esperar."),
    "how_calc": ("How this is calculated", "Cómo se calcula"),
    "how_calc_text": ("Lempiras each option brings in from the lots involved. Other buyers take the 14-day average "
                      "(lb/day) until the lot's freshness runs out; whatever is left then spoils. Fish already on ice "
                      "is a sunk cost, so the options are compared on money in. The counter-offer splits the "
                      "difference between the offer and your list price, never below the walk-away price.",
                      "Lempiras que deja cada opción con los lotes del pedido. Otros compradores se llevan el promedio "
                      "de 14 días (lb/día) hasta que se acaba la frescura del lote; lo que sobra se pierde. El pescado "
                      "que ya está en hielo es un costo hundido, así que las opciones se comparan por el dinero que "
                      "entra. La contraoferta queda a medio camino entre la oferta y su precio de lista, nunca debajo "
                      "del precio para retirarse."),
    "close_order": ("Close the order", "Cerrar el pedido"),
    "cart_pounds": ("Pounds", "Libras"),
    "cart_price": ("Price / lb", "Precio / lb"),
    "cart_caption": ("Prefilled with what the buyer asked for, capped at your stock. Edit pounds and prices to "
                     "what you agreed before confirming.",
                     "Prellenado con lo que pidió el comprador, limitado a su stock. Ajuste libras y precios a lo "
                     "que acordaron antes de confirmar."),
    "confirm_btn": ("Confirm order and update stock", "Confirmar pedido y actualizar stock"),
    "err_empty": ("Add at least one product with pounds before confirming.",
                  "Agregue al menos un producto con libras antes de confirmar."),
    "err_stock": ("Not enough stock. ", "No hay suficiente stock. "),
    "only_x": ("{product}: only {stock} lb on ice.", "{product}: solo hay {stock} lb en hielo."),
    "order_confirmed": ("Order confirmed. Stock, dashboard and today's actions are updated.",
                        "Pedido confirmado. El stock, el panel y las acciones de hoy ya están actualizados."),
    "receipt_caption": ("WhatsApp receipt: copy it with the button in the corner.",
                        "Recibo para WhatsApp: cópielo con el botón de la esquina."),
    "open_whatsapp": ("Open in WhatsApp", "Abrir en WhatsApp"),
    "prep": ("Preparation", "Preparación"),
    "prep_whole": ("Whole", "Entero"),
    "prep_cleaned": ("Cleaned and scaled (+L {fee}/lb)", "Limpio y escamado (+L {fee}/lb)"),
    "prep_fillet": ("Filleted (+L {fee}/lb)", "Fileteado (+L {fee}/lb)"),
    "prep_note": ("Weighed whole, before cleaning.", "Se pesa entero, antes de limpiar."),
    "payment": ("Payment", "Pago"),
    "pay_cash": ("Cash on delivery", "Efectivo al recibir"),
    "pay_transfer": ("Bank transfer before dispatch", "Transferencia antes del despacho"),
    "log_title": ("Messages handled this session", "Mensajes atendidos en esta sesión"),
    "log_message": ("Message", "Mensaje"),
    "log_reasons": ("Reasons", "Motivos"),
    "log_source": ("Source", "Fuente"),
    # Competing buyers
    "tab_queue": ("Several buyers", "Varios compradores"),
    "queue_intro": ("Several buyers asking for the same stock at once? Paste their messages, one per line. "
                    "\"Name: message\" keeps each buyer's name.",
                    "¿Varios compradores piden el mismo producto a la vez? Pegue sus mensajes, uno por línea. "
                    "\"Nombre: mensaje\" conserva el nombre de cada uno."),
    "queue_label": ("Buyer messages (synthetic example)", "Mensajes de compradores (ejemplo sintético)"),
    "queue_btn": ("Who do I sell to first?", "¿A quién le vendo primero?"),
    "queue_empty": ("Paste at least one buyer message.", "Pegue al menos un mensaje."),
    "cash_marea": ("Cash today, in Marea's order", "Efectivo hoy, en el orden de Marea"),
    "cash_fifo": ("Cash today, in arrival order", "Efectivo hoy, por orden de llegada"),
    "cash_diff": ("Serving in this order brings **L {diff} more** today than answering in arrival order.",
                  "Atender en este orden deja **L {diff} más** hoy que contestar por orden de llegada."),
    "cash_same": ("Here the arrival order already gives the same cash today.",
                  "Aquí el orden de llegada ya deja el mismo efectivo hoy."),
    "q_rank": ("Order", "Orden"),
    "q_asks": ("Asks", "Pide"),
    "q_gets": ("Gets", "Recibe"),
    "q_cash": ("Cash today", "Efectivo hoy"),
    "q_notes": ("Notes", "Notas"),
    "n_ok": ("pays today", "paga hoy"),
    "n_today": ("only if delivered today", "solo si se entrega hoy"),
    "n_credit": ("wants credit", "pide crédito"),
    "n_zone": ("outside your zones", "fuera de sus zonas"),
    "n_out": ("not available", "no disponible"),
    "n_noqty": ("no pounds given", "no dijo cuántas libras"),
    "n_noproduct": ("no product recognized", "sin producto reconocido"),
    "left_after": ("Left on ice after these orders: {left}.", "Queda en hielo después de estos pedidos: {left}."),
    "queue_rule": ("Order of service, decided by code: buyers who pay today and can be served as asked; then "
                   "those who want delivery after the lot loses freshness (only if they take it today); then "
                   "credit. Outside your zones or out of stock are not served. Within each group: highest price "
                   "per pound first, then the bigger order. Serving the highest price first gives the most money "
                   "for the pounds you have.",
                   "Orden de atención, decidido con código: primero quien paga hoy y se le puede entregar como "
                   "pide; luego quien pide entrega cuando el lote ya no está fresco (solo si lo recibe hoy); luego "
                   "quien pide crédito. Fuera de zona o sin stock no se atiende. Dentro de cada grupo: mejor precio "
                   "por libra primero y luego el pedido más grande. Atender primero al mejor precio es lo que más "
                   "dinero deja con las libras que tiene."),
    "replies_title": ("Replies, one per buyer", "Respuestas, una por comprador"),
    "reserve_btn": ("Reserve these pounds and update stock", "Apartar estas libras y actualizar stock"),
    "reserved": ("{n} orders reserved. Stock, dashboard and today's actions are updated.",
                 "{n} pedidos apartados. El stock, el panel y las acciones de hoy ya están actualizados."),
    # Dashboard
    "session_title": ("This session with Marea", "Esta sesión con Marea"),
    "orders": ("Orders confirmed", "Pedidos confirmados"),
    "sales": ("Sales", "Ventas"),
    "rescued": ("Sold from lots at risk", "Vendido de lotes en riesgo"),
    "flagged": ("Deals flagged for you", "Tratos que le avisamos"),
    "session_caption": ("Updates as you use Marea. \"Sold from lots at risk\" counts pounds that the forecast "
                        "said would spoil, at the price you sold them.",
                        "Se actualiza mientras usa Marea. \"Vendido de lotes en riesgo\" cuenta las libras que el "
                        "pronóstico daba por perdidas, al precio al que las vendió."),
    "cava_title": ("Break-even today (\"librar la cava\")", "Librar la cava (punto de equilibrio de hoy)"),
    "cava_progress": ("L {sold} of L {capital} recovered ({pct})", "L {sold} de L {capital} recuperados ({pct})"),
    "cava_missing": ("**L {missing}** still to sell to recover today's money: fish on ice at cost L {fish} "
                     "+ ice L {ice} + fuel L {fuel}.",
                     "Faltan **L {missing}** por vender para recuperar lo invertido hoy: pescado en hielo a costo "
                     "L {fish} + hielo L {ice} + combustible L {fuel}."),
    "cava_done": ("Today's money is back (fish at cost L {fish} + ice L {ice} + fuel L {fuel}). From here, every "
                  "pound you sell is profit, so lots at risk can go at the walk-away price.",
                  "Ya recuperó lo invertido hoy (pescado a costo L {fish} + hielo L {ice} + combustible L {fuel}). "
                  "Desde aquí cada libra vendida es ganancia, así que los lotes en riesgo pueden salir al precio "
                  "para retirarse."),
    "revenue_30d": ("Revenue, last 30 days", "Ventas, últimos 30 días"),
    "gross_margin": ("Gross margin ({m})", "Margen bruto ({m})"),
    "at_risk": ("At risk of spoiling (L {v} at cost)", "En riesgo de perderse (L {v} a costo)"),
    "need_action": ("Products needing action", "Productos que requieren acción"),
    "daily_rev": ("Daily revenue, last 30 days", "Ventas diarias, últimos 30 días"),
    "revenue_series": ("Revenue (L)", "Ventas (L)"),
    "lots": ("Lots on ice", "Lotes en hielo"),
    "col_stock": ("Stock", "Stock"),
    "col_fresh": ("Freshness left", "Frescura restante"),
    "col_sells": ("Sells / day", "Vende / día"),
    "col_trend": ("Trend", "Tendencia"),
    "col_risk": ("At risk", "En riesgo"),
    "col_days": ("Days of stock", "Días de stock"),
    "col_margin": ("Margin", "Margen"),
    "col_action": ("Action", "Acción"),
    "dash_caption": ("Computed with pandas, no LLM. Forecast = 14-day moving average of lb sold per day. "
                     "At risk = stock − (avg lb/day × hours of freshness left ÷ 24).",
                     "Calculado con pandas, sin LLM. Pronóstico = promedio móvil de 14 días de libras vendidas por "
                     "día. En riesgo = stock − (promedio lb/día × horas de frescura ÷ 24)."),
    # What to do today
    "recs_intro": ("Actions come from fixed rules in code. The model on AMD only explains them in plain words.",
                   "Las acciones salen de reglas fijas en código. El modelo en AMD solo las explica en palabras sencillas."),
    "col_price_today": ("Price today", "Precio de hoy"),
    "col_buy": ("Buy", "Comprar"),
    "col_why": ("Why (rule)", "Por qué (regla)"),
    "explain_btn": ("Explain with AI", "Explicar con IA"),
    "asking": ("Asking the model on AMD...", "Consultando al modelo en AMD..."),
    "rec_failed": ("Model call failed, showing rule output instead: {e}",
                   "Falló la llamada al modelo, se muestran las reglas: {e}"),
    "who_title": ("Who to offer it to", "A quién ofrecerlo"),
    "who_caption": ("Regular buyers ranked by code: buys this species 50 pts, usual order size against the pounds "
                    "at risk 30, delivery zone 10, ordered in the last week 10. Buyers are fictional.",
                    "Clientes frecuentes ordenados por código: compra esta especie 50 pts, tamaño de pedido frente "
                    "a las libras en riesgo 30, zona de entrega 10, compró en la última semana 10. Los clientes son "
                    "ficticios."),
    "lot_line": ("**{name}**: {lbs} lb at risk, today's price L {price}/lb",
                 "**{name}**: {lbs} lb en riesgo, precio de hoy L {price}/lb"),
    "col_buyer": ("Buyer", "Cliente"),
    "col_type": ("Type", "Tipo"),
    "col_zone": ("Zone", "Zona"),
    "col_usual": ("Usual order", "Pedido usual"),
    "col_last": ("Last order", "Último pedido"),
    "days_ago": ("%d days ago", "hace %d días"),
    "col_match": ("Match", "Afinidad"),
    "col_offer": ("Offer", "Ofrecer"),
    "flash_btn": ("Draft flash-sale messages for these buyers", "Redactar ofertas relámpago para estos clientes"),
    "to_buyer": ("To **{name}**", "Para **{name}**"),
    "flash_caption": (". Nothing is sent automatically: copy each message into WhatsApp.",
                      ". No se envía nada automáticamente: copie cada mensaje a WhatsApp."),
    "flash_failed": ("Model call failed, showing templates instead: {e}",
                     "Falló la llamada al modelo, se muestran plantillas: {e}"),
    # Footer
    "footer_on": ("Demo with synthetic data. Language model inference runs on AMD GPUs via AMD Token Factory.",
                  "Demo con datos sintéticos. El modelo de lenguaje corre en GPUs AMD mediante AMD Token Factory."),
    "footer_off": ("Demo with synthetic data. AMD model not connected yet: showing offline templates.",
                   "Demo con datos sintéticos. Modelo de AMD aún sin conectar: se muestran plantillas."),
}

FLAGS = {
    "UNKNOWN_PRODUCT": ("No product from your catalog was recognized.", "No se reconoció ningún producto de su catálogo."),
    "CLOSED_SEASON": ("{name} is marked by you as closed season.", "Usted marcó {name} en veda."),
    "OUT_OF_STOCK": ("{name} is out of stock.", "No hay {name} en stock."),
    "OVER_STOCK": ("Asks for {qty} lb of {name}; you have {stock} lb on ice.",
                   "Pide {qty} lb de {name}; usted tiene {stock} lb en hielo."),
    "FRESHNESS": ("Delivery in ~{when} h, but this {name} lot has {hours} h of freshness left.",
                  "Entrega en ~{when} h, pero este lote de {name} tiene {hours} h de frescura."),
    "BELOW_FLOOR": ("{name}: offer L {offer}/lb is below your floor L {floor}/lb (list L {list}).",
                    "{name}: oferta de L {offer}/lb, debajo de su mínimo de L {floor}/lb (lista L {list})."),
    "COUNTER_OFFER": ("{name}: offer L {offer}/lb is between your floor and list price. Accept or counter?",
                      "{name}: oferta de L {offer}/lb, entre su mínimo y su precio de lista. ¿Acepta o contraoferta?"),
    "BELOW_FLOOR_ALL": ("Offer L {offer} for the whole order is below your floor total L {floor} (list L {list}).",
                        "Oferta de L {offer} por todo el pedido, debajo de su mínimo total de L {floor} (lista L {list})."),
    "COUNTER_OFFER_ALL": ("Offer L {offer} for the whole order is between your floor total L {floor} and list "
                          "total L {list}.",
                          "Oferta de L {offer} por todo el pedido, entre su mínimo total de L {floor} y su lista "
                          "total de L {list}."),
    "BUNDLE_OFFER": ("Offers L {offer} for several products without saying how much of each.",
                     "Ofrece L {offer} por varios productos sin decir cuánto de cada uno."),
    "DISCOUNT_ASK": ("Buyer asks for a lower price without naming one.",
                     "El comprador pide rebaja sin decir cuánto."),
    "PAY_LATER": ("Buyer wants to pay later.", "El comprador quiere pagar después."),
    "INVOICE": ("Buyer asks for an invoice (factura).", "El comprador pide factura."),
    "CUSTOM_PREP": ("Buyer asks for cleaning or filleting.", "El comprador pide limpiar o filetear."),
    "FREEBIE": ("Buyer asks for something free (extra product or delivery).",
                "El comprador pide algo gratis (producto extra o envío)."),
    "ZONE_UNKNOWN": ("Delivery requested to a place outside your zones ({zones}).",
                     "Pide entrega a un lugar fuera de sus zonas ({zones})."),
}

REASONS = {
    "Restock": ("Out of stock. Sells {avg} lb/day (14-day average), so buy {qty} lb to cover {days} days.",
                "Sin stock. Vende {avg} lb/día (promedio de 14 días): compre {qty} lb para cubrir {days} días."),
    "Discard": ("Past its {shelf} h shelf life: {stock} lb lost (L {loss} at cost).",
                "Pasó su vida útil de {shelf} h: se pierden {stock} lb (L {loss} a costo)."),
    "Mark down": ("{risk} of {stock} lb may not sell in the {hours} h of freshness left. {pct} off gives "
                  "L {price}/lb (never below floor L {floor}).",
                  "{risk} de {stock} lb podrían no venderse en las {hours} h de frescura. Con {pct} de descuento "
                  "queda en L {price}/lb (nunca debajo del mínimo de L {floor})."),
    "Restock soon": ("Only {cover} days of stock at {avg} lb/day. Buy {qty} lb.",
                     "Solo {cover} días de stock a {avg} lb/día. Compre {qty} lb."),
    "OK": ("Stock and freshness are in line with demand.", "El stock y la frescura van de acuerdo con la demanda."),
}

ACTIONS = {
    "OK": ("OK", "OK"),
    "Mark down": ("Mark down", "Rebajar"),
    "Restock": ("Restock", "Reponer"),
    "Restock soon": ("Restock soon", "Reponer pronto"),
    "Discard": ("Discard", "Descartar"),
}

BUYER_TYPES = {
    "comedor": ("eatery", "comedor"),
    "restaurant": ("restaurant", "restaurante"),
    "reseller": ("reseller", "revendedor"),
    "hotel": ("hotel", "hotel"),
    "household": ("household", "hogar"),
}

SOURCES = [  # technical source captions from the copilot, in English, with their Spanish version
    ("offline template (no AMD API key set)", "plantilla sin conexión (sin clave de AMD)"),
    ("offline template (model call failed)", "plantilla sin conexión (falló el modelo)"),
    ("(some messages from template)", "(algunos mensajes de plantilla)"),
    (" on AMD Token Factory", " en AMD Token Factory"),
]

DAYS = (["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"])
MONTHS = (["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
          ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"])


def _pick(pair, lang):
    return pair[1] if lang == "es" else pair[0]


def t(key, lang="en", **kw):
    text = _pick(TEXT[key], lang)
    return text.format(**kw) if kw else text


def flag(code, lang="en", **kw):
    return _pick(FLAGS[code], lang).format(**kw)


def reason(action, lang="en", **kw):
    return _pick(REASONS[action], lang).format(**kw)


def action(name, lang="en"):
    return _pick(ACTIONS.get(name, (name, name)), lang)


def buyer_type(name, lang="en"):
    return _pick(BUYER_TYPES.get(name, (name, name)), lang)


def source(text, lang="en"):
    if lang == "es":
        for en, es in SOURCES:
            text = text.replace(en, es)
    return text


def stamp(ts, lang="en"):
    i = 1 if lang == "es" else 0
    return f"{DAYS[i][ts.weekday()]} {ts.day} {MONTHS[i][ts.month - 1]} {ts.year}, {ts:%H:%M}"
