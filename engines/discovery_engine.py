"""
engines/discovery_engine.py
===========================
Discovery Engine — wraps agents/opportunity_finder.py logic into the BaseEngine interface.
Responsible for finding cross-graph concept intersections and generating opportunity candidates.
"""

from typing import Any, Dict
from engines.base_engine import BaseEngine
from agents.opportunity_finder import run as run_finder


class DiscoveryEngine(BaseEngine):
    """
    Discovery Engine: Traverses the knowledge graph to discover high-confidence
    intersections (Problem x Technology x CommercialAnchor) and generates opportunity candidates.
    """

    def __init__(self):
        super().__init__("DiscoveryEngine")

    @property
    def mission(self) -> str:
        return "Traverse the knowledge graph to identify novel, commercially grounded opportunity candidates."

    @property
    def responsibilities(self) -> list[str]:
        return [
            "Find Problem, Technology, and CommercialAnchor concepts in the graph.",
            "Traverse graph edges to find promising combinations.",
            "Generate detailed opportunity candidates using LLM enrichment."
        ]

    @property
    def inputs(self) -> list[str]:
        return ["candidate_count"]

    @property
    def outputs(self) -> list[str]:
        return ["opportunities"]

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the Discovery Engine to generate candidates.
        """
        count = inputs.get("candidate_count", 30)
        self.logger.info(f"Running Discovery Engine to generate {count} opportunity candidates...")

        try:
            opportunities = run_finder(count=count)
            self.logger.info(f"Generated {len(opportunities)} opportunity candidates.")
            return {
                "opportunities": opportunities,
                "count": len(opportunities)
            }
        except Exception as e:
            self.log_failure("generate_opportunities", e)
            return {
                "opportunities": [],
                "count": 0,
                "error": str(e)
            }
