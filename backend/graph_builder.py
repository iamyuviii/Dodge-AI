"""
graph_builder.py — Constructs a NetworkX DiGraph from SQLite data
and serialises it to a React Flow-compatible JSON format.
"""

import sqlite3
import json
import networkx as nx
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "business.db"
GRAPH_CACHE = BASE_DIR / "graph_cache.json"


# ─── colour palette per node type ─────────────────────────────────────────────
NODE_STYLES = {
    "Customer":   {"color": "#6366f1", "icon": "👤"},
    "Address":    {"color": "#8b5cf6", "icon": "📍"},
    "SalesOrder": {"color": "#0ea5e9", "icon": "📋"},
    "OrderItem":  {"color": "#38bdf8", "icon": "🔖"},
    "Product":    {"color": "#10b981", "icon": "📦"},
    "Delivery":   {"color": "#f59e0b", "icon": "🚚"},
    "Invoice":    {"color": "#ef4444", "icon": "🧾"},
    "Payment":    {"color": "#22c55e", "icon": "💳"},
}


def build_graph() -> nx.DiGraph:
    G = nx.DiGraph()

    if not DB_PATH.exists():
        return G

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    def rows(sql):
        return conn.execute(sql).fetchall()

    # ── Customers ──
    for r in rows("SELECT * FROM customers"):
        G.add_node(f"C:{r['customer_id']}",
                   node_type="Customer",
                   label=r['customer_name'] or r['customer_id'],
                   **{k: r[k] for k in r.keys()})

    # ── Addresses ──
    for r in rows("SELECT * FROM addresses"):
        G.add_node(f"A:{r['address_id']}",
                   node_type="Address",
                   label=f"{r['city'] or ''}, {r['country'] or ''}".strip(', '),
                   **{k: r[k] for k in r.keys()})
        if r['customer_id']:
            G.add_edge(f"C:{r['customer_id']}", f"A:{r['address_id']}",
                       label="LOCATED_AT", edge_type="LOCATED_AT")

    # ── Sales Orders ──
    for r in rows("SELECT * FROM sales_orders"):
        G.add_node(f"SO:{r['order_id']}",
                   node_type="SalesOrder",
                   label=f"SO {r['order_id']}",
                   **{k: r[k] for k in r.keys()})
        if r['customer_id']:
            G.add_edge(f"C:{r['customer_id']}", f"SO:{r['order_id']}",
                       label="PLACED_ORDER", edge_type="PLACED_ORDER")

    # ── Order Items ──
    for r in rows("SELECT * FROM order_items"):
        G.add_node(f"OI:{r['item_id']}",
                   node_type="OrderItem",
                   label=f"Item {r['item_id']}",
                   **{k: r[k] for k in r.keys()})
        if r['order_id']:
            G.add_edge(f"SO:{r['order_id']}", f"OI:{r['item_id']}",
                       label="HAS_ITEM", edge_type="HAS_ITEM")
        if r['product_id']:
            G.add_edge(f"OI:{r['item_id']}", f"P:{r['product_id']}",
                       label="IS_PRODUCT", edge_type="IS_PRODUCT")

    # ── Products ──
    for r in rows("SELECT * FROM products"):
        G.add_node(f"P:{r['product_id']}",
                   node_type="Product",
                   label=r['product_name'] or r['product_id'],
                   **{k: r[k] for k in r.keys()})

    # ── Deliveries ──
    for r in rows("SELECT * FROM deliveries"):
        G.add_node(f"D:{r['delivery_id']}",
                   node_type="Delivery",
                   label=f"Delivery {r['delivery_id']}",
                   **{k: r[k] for k in r.keys()})
        if r['order_id']:
            G.add_edge(f"SO:{r['order_id']}", f"D:{r['delivery_id']}",
                       label="FULFILLED_BY", edge_type="FULFILLED_BY")

    # ── Invoices ──
    for r in rows("SELECT * FROM invoices"):
        G.add_node(f"INV:{r['invoice_id']}",
                   node_type="Invoice",
                   label=f"Invoice {r['invoice_id']}",
                   **{k: r[k] for k in r.keys()})
        if r['delivery_id']:
            G.add_edge(f"D:{r['delivery_id']}", f"INV:{r['invoice_id']}",
                       label="INVOICED_AS", edge_type="INVOICED_AS")
        if r['order_id']:
            G.add_edge(f"SO:{r['order_id']}", f"INV:{r['invoice_id']}",
                       label="BILLED_AS", edge_type="BILLED_AS")

    # ── Payments ──
    for r in rows("SELECT * FROM payments"):
        G.add_node(f"PAY:{r['payment_id']}",
                   node_type="Payment",
                   label=f"Payment {r['payment_id']}",
                   **{k: r[k] for k in r.keys()})
        if r['invoice_id']:
            G.add_edge(f"INV:{r['invoice_id']}", f"PAY:{r['payment_id']}",
                       label="PAID_VIA", edge_type="PAID_VIA")

    conn.close()
    return G

def get_initial_subgraph(G: nx.DiGraph, limit: int = 30) -> nx.DiGraph:
    """Return a connected subgraph capped at `limit` nodes."""
    if G.number_of_nodes() <= limit:
        return G
    # Seed with sales orders first to get good flow logic
    seeds = [n for n, d in G.nodes(data=True) if d.get("node_type") == "SalesOrder"]
    if not seeds:
        seeds = list(G.nodes())
        
    subgraph_nodes = set()
    queue = seeds[:4] # Take ~4 seeds
    visited = set(queue)
    
    while queue and len(subgraph_nodes) < limit:
        node = queue.pop(0)
        subgraph_nodes.add(node)
        # Add neighbors to queue
        for neighbor in G.successors(node):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
        for neighbor in G.predecessors(node):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
                
    return G.subgraph(list(subgraph_nodes))


def graph_to_json(G: nx.DiGraph) -> dict:
    """Convert NetworkX graph to React Flow node/edge format."""
    # Simple grid layout — x,y positions
    nodes_list = list(G.nodes(data=True))

    # Group by type for columnar layout
    type_order = ["Customer", "Address", "SalesOrder", "OrderItem",
                  "Product", "Delivery", "Invoice", "Payment"]

    type_buckets: dict[str, list] = {t: [] for t in type_order}
    for node_id, data in nodes_list:
        bucket = data.get("node_type", "Other")
        if bucket not in type_buckets:
            type_buckets[bucket] = []
        type_buckets[bucket].append((node_id, data))

    rf_nodes = []
    col_x = 0
    for ntype in list(type_buckets.keys()):
        bucket = type_buckets.get(ntype, [])
        if not bucket:
            continue
        style = NODE_STYLES.get(ntype, {"color": "#64748b", "icon": "⬡"})
        for row_idx, (node_id, data) in enumerate(bucket):
            meta = {k: v for k, v in data.items()
                    if k not in ("node_type", "label")}
            rf_nodes.append({
                "id": node_id,
                "type": "customNode",
                "position": {"x": col_x, "y": row_idx * 130},
                "data": {
                    "label": data.get("label", node_id),
                    "node_type": ntype,
                    "color": style["color"],
                    "icon": style["icon"],
                    "meta": meta,
                },
            })
        col_x += 260

    rf_edges = []
    for src, dst, edata in G.edges(data=True):
        rf_edges.append({
            "id": f"{src}→{dst}",
            "source": src,
            "target": dst,
            "label": edata.get("label", ""),
            "type": "smoothstep",
            "animated": True,
            "style": {"stroke": "#6366f1"},
            "labelStyle": {"fill": "#a5b4fc", "fontSize": 10},
        })

    return {"nodes": rf_nodes, "edges": rf_edges}


def get_graph_json() -> dict:
    """Return (cached) graph JSON."""
    G = build_graph()
    data = graph_to_json(G)
    # also cache to disk for inspection
    GRAPH_CACHE.write_text(json.dumps(data, indent=2))
    return data


def get_schema_summary() -> str:
    """Return a concise schema string for the LLM system prompt."""
    return """
SQLite database schema (exact table & column names):

TABLE customers  (customer_id TEXT PK, customer_name, country, region)
TABLE addresses  (address_id TEXT PK, customer_id FK→customers, street, city, postal_code, country)
TABLE products   (product_id TEXT PK, product_name, category, unit_price REAL)
TABLE sales_orders (order_id TEXT PK, customer_id FK→customers, order_date, status, total_amount REAL, currency)
TABLE order_items  (item_id TEXT PK, order_id FK→sales_orders, product_id FK→products, quantity REAL, unit_price REAL, amount REAL)
TABLE deliveries   (delivery_id TEXT PK, order_id FK→sales_orders, delivery_date, status, plant, ship_to)
TABLE invoices     (invoice_id TEXT PK, delivery_id FK→deliveries, order_id FK→sales_orders, invoice_date, amount REAL, currency, status)
TABLE payments     (payment_id TEXT PK, invoice_id FK→invoices, payment_date, amount REAL, method, status)

Key relationships:
- Customer → SalesOrder (via sales_orders.customer_id)
- SalesOrder → OrderItem (via order_items.order_id)
- OrderItem → Product (via order_items.product_id)
- SalesOrder → Delivery (via deliveries.order_id)
- Delivery → Invoice (via invoices.delivery_id)
- SalesOrder → Invoice (via invoices.order_id)
- Invoice → Payment (via payments.invoice_id)
- Customer → Address (via addresses.customer_id)
"""


if __name__ == "__main__":
    data = get_graph_json()
    print(f"Nodes: {len(data['nodes'])}, Edges: {len(data['edges'])}")
