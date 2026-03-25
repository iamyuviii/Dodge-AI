"""
preprocess.py — Dataset ingestion & SQLite DB creation.

Since the dataset ships as an Excel file with multiple sheets,
we read each sheet into a pandas DataFrame, clean it, and
store it into SQLite. The script is idempotent (safe to re-run).
"""

import os
import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "backend" / "business.db"


# ─── helpers ──────────────────────────────────────────────────────────────────

def clean_col(col: str) -> str:
    """Normalise a column header to snake_case."""
    return (
        col.strip()
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
        .replace(".", "")
    )


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [clean_col(c) for c in df.columns]
    df = df.dropna(how="all")
    # Strip whitespace from string columns
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def find_dataset() -> Path | None:
    """Return the first Excel/CSV file found in data/."""
    for ext in ("*.xlsx", "*.xls", "*.csv"):
        files = list(DATA_DIR.glob(ext))
        if files:
            return files[0]
    return None


# ─── sheet readers ────────────────────────────────────────────────────────────

def read_excel_sheets(path: Path) -> dict[str, pd.DataFrame]:
    xl = pd.ExcelFile(path)
    return {sheet: clean_df(xl.parse(sheet)) for sheet in xl.sheet_names}


def read_csv(path: Path) -> dict[str, pd.DataFrame]:
    return {"data": clean_df(pd.read_csv(path))}


# ─── schema & write ───────────────────────────────────────────────────────────

CREATE_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    customer_id   TEXT PRIMARY KEY,
    customer_name TEXT,
    country       TEXT,
    region        TEXT
);

CREATE TABLE IF NOT EXISTS addresses (
    address_id   TEXT PRIMARY KEY,
    customer_id  TEXT REFERENCES customers(customer_id),
    street       TEXT,
    city         TEXT,
    postal_code  TEXT,
    country      TEXT
);

CREATE TABLE IF NOT EXISTS products (
    product_id   TEXT PRIMARY KEY,
    product_name TEXT,
    category     TEXT,
    unit_price   REAL
);

CREATE TABLE IF NOT EXISTS sales_orders (
    order_id      TEXT PRIMARY KEY,
    customer_id   TEXT REFERENCES customers(customer_id),
    order_date    TEXT,
    status        TEXT,
    total_amount  REAL,
    currency      TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    item_id    TEXT PRIMARY KEY,
    order_id   TEXT REFERENCES sales_orders(order_id),
    product_id TEXT REFERENCES products(product_id),
    quantity   REAL,
    unit_price REAL,
    amount     REAL
);

CREATE TABLE IF NOT EXISTS deliveries (
    delivery_id   TEXT PRIMARY KEY,
    order_id      TEXT REFERENCES sales_orders(order_id),
    delivery_date TEXT,
    status        TEXT,
    plant         TEXT,
    ship_to       TEXT
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id   TEXT PRIMARY KEY,
    delivery_id  TEXT REFERENCES deliveries(delivery_id),
    order_id     TEXT REFERENCES sales_orders(order_id),
    invoice_date TEXT,
    amount       REAL,
    currency     TEXT,
    status       TEXT
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id   TEXT PRIMARY KEY,
    invoice_id   TEXT REFERENCES invoices(invoice_id),
    payment_date TEXT,
    amount       REAL,
    method       TEXT,
    status       TEXT
);
"""


# ─── column-name aliases (maps from discovered sheets to canonical tables) ────
# We try to auto-map columns; sheets may have recognisable prefixes/names.

SHEET_TABLE_MAP = {
    # common names that appear in SAP-style exports
    "sales order": "sales_orders",
    "sales_order": "sales_orders",
    "orders":      "sales_orders",
    "order":       "sales_orders",

    "order item":  "order_items",
    "order_item":  "order_items",
    "order items": "order_items",
    "items":       "order_items",
    "line items":  "order_items",

    "delivery":    "deliveries",
    "deliveries":  "deliveries",

    "invoice":     "invoices",
    "invoices":    "invoices",
    "billing":     "invoices",
    "billing document": "invoices",

    "payment":     "payments",
    "payments":    "payments",

    "customer":    "customers",
    "customers":   "customers",

    "product":     "products",
    "products":    "products",
    "material":    "products",
    "materials":   "products",

    "address":     "addresses",
    "addresses":   "addresses",
}


def _col_alias(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first existing column from candidates."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def infer_id_column(df: pd.DataFrame, table: str) -> str | None:
    """Try to find a primary-key column for a given table."""
    prefixes = {
        "sales_orders": ["order_id", "salesorderid", "so_number", "vbeln", "doc_number"],
        "order_items":  ["item_id", "orderitemid", "posnr", "item_number"],
        "deliveries":   ["delivery_id", "deliveryid", "deliv_numb", "likp_vbeln"],
        "invoices":     ["invoice_id", "invoiceid", "billing_doc", "vbeln_vf", "belnr"],
        "payments":     ["payment_id", "paymentid", "doc_number", "augbl"],
        "customers":    ["customer_id", "customerid", "kunnr", "sold_to"],
        "products":     ["product_id", "productid", "matnr", "material_number"],
        "addresses":    ["address_id", "adrnr", "address_number"],
    }
    return _col_alias(df, prefixes.get(table, []))


def smart_load(sheets: dict[str, pd.DataFrame], conn: sqlite3.Connection):
    """
    Attempt to load sheets into matching tables.
    Falls back to writing the sheet as a raw table if no match found.
    """
    cursor = conn.cursor()

    for sheet_name, df in sheets.items():
        table = SHEET_TABLE_MAP.get(sheet_name.lower().strip())

        if table:
            print(f"  Mapping sheet '{sheet_name}' → table '{table}'")
            # Write to the matched table (replace existing rows)
            try:
                df.to_sql(table, conn, if_exists="replace", index=False)
                print(f"    ✓ Loaded {len(df)} rows into '{table}'")
            except Exception as e:
                print(f"    ✗ Failed to load '{table}': {e}")
        else:
            # Write as-is with the sheet name as table name
            raw_table = clean_col(sheet_name)
            print(f"  Sheet '{sheet_name}' → raw table '{raw_table}'")
            try:
                df.to_sql(raw_table, conn, if_exists="replace", index=False)
                print(f"    ✓ Loaded {len(df)} rows into '{raw_table}'")
            except Exception as e:
                print(f"    ✗ Failed: {e}")


def seed_demo_data(conn: sqlite3.Connection):
    """
    Populate tables with a concise demo dataset (~28 graph nodes)
    that still illustrates complete and incomplete business flows.
    """
    print("  Seeding demo data…")
    cur = conn.cursor()

    cur.executescript("""
    -- Customers (3)
    INSERT OR IGNORE INTO customers VALUES ('C001','Acme Corp','US','North');
    INSERT OR IGNORE INTO customers VALUES ('C002','Global Trade GmbH','DE','Europe');
    INSERT OR IGNORE INTO customers VALUES ('C003','Pacific Rim Ltd','JP','Asia');

    -- Addresses (3)
    INSERT OR IGNORE INTO addresses VALUES ('A001','C001','123 Main St','New York','10001','US');
    INSERT OR IGNORE INTO addresses VALUES ('A002','C002','Berliner Str 45','Berlin','10115','DE');
    INSERT OR IGNORE INTO addresses VALUES ('A003','C003','Shibuya 2-1','Tokyo','150-0002','JP');

    -- Products (4)
    INSERT OR IGNORE INTO products VALUES ('P001','Industrial Pump','Machinery',4500.00);
    INSERT OR IGNORE INTO products VALUES ('P002','Control Unit','Electronics',1200.00);
    INSERT OR IGNORE INTO products VALUES ('P003','Steel Pipes (set)','Raw Material',320.00);
    INSERT OR IGNORE INTO products VALUES ('P004','Safety Valve','Hardware',85.00);

    -- Sales Orders (4)
    -- SO001: Complete full flow (SO → Delivery → Invoice → Payment)
    INSERT OR IGNORE INTO sales_orders VALUES ('SO001','C001','2024-01-05','Complete',10425.00,'USD');
    -- SO002: Complete full flow
    INSERT OR IGNORE INTO sales_orders VALUES ('SO002','C002','2024-01-12','Complete',4800.00,'EUR');
    -- SO003: Delivered but NOT invoiced (incomplete flow)
    INSERT OR IGNORE INTO sales_orders VALUES ('SO003','C003','2024-01-20','Delivered',640.00,'JPY');
    -- SO004: Open — no delivery yet (incomplete flow)
    INSERT OR IGNORE INTO sales_orders VALUES ('SO004','C001','2024-02-01','Open',1200.00,'USD');

    -- Order Items (8)
    INSERT OR IGNORE INTO order_items VALUES ('OI001','SO001','P001',2,4500.00,9000.00);
    INSERT OR IGNORE INTO order_items VALUES ('OI002','SO001','P004',5,85.00,425.00);
    INSERT OR IGNORE INTO order_items VALUES ('OI003','SO002','P002',4,1200.00,4800.00);
    INSERT OR IGNORE INTO order_items VALUES ('OI004','SO003','P003',2,320.00,640.00);
    INSERT OR IGNORE INTO order_items VALUES ('OI005','SO004','P002',1,1200.00,1200.00);
    INSERT OR IGNORE INTO order_items VALUES ('OI006','SO001','P003',3,320.00,960.00);
    INSERT OR IGNORE INTO order_items VALUES ('OI007','SO002','P004',1,85.00,85.00);
    INSERT OR IGNORE INTO order_items VALUES ('OI008','SO004','P001',1,4500.00,4500.00);

    -- Deliveries (3 — SO004 has none: incomplete)
    INSERT OR IGNORE INTO deliveries VALUES ('D001','SO001','2024-01-15','Delivered','Plant-A','New York');
    INSERT OR IGNORE INTO deliveries VALUES ('D002','SO002','2024-01-25','Delivered','Plant-B','Berlin');
    INSERT OR IGNORE INTO deliveries VALUES ('D003','SO003','2024-02-05','Delivered','Plant-C','Tokyo');

    -- Invoices (2 — D003/SO003 not invoiced: incomplete)
    INSERT OR IGNORE INTO invoices VALUES ('INV001','D001','SO001','2024-01-20',10425.00,'USD','Paid');
    INSERT OR IGNORE INTO invoices VALUES ('INV002','D002','SO002','2024-02-01',4800.00,'EUR','Outstanding');

    -- Payments (1 — INV002 unpaid: outstanding)
    INSERT OR IGNORE INTO payments VALUES ('PAY001','INV001','2024-01-28',10425.00,'Wire Transfer','Completed');
    """)
    conn.commit()
    print("  ✓ Demo data seeded.")


# ─── main ─────────────────────────────────────────────────────────────────────


def run():
    print("=== Data Preprocessor ===")
    print(f"DB path: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(CREATE_SCHEMA)
    conn.commit()
    print("✓ Schema created")

    dataset = find_dataset()

    if dataset:
        print(f"Found dataset: {dataset.name}")
        if dataset.suffix in (".xlsx", ".xls"):
            sheets = read_excel_sheets(dataset)
        else:
            sheets = read_csv(dataset)
        smart_load(sheets, conn)
    else:
        print("No dataset file found in data/ — seeding demo data.")
        seed_demo_data(conn)

    conn.close()
    print("=== Done ===")


if __name__ == "__main__":
    run()
