"""Generate markdown report for critic survivors."""

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.init_db import DB_PATH


def get_survivors() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, title, problem, technology, market, timing_signal,
                   reasoning, evidence, existing_competitors,
                   novelty_score, timing_score, market_score, feasibility,
                   confidence_score, edge_confidence,
                   source_papers, source_patents, source_startups, critic_notes
            FROM opportunities WHERE critic_verdict = 'survived'
            ORDER BY confidence_score DESC, novelty_score DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_rejected_count() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE critic_verdict = 'rejected'"
        ).fetchone()[0]


def _parse(raw) -> list:
    try:
        return json.loads(raw) if raw else []
    except (json.JSONDecodeError, TypeError):
        return []


def write_report(path: Path | None = None) -> Path:
    survivors = get_survivors()
    rejected = get_rejected_count()
    path = path or ROOT / "reports" / "opportunity_report_001.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# AIVE Opportunity Report #001",
        "",
        f"**Survivors:** {len(survivors)} | **Rejected:** {rejected}",
        "",
        "> First report after Critic pass. Score survivors manually in OPPORTUNITY_REVIEW.md",
        "",
    ]

    if not survivors:
        lines += ["## No survivors", "", "Critic killed everything. Fix extraction or graph quality — do not add agents.", ""]
    else:
        for i, opp in enumerate(survivors, 1):
            papers = _parse(opp.get("source_papers"))
            patents = _parse(opp.get("source_patents"))
            startups = _parse(opp.get("source_startups"))
            competitors = _parse(opp.get("existing_competitors"))

            lines += [
                f"## Opportunity {i}: {opp.get('title', 'Untitled')}",
                "",
                f"**ID:** `{opp['id']}`",
                "",
                "| Dimension | Detail |",
                "|---|---|",
                f"| Problem | {opp.get('problem', '')} |",
                f"| Technology | {opp.get('technology', '')} |",
                f"| Market | {opp.get('market', '')} |",
                f"| Timing | {opp.get('timing_signal', '')} |",
                "",
                f"**Reasoning:** {opp.get('reasoning', '')}",
                "",
                "**Scores:**",
                f"- Novelty: {opp.get('novelty_score')} | Timing: {opp.get('timing_score')} | Market: {opp.get('market_score')}",
                f"- Feasibility: {opp.get('feasibility')} | Confidence: {opp.get('confidence_score')} | Edge: {opp.get('edge_confidence')}",
                "",
                "**Evidence:**",
            ]
            if papers:
                lines.append("- Papers: " + "; ".join(papers[:3]))
            if patents:
                lines.append("- Patents: " + "; ".join(patents[:3]))
            if startups:
                lines.append("- Startups: " + "; ".join(startups[:3]))
            if competitors:
                lines.append(f"- Competitors: {', '.join(competitors)}")
            lines += ["", "---", ""]

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report: {path}")
    return path


def main():
    write_report()


if __name__ == "__main__":
    main()
