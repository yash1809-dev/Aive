"""
engines/critic_engine.py
========================
Critic Engine — wraps agents/critic.py logic into the BaseEngine interface.
Responsible for reviewing, scoring, and weeding out weak opportunity candidates.
"""

from typing import Any, Dict
from engines.base_engine import BaseEngine
from agents.critic import critique, save_verdict, get_pending


class CriticEngine(BaseEngine):
    """
    Critic Engine: Evaluates generated opportunities against market, timing,
    feasibility, and competitive benchmarks, killing 70%+ of ideas to prevent noise.
    """

    def __init__(self):
        super().__init__("CriticEngine")

    @property
    def mission(self) -> str:
        return "Critique generated opportunity candidates ruthlessly and filter out the weak ones."

    @property
    def responsibilities(self) -> list[str]:
        return [
            "Evaluate candidate feasibility, market size, competition, and timing.",
            "Classify candidates as 'survived' or 'rejected'.",
            "Log feedback and details on killed candidates for continuous learning."
        ]

    @property
    def inputs(self) -> list[str]:
        return ["opportunities"]

    @property
    def outputs(self) -> list[str]:
        return ["verdict", "critic_notes"]

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the Critic Engine on pending opportunities or specific ones.
        If inputs['opportunities'] is provided, run on those; otherwise, run on all pending in DB.
        """
        opportunities = inputs.get("opportunities")
        if not opportunities:
            opportunities = get_pending()

        if not opportunities:
            self.logger.info("No pending opportunities for critique.")
            return {"total": 0, "survived": 0, "rejected": 0}

        survived_count = 0
        rejected_count = 0
        results = []

        for opp in opportunities:
            opp_title = opp.get("title", "Untitled")[:50]
            self.logger.info(f"Critiquing opportunity: {opp_title}...")
            try:
                result = critique(opp)
                save_verdict(opp["id"], result)
                verdict = result.get("verdict", "rejected")
                if verdict == "survived":
                    survived_count += 1
                else:
                    rejected_count += 1
                results.append({"id": opp["id"], "verdict": verdict, "notes": result})
            except Exception as e:
                self.log_failure("critique", e, {"opportunity_id": opp.get("id")})

        self.logger.info(
            f"Critique batch complete. Total: {len(opportunities)} | Survived: {survived_count} | Rejected: {rejected_count}"
        )
        return {
            "total": len(opportunities),
            "survived": survived_count,
            "rejected": rejected_count,
            "details": results
        }
