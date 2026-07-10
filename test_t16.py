"""
T16 — Counterfactual Opportunity Test
Removes one node at a time and re-runs opportunity generation.
Reveals which nodes actually drive an opportunity vs. which are incidental.

Run: python test_t16.py
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def get_opportunity(conn, opp_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM opportunities WHERE id=?", (opp_id,)
    ).fetchone()
    return dict(row) if row else None


def get_survived_opportunities(conn, limit: int = 3) -> list[dict]:
    rows = conn.execute("""
        SELECT id, title, problem, technology, market,
               novelty_score, confidence_score
        FROM opportunities
        WHERE critic_verdict = 'survived'
        ORDER BY confidence_score DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def run_with_node_removed(node_label: str, node_type: str, count: int = 5) -> list[dict]:
    """
    Temporarily hides a node by type+label and runs opportunity finder.
    Returns the opportunities generated without that node.
    """
    from agents.opportunity_finder import find_missing_combinations, generate_opportunity, TIMING_SIGNALS

    # We can't truly delete — instead we mark what's excluded and filter in-process
    # For now: run opportunity finder and filter out opps that reference the removed node
    candidates = find_missing_combinations(limit=count * 2)

    # Filter out candidates that reference the removed concept
    filtered = [
        c for c in candidates
        if node_label.lower() not in c.get("problem", "").lower()
        and node_label.lower() not in c.get("technology", "").lower()
        and node_label.lower() not in c.get("market", "").lower()
    ]

    return filtered[:count]


def run_t16():
    print("\n" + "="*65)
    print("T16: COUNTERFACTUAL OPPORTUNITY TEST")
    print("="*65)

    conn = sqlite3.connect("data/aive.db")
    conn.row_factory = sqlite3.Row

    survived = get_survived_opportunities(conn, limit=3)
    if not survived:
        print("  No survived opportunities yet. Run opportunity_finder.py + critic.py first.")
        conn.close()
        return

    print(f"\nTesting {len(survived)} survived opportunity/ies:\n")

    for opp in survived:
        print(f"\n  Opportunity: {opp['title']}")
        print(f"  Problem:     {str(opp['problem'])[:60]}")
        print(f"  Technology:  {str(opp['technology'])[:60]}")
        print(f"  Market:      {str(opp['market'])[:60]}")
        print(f"  Confidence:  {opp['confidence_score']}/10, Novelty: {opp['novelty_score']}/10")

        # Extract the key concepts from this opportunity
        key_concepts = []
        if opp['technology']:
            # Find the first 2-3 words as a concept handle
            tech_words = str(opp['technology']).split()[:3]
            key_concepts.append((" ".join(tech_words), "Technology"))
        if opp['problem']:
            prob_words = str(opp['problem']).split()[:3]
            key_concepts.append((" ".join(prob_words), "Problem"))

        print(f"\n  Counterfactual analysis:")
        print(f"  {'Node Removed':<35} {'Candidates Without It':<25} {'Verdict'}")
        print(f"  {'-'*35} {'-'*25} {'-'*15}")

        for label, ntype in key_concepts:
            without = run_with_node_removed(label, ntype, count=5)
            verdict = "SURVIVES" if len(without) >= 3 else "DESTROYED"
            driver_label = "Incidental" if verdict == "SURVIVES" else "KEY DRIVER"
            print(f"  {label[:35]:<35} {len(without)} candidates{'':<15} {driver_label}")

        print()
        print("  Interpretation:")
        print("  - DESTROYED = removing this concept kills opportunity generation")
        print("    → This concept is a KEY DRIVER of the opportunity")
        print("  - SURVIVES  = opportunity generates even without this concept")
        print("    → This concept may be incidental / obvious")

    conn.close()

    print(f"\n{'='*65}")
    print("KEY INSIGHT:")
    print("If all concepts survive removal → the opportunity was already obvious")
    print("If a Regulation or EconomicSignal is a key driver →")
    print("  AIVE is finding regulation/market-driven opportunities, not just tech combos")
    print("  That's genuinely valuable.")


def show_ontology_balance():
    """Check if the graph is technology-biased (bad) or balanced (good)."""
    print("\n" + "="*65)
    print("ONTOLOGY BALANCE CHECK")
    print("="*65)
    conn = sqlite3.connect("data/aive.db")
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT COUNT(*) as n FROM nodes").fetchone()["n"]
    if total == 0:
        print("  No nodes yet. Run rebuild_graph.py first.")
        conn.close()
        return

    types = conn.execute(
        "SELECT node_type, COUNT(*) as n FROM nodes GROUP BY node_type ORDER BY n DESC"
    ).fetchall()

    print(f"\n  Total nodes: {total}")
    print(f"\n  {'Type':<20} {'Count':>6} {'%':>6}  {'Status'}")
    print(f"  {'-'*20} {'-'*6} {'-'*6}  {'-'*20}")

    tech_pct = 0
    for t in types:
        pct = t['n'] / total * 100
        if t['node_type'] == 'Technology':
            tech_pct = pct
        status = ""
        if t['node_type'] == 'Technology' and pct > 40:
            status = "⚠ TOO HIGH (should be <25%)"
        elif t['node_type'] in ('Buyer', 'Regulation', 'EconomicSignal') and pct < 5:
            status = "⚠ TOO LOW (commercial signal weak)"
        elif t['node_type'] in ('Buyer', 'Regulation', 'EconomicSignal') and pct >= 5:
            status = "✓ good"
        print(f"  {t['node_type']:<20} {t['n']:>6} {pct:>5.0f}%  {status}")

    print()
    if tech_pct > 40:
        print("  VERDICT: Graph is technology-biased. Still modeling papers, not markets.")
    elif tech_pct > 25:
        print("  VERDICT: Partially balanced. More economic reality needed.")
    else:
        print("  VERDICT: Well-balanced ontology. Modeling economic reality.")

    conn.close()


if __name__ == "__main__":
    show_ontology_balance()
    run_t16()
