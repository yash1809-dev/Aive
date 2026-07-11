# Design Document

## Overview

AIVE's existing 5-layer pipeline (ingest → extract → graph → opportunities → critic) is preserved entirely. Three new capability layers are added on top:

- **Understanding Layer** — `agents/universal_analyst.py` handles any document type
- **Discovery Layer** — `agents/discovery_classifier.py` detects gaps, contradictions, and transfers
- **Intelligence Layer** — `agents/report_builder.py` and `engines/qa_engine.py` generate research-grade outputs

Every new capability is a new file. No existing agent, engine, or route is rewritten. Backward compatibility is non-negotiable.

## Architecture

```
Existing (unchanged):
  Layer 1  Data Layer          ingest/, data/
  Layer 2  Knowledge Extraction agents/research_analyst.py
                                agents/patent_analyst.py
                                agents/startup_analyst.py
  Layer 3  Knowledge Graph      graph/knowledge_graph.py
  Layer 4  Opportunity Engine   agents/opportunity_finder.py
  Layer 5  Critic Engine        agents/critic.py

New (added):
  Layer 6  Understanding        agents/universal_analyst.py
                                graph/label_normalizer.py
  Layer 7  Discovery            agents/discovery_classifier.py
  Layer 8  Intelligence         agents/report_builder.py
                                engines/qa_engine.py
                                db/migrate_v2.py

New API routes (added to app/main.py):
  POST /api/understand
  GET  /api/discoveries
  GET  /api/contradictions
  GET  /api/research-gaps
  POST /api/reports/generate-deep
  GET  /api/visualizations/funnel
  GET  /api/visualizations/scores
  GET  /api/visualizations/timeline
  GET  /api/visualizations/distribution

New frontend (added to app/templates/index.html):
  Inspector: Insights tab (funnel + distribution charts)
  Sidebar: Discoveries nav item
  Canvas: New node types for contradictions, gaps, transfers
  Copilot: Evidence reference badges + confidence indicator
```

## Components and Interfaces

### Component 1: UniversalAnalyst (`agents/universal_analyst.py`)

**Responsibility:** Extract structured knowledge from any document type.

**Interface:**
```python
class UniversalAnalyst:
    def classify(self, raw_text: str, metadata: dict) -> dict:
        """
        Returns:
            doc_type: str  -- paper|patent|startup|report|technical_doc|news|dataset|other
            domain: str    -- auto-detected from content (e.g. "materials science")
            dimensions: list[str]  -- which fields are present
        """

    def extract(self, item: dict) -> dict:
        """
        Returns standard extraction schema plus:
            doc_type: str
            domain: str
            evidence_classification: dict  -- per-field: fact|inference|hypothesis|unknown
            confidence: float
        """

    def run(self, item_id: str, db_path: Path = DB_PATH) -> dict:
        """Full pipeline: load item → classify → extract → save → return result"""
```

**Prompt design (classification):**
The classifier prompt provides no domain hints. It instructs the LLM: "Read this document and identify: what type of document this is, what domain it belongs to, what structured knowledge dimensions are present." Output is JSON with doc_type, domain, and dimensions array.

**Prompt design (extraction):**
For detected paper/patent/startup types, the existing specialist prompts are used. For all other types, a universal extraction prompt asks: "Extract whatever structured knowledge exists in this document. Identify the central problem or challenge, the proposed solution or technology, the intended market or application, key concepts, and beneficiaries. For each extracted field, indicate whether the claim is a direct fact from the source, an inference, a hypothesis, or unknown." Output follows the standard extraction schema.

**Evidence classification storage:**
The `evidence_classification` JSON column on `items` stores per-field classifications:
```json
{"problem": "fact", "technology": "inference", "market": "hypothesis", "summary": "inference"}
```

### Component 2: LabelNormalizer (`graph/label_normalizer.py`)

**Responsibility:** Reduce graph label duplication across any domain without hardcoding.

**Interface:**
```python
class LabelNormalizer:
    def normalize(self, label: str, existing_labels: list[str]) -> str:
        """Returns canonical form: MERGE_MAP fast-path first, then similarity."""

    def token_similarity(self, a: str, b: str) -> float:
        """Jaccard similarity on word tokens."""

    def is_mergeable(self, new_label: str, existing_label: str) -> bool:
        """True if one is a substring of the other, or token Jaccard > 0.7."""
```

**Integration point:** Called in `graph/knowledge_graph.py` `upsert_node()` after the MERGE_MAP fast path. No LLM calls — pure string operations for speed.

**Merge log:** Writes discovered merges to `data/merge_log.json` for operator review.

### Component 3: DiscoveryClassifier (`agents/discovery_classifier.py`)

**Responsibility:** Detect typed discoveries beyond commercial opportunities.

**Interface:**
```python
def find_research_gaps(db_path: Path) -> list[dict]:
    """Graph topology: problems with no technology, technologies with no buyer."""

def find_contradictions(db_path: Path, sample_size: int = 50) -> list[dict]:
    """LLM-as-judge: do any two items make conflicting claims about the same node?"""

def find_method_transfers(db_path: Path) -> list[dict]:
    """Technology nodes present in domain A context, absent from analogous domain B problems."""

def run(db_path: Path) -> dict:
    """Run all three detectors, save to discoveries and contradictions tables, return counts."""
```

**Research gap algorithm (no LLM):**
1. Query all Problem nodes
2. For each, check if any Technology/Capability node is connected via `solves` edge
3. Problems with no such connection = structural research gap
4. Query all Technology nodes
5. For each, check if any Buyer node is connected via `purchased_by` edge
6. Technologies with no buyer = commercialization gap

**Contradiction detection algorithm:**
1. Sample item pairs that share at least one graph node (indicating related content)
2. For each pair, extract `problem` and `technology` fields
3. LLM prompt: "Do these two documents make contradictory claims about [shared concept]? Answer YES/NO with explanation."
4. YES responses become contradiction records

### Component 4: ReportBuilder (`agents/report_builder.py`)

**Responsibility:** Generate publication-quality research reports with full section structure.

**Interface:**
```python
class ReportBuilder:
    def build(self, db_path: Path, output_path: Path,
              scope: str = "all",
              sections: list[str] = None) -> dict:
        """
        Generates full research-grade Markdown report.
        Returns: {report_path, word_count, sections_generated, opportunity_count}
        """
```

**Section generation strategy:**

Deterministic sections (no LLM, generated from DB):
- Evidence: list of all source items with provenance
- Knowledge Graph Summary: node counts, edge counts, type distribution table
- References: all cited items with source URLs

LLM-generated sections (each is an independent focused LLM call):
- Executive Summary: prompt receives top 5 opportunities + graph stats
- Key Findings: prompt receives all survived opportunities with scores
- Cross-Document Insights: prompt receives concept clusters (nodes with 3+ sources)
- Contradictions: prompt receives each contradiction record
- Research Gaps: prompt receives each gap record
- Risk Analysis: prompt receives each opportunity + its critic notes
- Validation Strategy: prompt receives each opportunity title + market + technology

**Hallucination prevention:** Every LLM prompt for report sections ends with: "Base every claim strictly on the provided data. Do not introduce information not present in the data. If insufficient data exists for a section, write 'Insufficient evidence for this section.'"

**Citation format:** Every LLM-generated section appends item IDs in brackets: `This technology shows strong commercial potential [paper_abc123]`.

### Component 5: QAEngine (`engines/qa_engine.py`)

**Responsibility:** Route questions to appropriate answering strategies with evidence grounding.

**Interface:**
```python
class QAEngine(BaseEngine):
    def answer(self, question: str, db_path: Path) -> dict:
        """Returns: {reply, evidence_refs, confidence, reasoning_path}"""

    def classify_question(self, question: str) -> str:
        """Returns: factual|graph|comparative|discovery|gap"""

    def answer_factual(self, question: str, db_path: Path) -> dict: ...
    def answer_graph(self, question: str, db_path: Path) -> dict: ...
    def answer_discovery(self, question: str, db_path: Path) -> dict: ...
    def answer_gap(self, question: str, db_path: Path) -> dict: ...
```

**Integration:** The existing `/api/copilot` route in `app/main.py` instantiates `QAEngine` and calls `answer()`. The response dict is merged with the existing response structure — `reply` key preserved, `evidence_refs` and `confidence` added.

## Data Models

### New column: `items.evidence_classification` (TEXT, JSON)
```json
{
  "problem": "fact",
  "solution": "inference",
  "technology": "fact",
  "market": "hypothesis",
  "summary": "inference"
}
```

### New column: `items.doc_type` (TEXT)
Values: `paper`, `patent`, `startup`, `report`, `technical_doc`, `news`, `dataset`, `other`

### New column: `items.domain` (TEXT)
Free text, auto-detected by UniversalAnalyst. Examples: `edtech`, `materials science`, `aerospace`, `healthcare`.

### New column: `opportunities.reasoning_chain` (TEXT, JSON)
```json
[
  {"type": "item", "id": "paper_abc123", "role": "evidence"},
  {"type": "node", "id": "node_problem_teacher_shortage", "label": "Teacher Shortage"},
  {"type": "edge", "relationship": "solves", "weight": 0.85},
  {"type": "node", "id": "node_technology_lora_fine_tuning", "label": "LoRA Fine-Tuning"},
  {"type": "conclusion", "text": "LoRA addresses teacher shortage via efficient local model training"}
]
```

### New table: `discoveries`
```sql
CREATE TABLE IF NOT EXISTS discoveries (
    id           TEXT PRIMARY KEY,
    type         TEXT NOT NULL,
    title        TEXT,
    description  TEXT,
    evidence     TEXT,
    source_nodes TEXT,
    confidence   REAL DEFAULT 0.5,
    reasoning    TEXT,
    created_at   TEXT
);
```

### New table: `contradictions`
```sql
CREATE TABLE IF NOT EXISTS contradictions (
    id           TEXT PRIMARY KEY,
    concept      TEXT,
    claim_a      TEXT,
    claim_b      TEXT,
    source_a     TEXT,
    source_b     TEXT,
    explanation  TEXT,
    confidence   REAL,
    created_at   TEXT
);
```

### API Response: `/api/copilot` (extended, backward compatible)
```json
{
  "status": "success",
  "reply": "...",
  "evidence_refs": ["paper_abc123", "startup_def456"],
  "confidence": "high"
}
```
`evidence_refs` and `confidence` are new optional fields. Existing consumers that only read `reply` are unaffected.

## Correctness Properties

Property 1: Every LLM call must pass through `agents/base.py:call_llm()` — no direct API calls in new agents.

Property 2: Every DB path must come from `db/init_db.DB_PATH` — no hardcoded database paths in new code.

Property 3: Every extracted claim must have an evidence phrase from the source document — no free generation allowed.

Property 4: No existing table, column, or row may be deleted by new migrations — all changes are additive.

Property 5: No existing API route signature may change — all new fields in responses are optional.

Property 6: Research gap detection must not call LLM — pure graph topology analysis only for performance.

## Error Handling

All new agents follow the existing AIVE error handling pattern:
- Wrap LLM calls in try/except
- On LLM failure: retry with fallback model (extractor if reasoner fails), then skip and log
- On DB error: re-raise after logging with `self.log_failure()`
- Never crash the pipeline — failed items get `extraction_status='failed'` or equivalent, pipeline continues

All new Flask routes follow the existing pattern:
```python
@app.route("/api/new-endpoint")
def new_endpoint():
    conn = get_db_connection()
    try:
        # logic
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
```

## Testing Strategy

Each new component can be tested independently:

- **UniversalAnalyst**: Call `classify()` on documents of known types and assert `doc_type` matches
- **LabelNormalizer**: Call `is_mergeable()` on known synonym pairs and assert True; on distinct pairs assert False
- **DiscoveryClassifier**: Run `find_research_gaps()` on the existing EdTech database and verify it returns nodes that genuinely have no technology connections
- **ReportBuilder**: Call `build()` and assert all 15 section headers are present in output; assert all `[item_id]` citations resolve to real items in DB
- **QAEngine**: Send known question types and assert `confidence` is not None and `evidence_refs` is a list
- **Visualization endpoints**: Assert all four endpoints return 200 with valid JSON against the existing database
- **Migration**: Run `migrate_v2.py` against a copy of `data/aive.db` and assert all new columns and tables exist without data loss in existing tables
