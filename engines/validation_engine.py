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
        V2: Increased score variance through tiered evidence quality and amplified novelty weight.
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

        # 1. Evidence Quality / Volume (EQ) — Tiered scoring for better differentiation
        papers_count = len(papers)
        patents_count = len(patents)
        startups_count = len(startups)
        
        # Use exponential scaling to create tiers:
        # 0 sources → 0.1, 1-2 → 0.3-0.5, 3-4 → 0.6-0.75, 5+ → 0.85-1.0
        total_sources = papers_count + patents_count + startups_count
        if total_sources == 0:
            eq_score = 0.1
        elif total_sources <= 2:
            eq_score = 0.3 + (total_sources * 0.1)
        elif total_sources <= 4:
            eq_score = 0.5 + ((total_sources - 2) * 0.125)
        else:
            eq_score = min(1.0, 0.75 + ((total_sources - 4) * 0.05))
        
        # Bonus for cross-domain evidence (patents + startups signal commercialization)
        if patents_count > 0 and startups_count > 0:
            eq_score = min(1.0, eq_score + 0.15)

        # 2. Novelty amplification — High novelty (8-10) gets major boost, low (1-4) gets penalty
        novelty_scaled = novelty / 10.0
        if novelty >= 8.0:
            novelty_weight = 0.4  # Double weight for breakthrough ideas
            novelty_scaled = min(1.0, novelty_scaled * 1.2)  # 20% boost
        elif novelty >= 6.0:
            novelty_weight = 0.25  # Standard weight
        else:
            novelty_weight = 0.15  # Reduced weight for incremental ideas
            novelty_scaled = novelty_scaled * 0.8  # 20% penalty

        # 3. Feasibility with market validation
        feasibility_scaled = feasibility / 10.0
        market_scaled = market / 10.0
        # High market + high feasibility = multiplier effect
        if market >= 7.0 and feasibility >= 7.0:
            feasibility_scaled = min(1.0, feasibility_scaled * 1.15)

        # 4. Cross-Domain Support (CDS) — More granular
        source_types = 0
        if papers: source_types += 1
        if patents: source_types += 1
        if startups: source_types += 1
        
        # Reward true cross-domain evidence
        if source_types == 3:
            cds_score = 1.0
        elif source_types == 2:
            cds_score = 0.6
        elif source_types == 1:
            cds_score = 0.25
        else:
            cds_score = 0.1

        # 5. Core Trust Calculation with dynamic weighting
        trust_score = (
            eq_score * 0.25 +
            novelty_scaled * novelty_weight +
            feasibility_scaled * 0.2 +
            cds_score * 0.2 +
            edge_conf * 0.1 +
            market_scaled * 0.1
        )

        # Significant deductions for weak signals
        if timing < 3.0:
            trust_score -= 0.15  # Doubled penalty
        if market < 3.0:
            trust_score -= 0.12
        if feasibility < 3.0:
            trust_score -= 0.1

        # Bonus for timing excellence (urgent + ready)
        if timing >= 8.0:
            trust_score += 0.12

        # 6. Deterministic hash delta for uniqueness (widened range)
        opp_id = opp.get("id", "")
        h = int(hashlib.md5(opp_id.encode("utf-8")).hexdigest(), 16)
        # Deterministic delta between -0.08 and +0.08 (doubled from before)
        hash_delta = ((h % 161) - 80) / 1000.0
        trust_score += hash_delta

        # 7. Scale to 1.0 - 10.0 with better spread
        # Use power scaling to amplify differences
        trust_score = max(0.0, min(1.0, trust_score))
        final_score = 1.0 + (trust_score ** 0.85) * 9.0  # Power curve creates more spread
        final_score = round(final_score, 1)

        # 8. Determine Validation Status with finer thresholds
        critic_verdict = opp.get("critic_verdict", "pending")
        if critic_verdict == "rejected":
            status = "Deprecated"
        elif critic_verdict == "survived":
            if final_score >= 8.0:
                status = "Highly Validated"
            elif final_score >= 6.0:
                status = "Validated"
            elif final_score >= 4.0:
                status = "Partially Validated"
            else:
                status = "Needs Review"
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
