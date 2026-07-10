"""
graph/knowledge_graph.py
=========================
Knowledge Graph Builder — Rich Ontology Version

Node types: Problem, Technology, Capability, Customer, User, Market,
            Constraint, Outcome, Competitor
Relationship types: solves, requires, benefits, purchased_by,
                    constrained_by, enabled_by, competes_with, produces

Build pipeline:
  1. Run concept_extractor.py against all extracted items
  2. Upsert typed concept nodes (merge duplicates by normalized label)
  3. Upsert typed relationship edges (skip self-referential)
  4. Return stats
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "aive.db"
sys.path.insert(0, str(ROOT))

# ── Canonical merge map ───────────────────────────────────────────────────────
# Maps common variant phrases → canonical short concept label
MERGE_MAP = {
    # Problems
    "teacher shortage": "Teacher Shortage",
    "teacher workload": "Teacher Workload",
    "teacher burnout": "Teacher Burnout",
    "educator administrative burden": "Teacher Workload",
    "administrative workload": "Teacher Workload",
    "grading workload": "Teacher Grading Workload",
    "educator capacity constraint": "Teacher Workload",
    "cold-start problem in knowledge tracing": "Knowledge Tracing Cold Start",
    "cold-start knowledge tracing": "Knowledge Tracing Cold Start",
    "student knowledge modeling": "Student Knowledge Modeling",
    "knowledge tracing gap": "Student Knowledge Modeling",
    "academic integrity": "Academic Integrity",
    "academic dishonesty": "Academic Integrity",
    "inappropriate llm use": "Academic Integrity",
    "unstructured llm tutoring": "Unstructured LLM Tutoring",

    # Technologies
    "offline inference": "On-Device LLM Inference",
    "local inference": "On-Device LLM Inference",
    "on-device inference": "On-Device LLM Inference",
    "edge-deployed": "On-Device LLM Inference",
    "privacy-preserving local ai": "On-Device LLM Inference",
    "lora": "LoRA Fine-Tuning",
    "qlora": "QLoRA Fine-Tuning",
    "low-rank adaptation": "LoRA Fine-Tuning",
    "knowledge tracing": "Knowledge Tracing",
    "deep knowledge tracing": "Deep Knowledge Tracing",
    "bayesian knowledge tracing": "Bayesian Knowledge Tracing",
    "socratic dialogue": "Socratic Tutoring",
    "socratic hints": "Socratic Tutoring",
    "socratic tutoring": "Socratic Tutoring",
    "knowledge graph": "Knowledge Graph",
    "prerequisite knowledge graph": "Prerequisite Knowledge Graph",
    "rlhf": "RLHF",
    "reinforcement learning from human feedback": "RLHF",

    # Markets / Customers → split into Buyer / Organization
    "k-12 education": "K-12 School Districts",
    "k-12 schools": "K-12 School Districts",
    "k12": "K-12 School Districts",
    "higher education": "Universities",
    "university": "Universities",
    "edtech": "EdTech Vendors",
    "education technology": "EdTech Vendors",

    # Regulations
    "ferpa": "FERPA",
    "coppa": "COPPA",
    "eu ai act": "EU AI Act",
    "gdpr": "GDPR",

    # Economic signals
    "teacher shortage": "Teacher Shortage",
    "inference cost": "LLM Inference Cost Drop",
    "school budget": "School Budget Constraints",
}

VALID_NODE_TYPES = {
    "Problem", "Technology", "Capability", "Workflow",
    "User", "Buyer", "Organization", "Competitor",
    "Constraint", "Regulation", "EconomicSignal", "Outcome",
    "Resource",   # Capital, Compute, Talent, Data — what the opportunity requires
}

VALID_RELATIONS = {
    "solves", "improves", "benefits", "purchased_by", "used_by",
    "deployed_in", "constrained_by", "enabled_by", "competes_with",
    "produces", "signals", "regulated_by", "requires_resource",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize_label(text: str) -> str:
    """Map raw label to canonical short concept label."""
    if not text:
        return "Unknown"
    lower = text.lower().strip().rstrip(".")
    for pattern, canonical in MERGE_MAP.items():
        if pattern in lower:
            return canonical
    # Truncate to 5 meaningful words
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]*", text)
    STOP = {"the","a","an","of","in","for","to","and","or","is","are","with",
            "by","on","at","that","this","it","which","from","as","using","use",
            "via","into","through","between","system","approach","method",
            "solution","platform","tool","based","new","can","also","than",
            "more","better","specific","utilizing","utilizes","used"}
    meaningful = [w for w in words if w.lower() not in STOP and len(w) > 2]
    result = " ".join(meaningful[:5])
    return result.title()[:60] if result else text[:40].title()


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower().strip())[:80] or "unknown"


def upsert_node(conn, label: str, node_type: str, item_id: str,
                evidence_phrase: str = "") -> str:
    """Insert or update a concept node, merging source items and tracking evidence."""
    if node_type not in VALID_NODE_TYPES:
        node_type = "Technology"
    canonical = normalize_label(label)
    node_id = f"node_{node_type.lower()}_{slugify(canonical)}"
    row = conn.execute("SELECT source_items FROM nodes WHERE id=?", (node_id,)).fetchone()
    sources = json.loads(row[0]) if row else []
    if item_id not in sources:
        sources.append(item_id)

    # Confidence score = evidence breadth: more source items → higher confidence
    # Scaled: 1 source=0.5, 2=0.65, 3=0.75, 4+=0.85, cross-type bonus applied later
    base_confidence = min(0.95, 0.5 + len(sources) * 0.1)

    if row:
        conn.execute(
            "UPDATE nodes SET source_items=? WHERE id=?",
            (json.dumps(sources), node_id),
        )
    else:
        conn.execute(
            """INSERT INTO nodes (id, label, node_type, source_items)
               VALUES (?,?,?,?)""",
            (node_id, canonical, node_type, json.dumps([item_id])),
        )
    return node_id


def upsert_edge(conn, from_id: str, to_id: str, relationship: str,
                item_id: str, weight: float = 0.7, evidence_phrase: str = ""):
    """Insert or update a typed relationship edge. Skips self-referential and low-quality edges."""
    if from_id == to_id:
        return
    if relationship not in VALID_RELATIONS:
        return

    # ── Quality gate ─────────────────────────────────────────────────────────
    # Reject edges below minimum weight — low-weight edges degrade T7 precision
    if weight < 0.6:
        return

    # Reject edges where either label resolves to a generic single-word node.
    # These produce semantically empty relationships like "Technology → solves → Education".
    def _label_from_id(node_id: str) -> str:
        row = conn.execute("SELECT label FROM nodes WHERE id=?", (node_id,)).fetchone()
        return row[0] if row else ""

    from_label = _label_from_id(from_id)
    to_label   = _label_from_id(to_id)

    _GENERIC_LABELS = {
        "technology", "education", "ai", "learning", "students", "teachers",
        "schools", "data", "system", "model", "platform", "tool", "solution",
        "approach", "method", "process", "outcome", "result", "user", "users",
    }

    def _is_generic(label: str) -> bool:
        """True if label is a single word or a known vague concept."""
        clean = label.strip().lower()
        words = clean.split()
        if len(words) <= 1 and clean in _GENERIC_LABELS:
            return True
        if len(clean) < 4:
            return True
        return False

    if _is_generic(from_label) or _is_generic(to_label):
        return
    # ── End quality gate ──────────────────────────────────────────────────────

    edge_id = f"edge_{from_id[:40]}_{relationship}_{to_id[:40]}"
    row = conn.execute("SELECT evidence, weight FROM edges WHERE id=?", (edge_id,)).fetchone()
    evidence = json.loads(row[0]) if row else []
    if item_id not in evidence:
        evidence.append(item_id)
    new_weight = min(1.0, (row[1] if row else 0) + 0.1) if row else weight
    if row:
        conn.execute("UPDATE edges SET evidence=?, weight=? WHERE id=?",
                     (json.dumps(evidence), new_weight, edge_id))
    else:
        conn.execute(
            "INSERT INTO edges (id, from_node, to_node, relationship, weight, evidence) "
            "VALUES (?,?,?,?,?,?)",
            (edge_id, from_id, to_id, relationship, new_weight, json.dumps([item_id])),
        )


# ── Main build ────────────────────────────────────────────────────────────────

def build_graph(clear: bool = True) -> dict:
    """
    Run concept extraction on all extracted items, then build the graph.
    Returns stats dict.
    """
    from agents.concept_extractor import run as extract_all_concepts

    concept_results = extract_all_concepts()

    with sqlite3.connect(DB_PATH) as conn:
        if clear:
            conn.execute("DELETE FROM edges")
            conn.execute("DELETE FROM nodes")

        for item_result in concept_results:
            item_id = item_result["item_id"]
            item_type = item_result.get("item_type", "")

            # Upsert all concept nodes with evidence
            node_id_map: dict[str, str] = {}
            for concept in item_result.get("concepts", []):
                label = concept["label"]
                ctype = concept["type"]
                evidence = concept.get("evidence", "")
                nid = upsert_node(conn, label, ctype, item_id, evidence)
                node_id_map[label] = nid

            # Upsert all typed relationships with evidence stored
            for rel in item_result.get("relationships", []):
                from_label = rel["from"]
                to_label = rel["to"]
                relation = rel["relation"]
                rel_evidence = rel.get("evidence", "")

                # Resolve node IDs — fallback type is Technology
                if from_label not in node_id_map:
                    node_id_map[from_label] = upsert_node(
                        conn, from_label, "Technology", item_id)
                if to_label not in node_id_map:
                    node_id_map[to_label] = upsert_node(
                        conn, to_label, "Technology", item_id)

                # Weight by source type diversity: cross-type evidence is stronger
                base_weight = 0.7
                if item_type == "paper":
                    base_weight = 0.75
                elif item_type == "patent":
                    base_weight = 0.80  # patents signal commercial intent
                elif item_type == "startup":
                    base_weight = 0.85  # startup evidence = market validation

                upsert_edge(
                    conn,
                    node_id_map[from_label],
                    node_id_map[to_label],
                    relation,
                    item_id,
                    weight=base_weight,
                    evidence_phrase=rel_evidence,
                )

        n_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        n_edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        n_items = len(concept_results)

    return {"items": n_items, "nodes": n_nodes, "edges": n_edges}


def query_technologies_for_problem(problem_keyword: str) -> list[dict]:
    """Find technologies that solve a given problem (by keyword match)."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        problem_nodes = conn.execute(
            "SELECT id, label FROM nodes WHERE node_type='Problem' AND lower(label) LIKE ?",
            (f"%{problem_keyword.lower()}%",),
        ).fetchall()

        results = []
        for pnode in problem_nodes:
            edges = conn.execute(
                """
                SELECT n.label AS technology, e.weight, e.evidence, n.node_type
                FROM edges e
                JOIN nodes n ON e.from_node = n.id
                WHERE e.to_node = ? AND e.relationship = 'solves'
                ORDER BY e.weight DESC
                """,
                (pnode["id"],),
            ).fetchall()
            for e in edges:
                results.append({
                    "problem": pnode["label"],
                    "technology": e["technology"],
                    "type": e["node_type"],
                    "weight": e["weight"],
                    "evidence": json.loads(e["evidence"]),
                })
    return results


def commercialization_profile(technology_label: str) -> dict:
    """
    T14 — Commercialization Graph Test.
    For a given technology keyword, answer the 6 commercialization questions using graph evidence.
    Uses fuzzy keyword matching across all node labels.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # Search across ALL nodes, not just Technology type
        # Split into keywords and find any matching node
        keywords = [w.lower() for w in technology_label.split() if len(w) > 3]

        def find_nodes_by_keywords(node_types=None):
            """Find nodes matching any keyword."""
            results = []
            type_filter = ""
            params = []
            if node_types:
                placeholders = ",".join("?" * len(node_types))
                type_filter = f"AND node_type IN ({placeholders})"
                params = list(node_types)

            for kw in keywords:
                rows = conn.execute(
                    f"SELECT id, label, node_type FROM nodes "
                    f"WHERE lower(label) LIKE ? {type_filter} LIMIT 3",
                    [f"%{kw}%"] + params
                ).fetchall()
                results.extend(rows)
            return results

        start_nodes = find_nodes_by_keywords()
        if not start_nodes:
            # Try single-word search
            for kw in technology_label.lower().split():
                rows = conn.execute(
                    "SELECT id, label, node_type FROM nodes WHERE lower(label) LIKE ? LIMIT 3",
                    (f"%{kw}%",)
                ).fetchall()
                start_nodes.extend(rows)

        if not start_nodes:
            return {"error": f"No nodes found matching '{technology_label}'"}

        # Deduplicate
        seen_ids = set()
        unique_starts = []
        for n in start_nodes:
            if n["id"] not in seen_ids:
                seen_ids.add(n["id"])
                unique_starts.append(n)

        print(f"\n  Found {len(unique_starts)} matching nodes:")
        for n in unique_starts[:5]:
            print(f"    [{n['node_type']}] {n['label']}")

        def get_related_from_nodes(node_ids, rel_type):
            results = []
            for nid in node_ids:
                rows = conn.execute("""
                    SELECT n.label, n.node_type, e.evidence
                    FROM edges e JOIN nodes n ON e.to_node = n.id
                    WHERE e.from_node = ? AND e.relationship = ?
                """, (nid, rel_type)).fetchall()
                results.extend([{
                    "label": r["label"], "type": r["node_type"],
                    "evidence": json.loads(r["evidence"] or "[]")
                } for r in rows])
            return results

        def get_all_related(node_ids):
            """Get all edges from/to these nodes."""
            results = {}
            for rel in VALID_RELATIONS:
                found = get_related_from_nodes(node_ids, rel)
                if found:
                    results[rel] = found
            return results

        node_ids = [n["id"] for n in unique_starts]
        all_edges = get_all_related(node_ids)

        return {
            "technology": technology_label,
            "matched_nodes": [{"label": n["label"], "type": n["node_type"]} for n in unique_starts[:5]],
            "Q1_problems_solved":     all_edges.get("solves", []),
            "Q2_workflows_improved":  all_edges.get("improves", []),
            "Q3_users_benefited":     all_edges.get("benefits", []),
            "Q4_buyers":              all_edges.get("purchased_by", []),
            "Q5_regulations":         all_edges.get("regulated_by", []) + all_edges.get("constrained_by", []),
            "Q6_competitors":         all_edges.get("competes_with", []),
        }
