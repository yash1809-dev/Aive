"""
agents/report_builder.py
========================
Research-Grade Report Builder — generates publication-quality Markdown reports.

Produces 15-section structured reports with full evidence traceability,
inline citations ([item_id]), and grounded LLM-generated sections.
All LLM calls receive specific DB facts as context — no free generation.

Backward compatible: existing report_writer.py and /api/reports/generate unchanged.
"""

import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.init_db import DB_PATH


class ReportBuilder:
    """
    Generates research-grade reports with 15 structured sections.
    Deterministic sections are built from DB without LLM calls.
    LLM sections are grounded in DB facts with inline citations.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    # ── Data loaders ──────────────────────────────────────────────────────────

    def _load_opportunities(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT id, title, problem, technology, market, timing_signal,
                       reasoning, evidence, existing_competitors,
                       novelty_score, timing_score, market_score, feasibility,
                       confidence_score, edge_confidence, reasoning_chain,
                       source_papers, source_patents, source_startups, critic_notes
                FROM opportunities WHERE critic_verdict='survived'
                ORDER BY confidence_score DESC
            """).fetchall()
        return [dict(r) for r in rows]

    def _load_items(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT id, title, type, domain, doc_type, summary, problem,
                       technology, source_url, year, evidence_classification
                FROM items WHERE extraction_status='done'
                ORDER BY extracted_at DESC
            """).fetchall()
        return [dict(r) for r in rows]

    def _load_graph_summary(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            n_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            n_edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            type_counts = dict(conn.execute(
                "SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type"
            ).fetchall())
            rel_counts = dict(conn.execute(
                "SELECT relationship, COUNT(*) FROM edges GROUP BY relationship"
            ).fetchall())
        return {
            "total_nodes": n_nodes,
            "total_edges": n_edges,
            "node_types": type_counts,
            "relationship_types": rel_counts,
        }

    def _load_discoveries(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT * FROM discoveries ORDER BY confidence DESC LIMIT 20"
                ).fetchall()
                return [dict(r) for r in rows]
            except Exception:
                return []

    def _load_contradictions(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT * FROM contradictions ORDER BY confidence DESC LIMIT 10"
                ).fetchall()
                return [dict(r) for r in rows]
            except Exception:
                return []

    def _load_rejected_count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM rejected_ideas").fetchone()[0]


    # ── LLM helpers ───────────────────────────────────────────────────────────

    def _llm(self, prompt: str, system: str = "") -> str:
        """
        Call LLM for prose generation. Uses raw HTTP directly so we get
        plain text back rather than forcing JSON parsing (report sections
        are narrative, not structured).
        """
        import os
        import urllib.request
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")

        prose_system = system or (
            "You are a senior research analyst writing a professional report. "
            "Be precise, cite evidence using [item_id] format, never fabricate facts. "
            "Write in clear prose. Do not return JSON."
        )

        try:
            provider = os.getenv("LLM_PROVIDER", "ollama").lower()

            if provider == "openai":
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
                resp = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": prose_system},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.4,
                    max_tokens=600,
                )
                return resp.choices[0].message.content.strip()

            # Ollama — request plain text, not JSON
            host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            model = os.getenv("OLLAMA_MODEL_REASONER",
                              os.getenv("OLLAMA_MODEL_EXTRACTOR", "llama3:8b"))
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": prose_system + " /no_think"},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.4},
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{host}/api/chat", data=payload,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as r:
                body = json.loads(r.read())
            return body["message"]["content"].strip()

        except Exception as e:
            return f"[Section generation failed: {e}]"

    def _parse(self, raw) -> list:
        try:
            return json.loads(raw) if raw else []
        except Exception:
            return []

    # ── Section generators ────────────────────────────────────────────────────

    def _s_executive_summary(self, opps, items, discoveries) -> str:
        """LLM-generated — grounded in top opportunities and item count."""
        top_opps = "\n".join(
            f"- [{o['id']}] {o['title']}: {o['problem']} → {o['technology']}"
            for o in opps[:5]
        ) or "No survived opportunities."
        prompt = (
            f"Write a 2-paragraph Executive Summary for a research intelligence report.\n\n"
            f"Data context:\n"
            f"- Total sources analyzed: {len(items)}\n"
            f"- Survived opportunities: {len(opps)}\n"
            f"- Research discoveries: {len(discoveries)}\n\n"
            f"Top opportunities:\n{top_opps}\n\n"
            f"Requirements: Cite opportunities using their IDs in [brackets]. "
            f"Be specific about the domain(s) and key technologies found. "
            f"Do not invent facts not in the context."
        )
        return self._llm(prompt)

    def _s_objectives(self, items) -> str:
        """LLM-generated — derived from actual domains present."""
        domains = list({i.get("domain") or "unknown" for i in items if i.get("domain")})[:5]
        prompt = (
            f"Write an Objectives section (3-5 bullet points) for this research report.\n\n"
            f"Domains covered: {', '.join(domains) or 'general'}\n"
            f"Total sources: {len(items)}\n\n"
            f"State what AIVE was tasked to discover in these domains. "
            f"Be factual. Use the domains listed above."
        )
        return self._llm(prompt)

    def _s_methodology(self, items) -> str:
        """LLM-generated — describes actual pipeline stages."""
        type_counts = {}
        for i in items:
            t = i.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        breakdown = ", ".join(f"{v} {k}s" for k, v in type_counts.items())
        prompt = (
            f"Write a Methodology section describing how AIVE processed these sources.\n\n"
            f"Sources: {breakdown or str(len(items)) + ' items'}\n\n"
            f"Pipeline stages: (1) Ingestion, (2) Universal Analyst extraction with evidence "
            f"classification, (3) Knowledge Graph construction with dynamic label normalization, "
            f"(4) Opportunity discovery, (5) Novelty adversarial check, (6) Critic filter, "
            f"(7) Discovery classification (research gaps, contradictions, method transfers).\n\n"
            f"Write 2 paragraphs. Be factual and specific about these stages."
        )
        return self._llm(prompt)

    def _s_evidence_list(self, items) -> str:
        """Deterministic — built from DB, no LLM."""
        if not items:
            return "_No extracted items found._\n"
        lines = ["| ID | Title | Type | Domain | Year |", "|---|---|---|---|---|"]
        for i in items[:50]:
            title = (i.get("title") or "")[:60]
            lines.append(
                f"| `{i['id']}` | {title} | {i.get('type','')} | "
                f"{i.get('domain') or '—'} | {i.get('year') or '—'} |"
            )
        if len(items) > 50:
            lines.append(f"\n_...and {len(items) - 50} more items._")
        return "\n".join(lines)

    def _s_graph_summary(self, graph) -> str:
        """Deterministic — built from graph stats, no LLM."""
        lines = [
            f"- **Total nodes:** {graph['total_nodes']}",
            f"- **Total edges:** {graph['total_edges']}",
            "",
            "**Node type distribution:**",
        ]
        for ntype, count in sorted(graph["node_types"].items(), key=lambda x: -x[1]):
            lines.append(f"  - {ntype}: {count}")
        lines += ["", "**Relationship types:**"]
        for rel, count in sorted(graph["relationship_types"].items(), key=lambda x: -x[1]):
            lines.append(f"  - `{rel}`: {count} edges")
        return "\n".join(lines)

    def _s_key_findings(self, opps, items) -> str:
        """LLM-generated — grounded in actual survived opportunities."""
        if not opps:
            return "_No survived opportunities to report._\n"
        opp_ctx = "\n".join(
            f"[{o['id']}] {o['title']}: problem={o.get('problem','')}, "
            f"tech={o.get('technology','')}, confidence={o.get('confidence_score','')}"
            for o in opps[:8]
        )
        prompt = (
            f"Write a Key Findings section (numbered list, 5-7 findings) "
            f"based on these survived opportunities:\n\n{opp_ctx}\n\n"
            f"Each finding must cite at least one opportunity ID in [brackets]. "
            f"Focus on patterns, recurring technologies, and high-confidence insights. "
            f"Do not invent opportunities not in the list."
        )
        return self._llm(prompt)

    def _s_cross_document_insights(self, opps, items) -> str:
        """LLM-generated — patterns across multiple sources."""
        techs = [o.get("technology", "") for o in opps if o.get("technology")]
        problems = [o.get("problem", "") for o in opps if o.get("problem")]
        prompt = (
            f"Write a Cross-Document Insights section identifying patterns across sources.\n\n"
            f"Recurring technologies: {', '.join(techs[:10]) or 'none'}\n"
            f"Recurring problems: {', '.join(problems[:10]) or 'none'}\n"
            f"Total sources: {len(items)}\n\n"
            f"Identify 3-4 cross-cutting themes. Be specific. "
            f"Cite opportunity IDs in [brackets] where relevant: "
            f"{', '.join('['+o['id']+']' for o in opps[:5])}"
        )
        return self._llm(prompt)

    def _s_contradictions_section(self, contradictions) -> str:
        """LLM-generated with deterministic fallback."""
        if not contradictions:
            return "_No contradictions detected in this dataset._\n"
        lines = []
        for c in contradictions[:5]:
            lines.append(f"**Concept: {c.get('concept', 'Unknown')}**\n")
            lines.append(f"- Claim A (source `{c.get('source_a','?')}`): {c.get('claim_a','')}")
            lines.append(f"- Claim B (source `{c.get('source_b','?')}`): {c.get('claim_b','')}")
            lines.append(f"- Explanation: {c.get('explanation','')}")
            lines.append(f"- Confidence: {c.get('confidence', 0):.0%}\n")
        return "\n".join(lines)

    def _s_research_gaps(self, discoveries) -> str:
        """Deterministic — filtered from discoveries table."""
        gaps = [d for d in discoveries if d.get("type") == "research_gap"]
        if not gaps:
            return "_No research gaps detected._\n"
        lines = []
        for g in gaps[:8]:
            lines.append(f"**{g.get('title', 'Unnamed Gap')}**")
            lines.append(f"> {g.get('description', '')}")
            lines.append(f"_Confidence: {g.get('confidence', 0):.0%}_\n")
        return "\n".join(lines)

    def _s_novel_opportunities(self, opps) -> str:
        """Deterministic — top opportunities with full score breakdown."""
        if not opps:
            return "_No novel opportunities survived the critic filter._\n"
        lines = []
        for i, o in enumerate(opps[:10], 1):
            papers = self._parse(o.get("source_papers"))
            patents = self._parse(o.get("source_patents"))
            startups = self._parse(o.get("source_startups"))
            competitors = self._parse(o.get("existing_competitors"))
            lines += [
                f"### {i}. {o.get('title', 'Untitled')} `[{o['id']}]`",
                "",
                f"| Dimension | Value |",
                f"|---|---|",
                f"| Problem | {o.get('problem','')} |",
                f"| Technology | {o.get('technology','')} |",
                f"| Market | {o.get('market','')} |",
                f"| Timing Signal | {o.get('timing_signal','')} |",
                "",
                f"**Scores:** Novelty {o.get('novelty_score','?')} · "
                f"Timing {o.get('timing_score','?')} · "
                f"Market {o.get('market_score','?')} · "
                f"Feasibility {o.get('feasibility','?')} · "
                f"Confidence {o.get('confidence_score','?')}",
                "",
                f"**Reasoning:** {o.get('reasoning','')}",
                "",
            ]
            if papers or patents or startups:
                lines.append("**Evidence sources:**")
                if papers:
                    lines.append("- Papers: " + ", ".join(f"`{p}`" for p in papers[:3]))
                if patents:
                    lines.append("- Patents: " + ", ".join(f"`{p}`" for p in patents[:3]))
                if startups:
                    lines.append("- Startups: " + ", ".join(f"`{p}`" for p in startups[:3]))
            if competitors:
                lines.append(f"- Known competitors: {', '.join(competitors[:5])}")
            lines.append("")
        return "\n".join(lines)

    def _s_risk_analysis(self, opps) -> str:
        """LLM-generated — grounded in opportunity data."""
        if not opps:
            return "_No opportunities to assess risk for._\n"
        opp_ctx = "\n".join(
            f"[{o['id']}] {o['title']}: feasibility={o.get('feasibility','?')}, "
            f"competitors={self._parse(o.get('existing_competitors'))[:3]}"
            for o in opps[:6]
        )
        prompt = (
            f"Write a Risk Analysis section for these research opportunities:\n\n{opp_ctx}\n\n"
            f"Identify 3-5 risks (technical, commercial, regulatory). "
            f"Cite opportunity IDs in [brackets]. Be specific and realistic."
        )
        return self._llm(prompt)

    def _s_validation_strategy(self, opps) -> str:
        """LLM-generated — next steps grounded in specific opportunities."""
        if not opps:
            return "_No opportunities to validate._\n"
        top = opps[0] if opps else {}
        prompt = (
            f"Write a Validation Strategy section for the top research opportunity:\n\n"
            f"Title: {top.get('title','')}\n"
            f"Problem: {top.get('problem','')}\n"
            f"Technology: {top.get('technology','')}\n"
            f"Market: {top.get('market','')}\n\n"
            f"Propose 3-5 concrete validation experiments or market tests. "
            f"Include success metrics. Be actionable and specific."
        )
        return self._llm(prompt)

    def _s_confidence_analysis(self, opps, items) -> str:
        """Deterministic + LLM summary."""
        if not opps:
            return "_No confidence data available._\n"
        scores = [o.get("confidence_score") or 0 for o in opps]
        avg = sum(scores) / len(scores) if scores else 0
        high = sum(1 for s in scores if s >= 7)
        med = sum(1 for s in scores if 4 <= s < 7)
        low = sum(1 for s in scores if s < 4)

        ev_counts = {"fact": 0, "inference": 0, "hypothesis": 0, "unknown": 0}
        for item in items:
            ec = item.get("evidence_classification")
            if ec:
                try:
                    ec_dict = json.loads(ec) if isinstance(ec, str) else ec
                    for v in ec_dict.values():
                        if v in ev_counts:
                            ev_counts[v] += 1
                except Exception:
                    pass

        lines = [
            f"- **Average confidence score:** {avg:.1f}/10",
            f"- **High confidence (≥7):** {high} opportunities",
            f"- **Medium confidence (4-6):** {med} opportunities",
            f"- **Low confidence (<4):** {low} opportunities",
            "",
            "**Evidence quality breakdown across all extracted items:**",
            f"- Fact: {ev_counts['fact']}",
            f"- Inference: {ev_counts['inference']}",
            f"- Hypothesis: {ev_counts['hypothesis']}",
            f"- Unknown: {ev_counts['unknown']}",
        ]
        return "\n".join(lines)

    def _s_future_work(self, discoveries, opps) -> str:
        """LLM-generated — grounded in gaps and transfers."""
        transfers = [d for d in discoveries if d.get("type") == "method_transfer"]
        gaps = [d for d in discoveries if d.get("type") == "research_gap"]
        prompt = (
            f"Write a Future Work section for this research report.\n\n"
            f"Detected research gaps: {len(gaps)}\n"
            f"Method transfer opportunities: {len(transfers)}\n"
            f"Top gap: {gaps[0].get('title','') if gaps else 'none'}\n"
            f"Top transfer: {transfers[0].get('title','') if transfers else 'none'}\n\n"
            f"Propose 4-6 concrete future research directions. Be specific."
        )
        return self._llm(prompt)

    def _s_references(self, items) -> str:
        """Deterministic — builds reference list from items table, no LLM."""
        if not items:
            return "_No source documents available._\n"
        lines = []
        for i, item in enumerate(items[:60], 1):
            url = item.get("source_url", "")
            url_part = f" [{url}]({url})" if url and url not in ("manual", "") else ""
            lines.append(
                f"{i}. `{item['id']}` — **{item.get('title','Untitled')}** "
                f"({item.get('type','')}, {item.get('year') or 'n.d.'}){url_part}"
            )
        return "\n".join(lines)

    def _s_appendix(self, opps, items, graph) -> str:
        """Deterministic — rejected count + basic stats."""
        rejected = self._load_rejected_count()
        lines = [
            "### A. Pipeline Statistics",
            "",
            f"| Stage | Count |",
            f"|---|---|",
            f"| Total sources ingested | {len(items)} |",
            f"| Opportunities discovered | {len(opps) + rejected} |",
            f"| Survived critic filter | {len(opps)} |",
            f"| Rejected by critic | {rejected} |",
            f"| Knowledge graph nodes | {graph['total_nodes']} |",
            f"| Knowledge graph edges | {graph['total_edges']} |",
        ]
        return "\n".join(lines)


    # ── Main builder ──────────────────────────────────────────────────────────

    def build(self, output_path: Optional[Path] = None) -> Path:
        """
        Generate the full 15-section research-grade report.
        Returns path to saved Markdown file.
        """
        print("ReportBuilder: Loading data...")
        opps = self._load_opportunities()
        items = self._load_items()
        graph = self._load_graph_summary()
        discoveries = self._load_discoveries()
        contradictions = self._load_contradictions()

        print(f"  {len(opps)} opportunities, {len(items)} items, "
              f"{graph['total_nodes']} nodes, {len(discoveries)} discoveries")

        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y-%m-%d %H:%M UTC")

        # Build each section
        sections = {
            "Executive Summary":        self._s_executive_summary(opps, items, discoveries),
            "Objectives":               self._s_objectives(items),
            "Methodology":              self._s_methodology(items),
            "Evidence List":            self._s_evidence_list(items),
            "Knowledge Graph Summary":  self._s_graph_summary(graph),
            "Key Findings":             self._s_key_findings(opps, items),
            "Cross-Document Insights":  self._s_cross_document_insights(opps, items),
            "Contradictions":           self._s_contradictions_section(contradictions),
            "Research Gaps":            self._s_research_gaps(discoveries),
            "Novel Opportunities":      self._s_novel_opportunities(opps),
            "Risk Analysis":            self._s_risk_analysis(opps),
            "Validation Strategy":      self._s_validation_strategy(opps),
            "Confidence Analysis":      self._s_confidence_analysis(opps, items),
            "Future Work":              self._s_future_work(discoveries, opps),
            "References":               self._s_references(items),
        }

        # Assemble report
        lines = [
            "# AIVE Research Intelligence Report",
            "",
            f"_Generated: {timestamp}_  ",
            f"_Sources: {len(items)} | Opportunities: {len(opps)} | "
            f"Graph nodes: {graph['total_nodes']}_",
            "",
            "---",
            "",
        ]

        for section_num, (title, content) in enumerate(sections.items(), 1):
            lines += [
                f"## {section_num}. {title}",
                "",
                content,
                "",
                "---",
                "",
            ]

        # Appendix
        lines += [
            "## Appendix",
            "",
            self._s_appendix(opps, items, graph),
            "",
        ]

        report_text = "\n".join(lines)

        # Save
        output_path = output_path or (
            ROOT / "reports" / f"aive_deep_{now.strftime('%Y%m%d_%H%M%S')}.md"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_text, encoding="utf-8")
        print(f"ReportBuilder: Saved to {output_path}")
        return output_path


# ── CLI Entry Point ───────────────────────────────────────────────────────────

def build(output_path: Optional[Path] = None, db_path: Path = DB_PATH) -> Path:
    """Convenience function to run a deep report build."""
    builder = ReportBuilder(db_path=db_path)
    return builder.build(output_path=output_path)


if __name__ == "__main__":
    import sys as _sys
    out = Path(_sys.argv[1]) if len(_sys.argv) > 1 else None
    path = build(out)
    print(f"Report: {path}")
