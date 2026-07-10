import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "aive.db"

ITEM_MIGRATIONS = [
    "ALTER TABLE items ADD COLUMN impact TEXT",
    "ALTER TABLE items ADD COLUMN beneficiaries TEXT",
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


if __name__ == "__main__":
    migrate()
