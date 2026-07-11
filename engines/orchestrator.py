"""
engines/orchestrator.py
=======================
Cognitive Orchestrator for AIVE.
Coordinates the full discovery pipeline:
  Discovery → Novelty → Critic → Validation → Report
"""

from typing import Any, Dict
from engines.base_engine import BaseEngine
from engines.event_bus import EventBus
from engines.discovery_engine import DiscoveryEngine
from engines.novelty_engine import NoveltyEngine
from engines.critic_engine import CriticEngine
from engines.validation_engine import ValidationEngine
from engines.report_engine import ReportEngine
from engines.learning_engine import LearningEngine


class Orchestrator(BaseEngine):
    """
    Coordinates all AIVE cognitive engines through a multi-stage pipeline:
    Discovery → Novelty Filtering → Critic → Validation → Report
    """

    def __init__(self, event_bus: EventBus = None):
        super().__init__("Orchestrator")
        self.event_bus = event_bus or EventBus()
        self.discovery_engine = DiscoveryEngine()
        self.novelty_engine = NoveltyEngine()
        self.critic_engine = CriticEngine()
        self.validation_engine = ValidationEngine()
        self.report_engine = ReportEngine()
        self.learning_engine = LearningEngine()

        self.event_bus.subscribe("discovery.triggered", self.handle_discovery_trigger)
        self.event_bus.subscribe("critique.triggered", self.handle_critique_trigger)

    @property
    def mission(self) -> str:
        return "Coordinate all cognitive engines through the full discovery and validation pipeline."

    @property
    def responsibilities(self) -> list[str]:
        return [
            "Trigger opportunity discovery batches.",
            "Run novelty adversarial check on candidates.",
            "Apply Critic filter.",
            "Update confidence scores via Validation.",
            "Generate portfolio reports.",
            "Publish pipeline lifecycle events.",
        ]

    @property
    def inputs(self) -> list[str]:
        return ["action", "parameters"]

    @property
    def outputs(self) -> list[str]:
        return ["status", "summary"]

    def handle_discovery_trigger(self, payload: Dict[str, Any]):
        count = payload.get("count", 30)
        self.run({"action": "discover", "count": count})

    def handle_critique_trigger(self, payload: Dict[str, Any]):
        self.run({"action": "critique"})

    def run_full_pipeline(self, count: int = 30) -> Dict[str, Any]:
        """
        Full pipeline: Discovery → Novelty → Critic → Validation → Report
        """
        self.logger.info(f"Starting full pipeline (count={count})...")
        self.event_bus.publish("pipeline.start", {"count": count})

        # Stage 1: Discovery
        disc_res = self.discovery_engine.run({"candidate_count": count})
        self.event_bus.publish("discovery.complete", {"count": disc_res["count"]})
        self.logger.info(f"Discovery: {disc_res['count']} candidates generated.")

        # Stage 2: Novelty check (runs per-opportunity on the result set)
        opportunities = disc_res.get("opportunities", [])
        novelty_passed, novelty_blocked = 0, 0
        for opp in opportunities:
            novelty = self.novelty_engine.run({"opportunity": opp})
            if not novelty.get("is_novel", True):
                novelty_blocked += 1
            else:
                novelty_passed += 1
        self.logger.info(f"Novelty: {novelty_passed} passed / {novelty_blocked} blocked.")

        # Stage 3: Critic
        crit_res = self.critic_engine.run({})
        self.event_bus.publish("critique.complete", crit_res)
        self.logger.info(f"Critic: {crit_res['survived']} survived / {crit_res['rejected']} killed.")

        # Stage 4: Validation scoring
        val_res = self.validation_engine.run({})

        # Stage 5: Report
        rep_res = self.report_engine.run({"output_filename": "pipeline_report.md"})

        # Stage 6: Learning Engine analysis
        learn_res = self.learning_engine.run({"action": "full_report"})

        self.event_bus.publish("pipeline.complete", {
            "discovered": disc_res["count"],
            "survived": crit_res["survived"],
        })

        return {
            "discovery": disc_res,
            "novelty": {"passed": novelty_passed, "blocked": novelty_blocked},
            "critique": crit_res,
            "validation": val_res,
            "report": rep_res,
            "learning": learn_res.get("overall_recommendations", []),
        }

    # Allow running individual stages too
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        action = inputs.get("action", "run_pipeline")
        count = inputs.get("count", 30)

        if action == "discover":
            res = self.discovery_engine.run({"candidate_count": count})
            return {"status": "success", "engine": "discovery", "result": res}
        elif action == "critique":
            res = self.critic_engine.run({})
            return {"status": "success", "engine": "critic", "result": res}
        elif action == "validate":
            res = self.validation_engine.run({})
            return {"status": "success", "engine": "validation", "result": res}
        elif action == "report":
            res = self.report_engine.run({"output_filename": "manual_report.md"})
            return {"status": "success", "engine": "report", "result": res}
        elif action == "learn":
            res = self.learning_engine.run({"action": "full_report"})
            return {"status": "success", "engine": "learning", "result": res}
        elif action == "run_pipeline":
            res = self.run_full_pipeline(count=count)
            return {"status": "success", "pipeline": res}
        else:
            err = ValueError(f"Unknown orchestration action: {action}")
            self.log_failure("run", err)
            return {"status": "failure", "error": str(err)}
