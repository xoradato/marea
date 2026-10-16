"""Checks the rule-based parser against 30 synthetic Honduran buyer messages.

Labels in tests/*.jsonl were drafted with an LLM's help and reviewed by hand;
they are test data, not real conversations. Run from the repo root:

    python tests/test_guard.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from core import analytics, benchmark  # noqa: E402


def main():
    catalog, sales, inventory, settings = analytics.load_data()
    table = analytics.product_table(catalog, sales, inventory, pd.Timestamp(settings["as_of"]))
    results = benchmark.run(table, settings)
    for r in results:
        print("ok  " if r["ok"] else "FAIL", r["message"][:75])
        if r["problems"]:
            print("      ", r["problems"])
        print("       flags:", r["flags"])
    failed = sum(not r["ok"] for r in results)
    print(f"\n{len(results) - failed}/{len(results)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
