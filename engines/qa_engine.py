"""
engines/qa_engine.py
====================
QA Engine — Copilot responses grounded in structured knowledge.

Classifies question type, routes to specialized answer methods,
and always returns evidence references + confidence level.

Question types:
  factual        — full-text search across items, LLM synthesis
  graph_traversal — graph query by concept
  comparative    — compare two or more concepts/opportunities
  discovery      — query opportunities and discoveries tables
  gap            — query contradictions and research gaps

Every response includes:
  evidence_refs: list[str]   — item IDs supporting the answer
  confidence: str            — High | Medium | Low | Unknown

Backward compatible: existing `reply` field is preserved.
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engines.base_engine import BaseEngine
from db.init_db import DB_PATH


class QAEngine(BaseEngine):
    """
    Knowledge-grounded question answering engine.
    Routes questions to specialized answer methods based on detected type.
    """

    def __init__(self, db_path: Path = DB_PATH):
        super().__init__("QAEngine")
        self.db_path = db_path

    @property
    def mission(self) -> str:
        return "Answer research questions grounded in the AIVE knowledge graph."

    @property
    def responsibilities(self) -> list[str]:
        return [
            "Classify question type (factual, graph, comparative, discovery, gap).",
            "Route to specialized answer methods.",
            "Ground every answer in DB evidence.",
            "Return evidence_refs and confidence with every response.",
            "Explicitly state gaps rather than hallucinating.",
        ]

    @property
    def inputs(self) -> list[str]:
        return ["message", "workspace_context"]

    @property
    def outputs(self) -> list[str]:
        return ["reply", "evidence_refs", "confidence", "question_type"]

    # ── LLM helper ─────────────────────────────────────────────────────────

    def _call_llm(self, system: str, user: str) -> str:
        import os
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        provider = os.getenv("LLM_PROVIDER", "ollama").lower()

        if provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                temperature=0.3, max_tokens=800,
            )
            return resp.choices[0].message.content.strip()
        else:
            import urllib.request as urlreq
            host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            model = os.getenv("OLLAMA_MODEL_REASONER",
                              os.getenv("OLLAMA_MODEL_EXTRACTOR", "llama3:8b"))
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system + " /no_think"},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "options": {"temperature": 0.3},
            }).encode()
            req = urlreq.Request(
                f"{host}/api/chat", data=payload,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with urlreq.urlopen(req, timeout=120) as r:
                body = json.loads(r.read())
            return body["message"]["content"].strip()

    # ── Question classifier ────────────────────────────────────────────────

    def classify_question(self, message: str) -> str:
        """
        Classify question type from message text.
        Returns: factual | graph_traversal | comparative | discovery | gap
        """
        lower = message.lower()

        # Gap indicators
        if any(w in lower for w in ["gap", "missing", "contradiction", "conflict",
                                     "disagree", "inconsistent", "unsolved"]):
            return "gap"

        # Discovery indicators
        if any(w in lower for w in ["opportunity", "discover", "find", "identify",
                                     "novel", "innovation", "startup", "commerci"]):
            return "discovery"

        # Graph traversal indicators
        if any(w in lower for w in ["connected", "related to", "graph", "node",
                                     "relationship", "link", "path", "network",
                                     "who uses", "what solves", "which technology"]):
            return "graph_traversal"

        # Comparative indicators
        if any(w in lower for w in ["compare", "versus", "vs", "difference between",
                                     "better than", "contrast", "which is"]):
            return "comparative"

        # Default to factual
        return "factual"

    # ── Answer methods ────────────────────────────────────────────────────

    def answer_factual(self, message: str) -> Dict[str, Any]:
        """
        Full-text search across items, LLM synthesis with evidence pinning.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Extract keywords from message for search
            keywords = [w for w in message.lower().split()
                        if len(w) > 3 and w not in
                        {"what", "when", "where", "which", "does", "have", "with",
                         "that", "this", "from", "about", "tell", "show"}]

            found_items = []
            seen_ids = set()
            for kw in keywords[:5]:
                rows = conn.execute("""
                    SELECT id, title, summary, problem, technology, type, domain
                    FROM items
                    WHERE extraction_status='done'
                      AND (lower(title) LIKE ? OR lower(summary) LIKE ?
                           OR lower(problem) LIKE ? OR lower(technology) LIKE ?)
                    LIMIT 5
                """, (f"%{kw}%", f"%{kw}%", f"%{kw}%", f"%{kw}%")).fetchall()
                for r in rows:
                    if r["id"] not in seen_ids:
                        seen_ids.add(r["id"])
                        found_items.append(dict(r))

        if not found_items:
            return {
                "reply": (
                    "I don't have sufficient information in the knowledge base to answer "
                    f"that question. The graph contains no items matching your query about "
                    f'"{message[:80]}". Consider adding relevant papers or documents.'
                ),
                "evidence_refs": [],
                "confidence": "Unknown",
                "question_type": "factual",
            }

        # Build grounded context
        ctx = "\n".join(
            f"[{i['id']}] {i['title']}: problem={i.get('problem','')}, "
            f"tech={i.get('technology','')}, summary={i.get('summary','')[:150]}"
            for i in found_items[:6]
        )
        system = (
            "You are AIVE Research Copilot. Answer questions using ONLY the provided "
            "knowledge base context. Cite sources using [item_id] format. "
            "If the context doesn't answer the question, say so explicitly."
        )
        user = f"Knowledge base context:\n{ctx}\n\nQuestion: {message}\n\nAnswer in 2-3 paragraphs with citations."
        reply = self._call_llm(system, user)
        confidence = "High" if len(found_items) >= 3 else "Medium" if found_items else "Low"

        return {
            "reply": reply,
            "evidence_refs": [i["id"] for i in found_items],
            "confidence": confidence,
            "question_type": "factual",
        }

    def answer_graph(self, message: str) -> Dict[str, Any]:
        """
        Parse concept from question, query graph, format structured result.
        """
        # Extract concept keywords
        stop = {"what", "which", "technology", "technologies", "solve", "solves",
                "problem", "problems", "connected", "related", "uses", "using",
                "the", "for", "are", "is", "show", "me", "find"}
        concept = " ".join(
            w for w in message.lower().split()
            if w not in stop and len(w) > 2
        )[:40]

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Find matching nodes
            words = concept.split()
            nodes = []
            for word in words[:3]:
                rows = conn.execute("""
                    SELECT id, label, node_type, source_items FROM nodes
                    WHERE lower(label) LIKE ? LIMIT 4
                """, (f"%{word}%",)).fetchall()
                nodes.extend(rows)

            if not nodes:
                return {
                    "reply": (
                        f"No graph nodes found matching '{concept}'. "
                        "Try asking about a specific technology, problem, or market."
                    ),
                    "evidence_refs": [],
                    "confidence": "Unknown",
                    "question_type": "graph_traversal",
                }

            # Get edges for top matching node
            node = nodes[0]
            edges = conn.execute("""
                SELECT e.relationship, n.label, n.node_type, e.weight, e.evidence
                FROM edges e
                JOIN nodes n ON (
                    CASE WHEN e.from_node=? THEN e.to_node ELSE e.from_node END = n.id
                )
                WHERE e.from_node=? OR e.to_node=?
                ORDER BY e.weight DESC LIMIT 10
            """, (node["id"], node["id"], node["id"])).fetchall()

        evidence_refs = []
        for e in edges:
            try:
                evidence_refs.extend(json.loads(e["evidence"] or "[]"))
            except Exception:
                pass
        evidence_refs = list(set(evidence_refs))[:6]

        if not edges:
            reply = f"Node **{node['label']}** ({node['node_type']}) exists in the graph but has no connections yet."
        else:
            edge_lines = "\n".join(
                f"- `{e['relationship']}` → **{e['label']}** ({e['node_type']}) [weight: {e['weight']:.2f}]"
                for e in edges
            )
            reply = f"**{node['label']}** ({node['node_type']}) has {len(edges)} connections:\n\n{edge_lines}"

        return {
            "reply": reply,
            "evidence_refs": evidence_refs,
            "confidence": "High" if len(edges) >= 3 else "Medium",
            "question_type": "graph_traversal",
        }

    def answer_discovery(self, message: str) -> Dict[str, Any]:
        """
        Query opportunities and discoveries tables, return ranked results.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            opps = conn.execute("""
                SELECT id, title, problem, technology, market, confidence_score
                FROM opportunities WHERE critic_verdict='survived'
                ORDER BY confidence_score DESC LIMIT 5
            """).fetchall()

            try:
                disc = conn.execute("""
                    SELECT id, type, title, description, confidence
                    FROM discoveries ORDER BY confidence DESC LIMIT 5
                """).fetchall()
            except Exception:
                disc = []

        opp_ctx = "\n".join(
            f"[{o['id']}] {o['title']}: {o.get('problem','')} | "
            f"tech: {o.get('technology','')} | conf: {o.get('confidence_score','')}"
            for o in opps
        ) or "No survived opportunities yet."

        disc_ctx = "\n".join(
            f"[{d['id']}] {d.get('type','')}: {d.get('title','')}"
            for d in disc
        ) or "No discoveries yet."

        system = (
            "You are AIVE Research Copilot. Answer based ONLY on the provided opportunities "
            "and discoveries. Cite IDs in [brackets]. State clearly if data is insufficient."
        )
        user = (
            f"Survived opportunities:\n{opp_ctx}\n\n"
            f"Research discoveries:\n{disc_ctx}\n\n"
            f"Question: {message}\n\nAnswer concisely with citations."
        )
        reply = self._call_llm(system, user)
        all_refs = [o["id"] for o in opps] + [d["id"] for d in disc]

        return {
            "reply": reply,
            "evidence_refs": all_refs[:8],
            "confidence": "High" if len(opps) >= 3 else "Medium",
            "question_type": "discovery",
        }

    def answer_gap(self, message: str) -> Dict[str, Any]:
        """
        Query contradictions and research gaps tables.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            try:
                gaps = conn.execute("""
                    SELECT id, title, description, confidence FROM discoveries
                    WHERE type='research_gap' ORDER BY confidence DESC LIMIT 5
                """).fetchall()
                contras = conn.execute("""
                    SELECT id, concept, claim_a, claim_b, explanation, confidence
                    FROM contradictions ORDER BY confidence DESC LIMIT 5
                """).fetchall()
            except Exception:
                gaps = []
                contras = []

        if not gaps and not contras:
            return {
                "reply": (
                    "No research gaps or contradictions have been detected yet. "
                    "Run the full pipeline to generate discovery classifications."
                ),
                "evidence_refs": [],
                "confidence": "Unknown",
                "question_type": "gap",
            }

        gap_ctx = "\n".join(
            f"[{g['id']}] GAP: {g.get('title','')}: {g.get('description','')[:120]}"
            for g in gaps
        ) or "No gaps detected."

        contra_ctx = "\n".join(
            f"[{c['id']}] CONTRADICTION on '{c.get('concept','')}':\n"
            f"  A: {c.get('claim_a','')}\n  B: {c.get('claim_b','')}"
            for c in contras
        ) or "No contradictions detected."

        system = (
            "You are AIVE Research Copilot. Describe research gaps and contradictions "
            "from the provided data. Cite IDs in [brackets]. Be honest about limitations."
        )
        user = (
            f"Research gaps:\n{gap_ctx}\n\n"
            f"Contradictions:\n{contra_ctx}\n\n"
            f"Question: {message}\n\nSummarize relevant gaps/contradictions."
        )
        reply = self._call_llm(system, user)
        all_refs = [g["id"] for g in gaps] + [c["id"] for c in contras]

        return {
            "reply": reply,
            "evidence_refs": all_refs[:8],
            "confidence": "Medium",
            "question_type": "gap",
        }

    def answer_comparative(self, message: str) -> Dict[str, Any]:
        """
        Compare two or more concepts/opportunities.
        Delegates to factual with comparative framing.
        """
        result = self.answer_factual(message)
        result["question_type"] = "comparative"
        return result

    # ── Main dispatcher ────────────────────────────────────────────────────

    def answer(self, message: str) -> Dict[str, Any]:
        """
        Classify and route the question, return grounded answer with evidence.
        """
        q_type = self.classify_question(message)
        self.logger.info(f"Question type: {q_type} | '{message[:60]}'")

        if q_type == "factual":
            return self.answer_factual(message)
        elif q_type == "graph_traversal":
            return self.answer_graph(message)
        elif q_type == "discovery":
            return self.answer_discovery(message)
        elif q_type == "gap":
            return self.answer_gap(message)
        elif q_type == "comparative":
            return self.answer_comparative(message)
        else:
            return self.answer_factual(message)

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        message = inputs.get("message", "")
        if not message:
            return {"error": "message is required", "reply": "", "evidence_refs": [], "confidence": "Unknown"}
        try:
            return self.answer(message)
        except Exception as e:
            self.log_failure("answer", e, {"message": message})
            return {
                "reply": f"I encountered an error processing your question: {e}",
                "evidence_refs": [],
                "confidence": "Unknown",
                "question_type": "unknown",
                "error": str(e),
            }
