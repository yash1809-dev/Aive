import json
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "aive.db"
c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row
rows = c.execute(
    "SELECT title, problem, technology, keywords, industry, impact FROM items WHERE type='paper'"
).fetchall()
print(json.dumps([dict(r) for r in rows], indent=2))
