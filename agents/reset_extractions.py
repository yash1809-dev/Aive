"""Reset paper extractions to re-run quality check."""

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.init_db import DB_PATH

limit = int(sys.argv[1]) if len(sys.argv) > 1 else 999

with sqlite3.connect(DB_PATH) as conn:
    if limit >= 999:
        conn.execute(
            """
            UPDATE items SET
                problem = NULL, solution = NULL, technology = NULL,
                keywords = NULL, industry = NULL, impact = NULL,
                summary = NULL, extracted_at = NULL,
                extraction_status = 'pending'
            WHERE type = 'paper'
            """
        )
    else:
        ids = [
            row[0]
            for row in conn.execute(
                """
                SELECT id FROM items
                WHERE type = 'paper' AND extraction_status = 'done'
                ORDER BY extracted_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        ]
        for item_id in ids:
            conn.execute(
                """
                UPDATE items SET
                    problem = NULL, solution = NULL, technology = NULL,
                    keywords = NULL, industry = NULL, impact = NULL,
                    summary = NULL, extracted_at = NULL,
                    extraction_status = 'pending'
                WHERE id = ?
                """,
                (item_id,),
            )
    print(f"Reset {conn.total_changes} papers to pending.")
