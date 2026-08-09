

import logging
import re
import sqlite3
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import networkx as nx

from graph_builder import build_graph, graph_to_json, NODE_STYLES, get_initial_subgraph
from groq_client import answer_query
import preprocess

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nexora")

BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "business.db"

# ─── Graph cache ──────────────────────────────────────────────────────────────

_graph: nx.DiGraph | None = None


def get_graph() -> nx.DiGraph:
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ─── Lifespan (replaces deprecated @app.on_event) ────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    global _graph
    if not DB_PATH.exists():
        logger.info("Database not found — running preprocessor…")
        preprocess.run()
    _graph = build_graph()
    logger.info(
        "Graph loaded: %d nodes, %d edges",
        _graph.number_of_nodes(),
        _graph.number_of_edges(),
    )
    yield
    logger.info("Server shutting down.")


app = FastAPI(title="Nexora API", version="1.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Response models ─────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    nodes: int
    edges: int
    db_exists: bool


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    sql: str | None = None
    data: list[dict] = []
    error: str | None = None


class UploadResponse(BaseModel):
    status: str
    filename: str
    nodes: int
    edges: int


class ReloadResponse(BaseModel):
    nodes: int
    edges: int


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse)
def health():
    G = get_graph()
    return HealthResponse(
        status="ok",
        nodes=G.number_of_nodes(),
        edges=G.number_of_edges(),
        db_exists=DB_PATH.exists(),
    )


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

    _VALID_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        result = {}
        for table in tables:
            # Sanitize table name to prevent SQL injection
            if not _VALID_TABLE_RE.match(table):
                logger.warning("Skipping table with invalid name: %s", table)
                continue
            cur2 = conn.execute(f"PRAGMA table_info([{table}])")
            result[table] = [{"name": r[1], "type": r[2]} for r in cur2.fetchall()]
    return {"tables": result}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(400, "Message cannot be empty")
    result = answer_query(req.message.strip())
    return ChatResponse(**result)


@app.post("/api/reload", response_model=ReloadResponse)
def reload_graph():
    """Force-reload the graph from the database."""
    global _graph
    _graph = build_graph()
    logger.info("Graph reloaded: %d nodes, %d edges", _graph.number_of_nodes(), _graph.number_of_edges())
    return ReloadResponse(nodes=_graph.number_of_nodes(), edges=_graph.number_of_edges())


ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_data(file: UploadFile = File(...)):
    """Accept a CSV or Excel file, save it to data/, re-run preprocessor, reload graph."""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Please upload CSV or Excel.")

    # Save to data/ directory (overwrite any existing file)
    data_dir = BASE_DIR.parent / "data"
    data_dir.mkdir(exist_ok=True)

    # Remove old files first
    for old in data_dir.iterdir():
        if old.suffix.lower() in ALLOWED_EXTENSIONS:
            old.unlink()

    dest = data_dir / file.filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    logger.info("Saved uploaded file: %s (%s)", file.filename, ext)

    # Remove old DB so preprocessor rebuilds from scratch
    if DB_PATH.exists():
        DB_PATH.unlink()

    # Rebuild database and graph
    try:
        preprocess.run()
    except Exception as e:
        logger.error("Preprocessing failed: %s", e)
        raise HTTPException(500, f"Failed to process uploaded file: {e}")

    global _graph
    _graph = build_graph()
    logger.info(
        "Upload complete — graph rebuilt: %d nodes, %d edges",
        _graph.number_of_nodes(),
        _graph.number_of_edges(),
    )

    return UploadResponse(
        status="ok",
        filename=file.filename,
        nodes=_graph.number_of_nodes(),
        edges=_graph.number_of_edges(),
    )
