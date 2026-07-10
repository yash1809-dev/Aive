"""
AIVE Live Test Runner
Tests T1 (Extraction), T3 (False Opportunity), T7 (Graph Quality) against the live system.
Run: python test_live.py
"""
import json
import sys
import sqlite3
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# ─── 0. Check Ollama is reachable ───────────────────────────────────────────
def check_ollama():
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        models = [m["name"] for m in data.get("models", [])]
        print(f"[OK] Ollama running. Models: {models}")
        return True
    except Exception as e:
        print(f"[FAIL] Ollama not reachable: {e}")
        print("       Start Ollama first: ollama serve")
        return False

# ─── 1. Check DB ─────────────────────────────────────────────────────────────
def check_db():
    db = ROOT / "data" / "aive.db"
    if not db.exists():
        print(f"[FAIL] aive.db not found at {db}")
        return None
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    items = conn.execute("SELECT type, COUNT(*) as n FROM items GROUP BY type").fetchall()
    nodes = conn.execute("SELECT COUNT(*) as n FROM nodes").fetchone()["n"]
    edges = conn.execute("SELECT COUNT(*) as n FROM edges").fetchone()["n"]
    opps  = conn.execute("SELECT COUNT(*) as n FROM opportunities").fetchone()["n"]
    survived = conn.execute("SELECT COUNT(*) as n FROM opportunities WHERE critic_verdict='survived'").fetchone()["n"]
    print(f"[OK] aive.db found")
    for row in items:
        print(f"     {row['type']}: {row['n']}")
    print(f"     nodes: {nodes}, edges: {edges}")
    print(f"     opportunities: {opps} total, {survived} survived critic")
    conn.close()
    return db

# ─── T1: Extraction Accuracy ─────────────────────────────────────────────────
def test_t1_extraction():
    print("\n" + "="*60)
    print("T1: EXTRACTION ACCURACY TEST")
    print("="*60)
    from agents.base import call_llm

    # LoRA paper excerpt (easy)
    lora_text = """We propose Low-Rank Adaptation, or LoRA, which freezes the pretrained 
    model weights and injects trainable rank decomposition matrices into each layer of the 
    Transformer architecture, greatly reducing the number of trainable parameters for 
    downstream tasks. LoRA reduces the number of trainable parameters by 10,000 times 
    and the GPU memory requirement by 3 times compared to GPT-3 fine-tuned with Adam."""

    expected_problem = "Fine-tuning large language models is prohibitively expensive"
    expected_technology = "Low-rank decomposition matrices injected into attention layers"

    prompt = f"""Extract the problem and technology from this text:

{lora_text}

Return JSON with keys: problem (str), technology (str)"""

    print("\nPaper: LoRA (easy)")
    try:
        extracted = call_llm(prompt, system="Return only valid JSON with keys: problem (str), technology (str)", agent="extractor")
        print(f"  Extracted problem   : {extracted.get('problem', 'N/A')[:100]}")
        print(f"  Expected problem    : {expected_problem}")
        print(f"  Extracted technology: {extracted.get('technology', 'N/A')[:100]}")
        print(f"  Expected technology : {expected_technology}")

        # Score manually
        prob_ok = any(kw in extracted.get('problem','').lower() for kw in ['expensive','cost','fine-tun','parameter','memory'])
        tech_ok = any(kw in extracted.get('technology','').lower() for kw in ['rank','decomposition','lora','adapter','matrix','matrices'])
        print(f"\n  Problem match: {'PASS' if prob_ok else 'FAIL'}")
        print(f"  Technology match: {'PASS' if tech_ok else 'FAIL'}")
        return prob_ok and tech_ok
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

# ─── T3: False Opportunity Rejection ─────────────────────────────────────────
def test_t3_false_opportunity():
    print("\n" + "="*60)
    print("T3: FALSE OPPORTUNITY REJECTION TEST")
    print("="*60)
    from agents.critic import critique

    nonsense_opps = [
        {
            "id": "test_false_001",
            "title": "Blockchain Attendance Platform",
            "problem": "Teacher attendance tracking in K-12 schools",
            "technology": "Blockchain distributed ledger",
            "market": "K-12 schools",
            "timing_signal": "Blockchain is trending",
            "reasoning": "Put attendance on blockchain for immutability",
            "evidence": "[]",
            "existing_competitors": "[]",
            "novelty_score": 5, "timing_score": 5, "market_score": 5,
            "feasibility": 5, "confidence_score": 5, "edge_confidence": 0.5,
            "source_papers": "[]", "source_patents": "[]", "source_startups": "[]",
        },
        {
            "id": "test_false_002",
            "title": "NFT Student Certificates",
            "problem": "Verifying academic credentials",
            "technology": "NFTs on Ethereum blockchain",
            "market": "Universities",
            "timing_signal": "NFTs are popular",
            "reasoning": "Issue diplomas as NFTs",
            "evidence": "[]",
            "existing_competitors": "[]",
            "novelty_score": 5, "timing_score": 5, "market_score": 5,
            "feasibility": 5, "confidence_score": 5, "edge_confidence": 0.5,
            "source_papers": "[]", "source_patents": "[]", "source_startups": "[]",
        },
    ]

    results = []
    for opp in nonsense_opps:
        print(f"\n  Testing: {opp['title']}")
        try:
            result = critique(opp)
            verdict = result.get("verdict", "unknown")
            summary = result.get("summary", "")[:80]
            print(f"  Verdict : {verdict}")
            print(f"  Summary : {summary}")
            results.append(verdict == "rejected")
        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append(False)

    passed = all(results)
    rejection_rate = sum(results) / len(results) if results else 0
    print(f"\n  Rejection rate: {rejection_rate:.0%} ({'PASS' if passed else 'FAIL'})")
    return passed

# ─── T7: Graph Quality ────────────────────────────────────────────────────────
def test_t7_graph_quality(db_path):
    print("\n" + "="*60)
    print("T7: GRAPH QUALITY TEST (sample 10 edges)")
    print("="*60)
    from agents.base import call_llm

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    edges = conn.execute("""
        SELECT e.id, e.relationship, n1.label as from_label, n2.label as to_label
        FROM edges e
        JOIN nodes n1 ON e.from_node = n1.id
        JOIN nodes n2 ON e.to_node = n2.id
        ORDER BY RANDOM() LIMIT 10
    """).fetchall()
    conn.close()

    if not edges:
        print("  [SKIP] No edges in graph")
        return None

    valid = 0
    total = 0
    for edge in edges:
        prompt = (f"Is this knowledge graph relationship semantically valid?\n"
                  f"{edge['from_label']} → {edge['relationship']} → {edge['to_label']}\n"
                  f"Return JSON: {{\"is_valid\": true/false, \"reasoning\": \"one sentence\"}}")
        try:
            result = call_llm(prompt, system="You are a knowledge graph validator. Return only valid JSON.", agent="extractor")
            is_valid = bool(result.get("is_valid", False))
            reasoning = result.get("reasoning", "")[:60]
            status = "✓" if is_valid else "✗"
            print(f"  {status} {edge['from_label'][:25]} → {edge['relationship'][:20]} → {edge['to_label'][:25]}")
            print(f"    {reasoning}")
            if is_valid:
                valid += 1
            total += 1
        except Exception as e:
            print(f"  [ERROR] edge {edge['id']}: {e}")
            total += 1

    precision = valid / total if total > 0 else 0
    passed = precision > 0.90
    print(f"\n  Edge precision: {valid}/{total} = {precision:.0%} ({'PASS >90%' if passed else 'FAIL <90%'})")
    return passed

# ─── T8: Show what's in the DB ────────────────────────────────────────────────
def show_opportunities(db_path):
    print("\n" + "="*60)
    print("CURRENT OPPORTUNITIES (survived critic)")
    print("="*60)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT title, problem, technology, market, 
               novelty_score, confidence_score, critic_verdict
        FROM opportunities 
        WHERE critic_verdict = 'survived'
        ORDER BY confidence_score DESC
        LIMIT 5
    """).fetchall()
    conn.close()

    if not rows:
        print("  No survived opportunities yet. Run: python agents/opportunity_finder.py")
        print("  Then: python agents/critic.py")
        return

    for i, row in enumerate(rows, 1):
        print(f"\n  #{i}: {row['title']}")
        print(f"       Problem    : {str(row['problem'])[:80]}")
        print(f"       Technology : {str(row['technology'])[:80]}")
        print(f"       Market     : {str(row['market'])[:60]}")
        print(f"       Scores     : novelty={row['novelty_score']} confidence={row['confidence_score']}")


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("AIVE LIVE TEST RUNNER")
    print("Testing: T1 Extraction | T3 False Opportunity | T7 Graph Quality")
    print()

    if not check_ollama():
        sys.exit(1)

    db = check_db()
    if not db:
        sys.exit(1)

    show_opportunities(db)

    t1 = test_t1_extraction()
    t3 = test_t3_false_opportunity()
    t7 = test_t7_graph_quality(db)

    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"  T1 Extraction Accuracy : {'PASS' if t1 else 'FAIL'}")
    print(f"  T3 False Opportunity   : {'PASS' if t3 else 'FAIL'}")
    print(f"  T7 Graph Quality       : {'PASS' if t7 else ('FAIL' if t7 is False else 'SKIP - no edges')}")
    print()
