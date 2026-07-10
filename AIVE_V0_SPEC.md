# AIVE V0 — Vision, Mission & Implementation Plan

**Version:** 0.1  
**Domain focus:** Edtech (AI + Education)  
**Status:** Week 1 — `radar.py` live, first 10 papers fetched from arXiv  
**Last updated:** June 12, 2026

---

## 1. Mission

**Build a machine that finds non-obvious connections between technologies, problems, and markets.**

AIVE V0 is not a startup generator, patent factory, or prediction engine. It is a **Knowledge Discovery System** — Type A, not Type B.

| Type A (V0) | Type B (later) |
|---|---|
| Discovers insights humans missed | Generates inventions |
| Verifiable against real sources | Harder to verify |
| "I didn't think of that" | "Here's a new product" |

**The only question for the next 30 days:**

> Can we make a machine that finds non-obvious connections?

Everything else — funding, patents, investors, venture studios, billion-dollar valuations — is a distraction until this question has an answer.

---

## 2. Vision

Valuable opportunities often exist at the intersection of **disconnected domains**. Humans rarely search across all three dimensions at once:

```
Technology  +  Problem  +  Market  =  Opportunity
```

**Example:**

| Dimension | Source |
|---|---|
| Technology | Small local AI models (paper) |
| Problem | Teacher shortage (research) |
| Market | Rural schools (startup signal) |
| **Connection** | **Offline AI teaching assistant** |

Nobody invented anything new. The value came from **connecting dots** that lived in separate silos.

**What success looks like:**

You read the output and say:

> *"Interesting. I didn't think of that."*

That is enough. Not revenue. Not users. Not valuation.

---

## 3. Core Hypothesis

> Valuable opportunities exist at the intersection of disconnected domains, and a structured knowledge system can surface them faster and more broadly than manual research.

**V0 must prove at least one of:**

| Test | Question |
|---|---|
| **A** | Does AIVE find opportunities you did not think of? |
| **B** | Does AIVE find opportunities faster than manual research? |
| **C** | Does AIVE combine domains humans rarely combine? |

If all three fail after 100 generated opportunities, AIVE fails. If 5–10 make you stop and think, you're onto something.

---

## 4. Inputs

### 4.1 Data Sources

| Source | API / Method | Target | Domains |
|---|---|---|---|
| **Research Papers** | arXiv API (`radar.py`) | 100 | AI, Education, Healthcare |
| **Patents** | Google Patents (manual first, scrape later) | 100 | Same domains |
| **Startups** | Product Hunt, YC, startup directories | 100 | Same domains |

**Week 1 collection pace:** 20 papers + 20 patents + 20 startups (60 total).  
**Week 1 end state:** 100 + 100 + 100 (300 total).

### 4.2 arXiv Queries (Edtech focus)

```
Primary:   all:education AND (all:AI OR all:machine learning)
Secondary: all:healthcare AND (all:AI OR all:machine learning)
Tertiary:  all:tutoring OR all:"knowledge tracing" OR all:"automated essay"
```

### 4.3 Patent Search Terms (manual)

```
"adaptive learning" AI
"automated essay scoring"
"offline inference" education
"knowledge tracing" neural
"virtual tutor" machine learning
```

### 4.4 Startup Sources

- [Y Combinator companies](https://www.ycombinator.com/companies) — filter Edtech, Health
- [Product Hunt](https://www.producthunt.com) — search "education AI", "healthtech AI"
- [Crunchbase](https://www.crunchbase.com) — free tier for descriptions

---

## 5. Outputs

### 5.1 Primary Deliverable (Week 1 end)

**10 Generated Opportunities**, each containing:

```json
{
  "id": "opp_001",
  "title": "Offline AI Teaching Assistant for Rural Schools",
  "problem": "Teacher shortage in underserved regions",
  "technology": "On-device small language models",
  "market": "Rural K-12 education",
  "reasoning": "Paper X shows offline LLM viability. Patent Y covers low-power edge chips. Startup Z validates rural edtech demand. No existing product combines all three.",
  "confidence": "medium",
  "sources": {
    "papers": ["paper_003", "paper_010"],
    "patents": ["patent_014"],
    "startups": ["startup_007", "startup_022"]
  },
  "critic_verdict": "survived",
  "critic_notes": "Competitor X exists but targets urban markets only."
}
```

### 5.2 Daily Output (Week 2+)

Every morning, AIVE produces:

| Field | Example |
|---|---|
| **Emerging Technology** | Local LLMs |
| **Emerging Problem** | Teacher shortages |
| **Potential Opportunity** | Offline AI tutoring |
| **Why It Exists** | 3 papers, 2 patents, 1 market signal |
| **Confidence** | Low / Medium / High |

### 5.3 Rejected Ideas Log

Ideas killed by the Critic agent — equally important. You learn from failures.

---

## 6. Data Schema

### 6.1 Knowledge Item (universal record)

Every paper, patent, and startup becomes one row:

```json
{
  "id": "paper_001",
  "title": "Hey Chat, Can You Teach Me?",
  "source": "arxiv",
  "source_url": "https://arxiv.org/abs/2606.11744v1",
  "type": "paper",
  "raw_text": "...",
  "summary": "LLMs used for learning lack structured Socratic dialogue...",
  "problem": "Unstructured chat-based learning fails to follow curriculum",
  "solution": "Structured Socratic dialogue policy for LLM tutoring",
  "technology": "Dialogue policy optimization, LLM tutoring",
  "keywords": ["Socratic dialogue", "LLM", "education", "tutoring"],
  "industry": ["education", "AI"],
  "year": "2026",
  "extracted_at": "2026-06-12T10:00:00Z",
  "extraction_status": "done"
}
```

### 6.2 Graph Node

```json
{
  "id": "node_042",
  "label": "Teacher Shortage",
  "node_type": "problem",
  "source_items": ["paper_006", "startup_015"]
}
```

### 6.3 Graph Edge

```json
{
  "id": "edge_108",
  "from_node": "node_042",
  "to_node": "node_017",
  "relationship": "solved_by",
  "weight": 0.7,
  "evidence": ["paper_003", "patent_008"]
}
```

### 6.4 Opportunity

```json
{
  "id": "opp_001",
  "title": "",
  "problem_node": "node_042",
  "technology_node": "node_017",
  "market_node": "node_089",
  "reasoning": "",
  "confidence": "low|medium|high",
  "source_papers": [],
  "source_patents": [],
  "source_startups": [],
  "critic_verdict": "survived|rejected",
  "critic_notes": "",
  "created_at": ""
}
```

---

## 7. System Architecture

Think of AIVE as a city with five layers.

```
┌─────────────────────────────────────────────────────┐
│  Layer 5 — Critic                                   │
│  Kills bad ideas before they waste your attention   │
├─────────────────────────────────────────────────────┤
│  Layer 4 — Opportunity Engine                       │
│  Problem + Technology + Market → Opportunity        │
├─────────────────────────────────────────────────────┤
│  Layer 3 — Knowledge Graph                          │
│  Technologies ↔ Problems ↔ Industries ↔ Benefits  │
├─────────────────────────────────────────────────────┤
│  Layer 2 — Knowledge Extraction                     │
│  Raw docs → structured problem/solution/keywords    │
├─────────────────────────────────────────────────────┤
│  Layer 1 — Data Layer                               │
│  300 items: papers + patents + startups (SQLite)    │
└─────────────────────────────────────────────────────┘
```

### Layer 1 — Data Layer

Stores raw knowledge. SQLite database. No complex infra.

### Layer 2 — Knowledge Extraction

Raw papers are useless. Agents extract:

- Problem
- Solution / Technology
- Keywords
- Industry

Now each document is machine-readable.

### Layer 3 — Knowledge Graph

Instead of storing documents, store **relationships**:

```
Teacher Shortage
      │
      ▼
  Education
      │
      ▼
Offline AI Models
      │
      ▼
Low Power Chips
```

Node types: `technology`, `problem`, `industry`, `benefit`, `market`

### Layer 4 — Opportunity Engine

Four questions per candidate:

1. What problem appears frequently?
2. What new technology can solve it?
3. Has anyone commercialized it?
4. How difficult is it?

### Layer 5 — Critic

Most ideas should die. Questions:

- Already exists?
- Market too small?
- Technically impossible?
- Bad timing?

Without Critic: AIVE becomes a hallucination machine.

---

## 8. Agent Team

Seven agents total. Build in order — not all at once.

| Agent | Role | Week | Input | Output |
|---|---|---|---|---|
| **1. Research Analyst** | Reads papers | 1 | arXiv paper | problem, solution, keywords |
| **2. Patent Analyst** | Reads patents | 1 | Patent text | claims, technology map |
| **3. Startup Analyst** | Reads startup descriptions | 1 | Startup blurb | market map, problem, solution |
| **4. Graph Builder** | Creates relationships | 2 | Extracted items | nodes + edges |
| **5. Opportunity Finder** | Searches graph for gaps | 3 | Knowledge graph | candidate opportunities |
| **6. Critic** | Kills bad ideas | 4 | Opportunities | survived / rejected |
| **7. Report Writer** | Produces final output | 4 | Survived opportunities | formatted reports |

### Agent Prompt Pattern (all extractors)

```
You are a {type} analyst for AIVE.

Read this {type} and extract structured knowledge.

Return JSON only:
{
  "problem": "What problem does this address?",
  "solution": "What solution or technology is proposed?",
  "technology": "Core technology in plain language",
  "keywords": ["keyword1", "keyword2"],
  "industry": ["education"],
  "summary": "2-sentence summary"
}
```

### Connector / Opportunity Finder Logic

```
FOR each problem_node in graph:
  FOR each technology_node where edge.weight > 0.5:
    FOR each market_node in same industry:
      IF no startup already combines all three:
        GENERATE opportunity
        SEND to Critic
```

---

## 9. Technology Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Simple, you are learning it |
| LLM | OpenAI API (or Anthropic) | Start with API, no local models yet |
| Storage | SQLite | Zero setup, file-based |
| Embeddings | OpenAI `text-embedding-3-small` | Week 2+ for similarity search |
| Web UI | Flask + basic HTML | Week 3, or terminal first |
| Paper fetch | arXiv API | Already working in `radar.py` |

### Dependencies (`requirements.txt`)

```
openai
flask
sqlite3  # built-in
requests
python-dotenv
```

### Environment (`.env`)

```
OPENAI_API_KEY=sk-...
AIVE_DB_PATH=./data/aive.db
AIVE_DOMAIN=edtech
```

---

## 10. Project Structure

```
AIC/
├── AIVE_V0_SPEC.md          ← this document
├── radar.py                  ← arXiv fetcher (DONE)
├── requirements.txt
├── .env
├── .gitignore
│
├── data/
│   ├── aive.db               ← SQLite database
│   ├── raw/
│   │   ├── papers/           ← cached arXiv responses
│   │   ├── patents/          ← manual patent text files
│   │   └── startups/         ← startup description files
│   └── exports/
│       └── opportunities.json
│
├── db/
│   ├── schema.sql            ← table definitions
│   └── init_db.py            ← create tables
│
├── ingest/
│   ├── fetch_papers.py       ← extends radar.py, saves to DB
│   ├── import_patents.py     ← manual import helper
│   └── import_startups.py    ← manual import helper
│
├── agents/
│   ├── base.py               ← shared LLM call + JSON parse
│   ├── research_analyst.py
│   ├── patent_analyst.py
│   ├── startup_analyst.py
│   ├── graph_builder.py
│   ├── opportunity_finder.py
│   ├── critic.py
│   └── report_writer.py
│
├── graph/
│   └── knowledge_graph.py    ← node/edge CRUD + queries
│
├── app/
│   └── main.py               ← Flask dashboard (Week 3)
│
└── run.py                    ← CLI entry point
```

---

## 11. Database Schema (SQLite)

```sql
-- Raw knowledge items
CREATE TABLE items (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    source      TEXT,
    source_url  TEXT,
    type        TEXT NOT NULL,  -- paper | patent | startup
    raw_text    TEXT,
    summary     TEXT,
    problem     TEXT,
    solution    TEXT,
    technology  TEXT,
    keywords    TEXT,           -- JSON array
    industry    TEXT,           -- JSON array
    year        TEXT,
    extracted_at TEXT,
    extraction_status TEXT DEFAULT 'pending'  -- pending | done | failed
);

-- Knowledge graph nodes
CREATE TABLE nodes (
    id          TEXT PRIMARY KEY,
    label       TEXT NOT NULL,
    node_type   TEXT NOT NULL,  -- technology | problem | industry | benefit | market
    source_items TEXT            -- JSON array of item IDs
);

-- Knowledge graph edges
CREATE TABLE edges (
    id            TEXT PRIMARY KEY,
    from_node     TEXT REFERENCES nodes(id),
    to_node       TEXT REFERENCES nodes(id),
    relationship  TEXT,         -- solves | enables | targets | competes_with
    weight        REAL DEFAULT 0.5,
    evidence      TEXT           -- JSON array of item IDs
);

-- Generated opportunities
CREATE TABLE opportunities (
    id              TEXT PRIMARY KEY,
    title           TEXT,
    problem_node    TEXT REFERENCES nodes(id),
    technology_node TEXT REFERENCES nodes(id),
    market_node     TEXT REFERENCES nodes(id),
    reasoning       TEXT,
    confidence      TEXT,       -- low | medium | high
    source_papers   TEXT,       -- JSON array
    source_patents  TEXT,
    source_startups TEXT,
    critic_verdict  TEXT,       -- pending | survived | rejected
    critic_notes    TEXT,
    created_at      TEXT
);

-- Rejected ideas (for learning)
CREATE TABLE rejected_ideas (
    id          TEXT PRIMARY KEY,
    opportunity_id TEXT REFERENCES opportunities(id),
    reason      TEXT,
    rejected_at TEXT
);
```

---

## 12. Implementation Plan — 30 Days

### Week 1 — Data + Extraction (Days 1–7)

**Goal:** 60 items ingested, 3 extractors running, first structured knowledge in DB.

| Day | Task | Deliverable |
|---|---|---|
| **Day 1** ✅ | Run `radar.py`, commit edtech domain | 10 live papers in terminal |
| **Day 2** | `schema.sql` + `init_db.py` + extend `radar.py` to save papers | SQLite DB with 20 papers |
| **Day 3** | `agents/base.py` + `research_analyst.py` | First paper extracted to JSON |
| **Day 4** | Run extractor on all 20 papers | 20 structured paper records |
| **Day 5** | Manual collect 20 patents + `import_patents.py` | 20 patents in DB |
| **Day 6** | `patent_analyst.py` + run on all patents | 20 structured patent records |
| **Day 7** | Collect 20 startups + `startup_analyst.py` | 60 total structured items |

**Week 1 exit criteria:**
- [ ] 60 items in SQLite (20 each type)
- [ ] All items have `problem`, `solution`, `keywords` populated
- [ ] You can query: "show me all education + AI problems"

---

### Week 2 — Knowledge Graph (Days 8–14)

**Goal:** Graph built from 60 items. Collect remaining data to 100 each.

| Day | Task | Deliverable |
|---|---|---|
| **Day 8** | `graph/knowledge_graph.py` — node/edge tables | Graph schema live |
| **Day 9** | `agents/graph_builder.py` | First nodes + edges from 20 papers |
| **Day 10** | Run graph builder on all 60 items | Full graph from Week 1 data |
| **Day 11–13** | Collect remaining 80 papers, 80 patents, 80 startups | 300 total items |
| **Day 14** | Re-run all extractors + graph builder on full dataset | Graph with 300-item coverage |

**Week 2 exit criteria:**
- [ ] Knowledge graph with 50+ nodes, 100+ edges
- [ ] 300 items total in database
- [ ] Visual query: "what technologies connect to teacher shortage?"

---

### Week 3 — Opportunity Engine (Days 15–21)

**Goal:** First 10 generated opportunities with reasoning and sources.

| Day | Task | Deliverable |
|---|---|---|
| **Day 15** | `agents/opportunity_finder.py` — graph traversal logic | First raw opportunity candidate |
| **Day 16** | Add embeddings for similarity boost (optional) | Better cross-domain matching |
| **Day 17–18** | Run opportunity finder, generate 20 candidates | 20 candidate opportunities |
| **Day 19** | `agents/report_writer.py` | First formatted opportunity report |
| **Day 20–21** | Refine prompts, re-run, pick top 10 | **10 opportunities delivered** |

**Week 3 exit criteria:**
- [ ] 10 opportunities with sources (papers + patents + startups)
- [ ] Each has problem + technology + market + reasoning
- [ ] At least 1 makes you say "I didn't think of that"

---

### Week 4 — Critic + Dashboard (Days 22–30)

**Goal:** Quality filter live. Simple dashboard. Daily output automated.

| Day | Task | Deliverable |
|---|---|---|
| **Day 22** | `agents/critic.py` | First rejected idea logged |
| **Day 23** | Run critic on all 20 candidates, keep survivors | Quality-filtered list |
| **Day 24–26** | `app/main.py` Flask dashboard (5 tabs) | Web UI running locally |
| **Day 27** | `run.py` daily pipeline script | One command runs full pipeline |
| **Day 28–30** | Generate 100 opportunities, score them | Success metric: 5–10 surprising ones |

**Week 4 exit criteria:**
- [ ] Critic rejecting obvious/bad ideas
- [ ] Dashboard with 5 tabs (Papers, Patents, Graph, Opportunities, Rejected)
- [ ] Daily automated output
- [ ] 5–10 opportunities rated "surprisingly interesting"

---

## 13. Dashboard V0 (Week 3–4)

Five tabs. Nothing more.

| Tab | Shows |
|---|---|
| **Papers** | Latest ingested papers with extraction status |
| **Patents** | Latest patents with technology map |
| **Knowledge Graph** | Node/edge list (text first, visual later) |
| **Opportunities** | Generated opportunities with confidence + sources |
| **Rejected Ideas** | What the Critic killed and why |

Terminal output is acceptable for Week 1–2. Dashboard is Week 3.

---

## 14. CLI Commands (target state)

```bash
# Ingest
python ingest/fetch_papers.py --count 20
python ingest/import_patents.py --file data/raw/patents/batch1.txt
python ingest/import_startups.py --file data/raw/startups/yc_edtech.csv

# Extract
python agents/research_analyst.py --all
python agents/patent_analyst.py --all
python agents/startup_analyst.py --all

# Graph + Opportunities
python agents/graph_builder.py --all
python agents/opportunity_finder.py --count 10
python agents/critic.py --all

# Full pipeline
python run.py daily

# Dashboard
python app/main.py
```

---

## 15. Success Criteria

### Primary (Week 1 end)

| Metric | Target |
|---|---|
| Structured items in DB | 60 (20 per type) |
| Extraction success rate | > 90% |
| Manual review | At least 3 items have useful problem/solution fields |

### Primary (Week 3 end)

| Metric | Target |
|---|---|
| Generated opportunities | 10 |
| Each with 2+ source types | Yes |
| "Surprisingly interesting" count | ≥ 1 |

### Primary (Week 4 / Day 30)

| Metric | Target |
|---|---|
| Total opportunities generated | 100 |
| Surprisingly interesting | 5–10 |
| Rejected by Critic | > 50% (healthy filter) |
| Cross-domain combinations | At least 3 domains humans rarely combine |

### Failure signals

- Zero opportunities survive the Critic → prompts need rework
- All opportunities are obvious combinations → graph is too shallow
- Extractors return empty fields → LLM prompts or input quality problem
- Everything sounds impressive but cites no real sources → hallucination, stop

---

## 16. Learning Roadmap (parallel track)

Learn while building. Do not learn everything first.

| Week | Learn | While building |
|---|---|---|
| 1 | Python basics, JSON, SQLite, API calls | `radar.py`, DB, first agent |
| 2 | SQL queries, data modeling, graph concepts | Graph builder |
| 3 | Prompt engineering, structured output | Opportunity finder |
| 4 | Embeddings, RAG basics, Flask | Critic + dashboard |

---

## 17. What Is Forbidden (30 days)

- Funding conversations
- Company registration
- Investor outreach
- Patent lawyers
- "100 agents" architecture
- Venture studios
- Billion-dollar valuation thinking
- Building features not in this spec
- Complex databases (Postgres, Neo4j) — SQLite only
- Local LLM hosting — API only for V0

---

## 18. Immediate Next Steps (Day 2)

1. Create `db/schema.sql` and `db/init_db.py`
2. Extend `radar.py` → `ingest/fetch_papers.py` (fetch + save to SQLite)
3. Fetch 20 papers into the database
4. Create `agents/base.py` (LLM call wrapper)
5. Create `agents/research_analyst.py`
6. Run extractor on first paper — verify JSON output

**Status: Building Day 2.**

---

## 19. Example Opportunity (target output)

```
Opportunity #1
──────────────
Title:    Socratic Offline Tutor for Rural Classrooms

Problem:  Unstructured LLM chat fails to teach; teacher shortage in rural areas
Technology: Dialogue policy optimization + on-device small LLMs
Market:   Rural K-12 schools without reliable internet

Why:
  • Paper: "Hey Chat, Can You Teach Me?" — proves structured Socratic LLM dialogue works
  • Paper: "Sequential Fine-Tuning of LLaMA for Essay Scoring" — local model fine-tuning viable
  • Patent: [low-power edge inference chip for education devices]
  • Startup: [rural edtech platform with offline-first positioning]
  • Gap: No product combines Socratic structure + offline local models + rural distribution

Confidence: Medium
Critic: Survived — competitor X exists but requires cloud connectivity
```

---

*This document is the foundation. Code follows design. Design follows this.*

---

## 20. CTO Review Addendum (locked — no V0.2 redesign)

**First real proof:** One opportunity survives the Critic and genuinely surprises you. Not 300 documents. Not a dashboard.

### V0 changes (accepted)

| Change | Rationale |
|---|---|
| **20/20/20 first** | Full pipeline end-to-end before scaling to 100 each |
| **No dashboard** | Terminal + JSON + Markdown report only |
| **Opportunity Quality Score** | Novelty, Timing, Market, Feasibility, Defensibility — each 0–10 |
| **Signal extraction > volume** | Better extraction beats more documents |

### V1+ backlog (note, do not build yet)

| Item | Why it matters |
|---|---|
| **Feedback loop** | Opportunity → Human eval → Outcome tracking → Learning |
| **Opportunity memory** | Did someone build it? Fund it? Why did it fail? |
| **Temporal layer** | First seen, momentum, trend velocity on nodes |
| **Critic expansion** | Technical, Market, Timing, Competition, Distribution critics |
| **Node hierarchy** | Separate Opportunity → Product → Invention → Company |
| **Human insight layer** | Founder interviews, research notes, user pain points |

### Evolution path (future, not V0)

```
Knowledge Discovery → Opportunity Discovery → Product Discovery → Invention Discovery → Venture Discovery
```

**Rule:** Build the pipeline as written. Stop redesigning when code can run.

**Execution plan:** See `AIVE_PHASE0_OPERATING_PLAN.md` — the 90-day day-by-day schedule. Follow that, not this document.
