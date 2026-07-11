# AIVE — Full Project Understanding Guide

> **Reference this file first before scanning the codebase.**
> **Cross-reference with `KNOWLEDGE_GRAPH.md` for file-to-component relationships.**

**Project:** AIVE V0 — AI-Powered Knowledge Discovery System  
**Domain:** EdTech (AI + Education)  
**Tech Stack:** Python 3.11+, SQLite, Ollama (local LLMs), OpenAI fallback  
**Last Indexed:** 2026-07-10

---

## 1. Mission & Core Concept

AIVE is a **Knowledge Discovery System** — not a startup generator. Its singular goal:

> Find non-obvious connections between Technologies, Problems, and Markets that humans would likely miss.

The formula: `Technology + Problem + Market = Opportunity`

**Success metric:** The system produces one opportunity that makes a smart human say "I didn't think of that."

---

## 2. System Architecture — 5 Layers

```
Layer 5 — Critic Engine          agents/critic.py
           ↑
Layer 4 — Opportunity Engine     agents/opportunity_finder.py
           ↑
Layer 3 — Knowledge Graph        graph/knowledge_graph.py + agents/concept_extractor.py
           ↑
Layer 2 — Knowledge Extraction   agents/research_analyst.py + patent_analyst.py + startup_analyst.py
           ↑
Layer 1 — Data Layer             data/aive.db (SQLite) + ingest/
```

Data flows **bottom up**: raw papers → extracted knowledge → graph nodes → opportunity candidates → critic filter → final report.

---

## 3. Data Pipeline — End to End

### Step 1: Data Ingestion (ingest/)

| File | Source | Output |
|---|---|---|
| `fetch_papers.py` | arXiv API (XML) | `items` table rows, type=`paper` |
| `import_patents.py` | Manual patent text files | `items` table rows, type=`patent` |
| `import_startups.py` | CSV/manual startup data | `items` table rows, type=`startup` |
| `fetch_economic_signals.py` | Hardcoded market intelligence | `items` table rows, type=`economic_signal` |
| `fetch_new_domains.py` | Additional arXiv queries | Extends papers collection |

All ingested items go to `data/aive.db` → `items` table with `extraction_status='pending'`.
Raw JSON cache files saved to `data/raw/papers/` for audit purposes.

---

### Step 2: Knowledge Extraction (agents/)

Each **Analyst Agent** reads one raw item and calls the LLM (via `agents/base.py`) to extract structured JSON.

#### agents/research_analyst.py
- **Input:** arXiv paper abstract (`raw_text` field, truncated to 6000 chars)
- **Prompt:** Extracts `problem`, `solution`, `technology`, `keywords`, `industry`, `impact`, `beneficiaries`, `summary`
- **Quality rules:** Rejects generic output like "AI for education" — requires specific noun phrases
- **Output:** Updates `items` row with extracted fields, sets `extraction_status='done'`
- **Error handling:** 3 consecutive LLM failures → stops gracefully (Ollama down detection)

#### agents/patent_analyst.py
- Same structure as research_analyst but prompt tuned for patent language (claims, prior art)
- Handles `type='patent'` items only

#### agents/startup_analyst.py
- Same structure, tuned for startup descriptions (market validation, business model)
- Handles `type='startup'` items only

#### agents/enrich_beneficiaries.py
- **Enrichment patch** — adds `beneficiaries` and improves `impact` fields to already-extracted papers
- Run once after bulk extraction to improve graph quality

---

### Step 3: Concept Extraction (agents/concept_extractor.py)

The most critical pre-graph step. Converts unstructured extraction fields into typed graph concepts.

**Input:** Extracted item fields (problem, technology, solution, keywords, industry, beneficiaries)

**13 Node Types:**

| Type | Example |
|---|---|
| Problem | "Teacher Grading Workload" |
| Technology | "LoRA Fine-Tuning" |
| Capability | "Offline Inference" |
| Workflow | "Essay Grading", "IEP Generation" |
| User | "Students", "Teachers" |
| Buyer | "School District IT Department" |
| Organization | "K-12 School District" |
| Competitor | "Khanmigo", "MagicSchool" |
| Constraint | "Limited Internet Access" |
| Regulation | "FERPA", "COPPA", "EU AI Act" |
| EconomicSignal | "Teacher Shortage", "LLM Cost Drop" |
| Outcome | "50% Grading Time Saved" |
| Resource | "GPU Compute", "Training Data" |

**13 Relationship Types:**
solves, improves, benefits, purchased_by, used_by, deployed_in, constrained_by, enabled_by, competes_with, produces, signals, regulated_by, requires_resource

**Anti-hallucination guard:** Every concept requires an `evidence` phrase from the actual source. Edge semantic coherence check: tokens from both concept labels must appear in the evidence phrase.

**Caching:** Results cached to `data/concept_cache.json`. Delete to force re-extraction.

---

### Step 4: Graph Building (graph/knowledge_graph.py)

Converts concept extraction results into the SQLite graph (nodes + edges tables).

#### Node Upsert Logic
- Normalizes labels using MERGE_MAP (e.g., "offline inference" → "On-Device LLM Inference")
- Node ID format: `node_{type_lower}_{slugified_label}`
- Merges duplicate nodes by canonical label — accumulates `source_items` array
- Confidence scales with source count: 1 source=0.5, 2=0.65, 3=0.75, 4+=0.85

#### Edge Upsert Logic
- Edge ID: `edge_{from_id}_{relationship}_{to_id}`
- **Quality gates (hard filters):**
  - Skips self-referential edges
  - Rejects edges with weight < 0.6
  - Rejects edges where either endpoint is a single generic word ("education", "ai", "learning")
- **Weight by source type:** paper=0.75, patent=0.80 (signals commercial intent), startup=0.85 (market validation)
- Accumulates evidence item IDs per edge; weight increases with each new source

#### Query Functions
- `query_technologies_for_problem(keyword)` — finds what technologies `solves` a problem
- `commercialization_profile(technology)` — full 6-question commercialization analysis using graph traversal

---

### Step 5: Opportunity Discovery (agents/opportunity_finder.py)

The intelligence core. Finds `Problem × Technology × CommercialAnchor` triples in the graph.

#### Candidate Discovery Algorithm
1. Collect top 25 `Problem` nodes (ranked by source count)
2. Collect top 25 `Technology`/`Capability` nodes
3. For each `Problem × Technology` pair:
   - Check if directly connected OR share source items (implicit connection)
   - Find best commercial anchor (Buyer > EconomicSignal > Regulation)
   - **Score the triple:**
     - Base: 0.5
     - +0.2 per evidence type (paper/patent/startup)
     - +0.4 if commercially anchored
     - +0.2 if anchor is Buyer (highest commercial signal)
     - +0.3 if has economic signal + research paper (cross-domain bonus)
     - Penalty: over-represented nodes (too obvious)
     - Penalty: 4+ competitor startups (market saturated)

#### LLM Enrichment
Each candidate is enriched by the `reasoner` LLM model with:
- title, problem, technology, market, timing_signal, reasoning
- existing_competitors, evidence_summary, buyer, regulation, economic_signal
- Scores: novelty_score, timing_score, market_score, feasibility, confidence_score (0-10 each)

**Reject conditions in prompt:** no buyer, vague timing signal, score >7 only if cross-layer evidence.

Output saved to `data/exports/opportunities_batch1.json` and `opportunities` table.

---

### Step 6: Critic Engine (agents/critic.py)

**Philosophy:** Most ideas should die. Target: kill 70%+ of opportunities.

**6 Critic Questions evaluated by LLM:**
1. `already_exists` — is there an exact product doing this?
2. `too_crowded` — too many competitors?
3. `too_early` — technology not ready?
4. `no_customer` — no identifiable buyer?
5. `technically_hard` — infeasible in 12 months?
6. `distribution_problem` — no path to customers?

**Hard rejection rules:**
- `already_exists AND too_crowded` → reject
- `no_customer` → reject
- `technically_hard AND too_early` → reject
- Generic "AI in education" with no specific intersection → reject

**Survived** opportunities stay in `opportunities` table with `critic_verdict='survived'`.
**Rejected** ideas logged to `rejected_ideas` table with reason.

Output saved to `data/exports/critic_results.json`.

---

### Step 7: Report Writing (agents/report_writer.py)

Generates `reports/opportunity_report_001.md` — a Markdown report of critic survivors.

Each opportunity card includes: Problem, Technology, Market, Timing, Reasoning, Scores (Novelty/Timing/Market/Feasibility/Confidence), Evidence (papers/patents/startups), Competitors.

---

## 4. Validation Suite (validation/)

An independent quality testing framework that measures pipeline health without running the full pipeline.

### Test Files (validation/tests/)

| Test | File | What It Checks |
|---|---|---|
| T1 | `t1_extraction.py` | Extraction accuracy — LLM-as-judge vs ground truth fixtures |
| T2 | `t2_cross_doc.py` | Cross-document pattern detection across paper+patent+startup |
| T3 | `t3_false_opportunity.py` | False opportunity rate — does critic correctly kill bad ideas? |
| T7 | `t7_graph_quality.py` | Graph edge semantic validity (samples 50 random edges, LLM judges) |
| T9 | `t9_commercialization.py` | Commercialization coverage — Buyer/EconomicSignal nodes present? |

### Evaluators (validation/evaluators/)

| File | Role |
|---|---|
| `extraction_eval.py` | LLM-as-judge scorer for T1 |
| `graph_auditor.py` | Samples and audits graph edges for T7 |
| `novelty_search.py` | External search to check if opportunity already exists (T4) |
| `persona_simulator.py` | Simulates founder/investor panels (T5, T6) |

### Validation Data Models (validation/models.py)

All test result dataclasses: TestResult, SuiteReport, ExtractionGroundTruth, ExtractionScore, NoveltyResult, FounderResponse, InvestorResponse, EdgeAuditResult, GraphAuditReport

### Score Recording (validation/score_recorder.py)

Persists test scores to `data/validation.db` for historical tracking.

### Validation DB (data/validation.db)

Separate SQLite DB (not aive.db) — stores validation run history.

---

## 5. LLM Infrastructure (agents/base.py)

Central LLM interface — all agents call through here.

### Models
- **Extractor model:** `qwen3:8b` (default via Ollama) — fast, structured JSON extraction
- **Reasoner model:** `deepseek-r1:8b` (default via Ollama) — deeper reasoning for opportunities/critic

Configured via `.env`:
```
OLLAMA_MODEL_EXTRACTOR=qwen3:8b
OLLAMA_MODEL_REASONER=deepseek-r1:8b
OLLAMA_HOST=http://localhost:11434
LLM_PROVIDER=ollama  # or "openai"
```

### Key Functions
- `call_llm(prompt, system, agent)` — main entry point; routes to ollama or openai
- `call_ollama(...)` — HTTP request to local Ollama /api/chat, appends /no_think to system prompt (disables qwen3 chain-of-thought, cuts response time from ~90s to ~15s)
- `call_openai(...)` — OpenAI API fallback with json_object response format
- `extract_json(text)` — parses JSON from LLM output; regex fallback for partial JSON

**Ablation testing support:** Setting `AIVE_DISABLE_AGENT=<agent_name>` in env causes that agent to return {} immediately (used in T8 Destruction Test).

---

## 6. Database Schema (db/schema.sql)

### Tables

#### items — Raw + Extracted Knowledge
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | e.g. `paper_2606_11744v1` |
| title | TEXT | Document title |
| source | TEXT | arxiv, manual, etc. |
| source_url | TEXT | Original URL |
| type | TEXT | paper, patent, startup, economic_signal |
| raw_text | TEXT | Original abstract/description |
| summary | TEXT | LLM-generated 2-sentence summary |
| problem | TEXT | Extracted problem (noun phrase) |
| solution | TEXT | Extracted solution |
| technology | TEXT | Named technology (noun phrase) |
| keywords | TEXT | JSON array |
| industry | TEXT | JSON array of specific market segments |
| impact | TEXT | Who benefits and how |
| beneficiaries | TEXT | JSON array of specific beneficiary groups |
| year | TEXT | Publication year |
| extracted_at | TEXT | ISO timestamp |
| extraction_status | TEXT | pending, done, failed |

#### nodes — Knowledge Graph Nodes
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | `node_{type}_{slugified_label}` |
| label | TEXT | Canonical concept label |
| node_type | TEXT | One of 13 valid types |
| source_items | TEXT | JSON array of item IDs |

#### edges — Knowledge Graph Edges
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | `edge_{from}_{rel}_{to}` |
| from_node | TEXT FK | Source node ID |
| to_node | TEXT FK | Target node ID |
| relationship | TEXT | One of 13 valid relation types |
| weight | REAL | 0.6–1.0 (higher = stronger evidence) |
| evidence | TEXT | JSON array of item IDs |

#### opportunities — Generated Opportunities
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | `opp_{uuid8}` |
| title | TEXT | 5-8 word opportunity name |
| problem | TEXT | Specific problem |
| technology | TEXT | Specific technology |
| market | TEXT | Market segment / commercial anchor |
| timing_signal | TEXT | Why now? |
| problem_node | TEXT FK | Linked graph node |
| technology_node | TEXT FK | Linked graph node |
| reasoning | TEXT | 2-3 sentence connection logic |
| evidence | TEXT | JSON array of evidence points |
| existing_competitors | TEXT | JSON array |
| novelty_score | INTEGER | 0-10 |
| timing_score | INTEGER | 0-10 |
| market_score | INTEGER | 0-10 |
| feasibility | INTEGER | 0-10 |
| confidence_score | INTEGER | 0-10 |
| edge_confidence | REAL | Graph edge strength |
| critic_verdict | TEXT | pending, survived, rejected |
| critic_notes | TEXT | Full JSON critic output |

#### opportunity_feedback — Human Ratings
Stores human evaluation: human_rating, novel, feasible, valuable, surprising, would_build

#### rejected_ideas — Critic Rejections
Stores rejected opportunity IDs with rejection reason and timestamp.

---

## 7. Scoring Systems

### Opportunity Composite Score
Computed in run_batch.py:
```
composite = novelty_score + timing_score + market_score + feasibility + confidence_score
# Max: 50 points
```

### Ontology Coverage Score (agents/ontology_scorer.py)
Rates each opportunity 0–10 on how many of the 10 commercial reality dimensions are covered in the graph:
Problem, Technology, Workflow, User, Buyer, Constraint, Regulation, Competitor, EconomicSignal, Resource

**Critical rule:** If Buyer is missing → score is automatically non-viable regardless of total.
**Pass threshold:** ≥6/10 AND buyer present.

---

## 8. Utility Scripts (Root Level)

| Script | Purpose |
|---|---|
| `radar.py` | Original arXiv fetcher (terminal only, no DB) |
| `run_batch.py` | Full pipeline: generate → critic → rank → report |
| `run_aues.py` | Runs the AIVE User Evaluation Suite (validation tests) |
| `run_t33_t34.py` | Runs specific validation tests T33/T34 |
| `analyze_batch.py` | Analyzes output of a completed batch run |
| `rebuild_graph.py` | Clears and rebuilds graph from concept cache |
| `reextract_and_rebuild.py` | Clears extractions and rebuilds everything |
| `generate_dossier.py` | Creates detailed dossier for a specific opportunity |
| `inspect_graph.py` | Prints graph stats and sample nodes/edges |
| `inspect_t7.py` | Inspects T7 test results |
| `check_graph_now.py` | Quick graph health check |
| `reset_pending.py` | Resets stuck pending items to allow re-extraction |
| `test_live.py` | Live system integration tests |
| `test_t14.py / t15 / t16` | Specific test runners |

### scripts/ Directory
| Script | Purpose |
|---|---|
| `status.py` | Prints pipeline status (item counts by type/status) |
| `critic_status.py` | Prints critic results summary |
| `domain_map.py` | Generates domain map from extracted data |
| `dump_papers.py` | Exports papers to text for review |

---

## 9. Data Files & Exports

| Path | Contents |
|---|---|
| `data/aive.db` | Main SQLite database (all items, graph, opportunities) |
| `data/validation.db` | Validation test history |
| `data/concept_cache.json` | Cached concept extraction results (avoids LLM re-runs) |
| `data/exports/opportunities_batch1.json` | Latest opportunity generation run |
| `data/exports/critic_results.json` | Latest critic pass results |
| `data/exports/batch_report_{timestamp}.json` | Full batch pipeline results |
| `data/raw/papers/*.json` | Cached arXiv API responses |
| `reports/opportunity_report_001.md` | Latest Markdown opportunity report |

---

## 10. Configuration (.env)

```env
# LLM Provider
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_EXTRACTOR=qwen3:8b
OLLAMA_MODEL_REASONER=deepseek-r1:8b

# OpenAI fallback
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Database
AIVE_DB_PATH=./data/aive.db
AIVE_DOMAIN=edtech

# Ablation testing
AIVE_DISABLE_AGENT=
```

---

## 11. Domain Knowledge (DOMAIN_MAP.md)

Manual analysis of first 20 papers that informed the initial graph design.

**Top 3 Problem Clusters:**
1. **Tutoring & Curriculum** — unstructured chat → needs PKG + Socratic PPO + local LLM → rural schools
2. **Assessment & Tracing** — cold-start + AES + MCQ → student models → formative assessment
3. **Trust & Privacy** — academic integrity + local LLM + schema decoding → special ed + institutions

**Node Merge Rules:**
- "IEP automation", "essay scoring", "formative assessment" → merge to `Educator Administrative Burden`
- "offline inference", "local LLM", "privacy-preserving AI" → merge to `On-Device LLM Inference`
- All knowledge graph variants → unified `Knowledge Graph` node

---

## 12. How to Run the System

### Full Pipeline (one command)
```bash
python run_batch.py --count 30
```

### Step by Step
```bash
# 1. Ingest data
python ingest/fetch_papers.py 20
python ingest/fetch_economic_signals.py

# 2. Extract knowledge
python agents/research_analyst.py 20
python agents/patent_analyst.py 20
python agents/startup_analyst.py 20

# 3. Enrich (optional)
python agents/enrich_beneficiaries.py

# 4. Build graph
python rebuild_graph.py

# 5. Check graph health
python inspect_graph.py
python agents/ontology_scorer.py

# 6. Generate opportunities
python agents/opportunity_finder.py 30

# 7. Run critic
python agents/critic.py

# 8. Write report
python agents/report_writer.py

# 9. Run validation suite
python run_aues.py
```

---

## 13. Key Design Decisions

| Decision | Rationale |
|---|---|
| SQLite only | Zero infra, portable, fully inspectable |
| Local Ollama first | No API costs during development; OpenAI as fallback |
| /no_think system prompt suffix | Disables qwen3 chain-of-thought; cuts response time from ~90s to ~15s |
| Evidence anchoring on every concept | Prevents hallucinated cross-domain edges |
| Weight by source type | Startup evidence > patent > paper (commercial validation hierarchy) |
| MERGE_MAP in graph builder | Deduplicates variant phrasings before they pollute the graph |
| Concept cache JSON | Avoids redundant LLM calls on graph rebuilds |
| Critic kills 70%+ target | Prevents hallucination machine effect |
| Buyer required for viability | No buyer = commercially ungrounded regardless of technical interest |

---

## 14. Current State (Day 29 of 90)

| Component | Status |
|---|---|
| Paper ingestion (arXiv) | DONE |
| Patent ingestion | DONE |
| Startup ingestion | DONE |
| Economic signals ingestion | DONE |
| Research/Patent/Startup extraction | DONE |
| Concept extraction + graph build | DONE |
| Opportunity finder | DONE |
| Critic engine | DONE |
| Report writer | DONE |
| Validation suite (T1-T9) | DONE |
| Ontology scorer | DONE |
| Flask dashboard | PLANNED (Week 8) |

---

## 15. Future (V1+, not building yet)

- Feedback loop: human eval → outcome tracking → learning
- Temporal layer: trend velocity on nodes
- Expanded critic: Technical, Market, Timing, Competition, Distribution critics
- Node hierarchy: Opportunity → Product → Invention → Company
- Human insight layer: founder interviews, user pain points
- Neo4j migration for complex graph queries

---

> **To update this file:** When adding a new agent, table, evaluator, or script — add an entry in the relevant section above AND update KNOWLEDGE_GRAPH.md.
