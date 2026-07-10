"""
agents/concept_extractor.py
============================
Concept Extraction Agent — extracts named concepts from an already-extracted item.

Takes the raw item fields (problem, technology, solution, keywords, industry, beneficiaries)
and produces a structured list of typed concept nodes with rich relationship hints.

Output per item:
{
  "concepts": [
    {"label": "Knowledge Tracing", "type": "Technology"},
    {"label": "Teacher Grading Workload", "type": "Problem"},
    {"label": "K-12 School Districts", "type": "Customer"},
    ...
  ],
  "relationships": [
    {"from": "Knowledge Tracing", "relation": "solves", "to": "Teacher Grading Workload"},
    {"from": "Knowledge Tracing", "relation": "purchased_by", "to": "K-12 School Districts"},
    ...
  ]
}
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.base import call_llm
from db.init_db import DB_PATH

# ── Valid node types ──────────────────────────────────────────────────────────
NODE_TYPES = {
    "Problem",          # A pain point, gap, or challenge
    "Technology",       # A named technique, model, system, or method
    "Capability",       # A functional ability a technology provides
    "Workflow",         # A named task or process people do (e.g. Essay Grading, Lesson Planning)
    "User",             # Who uses the product day-to-day
    "Buyer",            # Who writes the cheque (may differ from User)
    "Organization",     # A specific type of institution (e.g. K-12 School District, University)
    "Competitor",       # An existing named product or approach
    "Constraint",       # A technical or resource limitation
    "Regulation",       # A law, policy, or compliance requirement (e.g. FERPA, EU AI Act)
    "EconomicSignal",   # A market force driving timing (e.g. Teacher Shortage, Inference Cost Drop)
    "Outcome",          # A measurable result or benefit
    "Resource",         # What the opportunity requires: Capital, Compute, Talent, Data
}

# ── Valid relationship types ──────────────────────────────────────────────────
RELATION_TYPES = {
    "solves",               # Technology/Capability solves Problem
    "improves",             # Technology improves Workflow
    "benefits",             # Technology/Outcome benefits User
    "purchased_by",         # Technology purchased_by Buyer
    "used_by",              # Technology used_by User
    "deployed_in",          # Technology deployed_in Organization
    "constrained_by",       # Technology/Market constrained_by Constraint/Regulation
    "enabled_by",           # Technology enabled_by another Technology/Capability
    "competes_with",        # Technology competes_with Competitor
    "produces",             # Technology produces Outcome
    "signals",              # EconomicSignal signals opportunity timing
    "regulated_by",         # Technology/Workflow regulated_by Regulation
    "requires_resource",    # Technology/Opportunity requires_resource Resource
}

CONCEPT_PROMPT = """You are building an Innovation Knowledge Graph that models economic reality, not documents.

Your job: extract NAMED CONCEPTS and PRECISE RELATIONSHIPS from this item.

NODE TYPE RULES — pick the most specific type:
- Problem: A pain point or gap (e.g. "Teacher Grading Workload", "Cold-Start Knowledge Tracing")
- Technology: A named technique/model/system (e.g. "LoRA Fine-Tuning", "Bayesian Knowledge Tracing")
- Capability: A functional ability (e.g. "Offline Inference", "Real-Time Feedback")
- Workflow: A named task people perform (e.g. "Essay Grading", "IEP Generation", "Lesson Planning")
- User: Who uses it day-to-day (e.g. "Students", "Teachers")
- Buyer: Who writes the cheque (e.g. "School District", "University IT Department")
- Organization: Institution type (e.g. "K-12 School", "EdTech Vendor", "Community College")
- Competitor: An existing named product (e.g. "Khanmigo", "MagicSchool", "Duolingo")
- Constraint: A technical/resource limit (e.g. "Limited Internet Access", "GPU Memory Cost")
- Regulation: A law or policy (e.g. "FERPA", "EU AI Act", "COPPA")
- EconomicSignal: A market force driving timing (e.g. "Teacher Shortage", "LLM Cost Drop")
- Outcome: A measurable result (e.g. "50% Grading Time Saved", "Improved Test Scores")
- Resource: What the opportunity requires (e.g. "GPU Compute", "Training Data", "Teacher Time")

IMPORTANT BALANCE RULE: For every 2 Technology nodes, extract at least 1 Buyer/User AND 1 Constraint/Regulation/EconomicSignal.
If you cannot identify these, the technology may not yet be commercially relevant — note that honestly.

CONCEPT LABEL RULES:
- 1-4 words maximum. No sentences.
- Use canonical names: "Knowledge Tracing" not "The system that models student knowledge over time"
- Use "Teacher Grading Workload" not "The administrative burden faced by teachers when grading"

RELATIONSHIP RULES — only use these verbs:
- solves: Technology/Capability solves Problem
- improves: Technology improves Workflow  
- benefits: Technology benefits User
- purchased_by: Technology purchased_by Buyer
- used_by: Technology used_by User
- deployed_in: Technology deployed_in Organization
- constrained_by: Technology/Workflow constrained_by Constraint/Regulation
- enabled_by: Technology enabled_by Technology/Capability
- competes_with: Technology competes_with Competitor
- produces: Technology produces Outcome
- signals: EconomicSignal signals timing for Technology/Problem
- regulated_by: Technology/Workflow regulated_by Regulation
- requires_resource: Technology/Workflow requires_resource Resource

EVIDENCE ANCHORING RULE:
Every concept must include the exact phrase from the source that supports it.
This prevents hallucination.

Item to analyze:
Title: {title}
Type: {item_type}
Problem: {problem}
Technology: {technology}
Solution: {solution}
Keywords: {keywords}
Industry: {industry}
Beneficiaries: {beneficiaries}

Return ONLY valid JSON:
{{
  "concepts": [
    {{
      "label": "Short Concept Name",
      "type": "Problem|Technology|Capability|Workflow|User|Buyer|Organization|Competitor|Constraint|Regulation|EconomicSignal|Outcome|Resource",
      "evidence": "exact phrase from source that supports this concept"
    }}
  ],
  "relationships": [
    {{
      "from": "Concept A",
      "relation": "solves|improves|benefits|purchased_by|used_by|deployed_in|constrained_by|enabled_by|competes_with|produces|signals|regulated_by",
      "to": "Concept B",
      "evidence": "exact phrase from source supporting this relationship"
    }}
  ]
}}

Extract 5-10 concepts and 4-8 relationships. Quality over quantity. Only include concepts directly evidenced in the source.
"""


def extract_concepts(item: dict) -> dict:
    """Extract typed concepts and relationships from one item."""
    prompt = CONCEPT_PROMPT.format(
        title=item.get("title", ""),
        item_type=item.get("type", ""),
        problem=item.get("problem", ""),
        technology=item.get("technology", ""),
        solution=item.get("solution", ""),
        keywords=item.get("keywords", ""),
        industry=item.get("industry", ""),
        beneficiaries=item.get("beneficiaries", ""),
    )
    try:
        result = call_llm(prompt, system="You are a knowledge graph ontologist. Return only valid JSON.", agent="reasoner")
    except Exception:
        result = call_llm(prompt, system="You are a knowledge graph ontologist. Return only valid JSON.", agent="extractor")

    # Validate and filter — enforce evidence anchoring
    concepts = []
    for c in result.get("concepts", []):
        label = str(c.get("label", "")).strip()
        ctype = str(c.get("type", "")).strip()
        evidence = str(c.get("evidence", "")).strip()
        if label and ctype in NODE_TYPES and len(label) <= 60:
            concepts.append({"label": label, "type": ctype, "evidence": evidence})

    relationships = []
    for r in result.get("relationships", []):
        frm = str(r.get("from", "")).strip()
        rel = str(r.get("relation", "")).strip()
        to = str(r.get("to", "")).strip()
        evidence = str(r.get("evidence", "")).strip()
        if frm and rel and to and rel in RELATION_TYPES and frm != to:
            # ── Semantic coherence check ──────────────────────────────────────
            # Reject relationships between concepts from unrelated domains.
            # "evidence" must contain at least one token that appears in
            # either the from-label or to-label — this catches hallucinated
            # cross-domain edges like "Genetic Algorithms → benefits →
            # Traditional Chinese Medicine Clinicians" where neither concept
            # appears in the source evidence phrase.
            if evidence:
                frm_tokens = set(w.lower() for w in frm.split() if len(w) > 2)
                to_tokens  = set(w.lower() for w in to.split()  if len(w) > 2)
                ev_lower   = evidence.lower()
                # At least one token from either label must appear in evidence
                has_anchor = any(t in ev_lower for t in frm_tokens | to_tokens)
                if not has_anchor:
                    continue  # skip hallucinated cross-domain edge
            relationships.append({"from": frm, "relation": rel, "to": to, "evidence": evidence})

    return {"concepts": concepts, "relationships": relationships}


def get_extracted_items() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, title, type, problem, technology, solution,
                   keywords, industry, beneficiaries
            FROM items WHERE extraction_status = 'done'
        """).fetchall()
    return [dict(r) for r in rows]


def run() -> list[dict]:
    items = get_extracted_items()
    if not items:
        print("No extracted items found. Run agents first.")
        return []

    # Cache to avoid re-running LLM on every rebuild
    cache_path = ROOT / "data" / "concept_cache.json"

    if cache_path.exists():
        import json as _json
        cached = _json.loads(cache_path.read_text(encoding="utf-8"))
        cached_ids = {r["item_id"] for r in cached}
        new_items = [i for i in items if i["id"] not in cached_ids]
        if not new_items:
            print(f"Using cached concepts for all {len(cached)} items (delete data/concept_cache.json to re-extract)")
            return cached
        print(f"Using cache for {len(cached)} items, extracting {len(new_items)} new items...")
        results = cached
        items_to_process = new_items
    else:
        results = []
        items_to_process = items
        print(f"Extracting concepts from {len(items_to_process)} items...")

    for item in items_to_process:
        title = item.get("title", "")[:60]
        print(f"  {title}...")
        try:
            result = extract_concepts(item)
            result["item_id"] = item["id"]
            result["item_type"] = item["type"]
            results.append(result)
        except Exception as e:
            print(f"  [ERROR] {e}")

    # Save cache
    import json as _json
    cache_path.write_text(_json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return results


if __name__ == "__main__":
    results = run()
    print(f"\nExtracted concepts from {len(results)} items")
    # Show sample
    for r in results[:3]:
        print(f"\n  Item: {r['item_id']}")
        for c in r["concepts"]:
            print(f"    [{c['type']}] {c['label']}")
        for rel in r["relationships"]:
            print(f"    {rel['from']} --{rel['relation']}--> {rel['to']}")
