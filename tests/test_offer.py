"""Checks the sell-now-or-wait math and the buyer ranking on the shipped synthetic data.

Run from the repo root:  python tests/test_offer.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from core import analytics, guard  # noqa: E402


def setup():
    catalog, sales, inventory, settings = analytics.load_data()
    table = analytics.product_table(catalog, sales, inventory, pd.Timestamp(settings["as_of"]))
    return table, settings


def test_spoiling_lot_favors_selling_now(table, settings):
    # Shrimp: 35 lb on ice, 18 h left, ~15.4 lb/day -> about 11.6 lb sell to others, the rest spoils
    c = guard.check_message("me deja 10 libras de camaron a 70", table, settings)
    sc = analytics.offer_scenarios(c, table)
    ln = sc["lines"].iloc[0]
    assert ln["walk_away"] == 0, ln          # every pound sold now would otherwise spoil
    assert sc["accept"] > sc["wait"], sc     # even below the L 80 floor, selling beats waiting
    assert ln["counter"] == 83, ln           # halfway between L 70 and list L 95, rounded


def test_fresh_lot_favors_waiting(table, settings):
    # Red snapper: 12 lb, 42 h left, ~10.1 lb/day -> the whole lot sells at list anyway
    c = guard.check_message("le compro 5 libras de pargo a 75", table, settings)
    sc = analytics.offer_scenarios(c, table)
    ln = sc["lines"].iloc[0]
    assert ln["walk_away"] == ln["list"], ln  # no reason to go below list
    assert ln["counter"] == ln["list"], ln
    assert sc["wait"] > sc["accept"], sc


def test_no_offer_no_scenarios(table, settings):
    c = guard.check_message("ocupo 5 libras de pargo para hoy", table, settings)
    assert analytics.offer_scenarios(c, table) is None


def test_buyer_ranking_prefers_species(table, settings):
    lot = table.set_index("product_id").loc["SHR"].copy()
    lot["product_id"] = "SHR"
    ranked = analytics.match_buyers(lot, analytics.load_buyers(), settings)
    assert all("SHR" in p.split("|") for p in ranked["preferred_products"]), ranked
    assert ranked["match"].is_monotonic_decreasing


if __name__ == "__main__":
    table, settings = setup()
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t(table, settings)
        print("ok  ", t.__name__)
    print(f"{len(tests)}/{len(tests)} passed")
