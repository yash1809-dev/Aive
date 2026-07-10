"""
run_aues.py — AIVE Ultimate Evaluation Suite runner
Runs T1, T2, T3 (the implemented tests) and prints a scored report card.
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from validation.score_recorder import ScoreRecorder
from validation.tests.t1_extraction import T1ExtractionAccuracy
from validation.tests.t2_cross_doc import T2CrossDocReasoning
from validation.tests.t3_false_opportunity import T3FalseOpportunityRejection
from validation.tests.t7_graph_quality import T7GraphQuality
from validation.tests.t9_commercialization import T9CommercialIntelligence

FIXTURES_DIR = ROOT / "validation" / "fixtures"

TESTS = [
    (T1ExtractionAccuracy,        FIXTURES_DIR / "extraction_fixtures.json"),
    (T2CrossDocReasoning,         FIXTURES_DIR / "cross_doc_fixtures.json"),
    (T3FalseOpportunityRejection, FIXTURES_DIR / "false_opportunity_fixtures.json"),
    (T7GraphQuality,              None),   # reads aive.db directly — no fixture file
    (T9CommercialIntelligence,    None),   # reads aive.db directly — no fixture file
]

recorder = ScoreRecorder()
run_id = recorder.new_run(label=f"AUES run {datetime.now(timezone.utc).isoformat()}")
print(f"\n{'='*60}")
print(f"AIVE ULTIMATE EVALUATION SUITE — run_id: {run_id}")
print(f"{'='*60}\n")

results = []
for TestClass, fixture_path in TESTS:
    t = TestClass()
    print(f"▶ Running {t.test_id} — {t.test_name} ...")
    start = time.time()
    try:
        # T7 and T9 read directly from aive.db — no fixture file needed
        if fixture_path and str(fixture_path) and fixture_path.exists():
            fixtures = t.load_fixtures(fixture_path)
        else:
            fixtures = {}
        result = t.run({"run_id": run_id}, fixtures)
    except Exception as exc:
        from validation.models import TestResult
        result = TestResult(
            test_id=t.test_id, test_name=t.test_name, run_id=run_id,
            passed=False, scores={}, threshold=t.pass_threshold,
            details={}, error=str(exc),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    elapsed = time.time() - start
    try:
        recorder.record(run_id, result)
    except Exception:
        pass
    results.append((result, elapsed))

    status = "✅ PASS" if result.passed else ("⚠️  ERROR" if result.error else "❌ FAIL")
    print(f"   {status} | {elapsed:.1f}s")
    for k, v in result.scores.items():
        threshold = result.threshold.get(k, "?")
        print(f"   {k}: {v:.2f}  (threshold: {threshold})")
    if result.error:
        print(f"   error: {result.error}")
    print()

# Summary
print(f"{'='*60}")
print("RESULTS SUMMARY")
print(f"{'='*60}")
passed = sum(1 for r, _ in results if r.passed)
failed = sum(1 for r, _ in results if not r.passed and not r.error)
errored = sum(1 for r, _ in results if r.error)
total = len(results)
print(f"Total: {total}  |  Passed: {passed}  |  Failed: {failed}  |  Errored: {errored}")
print(f"Pass rate: {passed/total*100:.0f}%\n")

for r, elapsed in results:
    status = "PASS" if r.passed else ("ERROR" if r.error else "FAIL")
    print(f"  {r.test_id:4s} {status:6s}  {elapsed:.1f}s  —  {r.test_name}")

# Save JSON report
report_path = ROOT / "data" / "exports" / f"aues_report_{run_id}.json"
report = {
    "run_id": run_id,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "summary": {"total": total, "passed": passed, "failed": failed, "errored": errored},
    "results": [
        {
            "test_id": r.test_id, "test_name": r.test_name,
            "passed": r.passed, "scores": r.scores,
            "threshold": r.threshold, "error": r.error,
        }
        for r, _ in results
    ],
}
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2))
print(f"\nReport saved: {report_path.name}")
