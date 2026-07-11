"""
engines/learning_engine.py
==========================
Learning Engine — continuously improves AIVE's reasoning quality
by analyzing patterns in human feedback, critic verdicts, and
historical opportunity outcomes to tune future discovery runs.

Implements the AIVE principle: "Evidence Over Opinion" —
every learning signal must be grounded in measurable outcomes.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List
from engines.base_engine import BaseEngine

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "aive.db"


class LearningEngine(BaseEngine):
    """
    Learns from feedback, rejection patterns, and survival patterns to
    improve graph quality and opportunity generation over time.
    """

    def __init__(self, db_path: Path = DB_PATH):
        super().__init__("LearningEngine")
        self.db_path = db_path

    @property
    def mission(self) -> str:
        return "Learn from feedback and outcomes to continuously improve discovery quality."

    @property
    def responsibilities(self) -> list[str]:
        return [
            "Analyze rejection patterns to identify systematic weak signals.",
            "Surface high-performing node type combinations.",
            "Generate quality improvement recommendations.",
            "Track confidence calibration over time.",
        ]

    @property
    def inputs(self) -> list[str]:
        return ["action"]

    @property
    def outputs(self) -> list[str]:
        return ["insights", "recommendations", "calibration_report"]

    def analyze_rejection_patterns(self) -> Dict[str, Any]:
        """
        Find common patterns in rejected opportunities:
        - Which problem types get rejected most?
        - Which technology types survive best?
        - What are common kill reasons?
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Kill rate by technology keyword
            rejected = conn.execute(
                "SELECT o.technology, r.reason FROM rejected_ideas r JOIN opportunities o ON r.opportunity_id = o.id"
            ).fetchall()

            survived = conn.execute(
                "SELECT technology, novelty_score, confidence_score FROM opportunities WHERE critic_verdict='survived'"
            ).fetchall()

            total_opps = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
            total_survived = conn.execute(
                "SELECT COUNT(*) FROM opportunities WHERE critic_verdict='survived'"
            ).fetchone()[0]
            total_rejected = conn.execute("SELECT COUNT(*) FROM rejected_ideas").fetchone()[0]

        kill_rate = (total_rejected / total_opps * 100) if total_opps else 0
        survival_rate = (total_survived / total_opps * 100) if total_opps else 0

        # Common kill reasons
        reason_counts: Dict[str, int] = {}
        for r in rejected:
            reason = r["reason"] or ""
            # Extract key phrase
            key = reason[:60].strip()
            reason_counts[key] = reason_counts.get(key, 0) + 1

        top_kill_reasons = sorted(reason_counts.items(), key=lambda x: -x[1])[:5]

        # Surviving technology patterns
        surviving_techs = [s["technology"][:50] for s in survived]

        return {
            "total_opportunities": total_opps,
            "total_survived": total_survived,
            "total_rejected": total_rejected,
            "kill_rate_pct": round(kill_rate, 1),
            "survival_rate_pct": round(survival_rate, 1),
            "top_kill_reasons": top_kill_reasons,
            "surviving_technologies_sample": surviving_techs[:10],
        }

    def analyze_graph_health(self) -> Dict[str, Any]:
        """
        Assess graph quality metrics — node type distribution, orphan rate,
        edge density, and cross-domain coverage.
        """
        with sqlite3.connect(self.db_path) as conn:
            total_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            total_edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            orphan_nodes = conn.execute("""
                SELECT COUNT(*) FROM nodes n
                WHERE NOT EXISTS (
                    SELECT 1 FROM edges e WHERE e.from_node=n.id OR e.to_node=n.id
                )
            """).fetchone()[0]

            type_dist = conn.execute(
                "SELECT node_type, COUNT(*) as cnt FROM nodes GROUP BY node_type ORDER BY cnt DESC"
            ).fetchall()

        orphan_rate = (orphan_nodes / total_nodes * 100) if total_nodes else 0
        edge_density = (total_edges / total_nodes) if total_nodes else 0

        type_breakdown = {r[0]: r[1] for r in type_dist}

        # Flag imbalanced types
        tech_count = type_breakdown.get("Technology", 0)
        buyer_count = type_breakdown.get("Buyer", 0)
        econ_count = type_breakdown.get("EconomicSignal", 0)
        reg_count = type_breakdown.get("Regulation", 0)

        recommendations = []
        if orphan_rate > 20:
            recommendations.append(f"HIGH ORPHAN RATE ({orphan_rate:.0f}%): Run concept_extractor.py to improve connectivity.")
        if tech_count > (buyer_count + econ_count + reg_count) * 3:
            recommendations.append("TECH BIAS: Too many Technology nodes vs. Buyer/EconomicSignal. Ingest more commercial data.")
        if edge_density < 1.5:
            recommendations.append("LOW EDGE DENSITY: Graph is sparse. More items from diverse domains will improve traversal quality.")

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "orphan_nodes": orphan_nodes,
            "orphan_rate_pct": round(orphan_rate, 1),
            "edge_density": round(edge_density, 2),
            "type_distribution": type_breakdown,
            "recommendations": recommendations,
        }

    def generate_learning_report(self) -> Dict[str, Any]:
        rejection = self.analyze_rejection_patterns()
        graph = self.analyze_graph_health()

        report = {
            "rejection_analysis": rejection,
            "graph_health": graph,
            "overall_recommendations": graph["recommendations"],
        }

        # Save report to file
        reports_dir = ROOT / "reports"
        reports_dir.mkdir(exist_ok=True)
        path = reports_dir / "learning_report.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self.logger.info(f"Learning report saved: {path}")
        return report

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        action = inputs.get("action", "full_report")

        if action == "rejection_patterns":
            return self.analyze_rejection_patterns()
        elif action == "graph_health":
            return self.analyze_graph_health()
        elif action == "full_report":
            return self.generate_learning_report()
        else:
            return {"error": f"Unknown action: {action}"}
