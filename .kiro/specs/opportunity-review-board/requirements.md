# Requirements Document

## Introduction

The Opportunity Review Board is a human validation layer for AIVE. Its purpose is to
answer the question: "Did AIVE surface insights that independent people would not have
connected themselves?" It extends the existing automated Critic (Layer 5) with a
structured, multi-reviewer scoring workflow, agreement analysis, and milestone detection.
The board is additive to the machine Critic — it does not replace or re-run Critic
verdicts.

The extended opportunity formula this feature operates over is:

```
Problem + Technology + Market + Urgency + Distribution = Opportunity
```

Two new dimensions — Urgency and Distribution — are scored by human reviewers and are
separate from the machine Critic's existing six kill-flags. Critic verdicts are
immutable; human scores cannot change them.

---

## Glossary

- **Review_Board_CLI**: The command-line interface that drives a single reviewer through
  a structured scoring session for one or more opportunities.
- **Reviewer**: A human participant who scores opportunities via the Review_Board_CLI.
  Each reviewer has a unique identity and an assigned role.
- **Reviewer_Role**: A categorical label assigned to a reviewer. Valid values: `founder`,
  `researcher`, `student`, `builder`.
- **Review_Session**: A single sitting in which one Reviewer scores one or more
  opportunities. A session produces one feedback record per scored opportunity.
- **Scoring_Rubric**: The five human dimensions evaluated per opportunity: Novelty,
  Market, Timing, Defensibility, Surprising. Each dimension is scored 0–10 inclusive.
- **Urgency_Score**: A reviewer-assigned integer (0–10 inclusive) representing how
  time-sensitive the opportunity is, extending the base opportunity formula.
- **Distribution_Score**: A reviewer-assigned integer (0–10 inclusive) representing how
  tractable the go-to-market path is, extending the base opportunity formula.
- **Extended_Score**: The sum `Novelty + Market + Timing + Defensibility + Surprising +
  Urgency + Distribution` for a single review record (range 0–70 inclusive).
- **Aggregated_Score**: The arithmetic mean of Extended_Scores across all
  Feedback_Records for the same opportunity, rounded to 2 decimal places.
- **Agreement_Rate**: For a given opportunity with ≥2 Feedback_Records, the fraction of
  reviewer pairs (expressed as a decimal 0.0–1.0, rounded to 2 decimal places) whose
  Extended_Scores differ by ≤10 points. Reported as "N/A" when fewer than 2
  Feedback_Records exist.
- **Divergence_Flag**: A boolean re-evaluated on every write. Set to `true` when any two
  Feedback_Records for the same opportunity have Extended_Scores that differ by more
  than 20 points.
- **Milestone_Threshold**: A positive integer ≥ 1. The minimum number of distinct
  Reviewers who must independently mark `surprising ≥ 8` AND
  `would_not_have_connected = true` for an opportunity to reach milestone status.
  Default value: 5.
- **Milestone_Status**: A boolean property of an opportunity. `true` when the count of
  qualifying distinct Reviewer records meets or exceeds the Milestone_Threshold.
- **Review_Report**: A structured Markdown document summarising AIVE machine scores,
  human scores, per-reviewer records, agreement statistics, and milestone status for
  each reviewed opportunity.
- **Opportunity_Record**: A row in the `opportunities` table, as defined by the existing
  `db/schema.sql`.
- **Feedback_Record**: A row in the `opportunity_feedback` table, extended by this
  feature to include reviewer identity, role, and the new scoring dimensions.
- **Critic_Verdict**: The machine decision (`survived` | `rejected`) recorded in
  `opportunities.critic_verdict`. This field is read-only from the perspective of the
  Review Board.

---

## Requirements

### Requirement 1: Review Board CLI — Session Flow

**User Story:** As a Reviewer, I want a guided CLI session that walks me through scoring
each surviving opportunity so that I can provide structured human feedback without
remembering the rubric format.

#### Acceptance Criteria

1. WHEN a Reviewer launches the Review_Board_CLI with a valid reviewer identity and
   role, THE Review_Board_CLI SHALL display the Reviewer's name, role, and the total
   number of Opportunity_Records available for scoring before presenting the first
   opportunity. A valid reviewer identity is a non-empty `--reviewer-id` string and a
   `--role` value that is one of the four Reviewer_Role values.

2. WHEN the Review_Board_CLI presents an opportunity, THE Review_Board_CLI SHALL display
   the opportunity title, problem, technology, market, timing signal, reasoning, machine
   scores (novelty, timing, market, feasibility, confidence), and the Critic_Verdict
   summary.

3. WHEN a Reviewer provides a score for a Scoring_Rubric dimension, THE
   Review_Board_CLI SHALL accept only integer values in the range 0–10 inclusive.

4. IF a Reviewer enters a value outside 0–10 for any scoring dimension, THEN THE
   Review_Board_CLI SHALL display a validation error and re-prompt for that dimension
   without discarding previously entered scores for that opportunity.

5. WHEN a Reviewer has answered all seven scoring dimensions (Novelty, Market, Timing,
   Defensibility, Surprising, Urgency, Distribution) for an opportunity, THE
   Review_Board_CLI SHALL prompt the Reviewer to confirm submission before persisting the
   Feedback_Record.

6. IF a Reviewer attempts to submit a Feedback_Record before all seven dimensions have
   been scored, THEN THE Review_Board_CLI SHALL display an error identifying the missing
   dimensions and SHALL NOT persist the record.

7. WHEN a Reviewer confirms submission, THE Review_Board_CLI SHALL persist the
   Feedback_Record and display the saved Feedback_Record ID before advancing to the next
   opportunity.

8. WHEN a Review_Session ends (all selected opportunities scored or Reviewer exits),
   THE Review_Board_CLI SHALL display a session summary showing: the count of
   opportunities scored, and the Reviewer's average Extended_Score across the session
   computed as (sum of all dimension scores across all scored opportunities) ÷ (number
   of scored opportunities), rounded to 2 decimal places.

9. WHERE a Reviewer uses the `--opportunity` flag with one or more opportunity IDs, THE
   Review_Board_CLI SHALL restrict the session to only those opportunities, in the order
   specified.

10. IF the `--reviewer-id` argument is missing or empty, or if the `--role` argument is
    not one of the four valid Reviewer_Role values, THEN THE Review_Board_CLI SHALL
    display an error message and exit with a non-zero status code before presenting any
    opportunity.

---

### Requirement 2: Reviewer Profiles

**User Story:** As the AIVE system, I want every Feedback_Record tagged with the
Reviewer's identity and role so that aggregation can distinguish founder perspective
from researcher perspective from builder perspective.

#### Acceptance Criteria

1. THE Review_Board_CLI SHALL require a `--reviewer-id` argument (a non-empty string
   unique per person) and a `--role` argument (one of `founder`, `researcher`, `student`,
   `builder`) at session start.

2. IF the `--role` argument is not one of the four valid Reviewer_Role values, THEN THE
   Review_Board_CLI SHALL display an error message listing the valid roles and exit with
   a non-zero status code before presenting any opportunity.

3. IF the `--reviewer-id` argument is absent or is an empty string, THEN THE
   Review_Board_CLI SHALL display an error message stating that a non-empty reviewer
   identity is required and exit with a non-zero status code before presenting any
   opportunity.

4. WHEN a Feedback_Record is persisted, THE Feedback_Store SHALL store the
   `reviewer_id`, `reviewer_role`, `urgency_score`, `distribution_score`,
   `would_not_have_connected`, and all five Scoring_Rubric dimension scores alongside
   the UTC timestamp of submission.

5. WHEN a Reviewer submits a Feedback_Record for an `opportunity_id` that already has a
   record from the same `reviewer_id`, THE Feedback_Store SHALL overwrite the existing
   record in place, updating all scoring fields and the submission timestamp, so that
   exactly one Feedback_Record per `reviewer_id`–`opportunity_id` pair exists at all
   times.

6. WHEN a Reviewer launches the Review_Board_CLI and has already scored one or more
   opportunities in a prior session, THE Review_Board_CLI SHALL display the list of
   previously scored opportunity IDs and titles, and SHALL prompt the Reviewer to choose
   whether to skip or re-score each one before that opportunity is presented.

---

### Requirement 3: Multi-Reviewer Aggregation

**User Story:** As a researcher or founder, I want to see how multiple reviewers scored
the same opportunity so that I can identify consensus and surface interesting divergence.

#### Acceptance Criteria

1. WHEN the Aggregation_Engine computes the Aggregated_Score for an opportunity with at
   least one Feedback_Record, THE Aggregation_Engine SHALL compute it as the arithmetic
   mean of Extended_Scores across all Feedback_Records for that opportunity, rounded to
   2 decimal places, regardless of the order in which those records were submitted.

2. THE Aggregation_Engine SHALL produce the same Aggregated_Score for any permutation of
   the input Feedback_Records (commutativity property).

3. IF an opportunity has fewer than 2 Feedback_Records, THEN THE Aggregation_Engine
   SHALL report Agreement_Rate as "N/A" for that opportunity.

4. WHEN the Aggregation_Engine evaluates Agreement_Rate for an opportunity with at least
   two Feedback_Records, THE Aggregation_Engine SHALL compute the fraction of reviewer
   pairs whose Extended_Scores differ by ≤10, expressed as a decimal 0.0–1.0 rounded to
   2 decimal places.

5. WHEN any two Feedback_Records for the same opportunity have Extended_Scores that
   differ by more than 20 points, THE Aggregation_Engine SHALL set the Divergence_Flag
   to `true` for that opportunity. THE Aggregation_Engine SHALL re-evaluate the
   Divergence_Flag each time a Feedback_Record for that opportunity is written or
   overwritten.

6. WHEN the Aggregation_Engine computes per-dimension means, THE Aggregation_Engine
   SHALL deduplicate Feedback_Records by `reviewer_id` (keeping the most recent record
   per reviewer) before computing, so that adding a second record with identical scores
   for the same `reviewer_id` does not change any per-dimension mean.

7. THE Aggregation_Engine SHALL associate every aggregated result with the complete set
   of distinct `reviewer_id` values that contributed to it, and SHALL never include
   scores from one `opportunity_id` in the aggregate of a different `opportunity_id`.

---

### Requirement 4: Milestone Detection

**User Story:** As the project lead, I want the system to automatically flag when an
opportunity has reached the "5 people say I didn't think of that" threshold so that
AIVE can declare its first major milestone.

#### Acceptance Criteria

1. WHEN the Milestone_Detector evaluates an opportunity, THE Milestone_Detector SHALL
   set Milestone_Status to `true` if and only if the count of distinct Feedback_Records
   where `surprising ≥ 8` (on a scale of 1–10 inclusive) AND
   `would_not_have_connected = true` is greater than or equal to the
   Milestone_Threshold, where Milestone_Threshold is a positive integer ≥ 1.

2. WHEN the Milestone_Detector evaluates the same set of Feedback_Records more than
   once, THE Milestone_Detector SHALL return the same Milestone_Status each time
   (determinism property).

3. WHEN the Milestone_Threshold is set to N and exactly N − 1 qualifying Feedback_Records
   exist for an opportunity, THE Milestone_Detector SHALL set Milestone_Status to
   `false`.

4. WHEN the Milestone_Threshold is set to N and exactly N qualifying Feedback_Records
   exist for an opportunity, THE Milestone_Detector SHALL set Milestone_Status to
   `true`.

5. WHEN a Reviewer submits a Feedback_Record that overwrites a prior record for the same
   `reviewer_id` and `opportunity_id`, THE Milestone_Detector SHALL use the record with
   the latest submission timestamp for that reviewer when evaluating the qualifying
   count. IF two records for the same reviewer have identical timestamps, THE
   Milestone_Detector SHALL use the record most recently written to the Feedback_Store.

6. WHEN an opportunity's Milestone_Status transitions from `false` to `true` for the
   first time, THE Milestone_Detector SHALL emit exactly one console notification of the
   form: "MILESTONE: [opportunity title] reached [N] independent confirmations."

7. WHEN the Milestone_Detector re-evaluates an opportunity whose Milestone_Status is
   already `true`, THE Milestone_Detector SHALL NOT emit an additional notification.

8. THE Milestone_Detector SHALL evaluate Milestone_Status using only the count of
   qualifying records; it SHALL NOT inspect or modify the `critic_verdict`,
   `critic_notes`, or any other field in the `opportunities` table.

---

### Requirement 5: Distribution Dimension

**User Story:** As a builder or founder, I want to score Urgency and Distribution for
each opportunity so that the extended formula Problem + Technology + Market + Urgency
+ Distribution is fully represented in the human review layer.

#### Acceptance Criteria

1. THE Feedback_Store SHALL persist `urgency_score` (integer 0–10 inclusive) and
   `distribution_score` (integer 0–10 inclusive) as distinct fields in every
   Feedback_Record.

2. WHEN the Review_Board_CLI prompts for Urgency, THE Review_Board_CLI SHALL display the
   definition: "How time-sensitive is this opportunity? (0 = no urgency, 10 = window
   closes within 12 months)."

3. WHEN the Review_Board_CLI prompts for Distribution, THE Review_Board_CLI SHALL
   display the definition: "How tractable is reaching the target customer? (0 =
   no path to market, 10 = clear, validated channel)."

4. WHEN the Extended_Score is computed for a Feedback_Record, THE Scoring_Engine SHALL
   compute it as the sum of all seven fields: Novelty + Market + Timing + Defensibility
   + Surprising + Urgency + Distribution.

5. THE Scoring_Engine SHALL NOT read from or write to the `critic_verdict`,
   `critic_notes`, `novelty_score`, `timing_score`, `market_score`, `feasibility`, or
   `confidence_score` fields in the `opportunities` table when computing or persisting
   any human scoring dimension.

6. WHEN a Feedback_Record is created for an opportunity that was evaluated by the Critic
   before the Distribution Dimension existed, THE Scoring_Engine SHALL persist
   `urgency_score` and `distribution_score` in the new Feedback_Record without altering
   any field in the existing Opportunity_Record.

7. IF a Reviewer enters a value outside 0–10 for `urgency_score` or
   `distribution_score`, THEN THE Review_Board_CLI SHALL apply the same validation
   error and re-prompt behaviour defined for Scoring_Rubric dimensions in Requirement
   1 AC4.

---

### Requirement 6: Review Report

**User Story:** As the project lead, I want a generated Markdown report that shows AIVE
machine scores, human scores, agreement statistics, and milestone status for each
reviewed opportunity so that I can make a go/no-go decision on AIVE's first milestone.

#### Acceptance Criteria

1. WHEN the Report_Generator is invoked, THE Report_Generator SHALL produce a Markdown
   file containing one section per reviewed opportunity, ordered by Aggregated_Score
   descending.

2. FOR EACH opportunity section in the report, THE Report_Generator SHALL include: the
   opportunity title, Critic_Verdict, machine scores (novelty, timing, market,
   feasibility, confidence), Aggregated_Score rounded to 2 decimal places, Agreement_Rate
   (or "N/A" when fewer than 2 reviewers), per-reviewer breakdown (reviewer ID, role,
   Extended_Score, notes), Divergence_Flag, and Milestone_Status.

3. WHEN the Report_Generator includes per-reviewer data, THE Report_Generator SHALL
   display reviewer identity as the `reviewer_id` string and SHALL NOT expose any field
   that is not one of: `reviewer_id`, `reviewer_role`, Extended_Score, the seven
   individual dimension scores, `notes`, and submission timestamp.

4. WHEN the Report_Generator is invoked with the `--milestone-only` flag, THE
   Report_Generator SHALL include only opportunities where Milestone_Status is `true`.

5. WHEN the Report_Generator is invoked with the `--min-reviewers N` flag (N ≥ 1), THE
   Report_Generator SHALL exclude opportunities that have fewer than N Feedback_Records
   after deduplication by `reviewer_id`.

6. WHEN the Report_Generator is invoked with both `--milestone-only` and
   `--min-reviewers N`, THE Report_Generator SHALL apply both filters and include only
   opportunities that satisfy both conditions simultaneously.

7. WHEN no opportunities remain after applying all active filters, THE Report_Generator
   SHALL produce a report containing only the summary section and a single line stating
   "No opportunities matched the specified filters."

8. THE Report_Generator SHALL include a summary section at the top of the report
   containing: total opportunities reviewed, count with Milestone_Status `true`, overall
   Agreement_Rate computed as the mean of per-opportunity Agreement_Rates (excluding
   opportunities with fewer than 2 reviewers from this mean), and the Reviewer_Role
   distribution showing the count of distinct reviewers per role.

9. WHEN the Report_Generator writes the output file, THE Report_Generator SHALL write it
   to `data/exports/review_report_<timestamp>.md` where `<timestamp>` is the UTC
   datetime in `YYYYMMDD_HHMMSS` format.

10. WHEN the Report_Generator is invoked twice with identical input Feedback_Records and
    Opportunity_Records, THE Report_Generator SHALL produce reports with identical
    section content, excluding only the output filename timestamp.

---

### Requirement 7: Schema Migration

**User Story:** As a developer, I want the database schema extended with the new fields
required by the Review Board so that all components can persist and query review data
without breaking existing records.

#### Acceptance Criteria

1. THE Migration_Script SHALL add the following columns to the `opportunity_feedback`
   table: `reviewer_id` (TEXT), `reviewer_role` (TEXT), `urgency_score` (INTEGER),
   `distribution_score` (INTEGER), and `would_not_have_connected` (INTEGER DEFAULT 0).

2. WHEN the Migration_Script is run against a database that already has an
   `opportunity_feedback` table with existing rows, THE Migration_Script SHALL preserve
   all existing rows; the four nullable columns (`reviewer_id`, `reviewer_role`,
   `urgency_score`, `distribution_score`) SHALL be set to NULL for pre-existing rows,
   and `would_not_have_connected` SHALL be set to 0 for pre-existing rows (SQLite
   DEFAULT behaviour).

3. IF the Migration_Script is run against a database where all five columns already
   exist, THEN THE Migration_Script SHALL complete without raising an exception, without
   duplicating any column, and SHALL exit with a zero return code.

4. WHEN the Migration_Script completes successfully, THE Migration_Script SHALL print one
   confirmation line per column in the format: "Added: <column_name>" if the column was
   newly created, or "Present: <column_name>" if the column already existed.

5. IF an unexpected error occurs during migration (e.g. disk full, permission denied),
   THEN THE Migration_Script SHALL preserve the existing schema without partial writes,
   print the error to stderr, and exit with a non-zero return code.

---

### Requirement 8: Correctness Properties for Property-Based Testing

**User Story:** As a developer, I want the core aggregation and milestone logic verified
by property-based tests so that correctness is maintained as the codebase evolves.

#### Acceptance Criteria

1. THE Aggregation_Engine SHALL return the same Aggregated_Score for any permutation of
   a non-empty list of Feedback_Records for the same opportunity (commutativity /
   order-independence).

2. THE Aggregation_Engine SHALL return an Aggregated_Score in the range [0.0, 70.0]
   inclusive for any non-empty list of Feedback_Records.

3. THE Milestone_Detector SHALL return the same Milestone_Status boolean for any
   Milestone_Threshold value N ≥ 1 when evaluated against the same set of
   Feedback_Records (determinism).

4. IF no Feedback_Record in a given list has both `surprising ≥ 8` and
   `would_not_have_connected = true`, THEN THE Milestone_Detector SHALL return
   Milestone_Status `false` for any Milestone_Threshold ≥ 1.

5. WHEN the count of Feedback_Records satisfying `surprising ≥ 8` AND
   `would_not_have_connected = true` equals the Milestone_Threshold N, THE
   Milestone_Detector SHALL return Milestone_Status `true`.

6. WHEN a Feedback_Record whose `reviewer_id` and `opportunity_id` match an existing
   record is added and all seven scoring fields (`novelty`, `market`, `timing`,
   `defensibility`, `surprising`, `urgency_score`, `distribution_score`) are identical
   to the existing record, THE Aggregation_Engine SHALL return the same Aggregated_Score
   after deduplication as before the duplicate was added (idempotence after
   deduplication).

7. FOR any non-empty list of Feedback_Records split into two non-overlapping subsets A
   and B that together cover all records, THE Aggregation_Engine's Aggregated_Score on
   the full list SHALL equal
   `(mean(A) × |A| + mean(B) × |B|) / (|A| + |B|)` — confirming confluence under
   partition.

8. THE Report_Generator SHALL produce reports with identical section content (excluding
   only the output filename timestamp) for any two invocations supplied with identical
   Feedback_Records and Opportunity_Records (deterministic output property).
