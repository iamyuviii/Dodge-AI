"""
main.py — FastAPI backend server.
Endpoints:
  GET  /api/graph          → full graph JSON
  GET  /api/graph/expand   → neighbors of a node
  POST /api/chat           → LLM-powered natural-language query
  GET  /api/health         → health check
"""

import sqlite3
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import networkx as nx

from graph_builder import build_graph, graph_to_json, NODE_STYLES
from groq_client import answer_query
import preprocess

BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "business.db"

app = FastAPI(title="Context Graph API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache
_graph: nx.DiGraph | None = None


def get_graph() -> nx.DiGraph:
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    if not DB_PATH.exists():
        print("Database not found — running preprocessor…")
        preprocess.run()
    global _graph
    _graph = build_graph()
    print(f"Graph loaded: {_graph.number_of_nodes()} nodes, {_graph.number_of_edges()} edges")


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    G = get_graph()
    return {
        "status": "ok",
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "db_exists": DB_PATH.exists(),
    }


from graph_builder import build_graph, graph_to_json, NODE_STYLES, get_initial_subgraph

@app.get("/api/graph")
def get_graph_endpoint():
    G = get_graph()
    sub_G = get_initial_subgraph(G, 30)
    return graph_to_json(sub_G)


@app.get("/api/graph/expand/{node_id:path}")
def expand_node(node_id: str):
    """Return the node + its immediate neighbours as a mini sub-graph."""
    G = get_graph()
    if node_id not in G:
        raise HTTPException(404, f"Node '{node_id}' not found")

    subgraph_nodes = {node_id}
    predecessors = list(G.predecessors(node_id))
    successors   = list(G.successors(node_id))
    subgraph_nodes.update(predecessors)
    subgraph_nodes.update(successors)

    sub = G.subgraph(subgraph_nodes)
    return graph_to_json(sub)


@app.get("/api/graph/node/{node_id:path}")
def get_node_detail(node_id: str):
    """Return full metadata for a single node."""
    G = get_graph()
    if node_id not in G:
        raise HTTPException(404, f"Node '{node_id}' not found")
    data = G.nodes[node_id]
    style = NODE_STYLES.get(data.get("node_type", ""), {"color": "#64748b", "icon": "⬡"})
    return {
        "id": node_id,
        "node_type": data.get("node_type"),
        "label": data.get("label", node_id),
        "color": style["color"],
        "icon": style["icon"],
        "meta": {k: v for k, v in data.items() if k not in ("node_type", "label")},
        "in_edges": [
            {"source": s, "label": G.edges[s, node_id].get("label", "")}
            for s in G.predecessors(node_id)
        ],
        "out_edges": [
            {"target": t, "label": G.edges[node_id, t].get("label", "")}
            for t in G.successors(node_id)
        ],
    }


@app.get("/api/schema")
def get_schema():
    """Return the list of tables in the SQLite database."""
    if not DB_PATH.exists():
        return {"tables": []}
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    result = {}
    for table in tables:
        cur2 = conn.execute(f"PRAGMA table_info({table})")
        result[table] = [{"name": r[1], "type": r[2]} for r in cur2.fetchall()]
    conn.close()
    return {"tables": result}


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(400, "Message cannot be empty")
    result = answer_query(req.message.strip())
    return result


@app.post("/api/reload")
def reload_graph():
    """Force-reload the graph from the database."""
    global _graph
    _graph = build_graph()
    return {"nodes": _graph.number_of_nodes(), "edges": _graph.number_of_edges()}
