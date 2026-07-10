"""Week 4 — Critic Engine. Most ideas should die."""

import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.base import call_llm
from db.init_db import DB_PATH

CRITIC_PROMPT = """You are AIVE Critic. Your job is to KILL bad opportunities.

Be ruthless. Most ideas should die. Only survivors should be non-obvious, feasible, and timely.

Evaluate this opportunity:

{opportunity}

Answer ALL critic categories. Return JSON only:
{{
  "verdict": "survived" or "rejected",
  "already_exists": {{ "answer": true/false, "note": "..." }},
  "too_crowded": {{ "answer": true/false, "note": "..." }},
  "too_early": {{ "answer": true/false, "note": "..." }},
  "no_customer": {{ "answer": true/false, "note": "..." }},
  "technically_hard": {{ "answer": true/false, "note": "..." }},
  "distribution_problem": {{ "answer": true/false, "note": "..." }},
  "summary": "One sentence — why it survived or died",
  "kill_reasons": ["reason 1", "reason 2"]
}}

Rules:
- REJECT if already_exists AND too_crowded
- REJECT if no_customer
- REJECT if technically_hard AND too_early
- REJECT if generic "AI in education" with no specific intersection
- REJECT duplicates of obvious products (Khanmigo clone, another LMS)
- SURVIVE only if: non-obvious cross-domain connection + evidence + clear timing + feasible in 12 months
- Target: reject 70%+ of opportunities. When in doubt, reject.
"""


def get_pending() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, title, problem, technology, market, timing_signal,
                   reasoning, evidence, existing_competitors,
                   novelty_score, timing_score, market_score, feasibility,
                   confidence_score, edge_confidence,
                   source_papers, source_patents, source_startups
            FROM opportunities
            WHERE critic_verdict = 'pending' OR critic_verdict IS NULL
            ORDER BY confidence_score DESC, novelty_score DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def critique(opp: dict) -> dict:
    payload = {
        **opp,
        "existing_competitors": _parse_json(opp.get("existing_competitors")),
        "evidence": _parse_json(opp.get("evidence")),
        "source_papers": _parse_json(opp.get("source_papers")),
        "source_patents": _parse_json(opp.get("source_patents")),
        "source_startups": _parse_json(opp.get("source_startups")),
    }
    try:
        result = call_llm(
            CRITIC_PROMPT.format(opportunity=json.dumps(payload, indent=2)),
            system="You are a skeptical venture critic. Kill weak ideas. Return valid JSON only.",
            agent="reasoner",
        )
    except Exception:
        result = call_llm(
            CRITIC_PROMPT.format(opportunity=json.dumps(payload, indent=2)),
            system="You are a skeptical venture critic. Kill weak ideas. Return valid JSON only.",
            agent="extractor",
        )
    return result


def _parse_json(raw) -> list:
    try:
        return json.loads(raw) if raw else []
    except (json.JSONDecodeError, TypeError):
        return []


def save_verdict(opp_id: str, result: dict) -> None:
    verdict = result.get("verdict", "rejected")
    notes = json.dumps(result, indent=2)
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE opportunities SET critic_verdict=?, critic_notes=?, created_at=COALESCE(created_at, ?)
            WHERE id=?
            """,
            (verdict, notes, now, opp_id),
        )
        if verdict == "rejected":
            conn.execute(
                """
                INSERT OR REPLACE INTO rejected_ideas (id, opportunity_id, reason, rejected_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    f"rej_{uuid.uuid4().hex[:8]}",
                    opp_id,
                    result.get("summary", "Rejected by critic"),
                    now,
                ),
            )


def run() -> dict:
    pending = get_pending()
    if not pending:
        print("No pending opportunities.")
        return {"total": 0, "survived": 0, "rejected": 0}

    survived, rejected = [], []
    for opp in pending:
        print(f"Criticizing: {opp['title'][:60]}...")
        result = critique(opp)
        save_verdict(opp["id"], result)
        entry = {"id": opp["id"], "title": opp["title"], **result}
        if result.get("verdict") == "survived":
            survived.append(entry)
            print(f"  SURVIVED -- {result.get('summary', '')[:80]}")
        else:
            rejected.append(entry)
            print(f"  REJECTED -- {result.get('summary', '')[:80]}")

    out = ROOT / "data" / "exports" / "critic_results.json"
    out.write_text(
        json.dumps({"survived": survived, "rejected": rejected}, indent=2),
        encoding="utf-8",
    )

    total = len(pending)
    kill_rate = len(rejected) / total * 100 if total else 0
    print(f"\nTotal: {total} | Survived: {len(survived)} | Rejected: {len(rejected)} | Kill rate: {kill_rate:.0f}%")
    print(f"Saved: {out}")
    return {"total": total, "survived": len(survived), "rejected": len(rejected), "kill_rate": kill_rate}


def main():
    run()


if __name__ == "__main__":
    main()
