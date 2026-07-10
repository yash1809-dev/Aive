# AIVE Domain Map

**Source:** 20 edtech papers (arXiv), extracted June 2026  
**Purpose:** Founder intuition — what patterns exist before graph automation

---

## Knowledge Quality Review

### 1. Five biggest problems appearing repeatedly

1. **Unstructured LLM tutoring** — Chat-based learning lacks curriculum sequencing, Socratic structure, and student knowledge inference ("Hey Chat", IntElicit, AI delegation in education).

2. **Assessment blind spots** — Essay scoring coherence, MCQ difficulty estimation, physics misconceptions, and knowledge-tracing cold-start all point to the same gap: we cannot reliably model what a student knows from sparse data.

3. **Academic integrity under LLM pressure** — Students use LLMs in morally gray ways; institutions lack guidance on acceptable assistance and authorship.

4. **Privacy and local inference** — Special-education IEP generation and research infrastructures (SafeInsights) need on-device, schema-constrained LLMs — cloud dependence is a blocker.

5. **Measurement confusion** — Learner agency, autonomy, and creativity are measured inconsistently (jingle-jangle fallacy), polluting both research and AI system design.

### 2. Five technologies appearing repeatedly

1. **Knowledge graphs** — Prerequisite graphs for tutoring, Neo4j for diagnostics, skill-dependency graphs for learning paths, soft priors for Bayesian networks.

2. **Dialogue policy + reinforcement learning** — PPO for curriculum sequencing, dialogue policy optimization for Socratic tutoring and creativity elicitation.

3. **Knowledge tracing / student modeling** — Deep learning models predicting skill mastery; cold-start remains unsolved.

4. **Efficient local LLMs** — LoRA, QLoRA, 4-bit quantization, Breeze-7B fine-tuning for domain-specific education tasks.

5. **Structure-aware assessment models** — Distractor-aware MCQ difficulty, sequential essay scoring, multidimensional item-response models.

### 3. Three most interesting combinations

| # | Problem | Technology | Market | Why it's interesting |
|---|---|---|---|---|
| **A** | Unstructured LLM tutoring | PKG + PPO Socratic sequencing + local LoRA LLM | Rural / low-connectivity schools | No product combines curriculum structure, offline inference, and student state tracking — papers exist separately, patents cover pieces, no startup owns the intersection. |
| **B** | Assessment + cold-start tracing | Knowledge tracing + distractor-aware MCQ + AES | K-12 formative assessment | Three assessment modalities (essays, MCQs, practice logs) rarely fused into one student model — graph could link these nodes. |
| **C** | Teacher/admin workload + privacy | Corpus-grounded local IEP generation + schema-constrained decoding | Special education (Traditional Chinese, extensible) | Reduces paperwork burden with privacy-preserving local LLM — connects to broader "teacher shortage" problem without naming it directly in papers. |

---

## Top Problems

1. LLM tutoring without curriculum structure or student knowledge inference
2. Unreliable student knowledge modeling (cold-start, sparse data, assessment gaps)
3. Academic integrity and emotional burden of LLM use in education
4. Cloud-dependent AI blocking privacy-sensitive education contexts
5. Inconsistent measurement of learner constructs (agency, autonomy, creativity)

---

## Top Technologies

1. Prerequisite / skill-dependency knowledge graphs
2. Socratic dialogue with PPO or dialogue policy optimization
3. Deep knowledge tracing and student state models
4. Parameter-efficient local LLM fine-tuning (LoRA, QLoRA)
5. Structure-aware automated assessment (MCQ, essay, misconception detection)

---

## Top Beneficiaries

1. **Students** — K-12, STEM, special education, higher ed
2. **Teachers** — reduced grading, tutoring, IEP paperwork burden
3. **Schools / institutions** — scalable assessment, integrity policies
4. **Education researchers** — reproducible infrastructure, better constructs
5. **Underserved learners** — privacy-preserving, offline, culturally-aware contexts

---

## Interesting Repeated Patterns

1. **Teacher workload appears under different names** — IEP automation, essay scoring, formative assessment, tutoring support. AIVE should merge: *Educator Capacity Constraint*.

2. **Knowledge graphs appear in 4+ papers** but never connected to the same problem node — tutoring PKG, TCM diagnostics, skill paths, Bayesian priors. Graph Builder's first job: unify these.

3. **Local/offline inference is implicit, not central** — IEP paper uses local Breeze-7B; essay paper uses efficient LoRA; no paper says "rural offline schools" but the technology stack points there.

---

## Clusters (preview for Graph Builder)

```
Cluster A — Tutoring & Curriculum
  Teacher capacity / unstructured chat → PKG + Socratic PPO → K-12 STEM

Cluster B — Assessment & Tracing
  Cold-start + misconceptions + AES → student models → formative assessment

Cluster C — Trust & Privacy
  Academic integrity + local LLM + schema decoding → institutions + special ed
```

---

## Node Merge Candidates (Paper #1 ↔ Paper #17 test)

| Paper A says | Paper B says | Should merge to |
|---|---|---|
| "Unstructured LLM tutoring" | "Contextualized creativity assessment in AI dialogue" | **Structured AI-Mediated Learning** |
| "Cold-start in knowledge tracing" | "MCQ difficulty + misconception detection" | **Student Knowledge Modeling Gap** |
| "IEP generation workload" | "Automated essay scoring workload" | **Educator Administrative Burden** |

If Graph Builder creates these merged nodes, the system is working.

---

## One-Page Test

**Pass.** All 20 papers fit into three clusters (Tutoring, Assessment, Trust/Privacy) with five recurring problems and five technologies.

Extractor quality: **7.5–8/10** (acceptable). Industry field occasionally generic; problem/technology fields are paper-specific.

**Do not scale to 1000 papers yet.** Next: 20 patents → look for technology nodes that papers don't cover.
