import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "aive.db"

ITEM_MIGRATIONS = [
    "ALTER TABLE items ADD COLUMN impact TEXT",
    "ALTER TABLE items ADD COLUMN beneficiaries TEXT",
    "ALTER TABLE items ADD COLUMN ko_type TEXT DEFAULT 'document'",
    "ALTER TABLE items ADD COLUMN confidence REAL DEFAULT 0.5",
    "ALTER TABLE items ADD COLUMN version INTEGER DEFAULT 1",
    "ALTER TABLE items ADD COLUMN provenance TEXT",
    "ALTER TABLE items ADD COLUMN validation_state TEXT DEFAULT 'unvalidated'",
    "ALTER TABLE items ADD COLUMN reasoning_refs TEXT",
    "ALTER TABLE items ADD COLUMN discovery_refs TEXT",
]

OPPORTUNITY_COLUMNS = [
    ("problem", "TEXT"),
    ("technology", "TEXT"),
    ("market", "TEXT"),
    ("timing_signal", "TEXT"),
    ("evidence", "TEXT"),
    ("existing_competitors", "TEXT"),
    ("novelty_score", "INTEGER"),
    ("timing_score", "INTEGER"),
    ("confidence_score", "INTEGER"),
    ("edge_confidence", "REAL"),
]

FEEDBACK_TABLE = """
CREATE TABLE IF NOT EXISTS opportunity_feedback (
    id             TEXT PRIMARY KEY,
    opportunity_id TEXT REFERENCES opportunities(id),
    human_rating   INTEGER,
    novel          INTEGER,
    feasible       INTEGER,
    valuable       INTEGER,
    surprising     INTEGER,
    would_build    INTEGER DEFAULT 0,
    notes          TEXT,
    created_at     TEXT
);
"""


def migrate(db_path: Path = DB_PATH) -> None:
    with sqlite3.connect(db_path) as conn:
        for sql in ITEM_MIGRATIONS:
            try:
                conn.execute(sql)
                print(f"Applied: {sql}")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    print(f"Skipped (exists): {sql}")
                else:
                    raise

        for col, typ in OPPORTUNITY_COLUMNS:
            try:
                conn.execute(f"ALTER TABLE opportunities ADD COLUMN {col} {typ}")
                print(f"Applied: opportunities.{col}")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    print(f"Skipped (exists): opportunities.{col}")
                else:
                    raise

        conn.executescript(FEEDBACK_TABLE)
        print("Applied: opportunity_feedback table")

        # Workspace Tables
        WORKSPACE_TABLES = """
        CREATE TABLE IF NOT EXISTS workspaces (
            id             TEXT PRIMARY KEY,
            name           TEXT NOT NULL,
            status         TEXT DEFAULT 'active',
            created_at     TEXT NOT NULL,
            updated_at     TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS workspace_history (
            id             TEXT PRIMARY KEY,
            workspace_id   TEXT REFERENCES workspaces(id),
            version        INTEGER NOT NULL,
            snapshot_data  TEXT,
            created_at     TEXT NOT NULL,
            created_by     TEXT NOT NULL
        );
        """
        conn.executescript(WORKSPACE_TABLES)
        print("Applied: workspaces & workspace_history tables")


if __name__ == "__main__":
    migrate()
