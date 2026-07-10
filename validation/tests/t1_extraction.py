"""
validation/tests/t1_extraction.py
===================================
T1 — Extraction Accuracy Test

Evaluates how accurately the AIVE analyst agents extract ``problem`` and
``technology`` fields from source documents, and measures hallucination rate.

Pass criteria (Requirement 5):
    avg_problem_accuracy    > 8.5
    avg_technology_accuracy > 8.5
    total_hallucinations    < 5   (tracked as "_max" threshold)

Concurrency:
    Uses asyncio with a Semaphore(3) to cap simultaneous LLM calls at 3,
    preventing overload of the local Ollama inference server.

Standalone execution:
    python validation/tests/t1_extraction.py
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.base import call_llm
from validation.base_test import FixtureError, TestBase
from validation.evaluators.extraction_eval import ExtractionEvaluator
from validation.models import ExtractionGroundTruth, TestResult


class T1ExtractionAccuracy(TestBase):
    """T1 — Extraction Accuracy Test."""

    test_id = "T1"
    test_name = "Extraction Accuracy Test"
    pass_threshold = {
        "avg_problem_accuracy": 8.5,
        "avg_technology_accuracy": 8.5,
        "total_hallucinations_max": 5.0,
    }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _evaluate_item(
        sem: asyncio.Semaphore,
        evaluator: ExtractionEvaluator,
        item: dict,
    ) -> dict[str, Any]:
        """
        Simulate extraction for one fixture item then score it.

        Returns a result dict containing either ``score`` (ExtractionScore)
        or ``error`` (str) plus the original ``item_id``.
        """
        item_id = item.get("item_id", "unknown")

        async with sem:
            # Build extraction prompt from raw_text
            raw_text = item.get("raw_text", "")
            extraction_prompt = (
                f"Extract the problem and technology from this text: {raw_text}"
            )
            extraction_system = (
                "Return only valid JSON with keys: problem (str), technology (str)"
            )

            # Simulate extraction via LLM (mimics what research analyst would produce)
            try:
                extracted = await asyncio.to_thread(
                    call_llm,
                    extraction_prompt,
                    extraction_system,
                    "extractor",
                )
            except Exception as exc:
                # Retry once with agent="extractor" as per Requirement 5.6
                try:
                    extracted = await asyncio.to_thread(
                        call_llm,
                        extraction_prompt,
                        extraction_system,
                        "extractor",
                    )
                except Exception as retry_exc:
                    return {"item_id": item_id, "error": str(retry_exc)}

            # Build ExtractionGroundTruth from fixture item
            ground_truth = ExtractionGroundTruth(
                item_id=item_id,
                item_type=item.get("item_type", "paper"),
                difficulty=item.get("difficulty", "easy"),
                expected_problem=item.get("expected_problem", ""),
                expected_technology=item.get("expected_technology", ""),
                expected_keywords=item.get("expected_keywords", []),
                source_sentences=item.get("source_sentences", []),
            )

            # Score via ExtractionEvaluator
            try:
                score = await asyncio.to_thread(
                    evaluator.score,
                    ground_truth,
                    extracted,
                )
            except Exception as exc:
                return {"item_id": item_id, "error": str(exc)}

        return {"item_id": item_id, "score": score}

    # ------------------------------------------------------------------
    # Main run method
    # ------------------------------------------------------------------

    def run(self, config: dict, fixtures: dict) -> TestResult:
        """
        Execute the T1 extraction accuracy test.

        Args:
            config:   Runtime configuration dict. May include ``run_id``.
            fixtures: Pre-loaded fixture data (or empty dict to load defaults).

        Returns:
            A validated TestResult.
        """
        run_id: str = config.get("run_id", "standalone")

        # Load fixtures if not provided
        if not fixtures:
            default_path = (
                Path(__file__).resolve().parent.parent
                / "fixtures"
                / "extraction_fixtures.json"
            )
            try:
                fixtures = self.load_fixtures(default_path)
            except FixtureError as exc:
                return TestResult(
                    test_id=self.test_id,
                    test_name=self.test_name,
                    run_id=run_id,
                    passed=False,
                    scores={},
                    threshold=self.pass_threshold,
                    details={},
                    error=str(exc),
                    created_at=datetime.now(timezone.utc).isoformat(),
                )

        # Collect all fixture items across difficulty levels
        all_items: list[dict] = []
        for level in ("easy", "medium", "hard"):
            all_items.extend(fixtures.get(level, []))

        total_items = len(all_items)
        if total_items == 0:
            return TestResult(
                test_id=self.test_id,
                test_name=self.test_name,
                run_id=run_id,
                passed=False,
                scores={},
                threshold=self.pass_threshold,
                details={"items": []},
                error="no_fixture_items",
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        # Run async evaluation with concurrency limit of 3
        evaluator = ExtractionEvaluator()
        results = asyncio.run(self._run_async(evaluator, all_items))

        # Aggregate results
        item_details: list[dict] = []
        problem_scores: list[float] = []
        technology_scores: list[float] = []
        total_hallucinations: int = 0
        error_count: int = 0

        for res in results:
            if "error" in res:
                error_count += 1
                item_details.append({
                    "item_id": res["item_id"],
                    "status": "error",
                    "error": res["error"],
                })
            else:
                s = res["score"]
                problem_scores.append(s.problem_accuracy)
                technology_scores.append(s.technology_accuracy)
                total_hallucinations += s.hallucination_count
                item_details.append({
                    "item_id": res["item_id"],
                    "status": "ok",
                    "problem_accuracy": s.problem_accuracy,
                    "technology_accuracy": s.technology_accuracy,
                    "hallucination_count": s.hallucination_count,
                    "hallucinated_claims": s.hallucinated_claims,
                })

        # Check >50% error threshold (Requirement 5.7)
        if error_count > total_items / 2:
            result = TestResult(
                test_id=self.test_id,
                test_name=self.test_name,
                run_id=run_id,
                passed=False,
                scores={
                    "avg_problem_accuracy": 0.0,
                    "avg_technology_accuracy": 0.0,
                    "total_hallucinations_max": float(total_hallucinations),
                },
                threshold=self.pass_threshold,
                details={"items": item_details, "error_count": error_count},
                error="too_many_item_errors",
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            # Skip _validate_result here — passed is forced False due to errors,
            # scores are zeroed so compute_pass would also return False.
            return result

        # Compute averages
        avg_problem = (
            sum(problem_scores) / len(problem_scores) if problem_scores else 0.0
        )
        avg_technology = (
            sum(technology_scores) / len(technology_scores)
            if technology_scores
            else 0.0
        )

        scores = {
            "avg_problem_accuracy": avg_problem,
            "avg_technology_accuracy": avg_technology,
            "total_hallucinations_max": float(total_hallucinations),
        }

        passed = self.compute_pass(scores)

        result = TestResult(
            test_id=self.test_id,
            test_name=self.test_name,
            run_id=run_id,
            passed=passed,
            scores=scores,
            threshold=self.pass_threshold,
            details={
                "items": item_details,
                "error_count": error_count,
                "total_items": total_items,
            },
            error=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self._validate_result(result)
        return result

    async def _run_async(
        self,
        evaluator: ExtractionEvaluator,
        items: list[dict],
    ) -> list[dict[str, Any]]:
        """Run all item evaluations concurrently with Semaphore(3)."""
        sem = asyncio.Semaphore(3)
        tasks = [
            self._evaluate_item(sem, evaluator, item)
            for item in items
        ]
        return await asyncio.gather(*tasks)


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    T1ExtractionAccuracy._run_standalone(
        Path(__file__).resolve().parent.parent / "fixtures" / "extraction_fixtures.json"
    )
