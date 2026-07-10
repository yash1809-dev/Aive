import sqlite3
from pathlib import Path

# Project root is the parent of the validation/ directory
ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / "data" / "validation.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "validation_schema.sql"


def init_db(db_path: Path = None) -> Path:
    """Create data/validation.db and apply the schema if tables don't exist yet.

    The function is idempotent: every CREATE statement uses IF NOT EXISTS, so
    running it against an already-initialised database is a no-op.

    Args:
        db_path: Override the default database location.  When omitted the
                 database is created at <project_root>/data/validation.db.

    Returns:
        The resolved Path of the database file.
    """
    if db_path is None:
        db_path = DB_PATH
    else:
        db_path = Path(db_path)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema)

    print(f"Validation database ready: {db_path}")
    return db_path


if __name__ == "__main__":
    init_db()
