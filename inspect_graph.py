import sqlite3

conn = sqlite3.connect('data/aive.db')
conn.row_factory = sqlite3.Row

print("=== NODE TYPES ===")
types = conn.execute("SELECT node_type, COUNT(*) as n FROM nodes GROUP BY node_type ORDER BY n DESC").fetchall()
for t in types:
    print(f"  {t['node_type']}: {t['n']}")

print("\n=== RELATIONSHIP TYPES ===")
rels = conn.execute("SELECT relationship, COUNT(*) as n FROM edges GROUP BY relationship ORDER BY n DESC").fetchall()
for r in rels:
    print(f"  {r['relationship']}: {r['n']}")

print("\n=== 30 RANDOM EDGES ===")
edges = conn.execute("""
    SELECT e.relationship, n1.label as src, n2.label as dst, e.weight
    FROM edges e
    JOIN nodes n1 ON e.from_node = n1.id
    JOIN nodes n2 ON e.to_node = n2.id
    ORDER BY RANDOM() LIMIT 30
""").fetchall()
for e in edges:
    print(f"  [{e['weight']:.2f}] {e['src'][:40]} --{e['relationship']}--> {e['dst'][:40]}")

print("\n=== WEIGHT DISTRIBUTION ===")
buckets = conn.execute("""
    SELECT
      CASE
        WHEN weight >= 0.9 THEN '0.9-1.0'
        WHEN weight >= 0.7 THEN '0.7-0.9'
        WHEN weight >= 0.5 THEN '0.5-0.7'
        ELSE 'below 0.5'
      END as bucket,
      COUNT(*) as n
    FROM edges
    GROUP BY bucket ORDER BY bucket DESC
""").fetchall()
for b in buckets:
    print(f"  {b['bucket']}: {b['n']} edges")

conn.close()
