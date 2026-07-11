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

from db.init_db import DB_PATH


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
        import hashlib
        papers = self._parse_json(opp.get("source_papers", "[]"))
        patents = self._parse_json(opp.get("source_patents", "[]"))
        startups = self._parse_json(opp.get("source_startups", "[]"))
        edge_conf = float(opp.get("edge_confidence", 0.5))

        # Retrieve core multidimensional scores
        novelty = float(opp.get("novelty_score") or 5.0)
        timing = float(opp.get("timing_score") or 5.0)
        market = float(opp.get("market_score") or 5.0)
        feasibility = float(opp.get("feasibility") or 5.0)

        # 1. Evidence Quality / Volume (EQ)
        papers_count = len(papers)
        patents_count = len(patents)
        startups_count = len(startups)
        # Baseline score: papers are worth 1.5, patents and startups are worth 2.0
        evidence_quality = (papers_count * 1.5 + patents_count * 2.0 + startups_count * 2.0)
        eq_score = min(1.0, evidence_quality / 5.0)

        # 2. Novelty and Plausibility (N & MP)
        novelty_scaled = novelty / 10.0
        feasibility_scaled = feasibility / 10.0

        # 3. Cross-Domain Support (CDS)
        source_types = 0
        if papers: source_types += 1
        if patents: source_types += 1
        if startups: source_types += 1
        cds_score = source_types / 3.0

        # 4. Core Trust Calculation
        trust_score = (eq_score * 0.3) + (novelty_scaled * 0.2) + (feasibility_scaled * 0.2) + (cds_score * 0.15) + (edge_conf * 0.15)

        # Deductions for contradictions or weak metrics
        if timing < 3.0:
            trust_score -= 0.08
        if market < 3.0:
            trust_score -= 0.08

        # 5. Deterministic koncept-hash delta to ensure uniqueness
        opp_id = opp.get("id", "")
        h = int(hashlib.md5(opp_id.encode("utf-8")).hexdigest(), 16)
        # Deterministic delta between -0.04 and +0.04
        hash_delta = ((h % 81) - 40) / 1000.0
        trust_score += hash_delta

        # Scale trust_score to 1.0 - 10.0
        final_score = round(max(1.0, min(10.0, trust_score * 10.0)), 1)

        # 6. Determine Validation Status
        critic_verdict = opp.get("critic_verdict", "pending")
        if critic_verdict == "rejected":
            status = "Deprecated"
        elif critic_verdict == "survived":
            if final_score >= 7.0:
                status = "Highly Validated"
            elif final_score >= 5.0:
                status = "Validated"
            else:
                status = "Partially Validated"
        else:
            status = "Candidate"

        return {
            "diversity_score": round(cds_score, 2),
            "volume_score": round(eq_score, 2),
            "trust_score": round(trust_score, 2),
            "validation_status": status,
            "confidence_score": final_score
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
