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
def _robust_json_extract(text):
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return text[start:end+1]
    return text



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


def _run_pipeline_thread(force: bool = False):
    """Background thread: runs the full 3-stage pipeline without blocking Flask."""
    with _pipeline_lock:
        _pipeline_state["running"] = True
        _pipeline_state["stage"] = "extraction"
        _pipeline_state["last_error"] = None
        _pipeline_state["started_at"] = datetime.now(timezone.utc).isoformat()

    try:
        import os
        env = dict(os.environ, AIVE_ACTIVE_WORKSPACE=ACTIVE_WORKSPACE_ID)
        from utils.progress import write_progress

        # ── Force mode: reset all items + clear concept cache ────────────────
        if force:
            _pipeline_state["stage"] = "reset"
            write_progress("reset", "Resetting all items for full re-extraction", 0, 1)
            conn = get_db_connection()
            try:
                conn.execute("UPDATE items SET extraction_status='pending'")
                conn.commit()
            finally:
                conn.close()
            # Clear concept cache so graph_builder re-extracts richer concepts
            cache_path = ROOT / "data" / "concept_cache.json"
            if cache_path.exists():
                cache_path.unlink()

        # ── Stage 1: Extract knowledge from pending items ────────────────────
        _pipeline_state["stage"] = "extraction"
        write_progress("extraction", "Extracting knowledge from sources", 0, 1)

        # Use universal_analyst for 'document' type items; research_analyst for papers
        # Run research_analyst for papers/patents/startups
        proc1 = subprocess.run(
            [sys.executable, "-u", "agents/research_analyst.py", "50"],
            cwd=str(ROOT), timeout=600, env=env,
            capture_output=True, text=True
        )
        if proc1.returncode != 0:
            raise RuntimeError(f"research_analyst failed (exit {proc1.returncode}):\n{proc1.stderr}")

        # Also run patent and startup analysts for their respective types
        for analyst, item_type in [("patent_analyst", "patent"), ("startup_analyst", "startup")]:
            proc_a = subprocess.run(
                [sys.executable, "-u", f"agents/{analyst}.py", "50"],
                cwd=str(ROOT), timeout=600, env=env,
                capture_output=True, text=True
            )
            # Non-fatal — these may have no items

        # Stage 1b: Universal analyst for non-paper/patent/startup types
        proc1b = subprocess.run(
            [sys.executable, "-u", "agents/universal_analyst.py", "50"],
            cwd=str(ROOT), timeout=600, env=env,
            capture_output=True, text=True
        )
        # Non-fatal

        # ── Stage 2: Rebuild knowledge graph ────────────────────────────────
        _pipeline_state["stage"] = "graph_build"
        write_progress("graph_build", "Extracting concepts and building knowledge graph", 0, 1)
        proc2 = subprocess.run(
            [sys.executable, "agents/graph_builder.py"],
            cwd=str(ROOT), timeout=1200, env=env,
            capture_output=True, text=True
        )
        if proc2.returncode != 0:
            raise RuntimeError(f"graph_builder failed (exit {proc2.returncode}):\n{proc2.stderr}")

        # ── Stage 3: Opportunity discovery + novelty + critic + report ───────
        _pipeline_state["stage"] = "discovery"
        write_progress("discovery", "Discovering opportunities and running critic", 0, 1)
        proc3 = subprocess.run(
            [sys.executable, "scripts/run_orchestrator.py", "10"],
            cwd=str(ROOT), timeout=900, env=env,
            capture_output=True, text=True
        )

        import json as _json
        summary = None
        if proc3.stdout.strip():
            for line in reversed(proc3.stdout.strip().splitlines()):
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

        if proc3.returncode != 0 and proc3.stderr:
            # Non-fatal — log but don't crash; partial results are still useful
            _pipeline_state["last_error"] = proc3.stderr[-600:]

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
    """
    Starts the full pipeline in a background thread (non-blocking).
    POST body: { "force": true }  — resets all items and clears cache for full re-run.
    """
    if _pipeline_state["running"]:
        return jsonify({
            "status": "already_running",
            "stage": _pipeline_state["stage"],
            "message": "Pipeline is already running. Check /api/pipeline/status for progress."
        })
    data = request.get_json(silent=True) or {}
    force = bool(data.get("force", False))

    from utils.progress import clear_progress
    clear_progress()
    t = threading.Thread(target=_run_pipeline_thread, args=(force,), daemon=True)
    t.start()
    return jsonify({
        "status": "started",
        "force": force,
        "message": "Pipeline started. Poll /api/pipeline/status for progress."
    })


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


@app.route("/api/research-paper/graph", methods=["GET"])
def research_paper_graph():
    """
    Returns a visual graph structure for manual knowledge linking.
    Includes nodes (concepts, opportunities) and edges that can be linked.
    """
    conn = get_db_connection()
    try:
        # Get high-confidence opportunities
        opps = conn.execute("""
            SELECT id, title, problem, technology, confidence_score
            FROM opportunities WHERE critic_verdict='survived' 
            ORDER BY confidence_score DESC LIMIT 20
        """).fetchall()

        # Get key graph nodes
        nodes = conn.execute("""
            SELECT id, label, node_type FROM nodes 
            WHERE node_type IN ('Technology', 'Problem', 'Market', 'Method')
            LIMIT 50
        """).fetchall()

        # Get discoveries
        discoveries = conn.execute("""
            SELECT id, type, title, confidence FROM discoveries
            ORDER BY confidence DESC LIMIT 15
        """).fetchall()

        return jsonify({
            "opportunities": [dict(o) for o in opps],
            "concepts": [dict(n) for n in nodes],
            "discoveries": [dict(d) for d in discoveries]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/research-paper/generate", methods=["POST"])
def generate_research_paper():
    """
    Generates a research paper from manually linked knowledge nodes.
    Uses evidence-grounded LLM synthesis to prevent hallucination.
    
    POST body:
    {
      "title": "Paper title",
      "linked_nodes": ["opp_id1", "node_id2", "disc_id3"],
      "structure": ["abstract", "introduction", "methods", "results", "discussion", "conclusion"]
    }
    """
    data = request.json or {}
    title = data.get("title", "Untitled Research Paper")
    linked_nodes = data.get("linked_nodes", [])
    structure = data.get("structure", ["abstract", "introduction", "methods", "results", "discussion", "conclusion"])

    if not linked_nodes:
        return jsonify({"error": "No nodes linked. Please link knowledge nodes first."}), 400

    conn = get_db_connection()
    try:
        # Gather evidence from linked nodes
        evidence = []
        
        # Get opportunities
        opp_ids = [n for n in linked_nodes if n.startswith("opp_")]
        if opp_ids:
            placeholders = ",".join(["?" for _ in opp_ids])
            opps = conn.execute(f"""
                SELECT id, title, problem, technology, solution, reasoning, evidence
                FROM opportunities WHERE id IN ({placeholders})
            """, opp_ids).fetchall()
            evidence.extend([dict(o) for o in opps])

        # Get graph nodes
        node_ids = [n for n in linked_nodes if n.startswith("node_")]
        if node_ids:
            placeholders = ",".join(["?" for _ in node_ids])
            nodes = conn.execute(f"""
                SELECT id, label, node_type, source_items FROM nodes WHERE id IN ({placeholders})
            """, node_ids).fetchall()
            evidence.extend([dict(n) for n in nodes])

        # Get discoveries
        disc_ids = [n for n in linked_nodes if n.startswith("disc_")]
        if disc_ids:
            placeholders = ",".join(["?" for _ in disc_ids])
            discs = conn.execute(f"""
                SELECT id, type, title, description, evidence FROM discoveries WHERE id IN ({placeholders})
            """, disc_ids).fetchall()
            evidence.extend([dict(d) for d in discs])

        # Get source items for citations
        all_source_ids = set()
        for e in evidence:
            if "evidence" in e and e["evidence"]:
                try:
                    ev_list = json.loads(e["evidence"]) if isinstance(e["evidence"], str) else e["evidence"]
                    all_source_ids.update(ev_list)
                except:
                    pass
            if "source_items" in e and e["source_items"]:
                try:
                    src_list = json.loads(e["source_items"]) if isinstance(e["source_items"], str) else e["source_items"]
                    all_source_ids.update(src_list)
                except:
                    pass

        citations = {}
        if all_source_ids:
            placeholders = ",".join(["?" for _ in all_source_ids])
            items = conn.execute(f"""
                SELECT id, title, source_url, year FROM items WHERE id IN ({placeholders})
            """, list(all_source_ids)).fetchall()
            citations = {item["id"]: dict(item) for item in items}

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    # Build grounded context for LLM
    evidence_context = "\n\n".join([
        f"[{e.get('id')}] {e.get('title', e.get('label', 'Untitled'))}\n"
        f"Type: {e.get('node_type', e.get('type', 'unknown'))}\n"
        f"Content: {e.get('problem', e.get('description', e.get('reasoning', '')))[:300]}"
        for e in evidence
    ])

    # Generate paper using evidence-grounded LLM
    sections = {}
    for section in structure:
        system_prompt = (
            "You are a senior research scientist writing an academic paper. "
            "Use ONLY the provided evidence context. Cite sources using [item_id] format. "
            "Never fabricate facts or citations. Write in formal academic style. "
            "If evidence is insufficient for a section, state that explicitly."
        )
        
        section_prompts = {
            "abstract": f"Write a 150-200 word abstract for a paper titled '{title}' based on this evidence:\n{evidence_context[:2000]}",
            "introduction": f"Write an introduction section for '{title}' that establishes context and motivation. Evidence:\n{evidence_context[:3000]}",
            "methods": f"Write a methods/approach section describing the technical approach for '{title}'. Evidence:\n{evidence_context[:3000]}",
            "results": f"Write a results section presenting the key findings for '{title}'. Evidence:\n{evidence_context[:3000]}",
            "discussion": f"Write a discussion section analyzing implications and limitations for '{title}'. Evidence:\n{evidence_context[:3000]}",
            "conclusion": f"Write a conclusion section summarizing contributions for '{title}'. Evidence:\n{evidence_context[:2000]}"
        }
        
        user_prompt = section_prompts.get(section, f"Write the {section} section for '{title}'. Evidence:\n{evidence_context[:3000]}")
        
        try:
            section_text = _call_llm_internal(system_prompt, user_prompt)
            sections[section] = section_text
        except Exception as e:
            sections[section] = f"[Error generating {section}: {str(e)}]"

    # Assemble paper
    paper_md = f"# {title}\n\n"
    paper_md += f"*Generated by AIVE Research Paper Builder on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}*\n\n"
    paper_md += "---\n\n"
    
    for section in structure:
        paper_md += f"## {section.title()}\n\n"
        paper_md += sections.get(section, "[Section not generated]") + "\n\n"
    
    # Add references
    if citations:
        paper_md += "## References\n\n"
        for idx, (item_id, cite) in enumerate(citations.items(), 1):
            paper_md += f"{idx}. [{item_id}] {cite.get('title', 'Untitled')} ({cite.get('year', 'n.d.')}). "
            if cite.get('source_url'):
                paper_md += f"{cite['source_url']}"
            paper_md += "\n"

    # Save to reports directory
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    filename = f"research_paper_{slugify(title[:40])}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
    filepath = reports_dir / filename
    filepath.write_text(paper_md, encoding="utf-8")

    return jsonify({
        "status": "success",
        "filename": filename,
        "filepath": str(filepath),
        "paper_preview": paper_md[:500] + "...",
        "linked_nodes_count": len(linked_nodes),
        "evidence_count": len(evidence),
        "citations_count": len(citations)
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


def _call_llm_internal(system_prompt, user_prompt):
    import os
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
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
        return response.choices[0].message.content.strip()
    else:
        import urllib.request as urlreq
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL_REASONER", os.getenv("OLLAMA_MODEL_EXTRACTOR", "llama3:8b"))
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
        return body["message"]["content"].strip()


@app.route("/api/copilot", methods=["POST"])
def copilot():
    """
    AIVE Copilot — answers research questions using the local knowledge graph
    as grounding context. If the user describes a new opportunity concept,
    it automatically formulates, critiques, validates, and stores it in the active workspace database.
    """
    data = request.json or {}
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    conn = get_db_connection()
    try:
        # Check if user message proposes a new opportunity/concept
        detection_system = "You are a classification assistant. Reply only 'YES' or 'NO'."
        detection_user = f"Does the following message propose, outline, or describe a new business, scientific, or commercial opportunity, idea, or startup concept? Reply YES or NO only.\n\nMessage: {user_message}"
        
        is_opp = False
        try:
            reply = _call_llm_internal(detection_system, detection_user)
            if "YES" in reply.upper():
                is_opp = True
        except Exception:
            pass

        if is_opp:
            # Step 1: Formulate opportunity from user message
            formulate_system = "You are AIVE Opportunity Formulator. Extract opportunity details. Return valid JSON only."
            formulate_user = f"Formulate this concept into a structured opportunity:\n{user_message}\n\nReturn JSON in this exact format:\n{{\n  \"title\": \"opportunity title (5-8 words)\",\n  \"problem\": \"specific problem solved\",\n  \"technology\": \"specific technology used\",\n  \"market\": \"market segment and buyer\",\n  \"timing_signal\": \"timing signal/why now\",\n  \"reasoning\": \"reasons connecting technology and problem\",\n  \"novelty_score\": 5,\n  \"timing_score\": 5,\n  \"market_score\": 5,\n  \"feasibility\": 5\n}}"
            
            opp_data = {}
            try:
                form_reply = _call_llm_internal(formulate_system, formulate_user)
                form_reply_clean = _robust_json_extract(form_reply)
                opp_data = json.loads(form_reply_clean)
            except Exception as e:
                return jsonify({"status": "success", "reply": f"I detected you proposed a new opportunity, but I had trouble formulating it: {e}\n\nRaw output: {form_reply[:200]}"})

            # Step 2: Critique opportunity
            critic_system = "You are AIVE Critic. Evaluate this opportunity. Return valid JSON only."
            critic_user = f"Evaluate this opportunity concept:\n{json.dumps(opp_data, indent=2)}\n\nAnswer all categories. Target 70%+ rejection. Return JSON in this exact format:\n{{\n  \"verdict\": \"survived\" or \"rejected\",\n  \"summary\": \"one sentence reason for survival or rejection\",\n  \"kill_reasons\": []\n}}"
            
            critic_verdict = "rejected"
            critic_summary = "Failed critic review."
            try:
                crit_reply = _call_llm_internal(critic_system, critic_user)
                crit_reply_clean = _robust_json_extract(crit_reply)
                crit_parsed = json.loads(crit_reply_clean)
                critic_verdict = crit_parsed.get("verdict", "rejected")
                critic_summary = crit_parsed.get("summary", "Rejected by critic.")
            except Exception:
                pass

            # Step 3: Insert Opportunity + run validation
            opp_id = f"opp_usr_{uuid.uuid4().hex[:8]}"
            now = datetime.now(timezone.utc).isoformat()
            
            conn.execute(
                """INSERT INTO opportunities (
                    id, title, problem, technology, market, timing_signal, reasoning,
                    novelty_score, timing_score, market_score, feasibility, edge_confidence,
                    source_papers, source_patents, source_startups, critic_verdict, critic_notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.8, '[]', '[]', '[]', ?, ?, ?)""",
                (
                    opp_id, opp_data.get("title", "User Concept"), opp_data.get("problem", ""),
                    opp_data.get("technology", ""), opp_data.get("market", ""),
                    opp_data.get("timing_signal", ""), opp_data.get("reasoning", ""),
                    opp_data.get("novelty_score", 5), opp_data.get("timing_score", 5),
                    opp_data.get("market_score", 5), opp_data.get("feasibility", 5),
                    critic_verdict, json.dumps({"summary": critic_summary}), now
                )
            )

            if critic_verdict == "rejected":
                conn.execute(
                    "INSERT INTO rejected_ideas (id, opportunity_id, reason, rejected_at) VALUES (?, ?, ?, ?)",
                    (f"rej_{uuid.uuid4().hex[:8]}", opp_id, critic_summary, now)
                )

            # Recalculate validation score
            from engines.validation_engine import ValidationEngine
            # Pass connection directly using a custom validation method or instantiating with db_path
            from db.init_db import DB_PATH
            ve = ValidationEngine(db_path=DB_PATH)
            metrics = ve.calculate_metrics({
                "id": opp_id,
                "novelty_score": opp_data.get("novelty_score", 5),
                "timing_score": opp_data.get("timing_score", 5),
                "market_score": opp_data.get("market_score", 5),
                "feasibility": opp_data.get("feasibility", 5),
                "edge_confidence": 0.8,
                "critic_verdict": critic_verdict
            })
            
            conn.execute(
                "UPDATE opportunities SET confidence_score = ? WHERE id = ?",
                (metrics["confidence_score"], opp_id)
            )
            conn.commit()

            # Auto-generate updated report including the new opportunity/rejected idea
            import os as _os
            _report_env = dict(_os.environ, AIVE_ACTIVE_WORKSPACE=ACTIVE_WORKSPACE_ID)
            _now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            _report_file = f"aive_portfolio_{_now_str}.md"
            try:
                subprocess.Popen(
                    [sys.executable, "scripts/run_report.py", _report_file],
                    cwd=str(ROOT), env=_report_env,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                report_note = f"\n- **Report:** Saved as `{_report_file}` in Reports section."
            except Exception:
                report_note = ""

            status_text = "🎉 **Survived Critic Check!**" if critic_verdict == "survived" else "❌ **Rejected by Critic.**"
            reply_text = (
                f"{status_text}\n\n"
                f"I processed your concept **\"{opp_data.get('title')}\"** and added it to the workspace.\n\n"
                f"- **Verdict:** {critic_verdict.capitalize()}\n"
                f"- **Critic Summary:** {critic_summary}\n"
                f"- **Confidence Score:** {metrics['confidence_score']}/10 ({metrics['validation_status']})"
                f"{report_note}\n\n"
                f"It is now visible in the **{ 'Opportunities' if critic_verdict == 'survived' else 'Rejected Ideas' }** section on the Canvas."
            )
            return jsonify({"status": "success", "reply": reply_text})

        # Regular Chat Mode — route through QA Engine for grounded responses
        try:
            from engines.qa_engine import QAEngine
            from db.init_db import DB_PATH as _DB_PATH
            qa = QAEngine(db_path=_DB_PATH)
            qa_result = qa.answer(user_message)
            
            # Enhanced: Check if user is asking about research paper generation
            paper_keywords = ["research paper", "paper", "publish", "write paper", "generate paper", "create paper"]
            if any(kw in user_message.lower() for kw in paper_keywords):
                # Suggest using the research paper builder
                paper_suggestion = (
                    "\n\n💡 **Research Paper Builder Available**: "
                    "You can use the Research Paper Builder tab to visually link knowledge nodes "
                    "and generate evidence-grounded research papers. Navigate to the 'Paper Builder' tab to get started."
                )
                qa_result["reply"] = qa_result.get("reply", "") + paper_suggestion
            
            return jsonify({
                "status": "success",
                "reply": qa_result.get("reply", ""),
                "evidence_refs": qa_result.get("evidence_refs", []),
                "confidence": qa_result.get("confidence", "Unknown"),
                "question_type": qa_result.get("question_type", "factual"),
            })
        except Exception as qa_err:
            pass  # fallback to legacy context-based response below

        # Fallback: Enhanced legacy context-based response with deep document knowledge
        opps = conn.execute(
            """SELECT title, problem, technology, market, timing_signal
               FROM opportunities WHERE critic_verdict='survived'
               ORDER BY confidence_score DESC LIMIT 5"""
        ).fetchall()

        top_nodes = conn.execute(
            """SELECT label, node_type FROM nodes
               ORDER BY ROWID DESC LIMIT 20"""
        ).fetchall()

        # Enhanced: Include full document summaries for intensive knowledge
        recent = conn.execute(
            """SELECT id, title, problem, technology, solution, summary, domain, doc_type
               FROM items
               WHERE extraction_status='done'
               ORDER BY extracted_at DESC LIMIT 8"""
        ).fetchall()

        # Enhanced: Include discoveries and contradictions
        discoveries = conn.execute(
            """SELECT type, title, description FROM discoveries 
               ORDER BY confidence DESC LIMIT 5"""
        ).fetchall()

        contradictions = conn.execute(
            """SELECT concept, claim_a, claim_b FROM contradictions
               ORDER BY confidence DESC LIMIT 3"""
        ).fetchall()

        opp_ctx = "\n".join(
            f"- [{o['title']}] Problem: {o['problem']} | Tech: {o['technology']}"
            for o in opps
        ) or "No survived opportunities yet."

        node_ctx = ", ".join(f"{n['label']} ({n['node_type']})" for n in top_nodes) or "Graph is empty."

        # Enhanced document context with full details
        recent_ctx = "\n".join(
            f"- [{r['id']}] {r['title']}\n"
            f"  Domain: {r.get('domain', 'N/A')} | Type: {r.get('doc_type', 'N/A')}\n"
            f"  Problem: {r.get('problem', 'N/A')}\n"
            f"  Technology: {r.get('technology', 'N/A')}\n"
            f"  Solution: {r.get('solution', 'N/A')[:150]}\n"
            f"  Summary: {r.get('summary', 'N/A')[:200]}"
            for r in recent
        ) or "No recent extractions."

        disc_ctx = "\n".join(
            f"- {d['type']}: {d['title']} - {d.get('description', '')[:150]}"
            for d in discoveries
        ) or "No discoveries yet."

        contra_ctx = "\n".join(
            f"- {c['concept']}: Claim A: {c['claim_a'][:100]} vs Claim B: {c['claim_b'][:100]}"
            for c in contradictions
        ) or "No contradictions detected."

        system_prompt = (
            "You are the AIVE Research Copilot with INTENSIVE knowledge of all submitted documents. "
            "You help researchers synthesize knowledge, discover opportunities, understand contradictions, "
            "and suggest new research directions from a live scientific knowledge graph. "
            "Answer based on the provided context from the graph. Be specific and actionable. "
            "Reference specific document IDs [id] when citing evidence. "
            "If the graph has insufficient data, say so honestly and suggest what data to add. "
            "When users ask about research papers, suggest using the Research Paper Builder. "
            "Do NOT make up citations or papers that are not in the context."
        )

        user_prompt = f"""
LIVE KNOWLEDGE GRAPH CONTEXT:

TOP SURVIVED OPPORTUNITIES:
{opp_ctx}

RECENT GRAPH NODES (concepts, technologies, buyers):
{node_ctx}

RECENTLY EXTRACTED DOCUMENTS (Full Details):
{recent_ctx}

RESEARCH DISCOVERIES:
{disc_ctx}

DETECTED CONTRADICTIONS:
{contra_ctx}

USER QUESTION:
{user_message}

Answer concisely in 2-4 paragraphs. Reference the graph context and document IDs where relevant.
If asked about research papers, mention the Research Paper Builder feature.
"""
        reply = _call_llm_internal(system_prompt, user_prompt)
        return jsonify({"status": "success", "reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# ── TASK 4: Discovery endpoints ───────────────────────────────────────────────

@app.route("/api/discoveries")
def discoveries():
    """Returns all classified discoveries. Optional ?type= filter."""
    disc_type = request.args.get("type", None)
    conn = get_db_connection()
    try:
        if disc_type:
            rows = conn.execute(
                "SELECT * FROM discoveries WHERE type=? ORDER BY confidence DESC",
                (disc_type,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM discoveries ORDER BY confidence DESC"
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["evidence"] = json.loads(d["evidence"]) if d["evidence"] else []
            d["source_nodes"] = json.loads(d["source_nodes"]) if d["source_nodes"] else []
            result.append(d)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/contradictions")
def contradictions():
    """Returns all detected contradictions."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM contradictions ORDER BY confidence DESC"
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/research-gaps")
def research_gaps():
    """Returns discoveries of type research_gap."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM discoveries WHERE type='research_gap' ORDER BY confidence DESC"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["evidence"] = json.loads(d["evidence"]) if d["evidence"] else []
            d["source_nodes"] = json.loads(d["source_nodes"]) if d["source_nodes"] else []
            result.append(d)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# ── TASK 5: Deep report endpoint ──────────────────────────────────────────────

@app.route("/api/reports/generate-deep", methods=["POST"])
def generate_deep_report():
    """Generate a research-grade 15-section report using ReportBuilder."""
    import os
    try:
        from agents.report_builder import ReportBuilder
        from db.init_db import DB_PATH as _DB_PATH
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"aive_deep_{now_str}.md"
        output_path = ROOT / "reports" / filename
        builder = ReportBuilder(db_path=_DB_PATH)
        saved_path = builder.build(output_path=output_path)
        return jsonify({
            "status": "success",
            "report_path": filename,
            "message": f"Deep report saved as {filename}",
        })
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500


# ── TASK 7: Visualization API endpoints ───────────────────────────────────────

@app.route("/api/visualizations/funnel")
def viz_funnel():
    """Pipeline stage counts for funnel chart."""
    conn = get_db_connection()
    try:
        ingested = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        extracted = conn.execute(
            "SELECT COUNT(*) FROM items WHERE extraction_status='done'"
        ).fetchone()[0]
        graph_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        candidates = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
        survived = conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE critic_verdict='survived'"
        ).fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM rejected_ideas").fetchone()[0]
        return jsonify({
            "stages": [
                {"label": "Ingested", "count": ingested},
                {"label": "Extracted", "count": extracted},
                {"label": "Graph Nodes", "count": graph_nodes},
                {"label": "Candidates", "count": candidates},
                {"label": "Survived", "count": survived},
                {"label": "Rejected", "count": rejected},
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/visualizations/scores")
def viz_scores():
    """Per-opportunity score arrays for radar chart."""
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT id, title, novelty_score, timing_score, market_score,
                   feasibility, confidence_score
            FROM opportunities WHERE critic_verdict='survived'
            ORDER BY confidence_score DESC LIMIT 10
        """).fetchall()
        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "title": (r["title"] or "")[:40],
                "scores": {
                    "novelty":     r["novelty_score"] or 0,
                    "timing":      r["timing_score"] or 0,
                    "market":      r["market_score"] or 0,
                    "feasibility": r["feasibility"] or 0,
                    "confidence":  r["confidence_score"] or 0,
                }
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/visualizations/timeline")
def viz_timeline():
    """Ingestion counts grouped by date."""
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT DATE(extracted_at) AS date, COUNT(*) AS count
            FROM items
            WHERE extracted_at IS NOT NULL
            GROUP BY DATE(extracted_at)
            ORDER BY date ASC
            LIMIT 60
        """).fetchall()
        return jsonify([{"date": r["date"], "count": r["count"]} for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/visualizations/distribution")
def viz_distribution():
    """Node type counts for distribution chart."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT node_type, COUNT(*) AS count FROM nodes GROUP BY node_type ORDER BY count DESC"
        ).fetchall()
        return jsonify([{"type": r["node_type"], "count": r["count"]} for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# ── TASK 6: Enhanced Copilot with QA Engine ───────────────────────────────────
# (original copilot route is preserved; this adds QA engine routing to it)

@app.route("/api/understand", methods=["POST"])
def understand():
    """
    Universal document understanding endpoint.
    Accepts text, URL, or file content with optional type hint.
    Uses UniversalAnalyst to detect doc_type, domain, and extract structured knowledge.
    """
    data = request.json or {}
    raw_text = data.get("text", "").strip()
    source_url = data.get("url", "").strip()
    type_hint = data.get("type_hint", None)  # optional: paper, patent, startup, etc.
    
    # If URL provided, fetch content
    if source_url and not raw_text:
        try:
            page_title, raw_text = fetch_url_text(source_url)
        except Exception as e:
            return jsonify({"error": f"Failed to fetch URL: {e}"}), 400
    
    if not raw_text:
        return jsonify({"error": "No content provided. Supply 'text' or 'url'."}), 400
    
    # Call UniversalAnalyst
    try:
        from agents.universal_analyst import UniversalAnalyst
        analyst = UniversalAnalyst()
        
        metadata = {}
        if source_url:
            metadata["source_url"] = source_url
        if type_hint:
            metadata["type_hint"] = type_hint
        
        result = analyst.classify(raw_text, metadata)
        
        return jsonify({
            "status": "success",
            "doc_type": result.get("doc_type", "unknown"),
            "domain": result.get("domain", "unknown"),
            "extracted": result.get("extracted", {}),
            "evidence_classification": result.get("evidence_classification", {}),
            "metadata": result.get("metadata", {})
        })
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

