import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.base import call_llm
from db.init_db import DB_PATH

EXTRACTION_PROMPT = """You are compiling structured knowledge from ONE research paper.

CRITICAL: Read ONLY the paper below. Every field must describe THIS paper specifically.
Do NOT reuse text from these instructions. Do NOT invent a generic education/AI problem.

Field rules:
- problem: The specific gap or challenge THIS paper addresses. Write as a SHORT NOUN PHRASE (3-8 words). Examples: "Cold-start knowledge tracing", "Teacher grading workload", "LLM alignment with human intent". NOT a full sentence.
- solution: The method or system THIS paper proposes (1 sentence max).
- technology: The NAMED technique or system from THIS paper. Write as a SHORT NOUN PHRASE (2-6 words). Examples: "LoRA low-rank adaptation", "Deep knowledge tracing LSTM", "RLHF reward model PPO". NOT a full sentence. Use the actual name if one exists.
- keywords: 4-6 specific terms from THIS paper — method names, frameworks, datasets, metrics.
- industry: Array of 2-4 SPECIFIC market segments with real buyers. Examples: "K-12 special education", "Corporate compliance training", "University admissions testing". NOT generic terms like "Education" or "AI".
- impact: One sentence — who benefits and what changes in practice.
- beneficiaries: Array of 2-4 specific groups (e.g. "K-12 STEM teachers", "Special education administrators").
- summary: Two sentences on THIS paper's core contribution.

REJECT vague output. "AI for education" and "machine learning algorithms" are failures.

Paper title: {title}

Paper abstract:
{text}

Return JSON only:
{{
  "problem": "",
  "solution": "",
  "technology": "",
  "keywords": [],
  "industry": [],
  "impact": "",
  "beneficiaries": [],
  "summary": ""
}}
"""


def get_pending_papers(db_path: Path = DB_PATH, limit: int = 1) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, title, raw_text
            FROM items
            WHERE type = 'paper' AND extraction_status = 'pending'
            ORDER BY id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def extract_paper(paper: dict) -> dict:
    text = paper["raw_text"][:6000]
    prompt = EXTRACTION_PROMPT.format(title=paper["title"], text=text)
    return call_llm(prompt, agent="extractor")


def save_extraction(paper_id: str, data: dict, db_path: Path = DB_PATH) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE items SET
                problem = ?,
                solution = ?,
                technology = ?,
                keywords = ?,
                industry = ?,
                impact = ?,
                beneficiaries = ?,
                summary = ?,
                extracted_at = ?,
                extraction_status = 'done'
            WHERE id = ?
            """,
            (
                data.get("problem", ""),
                data.get("solution", ""),
                data.get("technology", ""),
                json.dumps(data.get("keywords", [])),
                json.dumps(data.get("industry", [])),
                data.get("impact", ""),
                json.dumps(data.get("beneficiaries", [])),
                data.get("summary", ""),
                datetime.now(timezone.utc).isoformat(),
                paper_id,
            ),
        )


def run(limit: int = 1) -> list[dict]:
    papers = get_pending_papers(limit=limit)
    results = []
    failed = 0
    for i, paper in enumerate(papers):
        print(f"[{i+1}/{len(papers)}] Extracting: {paper['title'][:70]}...")
        try:
            extracted = extract_paper(paper)
            save_extraction(paper["id"], extracted)
            results.append({"id": paper["id"], "title": paper["title"], **extracted})
            failed = 0  # reset consecutive failure count on success
        except Exception as exc:
            failed += 1
            print(f"  [ERROR] {exc}")
            # Mark as failed in DB so it doesn't block future runs
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "UPDATE items SET extraction_status='failed' WHERE id=?",
                    (paper["id"],),
                )
            # If 3 consecutive failures, Ollama is likely down — stop gracefully
            if failed >= 3:
                print(f"\n[ABORT] 3 consecutive failures — Ollama may be down.")
                print(f"Completed: {len(results)}/{len(papers)}")
                print(f"Resume with: python agents/research_analyst.py {limit - len(results)}")
                break
    return results


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    results = run(limit=limit)
    if not results:
        print("No pending papers.")
        return
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
