import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "aive.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def init_db(db_path: Path = DB_PATH) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema)
    print(f"Database ready: {db_path}")
    return db_path


if __name__ == "__main__":
    init_db()
