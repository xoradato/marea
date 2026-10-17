"""Checks that code verifies what the model extracts, with fixed model answers (no API call).

Run from the repo root:  python tests/test_extract.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from core import analytics, guard  # noqa: E402


def codes(check):
    return {code for code, _ in check.flags}


def main():
    catalog, sales, inventory, settings = analytics.load_data()
    table = analytics.product_table(catalog, sales, inventory, pd.Timestamp(settings["as_of"]))
    n = 0

    # 1. A good read of a message the rules cannot read: the same rules then set the flags
    msg = "kmaron a 75 la lb, me manda 10 a tela mañana?"
    assert not guard.check_message(msg, table, settings).items
    c, dropped = guard.check_extracted(msg, {"items": [{"product_id": "SHR", "lbs": 10, "offer": 75}],
                                             "zone": "Tela", "when": "tomorrow"}, table, settings)
    assert (c.product_ids, c.qty_lbs, c.offer_per_lb, c.zone, c.when_h) == (["SHR"], 10, 75, "Tela", 24)
    assert {"BELOW_FLOOR", "FRESHNESS"} <= codes(c) and not dropped
    n += 1

    # 2. Invented numbers and an invented zone are dropped, not trusted
    msg = "hi! could I get some red snapper delivered to Sambo Creek?"
    c, dropped = guard.check_extracted(msg, {"items": [{"product_id": "SNP", "lbs": 5, "offer": 80}],
                                             "zone": "Tela", "when": None}, table, settings)
    assert c.product_ids == ["SNP"] and c.qty_lbs is None and c.offer_per_lb is None, c.items
    assert c.zone is None and set(dropped) == {"lb 5", "L 80", "zone Tela"}, dropped
    assert "ZONE_UNKNOWN" in codes(c)                    # asks for delivery, zone not verified
    n += 1

    # 3. A total for the whole order becomes a price per pound; unknown product ids are dropped
    msg = "Good morning, I need 3 lb of lobster tails for tonight in La Ceiba, I can pay 900 for all"
    c, dropped = guard.check_extracted(msg, {"items": [{"product_id": "LOB", "lbs": 3, "offer": 900,
                                                        "offer_is_total": True},
                                                       {"product_id": "TUNA", "lbs": 3}],
                                             "zone": "La Ceiba", "when": "today"}, table, settings)
    assert (c.product_ids, c.offer_per_lb, c.items[0].offer_was_total) == (["LOB"], 300, True)
    assert dropped == ["product TUNA"] and "COUNTER_OFFER" in codes(c)
    n += 1

    # 4. Garbage from the model never crashes the check
    for junk in (None, {}, {"items": "x"}, {"items": [None, {"lbs": "ten"}]}):
        c, _ = guard.check_extracted("hola", junk or {}, table, settings)
        assert not c.items and "UNKNOWN_PRODUCT" in codes(c)
    n += 1
    print(f"{n}/{n} passed")


if __name__ == "__main__":
    main()
