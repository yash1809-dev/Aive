"""
T15 — Causal Chain Test
Asks the graph: "Why does this technology matter?"
A real intelligence system should produce a causal chain, not just a list.

Example chain:
  On-Device LLM Inference
    → improves  → Offline Learning
    → solves    → Student Data Privacy
    → constrained_by → FERPA
    → FERPA     → reduces Procurement Risk
    → purchased_by → K-12 School Districts

Run: python test_t15.py
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def get_causal_chain(technology_keyword: str, max_hops: int = 3) -> dict:
    """
    BFS traversal from a technology node, following meaningful edges.
    Returns a chain showing why this technology matters commercially.
    """
    conn = sqlite3.connect("data/aive.db")
    conn.row_factory = sqlite3.Row

    # Find the technology node
    start = conn.execute(
        "SELECT id, label, node_type FROM nodes WHERE lower(label) LIKE ? LIMIT 1",
        (f"%{technology_keyword.lower()}%",)
    ).fetchone()

    if not start:
        conn.close()
        return {"error": f"'{technology_keyword}' not found in graph"}

    print(f"\nStarting from: [{start['node_type']}] {start['label']}")

    visited = {start["id"]}
    chain = []
    queue = [(start["id"], start["label"], start["node_type"], 0)]

    # Priority edges for causal reasoning
    CAUSAL_PRIORITY = [
        "solves", "improves", "constrained_by", "regulated_by",
        "purchased_by", "produces", "signals", "competes_with"
    ]

    while queue:
        node_id, node_label, node_type, depth = queue.pop(0)
        if depth >= max_hops:
            continue

        edges = conn.execute("""
            SELECT e.relationship, n.id, n.label, n.node_type, e.evidence, e.weight
            FROM edges e
            JOIN nodes n ON e.to_node = n.id
            WHERE e.from_node = ?
            ORDER BY e.weight DESC
        """, (node_id,)).fetchall()

        for edge in edges:
            if edge["id"] in visited:
                continue
            visited.add(edge["id"])

            ev = json.loads(edge["evidence"] or "[]")
            ev_str = ev[0][:70] if ev else ""

            chain.append({
                "from": node_label,
                "from_type": node_type,
                "relation": edge["relationship"],
                "to": edge["label"],
                "to_type": edge["node_type"],
                "weight": edge["weight"],
                "evidence": ev_str,
                "depth": depth + 1,
            })

            # Continue BFS for causally important nodes
            if edge["node_type"] in ["Problem", "Constraint", "Regulation",
                                      "Buyer", "EconomicSignal", "Workflow"]:
                queue.append((edge["id"], edge["label"], edge["node_type"], depth + 1))

    conn.close()
    return {"start": start["label"], "chain": chain}


def run_t15(technology: str):
    print(f"\n{'='*65}")
    print(f"T15: CAUSAL CHAIN TEST — {technology}")
    print('='*65)

    result = get_causal_chain(technology, max_hops=3)

    if "error" in result:
        print(f"  ERROR: {result['error']}")
        return False

    chain = result["chain"]
    if not chain:
        print("  No causal chain found — graph has no outgoing edges for this node.")
        return False

    # Check which commercial questions are reachable
    reached_types = {step["to_type"] for step in chain}
    reached_relations = {step["relation"] for step in chain}

    print(f"\n  Chain depth reached: {max(s['depth'] for s in chain) if chain else 0} hops")
    print(f"  Total connections: {len(chain)}")
    print(f"\n  Causal path (most commercially relevant):")

    # Show the most commercially relevant path
    priority_steps = [s for s in chain if s["relation"] in
                      ["solves", "improves", "constrained_by", "regulated_by",
                       "purchased_by", "competes_with", "signals"]]

    shown = set()
    for step in sorted(priority_steps, key=lambda x: x["depth"]):
        key = (step["from"], step["to"])
        if key in shown:
            continue
        shown.add(key)
        indent = "  " * step["depth"]
        print(f"  {indent}[{step['from_type']}] {step['from'][:35]}")
        print(f"  {indent}  --{step['relation']}--> [{step['to_type']}] {step['to'][:35]}")
        if step["evidence"]:
            print(f"  {indent}  evidence: \"{step['evidence'][:60]}\"")

    # Score: how many of the 7 commercial dimensions are reachable?
    commercial_dims = {
        "Problem": "Q1 problem solved",
        "Workflow": "Q2 workflow improved",
        "User": "Q3 user benefited",
        "Buyer": "Q4 buyer identified",
        "Regulation": "Q5 regulation relevant",
        "Competitor": "Q6 competitor threatened",
        "EconomicSignal": "Q7 economic signal present",
    }

    print(f"\n  Commercial dimensions reachable:")
    score = 0
    for node_type, label in commercial_dims.items():
        found = node_type in reached_types
        print(f"    {'✓' if found else '✗'} {label} [{node_type}]")
        if found:
            score += 1

    passed = score >= 4
    print(f"\n  Score: {score}/7 dimensions reachable")
    print(f"  Result: {'PASS' if passed else 'FAIL'} (need 4/7 minimum)")
    return passed


if __name__ == "__main__":
    run_t15("On-Device LLM")
    run_t15("Knowledge Tracing")
    run_t15("LoRA")
