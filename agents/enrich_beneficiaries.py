"""Add beneficiaries field to existing extractions without full re-run."""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.base import call_llm
from db.init_db import DB_PATH

PROMPT = """Given this extracted paper knowledge, add beneficiaries.

Paper: {title}
Problem: {problem}
Technology: {technology}
Impact: {impact}

Return JSON only:
{{
  "beneficiaries": ["specific group 1", "specific group 2", "specific group 3"],
  "impact": "One sentence — who benefits and what changes (improve if vague)"
}}

Rules:
- beneficiaries must be specific (e.g. "K-12 STEM teachers", not "Education")
- 2-4 beneficiaries
"""


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 999
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, title, problem, technology, impact
            FROM items
            WHERE type='paper' AND extraction_status='done'
            AND (beneficiaries IS NULL OR beneficiaries='')
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    for row in rows:
        paper = dict(row)
        print(f"Enriching: {paper['title'][:60]}...")
        data = call_llm(
            PROMPT.format(**paper),
            agent="extractor",
        )
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                UPDATE items SET beneficiaries=?, impact=?, extracted_at=?
                WHERE id=?
                """,
                (
                    json.dumps(data.get("beneficiaries", [])),
                    data.get("impact", paper["impact"]),
                    datetime.now(timezone.utc).isoformat(),
                    paper["id"],
                ),
            )
    print(f"Enriched {len(rows)} papers.")


if __name__ == "__main__":
    main()
