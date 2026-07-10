import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.init_db import DB_PATH, init_db


def import_startups(path: Path) -> dict:
    init_db()
    items = json.loads(path.read_text(encoding="utf-8"))
    saved = 0
    with sqlite3.connect(DB_PATH) as conn:
        for item in items:
            conn.execute(
                """
                INSERT OR IGNORE INTO items
                (id, title, source, source_url, type, raw_text, year, extraction_status)
                VALUES (?, ?, ?, ?, 'startup', ?, ?, 'pending')
                """,
                (
                    item["id"],
                    item["title"],
                    item["source"],
                    item["source_url"],
                    item["raw_text"],
                    item.get("year", ""),
                ),
            )
            if conn.total_changes:
                saved += 1
    return {"total": len(items), "saved": saved}


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/raw/startups/startups_batch1.json"
    result = import_startups(path)
    print(f"Startups in file: {result['total']}")
    print(f"New in DB:        {result['saved']}")


if __name__ == "__main__":
    main()
