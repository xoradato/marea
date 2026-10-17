"""Scores the rule-based parser on synthetic buyer messages in tests/*.jsonl.

Two label formats:
- single product: "product", "qty_lbs", "offer_per_lb"
- several products: "items" as [product, qty_lbs, offer_per_lb] and "bundle_offer"
Both may add "when", "zone", "must_flag" and "must_not_flag". Flag checks assume the
shipped synthetic data (stock and freshness at the demo clock).
"""
import json
from pathlib import Path

from core import guard

CASES_DIR = Path(__file__).resolve().parent.parent / "tests"
CASE_FILES = ("buyer_messages.jsonl", "hard_messages.jsonl")
PRODUCT_IDS = {"camarón": "SHR", "pargo": "SNP", "róbalo": "SNK", "langosta": "LOB",
               "jaiba": "CRB", "macarela": "MAC"}
WHEN_H = {"hoy": 0, "mañana": 24, "pasado mañana": 48, None: None}


MODEL_CASE_FILE = "model_messages.jsonl"  # messages the rules alone cannot read


def load_cases(files=CASE_FILES):
    cases = []
    for name in files:
        lines = (CASES_DIR / name).read_text(encoding="utf-8").splitlines()
        cases += [json.loads(line) for line in lines if line.strip()]
    return cases


def _problems(case, c, zones):
    problems = []
    if "items" in case:
        want = [(PRODUCT_IDS[p], q, o) for p, q, o in case["items"]]
        got = [(i.pid, i.qty_lbs, i.offer_per_lb) for i in c.items]
        if got != want:
            problems.append(f"items {got} != {want}")
        if c.bundle_offer != case.get("bundle_offer"):
            problems.append(f"bundle {c.bundle_offer} != {case.get('bundle_offer')}")
    else:
        want_pid = PRODUCT_IDS.get(case["product"])
        if (c.product_ids[:1] or [None])[0] != want_pid:
            problems.append(f"product {c.product_ids} != {want_pid}")
        if c.qty_lbs != case["qty_lbs"]:
            problems.append(f"qty {c.qty_lbs} != {case['qty_lbs']}")
        if c.offer_per_lb != case["offer_per_lb"]:
            problems.append(f"offer {c.offer_per_lb} != {case['offer_per_lb']}")
    if c.when_h != WHEN_H[case["when"]]:
        problems.append(f"when {c.when_h} != {WHEN_H[case['when']]}")
    place = guard.normalize(case.get("zone") or case.get("delivery_place") or "")
    if place in zones and guard.normalize(c.zone or "") != place:
        problems.append(f"zone {c.zone} != {place}")
    codes = {code for code, _ in c.flags}
    if missing := set(case.get("must_flag", [])) - codes:
        problems.append(f"missing flags {sorted(missing)}")
    if extra := set(case.get("must_not_flag", [])) & codes:
        problems.append(f"unexpected flags {sorted(extra)}")
    return problems


def run(table, settings):
    """One result per message: {ok, message, problems, flags}."""
    zones = {guard.normalize(z) for z in settings["delivery_zones"]}
    results = []
    for case in load_cases():
        c = guard.check_message(case["message"], table, settings)
        problems = _problems(case, c, zones)
        results.append({
            "ok": not problems,
            "message": case["message"],
            "problems": "; ".join(problems),
            "flags": ", ".join(code for code, _ in c.flags),
        })
    return results


def run_model(table, settings):
    """Rules alone vs. rules + Gemma on AMD on messages the rules cannot read. One model call per message."""
    from core import copilot  # the rule benchmark above stays free of model calls

    zones = {guard.normalize(z) for z in settings["delivery_zones"]}
    results = []
    for case in load_cases((MODEL_CASE_FILE,)):
        rules = guard.check_message(case["message"], table, settings)
        data, res = copilot.model_read(case["message"], table, settings)
        if data is None:
            problems, dropped = [res.error or "no model answer"], []
        else:
            c, dropped = guard.check_extracted(case["message"], data, table, settings)
            problems = _problems(case, c, zones)
        results.append({
            "message": case["message"],
            "rules": not _problems(case, rules, zones),
            "with_model": not problems,
            "problems": "; ".join(problems),
            "dropped": ", ".join(dropped),
            "seconds": res.seconds,
        })
    return results
