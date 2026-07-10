import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "aive.db"
c = sqlite3.connect(DB)

for t in ("paper", "patent", "startup"):
    total = c.execute("SELECT COUNT(*) FROM items WHERE type=?", (t,)).fetchone()[0]
    done = c.execute(
        "SELECT COUNT(*) FROM items WHERE type=? AND extraction_status='done'", (t,)
    ).fetchone()[0]
    print(f"{t}: {done}/{total} extracted")

nodes = c.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
edges = c.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
print(f"graph: {nodes} nodes, {edges} edges")
