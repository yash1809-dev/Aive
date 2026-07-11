"""
app/main.py
============
AIVE Discovery Dashboard. Flask web server.
Exposes Papers, Patents, Graph Nodes, Opportunities, and Rejected Ideas.
"""

import json
import re
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, render_template, jsonify, request

ROOT = Path(__file__).resolve().parent.parent
MASTER_DB_PATH = ROOT / "data" / "aive.db"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB max upload

# Ensure the master database (aive.db) is always initialized
def _ensure_master_db():
    from db.init_db import init_db, SCHEMA_PATH
    MASTER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MASTER_DB_PATH.exists():
        import sqlite3
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        with sqlite3.connect(MASTER_DB_PATH) as conn:
            conn.executescript(schema)

_ensure_master_db()


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return slug[:60] or "untitled"


def fetch_url_text(url: str) -> tuple[str, str]:
    """Fetches a URL and strips HTML tags to return (title, plain_text)."""
    import urllib.request
    import html
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AIVE-Bot/1.0)"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw_bytes = resp.read()
    charset = resp.headers.get_content_charset() or "utf-8"
    raw_html = raw_bytes.decode(charset, errors="replace")
    # Extract <title>
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.IGNORECASE | re.DOTALL)
    page_title = html.unescape(title_match.group(1).strip()) if title_match else url
    # Strip scripts/styles
    clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=re.IGNORECASE | re.DOTALL)
    # Strip all remaining tags
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = html.unescape(clean)
    # Collapse whitespace
    clean = re.sub(r"[ \t]+", " ", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    return page_title, clean[:50000]  # cap at 50k chars


ACTIVE_WORKSPACE_ID = "default"


def save_item(title, raw_text, source_url, item_type, year=None):
    """Save a new source item to the database and return item_id."""
    year = year or str(datetime.now(timezone.utc).year)
    item_id = f"{item_type}_{slugify(title[:20])}_{uuid.uuid4().hex[:4]}"
    conn = get_db_connection()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO items
               (id, title, source, source_url, type, raw_text, year, extraction_status)
               VALUES (?, ?, 'manual', ?, ?, ?, ?, 'pending')""",
            (item_id, title, source_url, item_type, raw_text, year)
        )
        conn.commit()
    finally:
        conn.close()
    return item_id


def trigger_extraction_background():
    """Non-blocking single-paper extraction + incremental graph build."""
    import os
    env = dict(os.environ, AIVE_ACTIVE_WORKSPACE=ACTIVE_WORKSPACE_ID)
    subprocess.Popen(
        [sys.executable, "-u", "agents/research_analyst.py", "5"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env
    )


def get_db_connection():
    global ACTIVE_WORKSPACE_ID
    import os
    import importlib
    os.environ["AIVE_ACTIVE_WORKSPACE"] = ACTIVE_WORKSPACE_ID
    import db.init_db
    importlib.reload(db.init_db)
    
    conn = sqlite3.connect(db.init_db.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def stats():
    conn = get_db_connection()
    try:
        papers = conn.execute("SELECT COUNT(*) FROM items WHERE type='paper'").fetchone()[0]
        patents = conn.execute("SELECT COUNT(*) FROM items WHERE type='patent'").fetchone()[0]
        startups = conn.execute("SELECT COUNT(*) FROM items WHERE type='startup'").fetchone()[0]
        nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        opportunities = conn.execute("SELECT COUNT(*) FROM opportunities WHERE critic_verdict='survived'").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM rejected_ideas").fetchone()[0]
        
        return jsonify({
            "papers": papers,
            "patents": patents,
            "startups": startups,
            "nodes": nodes,
            "edges": edges,
            "opportunities": opportunities,
            "rejected": rejected
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/papers")
def papers():
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT id, title, source_url, year, extraction_status, problem, technology, solution FROM items WHERE type='paper' ORDER BY year DESC LIMIT 100"
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/patents")
def patents():
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT id, title, source_url, year, extraction_status, problem, technology, solution FROM items WHERE type='patent' ORDER BY year DESC LIMIT 100"
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/graph")
def graph():
    conn = get_db_connection()
    try:
        nodes = conn.execute("SELECT id, label, node_type FROM nodes").fetchall()
        edges = conn.execute("SELECT id, from_node, to_node, relationship, weight FROM edges").fetchall()
        return jsonify({
            "nodes": [dict(n) for n in nodes],
            "edges": [dict(e) for e in edges]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/opportunities")
def opportunities():
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM opportunities WHERE critic_verdict='survived' ORDER BY confidence_score DESC"
        ).fetchall()
        res = []
        for r in rows:
            d = dict(r)
            d["existing_competitors"] = json.loads(d["existing_competitors"]) if d["existing_competitors"] else []
            d["evidence"] = json.loads(d["evidence"]) if d["evidence"] else []
            d["source_papers"] = json.loads(d["source_papers"]) if d["source_papers"] else []
            d["source_patents"] = json.loads(d["source_patents"]) if d["source_patents"] else []
            d["source_startups"] = json.loads(d["source_startups"]) if d["source_startups"] else []
            res.append(d)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/rejected")
def rejected():
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT r.id, r.opportunity_id, r.reason, r.rejected_at, o.title, o.problem, o.technology, o.market
            FROM rejected_ideas r
            JOIN opportunities o ON r.opportunity_id = o.id
            ORDER BY r.rejected_at DESC
            """
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/reports")
def list_reports():
    """Returns lists of all generated Markdown reports in the reports directory."""
    import os
    reports_dir = ROOT / "reports"
    if not reports_dir.exists():
        return jsonify([])
    files = []
    for f in os.listdir(reports_dir):
        if f.endswith(".md"):
            p = reports_dir / f
            stat = p.stat()
            files.append({
                "filename": f,
                "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
                "size_bytes": stat.st_size
            })
    return jsonify(sorted(files, key=lambda x: x["created_at"], reverse=True))


@app.route("/api/reports/view/<filename>")
def view_report_content(filename):
    """Returns the markdown text content of a specific report."""
    p = ROOT / "reports" / filename
    if not p.exists() or ".." in filename:
        return jsonify({"error": "Report not found"}), 404
    return jsonify({"content": p.read_text(encoding="utf-8")})


@app.route("/api/reports/generate", methods=["POST"])
def generate_report():
    """Runs AIVE Report Engine as subprocess so it uses the active workspace DB."""
    import os, json as _json
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"aive_portfolio_{now_str}.md"
    env = dict(os.environ, AIVE_ACTIVE_WORKSPACE=ACTIVE_WORKSPACE_ID)
    proc = subprocess.run(
        [sys.executable, "scripts/run_report.py", filename],
        cwd=str(ROOT), capture_output=True, text=True, timeout=60, env=env
    )
    if proc.returncode == 0:
        try:
            result = _json.loads(proc.stdout.strip().splitlines()[-1])
        except Exception:
            result = {"report_path": filename, "status": "done"}
    else:
        result = {"error": proc.stderr[-400:], "status": "failed"}
    return jsonify(result)


@app.route("/api/workspaces", methods=["GET", "POST"])
def workspaces():
    from engines.workspace_runtime import WorkspaceRuntime
    wr = WorkspaceRuntime()
    if request.method == "POST":
        data = request.json or {}
        res = wr.run({"action": "create", "workspace_name": data.get("name", "New Workspace")})
        return jsonify(res)
    else:
        res = wr.run({"action": "list"})
        return jsonify(res.get("workspaces", []))


@app.route("/api/workspaces/<ws_id>/checkpoint", methods=["POST"])
def workspace_checkpoint(ws_id):
    from engines.workspace_runtime import WorkspaceRuntime
    wr = WorkspaceRuntime()
    res = wr.run({"action": "checkpoint", "workspace_id": ws_id, "created_by": "Dashboard"})
    return jsonify(res)


@app.route("/api/workspaces/<ws_id>/history")
def workspace_history(ws_id):
    from engines.workspace_runtime import WorkspaceRuntime
    wr = WorkspaceRuntime()
    res = wr.run({"action": "history", "workspace_id": ws_id})
    return jsonify(res.get("history", []))


@app.route("/api/workspaces/<ws_id>/restore/<version>", methods=["POST"])
def workspace_restore(ws_id, version):
    from engines.workspace_runtime import WorkspaceRuntime
    wr = WorkspaceRuntime()
    res = wr.run({"action": "restore", "workspace_id": ws_id, "version": version})
    return jsonify(res)


@app.route("/api/workspaces/active", methods=["GET", "POST"])
def active_workspace():
    global ACTIVE_WORKSPACE_ID
    if request.method == "POST":
        data = request.json or {}
        ACTIVE_WORKSPACE_ID = data.get("id", "default")
        return jsonify({"status": "success", "active_workspace_id": ACTIVE_WORKSPACE_ID})
    else:
        return jsonify({"active_workspace_id": ACTIVE_WORKSPACE_ID})


@app.route("/api/ingest/delete/<item_id>", methods=["POST", "DELETE"])
def delete_ingested_item(item_id):
    """
    Deletes an ingested paper/source from the active database.
    Wipes the item and deletes nodes/edges that have no other evidence.
    """
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM items WHERE id=?", (item_id,))
        # Also clean up nodes that only reference this item as source
        # source_items is stored as a JSON array in nodes
        rows = conn.execute("SELECT id, source_items FROM nodes").fetchall()
        for r in rows:
            try:
                srcs = json.loads(r["source_items"]) if r["source_items"] else []
                if item_id in srcs:
                    srcs.remove(item_id)
                    if not srcs:
                        conn.execute("DELETE FROM nodes WHERE id=?", (r["id"],))
                    else:
                        conn.execute("UPDATE nodes SET source_items=? WHERE id=?", (json.dumps(srcs), r["id"]))
            except Exception:
                pass
                
        # Also clean up edges referencing deleted nodes or whose evidence matches this item
        conn.execute("DELETE FROM edges WHERE from_node NOT IN (SELECT id FROM nodes) OR to_node NOT IN (SELECT id FROM nodes)")
        
        conn.commit()
        return jsonify({"status": "success", "message": f"Item {item_id} deleted."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/ingest/url", methods=["POST"])
def ingest_url():
    """
    Auto-fetches content from a URL, strips HTML to plaintext,
    and saves a new pending item to the database.
    """
    data = request.json or {}
    url = data.get("url", "").strip()
    item_type = data.get("type", "paper")
    if not url:
        return jsonify({"error": "URL is required"}), 400
    try:
        page_title, plain_text = fetch_url_text(url)
        item_id = save_item(page_title, plain_text, url, item_type)
        trigger_extraction_background()
        return jsonify({"status": "success", "item_id": item_id, "title": page_title})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ingest/manual", methods=["POST"])
def ingest_manual():
    """
    Submit a text/abstract directly (or a URL — AIVE auto-fetches if raw_text is empty).
    """
    data = request.json or {}
    title = data.get("title", "").strip()
    raw_text = data.get("raw_text", "").strip()
    source_url = data.get("source_url", "").strip()
    item_type = data.get("type", "paper")

    # If URL given but no text, auto-fetch the page
    if source_url and not raw_text:
        try:
            fetched_title, raw_text = fetch_url_text(source_url)
            if not title:
                title = fetched_title
        except Exception as e:
            return jsonify({"error": f"Failed to fetch URL: {e}"}), 400

    if not title:
        return jsonify({"error": "Title is required"}), 400
    if not raw_text:
        return jsonify({"error": "Could not extract content. Paste the abstract/text directly."}), 400

    item_id = save_item(title, raw_text, source_url or "manual", item_type)
    trigger_extraction_background()
    return jsonify({"status": "success", "item_id": item_id, "title": title})


@app.route("/api/ingest/file", methods=["POST"])
def ingest_file():
    """
    Multi-file PDF/TXT upload endpoint.
    Accepts multiple files via multipart/form-data (field name: 'files').
    Parses each file, saves as a pending item.
    """
    uploaded_files = request.files.getlist("files")
    item_type = request.form.get("type", "paper")
    saved = []
    errors = []

    for f in uploaded_files:
        filename = f.filename or "untitled"
        try:
            if filename.lower().endswith(".pdf"):
                from pypdf import PdfReader
                import io
                reader = PdfReader(io.BytesIO(f.read()))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
                title = filename.replace(".pdf", "").replace("_", " ").replace("-", " ")
            else:
                # Plain text
                text = f.read().decode("utf-8", errors="replace")
                title = filename.rsplit(".", 1)[0].replace("_", " ")

            if not text.strip():
                errors.append({"file": filename, "error": "Could not extract text"})
                continue

            item_id = save_item(title, text[:50000], f"file://{filename}", item_type)
            saved.append({"file": filename, "item_id": item_id, "title": title})
        except Exception as e:
            errors.append({"file": filename, "error": str(e)})

    if saved:
        trigger_extraction_background()

    return jsonify({"status": "success", "saved": saved, "errors": errors})


import threading

_pipeline_state = {
    "running": False,
    "stage": "idle",
    "started_at": None,
    "last_result": None,
    "last_error": None,
}
_pipeline_lock = threading.Lock()


def _run_pipeline_thread():
    """Background thread: runs the full 3-stage pipeline without blocking Flask."""
    with _pipeline_lock:
        _pipeline_state["running"] = True
        _pipeline_state["stage"] = "extraction"
        _pipeline_state["last_error"] = None
        _pipeline_state["started_at"] = datetime.now(timezone.utc).isoformat()

    try:
        import os
        env = dict(os.environ, AIVE_ACTIVE_WORKSPACE=ACTIVE_WORKSPACE_ID)
        # Stage 1: Extract knowledge from pending items
        _pipeline_state["stage"] = "extraction"
        proc1 = subprocess.run(
            [sys.executable, "-u", "agents/research_analyst.py", "10"],
            cwd=str(ROOT), timeout=600, env=env,
            capture_output=True, text=True
        )
        if proc1.returncode != 0:
            raise RuntimeError(f"research_analyst failed (exit {proc1.returncode}):\n{proc1.stderr}")

        # Stage 2: Rebuild knowledge graph
        _pipeline_state["stage"] = "graph_build"
        from utils.progress import write_progress
        write_progress("graph_build", "Connecting concepts in graph", 0, 1)
        proc2 = subprocess.run(
            [sys.executable, "agents/graph_builder.py"],
            cwd=str(ROOT), timeout=1200, env=env,
            capture_output=True, text=True
        )
        if proc2.returncode != 0:
            raise RuntimeError(f"graph_builder failed (exit {proc2.returncode}):\n{proc2.stderr}")

        # Stage 3: Opportunity discovery + novelty + critic + report
        # Run as subprocess so AIVE_ACTIVE_WORKSPACE is set BEFORE any
        # module-level DB_PATH constants are evaluated in the engine files.
        _pipeline_state["stage"] = "discovery"
        write_progress("discovery", "Critic check & scoring candidates", 0, 1)
        proc = subprocess.run(
            [sys.executable, "scripts/run_orchestrator.py", "15"],
            cwd=str(ROOT), timeout=600, env=env,
            capture_output=True, text=True
        )
        if proc.returncode == 0 and proc.stdout.strip():
            import json as _json
            summary = None
            for line in reversed(proc.stdout.strip().splitlines()):
                line_str = line.strip()
                if line_str.startswith("{") and line_str.endswith("}"):
                    try:
                        parsed = _json.loads(line_str)
                        if "discovered" in parsed:
                            summary = parsed
                            break
                    except Exception:
                        continue
            if summary:
                _pipeline_state["last_result"] = {
                    "discovered": summary.get("discovered", 0),
                    "survived":   summary.get("survived", 0),
                    "rejected":   summary.get("rejected", 0),
                }
            else:
                _pipeline_state["last_result"] = {"discovered": 0, "survived": 0, "rejected": 0}
        else:
            _pipeline_state["last_result"] = {"discovered": 0, "survived": 0, "rejected": 0}
            if proc.stderr:
                _pipeline_state["last_error"] = proc.stderr[-500:]
        _pipeline_state["stage"] = "done"
    except Exception as e:
        _pipeline_state["last_error"] = str(e)
        _pipeline_state["stage"] = "error"
    finally:
        _pipeline_state["running"] = False
        from utils.progress import clear_progress
        clear_progress()


@app.route("/api/pipeline/run", methods=["POST"])
def pipeline_run():
    """Starts the full pipeline in a background thread (non-blocking)."""
    if _pipeline_state["running"]:
        return jsonify({
            "status": "already_running",
            "stage": _pipeline_state["stage"],
            "message": "Pipeline is already running. Check /api/pipeline/status for progress."
        })
    from utils.progress import clear_progress
    clear_progress()
    t = threading.Thread(target=_run_pipeline_thread, daemon=True)
    t.start()
    return jsonify({"status": "started", "message": "Pipeline started in background. Poll /api/pipeline/status."})


@app.route("/api/pipeline/status")
def pipeline_status():
    """Returns current pipeline progress, counts, and Ollama health."""
    conn = get_db_connection()
    try:
        pending = conn.execute(
            "SELECT COUNT(*) FROM items WHERE extraction_status='pending'"
        ).fetchone()[0]
        done = conn.execute(
            "SELECT COUNT(*) FROM items WHERE extraction_status='done'"
        ).fetchone()[0]
        survived = conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE critic_verdict='survived'"
        ).fetchone()[0]
        nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM rejected_ideas").fetchone()[0]
    except Exception:
        pending = done = survived = nodes = rejected = 0
    finally:
        conn.close()

    # Read progress file
    progress_info = None
    try:
        progress_path = ROOT / "data" / "pipeline_progress.json"
        if progress_path.exists():
            progress_info = json.loads(progress_path.read_text(encoding="utf-8"))
    except Exception:
        pass

    return jsonify({
        "running": _pipeline_state["running"],
        "stage": _pipeline_state["stage"],
        "started_at": _pipeline_state["started_at"],
        "last_result": _pipeline_state["last_result"],
        "last_error": _pipeline_state["last_error"],
        "progress": progress_info,
        "db": {
            "pending_extractions": pending,
            "extracted": done,
            "survived_opportunities": survived,
            "rejected": rejected,
            "graph_nodes": nodes,
        }
    })


@app.route("/api/system/health")
def system_health():
    """
    Diagnostic endpoint. Tests Ollama connectivity, returns LLM config,
    and reports DB counts so you can verify the system is working end-to-end.
    """
    import os, urllib.request as urlreq
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    # Check Ollama
    ollama_ok = False
    ollama_models = []
    ollama_error = None
    try:
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        with urlreq.urlopen(f"{host}/api/tags", timeout=3) as r:
            tags = json.loads(r.read())
            ollama_models = [m["name"] for m in tags.get("models", [])]
            ollama_ok = True
    except Exception as e:
        ollama_error = str(e)

    # DB stats
    conn = get_db_connection()
    try:
        db_stats = {
            "items": conn.execute("SELECT COUNT(*) FROM items").fetchone()[0],
            "pending": conn.execute("SELECT COUNT(*) FROM items WHERE extraction_status='pending'").fetchone()[0],
            "extracted": conn.execute("SELECT COUNT(*) FROM items WHERE extraction_status='done'").fetchone()[0],
            "opportunities_survived": conn.execute("SELECT COUNT(*) FROM opportunities WHERE critic_verdict='survived'").fetchone()[0],
            "rejected": conn.execute("SELECT COUNT(*) FROM rejected_ideas").fetchone()[0],
            "graph_nodes": conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0],
            "graph_edges": conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0],
        }
    except Exception as e:
        db_stats = {"error": str(e)}
    finally:
        conn.close()

    provider = os.getenv("LLM_PROVIDER", "ollama")
    configured_model = os.getenv("OLLAMA_MODEL_EXTRACTOR", "qwen3:8b") if provider == "ollama" else os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_key_set = bool(os.getenv("OPENAI_API_KEY", "")) and os.getenv("OPENAI_API_KEY") != "sk-your-key-here"

    status = "healthy" if ollama_ok or (provider == "openai" and openai_key_set) else "degraded"

    return jsonify({
        "status": status,
        "llm": {
            "provider": provider,
            "model": configured_model,
            "ollama_reachable": ollama_ok,
            "ollama_models_available": ollama_models,
            "ollama_error": ollama_error,
            "openai_key_configured": openai_key_set,
        },
        "pipeline": _pipeline_state,
        "db": db_stats,
        "recommendation": (
            "System is ready." if status == "healthy"
            else "Ollama is unreachable or no LLM key set. Set OPENAI_API_KEY in .env or ensure Ollama is running."
        )
    })


@app.route("/api/ingest/arxiv", methods=["POST"])
def ingest_arxiv():
    """
    Trigger background arXiv ingestion from domain intelligence packs.
    Optionally filter to a single pack by name.
    Runs non-blocking in background.
    """
    data = request.json or {}
    pack_name = data.get("pack", None)

    cmd = [sys.executable, "ingest/pack_ingest.py"]
    if pack_name:
        cmd += ["--pack", pack_name]

    subprocess.Popen(cmd, cwd=str(ROOT),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return jsonify({
        "status": "started",
        "message": f"arXiv ingestion started for pack: {pack_name or 'ALL'}"
    })


@app.route("/api/packs")
def list_packs():
    """Returns the list of active domain intelligence packs."""
    try:
        from packs import ACTIVE_PACKS
        return jsonify([
            {"name": p.domain_name, "queries": len(p.arxiv_queries)} for p in ACTIVE_PACKS
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/copilot", methods=["POST"])
def copilot():
    """
    AIVE Copilot — answers research questions using the local knowledge graph
    as grounding context, then calls the configured LLM (Ollama or OpenAI).
    """
    data = request.json or {}
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    # Build context from live knowledge graph
    conn = get_db_connection()
    try:
        # Top survived opportunities as context
        opps = conn.execute(
            """SELECT title, problem, technology, market, timing_signal
               FROM opportunities WHERE critic_verdict='survived'
               ORDER BY confidence_score DESC LIMIT 5"""
        ).fetchall()

        # Top graph nodes for subject context
        top_nodes = conn.execute(
            """SELECT label, node_type FROM nodes
               ORDER BY ROWID DESC LIMIT 20"""
        ).fetchall()

        # Recent extractions for recency
        recent = conn.execute(
            """SELECT title, problem, technology FROM items
               WHERE extraction_status='done'
               ORDER BY extracted_at DESC LIMIT 5"""
        ).fetchall()
    finally:
        conn.close()

    opp_ctx = "\n".join(
        f"- [{o['title']}] Problem: {o['problem']} | Tech: {o['technology']}"
        for o in opps
    ) or "No survived opportunities yet."

    node_ctx = ", ".join(f"{n['label']} ({n['node_type']})" for n in top_nodes) or "Graph is empty."

    recent_ctx = "\n".join(
        f"- {r['title']}: {r['problem']}" for r in recent
    ) or "No recent extractions."

    system_prompt = (
        "You are the AIVE Research Copilot. "
        "You help researchers synthesize knowledge, discover opportunities, and understand contradictions "
        "from a live scientific knowledge graph. "
        "Answer based on the provided context from the graph. Be specific and actionable. "
        "If the graph has insufficient data, say so honestly and suggest what data to add. "
        "Do NOT make up citations or papers that are not in the context."
    )

    user_prompt = f"""
LIVE KNOWLEDGE GRAPH CONTEXT:

TOP SURVIVED OPPORTUNITIES:
{opp_ctx}

RECENT GRAPH NODES (concepts, technologies, buyers):
{node_ctx}

RECENTLY EXTRACTED PAPERS:
{recent_ctx}

USER QUESTION:
{user_message}

Answer concisely in 2-4 paragraphs. Reference the graph context where relevant.
"""

    try:
        import os
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")

        provider = os.getenv("LLM_PROVIDER", "ollama").lower()

        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key or api_key == "sk-your-key-here":
                return jsonify({"error": "OpenAI API key not configured in .env"}), 400
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4,
                max_tokens=800
            )
            reply = response.choices[0].message.content.strip()
        else:
            # Ollama
            import urllib.request as urlreq
            host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            model = os.getenv("OLLAMA_MODEL_REASONER", os.getenv("OLLAMA_MODEL_EXTRACTOR", "qwen3:8b"))
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt + " /no_think"},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {"temperature": 0.4}
            }).encode("utf-8")
            req = urlreq.Request(
                f"{host}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urlreq.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            reply = body["message"]["content"].strip()

        return jsonify({"status": "success", "reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

