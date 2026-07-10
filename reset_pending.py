import sqlite3
from pathlib import Path
DB = Path("data/aive.db")
with sqlite3.connect(DB) as c:
    c.execute("UPDATE items SET extraction_status='pending' WHERE type='paper' AND extraction_status='failed'")
    c.commit()
    pending = c.execute("SELECT COUNT(*) FROM items WHERE type='paper' AND extraction_status='pending'").fetchone()[0]
    done = c.execute("SELECT COUNT(*) FROM items WHERE type='paper' AND extraction_status='done'").fetchone()[0]
print(f"Pending: {pending}")
print(f"Done:    {done}")
