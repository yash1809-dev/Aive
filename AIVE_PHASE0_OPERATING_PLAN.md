# AIVE Phase 0 — 90-Day Execution Operating Plan

**Mode:** Founder  
**Start:** June 12, 2026  
**End:** September 10, 2026 (Day 90)  
**Domain:** Edtech (AI + Education)

> Architecture is done. This document is the only plan you follow until Day 90.

---

## Mission

Prove one thing:

> **Can AIVE generate opportunities that are better than what you would find manually?**

Nothing else matters until this is answered with evidence.

---

## Day 90 Success Criteria

| # | Criterion | Target |
|---|---|---|
| 1 | Knowledge items in DB | 300+ |
| 2 | Extraction pipeline | Working end-to-end |
| 3 | Knowledge graph | Working, queryable |
| 4 | Opportunity engine | Generating candidates |
| 5 | Critic engine | Killing 70%+ of candidates |
| 6 | Total opportunities generated | 100 |
| 7 | Genuinely surprising opportunities | 5 |
| 8 | External users who tested results | 3 |

**The real goal:** AIVE discovers **one** opportunity that a smart human would likely miss — with evidence (papers, patents, startups cited).

If that happens once, the core thesis is proven. Everything after that is scaling.

---

## Current State (as of Day 1)

| Done | Not done |
|---|---|
| `radar.py` — 10 live arXiv papers | Research Analyst not run |
| `db/schema.sql` + `init_db.py` | Patents, startups, graph, opportunities |
| `ingest/fetch_papers.py` — 20 papers in DB | |
| `agents/base.py` + `research_analyst.py` | |

**Resume at Day 4: Research Analyst on first paper.**

---

## Daily Schedule (4 hours)

| Block | Time | Activity |
|---|---|---|
| **Code** | 2 hrs | Build or run the pipeline step for today |
| **Read** | 1 hr | Read 1–2 papers from your ingested set |
| **Document** | 30 min | Log what worked, what failed, what surprised you |
| **Plan** | 30 min | Set tomorrow's single task before closing |

**Rule:** One primary task per day. Finish it before starting the next.

---

## What NOT To Build (until Day 90)

- Venture studio
- Startup factory
- Patent filing engine
- Autonomous research company
- Multi-agent civilization
- Company registration
- Fundraising
- Incubators
- Investor outreach
- Dashboard (until Week 8)

---

## When To Register a Company

Only after **one** of these:

| Trigger | Signal |
|---|---|
| **A** | First paying customer |
| **B** | Accepted into incubator |
| **C** | Co-founder joins |
| **D** | Revenue starts |

Before that: zero reason.

---

## Tools To Learn (priority order)

### Level 1 — Now (Month 1)

- Python
- SQLite
- JSON
- Git

### Level 2 — Month 2

- OpenAI APIs
- Embeddings
- Vector search

### Level 3 — After Day 90

- Knowledge graphs (Neo4j)
- LangGraph

Do not jump levels early.

---

# MONTH 1 — Foundation

## Week 1: Data Layer (Days 1–7)

**Goal:** 40 structured records (20 papers + 20 patents)

| Day | Date | Task | Command / Action | Done? |
|---|---|---|---|---|
| **1** | Jun 12 | Repo setup + first arXiv fetch | `python radar.py` | ✅ |
| **2** | Jun 13 | Init SQLite DB | `python db/init_db.py` | ✅ |
| **3** | Jun 14 | Paper ingestion → 20 papers in DB | `python ingest/fetch_papers.py 20` | ✅ |
| **4** | Jun 15 | Research Analyst — quality gate on 3 papers | `python agents/quality_check.py 3` | ✅ |
| **5** | Jun 16 | Run extraction on all 20 papers | `python agents/research_analyst.py 17` | ✅ |
| **6** | Jun 17 | Collect 20 patents + import | `python ingest/import_patents.py` | ✅ |
| **7** | Jun 18 | Patent extractor + run on all 20 | `python agents/patent_analyst.py 20` | ✅ |

**Week 1 deliverable:** 40 structured records in SQLite.

**Exit check:**
```sql
SELECT type, extraction_status, COUNT(*) FROM items GROUP BY type, extraction_status;
-- Expected: 20 paper done, 20 patent done
```

---

## Week 2: Complete Data Layer + Graph (Days 8–14)

**Goal:** 60 records + first knowledge graph

| Day | Date | Task | Done? |
|---|---|---|---|
| **8** | Jun 19 | Collect 20 startup descriptions + import | `python ingest/import_startups.py` | ✅ |
| **9** | Jun 20 | Startup extractor + run on all 20 | `python agents/startup_analyst.py 20` | ✅ |
| **10** | Jun 21 | Build `graph/knowledge_graph.py` | done | ✅ |
| **11** | Jun 22 | Build `agents/graph_builder.py` | done | ✅ |
| **12** | Jun 23 | Run graph builder on all 60 items | `python agents/graph_builder.py` | ✅ |
| **13** | Jun 24 | Test graph queries | `python agents/graph_builder.py query educator` | ✅ |
| **14** | Jun 25 | Scale to 100 papers, 100 patents, 100 startups (batch ingest) | ☐ |

**Week 2 deliverable:** First graph. You can ask:

> Which technologies connect to teacher shortages?

**Exit check:**
```sql
SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type;
SELECT relationship, COUNT(*) FROM edges GROUP BY relationship;
-- Expected: 30+ nodes, 50+ edges
```

---

# MONTH 2 — Intelligence Layer

## Week 3: Opportunity Engine (Days 15–21)

**Goal:** 20 generated opportunities (JSON only, no UI)

| Day | Date | Task | Done? |
|---|---|---|---|
| **15** | Jun 26 | Build `agents/opportunity_finder.py` | `python agents/opportunity_finder.py 10` | ✅ |
| **16** | Jun 27 | Test: Problem + Technology + Market = Opportunity | ☐ |
| **17** | Jun 28 | Generate first 5 opportunities | ☐ |
| **18** | Jun 29 | Generate 20 opportunities total | ☐ |
| **19** | Jun 30 | Build `agents/report_writer.py` — Markdown output | ☐ |
| **20** | Jul 1 | Review all 20 — mark which surprise you | ☐ |
| **21** | Jul 2 | Refine opportunity finder prompts based on review | ☐ |

**Week 3 deliverable:** `data/exports/opportunities_batch1.json` + Markdown report.

**Output format:**
```json
{
  "title": "...",
  "problem": "...",
  "technology": "...",
  "market": "...",
  "reasoning": "...",
  "sources": { "papers": [], "patents": [], "startups": [] },
  "scores": { "novelty": 0, "timing": 0, "market": 0, "feasibility": 0, "defensibility": 0 }
}
```

---

## Week 4: Critic Engine (Days 22–28)

**Goal:** Kill 70%. 5 survivors. First opportunity report.

| Day | Date | Task | Done? |
|---|---|---|---|
| **22** | Jul 3 | Build `agents/critic.py` | ☐ |
| **23** | Jul 4 | Run critic on all 20 opportunities | ☐ |
| **24** | Jul 5 | Review survivors — do any surprise you? | ☐ |
| **25** | Jul 6 | If 0 survivors surprise you: fix extraction, not architecture | ☐ |
| **26** | Jul 7 | Generate 20 more opportunities with improved pipeline | ☐ |
| **27** | Jul 8 | Critic pass #2 | ☐ |
| **28** | Jul 9 | Write first opportunity report (`reports/opportunity_report_001.md`) | ☐ |

**Critic questions (V0):**

1. Already exists?
2. Too crowded?
3. Too early?
4. No customer?

**Week 4 deliverable:** First opportunity report with ≥1 survivor that surprises you.

**If zero surprises:** Stop. Fix extraction and graph quality. Do not add agents.

---

# MONTH 3 — Validation Layer

> Most founders skip this. Do not skip.

## Week 5: External Validation (Days 29–35)

**Goal:** 15 conversations. Document answers.

| Day | Date | Task | Done? |
|---|---|---|---|
| **29** | Jul 10 | Prepare 3-opportunity summary to share | ☐ |
| **30** | Jul 11 | Talk to 2 founders | ☐ |
| **31** | Jul 12 | Talk to 2 researchers | ☐ |
| **32** | Jul 13 | Talk to 2 students | ☐ |
| **33** | Jul 14 | Talk to 3 more (any category) | ☐ |
| **34** | Jul 15 | Talk to 3 more | ☐ |
| **35** | Jul 16 | Talk to 3 more — hit 15 total | ☐ |

**Ask every person:**

1. Would you have found this yourself?
2. Is this interesting or obvious?
3. What's missing?

**Log in:** `data/validation/feedback_log.md`

**Week 5 deliverable:** 15 documented conversations. 3 external users who tested results.

---

## Week 6: Improve Pipeline (Days 36–42)

**Goal:** Better extraction, graph, prompts. Generate 50 opportunities.

| Day | Date | Task | Done? |
|---|---|---|---|
| **36** | Jul 17 | Review feedback — identify top 3 extraction failures | ☐ |
| **37** | Jul 18 | Fix Research Analyst prompts | ☐ |
| **38** | Jul 19 | Fix Patent + Startup Analyst prompts | ☐ |
| **39** | Jul 20 | Fix Graph Builder — improve edge quality | ☐ |
| **40** | Jul 21 | Re-extract all items with improved prompts | ☐ |
| **41** | Jul 22 | Rebuild graph | ☐ |
| **42** | Jul 23 | Generate 50 opportunities | ☐ |

**Week 6 deliverable:** 50 opportunities with improved quality.

---

## Week 7: Scale + Score (Days 43–49)

**Goal:** 100 opportunities. Quality-scored.

| Day | Date | Task | Done? |
|---|---|---|---|
| **43** | Jul 24 | Generate opportunities 51–75 | ☐ |
| **44** | Jul 25 | Generate opportunities 76–100 | ☐ |
| **45** | Jul 26 | Run critic on all 100 | ☐ |
| **46** | Jul 27 | Score survivors: Novelty, Timing, Market, Feasibility, Defensibility (0–10 each) | ☐ |
| **47** | Jul 28 | Rank top 10 by total score | ☐ |
| **48** | Jul 29 | Re-read top 10 — mark genuinely surprising ones | ☐ |
| **49** | Jul 30 | Write `reports/day60_progress.md` | ☐ |

**Week 7 deliverable:** 100 opportunities. Top 10 scored and ranked.

---

## Week 8: Dashboard + Day 90 Review (Days 50–56 → Day 90)

**Goal:** Simple dashboard. Final review. Go/no-go on AIVE V1.

| Day | Date | Task | Done? |
|---|---|---|---|
| **50** | Jul 31 | Build minimal Flask dashboard (5 tabs) | ☐ |
| **51** | Aug 1 | Papers tab | ☐ |
| **52** | Aug 2 | Patents + Graph tabs | ☐ |
| **53** | Aug 3 | Opportunities + Rejected tabs | ☐ |
| **54–82** | Aug 4–Sep 1 | Buffer: fix bugs, ingest more data, generate more opportunities | ☐ |
| **83–89** | Sep 2–Sep 8 | Final scoring, external re-validation with 3 users | ☐ |
| **90** | Sep 9 | Day 90 review — go/no-go decision | ☐ |

**Dashboard tabs (only now, not before):**

1. Papers
2. Patents
3. Graph
4. Opportunities
5. Rejected

---

# Day 90 Review Checklist

| Question | Yes / No |
|---|---|
| 300+ knowledge items in DB? | |
| Extraction pipeline works end-to-end? | |
| Graph answers cross-domain queries? | |
| 100 opportunities generated? | |
| Critic kills 70%+? | |
| 5 opportunities genuinely surprised you? | |
| 3 external users tested and gave feedback? | |
| At least 1 opportunity a smart human would likely miss? | |

**If 6+ Yes → AIVE V1.** Monetization, users, business model become real.  
**If <4 Yes → Fix the pipeline. Do not pivot. Do not register. Do not fundraise.**

---

# Weekly Log Template

Copy this into `data/logs/week_N.md` every Sunday:

```markdown
## Week N — [date range]

### Built
- 

### Ran
- 

### Surprised me
- 

### Failed
- 

### Next week (one goal)
- 
```

---

# File Checklist (build in order)

```
Phase 0 build order — do not skip ahead

[✅] radar.py
[✅] db/schema.sql
[✅] db/init_db.py
[✅] ingest/fetch_papers.py
[✅] agents/base.py
[✅] agents/research_analyst.py
[ ] agents/patent_analyst.py          ← Week 1 Day 7
[ ] ingest/import_patents.py          ← Week 1 Day 6
[ ] agents/startup_analyst.py         ← Week 2 Day 9
[ ] ingest/import_startups.py         ← Week 2 Day 8
[ ] graph/knowledge_graph.py          ← Week 2 Day 10
[ ] agents/graph_builder.py           ← Week 2 Day 11
[ ] agents/opportunity_finder.py      ← Week 3 Day 15
[ ] agents/report_writer.py           ← Week 3 Day 19
[ ] agents/critic.py                  ← Week 4 Day 22
[ ] run.py                            ← Week 4 (one-command pipeline)
[ ] app/main.py                       ← Week 8 only
```

---

# Tomorrow (Day 2)

One task. Nothing else.

```powershell
cd c:\Users\Asus\Documents\AIC
python db/init_db.py
python ingest/fetch_papers.py 20
```

Then verify:

```powershell
python -c "import sqlite3; c=sqlite3.connect('data/aive.db'); print(c.execute('SELECT COUNT(*) FROM items').fetchone())"
```

Expected output: `(20,)`

---

*No more architecture documents. Execute this plan.*
