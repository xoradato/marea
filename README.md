<img src="assets/marea-mark.svg" width="72" alt="Marea logo">

# Marea

Sales copilot for small-scale fish and seafood sellers in Honduras who sell through WhatsApp and Facebook Marketplace.

**Live demo:** https://marea-copilot.streamlit.app/

> Draft README. To be finished before submission.

## What it does

1. **Reply to a buyer.** Paste a buyer message. Rules in code read each product, pounds and offer (also in multi-product orders and "L 1100 for everything" offers) and check them against the seller's floor price, stock, delivery zone and lot freshness. If any rule triggers, the seller sees **DECIDE TÚ** and the draft is a holding reply. Otherwise the model drafts a reply in the seller's tone. Under the draft, the order's value, cost, gross profit and discount vs. list price are computed with code.
2. **Dashboard.** Revenue, margin, stock at risk of spoiling (in pounds and lempiras at cost), and days of cover, computed with pandas. A time slider simulates the next 36 hours: stock sells at the 14-day average and lots age, so you can see when markdowns start and when a lot must be discarded.
3. **What to do today.** Fixed rules choose the action (mark down, restock, discard). The model only explains the numbers. For each lot marked down, regular buyers are ranked with code and the model drafts a flash-sale WhatsApp message for each one. Nothing is sent automatically. "Post today's catch" drafts one WhatsApp Status or Marketplace post with what is on ice, specials first; code checks every price in the draft against the catalog and uses a template if the model wrote one that is not there.

When a buyer makes an offer, Marea compares three options in lempiras: accept, counter-offer, or reject and wait. The seller picks one, edits the draft and opens it in WhatsApp with one click. Confirming the order records preparation (whole, cleaned, filleted; weighed whole) and payment (cash on delivery or transfer before dispatch), drops the stock everywhere in the app and generates a WhatsApp-ready receipt. When several buyers ask for the same stock at once (common on Marketplace), the **Several buyers** tab ranks them with code and splits the pounds: buyers who pay today and can be served as asked first, then deliveries that only work today, then credit; within each group, highest price per pound first. It shows the cash this brings today against answering in arrival order (in the demo: L 3,110 vs. L 1,590), drafts a reply for each buyer and can reserve all the pounds at once. The dashboard tracks the day's break-even (librar la cava): fish on ice at cost plus ice and fuel, against what has been sold.

The interface switches between English and Spanish (sidebar). Messages to buyers, receipts and flash sales are always in Spanish.

## How the numbers are calculated (no LLM)

- Demand forecast: 14-day moving average of pounds sold per day.
- Expected sales before spoiling = avg lb/day × hours of freshness left ÷ 24.
- At risk = stock − expected sales before spoiling.
- Mark down when a lot has half or less of its shelf life left and stock is at risk: 10% off, or 15% if more than 40% of the lot is at risk. Never below the seller's floor price.
- Restock to cover 2 days of demand.
- Discard when a lot is past its shelf life; the loss is shown at cost.
- Sell now or wait: other buyers take the 14-day average until the lot's freshness runs out, the rest spoils. Accept = offer × pounds + list price × what others still buy; wait = list price × what others buy. Fish on ice is a sunk cost, so options are compared on money in. Walk-away price = lowest price per pound at which selling now still beats waiting. Counter-offer = halfway between offer and list price, never below the walk-away price.
- Buyer match score (0–100): buys this species 50, usual order size against pounds at risk 30, delivery zone 10, ordered in the last week 10.

`python tests/test_offer.py` and `python tests/test_queue.py` check these rules on the synthetic data.

## When the seller sees DECIDE TÚ

Rules in `core/guard.py`, not the LLM, raise it when a message has: an offer below the floor or below list price (per product or for the whole order), a request for a lower price, more pounds than in stock, an out-of-stock or closed-season product, delivery after the lot loses freshness, delivery outside the seller's zones, pay-later, an invoice, cleaning/filleting, or a request for something free.

`python tests/test_guard.py` checks the parser against 30 synthetic messages written in Honduran WhatsApp style: typos, "lps", numbers in words, totals vs. per-pound offers, sarcasm, two or three products in one message, and a buyer who changes their mind. The same benchmark is shown in the app under "Your catalog". Current result: 30/30. The messages and labels were drafted with an LLM's help and reviewed by hand; they are not real conversations.

## Where AMD runs

All language model calls (reply drafts, counter-offers, flash-sale messages and explanations) go to **Gemma-4-31B-IT** (Google), served on AMD GPUs by AMD Token Factory (AMD Radeon Cloud), through its OpenAI-compatible endpoint `https://developer.amd.com.cn/radeon/api/v1/chat/completions`. See `core/llm.py`.

- The model only writes text. Prices, quantities, flags and actions are computed in pandas and passed to it.
- Gemma-4-31B-IT does not "think" by default, so each reply is short and cheap against the team's daily usage cap. The model is one setting (`AMD_MODEL`); any chat model in the Token Factory catalog works.
- Rate limits are shared per team key. `core/llm.py` retries only 429 and 502/503 responses, with short backoff; if the model is slow, rate limited or down, the app falls back to its offline templates and says so.
- Token Factory keeps prompts and outputs for about 2 days. All data sent is synthetic.

## Data

All data in `data/` is **synthetic**, generated by `data/generate_data.py`. It does not describe any real seller.

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in the values
set -a; source .env; set +a
streamlit run app.py
```

Without an API key the app runs with offline templates so the rules and dashboard can still be tested.

## Credits

Sea turtle icon in the header: [iconsDB.com](https://www.iconsdb.com/white-icons/turtle-icon.html), CC0 1.0 (public domain), faded and hosted in this repo.

## License

MIT
