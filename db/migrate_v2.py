"""
db/migrate_v2.py
================
AIVE V2 Database Migration — Cognitive Discovery OS evolution.

Adds:
  - discoveries table     (research gaps, contradictions, method transfers)
  - contradictions table  (conflicting evidence pairs)
  - items.evidence_classification  (per-field fact/inference/hypothesis/unknown)
  - items.doc_type        (auto-detected document type)
  - items.domain          (auto-detected domain)
  - opportunities.reasoning_chain  (traceable inference path JSON)

Safe to run multiple times — all operations are idempotent.
Never removes or alters existing data.
"""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NEW_ITEM_COLUMNS = [
    ("evidence_classification", "TEXT"),   # JSON: {field: fact|inference|hypothesis|unknown}
    ("doc_type",                "TEXT"),   # paper|patent|startup|report|technical_doc|news|dataset|other
    ("domain",                  "TEXT"),   # auto-detected domain string
]

NEW_OPPORTUNITY_COLUMNS = [
    ("reasoning_chain", "TEXT"),           # JSON: traceable inference path
]

DISCOVERIES_TABLE = """
CREATE TABLE IF NOT EXISTS discoveries (
    id           TEXT PRIMARY KEY,
    type         TEXT NOT NULL,
    title        TEXT,
    description  TEXT,
    evidence     TEXT,
    source_nodes TEXT,
    confidence   REAL DEFAULT 0.5,
    reasoning    TEXT,
    created_at   TEXT
);
"""

CONTRADICTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS contradictions (
    id           TEXT PRIMARY KEY,
    concept      TEXT,
    claim_a      TEXT,
    claim_b      TEXT,
    source_a     TEXT,
    source_b     TEXT,
    explanation  TEXT,
    confidence   REAL DEFAULT 0.5,
    created_at   TEXT
);
"""


def _add_column(conn: sqlite3.Connection, table: str, col: str, col_type: str) -> bool:
    """Add column if it doesn't exist. Returns True if added, False if already existed."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        return True
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            return False
        raise


def migrate(db_path: Path) -> dict:
    """Run all V2 migrations against a single database file. Returns stats."""
    if not db_path.exists():
        print(f"  Skipping (not found): {db_path}")
        return {"skipped": True}

    added_cols = 0
    added_tables = 0

    with sqlite3.connect(db_path) as conn:
        # Items columns
        for col, col_type in NEW_ITEM_COLUMNS:
            if _add_column(conn, "items", col, col_type):
                print(f"  + items.{col} ({col_type})")
                added_cols += 1
            else:
                print(f"  ~ items.{col} already exists")

        # Opportunities columns
        for col, col_type in NEW_OPPORTUNITY_COLUMNS:
            if _add_column(conn, "opportunities", col, col_type):
                print(f"  + opportunities.{col} ({col_type})")
                added_cols += 1
            else:
                print(f"  ~ opportunities.{col} already exists")

        # New tables
        conn.executescript(DISCOVERIES_TABLE)
        conn.executescript(CONTRADICTIONS_TABLE)

        # Count tables to detect if they were newly created
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "discoveries" in tables:
            print(f"  + discoveries table ready")
            added_tables += 1
        if "contradictions" in tables:
            print(f"  + contradictions table ready")
            added_tables += 1

    return {"db": str(db_path), "added_cols": added_cols, "tables": added_tables}


def run_all() -> None:
    """Migrate all databases: master + all workspace DBs."""
    data_dir = ROOT / "data"
    dbs = sorted(data_dir.glob("*.db"))

    if not dbs:
        print("No databases found in data/. Run init_db.py first.")
        return

    print(f"AIVE V2 Migration — {len(dbs)} database(s)\n")
    total_cols = 0
    for db_path in dbs:
        print(f"[{db_path.name}]")
        result = migrate(db_path)
        total_cols += result.get("added_cols", 0)
        print()

    print(f"Done. Added {total_cols} column(s) across {len(dbs)} database(s).")
    print("All existing data preserved.")


if __name__ == "__main__":
    run_all()
