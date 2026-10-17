"""Generate the SYNTHETIC demo data used by Marea.

Every number here is invented for the demo. Nothing describes a real seller,
real prices or real catches. Run from the repo root:

    python data/generate_data.py
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent
SEED = 7
DAYS = 90
AS_OF = datetime(2026, 10, 17, 9, 0)  # demo clock: every "now" calculation uses this

# id, name, list price (L/lb), floor price (L/lb), unit cost (L/lb),
# shelf life on ice (h), base demand (lb/day), demand trend over the period, aliases
PRODUCTS = [
    ("SHR", "Camarón mediano", 95, 80, 62, 48, 14.0, 0.0, "camaron|camarones"),
    ("SNP", "Pargo rojo", 85, 72, 55, 48, 9.0, 0.0, "pargo|pargos"),
    ("SNK", "Róbalo", 90, 78, 60, 48, 5.0, -0.6, "robalo|robalos"),
    ("LOB", "Cola de langosta", 320, 280, 230, 72, 2.0, 0.0, "langosta|langostas|colas"),
    ("CRB", "Jaiba", 45, 38, 26, 24, 6.0, 0.2, "jaiba|jaibas|cangrejo|cangrejos"),
    ("MAC", "Macarela", 40, 32, 22, 36, 8.0, 0.0, "macarela|macarelas"),
]

# Lots currently on ice: id, stock (lb), hours since catch at AS_OF
INVENTORY = [
    ("SHR", 35, 30),
    ("SNP", 12, 6),
    ("SNK", 18, 26),
    ("LOB", 8, 10),
    ("CRB", 0, None),
    ("MAC", 20, 8),
]

# Regular buyers (invented names): id, name, type, zone, preferred products, typical lb per order, days since last order
BUYERS = [
    ("B01", "Comedor Doña Lety", "comedor", "La Ceiba", "SHR|SNP|MAC", 15, 3),
    ("B02", "Restaurante Brisa Norte", "restaurant", "La Ceiba", "SHR|LOB|SNK", 25, 6),
    ("B03", "Pulpería El Faro Azul", "reseller", "Sambo Creek", "MAC|CRB", 12, 9),
    ("B04", "Hotelito Las Palmas", "hotel", "Tela", "SHR|LOB|SNP", 30, 12),
    ("B05", "Carmen Zelaya", "household", "La Ceiba", "SNP|SNK", 5, 2),
    ("B06", "Asados Los Cayos", "restaurant", "Jutiapa", "SNK|SNP|SHR", 18, 5),
    ("B07", "Don Mario (reventa, mercado)", "reseller", "La Ceiba", "SHR|MAC|CRB", 40, 20),
    ("B08", "Sopas El Pescador", "comedor", "Sambo Creek", "CRB|SNK|MAC", 10, 4),
]

WEEKDAY_FACTOR = [0.8, 0.85, 0.9, 1.0, 1.25, 1.35, 1.15]  # Mon..Sun

SETTINGS = {
    "business_name": "Mariscos La Ola",
    "home_base": "La Ceiba",
    "tone": "Warm and brief Honduran Spanish, uses 'usted', at most 3 sentences, at most one emoji.",
    "delivery_zones": {"La Ceiba": 0, "Sambo Creek": 60, "Jutiapa": 80, "Tela": 150},
    # Neighborhoods the seller counts as inside a zone
    "zone_aliases": {"La Ceiba": ["Barrio La Isla", "Barrio Inglés", "Mazapán", "Zona Viva"]},
    "delivery_hours": "Monday to Saturday, 7:00-17:00",
    "min_order_lbs": 3,
    # Extra charge per pound for preparing the fish (weighed whole, before cleaning)
    "prep_fees": {"whole": 0, "cleaned": 10, "fillet": 25},
    # What the seller spends every day besides the fish
    "daily_overhead": {"ice": 300, "fuel": 200},
    "closed_season": [],
    "as_of": AS_OF.isoformat(timespec="minutes"),
}


def main():
    rng = np.random.default_rng(SEED)

    catalog = pd.DataFrame(
        [(p[0], p[1], p[2], p[3], p[4], p[5], p[8]) for p in PRODUCTS],
        columns=["product_id", "name", "list_price", "floor_price", "unit_cost", "shelf_life_h", "aliases"],
    )

    start = AS_OF.date() - timedelta(days=DAYS)
    rows = []
    for d in range(DAYS):
        day = start + timedelta(days=d)
        for pid, _, price, _, _, _, base, trend, _ in PRODUCTS:
            mean = base * (1 + trend * d / DAYS) * WEEKDAY_FACTOR[day.weekday()]
            lbs = int(rng.poisson(max(mean, 0.1)))
            if lbs == 0:
                continue
            discount = rng.choice([0, 0, 0, 0.05, 0.10])  # some sales were negotiated
            unit_price = round(price * (1 - discount), 2)
            rows.append({
                "date": day.isoformat(),
                "product_id": pid,
                "lbs": lbs,
                "unit_price": unit_price,
                "revenue": round(lbs * unit_price, 2),
            })
    sales = pd.DataFrame(rows)

    inventory = pd.DataFrame([
        {
            "product_id": pid,
            "stock_lbs": stock,
            "caught_at": (AS_OF - timedelta(hours=age)).isoformat(timespec="minutes") if age is not None else "",
        }
        for pid, stock, age in INVENTORY
    ])

    buyers = pd.DataFrame(BUYERS, columns=["buyer_id", "name", "type", "zone", "preferred_products",
                                           "typical_lbs", "last_order_days_ago"])

    catalog.to_csv(OUT_DIR / "catalog.csv", index=False)
    buyers.to_csv(OUT_DIR / "buyers.csv", index=False)
    sales.to_csv(OUT_DIR / "sales.csv", index=False)
    inventory.to_csv(OUT_DIR / "inventory.csv", index=False)
    (OUT_DIR / "settings.json").write_text(json.dumps(SETTINGS, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(catalog)} products, {len(sales)} sales rows, {len(inventory)} lots to {OUT_DIR}")


if __name__ == "__main__":
    main()
