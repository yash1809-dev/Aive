"""Quick diagnostic — run with: .venv/bin/python diagnose.py"""
import sqlite3, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "aive.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def q(sql):
    return conn.execute(sql).fetchone()[0]

print("=== DB STATE ===")
print("items total  :", q("SELECT COUNT(*) FROM items"))
print("items done   :", q("SELECT COUNT(*) FROM items WHERE extraction_status='done'"))
print("items pending:", q("SELECT COUNT(*) FROM items WHERE extraction_status='pending'"))
print("nodes        :", q("SELECT COUNT(*) FROM nodes"))
print("edges        :", q("SELECT COUNT(*) FROM edges"))
print("opps total   :", q("SELECT COUNT(*) FROM opportunities"))
print("opps survived:", q("SELECT COUNT(*) FROM opportunities WHERE critic_verdict='survived'"))

print("\n=== NODES ===")
for n in conn.execute("SELECT label, node_type FROM nodes").fetchall():
    print("  [{:15}] {}".format(n["node_type"], n["label"]))

print("\n=== EDGES ===")
edges = conn.execute("SELECT from_node, to_node, relationship, weight FROM edges").fetchall()
if edges:
    for e in edges:
        print("  {:20} | {} -> {}  w={}".format(e["relationship"], e["from_node"][:35], e["to_node"][:35], e["weight"]))
else:
    print("  (none)")

print("\n=== DISCOVERY ENGINE TEST ===")
sys.path.insert(0, str(ROOT))
try:
    from engines.discovery_engine import DiscoveryEngine
    de = DiscoveryEngine()
    res = de.run({"candidate_count": 3})
    print("  count:", res.get("count", 0))
    opps = res.get("opportunities", [])
    for o in opps[:3]:
        print("  opp:", o.get("title", ""))
    if res.get("error"):
        print("  ERROR:", res["error"])
except Exception as e:
    import traceback
    traceback.print_exc()

conn.close()
