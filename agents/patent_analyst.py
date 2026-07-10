import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.base import call_llm
from db.init_db import DB_PATH

EXTRACTION_PROMPT = """You are compiling structured knowledge from ONE patent.

CRITICAL: Read ONLY this patent. Every field must describe THIS patent specifically.

Field rules:
- problem: The specific technical or market problem this patent solves. Write as a SHORT NOUN PHRASE (3-8 words). Examples: "Offline student knowledge tracking", "Automated IEP generation delay". NOT a full sentence.
- solution: The claimed method or system (1 sentence max).
- technology: The NAMED technical approach. Write as a SHORT NOUN PHRASE (2-6 words). Examples: "Bayesian knowledge tracing system", "Edge-deployed NLP inference", "Cached lightweight LLM". Use the actual patent claim name.
- keywords: 4-6 specific patent terms — algorithms, architectures, components.
- industry: 2-4 SPECIFIC market segments with real buyers. Examples: "K-12 school districts", "Corporate LMS vendors". NOT generic terms like "Education".
- impact: One sentence — who benefits and what changes in practice.
- beneficiaries: 2-4 specific groups who benefit.
- summary: Two sentences on core contribution.

Patent title: {title}

Patent text:
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
            WHERE type='patent' AND extraction_status='pending'
            ORDER BY id LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def save_extraction(patent_id: str, data: dict) -> None:
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
                patent_id,
            ),
        )


def run(limit: int = 1) -> list[dict]:
    patents = get_pending(limit)
    results = []
    for patent in patents:
        print(f"Extracting: {patent['title'][:70]}...")
        data = call_llm(
            EXTRACTION_PROMPT.format(title=patent["title"], text=patent["raw_text"][:6000]),
            agent="extractor",
        )
        save_extraction(patent["id"], data)
        results.append({"id": patent["id"], "title": patent["title"], **data})
    return results


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    results = run(limit=limit)
    if not results:
        print("No pending patents.")
        return
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
