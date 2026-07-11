# Implementation Plan: AIVE Cognitive Discovery OS

## Overview

Ten implementation tasks, each independently deployable. Tasks 1–3 form the foundation and must be completed first. Tasks 4–7 build the new intelligence layer. Tasks 8–10 surface the capabilities in the frontend. Every task is additive — nothing is removed or rewritten.

## Tasks

- [ ] 1. Run database migration to add new tables and columns across all databases
  - Create `db/migrate_v2.py` that adds: `discoveries` table, `contradictions` table, `evidence_classification` column on items, `doc_type` column on items, `domain` column on items, `reasoning_chain` column on opportunities
  - Migration must use ALTER TABLE with existence check pattern (safe for existing DBs with data)
  - Migration must run against `data/aive.db` and all `data/aive_ws_*.db` workspace files found in `data/`
  - Update `db/schema.sql` to include new tables and columns for fresh database creation
  - Update `db/init_db.py` to call the new table creation statements when initializing fresh databases
  - Verify: all existing items, nodes, edges, opportunities, and rejected_ideas rows are intact after migration

- [ ] 2. Create Universal Analyst agent for domain-agnostic document understanding
  - Create `agents/universal_analyst.py` with `UniversalAnalyst` class
  - Implement `classify(raw_text, metadata)` that detects doc_type and domain from content with no preconfigured domain assumption
  - Implement `extract(item)` that delegates to existing specialist prompts for paper/patent/startup types and uses a universal prompt for all other types
  - Universal extraction prompt must instruct LLM to identify domain, problem, solution, technology, market, and evidence classification per field (fact/inference/hypothesis/unknown)
  - Implement `run(item_id, db_path)` that loads item, classifies, extracts, saves doc_type, domain, and evidence_classification back to DB, and returns result
  - Add `POST /api/understand` route to `app/main.py` that accepts JSON with `text`, optional `url`, optional `type_hint` — saves item, runs UniversalAnalyst, returns item_id, title, doc_type, domain
  - Leave `research_analyst.py`, `patent_analyst.py`, `startup_analyst.py` completely unchanged

- [ ] 3. Create LabelNormalizer for domain-agnostic graph deduplication
  - Create `graph/label_normalizer.py` with `LabelNormalizer` class
  - Implement `token_similarity(a, b)` returning Jaccard similarity on word token sets
  - Implement `is_mergeable(new_label, existing_label)` returning True when: one label is a substring of the other, or token Jaccard > 0.7
  - Implement `normalize(label, existing_labels)` that checks MERGE_MAP first, then checks all existing_labels for mergeable candidates, returns canonical form
  - Log all runtime-discovered merges (where similarity match was used) to `data/merge_log.json`
  - Integrate into `graph/knowledge_graph.py` `upsert_node()`: after the MERGE_MAP lookup, before creating a new node, call `normalizer.normalize(label, existing_labels)` where existing_labels comes from a graph-wide label cache built at the start of `build_graph()`
  - Verify: existing EdTech graph build produces same or fewer unique nodes than before (never more)

- [ ] 4. Create Discovery Classifier to detect research gaps and contradictions
  - Create `agents/discovery_classifier.py` with three detection functions
  - Implement `find_research_gaps(db_path)`: query Problem nodes, check for Technology connections via `solves` edges, return problems with zero such connections; query Technology nodes, check for Buyer connections via `purchased_by` edges, return technologies with zero buyer connections
  - Implement `find_contradictions(db_path, sample_size=50)`: sample item pairs sharing at least one graph node, use LLM-as-judge to detect conflicting claims about the shared concept, return confirmed contradictions
  - Implement `find_method_transfers(db_path)`: identify Technology nodes with connections in one domain cluster but absent in another domain cluster that has analogous Problem nodes
  - Implement `run(db_path)`: run all three detectors, save results to `discoveries` and `contradictions` tables, return counts
  - Add `GET /api/discoveries` route to `app/main.py` with optional `?type=` query parameter
  - Add `GET /api/contradictions` route to `app/main.py`
  - Add `GET /api/research-gaps` route to `app/main.py`
  - Integrate as optional stage in `scripts/run_orchestrator.py` after graph build, controlled by an `AIVE_SKIP_DISCOVERY_CLASSIFY` env flag so it can be bypassed for speed

- [ ] 5. Create research-grade Report Builder
  - Create `agents/report_builder.py` with `ReportBuilder` class
  - Implement deterministic section generators (no LLM): Evidence list from items table with source URLs, Knowledge Graph Summary with node/edge counts and type distribution table, References section with all source URLs
  - Implement LLM section generators for: Executive Summary (top 5 opportunities + graph stats as context), Key Findings (all survived opportunities with scores), Cross-Document Insights (concept nodes with 3+ source items), Contradictions (each contradiction record), Research Gaps (each gap record), Risk Analysis (each opportunity + critic notes), Validation Strategy (opportunity title + market + technology)
  - Every LLM prompt must end with anti-hallucination instruction: "Base every claim strictly on the provided data. Do not introduce information not present in the data."
  - Every LLM-generated sentence must have inline evidence citations in format `[item_id]`
  - Implement `build(db_path, output_path, scope, sections)` assembling all sections into valid Markdown
  - Add `POST /api/reports/generate-deep` route to `app/main.py` accepting JSON with `scope` (all/survived) and optional `sections` list
  - Leave `agents/report_writer.py` and `POST /api/reports/generate` unchanged

- [ ] 6. Enhance Copilot with grounded QA engine
  - Create `engines/qa_engine.py` with `QAEngine` class inheriting from `BaseEngine`
  - Implement `classify_question(question)` returning one of: factual, graph, comparative, discovery, gap
  - Implement `answer_factual(question, db_path)`: full-text search across items summary/problem/technology fields, LLM synthesis grounded in matching items, return reply + evidence_refs (item IDs)
  - Implement `answer_graph(question, db_path)`: parse concept keywords from question, call existing `query_technologies_for_problem()` or `commercialization_profile()`, format results as natural language
  - Implement `answer_discovery(question, db_path)`: query opportunities and discoveries tables ranked by confidence, return top 3 relevant results
  - Implement `answer_gap(question, db_path)`: query contradictions and research_gaps from discoveries table
  - Implement `answer(question, db_path)` that classifies then routes, always returning `{reply, evidence_refs, confidence, reasoning_path}`
  - Integrate into existing `/api/copilot` route in `app/main.py`: instantiate QAEngine, call answer(), merge result into existing response dict — preserve all existing copilot behavior for opportunity proposal detection path
  - When evidence is insufficient, reply must contain explicit statement: "The current knowledge base does not contain sufficient information to answer this confidently."

- [ ] 7. Add visualization data API endpoints
  - Add `GET /api/visualizations/funnel` to `app/main.py`: query DB for ingested count (all items), extracted count (extraction_status=done), graph_nodes count, candidates count (all opportunities), survived count, rejected count — return as JSON object
  - Add `GET /api/visualizations/scores` to `app/main.py`: query all survived opportunities, return array of objects with id, title, novelty_score, timing_score, market_score, feasibility, confidence_score
  - Add `GET /api/visualizations/timeline` to `app/main.py`: query items grouped by extracted_at date (date portion only), return array of {date, papers, patents, startups, other} per day
  - Add `GET /api/visualizations/distribution` to `app/main.py`: query node type counts from nodes table, return as {node_type: count} object
  - All four endpoints must follow existing Flask pattern: try/except, jsonify, conn.close() in finally
  - Verify all four endpoints return HTTP 200 with valid JSON against the existing aive.db

- [ ] 8. Add Insights tab to Inspector panel in frontend
  - Add "Insights" as fourth tab to the inspector-tabs div in `app/templates/index.html`
  - Add `id="inspector-insights"` panel div with `display:none` initial state, following existing inspector-body pattern
  - Extend `setInspectorTab()` function to handle 'insights' case, hide other panels, show inspector-insights
  - Add canvas element for funnel chart and canvas element for distribution chart inside inspector-insights
  - Implement `loadInsightsCharts()` function that: fetches `/api/visualizations/funnel`, creates a horizontal bar Chart.js chart; fetches `/api/visualizations/distribution`, creates a doughnut Chart.js chart
  - Call `loadInsightsCharts()` when Insights tab is activated (inside setInspectorTab switch)
  - Destroy and recreate chart instances on re-activation using Chart.js `.destroy()` method
  - Use amber token `#d6a34f` as primary chart color; use existing semantic colors for secondary series
  - All three existing inspector tabs (Copilot, Graph, Status) must continue to function without any changes

- [ ] 9. Add Discovery navigation to sidebar and canvas node types for new discovery types
  - Add "Discoveries" nav item to the sidebar-discovery Views section in `app/templates/index.html`, below the Library item
  - Style nav dot with color `var(--clr-warn)` (orange) for discoveries
  - Add `id="count-disc"` span for discovery count
  - Extend `switchNav()` to handle 'discoveries': fetch `/api/discoveries`, call `renderCanvas()` with results
  - Add CSS classes `.k-node-contradiction`, `.k-node-gap`, `.k-node-transfer` following the existing `.k-node-opp` pattern
  - Contradiction node: `.k-node-type` color `var(--clr-error)` (red)
  - Research gap node: `.k-node-type` color `var(--clr-warn)` (orange)
  - Method transfer node: `.k-node-type` color `var(--clr-startup)` (teal)
  - Extend `buildNode()` to handle discovery item structure: detect `item.type` values of `contradiction`, `research_gap`, `method_transfer` and apply correct CSS class
  - Extend `renderDetailPane()` summary tab to display discovery-specific fields: for contradiction show concept + claim_a + claim_b + sources; for research_gap show description + missing_dimension; for method_transfer show source domain + target domain
  - Update `loadStats()` to fetch discovery count and set `count-disc` element
  - All existing nav items (Opportunities, Rejected, Library) and canvas rendering must remain unchanged

- [ ] 10. Enhance Copilot message rendering with evidence references and confidence badges
  - In `sendCopilotMessage()` in `app/templates/index.html`, after receiving API response, check for `res.evidence_refs` and `res.confidence`
  - If `evidence_refs` array is non-empty, append a row of small inline badges below the bot message text: `<span class="tag tag-paper">ref</span>` per item ID (truncated to 8 chars for display, full ID in title attribute)
  - If `confidence` is present, append a confidence line below the message: `◎ High` in `var(--clr-success)` green, `◎ Medium` in `var(--amber)`, `◎ Low` in `var(--clr-error)` red, `◎ Unknown` in `var(--tx-2)` muted
  - Badges and confidence indicator must be appended as child elements to the existing `replyEl` div, never replacing the existing reply text
  - When `evidence_refs` and `confidence` are absent from the response, the message renders exactly as before — no change in appearance for old-format responses
  - Existing user message rendering, loading indicator, and error message rendering must remain unchanged

## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": 1,
      "tasks": [1]
    },
    {
      "wave": 2,
      "tasks": [2, 3, 7]
    },
    {
      "wave": 3,
      "tasks": [4, 5, 6]
    },
    {
      "wave": 4,
      "tasks": [8, 9, 10]
    }
  ]
}
```

Wave 1: Database migration must complete first — all other tasks depend on the new schema.
Wave 2: Universal Analyst, Label Normalizer, and Visualization API are independent and can be built in parallel.
Wave 3: Discovery Classifier, Report Builder, and QA Engine all depend on the new DB tables from Wave 1. Discovery Classifier results are used by Report Builder sections.
Wave 4: All frontend tasks. Insights tab depends on Visualization API (Wave 2). Discovery nav depends on Discovery Classifier endpoints (Wave 3). Copilot enhancement depends on QA Engine (Wave 3).

## Notes

All tasks must be verified against the existing `data/aive.db` database before being marked complete. The existing pipeline (ingest → extract → graph → opportunities → critic → report) must continue to produce identical results after all tasks are complete. Run `python agents/graph_builder.py` and `python scripts/run_orchestrator.py 5` as a smoke test after each task.
