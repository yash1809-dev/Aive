"""
engines/report_engine.py
========================
Report Engine — generates human-readable Markdown reports for surviving opportunities.
Saves outputs to the /reports directory.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List
from engines.base_engine import BaseEngine

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "aive.db"
REPORTS_DIR = ROOT / "reports"


class ReportEngine(BaseEngine):
    """
    Report Engine: Generates markdown portfolios and reports summarizing
    the validated opportunities, citing primary literature and market signals.
    """

    def __init__(self, db_path: Path = DB_PATH, reports_dir: Path = REPORTS_DIR):
        super().__init__("ReportEngine")
        self.db_path = db_path
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    @property
    def mission(self) -> str:
        return "Transform validated, surviving opportunities into professional, evidence-backed reports."

    @property
    def responsibilities(self) -> list[str]:
        return [
            "Query validated opportunities from the database.",
            "Format opportunity data with references and confidence breakdown.",
            "Write markdown reports to disk."
        ]

    @property
    def inputs(self) -> list[str]:
        return ["opportunity_ids", "output_filename"]

    @property
    def outputs(self) -> list[str]:
        return ["report_path", "opportunity_count"]

    def _get_survivors(self, opp_ids: List[str] = None) -> List[sqlite3.Row]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if opp_ids:
                placeholders = ",".join("?" * len(opp_ids))
                rows = conn.execute(
                    f"SELECT * FROM opportunities WHERE critic_verdict='survived' AND id IN ({placeholders})",
                    opp_ids
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM opportunities WHERE critic_verdict='survived' ORDER BY confidence_score DESC"
                ).fetchall()
        return rows

    def _parse_json(self, raw: str) -> List[Any]:
        try:
            return json.loads(raw) if raw else []
        except json.JSONDecodeError:
            return []

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        opp_ids = inputs.get("opportunity_ids")
        filename = inputs.get("output_filename", "surviving_opportunities_report.md")

        survivors = self._get_survivors(opp_ids)
        if not survivors:
            self.logger.warning("No surviving opportunities found to report.")
            return {"report_path": None, "opportunity_count": 0}

        report_path = self.reports_dir / filename
        
        md_lines = [
            "# AIVE Opportunity Portfolio",
            f"*Generated on: {sqlite3.connect(self.db_path).execute('SELECT datetime(\"now\")').fetchone()[0]} UTC*",
            "",
            "This portfolio contains evidence-backed, commercially-grounded discovery opportunities that survived the Critic's filter.",
            "",
            "---",
            ""
        ]

        for i, opp in enumerate(survivors):
            md_lines.append(f"## Opportunity #{i+1}: {opp['title']}")
            md_lines.append(f"**ID:** `{opp['id']}`  ")
            md_lines.append(f"**Confidence:** {opp['confidence_score']}/10 | **Edge Connection Weight:** {opp['edge_confidence']:.2f}")
            md_lines.append("")
            
            md_lines.append("### Concept Nodes")
            md_lines.append(f"- **Problem:** `{opp['problem']}` (Node ID: `{opp['problem_node']}`)")
            md_lines.append(f"- **Technology:** `{opp['technology']}` (Node ID: `{opp['technology_node']}`)")
            md_lines.append(f"- **Market:** `{opp['market']}`")
            md_lines.append("")

            md_lines.append("### Analysis")
            md_lines.append(f"- **Reasoning:** {opp['reasoning']}")
            md_lines.append(f"- **Timing Signal:** {opp['timing_signal']}")
            md_lines.append("")

            md_lines.append("### Scores")
            md_lines.append(f"- **Novelty Score:** {opp['novelty_score']}/10")
            md_lines.append(f"- **Timing Score:** {opp['timing_score']}/10")
            md_lines.append(f"- **Market Score:** {opp['market_score']}/10")
            md_lines.append(f"- **Feasibility:** {opp['feasibility']}/10")
            md_lines.append("")

            competitors = self._parse_json(opp["existing_competitors"])
            if competitors:
                md_lines.append("### Existing Competitors / Alternatives")
                for c in competitors:
                    md_lines.append(f"- {c}")
                md_lines.append("")

            evidence = self._parse_json(opp["evidence"])
            if evidence:
                md_lines.append("### Evolving Evidence Summary")
                for ev in evidence:
                    md_lines.append(f"- {ev}")
                md_lines.append("")

            papers = self._parse_json(opp["source_papers"])
            patents = self._parse_json(opp["source_patents"])
            startups = self._parse_json(opp["source_startups"])

            if papers or patents or startups:
                md_lines.append("### Primary Literature & Signals Citations")
                if papers:
                    md_lines.append("#### Research Papers")
                    for p in papers:
                        md_lines.append(f"- *{p}*")
                if patents:
                    md_lines.append("#### Patents")
                    for pat in patents:
                        md_lines.append(f"- *{pat}*")
                if startups:
                    md_lines.append("#### Commercial Signals / Startups")
                    for s in startups:
                        md_lines.append(f"- *{s}*")
                md_lines.append("")

            # Critic Notes
            if opp["critic_notes"]:
                try:
                    c_notes = json.loads(opp["critic_notes"])
                    summary = c_notes.get("summary", "")
                    md_lines.append("> [!NOTE]")
                    md_lines.append(f"> **Critic Verdict Summary:** {summary}")
                    md_lines.append("")
                except Exception:
                    pass

            md_lines.append("---")
            md_lines.append("")

        report_path.write_text("\n".join(md_lines), encoding="utf-8")
        self.logger.info(f"Report generated successfully: {report_path}")
        return {
            "report_path": str(report_path),
            "opportunity_count": len(survivors)
        }
