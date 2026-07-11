"""Pipeline flow diagnostic"""
import sqlite3, sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "aive.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print("=== STAGE 1 CHECK: What research_analyst.py would process ===")
pending = conn.execute("SELECT id, title, type, extraction_status FROM items WHERE extraction_status='pending'").fetchall()
done = conn.execute("SELECT id, title, type FROM items WHERE extraction_status='done'").fetchall()
print(f"Pending: {len(pending)}")
print(f"Done   : {len(done)}")
for d in done:
    print(f"  [done] {d['id']} | {d['title'][:50]}")

print("\n=== STAGE 2 CHECK: What graph_builder sees ===")
nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
print(f"Nodes: {nodes}, Edges: {edges}")

print("\n=== STAGE 1 SUBPROCESS TEST ===")
proc = subprocess.run(
    [sys.executable, "-u", "agents/research_analyst.py", "3"],
    cwd=str(ROOT), capture_output=True, text=True, timeout=30
)
print("Exit code:", proc.returncode)
print("STDOUT:", proc.stdout[-500:] if proc.stdout else "(empty)")
print("STDERR:", proc.stderr[-500:] if proc.stderr else "(empty)")

print("\n=== AFTER STAGE 1: Pending vs Done ===")
conn2 = sqlite3.connect(DB)
p2 = conn2.execute("SELECT COUNT(*) FROM items WHERE extraction_status='pending'").fetchone()[0]
d2 = conn2.execute("SELECT COUNT(*) FROM items WHERE extraction_status='done'").fetchone()[0]
print(f"Pending: {p2}, Done: {d2}")
conn2.close()
conn.close()
