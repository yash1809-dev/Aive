"""
validation/tests/t9_commercialization.py
==========================================
T9 — Commercial Intelligence Test

Loads all opportunities from data/aive.db (regardless of critic verdict)
and asks the LLM four commercial intelligence questions per opportunity:

  1. Buyer identification — who writes the first cheque?
  2. Adoption chain      — User → Influencer → Decision Maker → Buyer
  3. Competitor reality  — Incumbents, substitutes, workarounds
  4. Resource estimate   — Capital, Compute, Talent, Time to MVP

Pass criteria:
  buyer_identification_rate  >= 0.70   (identifies buyer in ≥70% of opportunities)
  adoption_chain_rate        >= 0.50   (maps full chain in ≥50%)
  competitor_rate            >= 0.60   (names ≥1 real competitor in ≥60%)

Standalone execution:
    python validation/tests/t9_commercialization.py
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from agents.base import call_llm
from validation.base_test import TestBase
from validation.models import TestResult

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / "data" / "aive.db"

_SYSTEM = (
    "You are a commercial intelligence analyst. "
    "Return only valid JSON. Be specific — name real companies, roles, dollar amounts. "
    "Vague answers like 'schools' or 'companies' score zero."
)

_PROMPT = """Evaluate this opportunity for commercial viability.

Opportunity:
Title: {title}
Problem: {problem}
Technology: {technology}
Market: {market}
Existing competitors: {competitors}

Answer all four sections. Return JSON:
{{
  "buyer": {{
    "identified": true/false,
    "who_pays": "specific role/org that writes the first cheque",
    "budget_source": "where the money comes from (budget line, fund, etc.)"
  }},
  "adoption_chain": {{
    "complete": true/false,
    "user": "...",
    "influencer": "...",
    "decision_maker": "...",
    "buyer": "..."
  }},
  "competitive_reality": {{
    "has_incumbents": true/false,
    "incumbents": ["..."],
    "substitutes": ["..."],
    "workarounds": ["what customers do today without this product"]
  }},
  "resource_estimate": {{
    "capital_to_mvp": "e.g. $150K–$300K",
    "compute_cost_monthly": "e.g. $2K/month",
    "talent_needed": ["e.g. ML engineer", "edtech sales lead"],
    "months_to_mvp": 6
  }}
}}"""


def _load_opportunities() -> list[dict]:
    """Load all opportunities from aive.db (read-only)."""
    uri = f"file:{DB_PATH}?mode=ro"
    query = """
        SELECT id, title, problem, technology, market,
               critic_verdict, existing_competitors,
               novelty_score, timing_score, market_score, feasibility
        FROM opportunities
        ORDER BY confidence_score DESC
    """
    with sqlite3.connect(uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query).fetchall()
    return [dict(r) for r in rows]


def _score_result(raw: dict) -> dict:
    """
    Extract boolean flags from an LLM commercial intelligence response.

    Adoption chain is scored by field presence, NOT the model's self-reported
    'complete' flag. The model consistently returns complete=false even when
    it populates all four fields — so we inspect the actual content instead.
    A field counts as populated when it's a non-empty string longer than 5 chars.
    """
    buyer_identified = bool(raw.get("buyer", {}).get("identified", False))
    has_incumbents   = bool(raw.get("competitive_reality", {}).get("has_incumbents", False))

    chain = raw.get("adoption_chain", {})
    _MIN_LEN = 5  # minimum chars for a field to be considered populated

    def _populated(val) -> bool:
        return isinstance(val, str) and len(val.strip()) > _MIN_LEN

    chain_complete = (
        _populated(chain.get("user", ""))
        and _populated(chain.get("influencer", ""))
        and _populated(chain.get("decision_maker", ""))
        and _populated(chain.get("buyer", ""))
    )

    return {
        "buyer_identified": buyer_identified,
        "adoption_chain_complete": chain_complete,
        "has_competitors": has_incumbents,
        "raw": raw,
    }


class T9CommercialIntelligence(TestBase):
    test_id = "T9"
    test_name = "Commercial Intelligence Test"
    pass_threshold = {
        "buyer_identification_rate": 0.70,
        "adoption_chain_rate": 0.50,
        "competitor_rate": 0.60,
    }

    def run(self, config: dict, fixtures: dict) -> TestResult:
        run_id = config.get("run_id", "standalone")

        try:
            opportunities = _load_opportunities()
        except Exception as exc:
            return TestResult(
                test_id=self.test_id, test_name=self.test_name, run_id=run_id,
                passed=False, scores={}, threshold=self.pass_threshold,
                details={}, error=f"db_load_failed: {exc}",
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        if not opportunities:
            return TestResult(
                test_id=self.test_id, test_name=self.test_name, run_id=run_id,
                passed=False, scores={}, threshold=self.pass_threshold,
                details={}, error="no_opportunities_in_db",
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        print(f"   Evaluating commercial intelligence for {len(opportunities)} opportunities ...")

        verdicts = []
        buyer_hits = 0
        chain_hits = 0
        competitor_hits = 0
        error_count = 0

        for opp in opportunities:
            prompt = _PROMPT.format(
                title=opp.get("title", ""),
                problem=opp.get("problem", ""),
                technology=opp.get("technology", ""),
                market=opp.get("market", ""),
                competitors=opp.get("existing_competitors", "unknown"),
            )

            try:
                raw = call_llm(prompt, system=_SYSTEM, agent="reasoner")
            except Exception:
                try:
                    raw = call_llm(prompt, system=_SYSTEM, agent="extractor")
                except Exception as exc:
                    error_count += 1
                    verdicts.append({
                        "id": opp["id"],
                        "title": opp.get("title", ""),
                        "critic_verdict": opp.get("critic_verdict", ""),
                        "error": str(exc),
                    })
                    continue

            scored = _score_result(raw)
            if scored["buyer_identified"]:
                buyer_hits += 1
            if scored["adoption_chain_complete"]:
                chain_hits += 1
            if scored["has_competitors"]:
                competitor_hits += 1

            verdicts.append({
                "id": opp["id"],
                "title": opp.get("title", ""),
                "critic_verdict": opp.get("critic_verdict", ""),
                "buyer_identified": scored["buyer_identified"],
                "adoption_chain_complete": scored["adoption_chain_complete"],
                "has_competitors": scored["has_competitors"],
                "buyer": raw.get("buyer", {}),
                "adoption_chain": raw.get("adoption_chain", {}),
                "competitive_reality": raw.get("competitive_reality", {}),
                "resource_estimate": raw.get("resource_estimate", {}),
            })

        total = len(opportunities)
        evaluated = total - error_count

        buyer_rate      = buyer_hits / evaluated if evaluated else 0.0
        chain_rate      = chain_hits / evaluated if evaluated else 0.0
        competitor_rate = competitor_hits / evaluated if evaluated else 0.0

        scores = {
            "buyer_identification_rate": buyer_rate,
            "adoption_chain_rate": chain_rate,
            "competitor_rate": competitor_rate,
        }
        passed = self.compute_pass(scores)

        result = TestResult(
            test_id=self.test_id, test_name=self.test_name, run_id=run_id,
            passed=passed, scores=scores, threshold=self.pass_threshold,
            details={
                "total_opportunities": total,
                "evaluated": evaluated,
                "error_count": error_count,
                "buyer_hits": buyer_hits,
                "chain_hits": chain_hits,
                "competitor_hits": competitor_hits,
                "commercialization_verdicts": verdicts,
            },
            error=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._validate_result(result)
        return result


if __name__ == "__main__":
    t = T9CommercialIntelligence()
    result = t.run({"run_id": "standalone"}, {})
    print(json.dumps({
        "test_id": result.test_id,
        "passed": result.passed,
        "scores": result.scores,
        "threshold": result.threshold,
        "total_opportunities": result.details.get("total_opportunities"),
        "buyer_hits": result.details.get("buyer_hits"),
        "chain_hits": result.details.get("chain_hits"),
        "competitor_hits": result.details.get("competitor_hits"),
        "error": result.error,
        "sample_verdicts": result.details.get("commercialization_verdicts", [])[:3],
    }, indent=2))
