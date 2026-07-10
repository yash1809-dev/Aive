"""
agents/ontology_scorer.py
==========================
Ontology Coverage Score — rates every opportunity on how completely
the knowledge graph can answer the 10 commercial reality questions.

An opportunity that scores < 6/10 is commercially ungrounded regardless
of how technically interesting it sounds.

Score dimensions:
  1. Problem         — does a specific Problem node exist?
  2. Technology      — does a Technology node exist?
  3. Workflow        — does a Workflow node exist?
  4. User            — does a User node exist?
  5. Buyer           — does a Buyer/Organization node exist with purchased_by edge?
  6. Constraint      — does a Constraint node exist?
  7. Regulation      — does a Regulation node exist?
  8. Competitor      — does a Competitor node exist?
  9. EconomicSignal  — does an EconomicSignal node exist?
  10. Resource        — does a Resource node with requires_resource exist?

Pass threshold: >= 6/10 to survive
Critical threshold: Buyer must be present (score 0 if Buyer missing)
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.init_db import DB_PATH


def score_opportunity(opportunity: dict) -> dict:
    """
    Score one opportunity on ontology coverage (0-10).
    Returns a dict with per-dimension scores and total.
    """
    opp_id = opportunity.get("id", "")
    title = opportunity.get("title", "")

    # Keywords from the opportunity to search graph with — use individual meaningful words
    search_terms = []
    for field in ("problem", "technology", "market", "title"):
        val = str(opportunity.get(field, "") or "")
        if val:
            # Extract individual meaningful words (3+ chars, skip stop words)
            STOP = {"the", "a", "an", "of", "in", "for", "to", "and", "or",
                    "is", "are", "with", "by", "using", "based", "from"}
            words = [w.lower().strip(".,") for w in val.split()
                     if len(w) > 3 and w.lower() not in STOP]
            search_terms.extend(words[:4])

    # Deduplicate
    search_terms = list(dict.fromkeys(search_terms))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    def find_node(node_types: list[str], terms: list[str]) -> bool:
        """Check if any node of given types matches any search term."""
        placeholders = ",".join("?" * len(node_types))
        for term in terms:
            rows = conn.execute(
                f"SELECT id FROM nodes WHERE node_type IN ({placeholders}) "
                f"AND lower(label) LIKE ? LIMIT 1",
                node_types + [f"%{term}%"]
            ).fetchone()
            if rows:
                return True
        return False

    def has_edge(rel_type: str, terms: list[str]) -> bool:
        """Check if any edge of given relationship type connects to nodes matching terms."""
        for term in terms:
            rows = conn.execute("""
                SELECT e.id FROM edges e
                JOIN nodes n1 ON e.from_node = n1.id
                JOIN nodes n2 ON e.to_node = n2.id
                WHERE e.relationship = ?
                AND (lower(n1.label) LIKE ? OR lower(n2.label) LIKE ?)
                LIMIT 1
            """, (rel_type, f"%{term}%", f"%{term}%")).fetchone()
            if rows:
                return True
        return False

    dimensions = {
        "Problem":         find_node(["Problem"], search_terms),
        "Technology":      find_node(["Technology"], search_terms),
        "Workflow":        find_node(["Workflow"], search_terms),
        "User":            find_node(["User"], search_terms),
        "Buyer":           find_node(["Buyer", "Organization"], search_terms) or has_edge("purchased_by", search_terms),
        "Constraint":      find_node(["Constraint"], search_terms),
        "Regulation":      find_node(["Regulation"], search_terms),
        "Competitor":      find_node(["Competitor"], search_terms),
        "EconomicSignal":  find_node(["EconomicSignal"], search_terms),
        "Resource":        find_node(["Resource"], search_terms) or has_edge("requires_resource", search_terms),
    }

    conn.close()

    score = sum(1 for v in dimensions.values() if v)

    # Critical rule: Buyer must be present
    buyer_present = dimensions["Buyer"]
    commercially_viable = buyer_present and score >= 6

    return {
        "opportunity_id": opp_id,
        "title": title,
        "ontology_score": score,
        "max_score": 10,
        "buyer_present": buyer_present,
        "commercially_viable": commercially_viable,
        "dimensions": dimensions,
        "missing": [k for k, v in dimensions.items() if not v],
        "verdict": "viable" if commercially_viable else (
            "no_buyer" if not buyer_present else "insufficient_coverage"
        ),
    }


def score_all_opportunities(min_score: int = 0) -> list[dict]:
    """Score all opportunities in the DB."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, title, problem, technology, market,
                   critic_verdict, confidence_score
            FROM opportunities
            ORDER BY confidence_score DESC
        """).fetchall()

    results = []
    for row in rows:
        score_result = score_opportunity(dict(row))
        if score_result["ontology_score"] >= min_score:
            results.append(score_result)
    return results


def print_coverage_report():
    """Print a human-readable ontology coverage report."""
    print("\n" + "="*65)
    print("ONTOLOGY COVERAGE SCORE — All Opportunities")
    print("="*65)

    results = score_all_opportunities()
    if not results:
        print("  No opportunities in DB. Run opportunity_finder.py first.")
        return

    viable = [r for r in results if r["commercially_viable"]]
    no_buyer = [r for r in results if not r["buyer_present"]]

    print(f"\n  Total opportunities: {len(results)}")
    print(f"  Commercially viable (buyer present + score >= 6): {len(viable)}")
    print(f"  Missing buyer entirely: {len(no_buyer)}")

    print(f"\n  {'Title':<45} {'Score':>6} {'Buyer':>6} {'Viable':>7}")
    print(f"  {'-'*45} {'-'*6} {'-'*6} {'-'*7}")

    for r in sorted(results, key=lambda x: x["ontology_score"], reverse=True):
        buyer = "✓" if r["buyer_present"] else "✗"
        viable_str = "✓" if r["commercially_viable"] else "✗"
        print(f"  {r['title'][:45]:<45} {r['ontology_score']:>5}/10 {buyer:>6} {viable_str:>7}")
        if r["missing"]:
            print(f"    missing: {', '.join(r['missing'])}")

    if not viable:
        print(f"\n  ⚠ ZERO commercially viable opportunities.")
        print(f"  This means the graph has no Buyer/Organization nodes connected to any opportunity.")
        print(f"  Run: python ingest/fetch_economic_signals.py")
        print(f"  Then rebuild the graph to add procurement intelligence.")


if __name__ == "__main__":
    print_coverage_report()
