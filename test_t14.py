"""
T14 — Commercialization Graph Test
For a given technology, answer the 6 commercialization questions using graph evidence.
Run: python test_t14.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from graph.knowledge_graph import commercialization_profile
import sqlite3

def run_t14(technology: str):
    print(f"\n{'='*65}")
    print(f"T14: COMMERCIALIZATION GRAPH TEST")
    print(f"Technology: {technology}")
    print('='*65)

    profile = commercialization_profile(technology)

    if "error" in profile:
        print(f"  ERROR: {profile['error']}")
        return False

    questions = [
        ("Q1", "What problem does it solve?",         "Q1_problems_solved"),
        ("Q2", "Which workflow does it improve?",      "Q2_workflows_improved"),
        ("Q3", "Who experiences the benefit?",         "Q3_users_benefited"),
        ("Q4", "Who writes the cheque?",               "Q4_buyers"),
        ("Q5", "Which regulation matters?",            "Q5_regulations"),
        ("Q6", "Which competitor is threatened?",      "Q6_competitors"),
    ]

    answered = 0
    for qid, question, key in questions:
        items = profile.get(key, [])
        print(f"\n  {qid}: {question}")
        if items:
            answered += 1
            for item in items[:3]:
                ev = item['evidence']
                ev_str = ev[0][:60] if ev else "no evidence stored"
                print(f"    → [{item['type']}] {item['label']}")
                print(f"       evidence: \"{ev_str}\"")
        else:
            print(f"    → NOT FOUND IN GRAPH")

    score = answered / len(questions)
    passed = score >= 0.67  # must answer at least 4/6
    print(f"\n  Score: {answered}/{len(questions)} questions answered = {score:.0%}")
    print(f"  Result: {'PASS' if passed else 'FAIL'} (need 4/6 minimum)")
    return passed


def show_graph_stats():
    conn = sqlite3.connect("data/aive.db")
    conn.row_factory = sqlite3.Row
    print("\n=== GRAPH STATS ===")
    types = conn.execute("SELECT node_type, COUNT(*) as n FROM nodes GROUP BY node_type ORDER BY n DESC").fetchall()
    for t in types:
        print(f"  {t['node_type']}: {t['n']}")
    rels = conn.execute("SELECT relationship, COUNT(*) as n FROM edges GROUP BY relationship ORDER BY n DESC").fetchall()
    print()
    for r in rels:
        print(f"  --{r['relationship']}--> : {r['n']}")
    total_nodes = conn.execute("SELECT COUNT(*) as n FROM nodes").fetchone()["n"]
    total_edges = conn.execute("SELECT COUNT(*) as n FROM edges").fetchone()["n"]
    print(f"\n  Total: {total_nodes} nodes, {total_edges} edges")
    conn.close()


if __name__ == "__main__":
    show_graph_stats()
    # Test with the surviving opportunity technology
    run_t14("On-Device LLM")
    run_t14("Knowledge Tracing")
    run_t14("LoRA")
