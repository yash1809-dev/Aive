import sqlite3
from pathlib import Path

c = sqlite3.connect(Path(__file__).resolve().parent.parent / "data" / "aive.db")
for v in ("pending", "survived", "rejected"):
    n = c.execute(
        f"SELECT COUNT(*) FROM opportunities WHERE critic_verdict='{v}'"
    ).fetchone()[0]
    print(f"{v}: {n}")
null_n = c.execute(
    "SELECT COUNT(*) FROM opportunities WHERE critic_verdict IS NULL"
).fetchone()[0]
print(f"null: {null_n}")
