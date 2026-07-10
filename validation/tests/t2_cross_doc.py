"""
validation/tests/t2_cross_doc.py
=================================
T2 — Cross-Document Reasoning Test

Feeds a multi-source pack (paper + paper + patent + startup) through AIVE's
opportunity finder logic and asks: does the resulting opportunity say something
that no single source would yield alone?

Pass criterion: non_obvious_score > 7.0
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from agents.base import call_llm
from validation.base_test import FixtureError, TestBase
from validation.models import TestResult

_SYSTEM = (
    "You are a research synthesis evaluator. Return only valid JSON. "
    "Be strict — a score above 7 means genuinely non-obvious cross-domain insight."
)

_EVAL_PROMPT = """Given this multi-source opportunity and the human-panel baseline, 
rate how non-obvious the opportunity is on a scale 0-10.

Human panel baseline:
{baseline}

AIVE-generated opportunity:
{opportunity}

Return JSON:
{{
  "non_obvious_score": <float 0-10>,
  "reasoning": "<1-2 sentences explaining your score>"
}}
"""


class T2CrossDocReasoning(TestBase):
    test_id = "T2"
    test_name = "Cross-Document Reasoning Test"
    pass_threshold = {"non_obvious_score": 7.0}

    def run(self, config: dict, fixtures: dict) -> TestResult:
        run_id = config.get("run_id", "standalone")

        if not fixtures:
            default_path = (
                Path(__file__).resolve().parent.parent
                / "fixtures" / "cross_doc_fixtures.json"
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

        packs = fixtures.get("packs", [])
        if not packs:
            return TestResult(
                test_id=self.test_id, test_name=self.test_name, run_id=run_id,
                passed=False, scores={}, threshold=self.pass_threshold,
                details={}, error="no_fixture_packs",
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        pack = packs[0]
        baseline = pack.get("human_panel_baseline", "")
        sources = pack.get("sources", {})

        # Synthesise all source key_insights into a combined summary for the LLM
        combined_insights = "\n".join(
            f"- [{k}] {v.get('key_insight', '')}"
            for k, v in sources.items()
        )

        # Generate opportunity by asking LLM to synthesise the sources
        synth_prompt = (
            "You are an opportunity analyst. Given these insights from different sources, "
            "describe the cross-domain opportunity that emerges:\n\n"
            f"{combined_insights}\n\n"
            "Return JSON: {\"title\": str, \"problem\": str, \"technology\": str, "
            "\"market\": str, \"reasoning\": str}"
        )

        try:
            generated = call_llm(synth_prompt, system="Return only valid JSON.", agent="reasoner")
        except Exception:
            try:
                generated = call_llm(synth_prompt, system="Return only valid JSON.", agent="extractor")
            except Exception as exc:
                return TestResult(
                    test_id=self.test_id, test_name=self.test_name, run_id=run_id,
                    passed=False, scores={}, threshold=self.pass_threshold,
                    details={}, error=f"llm_failed: {exc}",
                    created_at=datetime.now(timezone.utc).isoformat(),
                )

        # Evaluate non-obviousness
        eval_prompt = _EVAL_PROMPT.format(
            baseline=baseline,
            opportunity=str(generated),
        )
        try:
            eval_result = call_llm(eval_prompt, system=_SYSTEM, agent="reasoner")
        except Exception:
            try:
                eval_result = call_llm(eval_prompt, system=_SYSTEM, agent="extractor")
            except Exception as exc:
                return TestResult(
                    test_id=self.test_id, test_name=self.test_name, run_id=run_id,
                    passed=False, scores={}, threshold=self.pass_threshold,
                    details={}, error=f"eval_llm_failed: {exc}",
                    created_at=datetime.now(timezone.utc).isoformat(),
                )

        score = float(eval_result.get("non_obvious_score", 0.0))
        score = max(0.0, min(10.0, score))
        reasoning = str(eval_result.get("reasoning", ""))

        scores = {"non_obvious_score": score}
        passed = self.compute_pass(scores)

        result = TestResult(
            test_id=self.test_id, test_name=self.test_name, run_id=run_id,
            passed=passed, scores=scores, threshold=self.pass_threshold,
            details={
                "generated_opportunity": generated,
                "human_panel_baseline": baseline,
                "evaluator_reasoning": reasoning,
            },
            error=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._validate_result(result)
        return result


if __name__ == "__main__":
    T2CrossDocReasoning._run_standalone(
        Path(__file__).resolve().parent.parent / "fixtures" / "cross_doc_fixtures.json"
    )
