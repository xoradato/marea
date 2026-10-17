"""Checks who-to-sell-to-first on five synthetic buyers competing for 35 lb of shrimp.

Run from the repo root:  python tests/test_queue.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from core import analytics, buyer_queue  # noqa: E402

QUEUE = "\n".join([
    "Ana: buenas, me deja 10 libras de camaron a 70 y me lo lleva mañana a sambo creek",
    "Comedor Doña Lety: ocupo 15 lbs de camaron a 82 para hoy al mediodia, se las pago el viernes",
    "Carlos: quiero 4 libras de camaron, paso hoy mismo y le pago en efectivo",
    "Restaurante Brisa Norte: 12 libras de camaron a 85 para hoy en zona viva",
    "Hotelito Las Palmas: ocupo 20 lbs de camaron a 90 para pasado mañana en Tela",
])


def main():
    catalog, sales, inventory, settings = analytics.load_data()
    table = analytics.product_table(catalog, sales, inventory, pd.Timestamp(settings["as_of"]))
    q = buyer_queue.rank(QUEUE, table, settings)
    rk = q["ranked"]
    order = list(rk["buyer"])
    # Pays today first (best price first), then "only if delivered today", then credit
    assert order == ["Carlos", "Restaurante Brisa Norte", "Hotelito Las Palmas", "Ana", "Comedor Doña Lety"], order
    assert list(rk["gets"]) == [4, 12, 19, 0, 0], list(rk["gets"])           # 35 lb on ice
    assert q["cash_marea"] == 4 * 95 + 12 * 85 + 19 * 90, q["cash_marea"]
    assert q["cash_marea"] > q["cash_fifo"], (q["cash_marea"], q["cash_fifo"])
    assert buyer_queue.reply(rk.iloc[2]).startswith("¡Buenas! Solo me quedan 19 lb")
    assert "se lo tendría que entregar hoy" in buyer_queue.reply(rk.iloc[2]).lower()
    assert buyer_queue.split_messages("a las 4:30 paso por 5 libras de pargo") == [
        ("#1", "a las 4:30 paso por 5 libras de pargo")]                       # a time is not a name
    assert buyer_queue.rank("   \n  ", table, settings) is None

    # A buyer who wants "everything you have" is a full-lot order at list price, not a lost line
    big = QUEUE + "\nPalma Real: Quiero todo su producto disponible lo mas pronto posible"
    q2 = buyer_queue.rank(big, table, settings)
    top = q2["ranked"].iloc[0]
    assert (top["buyer"], top["gets"], top["price"], bool(top["takes_all"])) == ("Palma Real", 35, 95, True), top
    assert q2["cash_marea"] == 35 * 95 > q["cash_marea"], q2["cash_marea"]
    others = buyer_queue.other_catch(big, table, settings)
    text = buyer_queue.reply(top, others)
    assert "se las aparto todas" in text and "También tengo hoy róbalo" in text, text
    print(f"order {order}\ncash today: Marea L {q['cash_marea']:,.0f} vs arrival order L {q['cash_fifo']:,.0f}")
    print("1/1 passed")


if __name__ == "__main__":
    main()
