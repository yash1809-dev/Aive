import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Determine active workspace
ACTIVE_WS = os.getenv("AIVE_ACTIVE_WORKSPACE", "default")
if ACTIVE_WS == "default" or not ACTIVE_WS:
    DB_PATH = ROOT / "data" / "aive.db"
else:
    DB_PATH = ROOT / "data" / f"aive_{ACTIVE_WS}.db"

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def init_db(db_path: Path = DB_PATH) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema)
    print(f"Database ready: {db_path}")
    return db_path


# Auto-initialize if it doesn't exist yet
if not DB_PATH.exists():
    init_db(DB_PATH)

