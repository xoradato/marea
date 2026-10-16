"""Checks the rule-based parser against 20 synthetic Honduran buyer messages.

Labels in buyer_messages.jsonl were written by hand (with an LLM's help) and reviewed;
they are test data, not real conversations. Run from the repo root:

    python tests/test_guard.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from core import analytics, guard  # noqa: E402

PRODUCT_IDS = {"camarón": "SHR", "pargo": "SNP", "róbalo": "SNK", "langosta": "LOB",
               "jaiba": "CRB", "macarela": "MAC"}
WHEN_H = {"hoy": 0, "mañana": 24, "pasado mañana": 48, None: None}
# message prefix -> (flags that must appear, flags that must not appear)
FLAG_RULES = {
    "hola tenes pargo rojo": ({"DISCOUNT_ASK"}, {"ZONE_UNKNOWN"}),
    "buen dia ocupamos": ({"INVOICE", "ZONE_UNKNOWN", "OVER_STOCK"}, set()),
    "amigo le doy 300": ({"ZONE_UNKNOWN"}, set()),
    "buenas tardes me vende": ({"CUSTOM_PREP"}, set()),
    "vecino aparteme": ({"PAY_LATER"}, set()),
    "compa dejeme": ({"BELOW_FLOOR"}, {"PAY_LATER"}),
    "hola me manda 2 libras": (set(), {"ZONE_UNKNOWN"}),
    "buenas a como tiene": (set(), {"DISCOUNT_ASK", "ZONE_UNKNOWN"}),
}


def run():
    catalog, sales, inventory, settings = analytics.load_data()
    table = analytics.product_table(catalog, sales, inventory, pd.Timestamp(settings["as_of"]))
    zones = {guard.normalize(z) for z in settings["delivery_zones"]}
    failures = 0
    for line in (ROOT / "tests" / "buyer_messages.jsonl").read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        c = guard.check_message(case["message"], table, settings)
        want_pid = PRODUCT_IDS.get(case["product"])
        problems = []
        if (c.product_ids[:1] or [None])[0] != want_pid:
            problems.append(f"product {c.product_ids} != {want_pid}")
        if c.qty_lbs != case["qty_lbs"]:
            problems.append(f"qty {c.qty_lbs} != {case['qty_lbs']}")
        if c.offer_per_lb != case["offer_per_lb"]:
            problems.append(f"offer {c.offer_per_lb} != {case['offer_per_lb']}")
        if c.when_h != WHEN_H[case["when"]]:
            problems.append(f"when {c.when_h} != {WHEN_H[case['when']]}")
        place = guard.normalize(case["delivery_place"] or "")
        if place in zones and guard.normalize(c.zone or "") != place:
            problems.append(f"zone {c.zone} != {case['delivery_place']}")
        codes = {code for code, _ in c.flags}
        for prefix, (must, must_not) in FLAG_RULES.items():
            if case["message"].startswith(prefix):
                if must - codes:
                    problems.append(f"missing flags {sorted(must - codes)}")
                if must_not & codes:
                    problems.append(f"unexpected flags {sorted(must_not & codes)}")
        failures += bool(problems)
        print("FAIL" if problems else "ok  ", case["message"][:70])
        for p in problems:
            print("      ", p)
        print("       flags:", [code for code, _ in c.flags])
    print(f"\n{failures} failing")
    return failures


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
