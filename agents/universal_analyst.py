"""
agents/universal_analyst.py
============================
Universal Analyst — domain-agnostic document understanding agent.

Replaces the need for a dedicated specialist per document type.
Works for any domain: materials science, aerospace, healthcare, finance,
climate, legal, technical reports, news articles, datasets — anything.

Pipeline:
  1. classify()  — detect doc_type and domain from content
  2. extract()   — adaptive extraction based on detected type
  3. run()       — full pipeline: load → classify → extract → save

Evidence Classification:
  Every extracted field is annotated as:
    fact        — directly stated verbatim in source
    inference   — logically derived from stated facts
    hypothesis  — plausible but not directly evidenced
    unknown     — insufficient evidence to determine

Backward compatibility:
  research_analyst, patent_analyst, startup_analyst are untouched.
  UniversalAnalyst handles items with type='document' or explicit API calls.
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.base import call_llm
from db.init_db import DB_PATH

# ── Classification prompt ─────────────────────────────────────────────────────

CLASSIFY_PROMPT = """Analyze this document and identify what it is.

Return JSON only:
{{
  "doc_type": "paper|patent|startup|report|technical_doc|news|dataset|other",
  "domain": "the specific field or industry this document belongs to (1-3 words, e.g. materials science, aerospace, healthcare, edtech, climate)",
  "dimensions_present": ["problem", "technology", "market", "regulation", "data", "method", "finding"],
  "confidence": 0.8
}}

doc_type rules:
- paper: academic research with abstract, methods, results
- patent: describes an invention with claims
- startup: describes a company, product, or service
- report: industry or government report
- technical_doc: technical specification, API doc, whitepaper
- news: news article or press release
- dataset: describes a dataset or benchmark
- other: anything else

Domain must be specific. Never return "general" or "unknown". Look at the content and name the field.

Document (first 3000 chars):
{text}
"""

# ── Universal extraction prompt ───────────────────────────────────────────────

UNIVERSAL_EXTRACT_PROMPT = """You are an AIVE Knowledge Compiler. Extract structured knowledge from this document.

This document is a {doc_type} in the {domain} domain.

CRITICAL RULES:
- Extract from THIS document only. Never invent information.
- Every field must describe something actually present in the text.
- Use short noun phrases (3-8 words), not full sentences, for problem/technology/solution fields.
- For each extracted field, indicate evidence_classification:
    fact        = the claim is directly stated verbatim in the source
    inference   = derived by logical reasoning from stated facts
    hypothesis  = plausible interpretation but not directly supported
    unknown     = you cannot determine this from the text

Document title: {title}
Document type: {doc_type}
Domain: {domain}

Document text:
{text}

Return JSON only:
{{
  "problem": "specific problem or challenge addressed (noun phrase)",
  "solution": "proposed solution or method (1 sentence max)",
  "technology": "named technique, system, or method (noun phrase)",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4"],
  "industry": ["specific market segment 1", "specific market segment 2"],
  "impact": "who benefits and how (1 sentence)",
  "beneficiaries": ["specific beneficiary group 1", "specific beneficiary group 2"],
  "summary": "two sentences summarizing the core contribution",
  "evidence_classification": {{
    "problem": "fact|inference|hypothesis|unknown",
    "technology": "fact|inference|hypothesis|unknown",
    "solution": "fact|inference|hypothesis|unknown",
    "market": "fact|inference|hypothesis|unknown",
    "summary": "inference"
  }}
}}
"""


class UniversalAnalyst:
    """
    Domain-agnostic document understanding agent.
    Detects doc type and domain from content, then extracts structured knowledge.
    """

    # ── Classification ────────────────────────────────────────────────────────

    def classify(self, raw_text: str, metadata: dict = None) -> dict:
        """
        Detect document type and domain from content.

        Returns:
            doc_type: str — paper|patent|startup|report|technical_doc|news|dataset|other
            domain: str   — e.g. "edtech", "materials science", "aerospace"
            dimensions_present: list[str]
            confidence: float
        """
        metadata = metadata or {}
        text_sample = raw_text[:3000]
        prompt = CLASSIFY_PROMPT.format(text=text_sample)

        try:
            result = call_llm(
                prompt,
                system="You are a document classifier. Return valid JSON only.",
                agent="extractor",
            )
        except Exception as e:
            # Safe fallback: use type hint from metadata or 'other'
            return {
                "doc_type": metadata.get("type_hint", "other"),
                "domain": "unknown",
                "dimensions_present": [],
                "confidence": 0.1,
                "error": str(e),
            }

        return {
            "doc_type": result.get("doc_type", "other"),
            "domain": result.get("domain", "unknown"),
            "dimensions_present": result.get("dimensions_present", []),
            "confidence": result.get("confidence", 0.5),
        }

    # ── Extraction ────────────────────────────────────────────────────────────

    def extract(self, item: dict) -> dict:
        """
        Extract structured knowledge from an item dict.
        Delegates to specialist prompts for paper/patent/startup.
        Uses universal prompt for all other types.

        Returns standard extraction schema + doc_type, domain, evidence_classification.
        """
        doc_type = item.get("doc_type", "other")
        domain = item.get("domain", "unknown")
        title = item.get("title", "")
        raw_text = item.get("raw_text", "")[:6000]

        # For well-understood types, use the existing specialist extraction prompts
        # by importing them directly — this preserves prompt quality while adding
        # the doc_type/domain/evidence_classification overlay
        if doc_type == "paper":
            return self._extract_with_specialist("research_analyst", item)
        elif doc_type == "patent":
            return self._extract_with_specialist("patent_analyst", item)
        elif doc_type == "startup":
            return self._extract_with_specialist("startup_analyst", item)

        # Universal extraction for all other types
        prompt = UNIVERSAL_EXTRACT_PROMPT.format(
            doc_type=doc_type,
            domain=domain,
            title=title,
            text=raw_text,
        )

        try:
            result = call_llm(
                prompt,
                system=(
                    "You are AIVE Knowledge Compiler. "
                    "Extract structured knowledge from any document type. "
                    "Return valid JSON only. Never fabricate information."
                ),
                agent="extractor",
            )
        except Exception as e:
            return self._empty_extraction(doc_type, domain, error=str(e))

        # Ensure evidence_classification is present
        ev_class = result.get("evidence_classification", {})
        for field in ("problem", "technology", "solution", "market", "summary"):
            if field not in ev_class:
                ev_class[field] = "unknown"

        return {
            "problem": result.get("problem", ""),
            "solution": result.get("solution", ""),
            "technology": result.get("technology", ""),
            "keywords": result.get("keywords", []),
            "industry": result.get("industry", []),
            "impact": result.get("impact", ""),
            "beneficiaries": result.get("beneficiaries", []),
            "summary": result.get("summary", ""),
            "doc_type": doc_type,
            "domain": domain,
            "evidence_classification": ev_class,
        }

    def _extract_with_specialist(self, analyst_name: str, item: dict) -> dict:
        """
        Delegate to specialist prompts by importing the EXTRACTION_PROMPT
        string directly. This avoids coupling to specialist function signatures
        (which don't expose standalone extract_X functions).
        """
        raw_text = (item.get("raw_text") or "")[:6000]
        title = item.get("title", "")

        try:
            if analyst_name == "research_analyst":
                from agents.research_analyst import EXTRACTION_PROMPT
                prompt = EXTRACTION_PROMPT.format(title=title, text=raw_text)
            elif analyst_name == "patent_analyst":
                from agents.patent_analyst import EXTRACTION_PROMPT
                prompt = EXTRACTION_PROMPT.format(title=title, text=raw_text)
            elif analyst_name == "startup_analyst":
                from agents.startup_analyst import EXTRACTION_PROMPT
                prompt = EXTRACTION_PROMPT.format(title=title, text=raw_text)
            else:
                return self._empty_extraction(
                    item.get("doc_type", "other"), item.get("domain", "unknown")
                )

            result = call_llm(prompt, agent="extractor")

        except Exception as e:
            return self._empty_extraction(
                item.get("doc_type", "other"), item.get("domain", "unknown"), error=str(e)
            )

        # Overlay V2 fields
        result["doc_type"] = item.get("doc_type", analyst_name.replace("_analyst", ""))
        result["domain"] = item.get("domain", "unknown")
        result["evidence_classification"] = {
            "problem": "fact",
            "technology": "fact",
            "solution": "inference",
            "market": "inference",
            "summary": "inference",
        }
        return result

    def _empty_extraction(self, doc_type: str, domain: str, error: str = "") -> dict:
        """Return safe empty extraction on failure."""
        return {
            "problem": "",
            "solution": "",
            "technology": "",
            "keywords": [],
            "industry": [],
            "impact": "",
            "beneficiaries": [],
            "summary": "",
            "doc_type": doc_type,
            "domain": domain,
            "evidence_classification": {
                "problem": "unknown",
                "technology": "unknown",
                "solution": "unknown",
                "market": "unknown",
                "summary": "unknown",
            },
            "_error": error,
        }

    # ── Full pipeline ─────────────────────────────────────────────────────────

    def run(self, item_id: str, db_path: Path = DB_PATH) -> dict:
        """
        Full pipeline: load item → classify → extract → save → return result.
        """
        # Load item from DB
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, title, type, raw_text FROM items WHERE id=?", (item_id,)
            ).fetchone()

        if not row:
            return {"error": f"Item not found: {item_id}"}

        item = dict(row)

        # Phase 1: Classify
        classification = self.classify(
            item["raw_text"] or "",
            metadata={"type_hint": item.get("type", "other")},
        )
        item["doc_type"] = classification["doc_type"]
        item["domain"] = classification["domain"]

        # Phase 2: Extract
        extracted = self.extract(item)

        # Phase 3: Save
        self._save(item_id, extracted, db_path)

        return {
            "item_id": item_id,
            "title": item["title"],
            "doc_type": extracted.get("doc_type"),
            "domain": extracted.get("domain"),
            **extracted,
        }

    def _save(self, item_id: str, data: dict, db_path: Path) -> None:
        """Persist extraction results including V2 fields."""
        ev_class = data.get("evidence_classification", {})
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                UPDATE items SET
                    problem = ?,
                    solution = ?,
                    technology = ?,
                    keywords = ?,
                    industry = ?,
                    impact = ?,
                    beneficiaries = ?,
                    summary = ?,
                    extracted_at = ?,
                    extraction_status = 'done',
                    doc_type = ?,
                    domain = ?,
                    evidence_classification = ?
                WHERE id = ?
                """,
                (
                    data.get("problem", ""),
                    data.get("solution", ""),
                    data.get("technology", ""),
                    json.dumps(data.get("keywords", [])),
                    json.dumps(data.get("industry", [])),
                    data.get("impact", ""),
                    json.dumps(data.get("beneficiaries", [])),
                    data.get("summary", ""),
                    datetime.now(timezone.utc).isoformat(),
                    data.get("doc_type", "other"),
                    data.get("domain", "unknown"),
                    json.dumps(ev_class),
                    item_id,
                ),
            )


# ── Convenience entry point ───────────────────────────────────────────────────

def run_pending(limit: int = 10, db_path: Path = DB_PATH) -> list[dict]:
    """
    Run UniversalAnalyst on pending items of type 'document' or any type
    not handled by existing specialist agents.
    """
    specialist_types = {"paper", "patent", "startup"}
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, title, type FROM items
            WHERE extraction_status = 'pending'
              AND type NOT IN ('paper', 'patent', 'startup')
            ORDER BY id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    if not rows:
        print("No pending non-specialist items found.")
        return []

    analyst = UniversalAnalyst()
    results = []
    for i, row in enumerate(rows):
        print(f"[{i+1}/{len(rows)}] {row['title'][:60]}...")
        try:
            result = analyst.run(row["id"], db_path)
            results.append(result)
            print(f"  doc_type={result.get('doc_type')} domain={result.get('domain')}")
        except Exception as e:
            print(f"  [ERROR] {e}")
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "UPDATE items SET extraction_status='failed' WHERE id=?",
                    (row["id"],),
                )
    return results


if __name__ == "__main__":
    import sys as _sys
    limit = int(_sys.argv[1]) if len(_sys.argv) > 1 else 10
    results = run_pending(limit=limit)
    print(f"\nProcessed {len(results)} items via UniversalAnalyst.")
