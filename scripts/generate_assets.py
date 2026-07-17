"""
generate_assets.py — build Trailhead Supply Co.'s workshop data + PDFs.

Run this ONCE to (re)generate everything in data/ and documents/pdf/. Students
never need to run it — the generated files are committed to the repo. It exists so
the assets are reproducible and easy to tweak.

What it does:
  1. Writes six internally-consistent CSVs to data/ (customers, products, orders,
     order_items, inventory, shipments).
  2. Renders each markdown file in documents/markdown/ to a PDF in documents/pdf/.
  3. Verifies referential integrity and prints a summary.

Data generation uses stdlib only (random + csv), so producing the CSVs has no
dependencies. PDF rendering needs two small extra packages:

    pip install fpdf2 markdown

Everything is deterministic (fixed random seed), so re-running produces identical
data — including order #1027, which we use as a running example in the notebooks.
"""

from __future__ import annotations

import csv
import datetime as dt
import random
from pathlib import Path

# --- Paths -------------------------------------------------------------------
# Resolve paths relative to the repo root (this script lives in scripts/).
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
MD_DIR = REPO_ROOT / "documents" / "markdown"
PDF_DIR = REPO_ROOT / "documents" / "pdf"

SEED = 42
random.seed(SEED)


# --- Canonical facts (must match the policy documents) -----------------------
# These constants encode the same rules the markdown policies describe, so the
# structured data and the documents never contradict each other.
STANDARD_RETURN_DAYS = 30
EXTENDED_RETURN_DAYS = 60  # Trail Club members
WAREHOUSE = "Denver, CO"
CARRIERS = ["UPS", "FedEx", "USPS"]

SHIPPING_METHODS = {
    # method: (customer-facing cost, low/high business-day estimate)
    "Standard": (6.99, (5, 7)),
    "Expedited": (14.99, (2, 3)),
    "Overnight": (29.99, (1, 1)),
}
FREE_SHIP_THRESHOLD = 75.00


# --- Product catalog (explicit, ~20 items) -----------------------------------
# Fields: name, category, price, weight_kg, warranty_months, is_final_sale.
# warranty_months follows the Warranty Policy: 24 for Tents/Backpacks, else 12.
# return_window_days is derived below (0 for Final Sale, else the standard 30).
PRODUCTS = [
    ("Summit 2P Backpacking Tent",       "Tents",              289.00, 2.1, False),
    ("Basecamp 4P Family Tent",          "Tents",              349.00, 4.8, False),
    ("Ridgeline 1P Ultralight Tent",     "Tents",              259.00, 1.2, True),   # clearance
    ("Voyager 65L Backpack",             "Backpacks",          219.00, 1.9, False),
    ("Daybreak 30L Daypack",             "Backpacks",           89.00, 0.8, False),
    ("Alpine 45L Trekking Pack",         "Backpacks",          179.00, 1.5, False),
    ("Nightfall 20F Down Sleeping Bag",  "Sleeping Bags",      199.00, 1.1, False),
    ("Meadow 40F Synthetic Bag",         "Sleeping Bags",       99.00, 1.4, False),
    ("Frostline 0F Expedition Bag",      "Sleeping Bags",      279.00, 1.8, True),   # clearance
    ("Traverse Mid Hiking Boots",        "Footwear",           169.00, 1.0, False),
    ("Trailrunner Low Shoes",            "Footwear",           129.00, 0.7, False),
    ("Summit GTX Mountaineering Boots",  "Footwear",           329.00, 1.6, False),
    ("Blaze Backpacking Stove",          "Stoves & Cookware",   59.00, 0.3, False),
    ("Campfire 2-Pot Cook Set",          "Stoves & Cookware",   49.00, 0.6, False),
    ("Kettle Pro Titanium Pot",          "Stoves & Cookware",   45.00, 0.2, False),
    ("Horizon Down Jacket",              "Apparel",            189.00, 0.5, False),
    ("Rainguard Shell Jacket",           "Apparel",            159.00, 0.4, False),
    ("Trail Merino Base Layer",          "Apparel",             69.00, 0.3, False),
    ("Pathfinder GPS Handheld",          "Navigation",         249.00, 0.2, False),
    ("Trailhead Compass & Map Set",      "Navigation",          29.00, 0.1, False),
]


def build_products() -> list[dict]:
    rows = []
    for i, (name, category, price, weight, final_sale) in enumerate(PRODUCTS):
        warranty_months = 24 if category in ("Tents", "Backpacks") else 12
        rows.append(
            {
                "product_id": f"TSC-{1001 + i}",
                "name": name,
                "category": category,
                "price": f"{price:.2f}",
                "weight_kg": weight,
                "return_window_days": 0 if final_sale else STANDARD_RETURN_DAYS,
                "warranty_months": warranty_months,
                "is_final_sale": final_sale,
            }
        )
    return rows


# --- Customers (explicit, ~20) -----------------------------------------------
CUSTOMERS_RAW = [
    ("Ava Bennett",     "Denver",        "CO", True),
    ("Liam Carter",     "Portland",      "OR", False),
    ("Sofia Nguyen",    "Austin",        "TX", True),
    ("Noah Alvarez",    "Seattle",       "WA", False),
    ("Mia Thompson",    "Boulder",       "CO", True),
    ("Ethan Park",      "Chicago",       "IL", False),
    ("Isabella Rossi",  "Salt Lake City","UT", True),
    ("Lucas Meyer",     "Minneapolis",   "MN", False),
    ("Harper Sullivan", "Bend",          "OR", True),
    ("Mateo Garcia",    "Phoenix",       "AZ", False),
    ("Chloe Foster",    "Asheville",     "NC", True),
    ("Daniel Kim",      "San Diego",     "CA", False),
    ("Grace Walker",    "Missoula",      "MT", True),
    ("Owen Bennett",    "Boise",         "ID", False),
    ("Layla Hassan",    "Flagstaff",     "AZ", True),
    ("Henry Brooks",    "Fort Collins",  "CO", False),
    ("Zoe Mitchell",    "Bozeman",       "MT", True),
    ("Jack Rivera",     "Reno",          "NV", False),
    ("Nora Bailey",     "Burlington",    "VT", True),
    ("Leo Sanders",     "Tacoma",        "WA", False),
]


def build_customers() -> list[dict]:
    rows = []
    base = dt.date(2023, 1, 1)
    for i, (name, city, state, member) in enumerate(CUSTOMERS_RAW):
        join = base + dt.timedelta(days=random.randint(0, 900))
        first = name.split()[0].lower()
        last = name.split()[1].lower()
        rows.append(
            {
                "customer_id": f"C-{1001 + i}",
                "name": name,
                "email": f"{first}.{last}@example.com",
                "city": city,
                "state": state,
                "join_date": join.isoformat(),
                "trail_club_member": member,
            }
        )
    return rows


# --- Orders, order_items, shipments ------------------------------------------
ORDER_STATUS_BY_SHIPMENT = {
    # shipment status -> order status shown to the customer
    "Processing": "Processing",
    "Shipped": "Shipped",
    "In Transit": "Shipped",
    "Out for Delivery": "Shipped",
    "Delivered": "Delivered",
    "Delayed": "Shipped",
}
SHIPMENT_STATUSES = list(ORDER_STATUS_BY_SHIPMENT.keys())


def build_orders(customers: list[dict], products: list[dict]):
    orders, items, shipments = [], [], []
    product_by_id = {p["product_id"]: p for p in products}
    today = dt.date(2026, 1, 20)

    for n in range(30):  # order IDs 1001..1030 (so #1027 always exists)
        order_id = 1001 + n
        customer = random.choice(customers)
        member = customer["trail_club_member"]

        # 1–3 line items
        chosen = random.sample(products, k=random.randint(1, 3))
        subtotal = 0.0
        for p in chosen:
            qty = random.randint(1, 2)
            unit_price = float(p["price"])
            subtotal += unit_price * qty
            items.append(
                {
                    "order_id": order_id,
                    "product_id": p["product_id"],
                    "quantity": qty,
                    "unit_price": f"{unit_price:.2f}",
                }
            )

        method = random.choice(list(SHIPPING_METHODS))
        base_cost, (lo_days, hi_days) = SHIPPING_METHODS[method]
        # Free standard shipping for members, or any order >= $75 on Standard.
        free = method == "Standard" and (member or subtotal >= FREE_SHIP_THRESHOLD)
        shipping_cost = 0.0 if free else base_cost

        order_date = today - dt.timedelta(days=random.randint(0, 25))
        ship_status = random.choice(SHIPMENT_STATUSES)
        order_status = ORDER_STATUS_BY_SHIPMENT[ship_status]

        orders.append(
            {
                "order_id": order_id,
                "customer_id": customer["customer_id"],
                "order_date": order_date.isoformat(),
                "status": order_status,
                "shipping_method": method,
                "subtotal": f"{subtotal:.2f}",
                "shipping_cost": f"{shipping_cost:.2f}",
                "total": f"{subtotal + shipping_cost:.2f}",
            }
        )

        # Shipment record (Processing orders have no tracking yet).
        processing_start = order_date + dt.timedelta(days=random.randint(1, 2))
        est_delivery = processing_start + dt.timedelta(days=hi_days)
        if ship_status == "Processing":
            shipped_date, delivered_date, tracking, carrier = "", "", "", ""
        else:
            carrier = random.choice(CARRIERS)
            tracking = f"1Z{random.randint(10**9, 10**10 - 1)}"
            shipped_date = processing_start.isoformat()
            delivered_date = (
                est_delivery.isoformat() if ship_status == "Delivered" else ""
            )
        shipments.append(
            {
                "shipment_id": f"S-{2001 + n}",
                "order_id": order_id,
                "carrier": carrier,
                "tracking_number": tracking,
                "status": ship_status,
                "shipped_date": shipped_date,
                "estimated_delivery": est_delivery.isoformat(),
                "delivered_date": delivered_date,
            }
        )

    return orders, items, shipments


def build_inventory(products: list[dict]) -> list[dict]:
    rows = []
    for p in products:
        rows.append(
            {
                "product_id": p["product_id"],
                "warehouse": WAREHOUSE,
                "units_in_stock": random.randint(0, 120),
                "reorder_level": 20,
            }
        )
    return rows


# --- CSV writing -------------------------------------------------------------
def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {path.relative_to(REPO_ROOT)}  ({len(rows)} rows)")


# --- Referential integrity check ---------------------------------------------
def verify(customers, products, orders, items, inventory, shipments) -> None:
    cust_ids = {c["customer_id"] for c in customers}
    prod_ids = {p["product_id"] for p in products}
    order_ids = {o["order_id"] for o in orders}

    for o in orders:
        assert o["customer_id"] in cust_ids, f"order {o['order_id']} has unknown customer"
    for it in items:
        assert it["order_id"] in order_ids, f"item references unknown order {it['order_id']}"
        assert it["product_id"] in prod_ids, f"item references unknown product {it['product_id']}"
    for s in shipments:
        assert s["order_id"] in order_ids, f"shipment references unknown order {s['order_id']}"
    inv_prod_ids = {r["product_id"] for r in inventory}
    assert inv_prod_ids == prod_ids, "inventory must cover exactly the catalog"
    # Every non-Processing order should have exactly one shipment.
    ships_by_order = {s["order_id"] for s in shipments}
    assert ships_by_order == order_ids, "every order needs a shipment record"
    print("  referential integrity: OK")


# --- Markdown -> PDF ---------------------------------------------------------
# fpdf2's built-in fonts only support latin-1, but our markdown uses nicer Unicode
# punctuation (em-dashes, curly quotes, arrows). Map those to ASCII for the PDF
# render only — the markdown files keep their original typography.
_UNICODE_TO_ASCII = {
    "—": "-",   # em dash
    "–": "-",   # en dash
    "‘": "'", "’": "'",   # curly single quotes
    "“": '"', "”": '"',   # curly double quotes
    "→": "->",  # right arrow
    "…": "...", # ellipsis
    " ": " ",   # non-breaking space
    "•": "-",   # bullet
}


def _latin1_safe(text: str) -> str:
    for uni, ascii_ in _UNICODE_TO_ASCII.items():
        text = text.replace(uni, ascii_)
    # Drop anything still outside latin-1 (e.g. stray emoji) rather than crash.
    return text.encode("latin-1", "ignore").decode("latin-1")


def render_pdfs() -> None:
    try:
        import markdown as md_lib
        from fpdf import FPDF
    except ImportError:
        print(
            "  [skipped] PDF rendering needs extra packages. Run:\n"
            "      pip install fpdf2 markdown\n"
            "  (CSV data was still written; committed PDFs are unchanged.)"
        )
        return

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    for md_path in sorted(MD_DIR.glob("*.md")):
        text = _latin1_safe(md_path.read_text(encoding="utf-8"))
        html = md_lib.markdown(text, extensions=["tables"])
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        # fpdf2's write_html renders a practical subset of HTML (headings, lists,
        # paragraphs, tables) — plenty for these policy documents.
        pdf.write_html(html)
        out = PDF_DIR / f"{md_path.stem}.pdf"
        pdf.output(str(out))
        print(f"  wrote {out.relative_to(REPO_ROOT)}")


# --- Main --------------------------------------------------------------------
def main() -> None:
    print("Generating Trailhead Supply Co. data...")
    products = build_products()
    customers = build_customers()
    orders, items, shipments = build_orders(customers, products)
    inventory = build_inventory(products)

    write_csv(DATA_DIR / "products.csv", products)
    write_csv(DATA_DIR / "customers.csv", customers)
    write_csv(DATA_DIR / "orders.csv", orders)
    write_csv(DATA_DIR / "order_items.csv", items)
    write_csv(DATA_DIR / "inventory.csv", inventory)
    write_csv(DATA_DIR / "shipments.csv", shipments)

    verify(customers, products, orders, items, inventory, shipments)

    print("Rendering PDFs from documents/markdown/ ...")
    render_pdfs()

    # Show the running-example order so notebooks can reference it confidently.
    example = next(o for o in orders if o["order_id"] == 1027)
    ship = next(s for s in shipments if s["order_id"] == 1027)
    print(
        f"\nExample order #1027: status={example['status']}, "
        f"method={example['shipping_method']}, total=${example['total']}, "
        f"shipment={ship['status']}"
    )
    print("Done.")


if __name__ == "__main__":
    main()
