"""
validation/evaluators/graph_auditor.py
=======================================
GraphAuditor — samples edges from data/aive.db and uses an LLM to judge
whether each directed relationship is semantically valid.

Public API
----------
    GraphAuditor(aive_db_path=None)
        Constructor.  Pass an explicit Path to override the default location
        (ROOT / "data" / "aive.db").

    sample_edges(n: int = 50) -> list[dict]
        Return up to *n* randomly sampled edges, each as a plain dict with
        keys: id, from_node, to_node, relationship, from_label, to_label.
        Opens the database in READ-ONLY mode — never acquires a write lock.

    audit_edge(edge: dict) -> EdgeAuditResult
        Ask the LLM whether the relationship is semantically valid.
        Retries once with agent="extractor" on first failure.
        Falls back to is_valid=False / confidence=0.0 rather than raising.

    batch_audit(edges: list[dict]) -> GraphAuditReport
        Audit every edge, accumulate counts, compute precision, set passed.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from agents.base import call_llm
from validation.models import EdgeAuditResult, GraphAuditReport

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DB = ROOT / "data" / "aive.db"

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a knowledge graph validator. "
    "Return only valid JSON. "
    "Judge whether the relationship between two concepts is semantically meaningful."
)

_USER_PROMPT_TEMPLATE = (
    "Is this relationship semantically valid? "
    "{from_label} → {relationship} → {to_label}. "
    "Answer with is_valid (bool), reasoning (1-2 sentences), confidence (0.0-1.0)"
)

# ---------------------------------------------------------------------------
# GraphAuditor
# ---------------------------------------------------------------------------


class GraphAuditor:
    """Samples and semantically validates knowledge-graph edges via an LLM."""

    def __init__(self, aive_db_path: Path | str | None = None) -> None:
        self._db_path: Path = (
            Path(aive_db_path) if aive_db_path is not None else _DEFAULT_DB
        )

    # ------------------------------------------------------------------
    # sample_edges
    # ------------------------------------------------------------------

    def sample_edges(self, n: int = 50) -> list[dict]:
        """
        Return up to *n* randomly chosen edges from aive.db.

        Each dict has keys:
            id, from_node, to_node, relationship, from_label, to_label

        The database is opened in READ-ONLY mode so validation runs can
        never accidentally modify production data.
        """
        uri = f"file:{self._db_path}?mode=ro"
        query = (
            "SELECT e.id, e.from_node, e.to_node, e.relationship, "
            "       n1.label AS from_label, n2.label AS to_label "
            "FROM edges e "
            "JOIN nodes n1 ON e.from_node = n1.id "
            "JOIN nodes n2 ON e.to_node = n2.id "
            "ORDER BY RANDOM() "
            "LIMIT ?"
        )
        with sqlite3.connect(uri, uri=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, (n,))
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # audit_edge
    # ------------------------------------------------------------------

    def audit_edge(self, edge: dict) -> EdgeAuditResult:
        """
        Ask the LLM whether the edge relationship is semantically valid.

        On any LLM failure the method retries once with agent="extractor".
        If the retry also fails the result is marked as an error
        (is_valid=False, confidence=0.0) rather than raising an exception.
        """
        from_label   = edge.get("from_label", "")
        to_label     = edge.get("to_label", "")
        relationship = edge.get("relationship", "")
        edge_id      = edge.get("id", "")

        prompt = _USER_PROMPT_TEMPLATE.format(
            from_label=from_label,
            relationship=relationship,
            to_label=to_label,
        )

        llm_result: dict | None = None

        # First attempt
        try:
            llm_result = call_llm(prompt, system=_SYSTEM_PROMPT, agent="extractor")
        except Exception:
            llm_result = None

        # Single retry with agent="extractor" on failure
        if not llm_result:
            try:
                llm_result = call_llm(prompt, system=_SYSTEM_PROMPT, agent="extractor")
            except Exception:
                llm_result = None

        # Fall back gracefully if both attempts failed
        if not llm_result:
            return EdgeAuditResult(
                edge_id=edge_id,
                from_label=from_label,
                to_label=to_label,
                relationship=relationship,
                is_valid=False,
                reasoning="LLM call failed",
                confidence=0.0,
            )

        # Parse the LLM response — be tolerant of missing / mis-typed fields
        is_valid   = bool(llm_result.get("is_valid", False))
        reasoning  = str(llm_result.get("reasoning", ""))
        confidence = float(llm_result.get("confidence", 0.0))

        # Clamp confidence to [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))

        return EdgeAuditResult(
            edge_id=edge_id,
            from_label=from_label,
            to_label=to_label,
            relationship=relationship,
            is_valid=is_valid,
            reasoning=reasoning,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # batch_audit
    # ------------------------------------------------------------------

    def batch_audit(self, edges: list[dict]) -> GraphAuditReport:
        """
        Audit every edge in *edges* and aggregate the results.

        Computes:
            precision = valid_count / total_audited   (0.0 when total == 0)
            passed    = precision > 0.90
        """
        audit_results: list[EdgeAuditResult] = []
        valid_count = 0
        error_count = 0

        for edge in edges:
            result = self.audit_edge(edge)
            audit_results.append(result)

            if result.reasoning == "LLM call failed" and not result.is_valid and result.confidence == 0.0:
                error_count += 1
            elif result.is_valid:
                valid_count += 1

        total_audited = len(audit_results)
        precision     = valid_count / total_audited if total_audited > 0 else 0.0
        passed        = precision > 0.90

        return GraphAuditReport(
            edges=audit_results,
            precision=precision,
            passed=passed,
            total_audited=total_audited,
            valid_count=valid_count,
            error_count=error_count,
        )
