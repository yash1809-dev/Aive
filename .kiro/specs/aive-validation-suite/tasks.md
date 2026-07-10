# Implementation Plan: AIVE Validation Suite

## Overview

Build a 10-test validation framework that answers "Does AIVE deserve to exist?" The suite wraps the existing agents, graph, and critic pipeline without modifying them, stores all results in a separate `data/validation.db`, and runs via a single command: `python validation/run_suite.py`.

## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": 1,
      "tasks": ["1", "2", "3", "4", "5"],
      "description": "Foundation: directory structure, DB schema, ScoreRecorder, TestBase, agent patch"
    },
    {
      "wave": 2,
      "tasks": ["6", "7", "8"],
      "description": "Fixtures: extraction, cross-doc, false-opportunity, ultimate"
    },
    {
      "wave": 3,
      "tasks": ["9", "10", "11", "12"],
      "description": "Evaluators: ExtractionEvaluator, NoveltySearcher, PersonaSimulator, GraphAuditor"
    },
    {
      "wave": 4,
      "tasks": ["13", "14", "15", "16"],
      "description": "Test modules T1–T4"
    },
    {
      "wave": 5,
      "tasks": ["17", "18", "19"],
      "description": "Test modules T5–T7"
    },
    {
      "wave": 6,
      "tasks": ["20", "21", "22"],
      "description": "Test modules T8–T10"
    },
    {
      "wave": 7,
      "tasks": ["23", "24"],
      "description": "Suite runner and human panel collection"
    },
    {
      "wave": 8,
      "tasks": ["25"],
      "description": "Dependencies, unit tests, property-based tests"
    }
  ]
}
```

---

## Tasks

- [x] 1. Create validation/ directory structure and base modules
  - Create `validation/__init__.py`
  - Create `validation/models.py` with all dataclasses: `TestResult`, `SuiteReport`, `ExtractionGroundTruth`, `ExtractionScore`, `NoveltyResult`, `FounderResponse`, `InvestorResponse`, `EdgeAuditResult`, `GraphAuditReport`
  - Ensure all fields match requirements: `test_id`, `test_name`, `run_id`, `passed`, `scores`, `threshold`, `details`, `error`, `created_at`
  - Enforce `SuiteReport` invariant: `passed + failed + errored == total_tests`
  - **Files**: `validation/__init__.py`, `validation/models.py`

- [x] 2. Create validation database schema and initialiser
  - Create `validation/db/validation_schema.sql` with `test_runs` table (run_id, label, created_at, total_tests, passed, failed, errored) and `test_results` table (id, run_id, test_id, test_name, passed, scores_json, threshold_json, details_json, error, created_at)
  - Add `UNIQUE(run_id, test_id)` constraint to `test_results`
  - Create `validation/db/init_validation_db.py` that creates `data/validation.db` by executing the schema if it does not exist
  - **Files**: `validation/db/__init__.py`, `validation/db/validation_schema.sql`, `validation/db/init_validation_db.py`

- [x] 3. Implement ScoreRecorder
  - Create `validation/score_recorder.py`
  - Implement `new_run(label) -> str` — inserts into `test_runs`, returns `run_id`
  - Implement `record(run_id, result)` — inserts into `test_results`, raises `RecordingError` on integrity violation
  - Implement `get_run(run_id) -> list[TestResult]`
  - Implement `get_history(test_id, limit) -> list[TestResult]`
  - Implement `generate_report(run_id) -> SuiteReport` — raises `ValueError("run_id not found")` if missing
  - Use explicit SQLite transactions; never open a write connection to `data/aive.db`
  - On `RecordingError`, write fallback JSON to `data/exports/validation_fallback_{run_id}.json`
  - **Files**: `validation/score_recorder.py`

- [x] 4. Implement TestBase abstract class
  - Create `validation/base_test.py`
  - Define abstract `run(config, fixtures) -> TestResult`
  - Implement `load_fixtures(fixture_path) -> dict` — raises `FixtureError` if file missing or malformed
  - Implement `compute_pass(scores) -> bool` — pure function of scores and `self.pass_threshold`
  - Add post-run assertion: `result.passed == compute_pass(result.scores)`, raise `AssertionError` if mismatch
  - Support standalone execution: when run as `__main__`, execute with default fixtures and print JSON
  - **Files**: `validation/base_test.py`

- [x] 5. Patch agents/base.py to support AIVE_DISABLE_AGENT
  - Read `AIVE_DISABLE_AGENT` env var at the top of `call_llm()`
  - If the `agent` parameter value matches `AIVE_DISABLE_AGENT`, return `{}` immediately without making any LLM call
  - Add a comment explaining this is used exclusively by T8 ablation tests
  - **Files**: `agents/base.py`

- [x] 6. Create extraction fixtures (T1)
  - Create `validation/fixtures/extraction_fixtures.json`
  - Include at least one item per difficulty: `easy` (LoRA paper), `medium` (Knowledge Tracing paper), `hard` (RLHF paper)
  - Each item: `item_id`, `item_type`, `difficulty`, `expected_problem`, `expected_technology`, `expected_keywords`, `source_sentences`, and a truncated `raw_text` excerpt
  - **Files**: `validation/fixtures/extraction_fixtures.json`

- [x] 7. Create cross-document and false-opportunity fixtures (T2, T3)
  - Create `validation/fixtures/cross_doc_fixtures.json` with one multi-source pack: paper on local LLMs, paper on teacher workload, patent on knowledge tracing, startup on assessment software; include `human_panel_baseline` opportunity description
  - Create `validation/fixtures/false_opportunity_fixtures.json` with at least 5 nonsense combos (e.g., Blockchain + Teacher Attendance), each with `combo`, `technology`, `problem`, `market`, `expected_verdict: "rejected"`
  - **Files**: `validation/fixtures/cross_doc_fixtures.json`, `validation/fixtures/false_opportunity_fixtures.json`

- [x] 8. Create ultimate test fixtures (T10)
  - Create `validation/fixtures/ultimate_fixtures.json` with rating dimension definitions (`surprise`, `value`, `actionability`, `would_build`), thresholds, and rater persona templates for PersonaSimulator
  - **Files**: `validation/fixtures/ultimate_fixtures.json`

- [x] 9. Implement ExtractionEvaluator
  - Create `validation/evaluators/extraction_eval.py`
  - Implement `score(ground_truth, extracted) -> ExtractionScore`
  - Build LLM prompt returning JSON with `problem_accuracy` (0–10), `technology_accuracy` (0–10), `hallucination_count` (int), `hallucinated_claims` (list)
  - Only mark a claim hallucinated when unambiguously absent from source
  - Retry once with `agent="extractor"` on LLM failure
  - Validate: `problem_accuracy` and `technology_accuracy` must be in [0.0, 10.0]
  - **Files**: `validation/evaluators/__init__.py`, `validation/evaluators/extraction_eval.py`

- [x] 10. Implement NoveltySearcher
  - Create `validation/evaluators/novelty_search.py`
  - Implement `search(opportunity) -> NoveltyResult` and `batch_search(opportunities) -> list[NoveltyResult]`
  - Build search queries from high-level keywords only — never include raw opportunity text verbatim
  - Use `requests` with 10-second timeout; on timeout classify as `uncertain`
  - Query at least one of: Google Custom Search API, YC, ProductHunt, Crunchbase
  - Cache results in `validation.db` by `opportunity_id`
  - `novel` = no match found; `exists` = match found; warn in `details.warnings` if uncertain rate > 20%
  - **Files**: `validation/evaluators/novelty_search.py`

- [x] 11. Implement PersonaSimulator
  - Create `validation/evaluators/persona_simulator.py`
  - Implement `simulate_founder_panel(opportunity, n_founders=5) -> list[FounderResponse]`
  - Implement `simulate_investor_panel(opportunity, personas) -> list[InvestorResponse]`
  - Founder asks: `would_pay`, `would_build`, `would_not_find_themselves`, `reasoning`
  - Investor produces: `reaction` (`"Interesting"` | `"Massive opportunity"` | `"Pass"`), `reasoning`, `follow_up_questions`
  - Distinct system prompts per persona; all LLM calls via `call_llm()`
  - **Files**: `validation/evaluators/persona_simulator.py`

- [x] 12. Implement GraphAuditor
  - Create `validation/evaluators/graph_auditor.py`
  - Implement `sample_edges(n=50) -> list[Edge]` from `data/aive.db` read-only
  - Implement `audit_edge(edge) -> EdgeAuditResult` — LLM judges `is_valid` + `reasoning`
  - Implement `batch_audit(edges) -> GraphAuditReport` — `precision = valid_count / len(edges)`, `passed = precision > 0.90`
  - On LLM failure for single edge: mark as `error`, continue
  - **Files**: `validation/evaluators/graph_auditor.py`

- [x] 13. Implement T1 — Extraction Accuracy Test
  - Create `validation/tests/t1_extraction.py`
  - Load `extraction_fixtures.json`, evaluate each item using ExtractionEvaluator with asyncio concurrency limit 3
  - `passed = avg_problem_accuracy > 8.5 AND avg_technology_accuracy > 8.5 AND total_hallucinations < 5`
  - If >50% items error: `passed = False`, `error = "too_many_item_errors"`
  - **Files**: `validation/tests/__init__.py`, `validation/tests/t1_extraction.py`

- [x] 14. Implement T2 — Cross-Document Reasoning Test
  - Create `validation/tests/t2_cross_doc.py`
  - Load `cross_doc_fixtures.json`, run multi-source pack through opportunity finder
  - LLM rates resulting opportunity vs `human_panel_baseline` on `non_obvious_score` (0–10)
  - `passed = non_obvious_score > 7.0`; record baseline and reasoning in `details`
  - **Files**: `validation/tests/t2_cross_doc.py`

- [ ] 15. Implement T3 — False Opportunity Rejection Test
  - Create `validation/tests/t3_false_opportunity.py`
  - Load `false_opportunity_fixtures.json`, submit each to `agents/critic.py`
  - `rejection_rate = rejected_count / total`; `passed = rejection_rate == 1.0`
  - Record false positives in `details.false_positives`
  - **Files**: `validation/tests/t3_false_opportunity.py`

- [ ] 16. Implement T4 — Novelty Search Test
  - Create `validation/tests/t4_novelty.py`
  - Accept batch of 50 opportunities; call `NoveltySearcher.batch_search()`
  - `unique_opportunities_pct = novel_count / 50 * 100`; `passed = pct > 30`
  - Append warning if `uncertain_count / 50 > 0.2`
  - **Files**: `validation/tests/t4_novelty.py`

- [ ] 17. Implement T5 — Founder Panel Test
  - Create `validation/tests/t5_founder.py`
  - Default: `PersonaSimulator.simulate_founder_panel(opportunity, n_founders=5)`
  - `--live` mode: CLI questionnaire or Flask form
  - `passed = would_not_find_themselves_count >= 3`
  - Record all reasoning in `details.founder_responses`
  - **Files**: `validation/tests/t5_founder.py`

- [ ] 18. Implement T6 — Investor Panel Test
  - Create `validation/tests/t6_investor.py`
  - Default: `PersonaSimulator.simulate_investor_panel()` for YC, Sequoia, a16z personas
  - `passed = any(reaction == "Massive opportunity")`
  - Record reactions, reasoning, follow-ups in `details.investor_responses`
  - **Files**: `validation/tests/t6_investor.py`

- [ ] 19. Implement T7 — Graph Quality Test
  - Create `validation/tests/t7_graph_quality.py`
  - `GraphAuditor.sample_edges(50)` → `batch_audit()`
  - `passed = edge_precision > 0.90`; record per-edge results in `details.edge_audits`
  - **Files**: `validation/tests/t7_graph_quality.py`

- [ ] 20. Implement T8 — Destruction Test
  - Create `validation/tests/t8_destruction.py`
  - Baseline: all agents active, score opportunity batch
  - Ablation loop for each of `research_analyst`, `patent_analyst`, `startup_analyst`: set `AIVE_DISABLE_AGENT`, run, score, clear in `finally` block
  - `contribution_delta = baseline - ablated`; `passed = all deltas > 0`
  - Record ranked deltas in `details.contribution_deltas`
  - **Files**: `validation/tests/t8_destruction.py`

- [ ] 21. Implement T9 — Commercialization Test
  - Create `validation/tests/t9_commercialization.py`
  - Load `critic_verdict = "survived"` opportunities from `data/aive.db` (read-only)
  - "Who writes the first cheque?" LLM prompt per opportunity; score 1 if identified, 0 if not
  - `commercialization_rate = sum / total`; `passed = rate >= 0.5`
  - Record verdicts in `details.commercialization_verdicts`
  - **Files**: `validation/tests/t9_commercialization.py`

- [ ] 22. Implement T10 — Ultimate AIVE Test
  - Create `validation/tests/t10_ultimate.py`
  - Requires exactly 10 critic-surviving opportunities
  - 20 raters via PersonaSimulator (default) or `--live` Flask form with `--resume` support
  - 4 dimensions per opportunity per rater: `surprise`, `value`, `actionability`, `would_build`
  - `passed = any opportunity with avg_surprise > 8 AND avg_value > 8 AND avg_would_build > 6`
  - `< 20 responses` in non-live mode → `error = "insufficient_responses"` → record as `errored`
  - Record full rating matrix in `details.rating_matrix`
  - **Files**: `validation/tests/t10_ultimate.py`

- [ ] 23. Implement Suite Runner
  - Create `validation/run_suite.py` as CLI entry point and importable `run_suite()` function
  - `--tests T1 T4 T7`, `--label`, `--live`, `--resume` CLI flags
  - Invalid test ID → exit non-zero with error listing valid IDs
  - Catch unhandled exceptions per test → record as `errored`, continue
  - Automated tests (T1–T4, T7–T9) require no user interaction
  - T10 marked `pending` if collection incomplete; does not block suite
  - Write `data/exports/validation_report_{run_id}.json`; print Markdown summary to stdout
  - Initialize `data/validation.db` on first run
  - **Files**: `validation/run_suite.py`

- [ ] 24. Implement human panel collection interface
  - Create `validation/collect_human.py`
  - CLI mode: prompt raters with opportunity details, collect integer ratings 0–10
  - Flask mode: minimal form per opportunity per rater with CSRF token validation
  - Validate ratings are integers in [0, 10]; reject invalid values with descriptive error
  - Store responses in `validation.db` immediately; support `--resume` to collect only missing responses
  - **Files**: `validation/collect_human.py`

- [ ] 25. Update dependencies and add unit tests
  - Add `hypothesis>=6.100.0`, `flask>=3.0.0`, `requests>=2.32.0` to `requirements.txt`
  - `test_score_recorder.py` — SQLite read/write, deduplication, report generation with mock data
  - `test_extraction_eval.py` — scoring logic with mock `call_llm()`; verify score bounds [0.0, 10.0]
  - `test_novelty_search.py` — query construction and deduplication with mock HTTP responses
  - `test_base_test.py` — property test: `compute_pass` is pure; `report.passed + failed + errored == total`
  - **Files**: `requirements.txt`, `validation/tests/unit/__init__.py`, `validation/tests/unit/test_score_recorder.py`, `validation/tests/unit/test_extraction_eval.py`, `validation/tests/unit/test_novelty_search.py`, `validation/tests/unit/test_base_test.py`

## Notes

- Run the full suite: `python validation/run_suite.py`
- Run specific tests: `python validation/run_suite.py --tests T1 T7`
- Run a single test standalone: `python validation/tests/t1_extraction.py`
- Human panel mode: `python validation/run_suite.py --live`
- Resume incomplete T10: `python validation/run_suite.py --tests T10 --resume`
- The validation suite is read-only against `data/aive.db` — all results go to `data/validation.db`
- T8 ablation uses `AIVE_DISABLE_AGENT` env var, patched into `agents/base.py` in task 5
- T1/T2 use asyncio with concurrency limit 3 to avoid overloading local Ollama
- T4 novelty search caches results to avoid redundant API calls across runs
