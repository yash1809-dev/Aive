"""
Opportunity Engine — Economic Reality Version

Discovers opportunities by finding high-confidence intersections across
the 13-type knowledge graph:
  Problem × Technology × (Buyer OR EconomicSignal OR Regulation)

The key insight: an opportunity only matters if there is commercial grounding.
A Problem + Technology combination without a Buyer or EconomicSignal = noise.
"""

import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.base import call_llm
from db.init_db import DB_PATH

# ── Config ────────────────────────────────────────────────────────────────────
MIN_EDGE_WEIGHT = 0.65
MIN_SOURCES = 1

ENRICH_PROMPT = """You are AIVE Opportunity Finder. Evaluate this graph-derived candidate.

A strong opportunity requires ALL of:
1. A SPECIFIC problem with real pain
2. A SPECIFIC technology that addresses it
3. A CLEAR buyer who has budget
4. A TIMING signal — why now?
5. Evidence from the knowledge graph

Candidate:
{candidate}

Return JSON only:
{{
  "title": "Short opportunity name (5-8 words)",
  "problem": "Specific problem in plain language (1 sentence)",
  "technology": "Specific technology or method (1 sentence)",
  "market": "Specific market segment with named buyer type",
  "timing_signal": "Why NOW — cite specific regulation, cost change, or market event",
  "reasoning": "2-3 sentences connecting Problem + Technology + Buyer + Timing",
  "existing_competitors": ["competitor 1", "competitor 2"],
  "evidence_summary": ["evidence point 1", "evidence point 2", "evidence point 3"],
  "buyer": "Specific buyer (e.g. K-12 School District IT Procurement)",
  "regulation": "Relevant regulation or leave empty",
  "economic_signal": "Market timing signal or leave empty",
  "novelty_score": 0,
  "timing_score": 0,
  "market_score": 0,
  "feasibility": 0,
  "confidence_score": 0
}}

Score each 0-10. Be skeptical.
REJECT if buyer is "Unknown" or "N/A".
REJECT if timing_signal is vague like "AI is trending".
Only score above 7 if there is cross-layer evidence (research + commercial).
"""


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_evidence(raw) -> list[str]:
    try:
        return json.loads(raw) if raw else []
    except json.JSONDecodeError:
        return []


def _get_label(conn, node_id: str) -> str:
    row = conn.execute("SELECT label FROM nodes WHERE id=?", (node_id,)).fetchone()
    return row["label"] if row else ""


def _item_types(item_ids: list[str]) -> set[str]:
    if not item_ids:
        return set()
    with _conn() as conn:
        placeholders = ",".join("?" * len(item_ids))
        rows = conn.execute(
            f"SELECT DISTINCT type FROM items WHERE id IN ({placeholders})",
            item_ids,
        ).fetchall()
    return {r["type"] for r in rows}


# ── Discovery functions ───────────────────────────────────────────────────────

def find_problems(min_sources: int = MIN_SOURCES) -> list[dict]:
    """Find Problem nodes with sufficient evidence."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, label, source_items FROM nodes WHERE node_type='Problem'"
        ).fetchall()
    results = []
    for row in rows:
        sources = _parse_evidence(row["source_items"])
        if len(sources) >= min_sources:
            results.append({
                "node_id": row["id"],
                "label": row["label"],
                "source_count": len(sources),
                "sources": sources,
                "type": "Problem",
            })
    return sorted(results, key=lambda x: x["source_count"], reverse=True)


def find_technologies(min_sources: int = MIN_SOURCES) -> list[dict]:
    """Find Technology nodes with sufficient evidence."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, label, source_items FROM nodes WHERE node_type IN ('Technology','Capability')"
        ).fetchall()
    results = []
    for row in rows:
        sources = _parse_evidence(row["source_items"])
        if len(sources) >= min_sources:
            results.append({
                "node_id": row["id"],
                "label": row["label"],
                "source_count": len(sources),
                "sources": sources,
                "type": "Technology",
            })
    return sorted(results, key=lambda x: x["source_count"], reverse=True)


def find_commercial_anchors() -> list[dict]:
    """
    Find Buyer, EconomicSignal, Regulation, Organization nodes.
    These are the commercial grounding nodes — opportunities without
    at least one of these are commercially ungrounded.
    """
    with _conn() as conn:
        rows = conn.execute(
            """SELECT id, label, node_type, source_items FROM nodes
               WHERE node_type IN ('Buyer','EconomicSignal','Regulation','Organization','Constraint')"""
        ).fetchall()
    results = []
    for row in rows:
        sources = _parse_evidence(row["source_items"])
        results.append({
            "node_id": row["id"],
            "label": row["label"],
            "type": row["node_type"],
            "source_count": len(sources),
            "sources": sources,
        })
    return sorted(results, key=lambda x: x["source_count"], reverse=True)


def find_cross_graph_combinations(limit: int = 50) -> list[dict]:
    """
    Find Problem × Technology × CommercialAnchor triples.

    An opportunity candidate requires:
    - A Problem node
    - A Technology node that has ANY edge to/from the Problem (direct or via shared sources)
    - At least one commercial anchor (Buyer, EconomicSignal, Regulation)

    Source diversity bonus: candidates where evidence spans papers + patents + startups
    score higher.
    """
    problems = find_problems()[:25]
    technologies = find_technologies()[:25]
    anchors = find_commercial_anchors()

    if not problems or not technologies:
        return []

    # Build edges lookup for fast checking
    with _conn() as conn:
        all_edges = conn.execute(
            "SELECT from_node, to_node, relationship, evidence, weight FROM edges"
        ).fetchall()

    # Build adjacency: node_id -> {related_node_ids}
    adjacency: dict[str, set[str]] = {}
    edge_map: dict[tuple, dict] = {}
    for edge in all_edges:
        fn, tn = edge["from_node"], edge["to_node"]
        adjacency.setdefault(fn, set()).add(tn)
        adjacency.setdefault(tn, set()).add(fn)
        edge_map[(fn, tn)] = {
            "relationship": edge["relationship"],
            "evidence": _parse_evidence(edge["evidence"]),
            "weight": edge["weight"],
        }

    def are_connected(node_a: str, node_b: str) -> bool:
        """Check if two nodes are connected directly or via 1 hop."""
        if node_b in adjacency.get(node_a, set()):
            return True
        # 1-hop: any shared neighbor
        neighbors_a = adjacency.get(node_a, set())
        neighbors_b = adjacency.get(node_b, set())
        return bool(neighbors_a & neighbors_b)

    def get_connecting_evidence(node_a: str, node_b: str) -> list[str]:
        """Get evidence IDs connecting two nodes."""
        direct = edge_map.get((node_a, node_b)) or edge_map.get((node_b, node_a))
        if direct:
            return direct["evidence"]
        return []

    candidates = []
    seen = set()

    for prob, tech in product(problems[:15], technologies[:15]):
        if prob["label"] == tech["label"]:
            continue

        connected = are_connected(prob["node_id"], tech["node_id"])

        # Also consider shared sources as implicit connection
        shared_sources = set(prob["sources"]) & set(tech["sources"])

        if not connected and not shared_sources:
            continue

        # Find best commercial anchor for this pair
        best_anchor = None
        for anchor in anchors:
            anchor_connected = (
                are_connected(prob["node_id"], anchor["node_id"]) or
                are_connected(tech["node_id"], anchor["node_id"]) or
                bool(set(prob["sources"]) & set(anchor["sources"])) or
                bool(set(tech["sources"]) & set(anchor["sources"]))
            )
            if anchor_connected:
                best_anchor = anchor
                break

        # Score the candidate
        all_evidence = list(set(prob["sources"] + tech["sources"]))
        evidence_types = _item_types(all_evidence)
        type_diversity = len(evidence_types)

        score = 0.5
        score += type_diversity * 0.2
        score += len(shared_sources) * 0.05
        if best_anchor:
            score += 0.4
            if best_anchor["type"] == "Buyer":
                score += 0.2
            elif best_anchor["type"] == "EconomicSignal":
                score += 0.15
            elif best_anchor["type"] == "Regulation":
                score += 0.1

        # NOVELTY: reward cross-domain (research paper + economic signal)
        has_economic = any(s.startswith("econ_") for s in all_evidence)
        has_paper = any(not s.startswith("econ_") and not s.startswith("startup_") for s in all_evidence)
        has_startup = any(s.startswith("startup_") for s in all_evidence)
        if has_economic and has_paper:
            score += 0.3   # non-obvious cross-domain combination
        if has_economic and has_startup:
            score += 0.15  # competitor + startup insight

        # PENALTY: over-represented nodes are the obvious ones
        if prob["source_count"] > 4:
            score -= (prob["source_count"] - 4) * 0.1
        if tech["source_count"] > 4:
            score -= (tech["source_count"] - 4) * 0.05

        # COMPETITOR DENSITY PENALTY: if 3+ named competitors already appear in
        # the evidence, the Critic will almost certainly reject on "saturated market".
        # Pre-filter these before enrichment to save LLM calls and critic capacity.
        competitor_count = sum(1 for s in all_evidence if s.startswith("startup_"))
        if competitor_count >= 4:
            score -= (competitor_count - 3) * 0.25  # heavy penalty beyond 3 competitors
        if competitor_count >= 6:
            continue  # skip entirely — definitely saturated

        key = (prob["label"][:30], tech["label"][:30])
        if key in seen:
            continue
        seen.add(key)

        candidates.append({
            "problem": prob["label"],
            "technology": tech["label"],
            "problem_node": prob["node_id"],
            "technology_node": tech["node_id"],
            "commercial_anchor": best_anchor["label"] if best_anchor else None,
            "anchor_type": best_anchor["type"] if best_anchor else None,
            "evidence_ids": all_evidence,
            "evidence_types": sorted(evidence_types),
            "score": round(score, 2),
            "commercially_grounded": best_anchor is not None,
        })

    # Sort: commercially grounded first, then by score
    candidates.sort(key=lambda x: (x["commercially_grounded"], x["score"]), reverse=True)
    return candidates[:limit]


def _evidence_details(item_ids: list[str]) -> dict:
    ids = item_ids[:14]
    if not ids:
        return {"papers": [], "patents": [], "startups": [], "economic_signals": [], "items": []}
    with _conn() as conn:
        placeholders = ",".join("?" * len(ids))
        rows = conn.execute(
            f"SELECT id, type, title FROM items WHERE id IN ({placeholders})", ids
        ).fetchall()

    grouped = {"papers": [], "patents": [], "startups": [], "economic_signals": []}
    items = []
    for r in rows:
        items.append({"id": r["id"], "type": r["type"], "title": r["title"]})
        if r["type"] == "paper":
            grouped["papers"].append(r["title"])
        elif r["type"] == "patent":
            grouped["patents"].append(r["title"])
        elif r["type"] == "startup":
            grouped["startups"].append(r["title"])
        elif r["type"] == "economic_signal":
            grouped["economic_signals"].append(r["title"])
    grouped["items"] = items
    return grouped


def generate_opportunity(candidate: dict) -> dict:
    """LLM enriches a graph candidate into a full opportunity."""
    evidence = _evidence_details(candidate["evidence_ids"])
    payload = {**candidate, "evidence": evidence}

    try:
        enriched = call_llm(
            ENRICH_PROMPT.format(candidate=json.dumps(payload, indent=2)),
            system="You are a skeptical opportunity analyst. Return valid JSON only. Reject vague opportunities.",
            agent="reasoner",
        )
    except Exception:
        enriched = call_llm(
            ENRICH_PROMPT.format(candidate=json.dumps(payload, indent=2)),
            system="You are a skeptical opportunity analyst. Return valid JSON only.",
            agent="extractor",
        )
    return {**candidate, **enriched, "evidence_detail": evidence}


def save_opportunity(opp: dict) -> str:
    opp_id = f"opp_{uuid.uuid4().hex[:8]}"
    ev = opp.get("evidence_detail") or _evidence_details(opp.get("evidence_ids", []))
    now = datetime.now(timezone.utc).isoformat()

    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO opportunities (
                id, title, problem, technology, market, timing_signal,
                problem_node, technology_node, market_node, reasoning,
                evidence, existing_competitors,
                novelty_score, timing_score, market_score, feasibility, confidence_score,
                edge_confidence, source_papers, source_patents, source_startups, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                opp_id,
                opp.get("title", ""),
                opp.get("problem", ""),
                opp.get("technology", ""),
                opp.get("market", opp.get("commercial_anchor", "")),
                opp.get("timing_signal", ""),
                opp.get("problem_node"),
                opp.get("technology_node"),
                None,
                opp.get("reasoning", ""),
                json.dumps(opp.get("evidence_summary", [])),
                json.dumps(opp.get("existing_competitors", [])),
                opp.get("novelty_score", 0),
                opp.get("timing_score", 0),
                opp.get("market_score", 0),
                opp.get("feasibility", 0),
                opp.get("confidence_score", 0),
                opp.get("score", 0),
                json.dumps(ev.get("papers", [])),
                json.dumps(ev.get("patents", [])),
                json.dumps(ev.get("startups", [])),
                now,
            ),
        )
    return opp_id


def run(count: int = 30) -> list[dict]:
    print("1. Finding cross-graph opportunity candidates...")
    candidates = find_cross_graph_combinations(limit=count * 2)

    grounded = [c for c in candidates if c["commercially_grounded"]]
    ungrounded = [c for c in candidates if not c["commercially_grounded"]]
    print(f"   {len(grounded)} commercially grounded candidates")
    print(f"   {len(ungrounded)} ungrounded candidates (missing buyer/regulation/signal)")

    # Prioritize grounded; fill remaining slots with best ungrounded
    selected = (grounded + ungrounded)[:count]

    print(f"2. Enriching {len(selected)} candidates with LLM...")

    # Clear old opportunities
    with _conn() as conn:
        conn.execute("DELETE FROM opportunities")
        conn.execute("DELETE FROM rejected_ideas")
    print("   Cleared old opportunities")

    opportunities = []
    for i, candidate in enumerate(selected):
        anchor = candidate.get("commercial_anchor", "none")
        print(f"   [{i+1}/{len(selected)}] {candidate['problem'][:40]} × {candidate['technology'][:30]} [{anchor}]")
        try:
            opp = generate_opportunity(candidate)
            opp_id = save_opportunity(opp)
            opp["id"] = opp_id
            opportunities.append(opp)
        except Exception as e:
            print(f"   [ERROR] {e}")

    out = ROOT / "data" / "exports" / "opportunities_batch1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(opportunities, indent=2), encoding="utf-8")
    print(f"\nSaved {len(opportunities)} opportunities to {out}")
    print("Next: python agents/critic.py")
    return opportunities


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    run(count=count)


if __name__ == "__main__":
    main()
