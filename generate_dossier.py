"""
Generate an Opportunity Dossier for the top surviving opportunity.
Answers the 8 questions that determine if an opportunity is real.
Run: python generate_dossier.py
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from agents.base import call_llm

DB = ROOT / "data" / "aive.db"

DOSSIER_PROMPT = """You are a venture analyst. Write a rigorous opportunity dossier.

Opportunity data from AIVE knowledge graph:
{opportunity}

Graph context (related nodes and evidence):
{graph_context}

Answer ALL 8 questions with specifics. Be brutally honest. If you don't know something, say so explicitly.

Return JSON:
{{
  "opportunity_name": "...",
  "q1_problem": "What specific problem exists? Who experiences it daily? How painful is it (1-10)?",
  "q2_who_suffers": "Who suffers most? Give specific job titles, institutions, numbers affected.",
  "q3_who_pays": "Who writes the first cheque? Specific buyer type, budget line, procurement process.",
  "q4_why_now": "Why is this the right moment? Cite specific regulatory, economic, or technology changes.",
  "q5_regulation": "What regulation matters? How does it create urgency or constraint?",
  "q6_competitors": "Who are the existing competitors? What do they miss? Why would a buyer switch?",
  "q7_resources": "What does building this require? Capital, compute, data, talent, time.",
  "q8_kill_factors": "What 3 things could kill this opportunity? Be specific.",
  "overall_verdict": "In 2 sentences: is this worth pursuing? Why or why not?",
  "confidence": 0
}}
"""


def get_survived_opportunity():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT * FROM opportunities WHERE critic_verdict='survived'
        ORDER BY confidence_score DESC LIMIT 1
    """).fetchone()
    conn.close()
    return dict(row) if row else None


def get_graph_context(opp: dict) -> str:
    """Get related graph nodes for context."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    keywords = []
    for field in ("problem", "technology", "market"):
        val = str(opp.get(field, "") or "")
        if val:
            keywords.extend(val.lower().split()[:3])

    context_lines = []
    for kw in keywords[:5]:
        rows = conn.execute("""
            SELECT n1.label as from_label, n1.node_type as from_type,
                   e.relationship,
                   n2.label as to_label, n2.node_type as to_type,
                   e.evidence
            FROM edges e
            JOIN nodes n1 ON e.from_node = n1.id
            JOIN nodes n2 ON e.to_node = n2.id
            WHERE lower(n1.label) LIKE ? OR lower(n2.label) LIKE ?
            LIMIT 5
        """, (f"%{kw}%", f"%{kw}%")).fetchall()
        for r in rows:
            ev = json.loads(r["evidence"] or "[]")
            ev_str = ev[0][:60] if ev else ""
            context_lines.append(
                f"[{r['from_type']}] {r['from_label']} --{r['relationship']}--> "
                f"[{r['to_type']}] {r['to_label']} | evidence: {ev_str}"
            )
    conn.close()
    return "\n".join(context_lines[:20]) if context_lines else "No graph context found"


def generate_dossier(opp: dict) -> dict:
    graph_context = get_graph_context(opp)
    opp_summary = {
        "title": opp.get("title", ""),
        "problem": opp.get("problem", ""),
        "technology": opp.get("technology", ""),
        "market": opp.get("market", ""),
        "timing_signal": opp.get("timing_signal", ""),
        "reasoning": opp.get("reasoning", ""),
        "existing_competitors": json.loads(opp.get("existing_competitors", "[]") or "[]"),
        "novelty_score": opp.get("novelty_score"),
        "confidence_score": opp.get("confidence_score"),
    }
    prompt = DOSSIER_PROMPT.format(
        opportunity=json.dumps(opp_summary, indent=2),
        graph_context=graph_context,
    )
    try:
        result = call_llm(prompt, system="You are a rigorous venture analyst. Return only valid JSON.", agent="reasoner")
    except Exception:
        result = call_llm(prompt, system="You are a rigorous venture analyst. Return only valid JSON.", agent="extractor")
    return result


def print_dossier(dossier: dict, opp: dict):
    print("\n" + "="*70)
    print(f"OPPORTUNITY DOSSIER: {dossier.get('opportunity_name', opp.get('title', ''))}")
    print("="*70)

    questions = [
        ("Q1", "PROBLEM", "q1_problem"),
        ("Q2", "WHO SUFFERS", "q2_who_suffers"),
        ("Q3", "WHO PAYS", "q3_who_pays"),
        ("Q4", "WHY NOW", "q4_why_now"),
        ("Q5", "REGULATION", "q5_regulation"),
        ("Q6", "COMPETITORS", "q6_competitors"),
        ("Q7", "RESOURCES REQUIRED", "q7_resources"),
        ("Q8", "KILL FACTORS", "q8_kill_factors"),
    ]

    answered = 0
    for qid, label, key in questions:
        answer = dossier.get(key, "NOT ANSWERED")
        is_answered = answer and answer != "NOT ANSWERED" and len(str(answer)) > 20
        if is_answered:
            answered += 1
        print(f"\n{qid}: {label}")
        print(f"  {answer}")

    print(f"\n{'='*70}")
    print(f"VERDICT: {dossier.get('overall_verdict', 'N/A')}")
    print(f"Confidence: {dossier.get('confidence', 0)}/10")
    print(f"Questions answered: {answered}/8")
    print(f"{'='*70}")

    # Save to file
    out = ROOT / "data" / "exports" / "opportunity_dossier.md"
    lines = [
        f"# Opportunity Dossier: {dossier.get('opportunity_name', '')}",
        f"\n**Confidence:** {dossier.get('confidence', 0)}/10\n",
    ]
    for qid, label, key in questions:
        lines.append(f"\n## {qid}: {label}")
        lines.append(str(dossier.get(key, "N/A")))
    lines.append(f"\n## VERDICT")
    lines.append(str(dossier.get('overall_verdict', 'N/A')))
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nDossier saved: {out}")


if __name__ == "__main__":
    opp = get_survived_opportunity()
    if not opp:
        print("No survived opportunities. Run opportunity_finder.py + critic.py first.")
        sys.exit(1)

    print(f"Generating dossier for: {opp.get('title', '')}")
    dossier = generate_dossier(opp)
    print_dossier(dossier, opp)
