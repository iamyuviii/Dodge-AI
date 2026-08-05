"""
groq_client.py — Groq LLM integration with guardrails + SQL generation.
"""

import os
import sqlite3
import json
import re
import logging
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
from graph_builder import get_schema_summary

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger("nexora.groq")

DB_PATH = Path(__file__).parent / "business.db"

_client: Groq | None = None

# Maximum number of SQL retry attempts when execution fails
MAX_SQL_RETRIES = 2

# Timeout for Groq API calls (seconds)
API_TIMEOUT = 30


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key or api_key == "your_groq_api_key_here":
            raise ValueError("GROQ_API_KEY is not set. Please add it to .env")
        _client = Groq(api_key=api_key, timeout=API_TIMEOUT)
    return _client


MODEL = "llama-3.3-70b-versatile"

SCHEMA = get_schema_summary()

# ─── System prompts ────────────────────────────────────────────────────────────

GUARDRAIL_PROMPT = """You are a strict domain classifier.
Your ONLY job is to decide whether a user's message is related to business data analysis
(sales orders, deliveries, invoices, payments, customers, products, billing documents, etc.).

Reply with EXACTLY one word:
- "YES" if the message is related to the business domain described above
- "NO" if it is not (general knowledge, coding, creative writing, geography, sports, etc.)

Do not output anything other than YES or NO."""

SQL_GEN_PROMPT = f"""You are an expert SQLite query generator for a business data system.

{SCHEMA}

Rules:
1. Generate ONLY a single valid SQLite SELECT query — nothing else. Keep your output to just the query itself, with no text preamble or postamble.
2. Do NOT include markdown fences (```) or comments around the query.
3. Use exact table and column names from the schema above.
4. ALWAYS append "LIMIT 50" to the query to restrict the number of results, UNLESS the user explicitly asks for all records OR the query is an aggregation (like COUNT, SUM) that naturally returns one row.
5. If the question cannot be answered with the available schema, output EXACTLY the phrase: CANNOT_ANSWER
6. Never run INSERT, UPDATE, DELETE, DROP, or any write operation.

Example 1: "Which products are associated with the highest number of billing documents?"
SELECT p.product_name, COUNT(i.invoice_id)   as num_invoices FROM products p JOIN order_items oi ON p.product_id = oi.product_id JOIN invoices i ON oi.order_id = i.order_id GROUP BY p.product_id ORDER BY num_invoices DESC LIMIT 10;

Example 2: "Trace the full flow of billing document INV001"
SELECT so.order_id, d.delivery_id, i.invoice_id, p.payment_id FROM invoices i LEFT JOIN sales_orders so ON i.order_id = so.order_id LEFT JOIN deliveries d ON i.delivery_id = d.delivery_id LEFT JOIN payments p ON i.invoice_id = p.invoice_id WHERE i.invoice_id = 'INV001';
"""

SQL_FIX_PROMPT = f"""You are an expert SQLite query fixer.

{SCHEMA}

The user asked a question and a SQL query was generated, but it failed with an error.
Your job is to fix the SQL query so it executes correctly.
Output ONLY the corrected SQL query — no explanation, no markdown fences.
If the query is unfixable, output EXACTLY: CANNOT_ANSWER
"""

ANSWER_PROMPT = """You are a helpful business data analyst assistant.
The user asked a question. SQL was executed against a business database and returned results.
Summarise the data in clear, human-friendly natural language.
Be concise (3-6 sentences). Reference specific numbers and entity IDs from the data.
Do NOT fabricate data not present in the query results.
"""

OFF_TOPIC_REPLY = (
    "I'm sorry, but this system is designed to answer questions related to the "
    "business dataset only (sales orders, deliveries, invoices, payments, customers, products). "
    "Please ask a question about the data."
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _chat(messages: list[dict], temperature: float = 0.1) -> str:
    client = get_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=1024,
    )
    return resp.choices[0].message.content.strip()


def _is_on_topic(message: str) -> bool:
    reply = _chat([
        {"role": "system", "content": GUARDRAIL_PROMPT},
        {"role": "user",   "content": message},
    ])
    return reply.strip().upper().startswith("YES")


def _generate_sql(message: str) -> str:
    return _chat([
        {"role": "system", "content": SQL_GEN_PROMPT},
        {"role": "user",   "content": message},
    ])


def _fix_sql(original_question: str, broken_sql: str, error: str) -> str:
    """Ask the LLM to fix a broken SQL query."""
    return _chat([
        {"role": "system", "content": SQL_FIX_PROMPT},
        {"role": "user", "content": (
            f"Original question: {original_question}\n\n"
            f"Generated SQL:\n{broken_sql}\n\n"
            f"Error:\n{error}\n\n"
            f"Please fix this query."
        )},
    ])


def _clean_sql(raw: str) -> str:
    """Strip markdown fences and extraneous formatting from LLM-generated SQL."""
    sql = raw.strip()
    # Remove ```sql ... ``` blocks
    match = re.search(r"```[a-zA-Z]*\n?(.*?)\n?```", sql, re.DOTALL)
    if match:
        sql = match.group(1).strip()
    else:
        sql = re.sub(r"```[a-zA-Z]*", "", sql).strip().strip("`")
    # Remove leading/trailing semicolons and whitespace
    sql = sql.strip().rstrip(";").strip()
    return sql


def _execute_sql(sql: str) -> tuple[list[dict], str | None]:
    """Execute SQL and return (rows_as_dicts, error_or_None)."""
    if not DB_PATH.exists():
        return [], "Database not found. Run preprocess.py first."
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(sql)
            rows = [dict(r) for r in cur.fetchall()]
        return rows, None
    except Exception as e:
        return [], str(e)


def _summarise(question: str, sql: str, rows: list[dict]) -> str:
    data_str = json.dumps(rows[:50], indent=2, default=str)
    return _chat([
        {"role": "system", "content": ANSWER_PROMPT},
        {"role": "user",   "content": (
            f"User question: {question}\n\n"
            f"SQL used:\n{sql}\n\n"
            f"Query results ({len(rows)} matching rows total, showing up to {min(len(rows), 50)}):\n{data_str}"
        )},
    ], temperature=0.3)


def _is_write_operation(sql: str) -> bool:
    """Check if SQL contains forbidden write operations."""
    return bool(re.search(
        r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b",
        sql, re.IGNORECASE,
    ))


# ─── public API ───────────────────────────────────────────────────────────────

def answer_query(message: str) -> dict:
    """
    Main pipeline:
      1. Guardrail check
      2. SQL generation
      3. SQL execution (with retry on failure)
      4. Natural-language answer
    Returns dict with keys: answer, sql, data, error
    """

    # Step 1: Guardrail
    try:
        on_topic = _is_on_topic(message)
    except ValueError as e:
        return {
            "answer": str(e),
            "sql": None,
            "data": [],
            "error": "API key not configured",
        }

    if not on_topic:
        return {
            "answer": OFF_TOPIC_REPLY,
            "sql": None,
            "data": [],
            "error": None,
        }

    # Step 2: Generate SQL
    try:
        raw_sql = _generate_sql(message)
    except Exception as e:
        logger.error("SQL generation failed: %s", e)
        return {
            "answer": "Failed to generate a query. Please try rephrasing.",
            "sql": None,
            "data": [],
            "error": str(e),
        }

    sql = _clean_sql(raw_sql)

    if sql.upper().startswith("CANNOT_ANSWER"):
        return {
            "answer": (
                "I couldn't find a way to answer that question with the available data. "
                "Please try a different question about orders, deliveries, invoices, or payments."
            ),
            "sql": None,
            "data": [],
            "error": None,
        }

    # Safety: block write operations
    if _is_write_operation(sql):
        return {
            "answer": "That type of operation is not allowed.",
            "sql": None,
            "data": [],
            "error": "Write operation blocked",
        }

    # Step 3: Execute (with retry)
    rows, sql_error = _execute_sql(sql)

    if sql_error:
        logger.warning("SQL execution failed, attempting retry. Error: %s", sql_error)
        for attempt in range(MAX_SQL_RETRIES):
            try:
                fixed_raw = _fix_sql(message, sql, sql_error)
                fixed_sql = _clean_sql(fixed_raw)

                if fixed_sql.upper().startswith("CANNOT_ANSWER"):
                    break

                if _is_write_operation(fixed_sql):
                    break

                rows, sql_error = _execute_sql(fixed_sql)
                if not sql_error:
                    sql = fixed_sql
                    logger.info("SQL retry %d succeeded.", attempt + 1)
                    break
            except Exception as e:
                logger.warning("SQL retry %d failed: %s", attempt + 1, e)

    if sql_error:
        return {
            "answer": f"The query encountered an error: {sql_error}. Please try rephrasing.",
            "sql": sql,
            "data": [],
            "error": sql_error,
        }

    # Step 4: Summarise
    try:
        answer = _summarise(message, sql, rows)
    except Exception as e:
        logger.error("Summarisation failed: %s", e)
        answer = f"Query returned {len(rows)} result(s) but narrative generation failed."

    return {
        "answer": answer,
        "sql": sql,
        "data": rows,
        "error": None,
    }
