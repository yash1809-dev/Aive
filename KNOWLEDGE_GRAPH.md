# AIVE — Project Knowledge Graph

> **Google Open Knowledge Graph (KG) format — entity-relationship model**
> Reference this file for instant navigation without scanning the codebase.
> Last Indexed: 2026-07-10

---

## How to Use This Graph

1. **Finding a file:** Search by entity name → get file path and connections
2. **Understanding dependencies:** Follow edges (→) to see what calls what
3. **Editing safely:** Check "affects" edges before modifying
4. **Adding new code:** Find the matching component cluster and follow patterns

---

## Entity Index (Quick Lookup)

| Entity | Type | File Path |
|---|---|---|
| `base.py` | Agent | `agents/base.py` |
| `research_analyst.py` | Agent | `agents/research_analyst.py` |
| `patent_analyst.py` | Agent | `agents/patent_analyst.py` |
| `startup_analyst.py` | Agent | `agents/startup_analyst.py` |
| `concept_extractor.py` | Agent | `agents/concept_extractor.py` |
| `graph_builder.py` | Agent | `agents/graph_builder.py` |
| `opportunity_finder.py` | Agent | `agents/opportunity_finder.py` |
| `critic.py` | Agent | `agents/critic.py` |
| `report_writer.py` | Agent | `agents/report_writer.py` |
| `ontology_scorer.py` | Agent | `agents/ontology_scorer.py` |
| `enrich_beneficiaries.py` | Agent | `agents/enrich_beneficiaries.py` |
| `quality_check.py` | Agent | `agents/quality_check.py` |
| `record_feedback.py` | Agent | `agents/record_feedback.py` |
| `reset_extractions.py` | Agent | `agents/reset_extractions.py` |
| `knowledge_graph.py` | GraphEngine | `graph/knowledge_graph.py` |
| `fetch_papers.py` | Ingest | `ingest/fetch_papers.py` |
| `fetch_economic_signals.py` | Ingest | `ingest/fetch_economic_signals.py` |
| `fetch_new_domains.py` | Ingest | `ingest/fetch_new_domains.py` |
| `import_patents.py` | Ingest | `ingest/import_patents.py` |
| `import_startups.py` | Ingest | `ingest/import_startups.py` |
| `schema.sql` | Database | `db/schema.sql` |
| `init_db.py` | Database | `db/init_db.py` |
| `migrate.py` | Database | `db/migrate.py` |
| `aive.db` | DataStore | `data/aive.db` |
| `validation.db` | DataStore | `data/validation.db` |
| `concept_cache.json` | DataStore | `data/concept_cache.json` |
| `models.py` | Validation | `validation/models.py` |
| `score_recorder.py` | Validation | `validation/score_recorder.py` |
| `base_test.py` | Validation | `validation/base_test.py` |
| `t1_extraction.py` | ValidationTest | `validation/tests/t1_extraction.py` |
| `t2_cross_doc.py` | ValidationTest | `validation/tests/t2_cross_doc.py` |
| `t3_false_opportunity.py` | ValidationTest | `validation/tests/t3_false_opportunity.py` |
| `t7_graph_quality.py` | ValidationTest | `validation/tests/t7_graph_quality.py` |
| `t9_commercialization.py` | ValidationTest | `validation/tests/t9_commercialization.py` |
| `extraction_eval.py` | Evaluator | `validation/evaluators/extraction_eval.py` |
| `graph_auditor.py` | Evaluator | `validation/evaluators/graph_auditor.py` |
| `novelty_search.py` | Evaluator | `validation/evaluators/novelty_search.py` |
| `persona_simulator.py` | Evaluator | `validation/evaluators/persona_simulator.py` |
| `run_batch.py` | Runner | `run_batch.py` |
| `run_aues.py` | Runner | `run_aues.py` |
| `rebuild_graph.py` | Runner | `rebuild_graph.py` |
| `reextract_and_rebuild.py` | Runner | `reextract_and_rebuild.py` |
| `generate_dossier.py` | Runner | `generate_dossier.py` |
| `inspect_graph.py` | Diagnostic | `inspect_graph.py` |
| `radar.py` | Diagnostic | `radar.py` |
| `status.py` | Diagnostic | `scripts/status.py` |
| `.env` | Config | `.env` |
| `PROJECT_GUIDE.md` | Docs | `PROJECT_GUIDE.md` |
| `KNOWLEDGE_GRAPH.md` | Docs | `KNOWLEDGE_GRAPH.md` |
| `DOMAIN_MAP.md` | Docs | `DOMAIN_MAP.md` |
| `AIVE_V0_SPEC.md` | Docs | `AIVE_V0_SPEC.md` |
| `AIVE_PHASE0_OPERATING_PLAN.md` | Docs | `AIVE_PHASE0_OPERATING_PLAN.md` |

---

## Knowledge Graph — Entity Relationship Model

### Format
```
[Entity A]  --[relationship]--> [Entity B]
```

---

## Cluster 1: LLM Infrastructure

```
[base.py]
  --calls-->       Ollama API (http://localhost:11434/api/chat)
  --calls-->       OpenAI API (gpt-4o-mini)
  --reads-->       .env (OLLAMA_HOST, LLM_PROVIDER, OLLAMA_MODEL_EXTRACTOR, OLLAMA_MODEL_REASONER)
  --exports-->     call_llm()
  --exports-->     call_ollama()
  --exports-->     call_openai()
  --exports-->     extract_json()
  --used_by-->     research_analyst.py
  --used_by-->     patent_analyst.py
  --used_by-->     startup_analyst.py
  --used_by-->     concept_extractor.py
  --used_by-->     opportunity_finder.py
  --used_by-->     critic.py
  --used_by-->     enrich_beneficiaries.py
  --used_by-->     graph_auditor.py (validation)
  --used_by-->     extraction_eval.py (validation)
  --used_by-->     novelty_search.py (validation)
  --used_by-->     persona_simulator.py (validation)
```

**Edit base.py when:** Switching LLM provider, changing model names, adjusting temperature, modifying system prompt, fixing JSON parse failures.

---

## Cluster 2: Data Ingestion Pipeline

```
[fetch_papers.py]
  --reads-->       arXiv API (http://export.arxiv.org/api/query)
  --writes-->      aive.db → items table (type='paper', status='pending')
  --writes-->      data/raw/papers/arxiv_{timestamp}.json
  --calls-->       init_db.py (ensures DB exists)
  --called_by-->   run_batch.py (indirectly)
  QUERY: "all:education AND (all:AI OR all:machine learning)"

[fetch_economic_signals.py]
  --writes-->      aive.db → items table (type='economic_signal')
  --contains-->    ~25 hardcoded market intelligence records
  --reads-->       init_db.py (DB_PATH)
  TOPICS: ESSER funding, teacher shortage, EdTech funding, IEP crisis, FERPA, AI regulations

[import_patents.py]
  --reads-->       data/raw/patents/ (manual text files)
  --writes-->      aive.db → items table (type='patent', status='pending')

[import_startups.py]
  --reads-->       data/raw/startups/ (CSV or text files)
  --writes-->      aive.db → items table (type='startup', status='pending')

[fetch_new_domains.py]
  --reads-->       arXiv API (alternative queries)
  --writes-->      aive.db → items table (type='paper')
```

**Edit fetch_papers.py when:** Changing arXiv search query, adjusting paper count, modifying ID format.
**Edit fetch_economic_signals.py when:** Adding new market intelligence, updating procurement data.

---

## Cluster 3: Knowledge Extraction Agents

```
[research_analyst.py]
  --imports-->     base.py (call_llm)
  --imports-->     init_db.py (DB_PATH)
  --reads-->       aive.db → items WHERE type='paper' AND status='pending'
  --writes-->      aive.db → items (problem, solution, technology, keywords, industry, impact, beneficiaries, summary)
  --sets-->        extraction_status = 'done' | 'failed'
  --uses_model-->  OLLAMA_MODEL_EXTRACTOR (qwen3:8b)
  --called_by-->   reextract_and_rebuild.py
  PROMPT_PATTERN: Noun phrases only; rejects generic output; paper-specific extraction

[patent_analyst.py]
  --imports-->     base.py (call_llm)
  --imports-->     init_db.py (DB_PATH)
  --reads-->       aive.db → items WHERE type='patent' AND status='pending'
  --writes-->      aive.db → items (same fields as research_analyst)
  --uses_model-->  OLLAMA_MODEL_EXTRACTOR
  PROMPT_PATTERN: Patent claims, prior art, technical scope

[startup_analyst.py]
  --imports-->     base.py (call_llm)
  --imports-->     init_db.py (DB_PATH)
  --reads-->       aive.db → items WHERE type='startup' AND status='pending'
  --writes-->      aive.db → items (same fields + market emphasis)
  --uses_model-->  OLLAMA_MODEL_EXTRACTOR
  PROMPT_PATTERN: Market validation, business model, target customer

[enrich_beneficiaries.py]
  --imports-->     base.py (call_llm)
  --imports-->     init_db.py (DB_PATH)
  --reads-->       aive.db → items WHERE type='paper' AND beneficiaries IS NULL
  --writes-->      aive.db → items (beneficiaries, impact)
  --uses_model-->  OLLAMA_MODEL_EXTRACTOR
  PURPOSE: Post-hoc enrichment patch; run once after bulk extraction
```

**Edit any analyst when:** Prompt needs improvement, field format changes, new extraction fields added.

---

## Cluster 4: Concept Extraction & Graph Construction

```
[concept_extractor.py]
  --imports-->     base.py (call_llm)
  --imports-->     init_db.py (DB_PATH)
  --reads-->       aive.db → items WHERE status='done'
  --reads-->       data/concept_cache.json (if exists, skips cached items)
  --writes-->      data/concept_cache.json (cache of all extraction results)
  --uses_model-->  OLLAMA_MODEL_REASONER (deepseek-r1:8b) with fallback to extractor
  --called_by-->   knowledge_graph.py (build_graph())
  NODE_TYPES: Problem, Technology, Capability, Workflow, User, Buyer, Organization,
              Competitor, Constraint, Regulation, EconomicSignal, Outcome, Resource
  RELATION_TYPES: solves, improves, benefits, purchased_by, used_by, deployed_in,
                  constrained_by, enabled_by, competes_with, produces, signals,
                  regulated_by, requires_resource
  ANTI_HALLUCINATION: evidence phrase required for each concept + edge
  QUALITY_GUARD: token overlap check between concept labels and evidence text

[knowledge_graph.py]
  --imports-->     concept_extractor.py (run())
  --reads-->       aive.db → nodes, edges (for upsert logic)
  --writes-->      aive.db → nodes table
  --writes-->      aive.db → edges table
  --exports-->     build_graph()
  --exports-->     query_technologies_for_problem()
  --exports-->     commercialization_profile()
  --called_by-->   rebuild_graph.py
  --called_by-->   reextract_and_rebuild.py
  MERGE_MAP: 50+ canonical label normalizations
  NODE_ID_FORMAT: node_{type_lower}_{slugified_label}
  EDGE_ID_FORMAT: edge_{from_id}_{rel}_{to_id}
  EDGE_QUALITY_GATES:
    - min weight 0.6
    - no self-referential
    - no single-word generic nodes
  WEIGHTS: paper=0.75, patent=0.80, startup=0.85
```

**Edit concept_extractor.py when:** Adding node types, changing relationship types, improving evidence anchoring, adjusting concept quality rules.
**Edit knowledge_graph.py when:** Adding to MERGE_MAP (most common edit), changing edge weight logic, adding new query functions, modifying graph build behavior.

**IMPORTANT:** After editing knowledge_graph.py MERGE_MAP or concept_extractor.py NODE_TYPES/RELATION_TYPES:
1. Delete `data/concept_cache.json`
2. Run `python rebuild_graph.py`
3. Run `python agents/ontology_scorer.py` to verify

---

## Cluster 5: Opportunity Discovery

```
[opportunity_finder.py]
  --imports-->     base.py (call_llm)
  --imports-->     init_db.py (DB_PATH)
  --reads-->       aive.db → nodes (Problem, Technology, Capability nodes)
  --reads-->       aive.db → edges (for connectivity check)
  --reads-->       aive.db → nodes (Buyer, EconomicSignal, Regulation as anchors)
  --writes-->      aive.db → opportunities table
  --writes-->      data/exports/opportunities_batch1.json
  --uses_model-->  OLLAMA_MODEL_REASONER with fallback to extractor
  --called_by-->   run_batch.py
  ALGORITHM:
    1. find_problems() → top 25 Problem nodes by source count
    2. find_technologies() → top 25 Technology/Capability nodes
    3. find_commercial_anchors() → Buyer, EconomicSignal, Regulation nodes
    4. find_cross_graph_combinations() → Problem × Technology × Anchor triples
    5. generate_opportunity() → LLM enrichment per candidate
    6. save_opportunity() → persist to DB
  SCORING_FORMULA:
    base 0.5
    + type_diversity * 0.2 (paper/patent/startup coverage)
    + 0.4 if commercially anchored
    + 0.2 if Buyer anchor
    + 0.3 if economic signal + paper (cross-domain bonus)
    - penalty for over-represented nodes
    - penalty for 4+ competitor startups
  ENRICHMENT_FIELDS: title, problem, technology, market, timing_signal,
                     reasoning, existing_competitors, evidence_summary,
                     buyer, regulation, economic_signal,
                     novelty_score, timing_score, market_score,
                     feasibility, confidence_score
```

**Edit opportunity_finder.py when:** Adjusting scoring formula, changing commercial anchor priority, modifying enrichment prompt, altering candidate limits.

---

## Cluster 6: Critic Engine

```
[critic.py]
  --imports-->     base.py (call_llm)
  --imports-->     init_db.py (DB_PATH)
  --reads-->       aive.db → opportunities WHERE critic_verdict='pending'
  --writes-->      aive.db → opportunities (critic_verdict, critic_notes)
  --writes-->      aive.db → rejected_ideas table
  --writes-->      data/exports/critic_results.json
  --uses_model-->  OLLAMA_MODEL_REASONER with fallback to extractor
  --called_by-->   run_batch.py
  QUESTIONS: already_exists, too_crowded, too_early, no_customer,
             technically_hard, distribution_problem
  HARD_RULES:
    - already_exists AND too_crowded → reject
    - no_customer → reject
    - technically_hard AND too_early → reject
    - generic "AI in education" → reject
  TARGET_KILL_RATE: 70%+
```

**Edit critic.py when:** Adding new rejection criteria, adjusting kill rate target, modifying critic questions.

---

## Cluster 7: Output & Scoring

```
[report_writer.py]
  --imports-->     init_db.py (DB_PATH)
  --reads-->       aive.db → opportunities WHERE critic_verdict='survived'
  --reads-->       aive.db → opportunities WHERE critic_verdict='rejected' (count only)
  --writes-->      reports/opportunity_report_001.md
  OUTPUT_FORMAT: Markdown cards per opportunity

[ontology_scorer.py]
  --imports-->     init_db.py (DB_PATH)
  --reads-->       aive.db → opportunities
  --reads-->       aive.db → nodes (for dimension checking)
  --reads-->       aive.db → edges (for purchased_by, requires_resource)
  DIMENSIONS (10): Problem, Technology, Workflow, User, Buyer,
                   Constraint, Regulation, Competitor, EconomicSignal, Resource
  PASS_THRESHOLD: ≥6/10 AND buyer_present
  VERDICT: viable | no_buyer | insufficient_coverage
```

---

## Cluster 8: Database Layer

```
[init_db.py]
  --reads-->       schema.sql
  --creates-->     aive.db (if not exists)
  --exports-->     DB_PATH (used by all agents)
  --called_by-->   fetch_papers.py (init_db())
  DB_PATH_DEFAULT: ./data/aive.db

[schema.sql]
  --defines-->     items table (17 columns)
  --defines-->     nodes table (4 columns)
  --defines-->     edges table (6 columns)
  --defines-->     opportunities table (21 columns)
  --defines-->     opportunity_feedback table (9 columns)
  --defines-->     rejected_ideas table (4 columns)

[migrate.py]
  --reads-->       aive.db
  --modifies-->    Schema via ALTER TABLE statements
  PURPOSE: Adds columns to existing databases without data loss
```

**Edit schema.sql when:** Adding new columns. ALSO run migrate.py to apply to existing DB.
**Edit init_db.py when:** DB_PATH changes, new initialization logic.

---

## Cluster 9: Validation Suite

```
[models.py]
  --defines-->     TestResult dataclass
  --defines-->     SuiteReport dataclass
  --defines-->     ExtractionGroundTruth dataclass
  --defines-->     ExtractionScore dataclass
  --defines-->     NoveltyResult dataclass
  --defines-->     FounderResponse dataclass
  --defines-->     InvestorResponse dataclass
  --defines-->     EdgeAuditResult dataclass
  --defines-->     GraphAuditReport dataclass
  --used_by-->     All validation tests and evaluators

[base_test.py]
  --imports-->     models.py
  --imports-->     score_recorder.py
  --defines-->     BaseTest (abstract class all tests inherit)
  --used_by-->     t1_extraction.py, t2_cross_doc.py, etc.

[score_recorder.py]
  --reads-->       data/validation.db
  --writes-->      data/validation.db (test history)
  --called_by-->   All validation tests

[t1_extraction.py]
  --imports-->     base_test.py
  --imports-->     extraction_eval.py
  --reads-->       validation/fixtures/ (ground truth fixtures)
  --reads-->       aive.db → items (extracted data)
  --uses-->        LLM-as-judge scoring
  CHECKS: problem_accuracy ≥8/10, technology_accuracy ≥8/10, hallucination_count=0

[t7_graph_quality.py]
  --imports-->     base_test.py
  --imports-->     graph_auditor.py
  --reads-->       aive.db → edges (random 50 sample)
  --uses-->        LLM to judge semantic validity
  CHECKS: edge precision ≥90%

[graph_auditor.py]
  --imports-->     base.py (call_llm)
  --imports-->     models.py (EdgeAuditResult, GraphAuditReport)
  --reads-->       aive.db (READ ONLY)
  --exports-->     GraphAuditor class
  METHODS: sample_edges(n), audit_edge(edge), batch_audit(edges)

[extraction_eval.py]
  --imports-->     base.py (call_llm)
  --imports-->     models.py
  --exports-->     ExtractionEvaluator class
  PURPOSE: LLM-as-judge for T1 extraction accuracy

[novelty_search.py]
  --imports-->     base.py (call_llm)
  --imports-->     models.py (NoveltyResult)
  --reads-->       external sources (web search for existing products)
  PURPOSE: T4 — checks if opportunity already exists as a product

[persona_simulator.py]
  --imports-->     base.py (call_llm)
  --imports-->     models.py (FounderResponse, InvestorResponse)
  PURPOSE: T5/T6 — simulates founder and investor panel reactions
```

---

## Cluster 10: Pipeline Runners

```
[run_batch.py]
  --imports-->     opportunity_finder.py (generate)
  --imports-->     critic.py (criticize)
  --reads-->       aive.db → opportunities (for ranking)
  --writes-->      data/exports/batch_report_{timestamp}.json
  STEPS: 1-Generate → 2-Critic → 3-Rank → 4-Save Report → 5-Print Top 5
  ARGS: --count (default 100), --skip-generate, --skip-critic

[rebuild_graph.py]
  --imports-->     knowledge_graph.py (build_graph)
  --deletes-->     aive.db → nodes
  --deletes-->     aive.db → edges
  --calls-->       concept_extractor.py (via build_graph)
  SIDE_EFFECT: Preserves concept_cache.json for speed

[reextract_and_rebuild.py]
  --resets-->      aive.db → items (extraction_status = 'pending')
  --calls-->       research_analyst.py (all papers)
  --calls-->       knowledge_graph.py (build_graph, clear=True)
  PURPOSE: Full pipeline reset and rebuild

[run_aues.py]
  --imports-->     All validation test modules
  --writes-->      data/validation.db (via score_recorder)
  --prints-->      Aggregate test report
  PURPOSE: AIVE User Evaluation Suite runner

[generate_dossier.py]
  --reads-->       aive.db → specific opportunity
  --reads-->       aive.db → connected nodes and evidence items
  --writes-->      reports/dossier_{opp_id}.md
  PURPOSE: Deep-dive report for one specific opportunity
```

---

## Cluster 11: Configuration & Environment

```
[.env]
  --used_by-->     base.py (LLM config)
  --used_by-->     init_db.py (AIVE_DB_PATH)
  KEYS:
    LLM_PROVIDER=ollama|openai
    OLLAMA_HOST=http://localhost:11434
    OLLAMA_MODEL_EXTRACTOR=qwen3:8b
    OLLAMA_MODEL_REASONER=deepseek-r1:8b
    OPENAI_API_KEY=sk-...
    OPENAI_MODEL=gpt-4o-mini
    AIVE_DB_PATH=./data/aive.db
    AIVE_DOMAIN=edtech
    AIVE_DISABLE_AGENT=  (empty = all enabled)

[requirements.txt]
  DEPS: openai, requests, python-dotenv
  BUILT_IN: sqlite3, json, re, uuid, datetime, pathlib, urllib
```

---

## Data Flow Diagram (Full Pipeline)

```
arXiv API
    │
    ▼
fetch_papers.py ──────────────────────┐
fetch_economic_signals.py ────────────┤
import_patents.py ────────────────────┤──► items table (aive.db)
import_startups.py ───────────────────┘    [status: pending]
                                                │
                              research_analyst.py ◄──────┐
                              patent_analyst.py           │
                              startup_analyst.py          │  base.py
                              enrich_beneficiaries.py ◄──┘  (Ollama/OpenAI)
                                                │
                                          items table
                                         [status: done]
                                                │
                              concept_extractor.py ◄── base.py
                                                │
                              concept_cache.json (cached)
                                                │
                              knowledge_graph.py
                                    │           │
                               nodes table   edges table
                               (aive.db)     (aive.db)
                                    │           │
                              opportunity_finder.py ◄── base.py
                                                │
                              opportunities table
                               [verdict: pending]
                                                │
                                        critic.py ◄── base.py
                                                │
                                 ┌──────────────┴──────────────┐
                                 ▼                             ▼
                        survived opportunities          rejected_ideas
                                 │                             │
                        report_writer.py             (learning log)
                                 │
                  reports/opportunity_report_001.md

VALIDATION (parallel, non-destructive):
  run_aues.py → [t1, t2, t3, t7, t9] → graph_auditor, extraction_eval → validation.db
```

---

## Dependency Map (what imports what)

```
init_db.py          ← fetch_papers.py, all agents, all tests
base.py             ← all agents, graph_auditor, extraction_eval, novelty_search, persona_simulator
concept_extractor.py ← knowledge_graph.py
knowledge_graph.py  ← rebuild_graph.py, reextract_and_rebuild.py
opportunity_finder.py ← run_batch.py
critic.py           ← run_batch.py
models.py           ← base_test.py, all validation tests, all evaluators
base_test.py        ← t1, t2, t3, t7, t9 (validation tests)
score_recorder.py   ← base_test.py
graph_auditor.py    ← t7_graph_quality.py
extraction_eval.py  ← t1_extraction.py
novelty_search.py   ← (used by novelty tests)
persona_simulator.py ← (used by persona tests)
```

---

## Common Edits → Files to Touch

| Change Needed | Files to Edit | Files to Verify |
|---|---|---|
| Add new LLM model | `.env` | `base.py` (AGENT_MODELS) |
| Switch to OpenAI | `.env` (LLM_PROVIDER=openai) | none |
| New item type (e.g., 'report') | `schema.sql`, `migrate.py`, new ingest file | `concept_extractor.py` (item_type handling) |
| New node type | `concept_extractor.py` (NODE_TYPES), `knowledge_graph.py` (VALID_NODE_TYPES) | Delete concept_cache.json, rebuild graph |
| New relationship type | `concept_extractor.py` (RELATION_TYPES), `knowledge_graph.py` (VALID_RELATIONS) | Delete concept_cache.json, rebuild graph |
| Fix concept merging (duplicate nodes) | `knowledge_graph.py` (MERGE_MAP) | Rebuild graph, check inspect_graph.py |
| Improve extraction quality | `research_analyst.py` / `patent_analyst.py` / `startup_analyst.py` (prompts) | Run extraction, check DOMAIN_MAP |
| Change opportunity scoring | `opportunity_finder.py` (scoring formula in find_cross_graph_combinations) | Re-run opportunity_finder.py |
| Change critic rules | `critic.py` (CRITIC_PROMPT and/or hard rules) | Re-run critic.py |
| Add new validation test | New file in `validation/tests/`, inherit BaseTest | Add to run_aues.py |
| Add report field | `report_writer.py` (write_report function) | none |
| Add new DB column | `schema.sql` AND `migrate.py` | All agents reading/writing that table |
| Change arXiv query | `fetch_papers.py` (QUERY constant) | none |
| Add economic signal data | `fetch_economic_signals.py` (ECONOMIC_SIGNALS list) | Re-run fetch, rebuild graph |

---

## Critical Data Paths (Never Break These)

1. **items.extraction_status** → gates all downstream processing
   - `'pending'` = not processed
   - `'done'` = ready for graph
   - `'failed'` = skip, don't retry automatically
   - **Used by:** research_analyst.py, concept_extractor.py

2. **opportunities.critic_verdict** → gates report generation
   - `'pending'` = not reviewed by critic
   - `'survived'` = include in report
   - `'rejected'` = log to rejected_ideas
   - **Used by:** critic.py, report_writer.py, run_batch.py

3. **data/concept_cache.json** → gates graph rebuild speed
   - Presence = skip LLM calls for cached items
   - Absence = full re-extraction (slow)
   - **Delete when:** Changing NODE_TYPES, RELATION_TYPES, or MERGE_MAP

4. **DB_PATH** in init_db.py → single source of truth for database location
   - Imported by every agent
   - Override via AIVE_DB_PATH in .env

---

> **Update this file when:** Adding files, changing imports, adding DB columns, adding node/relation types, or changing data flow.
> Run: `python inspect_graph.py` to verify graph stats after changes.
> Run: `python run_aues.py` to verify pipeline health after major changes.
