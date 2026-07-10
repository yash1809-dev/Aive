"""
Reset all extractions, re-run all three agents with improved prompts, rebuild graph.
Run: python reextract_and_rebuild.py
"""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

DB = ROOT / "data" / "aive.db"

# Step 1: Reset extraction status
print("Step 1: Resetting extraction status for all items...")
conn = sqlite3.connect(DB)
conn.execute("""
    UPDATE items SET
        extraction_status='pending',
        problem=NULL, solution=NULL, technology=NULL,
        keywords=NULL, industry=NULL, impact=NULL,
        beneficiaries=NULL, summary=NULL, extracted_at=NULL
""")
conn.commit()
counts = conn.execute("SELECT type, COUNT(*) as n FROM items GROUP BY type").fetchall()
conn.close()
for row in counts:
    print(f"  {row[0]}: {row[1]} items reset to pending")

# Step 2: Re-extract papers
print("\nStep 2: Re-extracting papers...")
from agents.research_analyst import run as run_papers
results = run_papers(limit=20)
print(f"  Extracted {len(results)} papers")

# Step 3: Re-extract patents
print("\nStep 3: Re-extracting patents...")
from agents.patent_analyst import run as run_patents
results = run_patents(limit=20)
print(f"  Extracted {len(results)} patents")

# Step 4: Re-extract startups
print("\nStep 4: Re-extracting startups...")
from agents.startup_analyst import run as run_startups
results = run_startups(limit=20)
print(f"  Extracted {len(results)} startups")

# Step 5: Rebuild graph
print("\nStep 5: Rebuilding knowledge graph...")
from graph.knowledge_graph import build_graph
result = build_graph(clear=True)
print(f"  Graph: {result['nodes']} nodes, {result['edges']} edges")

# Step 6: Show sample nodes
print("\nStep 6: Sample nodes after re-extraction:")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print("\n  PROBLEM nodes (first 15):")
for row in conn.execute("SELECT label FROM nodes WHERE node_type='problem' ORDER BY label LIMIT 15").fetchall():
    print(f"    {row['label']}")

print("\n  TECHNOLOGY nodes (first 15):")
for row in conn.execute("SELECT label FROM nodes WHERE node_type='technology' ORDER BY label LIMIT 15").fetchall():
    print(f"    {row['label']}")

print("\n  MARKET nodes (first 15):")
for row in conn.execute("SELECT label FROM nodes WHERE node_type='market' ORDER BY label LIMIT 15").fetchall():
    print(f"    {row['label']}")

self_ref = conn.execute("SELECT COUNT(*) as n FROM edges WHERE from_node = to_node").fetchone()["n"]
print(f"\n  Self-referential edges: {self_ref} (should be 0)")

conn.close()
print("\nDone. Run python test_live.py to re-run T1/T3/T7 tests.")
