"""
validation/evaluators/persona_simulator.py
==========================================
LLM-based simulator for founder and investor panel personas.

Used by:
  - T5 (Founder Panel Test)  — simulate_founder_panel()
  - T6 (Investor Panel Test) — simulate_investor_panel()

All LLM calls are routed through agents.base.call_llm().
On LLM failure the methods retry once with agent="extractor",
then fall back to a neutral default response rather than crashing.
"""

from __future__ import annotations

from typing import Literal

from agents.base import call_llm
from validation.models import FounderResponse, InvestorResponse

# ---------------------------------------------------------------------------
# Founder persona system prompts
# ---------------------------------------------------------------------------

_FOUNDER_PERSONA_PROMPTS: list[str] = [
    (
        "You are an aggressive, skeptical serial founder. You have been burned by over-hyped "
        "research insights before and you demand hard evidence of customer pain before paying "
        "for anything. You are blunt and willing to say no quickly. "
        "Return only valid JSON."
    ),
    (
        "You are an idealistic first-time founder passionate about using technology to solve "
        "important societal problems. You get excited by ambitious, high-impact opportunities "
        "even when the path to revenue is unclear. "
        "Return only valid JSON."
    ),
    (
        "You are a pragmatic, experienced founder focused on unit economics, time-to-market, "
        "and capital efficiency. You evaluate every opportunity through the lens of whether "
        "you can reach $1M ARR in 18 months or fewer. "
        "Return only valid JSON."
    ),
    (
        "You are a deeply technical founder with a background in ML infrastructure and systems "
        "engineering. You assess opportunities by their technical defensibility and whether "
        "the core insight requires genuine engineering depth to reproduce. "
        "Return only valid JSON."
    ),
    (
        "You are a commercially-minded founder who has built and sold two B2B SaaS companies. "
        "You evaluate opportunities primarily on sales-motion clarity, buyer persona fit, and "
        "expansion revenue potential within an enterprise account. "
        "Return only valid JSON."
    ),
]

# ---------------------------------------------------------------------------
# Investor persona system prompts
# ---------------------------------------------------------------------------

_INVESTOR_PERSONA_PROMPTS: dict[str, str] = {
    "YC Partner": (
        "You are a YC partner known for funding technical founders solving real problems. "
        "You look for 10x market insights and unfair advantages. Be direct and honest. "
        "Return only valid JSON."
    ),
    "Sequoia Partner": (
        "You are a Sequoia Capital partner focused on large markets and defensible moats. "
        "You are skeptical of narrow opportunities and demand evidence of "
        "category-creating potential. "
        "Return only valid JSON."
    ),
    "a16z Partner": (
        "You are an a16z partner who deeply values technology-driven transformation of large "
        "incumbent industries. You are excited by opportunities at the intersection of AI and "
        "existing workflows. "
        "Return only valid JSON."
    ),
}

# Reaction values that are considered valid for InvestorResponse.
_VALID_REACTIONS: set[str] = {"Interesting", "Massive opportunity", "Pass"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_opportunity(opportunity: dict) -> str:
    """Return a concise, human-readable summary of an opportunity dict."""
    title = opportunity.get("title", "Untitled opportunity")
    problem = opportunity.get("problem", "")
    technology = opportunity.get("technology", "")
    market = opportunity.get("market", "")
    lines = [f"Opportunity: {title}"]
    if problem:
        lines.append(f"Problem: {problem}")
    if technology:
        lines.append(f"Technology: {technology}")
    if market:
        lines.append(f"Market: {market}")
    # Include any remaining fields for completeness, excluding already-used keys.
    for key, value in opportunity.items():
        if key not in {"title", "problem", "technology", "market"} and isinstance(value, (str, int, float)):
            lines.append(f"{key.capitalize()}: {value}")
    return "\n".join(lines)


def _safe_call_llm(prompt: str, system: str, agent: str = "reasoner") -> dict | None:
    """
    Call the LLM with one automatic retry on failure.

    On first failure, retries with agent="extractor".
    Returns None if both attempts fail.
    """
    try:
        return call_llm(prompt, system=system, agent=agent)
    except Exception:
        pass
    # Retry with the extractor agent as a fallback.
    try:
        return call_llm(prompt, system=system, agent="extractor")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# PersonaSimulator
# ---------------------------------------------------------------------------


class PersonaSimulator:
    """Simulates founder and investor personas using the configured LLM."""

    # ------------------------------------------------------------------
    # T5 — Founder Panel
    # ------------------------------------------------------------------

    def simulate_founder_panel(
        self,
        opportunity: dict,
        n_founders: int = 5,
    ) -> list[FounderResponse]:
        """
        Simulate ``n_founders`` distinct founder personas evaluating an opportunity.

        Each persona has a unique system prompt (cycling through five archetypes:
        aggressive/skeptical, idealistic, pragmatic, technical, commercial).

        Parameters
        ----------
        opportunity:
            Structured opportunity dict (title, problem, technology, market, …).
        n_founders:
            Number of founder personas to simulate.  Defaults to 5.

        Returns
        -------
        list[FounderResponse]
            One ``FounderResponse`` per simulated founder, in persona_id order.
        """
        opportunity_text = _format_opportunity(opportunity)
        user_prompt = (
            f"{opportunity_text}\n\n"
            "Please answer the following three questions about this opportunity:\n"
            "1. Would you pay for this insight? (yes/no + reasoning)\n"
            "2. Would you build this? (yes/no + reasoning)\n"
            "3. Would you NOT have found this yourself? (yes/no + reasoning)\n\n"
            "Return your answer as JSON with keys: "
            '"would_pay" (bool), "would_build" (bool), '
            '"would_not_find_themselves" (bool), "reasoning" (str).'
        )

        responses: list[FounderResponse] = []
        for i in range(n_founders):
            persona_id = f"founder_{i + 1}"
            # Cycle through the five distinct prompts; if n_founders > 5 the
            # cycle repeats but persona_ids remain unique.
            system_prompt = _FOUNDER_PERSONA_PROMPTS[i % len(_FOUNDER_PERSONA_PROMPTS)]

            result = _safe_call_llm(user_prompt, system=system_prompt)

            if result is None:
                # LLM completely unavailable — use a neutral default.
                responses.append(
                    FounderResponse(
                        persona_id=persona_id,
                        would_pay=False,
                        would_build=False,
                        would_not_find_themselves=False,
                        reasoning="LLM call failed; defaulting to neutral response.",
                    )
                )
                continue

            responses.append(
                FounderResponse(
                    persona_id=persona_id,
                    would_pay=bool(result.get("would_pay", False)),
                    would_build=bool(result.get("would_build", False)),
                    would_not_find_themselves=bool(
                        result.get("would_not_find_themselves", False)
                    ),
                    reasoning=str(result.get("reasoning", "")),
                )
            )

        return responses

    # ------------------------------------------------------------------
    # T6 — Investor Panel
    # ------------------------------------------------------------------

    def simulate_investor_panel(
        self,
        opportunity: dict,
        personas: list[str],
    ) -> list[InvestorResponse]:
        """
        Simulate a panel of named investor personas evaluating an opportunity.

        Parameters
        ----------
        opportunity:
            Structured opportunity dict (title, problem, technology, market, …).
        personas:
            List of investor persona names, e.g.
            ``["YC Partner", "Sequoia Partner", "a16z Partner"]``.
            For recognised names the standard system prompt is used; for
            unrecognised names a generic investor prompt is constructed on the fly.

        Returns
        -------
        list[InvestorResponse]
            One ``InvestorResponse`` per persona, in the order given.
        """
        opportunity_text = _format_opportunity(opportunity)
        user_prompt = (
            f"{opportunity_text}\n\n"
            "Please evaluate this opportunity and provide:\n"
            "1. Your reaction: one of 'Interesting', 'Massive opportunity', or 'Pass'.\n"
            "2. Your reasoning (2–4 sentences).\n"
            "3. Three follow-up questions you would ask the founding team.\n\n"
            "Return your answer as JSON with keys: "
            '"reaction" (str), "reasoning" (str), '
            '"follow_up_questions" (list of str).'
        )

        responses: list[InvestorResponse] = []
        for persona in personas:
            system_prompt = _INVESTOR_PERSONA_PROMPTS.get(
                persona,
                (
                    f"You are {persona}, an experienced venture capital investor. "
                    "You evaluate early-stage opportunities with a critical eye, "
                    "looking for large markets, strong founders, and defensible moats. "
                    "Return only valid JSON."
                ),
            )

            result = _safe_call_llm(user_prompt, system=system_prompt)

            if result is None:
                # LLM completely unavailable — use a neutral default.
                responses.append(
                    InvestorResponse(
                        persona=persona,
                        reaction="Interesting",
                        reasoning="LLM call failed; defaulting to neutral response.",
                        follow_up_questions=[],
                    )
                )
                continue

            # Validate reaction; default to "Interesting" if the LLM returned
            # something unexpected.
            raw_reaction = str(result.get("reaction", "Interesting"))
            reaction: Literal["Interesting", "Massive opportunity", "Pass"] = (
                raw_reaction if raw_reaction in _VALID_REACTIONS else "Interesting"  # type: ignore[assignment]
            )

            # Ensure follow_up_questions is always a list of strings.
            raw_questions = result.get("follow_up_questions", [])
            if isinstance(raw_questions, list):
                follow_up_questions = [str(q) for q in raw_questions]
            else:
                follow_up_questions = []

            responses.append(
                InvestorResponse(
                    persona=persona,
                    reaction=reaction,
                    reasoning=str(result.get("reasoning", "")),
                    follow_up_questions=follow_up_questions,
                )
            )

        return responses
