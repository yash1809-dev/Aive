"""
validation/tests/t7_graph_quality.py
=====================================
T7 — Graph Quality Test

Samples up to 50 edges from data/aive.db and uses an LLM judge to assess
whether each relationship is semantically valid.

Pass criterion: edge_precision > 0.90

Standalone execution:
    python validation/tests/t7_graph_quality.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from validation.base_test import TestBase
from validation.evaluators.graph_auditor import GraphAuditor
from validation.models import TestResult


class T7GraphQuality(TestBase):
    test_id = "T7"
    test_name = "Graph Quality Test"
    pass_threshold = {"edge_precision": 0.90}

    def run(self, config: dict, fixtures: dict) -> TestResult:
        run_id = config.get("run_id", "standalone")
        sample_size = config.get("sample_size", 50)

        auditor = GraphAuditor()

        # Sample edges
        try:
            edges = auditor.sample_edges(n=sample_size)
        except Exception as exc:
            return TestResult(
                test_id=self.test_id, test_name=self.test_name, run_id=run_id,
                passed=False, scores={}, threshold=self.pass_threshold,
                details={}, error=f"edge_sample_failed: {exc}",
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        if not edges:
            return TestResult(
                test_id=self.test_id, test_name=self.test_name, run_id=run_id,
                passed=False, scores={}, threshold=self.pass_threshold,
                details={}, error="no_edges_in_graph",
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        print(f"   Auditing {len(edges)} edges ...")
        report = auditor.batch_audit(edges)

        scores = {"edge_precision": report.precision}
        passed = self.compute_pass(scores)

        # Build per-edge detail (cap at 50 to keep output readable)
        edge_audits = [
            {
                "edge_id": e.edge_id,
                "relationship": f"{e.from_label} → {e.relationship} → {e.to_label}",
                "is_valid": e.is_valid,
                "confidence": e.confidence,
                "reasoning": e.reasoning,
            }
            for e in report.edges
        ]

        result = TestResult(
            test_id=self.test_id, test_name=self.test_name, run_id=run_id,
            passed=passed, scores=scores, threshold=self.pass_threshold,
            details={
                "total_audited": report.total_audited,
                "valid_count": report.valid_count,
                "error_count": report.error_count,
                "precision": report.precision,
                "edge_audits": edge_audits,
            },
            error=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._validate_result(result)
        return result


if __name__ == "__main__":
    from validation.models import TestResult as _TR
    import json as _json

    t = T7GraphQuality()
    result = t.run({"run_id": "standalone"}, {})
    print(_json.dumps({
        "test_id": result.test_id,
        "passed": result.passed,
        "scores": result.scores,
        "threshold": result.threshold,
        "details": {
            k: v for k, v in result.details.items() if k != "edge_audits"
        },
        "sample_edge_audits": result.details.get("edge_audits", [])[:5],
        "error": result.error,
    }, indent=2))
