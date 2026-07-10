import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.base import call_llm
from db.init_db import DB_PATH

EXTRACTION_PROMPT = """You are compiling structured knowledge from ONE startup description.

CRITICAL: Read ONLY this startup. Every field must describe THIS company specifically.

Field rules:
- problem: The specific market or user problem this startup addresses. Write as a SHORT NOUN PHRASE (3-8 words). Examples: "Teacher grading time waste", "Student engagement dropout risk". NOT a full sentence.
- solution: What product or service they offer (1 sentence max).
- technology: Their NAMED core technical approach. Write as a SHORT NOUN PHRASE (2-6 words). Examples: "AI essay grading rubric", "Adaptive quiz engine", "Offline LLM tutor". NOT "machine learning algorithms".
- keywords: 4-6 specific terms — product features, tech stack, market positioning.
- industry: 2-4 SPECIFIC market segments with real buyers. Examples: "K-12 school districts", "EdTech SaaS buyers". NOT generic terms like "Education" or "Students".
- impact: One sentence — who benefits and what changes in practice.
- beneficiaries: 2-4 specific groups who benefit.
- summary: Two sentences on what makes this startup notable.

Startup name: {title}

Startup description:
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


def get_pending(limit: int = 1) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, title, raw_text FROM items
            WHERE type='startup' AND extraction_status='pending'
            ORDER BY id LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def save_extraction(startup_id: str, data: dict) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE items SET
                problem=?, solution=?, technology=?, keywords=?, industry=?,
                impact=?, beneficiaries=?, summary=?, extracted_at=?,
                extraction_status='done'
            WHERE id=?
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
                startup_id,
            ),
        )


def run(limit: int = 1) -> list[dict]:
    startups = get_pending(limit)
    results = []
    for s in startups:
        print(f"Extracting: {s['title'][:70]}...")
        data = call_llm(
            EXTRACTION_PROMPT.format(title=s["title"], text=s["raw_text"][:6000]),
            agent="extractor",
        )
        save_extraction(s["id"], data)
        results.append({"id": s["id"], "title": s["title"], **data})
    return results


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    results = run(limit=limit)
    if not results:
        print("No pending startups.")
        return
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
