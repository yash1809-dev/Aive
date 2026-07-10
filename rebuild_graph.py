"""Rebuild the knowledge graph with the full 12-type ontology + evidence anchoring."""
import sys
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

NODES_BEFORE = 204  # baseline before ontology upgrade

from graph.knowledge_graph import build_graph

print("Rebuilding graph with 12-type ontology + evidence anchoring...")
result = build_graph(clear=True)
print(f"Done: {result['items']} items → {result['nodes']} nodes, {result['edges']} edges")

conn = sqlite3.connect("data/aive.db")
conn.row_factory = sqlite3.Row

# Concept Compression Ratio
compression = 1 - (result['nodes'] / NODES_BEFORE)
print(f"\n=== CONCEPT COMPRESSION RATIO ===")
print(f"  Before: {NODES_BEFORE} nodes")
print(f"  After:  {result['nodes']} nodes")
print(f"  Compression: {compression:.0%} reduction", end="")
if compression >= 0.4:
    print(" ✓ GOOD (>40% reduction — storing concepts not phrases)")
elif compression >= 0.2:
    print(" ~ PARTIAL (20-40% — some phrase nodes remain)")
else:
    print(" ✗ POOR (<20% — still mostly phrase nodes)")

# Node type distribution
print(f"\n=== NODE TYPES (12-type ontology) ===")
types = conn.execute("SELECT node_type, COUNT(*) as n FROM nodes GROUP BY node_type ORDER BY n DESC").fetchall()
for t in types:
    print(f"  {t['node_type']}: {t['n']}")

# Relationship type distribution
print(f"\n=== RELATIONSHIP TYPES ===")
rels = conn.execute("SELECT relationship, COUNT(*) as n FROM edges GROUP BY relationship ORDER BY n DESC").fetchall()
for r in rels:
    print(f"  --{r['relationship']}--> : {r['n']}")

# Evidence strength: nodes supported by multiple source types
print(f"\n=== EVIDENCE STRENGTH (cross-source concepts) ===")
high_conf = conn.execute("""
    SELECT label, node_type, source_items
    FROM nodes
    ORDER BY json_array_length(source_items) DESC
    LIMIT 15
""").fetchall()
for row in high_conf:
    sources = row['source_items']
    import json
    n = len(json.loads(sources))
    if n > 1:
        print(f"  [{row['node_type']}] {row['label'][:50]} — {n} sources")

# Self-referential check
self_ref = conn.execute("SELECT COUNT(*) as n FROM edges WHERE from_node = to_node").fetchone()["n"]
print(f"\n  Self-referential edges: {self_ref} (should be 0)")

# Sample edges with new relationship types
print(f"\n=== SAMPLE EDGES (new ontology) ===")
edges = conn.execute("""
    SELECT e.relationship, n1.label as src, n1.node_type as src_type,
           n2.label as dst, n2.node_type as dst_type, e.weight
    FROM edges e
    JOIN nodes n1 ON e.from_node = n1.id
    JOIN nodes n2 ON e.to_node = n2.id
    ORDER BY RANDOM() LIMIT 20
""").fetchall()
for e in edges:
    print(f"  [{e['src_type']}] {e['src'][:30]} --{e['relationship']}--> [{e['dst_type']}] {e['dst'][:30]}")

# Commercially valuable edges
print(f"\n=== COMMERCIALLY VALUABLE EDGES ===")
for rel in ["purchased_by", "regulated_by", "competes_with", "signals"]:
    count = conn.execute("SELECT COUNT(*) as n FROM edges WHERE relationship=?", (rel,)).fetchone()["n"]
    print(f"  --{rel}--> : {count} edges")

conn.close()
print(f"\nNext: python test_t14.py")
