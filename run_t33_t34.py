"""
run_t33_t34.py — Theme Expansion Test (T33) + White Space Discovery Test (T34)

T33: After domain expansion, measure theme distribution across opportunities.
     Pass condition: top theme < 35% of total candidates.

T34: White Space Discovery — find problems with strong evidence but sparse
     startup coverage. These are the highest-value frontier zones.

Run AFTER graph rebuild:
    python run_t33_t34.py
"""
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "aive.db"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _classify_domain(label: str) -> str:
    """Map a node label to a high-level domain bucket."""
    label_lower = label.lower()
    if any(k in label_lower for k in ["grading", "teacher workload", "grading workload", "assessment"]):
        return "Teacher Grading Workload"
    if any(k in label_lower for k in ["academic integrity", "plagiar", "dishonest", "cheating"]):
        return "Academic Integrity"
    if any(k in label_lower for k in ["special education", "iep", "disability", "autism", "dyslexia"]):
        return "Special Education / IEP"
    if any(k in label_lower for k in ["rural", "offline", "low resource", "underserved", "bandwidth"]):
        return "Rural / Offline Learning"
    if any(k in label_lower for k in ["vocational", "workforce", "skills training", "job training", "apprentice"]):
        return "Vocational / Workforce"
    if any(k in label_lower for k in ["adult literacy", "adult learning", "continuing education", "lifelong"]):
        return "Adult Literacy"
    if any(k in label_lower for k in ["medical", "clinical", "healthcare", "nursing", "patient", "hospital"]):
        return "Healthcare Education"
    if any(k in label_lower for k in ["language learning", "second language", "ell", "esl", "bilingual", "foreign language"]):
        return "Language Learning / ELL"
    if any(k in label_lower for k in ["knowledge tracing", "student model", "learning path", "adaptive"]):
        return "Adaptive / Personalized Learning"
    if any(k in label_lower for k in ["tutor", "socratic", "dialogue", "llm tutor"]):
        return "AI Tutoring"
    return "Other EdTech"


def load_graph_data():
    """Load nodes and edges from aive.db."""
    with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        nodes = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM nodes").fetchall()}
        edges = [dict(r) for r in conn.execute("SELECT * FROM edges").fetchall()]
        items = {r["id"]: dict(r) for r in conn.execute("SELECT id, type, title FROM items").fetchall()}
    return nodes, edges, items


# ── T33 — Theme Expansion Test ────────────────────────────────────────────────

def run_t33(nodes, edges, items):
    print(f"\n{'='*65}")
    print("T33 — THEME EXPANSION TEST")
    print(f"{'='*65}")
    print("Pass condition: top theme < 35% of total Problem nodes\n")

    problem_nodes = [n for n in nodes.values() if n["node_type"] == "Problem"]
    domain_counts = Counter()
    domain_examples = defaultdict(list)

    for node in problem_nodes:
        domain = _classify_domain(node["label"])
        domain_counts[domain] += 1
        if len(domain_examples[domain]) < 3:
            domain_examples[domain].append(node["label"])

    total = len(problem_nodes)
    print(f"Total Problem nodes: {total}\n")
    print(f"{'Domain':<35} {'Count':>5} {'%':>5}  {'Bar':<20}  Examples")
    print("-" * 100)

    top_theme_pct = 0
    for domain, count in domain_counts.most_common():
        pct = count / total * 100
        if pct > top_theme_pct:
            top_theme_pct = pct
        bar = "█" * min(count, 20)
        examples = ", ".join(domain_examples[domain][:2])[:45]
        print(f"{domain:<35} {count:>5} {pct:>4.0f}%  {bar:<20}  {examples}")

    unique_domains = len([d for d in domain_counts if d != "Other EdTech"])
    print(f"\nUnique named domains: {unique_domains}")
    print(f"Top theme concentration: {top_theme_pct:.0f}%")

    if top_theme_pct < 35:
        print("✅ PASS — Theme distribution is healthy")
    elif top_theme_pct < 50:
        print("⚠️  MODERATE — Still concentrated but improved")
    else:
        print("❌ FAIL — Graph still stuck in local optimum")

    return {"unique_domains": unique_domains, "top_theme_pct": top_theme_pct, "distribution": dict(domain_counts)}


# ── T34 — White Space Discovery ───────────────────────────────────────────────

def run_t34(nodes, edges, items):
    print(f"\n{'='*65}")
    print("T34 — WHITE SPACE DISCOVERY TEST")
    print(f"{'='*65}")
    print("Finding problems with strong evidence but sparse startup coverage\n")

    # For each Problem node, count:
    # - papers in source_items
    # - startups in source_items
    # - economic_signals in source_items
    # - edges to Buyer nodes (commercial grounding)
    import json as _json

    # Build buyer adjacency
    buyer_adjacent = defaultdict(set)
    for edge in edges:
        fn, tn = edge["from_node"], edge["to_node"]
        fn_node = nodes.get(fn, {})
        tn_node = nodes.get(tn, {})
        if fn_node.get("node_type") == "Buyer":
            buyer_adjacent[tn].add(fn)
        if tn_node.get("node_type") == "Buyer":
            buyer_adjacent[fn].add(tn)

    # Build economic signal adjacency
    econ_adjacent = defaultdict(set)
    for edge in edges:
        fn, tn = edge["from_node"], edge["to_node"]
        fn_node = nodes.get(fn, {})
        tn_node = nodes.get(tn, {})
        if fn_node.get("node_type") == "EconomicSignal":
            econ_adjacent[tn].add(fn)
        if tn_node.get("node_type") == "EconomicSignal":
            econ_adjacent[fn].add(tn)

    white_space_scores = []

    problem_nodes = [n for n in nodes.values() if n["node_type"] == "Problem"]
    for node in problem_nodes:
        sources = _json.loads(node.get("source_items") or "[]")
        paper_count   = sum(1 for s in sources if items.get(s, {}).get("type") == "paper")
        startup_count = sum(1 for s in sources if items.get(s, {}).get("type") == "startup")
        econ_count    = len(econ_adjacent.get(node["id"], set()))
        buyer_count   = len(buyer_adjacent.get(node["id"], set()))

        # White space score:
        # high papers + high signals + clear buyer - startup saturation
        evidence_strength = paper_count * 2 + econ_count * 3 + buyer_count * 2
        white_space = evidence_strength - (startup_count * 4)

        if paper_count >= 1:  # only include problems with at least 1 paper
            white_space_scores.append({
                "problem": node["label"],
                "domain": _classify_domain(node["label"]),
                "papers": paper_count,
                "startups": startup_count,
                "econ_signals": econ_count,
                "buyers": buyer_count,
                "evidence_strength": evidence_strength,
                "white_space_score": white_space,
            })

    # Sort by white space score descending
    white_space_scores.sort(key=lambda x: x["white_space_score"], reverse=True)

    print(f"{'Problem':<40} {'Domain':<25} {'Papers':>6} {'Startups':>8} {'Signals':>7} {'WS Score':>9}")
    print("-" * 100)

    top_white_space = []
    for entry in white_space_scores[:20]:
        ws = entry["white_space_score"]
        flag = "🔥" if ws >= 8 else ("✅" if ws >= 4 else "")
        prob = entry["problem"][:39]
        domain = entry["domain"][:24]
        print(f"{prob:<40} {domain:<25} {entry['papers']:>6} {entry['startups']:>8} {entry['econ_signals']:>7} {ws:>8.0f} {flag}")
        if ws >= 4:
            top_white_space.append(entry)

    high_ws = [e for e in white_space_scores if e["white_space_score"] >= 8]
    print(f"\nHigh white-space problems (score ≥ 8): {len(high_ws)}")
    print(f"Medium white-space problems (score ≥ 4): {len([e for e in white_space_scores if e['white_space_score'] >= 4])}")

    if high_ws:
        print(f"\n🔥 TOP FRONTIER OPPORTUNITIES:")
        for e in high_ws[:5]:
            print(f"   [{e['domain']}] {e['problem']}")
            print(f"      Papers: {e['papers']}  Startups: {e['startups']}  Signals: {e['econ_signals']}  WS Score: {e['white_space_score']}")

    return {"high_white_space": len(high_ws), "top_frontiers": [e["problem"] for e in high_ws[:5]]}


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading graph data from aive.db...")
    nodes, edges, items = load_graph_data()
    print(f"Nodes: {len(nodes)}  Edges: {len(edges)}  Items: {len(items)}")

    t33_result = run_t33(nodes, edges, items)
    t34_result = run_t34(nodes, edges, items)

    print(f"\n{'='*65}")
    print("COMBINED DIAGNOSIS")
    print(f"{'='*65}")
    print(f"Unique domains:         {t33_result['unique_domains']}")
    print(f"Top theme concentration: {t33_result['top_theme_pct']:.0f}%")
    print(f"High white-space zones: {t34_result['high_white_space']}")
    if t34_result['top_frontiers']:
        print(f"\nNext batch should prioritize these frontier problems:")
        for p in t34_result['top_frontiers']:
            print(f"  → {p}")
