# Requirements Document

## Introduction

The AIVE Validation Suite is a comprehensive testing and measurement framework that answers the central question: *"Does this machine produce better insights than a human would find manually?"* It wraps the existing AIVE pipeline — research/patent/startup analysts, knowledge graph, opportunity finder, and critic — without modifying any of them. The suite runs ten distinct test categories covering extraction accuracy, cross-document reasoning, false-positive rejection, novelty, founder and investor panel reactions, knowledge graph quality, per-agent contribution, commercialization viability, and ultimate human-rated quality. All results are stored in a dedicated `data/validation.db` database and a single command (`python validation/run_suite.py`) executes the full suite or any subset of tests.

---

## Glossary

- **Suite_Runner**: The orchestration module (`validation/run_suite.py`) that registers, schedules, and executes all test modules.
- **Test_Module**: An individual test class inheriting from `TestBase` (e.g., `T1ExtractionAccuracy`).
- **Score_Recorder**: The persistence component (`validation/score_recorder.py`) that writes and reads `TestResult` objects to/from `validation.db`.
- **Validation_DB**: The SQLite database at `data/validation.db` that stores all test results. Distinct from `aive.db`.
- **AIVE_DB**: The production SQLite database at `data/aive.db`. The validation suite never writes to this database.
- **TestResult**: A structured dataclass capturing a single test's outcome, scores, thresholds, and any error.
- **SuiteReport**: An aggregate report summarising pass/fail/error counts and per-test results for one complete run.
- **Fixture**: Versioned, canned input data stored in `validation/fixtures/` as JSON files used to make tests reproducible.
- **ExtractionEvaluator**: The LLM-as-judge component that scores analyst extractions against ground truth.
- **NoveltySearcher**: The component that queries external sources (Google, YC, ProductHunt, Crunchbase) to determine whether an opportunity already exists.
- **PersonaSimulator**: The LLM-based component that simulates founder and investor personas when real humans are unavailable.
- **GraphAuditor**: The component that samples knowledge-graph edges and uses an LLM to judge semantic validity.
- **run_id**: A unique identifier assigned to each suite execution, used to group all per-test results together.
- **LLM_Provider**: The configured LLM backend, accessed exclusively via `agents/base.py` `call_llm()`.
- **Ablation**: The process of disabling one analyst agent at a time (T8) to measure its individual contribution.
- **AIVE_DISABLE_AGENT**: An environment variable read by `agents/base.py` that suppresses a named agent during Ablation runs.
- **Human_Panel**: Real human raters used in tests T5, T6, and T10. Replaced by `PersonaSimulator` by default.
- **Critic**: The existing `agents/critic.py` module that rejects weak opportunities.
- **Opportunity**: A structured object produced by the AIVE Opportunity Finder containing title, problem, technology, market, and scores.
- **Edge**: A directed relationship between two nodes in the AIVE knowledge graph, stored in the `edges` table of `aive.db`.

---

## Requirements

### Requirement 1: Suite Entry Point and Selective Test Execution

**User Story:** As a developer or researcher, I want to run the entire validation suite or a subset of tests with a single CLI command, so that I can validate AIVE output quickly and reproducibly.

#### Acceptance Criteria

1. THE Suite_Runner SHALL accept an optional `--tests` argument that accepts one or more test IDs from the set `{T1, T2, T3, T4, T5, T6, T7, T8, T9, T10}`.
2. WHEN `--tests` is omitted, THE Suite_Runner SHALL execute all ten Test_Modules in sequence.
3. WHEN `--tests` is provided, THE Suite_Runner SHALL execute only the specified Test_Modules and skip the rest.
4. WHEN a test ID supplied to `--tests` is not in the valid set, THE Suite_Runner SHALL exit with a non-zero status code and print a descriptive error message listing valid test IDs.
5. THE Suite_Runner SHALL accept an optional `--label` argument that attaches a human-readable string to the run record in Validation_DB.
6. WHEN a Test_Module raises an unhandled exception, THE Suite_Runner SHALL record that test as `errored`, continue executing remaining tests, and include the error message in the final SuiteReport.
7. WHEN all selected tests have completed or errored, THE Suite_Runner SHALL write the SuiteReport to `data/exports/validation_report_{run_id}.json` and print a Markdown summary to stdout.
8. THE Suite_Runner SHALL complete a full ten-test run without requiring any user interaction for automated tests (T1–T4, T7–T9), using PersonaSimulator by default for T5, T6, and T10.

---

### Requirement 2: Validation Database Isolation

**User Story:** As a system operator, I want all validation results stored in a separate database, so that test runs never corrupt or alter production AIVE data.

#### Acceptance Criteria

1. THE Score_Recorder SHALL write all TestResult objects exclusively to `data/validation.db`.
2. THE Score_Recorder SHALL never open a write connection to `data/aive.db`.
3. WHEN `data/validation.db` does not exist at suite startup, THE Suite_Runner SHALL create it by running the schema defined in `validation/db/validation_schema.sql`.
4. THE Validation_DB SHALL contain a `test_runs` table (run_id, label, created_at, total_tests, passed, failed, errored) and a `test_results` table (id, run_id, test_id, test_name, passed, scores_json, threshold_json, details_json, error, created_at).
5. IF `data/validation.db` is locked or a write fails, THEN THE Score_Recorder SHALL raise `RecordingError` and THE Suite_Runner SHALL write all results to `data/exports/validation_fallback_{run_id}.json` as a fallback.
6. THE Validation_DB SHALL enforce a UNIQUE constraint on `(run_id, test_id)` so that recording the same TestResult twice raises an integrity error rather than creating duplicate rows.

---

### Requirement 3: TestBase Interface and Test Module Contract

**User Story:** As a developer adding or modifying a test, I want a consistent base class, so that all test modules behave predictably and are independently runnable.

#### Acceptance Criteria

1. THE TestBase SHALL expose a `run(config: dict, fixtures: dict) -> TestResult` method that every Test_Module must implement.
2. THE TestBase SHALL expose a `load_fixtures(fixture_path: Path) -> dict` method that reads a JSON fixture file and raises `FixtureError` if the file is missing or malformed.
3. THE TestBase SHALL expose a `compute_pass(scores: dict) -> bool` method that computes the pass verdict purely from `scores` and `self.pass_threshold` with no side effects.
4. WHEN a Test_Module is invoked directly (e.g., `python validation/tests/t1_extraction.py`), THE Test_Module SHALL execute its `run()` method with default fixtures and print the TestResult as JSON to stdout.
5. THE TestBase SHALL validate that the returned TestResult's `passed` field equals the result of `compute_pass(scores)`, raising `AssertionError` if they differ.

---

### Requirement 4: TestResult and SuiteReport Data Models

**User Story:** As a developer querying validation history, I want structured, typed result objects, so that I can programmatically compare results across runs.

#### Acceptance Criteria

1. THE TestResult SHALL contain the fields: `test_id` (str), `test_name` (str), `run_id` (str), `passed` (bool), `scores` (dict[str, float]), `threshold` (dict[str, float]), `details` (dict), `error` (str | None), `created_at` (ISO-8601 str).
2. THE SuiteReport SHALL contain the fields: `run_id` (str), `label` (str), `total_tests` (int), `passed` (int), `failed` (int), `errored` (int), `pass_rate` (float), `results` (list[TestResult]), `summary` (str), `created_at` (ISO-8601 str).
3. THE SuiteReport SHALL satisfy the invariant: `passed + failed + errored == total_tests` for every generated report.
4. WHEN `tests` is None, `total_tests` in the SuiteReport SHALL equal 10.
5. WHEN `tests` is a non-empty list of k distinct valid test IDs, `total_tests` in the SuiteReport SHALL equal k.

---

### Requirement 5: T1 — Extraction Accuracy Test

**User Story:** As a researcher evaluating AIVE, I want to measure how accurately the analyst agents extract problem and technology fields and how often they hallucinate, so that I can determine whether AIVE's knowledge base is reliable.

#### Acceptance Criteria

1. THE ExtractionEvaluator SHALL score each extraction against a ground-truth fixture, returning `problem_accuracy` and `technology_accuracy` in [0.0, 10.0] and a non-negative integer `hallucination_count`.
2. WHEN an extraction is evaluated, THE ExtractionEvaluator SHALL mark a claim as hallucinated only when it is unambiguously absent from the source document; uncertain claims SHALL NOT be counted as hallucinations.
3. THE T1 Test_Module SHALL load fixtures at three difficulty levels (easy, medium, hard) and evaluate every fixture item.
4. WHEN all fixture items have been scored, THE T1 Test_Module SHALL compute `avg_problem_accuracy` as the mean of all `problem_accuracy` scores and `avg_technology_accuracy` as the mean of all `technology_accuracy` scores.
5. WHEN `avg_problem_accuracy > 8.5` AND `avg_technology_accuracy > 8.5` AND `total_hallucinations < 5`, THE T1 Test_Module SHALL set `passed = True`; otherwise `passed = False`.
6. IF `call_llm()` raises an exception during evaluation of a single fixture item, THEN THE ExtractionEvaluator SHALL retry once using `agent="extractor"`; if the retry also fails, THE T1 Test_Module SHALL mark that item as `error` in details and continue with remaining items.
7. IF more than 50% of fixture items error, THEN THE T1 Test_Module SHALL set `passed = False` and `error = "too_many_item_errors"` in the TestResult.

---

### Requirement 6: T2 — Cross-Document Reasoning Test

**User Story:** As a researcher evaluating AIVE, I want to verify that the system produces non-obvious opportunities from multi-source inputs, so that I can confirm AIVE synthesises across documents rather than restating individual sources.

#### Acceptance Criteria

1. THE T2 Test_Module SHALL load a multi-source fixture pack containing at least one paper, one patent, and one startup item.
2. WHEN the opportunity finder processes the multi-source pack, THE T2 Test_Module SHALL pass the resulting opportunity to an LLM evaluator that rates it against a human-panel baseline on `non_obvious_score` (0–10).
3. WHEN `non_obvious_score > 7.0`, THE T2 Test_Module SHALL set `passed = True`; otherwise `passed = False`.
4. THE T2 Test_Module SHALL record the human-panel baseline description and the LLM evaluator's reasoning in the TestResult's `details` field.

---

### Requirement 7: T3 — False Opportunity Rejection Test

**User Story:** As a researcher evaluating AIVE, I want to confirm the Critic agent correctly rejects nonsensical opportunity combinations, so that I can trust the system's discrimination ability.

#### Acceptance Criteria

1. THE T3 Test_Module SHALL load a fixture set containing at least five nonsense opportunity combinations (e.g., "Blockchain + Teacher Attendance").
2. WHEN each nonsense opportunity is submitted to the Critic, THE T3 Test_Module SHALL record whether the Critic returned `verdict = "rejected"`.
3. WHEN the Critic returns `verdict = "survived"` for any nonsense opportunity, THE T3 Test_Module SHALL record the opportunity ID and Critic verdict in the TestResult's `details.false_positives` list.
4. WHEN all nonsense opportunities have been evaluated, THE T3 Test_Module SHALL compute `rejection_rate = rejected_count / total_nonsense_count`.
5. WHEN `rejection_rate == 1.0` (all nonsense combinations rejected), THE T3 Test_Module SHALL set `passed = True`; otherwise `passed = False`.

---

### Requirement 8: T4 — Novelty Search Test

**User Story:** As a researcher evaluating AIVE, I want to know what fraction of generated opportunities are not already covered by existing products, so that I can measure AIVE's novelty contribution.

#### Acceptance Criteria

1. THE T4 Test_Module SHALL accept a batch of exactly 50 opportunities as input.
2. WHEN evaluating an opportunity, THE NoveltySearcher SHALL query at least one external source from the set {Google, YC, ProductHunt, Crunchbase} per opportunity.
3. WHEN no external source returns an exact or near-exact match, THE NoveltySearcher SHALL classify the opportunity as `novel`.
4. WHEN at least one external source returns a matching product, THE NoveltySearcher SHALL classify the opportunity as `exists`.
5. WHEN a search request times out (exceeds 10 seconds), THE NoveltySearcher SHALL classify that opportunity as `uncertain` and SHALL NOT count it as either `novel` or `exists`.
6. THE T4 Test_Module SHALL compute `unique_opportunities_pct = (novel_count / total_opportunities) * 100`.
7. WHEN `unique_opportunities_pct > 30`, THE T4 Test_Module SHALL set `passed = True`; otherwise `passed = False`.
8. WHEN `uncertain_count / total_opportunities > 0.2`, THE T4 Test_Module SHALL append a warning to `details.warnings` recommending a re-run.
9. THE NoveltySearcher SHALL cache search results in Validation_DB by opportunity ID to prevent duplicate API calls for the same opportunity.
10. THE NoveltySearcher SHALL construct search queries from high-level keywords derived from opportunity fields and SHALL NOT include raw opportunity text verbatim in external queries.

---

### Requirement 9: T5 — Founder Panel Test

**User Story:** As a researcher evaluating AIVE, I want to measure whether experienced founders would not have found the opportunities themselves, so that I can confirm AIVE adds genuine discovery value.

#### Acceptance Criteria

1. THE T5 Test_Module SHALL simulate five distinct founder personas using PersonaSimulator by default.
2. WHEN real human founders are available (indicated by `--live` flag), THE T5 Test_Module SHALL collect responses via the human-panel collection interface instead of PersonaSimulator.
3. WHEN simulating each founder persona, THE PersonaSimulator SHALL ask whether the founder: (a) would they pay for this insight, (b) would they build this, (c) would they not have found this opportunity themselves.
4. THE T5 Test_Module SHALL count the number of founders who respond `True` to question (c) (`would_not_find_themselves`).
5. WHEN at least 3 out of 5 founder personas respond `True` to `would_not_find_themselves`, THE T5 Test_Module SHALL set `passed = True`; otherwise `passed = False`.
6. THE T5 Test_Module SHALL record each persona's reasoning in the TestResult's `details.founder_responses` list.

---

### Requirement 10: T6 — Investor Panel Test

**User Story:** As a researcher evaluating AIVE, I want to measure how YC, Sequoia, and a16z investor personas react to opportunities, so that I can calibrate the commercial relevance of AIVE outputs.

#### Acceptance Criteria

1. THE T6 Test_Module SHALL simulate investor personas for YC Partner, Sequoia Partner, and a16z Partner using PersonaSimulator by default.
2. WHEN real investor panelists are available (indicated by `--live` flag), THE T6 Test_Module SHALL collect responses via the human-panel collection interface instead of PersonaSimulator.
3. WHEN evaluating each opportunity, THE PersonaSimulator SHALL produce a reaction classified as one of: `"Interesting"`, `"Massive opportunity"`, or `"Pass"`, along with reasoning and follow-up questions.
4. THE T6 Test_Module SHALL record `interesting_count` and `massive_count` per opportunity.
5. THE T6 Test_Module SHALL record each investor persona's reaction, reasoning, and follow-up questions in the TestResult's `details.investor_responses` list.
6. WHEN at least one opportunity receives `"Massive opportunity"` from any investor persona, THE T6 Test_Module SHALL set `passed = True`; otherwise `passed = False`.

---

### Requirement 11: T7 — Graph Quality Test

**User Story:** As a researcher evaluating AIVE, I want to audit knowledge graph edge validity, so that I can ensure the graph's semantic relationships are trustworthy.

#### Acceptance Criteria

1. THE GraphAuditor SHALL sample exactly 50 random edges from the `edges` table in AIVE_DB.
2. WHEN auditing each edge, THE GraphAuditor SHALL retrieve the `label` of both the `from_node` and `to_node` and the `relationship` field.
3. WHEN auditing each edge, THE GraphAuditor SHALL call `call_llm()` to ask whether the relationship between the two node labels is semantically valid, returning `is_valid` (bool) and `reasoning` (str).
4. THE GraphAuditor SHALL compute `edge_precision = valid_edge_count / 50`.
5. WHEN `edge_precision > 0.90`, THE T7 Test_Module SHALL set `passed = True`; otherwise `passed = False`.
6. IF `call_llm()` fails for an individual edge, THEN THE GraphAuditor SHALL mark that edge as `error` in its `EdgeAuditResult` and continue with remaining edges.
7. THE T7 Test_Module SHALL record per-edge audit results in `details.edge_audits`.

---

### Requirement 12: T8 — Destruction (Ablation) Test

**User Story:** As a researcher evaluating AIVE, I want to measure each analyst agent's individual contribution by removing it and observing the quality drop, so that I can justify the multi-agent architecture.

#### Acceptance Criteria

1. THE T8 Test_Module SHALL first run the Opportunity Finder with all agents active to establish a `baseline_score`.
2. THE T8 Test_Module SHALL ablate each of the three agents (`research_analyst`, `patent_analyst`, `startup_analyst`) one at a time by setting the `AIVE_DISABLE_AGENT` environment variable to the agent's name before each ablation run.
3. WHEN an ablation run completes, THE T8 Test_Module SHALL clear `AIVE_DISABLE_AGENT` before proceeding to the next agent.
4. IF an ablation run raises an exception, THE T8 Test_Module SHALL clear `AIVE_DISABLE_AGENT` before propagating or recording the error.
5. THE T8 Test_Module SHALL compute `contribution_delta` for each agent as `baseline_score − ablated_score`.
6. WHEN all three agents have been ablated, THE T8 Test_Module SHALL set `passed = True` if every `contribution_delta > 0` (i.e. every agent meaningfully contributes); otherwise `passed = False`.
7. THE T8 Test_Module SHALL record baseline score, per-agent ablated scores, and deltas in `details.contribution_deltas`.
8. THE `agents/base.py` `call_llm()` function SHALL respect the `AIVE_DISABLE_AGENT` environment variable and return an empty result for any agent whose name matches the variable's value.

---

### Requirement 13: T9 — Commercialization Test

**User Story:** As a researcher evaluating AIVE, I want to verify that each surviving opportunity has an identifiable first-cheque writer, so that I can confirm AIVE outputs are commercially grounded.

#### Acceptance Criteria

1. THE T9 Test_Module SHALL evaluate every opportunity that has survived the Critic (i.e., `critic_verdict = "survived"` in AIVE_DB).
2. WHEN evaluating an opportunity, THE T9 Test_Module SHALL call `call_llm()` with a commercialization prompt asking: "Who writes the first cheque for this opportunity? Name the specific investor type, accelerator, or buyer."
3. WHEN the LLM cannot identify any plausible first-cheque writer, THE T9 Test_Module SHALL assign that opportunity a `commercialization_score` of 0.
4. WHEN the LLM identifies at least one plausible first-cheque writer, THE T9 Test_Module SHALL assign that opportunity a `commercialization_score` of 1.
5. THE T9 Test_Module SHALL compute `commercialization_rate = sum(commercialization_scores) / total_evaluated`.
6. WHEN `commercialization_rate >= 0.5`, THE T9 Test_Module SHALL set `passed = True`; otherwise `passed = False`.
7. THE T9 Test_Module SHALL record the identified first-cheque writers or failure reasons per opportunity in `details.commercialization_verdicts`.

---

### Requirement 14: T10 — Ultimate AIVE Test

**User Story:** As a researcher and stakeholder, I want the top-10 critic-surviving opportunities rated by 20 humans on surprise, value, actionability, and would-build, so that I can establish a ground-truth quality benchmark for AIVE.

#### Acceptance Criteria

1. THE T10 Test_Module SHALL require exactly 10 critic-surviving opportunities as input.
2. THE T10 Test_Module SHALL collect ratings from 20 raters by default using PersonaSimulator, or from real humans when the `--live` flag is set.
3. WHEN collecting ratings, THE T10 Test_Module SHALL ask each rater to score each opportunity on four dimensions: `surprise` (0–10), `value` (0–10), `actionability` (0–10), `would_build` (0–10).
4. THE T10 Test_Module SHALL compute per-opportunity average scores across all 20 raters for each dimension.
5. WHEN at least one opportunity has `avg_surprise > 8` AND `avg_value > 8` AND `avg_would_build > 6`, THE T10 Test_Module SHALL set `passed = True`; otherwise `passed = False`.
6. THE T10 Test_Module SHALL record the complete per-opportunity, per-rater rating matrix in `details.rating_matrix`.
7. IF fewer than 20 rater responses are collected and the test is not in `--live` mode, THEN THE T10 Test_Module SHALL set `error = "insufficient_responses"` and record the TestResult as `errored` (not `passed` or `failed`).
8. WHEN the `--resume` flag is supplied, THE T10 Test_Module SHALL load previously collected responses from Validation_DB and collect only the missing responses, avoiding duplication.

---

### Requirement 15: Human Panel Collection Interface

**User Story:** As a human panelist participating in T5, T6, or T10, I want a simple interface to submit my ratings, so that I can provide input without needing technical knowledge.

#### Acceptance Criteria

1. THE Suite_Runner SHALL provide a `--live` flag that switches T5, T6, and T10 from PersonaSimulator mode to human-collection mode.
2. WHEN in human-collection mode, THE Suite_Runner SHALL present each opportunity to human raters via a CLI questionnaire or a minimal Flask web form.
3. WHEN a human submits a rating, THE Score_Recorder SHALL validate that all numeric ratings are integers in [0, 10] before storage; invalid values SHALL be rejected with a descriptive error message.
4. WHEN the configured timeout for human response collection is exceeded and insufficient responses have been received, THE Suite_Runner SHALL record the test as `errored` with `error = "insufficient_responses"`.
5. WHERE Flask is used for human response collection, THE Suite_Runner SHALL enable CSRF token validation on all form submissions.

---

### Requirement 16: Score Recorder and Run History

**User Story:** As a researcher tracking AIVE improvement over time, I want to query historical test results and compare runs, so that I can observe whether AIVE improves with additional data or tuning.

#### Acceptance Criteria

1. THE Score_Recorder SHALL expose a `new_run(label: str) -> str` method that inserts a new row into `test_runs` and returns the unique `run_id`.
2. THE Score_Recorder SHALL expose a `record(run_id: str, result: TestResult) -> None` method that inserts the result into `test_results`.
3. THE Score_Recorder SHALL expose a `get_run(run_id: str) -> list[TestResult]` method that returns all results for the given run.
4. THE Score_Recorder SHALL expose a `get_history(test_id: str, limit: int) -> list[TestResult]` method that returns the most recent `limit` results for the given test.
5. THE Score_Recorder SHALL expose a `generate_report(run_id: str) -> SuiteReport` method that assembles a SuiteReport from all stored results for the run.
6. WHEN `generate_report` is called for a run_id that does not exist in Validation_DB, THE Score_Recorder SHALL raise `ValueError` with the message `"run_id not found"`.

---

### Requirement 17: LLM Integration via `call_llm()`

**User Story:** As a developer maintaining the validation suite, I want all LLM calls routed through `agents/base.py` `call_llm()`, so that the validation suite is consistent with AIVE's LLM configuration and switchable between providers.

#### Acceptance Criteria

1. THE Validation_Suite SHALL use `call_llm()` from `agents/base.py` for all LLM-as-judge evaluations (ExtractionEvaluator, PersonaSimulator, GraphAuditor, T2 evaluator, T9 commercialization evaluator).
2. THE Validation_Suite SHALL NOT import or instantiate any LLM client directly; all LLM access SHALL be via `call_llm()`.
3. WHEN `call_llm()` raises an exception, THE calling evaluator SHALL retry once with `agent="extractor"` before propagating the failure.
4. THE Validation_Suite SHALL respect the `LLM_PROVIDER` and `OLLAMA_HOST` environment variables as already defined in `agents/base.py`.

---

### Requirement 18: Fixture Management

**User Story:** As a developer running reproducible tests, I want canned fixtures for all tests that require controlled inputs, so that test results are comparable across runs regardless of database state.

#### Acceptance Criteria

1. THE Validation_Suite SHALL store all fixture files as JSON in `validation/fixtures/` with the following names: `extraction_fixtures.json` (T1), `cross_doc_fixtures.json` (T2), `false_opportunity_fixtures.json` (T3), `ultimate_fixtures.json` (T10).
2. WHEN a fixture file is missing or its JSON is malformed, THE TestBase `load_fixtures()` SHALL raise `FixtureError` and THE Suite_Runner SHALL record the associated test as `errored`.
3. THE extraction fixtures SHALL contain at least one item per difficulty level (easy, medium, hard), each with `expected_problem`, `expected_technology`, `expected_keywords`, and `source_sentences` fields.
4. THE false-opportunity fixtures SHALL contain at least five nonsense combinations, each with a `combo` description and an `expected_verdict` of `"rejected"`.

---

### Requirement 19: Performance and Concurrency

**User Story:** As a developer running the suite regularly, I want tests to complete in a reasonable time without overloading the local LLM inference server, so that the suite is practical to run daily.

#### Acceptance Criteria

1. THE T1 and T2 Test_Modules SHALL use `asyncio` with a concurrency limit of 3 simultaneous LLM calls to avoid overloading local Ollama inference.
2. THE T4 Test_Module SHALL cache NoveltySearcher results in Validation_DB by opportunity ID so that re-running the test on the same batch does not repeat external API calls.
3. THE T10 Test_Module SHALL mark itself as `pending` in the SuiteReport when human panel collection has not completed, and SHALL NOT block the rest of the suite.
4. WHEN writing to Validation_DB, THE Score_Recorder SHALL use explicit SQLite transactions to prevent partial writes; AIVE_DB SHALL never be locked by validation suite writes.

---

### Requirement 20: Project Structure and Dependencies

**User Story:** As a developer setting up the validation suite, I want a clear project layout and documented dependencies, so that I can install and run the suite without guesswork.

#### Acceptance Criteria

1. THE Validation_Suite SHALL be organised under a `validation/` directory at the project root with the sub-structure: `tests/` (10 test modules), `evaluators/` (ExtractionEvaluator, NoveltySearcher, PersonaSimulator, GraphAuditor), `fixtures/` (JSON fixture files), `db/` (schema and init script).
2. THE Validation_Suite SHALL add `hypothesis>=6.100.0`, `flask>=3.0.0`, and `requests>=2.32.0` to `requirements.txt`; all other dependencies (openai, python-dotenv) are already present.
3. THE `validation/db/validation_schema.sql` file SHALL define the `test_runs` and `test_results` tables including the UNIQUE constraint on `(run_id, test_id)`.
4. THE `validation/db/init_validation_db.py` script SHALL create `data/validation.db` by executing `validation_schema.sql` if the database does not already exist.
