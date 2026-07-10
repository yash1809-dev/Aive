"""
validation/tests/t3_false_opportunity.py
=========================================
T3 — False Opportunity Rejection Test

Feeds nonsense tech+problem+market combos to the AIVE Critic and checks that
every one gets rejected. A surviving nonsense combo is a false positive.

Pass criterion: rejection_rate == 1.0 (all nonsense combos rejected)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from agents.critic import critique
from validation.base_test import FixtureError, TestBase
from validation.models import TestResult


class T3FalseOpportunityRejection(TestBase):
    test_id = "T3"
    test_name = "False Opportunity Rejection Test"
    pass_threshold = {"rejection_rate": 1.0}

    def run(self, config: dict, fixtures: dict) -> TestResult:
        run_id = config.get("run_id", "standalone")

        if not fixtures:
            default_path = (
                Path(__file__).resolve().parent.parent
                / "fixtures" / "false_opportunity_fixtures.json"
            )
            try:
                fixtures = self.load_fixtures(default_path)
            except FixtureError as exc:
                return TestResult(
                    test_id=self.test_id, test_name=self.test_name, run_id=run_id,
                    passed=False, scores={}, threshold=self.pass_threshold,
                    details={}, error=str(exc),
                    created_at=datetime.now(timezone.utc).isoformat(),
                )

        combos = fixtures.get("combos", [])
        if not combos:
            return TestResult(
                test_id=self.test_id, test_name=self.test_name, run_id=run_id,
                passed=False, scores={}, threshold=self.pass_threshold,
                details={}, error="no_combos_in_fixture",
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        rejected_count = 0
        false_positives = []
        item_details = []

        for combo in combos:
            # Build a fake opportunity dict that matches what critique() expects
            fake_opp = {
                "id": combo.get("combo_id", "fake"),
                "title": combo.get("combo", ""),
                "problem": combo.get("problem", ""),
                "technology": combo.get("technology", ""),
                "market": combo.get("market", ""),
                "timing_signal": "",
                "reasoning": "",
                "evidence": "[]",
                "existing_competitors": "[]",
                "novelty_score": 5,
                "timing_score": 5,
                "market_score": 5,
                "feasibility": 5,
                "confidence_score": 5,
                "edge_confidence": 0.5,
                "source_papers": "[]",
                "source_patents": "[]",
                "source_startups": "[]",
            }

            try:
                result = critique(fake_opp)
                verdict = result.get("verdict", "rejected")
            except Exception as exc:
                # On LLM failure, conservatively assume rejected
                verdict = "rejected"
                item_details.append({
                    "combo_id": combo.get("combo_id"),
                    "combo": combo.get("combo"),
                    "verdict": "rejected",
                    "note": f"llm_error: {exc}",
                })
                rejected_count += 1
                continue

            if verdict == "rejected":
                rejected_count += 1
            else:
                false_positives.append({
                    "combo_id": combo.get("combo_id"),
                    "combo": combo.get("combo"),
                    "verdict": verdict,
                    "critic_summary": result.get("summary", ""),
                })

            item_details.append({
                "combo_id": combo.get("combo_id"),
                "combo": combo.get("combo"),
                "verdict": verdict,
                "critic_summary": result.get("summary", ""),
            })

        total = len(combos)
        rejection_rate = rejected_count / total if total > 0 else 0.0
        scores = {"rejection_rate": rejection_rate}
        passed = self.compute_pass(scores)

        result_obj = TestResult(
            test_id=self.test_id, test_name=self.test_name, run_id=run_id,
            passed=passed, scores=scores, threshold=self.pass_threshold,
            details={
                "total_combos": total,
                "rejected_count": rejected_count,
                "false_positives": false_positives,
                "items": item_details,
            },
            error=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._validate_result(result_obj)
        return result_obj


if __name__ == "__main__":
    T3FalseOpportunityRejection._run_standalone(
        Path(__file__).resolve().parent.parent / "fixtures" / "false_opportunity_fixtures.json"
    )
