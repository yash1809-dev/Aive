"""
engines/validation_engine.py
============================
Validation Engine — calculates multidimensional confidence, trust, and validation status
for opportunity candidates based on source item diversity, edge weight, and critic verdict.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List
from engines.base_engine import BaseEngine

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "aive.db"


class ValidationEngine(BaseEngine):
    """
    Validation Engine: Measures the evidentiary weight, reasoning consistency,
    and novelty status of discoveries, updating their validation state.
    """

    def __init__(self, db_path: Path = DB_PATH):
        super().__init__("ValidationEngine")
        self.db_path = db_path

    @property
    def mission(self) -> str:
        return "Validate discoveries using evidence depth, source diversity, and reasoning checks."

    @property
    def responsibilities(self) -> list[str]:
        return [
            "Evaluate evidence density and diversity for opportunity candidates.",
            "Calculate confidence and trust scores.",
            "Promote candidate status based on evidentiary validation."
        ]

    @property
    def inputs(self) -> list[str]:
        return ["opportunity_id"]

    @property
    def outputs(self) -> list[str]:
        return ["confidence_score", "validation_status", "trust_score"]

    def _parse_json(self, raw: str) -> List[Any]:
        try:
            return json.loads(raw) if raw else []
        except json.JSONDecodeError:
            return []

    def calculate_metrics(self, opp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate multidimensional validation metrics for an opportunity.
        """
        papers = self._parse_json(opp.get("source_papers", "[]"))
        patents = self._parse_json(opp.get("source_patents", "[]"))
        startups = self._parse_json(opp.get("source_startups", "[]"))
        edge_conf = float(opp.get("edge_confidence", 0.5))

        # 1. Source diversity score (0.0 to 1.0)
        source_types = 0
        if papers: source_types += 1
        if patents: source_types += 1
        if startups: source_types += 1
        diversity_score = source_types / 3.0

        # 2. Evidence volume score
        total_sources = len(papers) + len(patents) + len(startups)
        volume_score = min(1.0, total_sources / 10.0)  # capped at 10 sources

        # 3. Trust score (combining edge weight + diversity + volume)
        trust_score = (edge_conf * 0.4) + (diversity_score * 0.4) + (volume_score * 0.2)

        # 4. Determine Validation Status
        critic_verdict = opp.get("critic_verdict", "pending")
        if critic_verdict == "rejected":
            status = "Deprecated"
        elif critic_verdict == "survived":
            if trust_score > 0.8:
                status = "Highly Validated"
            elif trust_score > 0.6:
                status = "Validated"
            else:
                status = "Partially Validated"
        else:
            status = "Candidate"

        return {
            "diversity_score": round(diversity_score, 2),
            "volume_score": round(volume_score, 2),
            "trust_score": round(trust_score, 2),
            "validation_status": status,
            "confidence_score": int(trust_score * 10)
        }

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        opp_id = inputs.get("opportunity_id")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if opp_id:
                rows = conn.execute("SELECT * FROM opportunities WHERE id=?", (opp_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM opportunities").fetchall()

        results = []
        for r in rows:
            opp = dict(r)
            metrics = self.calculate_metrics(opp)
            
            # Save validated confidence score back to the database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE opportunities SET confidence_score = ? WHERE id = ?",
                    (metrics["confidence_score"], opp["id"])
                )
            
            results.append({
                "opportunity_id": opp["id"],
                "title": opp["title"],
                **metrics
            })

        return {"validated_opportunities": results}
