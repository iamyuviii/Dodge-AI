import json
import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SAP_DIR = BASE_DIR / "sap-o2c-data"
DB_PATH = BASE_DIR / "backend" / "business.db"

def get_file(folder_name):
    folder = SAP_DIR / folder_name
    if not folder.exists():
        return None
    files = list(folder.glob("*.jsonl"))
    return files[0] if files else None

def ingest_jsonl(conn):
    print("Ingesting SAP JSONL data...")
    cur = conn.cursor()
    
    # 1. Determine 50 valid Sales Orders that have flows
    valid_so = set()
    inv_items_file = get_file("billing_document_items")
    if inv_items_file:
         with open(inv_items_file, "r") as f:
            for line in f:
                doc = json.loads(line)
                ref = doc.get("referenceSdDocument")
                if ref and len(valid_so) < 40:
                    valid_so.add(ref)

    # Add a few open orders (from the start of the file)
    so_file = get_file("sales_order_headers")
    sales_orders = []
    if so_file:
        with open(so_file, "r") as f:
            for line in f:
                doc = json.loads(line)
                so_id = doc.get("salesOrder")
                if so_id in valid_so or len(valid_so) < 50:
                    valid_so.add(so_id)
                    sales_orders.append((
                        so_id,
                        doc.get("soldToParty"),
                        doc.get("creationDate"),
                        doc.get("overallDeliveryStatus"),
                        doc.get("totalNetAmount", 0),
                        doc.get("transactionCurrency")
                    ))
                    if len(sales_orders) >= 50:
                        break
    
    valid_cust = {so[1] for so in sales_orders}
    
    # 2. Customers
    bp_file = get_file("business_partners")
    customers = []
    if bp_file:
        with open(bp_file, "r") as f:
            for line in f:
                doc = json.loads(line)
                bpid = doc.get("businessPartner")
                # SAP often pads customer IDs with leading zeros
                if bpid in valid_cust or bpid.lstrip("0") in valid_cust or bpid.lstrip("0") == ("" if not bpid else ""):
                     customers.append((
                        bpid,
                        doc.get("businessPartnerFullName", doc.get("businessPartnerName", "Unknown")),
                        doc.get("correspondenceLanguage", "US"),
                        doc.get("region", "Default")
                    ))
    
    # Add dummy customers for any missing ones to prevent FK errors
    found_custs = {c[0] for c in customers}
    for c_id in valid_cust:
        if c_id not in found_custs:
            customers.append((c_id, f"Customer {c_id}", "US", "Default"))

    cur.executemany("INSERT OR IGNORE INTO customers VALUES (?,?,?,?)", customers)
    print(f"Loaded {len(customers)} customers.")

    cur.executemany("INSERT OR IGNORE INTO sales_orders VALUES (?,?,?,?,?,?)", sales_orders)
    print(f"Loaded {len(sales_orders)} sales orders.")

    # 3. Order Items and Products
    oi_file = get_file("sales_order_items")
    order_items = []
    valid_materials = set()
    if oi_file:
        with open(oi_file, "r") as f:
            for line in f:
                doc = json.loads(line)
                if doc.get("salesOrder") in valid_so:
                    order_items.append((
                        doc.get("salesOrderItem"),
                        doc.get("salesOrder"),
                        doc.get("material"),
                        doc.get("requestedQuantity", 0),
                        0, # unit price missing here, default 0
                        doc.get("netAmount", 0)
                    ))
                    valid_materials.add(doc.get("material"))

    prod_file = get_file("products")
    products = []
    if prod_file:
        with open(prod_file, "r") as f:
            for line in f:
                doc = json.loads(line)
                mat = doc.get("product")
                if mat in valid_materials:
                    products.append((
                        mat,
                        doc.get("productType", "Unknown"),
                        doc.get("productGroup", "Group"),
                        0 # unit price missing
                    ))
                    
    # Prevent FK errors for products
    found_prods = {p[0] for p in products}
    for p_id in valid_materials:
        if p_id not in found_prods:
            products.append((p_id, f"Product {p_id}", "Group", 0))

    cur.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?)", products)
    print(f"Loaded {len(products)} products.")

    cur.executemany("INSERT OR IGNORE INTO order_items VALUES (?,?,?,?,?,?)", order_items)
    print(f"Loaded {len(order_items)} order items.")

    # 4. Deliveries
    del_file = get_file("outbound_delivery_headers")
    deliveries = []
    valid_del = set()
    
    del_items_file = get_file("outbound_delivery_items")
    del_to_so = {}
    if del_items_file:
        with open(del_items_file, "r") as f:
            for line in f:
                doc = json.loads(line)
                if doc.get("referenceSdDocument") in valid_so:
                    del_to_so[doc.get("deliveryDocument")] = doc.get("referenceSdDocument")
                    
    if del_file:
        with open(del_file, "r") as f:
            for line in f:
                doc = json.loads(line)
                did = doc.get("deliveryDocument")
                if did in del_to_so:
                    deliveries.append((
                        did,
                        del_to_so[did],
                        doc.get("creationDate"),
                        doc.get("overallGoodsMovementStatus"),
                        "N/A", # plant
                        "N/A"  # shipTo
                    ))
                    valid_del.add(did)
    cur.executemany("INSERT OR IGNORE INTO deliveries VALUES (?,?,?,?,?,?)", deliveries)
    print(f"Loaded {len(deliveries)} deliveries.")

    # 5. Invoices
    inv_file = get_file("billing_document_headers")
    invoices = []
    valid_inv = set()
    
    inv_items_file = get_file("billing_document_items")
    inv_to_so = {}
    inv_to_del = {}
    if inv_items_file:
         with open(inv_items_file, "r") as f:
            for line in f:
                doc = json.loads(line)
                ref = doc.get("referenceSdDocument")
                if ref in valid_so:
                    inv_to_so[doc.get("billingDocument")] = ref
                elif ref in valid_del:
                    inv_to_del[doc.get("billingDocument")] = ref
                    
    if inv_file:
        with open(inv_file, "r") as f:
            for line in f:
                doc = json.loads(line)
                iid = doc.get("billingDocument")
                so_ref = inv_to_so.get(iid)
                del_ref = inv_to_del.get(iid)
                if so_ref or del_ref:
                    invoices.append((
                        iid,
                        del_ref,
                        so_ref if so_ref else del_to_so.get(del_ref),
                        doc.get("creationDate"),
                        doc.get("totalNetAmount", 0),
                        doc.get("transactionCurrency"),
                        doc.get("billingDocumentIsCancelled")
                    ))
                    valid_inv.add(iid)
    cur.executemany("INSERT OR IGNORE INTO invoices VALUES (?,?,?,?,?,?,?)", invoices)
    print(f"Loaded {len(invoices)} invoices.")

    # 6. Payments
    pay_file = get_file("payments_accounts_receivable")
    payments = []
    if pay_file:
        with open(pay_file, "r") as f:
            for line in f:
                doc = json.loads(line)
                inv_ref = doc.get("invoiceReference")
                if inv_ref in valid_inv:
                    payments.append((
                        doc.get("accountingDocument"),
                        inv_ref,
                        doc.get("postingDate"),
                        doc.get("amountInCompanyCodeCurrency", 0),
                        doc.get("financialAccountType"),
                        "Cleared" if doc.get("clearingDate") else "Open"
                    ))
    cur.executemany("INSERT OR IGNORE INTO payments VALUES (?,?,?,?,?,?)", payments)
    print(f"Loaded {len(payments)} payments.")
    
    conn.commit()

if __name__ == "__main__":
    import preprocess
    conn = sqlite3.connect(DB_PATH)
    schema = preprocess.CREATE_SCHEMA.replace("PRAGMA foreign_keys = ON;", "PRAGMA foreign_keys = OFF;")
    conn.executescript(schema)
    conn.commit()
    ingest_jsonl(conn)
    conn.close()
    print("Database built successfully!")
