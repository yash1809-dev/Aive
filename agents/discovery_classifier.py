"""
agents/discovery_classifier.py
===============================
Discovery Classifier — Research gaps, contradictions, and method transfers.

Analyzes the knowledge graph to detect:
  1. Research gaps      — Problems with no Technology connections, Technologies with no Buyer
  2. Contradictions     — Conflicting claims about the same concept across sources
  3. Method transfers   — Technologies present in one domain but absent from similar contexts

All discoveries are saved to the `discoveries` and `contradictions` tables with
full evidence traceability and confidence scoring.
"""

import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.base import call_llm
from db.init_db import DB_PATH


class DiscoveryClassifier:
    """
    Detect high-value research insights from the knowledge graph.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    # ── Research Gaps ─────────────────────────────────────────────────────────

    def find_research_gaps(self, min_confidence: float = 0.6) -> list[dict]:
        """
        Detect research gaps by analyzing graph topology:
          - Problems with no Technology nodes connected
          - Technologies with no Buyer/Organization nodes connected
          - High-value nodes with weak evidence support

        Returns list of gap discoveries with type, title, description, evidence.
        """
        gaps = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Gap Type 1: Unsolved Problems
            unsolved_problems = conn.execute("""
                SELECT n.id, n.label, n.source_items
                FROM nodes n
                WHERE n.node_type = 'Problem'
                  AND NOT EXISTS (
                      SELECT 1 FROM edges e
                      WHERE e.to_node = n.id
                        AND e.relationship = 'solves'
                  )
            """).fetchall()

            for problem in unsolved_problems:
                source_items = json.loads(problem["source_items"] or "[]")
                if len(source_items) >= 2:  # Only report if mentioned in multiple sources
                    gaps.append({
                        "type": "research_gap",
                        "title": f"Unsolved Problem: {problem['label']}",
                        "description": (
                            f"The problem '{problem['label']}' is mentioned across "
                            f"{len(source_items)} sources but has no documented solution "
                            f"technology in the knowledge graph."
                        ),
                        "evidence": source_items,
                        "source_nodes": [problem["id"]],
                        "confidence": min(0.9, 0.5 + len(source_items) * 0.1),
                        "reasoning": "Graph topology: Problem node with no incoming 'solves' edges.",
                    })

            # Gap Type 2: Uncommercial Technologies
            uncommercial_tech = conn.execute("""
                SELECT n.id, n.label, n.source_items
                FROM nodes n
                WHERE n.node_type = 'Technology'
                  AND NOT EXISTS (
                      SELECT 1 FROM edges e
                      WHERE e.from_node = n.id
                        AND e.relationship IN ('purchased_by', 'deployed_in')
                  )
            """).fetchall()

            for tech in uncommercial_tech:
                source_items = json.loads(tech["source_items"] or "[]")
                if len(source_items) >= 2:
                    gaps.append({
                        "type": "research_gap",
                        "title": f"Uncommercial Technology: {tech['label']}",
                        "description": (
                            f"The technology '{tech['label']}' appears in "
                            f"{len(source_items)} sources but has no documented "
                            f"commercial adoption or buyer relationships."
                        ),
                        "evidence": source_items,
                        "source_nodes": [tech["id"]],
                        "confidence": min(0.85, 0.4 + len(source_items) * 0.1),
                        "reasoning": "Graph topology: Technology node with no outgoing 'purchased_by' or 'deployed_in' edges.",
                    })

        # Filter by confidence
        return [g for g in gaps if g["confidence"] >= min_confidence]

    # ── Contradictions ────────────────────────────────────────────────────────

    def find_contradictions(self, sample_size: int = 50) -> list[dict]:
        """
        Detect conflicting claims about the same concept using LLM-as-judge.
        
        Strategy:
          1. Find nodes that appear in multiple items
          2. Extract relevant text segments from those items
          3. Use LLM to detect contradictory claims
          4. Save to contradictions table
        
        Args:
            sample_size: Max number of multi-source nodes to analyze (default 50)
        
        Returns:
            List of contradiction dicts with concept, claim_a, claim_b, sources
        """
        contradictions = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Find nodes with multiple source items (cross-document concepts)
            multi_source_nodes = conn.execute("""
                SELECT id, label, node_type, source_items
                FROM nodes
                WHERE json_array_length(source_items) >= 2
                ORDER BY json_array_length(source_items) DESC
                LIMIT ?
            """, (sample_size,)).fetchall()

            for node in multi_source_nodes:
                node_label = node["label"]
                source_ids = json.loads(node["source_items"] or "[]")
                
                if len(source_ids) < 2:
                    continue

                # Get text segments from first two sources
                items = conn.execute("""
                    SELECT id, title, summary, problem, solution, technology
                    FROM items
                    WHERE id IN (?, ?)
                """, source_ids[:2]).fetchall()

                if len(items) < 2:
                    continue

                # Build comparison prompt
                item_a = items[0]
                item_b = items[1]
                
                text_a = f"Title: {item_a['title']}\n"
                text_a += f"Summary: {item_a['summary'] or ''}\n"
                text_a += f"Problem: {item_a['problem'] or ''}\n"
                text_a += f"Technology: {item_a['technology'] or ''}"
                
                text_b = f"Title: {item_b['title']}\n"
                text_b += f"Summary: {item_b['summary'] or ''}\n"
                text_b += f"Problem: {item_b['problem'] or ''}\n"
                text_b += f"Technology: {item_b['technology'] or ''}"

                prompt = f"""Analyze these two sources that both discuss "{node_label}".
Determine if they make contradictory claims.

Source A:
{text_a}

Source B:
{text_b}

Return JSON only:
{{
  "contradicts": true or false,
  "concept": "{node_label}",
  "claim_a": "specific claim from source A (one sentence)",
  "claim_b": "specific conflicting claim from source B (one sentence)",
  "explanation": "why these claims contradict (one sentence)",
  "confidence": 0.0 to 1.0
}}

Only set contradicts=true if there is a clear factual disagreement.
Different emphasis or framing is not a contradiction.
"""

                try:
                    result = call_llm(
                        prompt,
                        system="You are a research analyst detecting contradictions. Return valid JSON only.",
                        agent="critic",
                    )
                    
                    if result.get("contradicts"):
                        contradictions.append({
                            "concept": result.get("concept", node_label),
                            "claim_a": result.get("claim_a", ""),
                            "claim_b": result.get("claim_b", ""),
                            "source_a": item_a["id"],
                            "source_b": item_b["id"],
                            "explanation": result.get("explanation", ""),
                            "confidence": result.get("confidence", 0.5),
                        })
                
                except Exception as e:
                    print(f"  [WARN] Contradiction check failed for {node_label}: {e}")
                    continue

        return contradictions

    # ── Method Transfers ──────────────────────────────────────────────────────

    def find_method_transfers(self, min_confidence: float = 0.6) -> list[dict]:
        """
        Identify Technology nodes present in one domain context but absent
        from another domain that has similar Problem nodes.
        
        Strategy:
          1. Group nodes by domain (from items.domain field)
          2. For each domain pair, find shared problems
          3. Detect technologies in domain A solving those problems but absent in domain B
          4. Score by problem similarity and technology relevance
        
        Returns:
            List of method transfer opportunities
        """
        transfers = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get domain distribution from items
            domains = conn.execute("""
                SELECT DISTINCT domain FROM items
                WHERE domain IS NOT NULL AND domain != 'unknown'
                LIMIT 10
            """).fetchall()

            domain_list = [d["domain"] for d in domains]
            
            if len(domain_list) < 2:
                return []  # Need at least 2 domains for transfer detection

            # For each domain pair, find transfer opportunities
            for i, domain_a in enumerate(domain_list):
                for domain_b in domain_list[i+1:]:
                    
                    # Find technologies used in domain A
                    tech_in_a = conn.execute("""
                        SELECT DISTINCT n.id, n.label, n.source_items
                        FROM nodes n
                        JOIN items i ON i.id IN (
                            SELECT value FROM json_each(n.source_items)
                        )
                        WHERE n.node_type = 'Technology'
                          AND i.domain = ?
                    """, (domain_a,)).fetchall()

                    # Find technologies used in domain B
                    tech_in_b_labels = {
                        row["label"] for row in conn.execute("""
                            SELECT DISTINCT n.label
                            FROM nodes n
                            JOIN items i ON i.id IN (
                                SELECT value FROM json_each(n.source_items)
                            )
                            WHERE n.node_type = 'Technology'
                              AND i.domain = ?
                        """, (domain_b,)).fetchall()
                    }

                    # Find problems in domain B
                    problems_in_b = conn.execute("""
                        SELECT DISTINCT n.id, n.label
                        FROM nodes n
                        JOIN items i ON i.id IN (
                            SELECT value FROM json_each(n.source_items)
                        )
                        WHERE n.node_type = 'Problem'
                          AND i.domain = ?
                    """, (domain_b,)).fetchall()

                    # Identify transfer candidates: tech in A but not in B
                    for tech in tech_in_a:
                        if tech["label"] not in tech_in_b_labels:
                            source_items = json.loads(tech["source_items"] or "[]")
                            
                            # Check if this tech solves any problems
                            solved_problems = conn.execute("""
                                SELECT n.label FROM edges e
                                JOIN nodes n ON e.to_node = n.id
                                WHERE e.from_node = ? AND e.relationship = 'solves'
                            """, (tech["id"],)).fetchall()

                            if solved_problems and problems_in_b:
                                transfers.append({
                                    "type": "method_transfer",
                                    "title": f"Transfer {tech['label']} from {domain_a} to {domain_b}",
                                    "description": (
                                        f"The technology '{tech['label']}' is used in {domain_a} "
                                        f"to solve {', '.join(p['label'] for p in solved_problems[:2])}. "
                                        f"This technology is absent from {domain_b}, which has "
                                        f"{len(problems_in_b)} documented problems."
                                    ),
                                    "evidence": source_items,
                                    "source_nodes": [tech["id"]],
                                    "confidence": min(0.8, 0.5 + len(source_items) * 0.05),
                                    "reasoning": f"Technology proven in {domain_a}, absent in {domain_b}.",
                                })

        return [t for t in transfers if t["confidence"] >= min_confidence]

    # ── Persist discoveries ───────────────────────────────────────────────────

    def save_discoveries(self, discoveries: list[dict]) -> int:
        """Save discoveries to the discoveries table."""
        if not discoveries:
            return 0

        with sqlite3.connect(self.db_path) as conn:
            for disc in discoveries:
                disc_id = f"disc_{uuid.uuid4().hex[:12]}"
                conn.execute("""
                    INSERT INTO discoveries
                    (id, type, title, description, evidence, source_nodes, confidence, reasoning, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    disc_id,
                    disc.get("type", "research_gap"),
                    disc.get("title", ""),
                    disc.get("description", ""),
                    json.dumps(disc.get("evidence", [])),
                    json.dumps(disc.get("source_nodes", [])),
                    disc.get("confidence", 0.5),
                    disc.get("reasoning", ""),
                    datetime.now(timezone.utc).isoformat(),
                ))

        return len(discoveries)

    def save_contradictions(self, contradictions: list[dict]) -> int:
        """Save contradictions to the contradictions table."""
        if not contradictions:
            return 0

        with sqlite3.connect(self.db_path) as conn:
            for contra in contradictions:
                contra_id = f"contra_{uuid.uuid4().hex[:12]}"
                conn.execute("""
                    INSERT INTO contradictions
                    (id, concept, claim_a, claim_b, source_a, source_b, explanation, confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    contra_id,
                    contra.get("concept", ""),
                    contra.get("claim_a", ""),
                    contra.get("claim_b", ""),
                    contra.get("source_a", ""),
                    contra.get("source_b", ""),
                    contra.get("explanation", ""),
                    contra.get("confidence", 0.5),
                    datetime.now(timezone.utc).isoformat(),
                ))

        return len(contradictions)

    # ── Main run ──────────────────────────────────────────────────────────────

    def run_all(self) -> dict:
        """
        Run all discovery classification methods and save results.
        Returns summary stats.
        """
        print("Running Discovery Classifier...\n")

        # Research Gaps
        print("  [1/3] Detecting research gaps...")
        gaps = self.find_research_gaps()
        print(f"    Found {len(gaps)} research gaps")

        # Contradictions
        print("  [2/3] Detecting contradictions...")
        contradictions = self.find_contradictions(sample_size=30)
        print(f"    Found {len(contradictions)} contradictions")

        # Method Transfers
        print("  [3/3] Detecting method transfer opportunities...")
        transfers = self.find_method_transfers()
        print(f"    Found {len(transfers)} method transfer opportunities")

        # Save all discoveries
        all_discoveries = gaps + transfers
        n_saved_disc = self.save_discoveries(all_discoveries)
        n_saved_contra = self.save_contradictions(contradictions)

        print(f"\nSaved {n_saved_disc} discoveries and {n_saved_contra} contradictions.")

        return {
            "research_gaps": len(gaps),
            "contradictions": len(contradictions),
            "method_transfers": len(transfers),
            "total_discoveries": n_saved_disc,
            "total_contradictions": n_saved_contra,
        }


# ── CLI Entry Point ───────────────────────────────────────────────────────────

def run(db_path: Path = DB_PATH) -> dict:
    """Run discovery classification pipeline."""
    classifier = DiscoveryClassifier(db_path)
    return classifier.run_all()


if __name__ == "__main__":
    result = run()
    print("\nDiscovery Classification Complete:")
    print(json.dumps(result, indent=2))
