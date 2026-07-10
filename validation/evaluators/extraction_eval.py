"""
validation/evaluators/extraction_eval.py
=========================================
ExtractionEvaluator — LLM-as-judge scorer for T1 extraction accuracy.

Scores an extracted dict (with ``problem`` and ``technology`` keys) against an
``ExtractionGroundTruth`` fixture item and returns an ``ExtractionScore``.

Scoring rubric (via LLM):
  - problem_accuracy    : 0–10  (how well extracted problem matches ground truth)
  - technology_accuracy : 0–10  (how well extracted technology matches ground truth)
  - hallucination_count : int ≥ 0  (claims unambiguously absent from source)
  - hallucinated_claims : list[str]

Retry logic:
  On any exception from call_llm(), retry once with agent="extractor".
  If the second call also fails, re-raise.

Validation:
  - problem_accuracy and technology_accuracy are clamped to [0.0, 10.0]
  - hallucination_count is clamped to ≥ 0
  - passed = problem_accuracy > 8.5 and technology_accuracy > 8.5 and hallucination_count < 5
"""

from __future__ import annotations

from agents.base import call_llm
from validation.models import ExtractionGroundTruth, ExtractionScore

# System prompt kept immutable to prevent prompt injection from fixture content.
_SYSTEM_PROMPT = (
    "You are a strict academic evaluator. Return only valid JSON. "
    "Be conservative — only mark a claim as hallucinated when it is UNAMBIGUOUSLY "
    "absent from the source document. Uncertain claims are NOT hallucinations."
)


def _build_user_prompt(
    ground_truth: ExtractionGroundTruth,
    extracted: dict,
) -> str:
    source_block = "\n".join(
        f"  - {s}" for s in ground_truth.source_sentences
    )
    return (
        "Score the following extraction against the ground truth.\n\n"
        "## Source sentences (authoritative)\n"
        f"{source_block}\n\n"
        "## Ground truth\n"
        f"Expected problem    : {ground_truth.expected_problem}\n"
        f"Expected technology : {ground_truth.expected_technology}\n\n"
        "## Extracted output\n"
        f"Extracted problem    : {extracted.get('problem', '')}\n"
        f"Extracted technology : {extracted.get('technology', '')}\n\n"
        "## Instructions\n"
        "1. Score `problem_accuracy` on a scale of 0–10 (10 = perfect match).\n"
        "2. Score `technology_accuracy` on a scale of 0–10 (10 = perfect match).\n"
        "3. List every claim in the extracted output that is UNAMBIGUOUSLY absent "
        "from the source sentences above. Uncertain or partially-supported claims "
        "are NOT hallucinations — only list claims that are clearly fabricated.\n"
        "4. Set `hallucination_count` to the length of `hallucinated_claims`.\n\n"
        "Return ONLY a JSON object with exactly these keys:\n"
        "{\n"
        '  "problem_accuracy": <float 0-10>,\n'
        '  "technology_accuracy": <float 0-10>,\n'
        '  "hallucination_count": <int>,\n'
        '  "hallucinated_claims": [<string>, ...]\n'
        "}"
    )


def _parse_response(raw: dict) -> tuple[float, float, int, list[str]]:
    """Extract and validate fields from the LLM response dict."""
    problem_accuracy = float(raw.get("problem_accuracy", 0.0))
    technology_accuracy = float(raw.get("technology_accuracy", 0.0))
    hallucination_count = int(raw.get("hallucination_count", 0))
    hallucinated_claims = list(raw.get("hallucinated_claims", []))

    # Clamp accuracy scores to [0.0, 10.0]
    problem_accuracy = max(0.0, min(10.0, problem_accuracy))
    technology_accuracy = max(0.0, min(10.0, technology_accuracy))

    # Clamp hallucination count to ≥ 0
    hallucination_count = max(0, hallucination_count)

    # Ensure hallucinated_claims is consistent with hallucination_count
    if hallucination_count != len(hallucinated_claims):
        hallucination_count = len(hallucinated_claims)

    return problem_accuracy, technology_accuracy, hallucination_count, hallucinated_claims


class ExtractionEvaluator:
    """
    LLM-as-judge evaluator for T1 extraction accuracy.

    Usage::

        evaluator = ExtractionEvaluator()
        score = evaluator.score(ground_truth, extracted)
    """

    def score(
        self,
        ground_truth: ExtractionGroundTruth,
        extracted: dict,
    ) -> ExtractionScore:
        """
        Score ``extracted`` against ``ground_truth`` using an LLM judge.

        Parameters
        ----------
        ground_truth:
            The fixture's authoritative ``ExtractionGroundTruth`` instance.
        extracted:
            Dict with at least ``problem`` and ``technology`` keys produced
            by the analyst agent under test.

        Returns
        -------
        ExtractionScore
            Validated score with ``passed`` set according to thresholds.

        Raises
        ------
        Exception
            Re-raised after one retry if both LLM calls fail.
        """
        prompt = _build_user_prompt(ground_truth, extracted)

        # First attempt
        try:
            raw = call_llm(prompt, system=_SYSTEM_PROMPT, agent="extractor")
        except Exception:
            # Retry once with agent="extractor" explicitly
            try:
                raw = call_llm(prompt, system=_SYSTEM_PROMPT, agent="extractor")
            except Exception:
                raise

        problem_accuracy, technology_accuracy, hallucination_count, hallucinated_claims = (
            _parse_response(raw)
        )

        passed = (
            problem_accuracy > 8.5
            and technology_accuracy > 8.5
            and hallucination_count < 5
        )

        return ExtractionScore(
            problem_accuracy=problem_accuracy,
            technology_accuracy=technology_accuracy,
            hallucination_count=hallucination_count,
            hallucinated_claims=hallucinated_claims,
            passed=passed,
        )
