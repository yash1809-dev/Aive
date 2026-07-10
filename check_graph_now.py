import sqlite3, json
conn = sqlite3.connect("data/aive.db")
conn.row_factory = sqlite3.Row
total = conn.execute("SELECT COUNT(*) as n FROM nodes").fetchone()["n"]
edges = conn.execute("SELECT COUNT(*) as n FROM edges").fetchone()["n"]
print(f"Current: {total} nodes, {edges} edges")
if total > 0:
    types = conn.execute("SELECT node_type, COUNT(*) as n FROM nodes GROUP BY node_type ORDER BY n DESC").fetchall()
    for t in types:
        pct = t['n']/total*100
        print(f"  {t['node_type']}: {t['n']} ({pct:.0f}%)")
conn.close()
