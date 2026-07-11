# Requirements Document

## Introduction

AIVE is a functional knowledge discovery pipeline that is not yet domain-agnostic, not yet capable of accepting arbitrary document types, and not yet producing outputs of professional research quality. This spec defines the requirements to evolve AIVE into a genuine Cognitive Discovery Operating System — one that accepts any information input, constructs internal structured understanding, reasons over evidence, discovers insights, answers grounded questions, and generates publication-quality reports and visualizations without hardcoded domain logic.

Every requirement in this document is additive. Nothing in the existing system is removed or rewritten. New capabilities are layered on top of the working architecture.

## Requirements

### REQ-1: Universal Document Understanding

- [ ] 1. AIVE shall be capable of extracting structured knowledge from any document type (paper, patent, startup, technical report, news article, dataset description, URL content) using a single Universal Analyst agent
- [ ] 2. The Universal Analyst shall first classify the document type and domain from the document content itself — never from a preconfigured domain assumption
- [ ] 3. The Universal Analyst shall apply appropriate extraction strategies per detected document type, delegating to existing specialist analysts for paper/patent/startup types
- [ ] 4. Every extracted knowledge field shall be annotated with an evidence classification: fact (directly stated), inference (logically derived), hypothesis (plausible but unverified), or unknown (insufficient evidence)
- [ ] 5. Every extracted knowledge object shall preserve provenance: source URL, ingestion timestamp, extraction model used, and confidence level
- [ ] 6. Existing specialist agents (research_analyst, patent_analyst, startup_analyst) shall remain unchanged and continue to function
- [ ] 7. The pipeline shall support URL ingestion: given only a URL, AIVE shall fetch content, extract text, and process through the understanding pipeline

### REQ-2: Domain-Agnostic Behaviour

- [ ] 8. The system shall function correctly on documents from any domain (materials science, aerospace, finance, climate, etc.) without configuration changes
- [ ] 9. The knowledge graph builder shall normalize semantically equivalent labels using runtime similarity matching, not only the hardcoded MERGE_MAP
- [ ] 10. The hardcoded MERGE_MAP shall continue to function as a fast-path override — it shall not be removed
- [ ] 11. The opportunity finder shall operate on any graph structure regardless of domain, relying only on universal node types (Problem, Technology, Buyer, EconomicSignal) not domain-specific labels
- [ ] 12. Hardcoded EdTech-specific scoring bonuses shall be generalized to work with any domain signal pattern

### REQ-3: Evidence-Based Reasoning

- [ ] 13. Every system output (opportunity, discovery, report section, Copilot response) shall distinguish between: facts, inferences, hypotheses, assumptions, and unknowns
- [ ] 14. Every opportunity shall carry a traceable reasoning chain: source items → graph nodes → edge path → conclusion
- [ ] 15. The reasoning chain shall be stored in the database and accessible via API
- [ ] 16. The system shall detect contradictions: cases where two evidence sources make conflicting claims about the same concept
- [ ] 17. Contradictions shall be stored as first-class objects and surfaced in reports and via API
- [ ] 18. When knowledge is insufficient to answer a question, the system shall explicitly state the limitation rather than generating a plausible-sounding answer

### REQ-4: Research-Grade Reports

- [ ] 19. Generated reports shall include: Executive Summary, Objectives, Methodology, Evidence, Knowledge Graph Summary, Reasoning Chain, Key Findings, Cross-Document Insights, Contradictions, Research Gaps, Novel Opportunities, Risk Analysis, Validation Strategy, Confidence Analysis, Future Work, References
- [ ] 20. Every claim in a generated report shall be traceable to at least one source document via inline citation
- [ ] 21. Reports shall not contain fabricated citations or references to non-existent sources
- [ ] 22. The existing simple report generation endpoint and report_writer.py shall remain unchanged
- [ ] 23. A new deep report generation endpoint shall be added that produces the full structured report

### REQ-5: Professional Visualizations

- [ ] 24. The system shall generate a pipeline kill funnel visualization showing: ingested, extracted, graph nodes, candidates, survived, rejected counts
- [ ] 25. The system shall generate a node type distribution visualization
- [ ] 26. The system shall generate a per-opportunity score radar chart (Novelty, Timing, Market, Feasibility, Confidence)
- [ ] 27. Visualization data shall be served via dedicated API endpoints
- [ ] 28. Visualizations shall be rendered client-side using the existing Chart.js integration
- [ ] 29. No external visualization services or new frontend dependencies shall be introduced

### REQ-6: Grounded Question Answering

- [ ] 30. The Copilot shall classify question type (factual, graph traversal, comparative, discovery, gap) and route to the appropriate answering strategy
- [ ] 31. Every Copilot response shall include references to the specific knowledge objects (item IDs) that support the answer
- [ ] 32. Every Copilot response shall include a confidence level: high, medium, low, or unknown
- [ ] 33. The existing /api/copilot endpoint shall remain backward compatible
- [ ] 34. The Copilot response format shall be extended with optional evidence_refs and confidence fields that the frontend displays when present

### REQ-7: Expanded Discovery Types

- [ ] 35. Beyond commercial opportunities, the system shall detect and store: Research Gaps (problems with no technology connections), Contradictions (conflicting evidence), Method Transfers (techniques applicable across domain boundaries)
- [ ] 36. Discoveries shall be stored as typed objects in a new discoveries table
- [ ] 37. Discoveries shall be accessible via API and surfaced in the frontend canvas
- [ ] 38. Research gap detection shall be based on graph topology analysis — no LLM required for gap identification

### REQ-8: Backend Integrity

- [ ] 39. All new API endpoints shall follow the existing Flask pattern: try/except error handling, jsonify responses, conn.close() in finally block
- [ ] 40. All database changes shall be additive only — no existing tables, columns, or data shall be removed or modified
- [ ] 41. All new agents shall call LLMs through agents/base.py call_llm() — never directly
- [ ] 42. All new DB access shall use the DB_PATH from db/init_db.py — never a hardcoded path
- [ ] 43. All new engines shall inherit from engines/base_engine.BaseEngine

### REQ-9: Frontend Integrity

- [ ] 44. All existing frontend functionality shall remain intact: canvas drag-drop nodes, copilot chat, pipeline runner, workspace time machine, ingestion modal, arXiv sync, report generation, system health
- [ ] 45. New frontend components shall use only existing CSS design tokens and the existing Chart.js library
- [ ] 46. No new JavaScript dependencies shall be added

## Glossary

- **Universal Analyst**: A new agent capable of extracting structured knowledge from any document type without domain-specific hardcoding
- **Evidence Classification**: A label applied to each extracted field indicating whether it is a fact, inference, hypothesis, or unknown
- **Discovery**: A typed output object from AIVE — one of: commercial opportunity, research gap, contradiction, method transfer
- **Research Gap**: A structural gap in the knowledge graph where a problem domain lacks viable technology connections or a technology lacks identified buyers
- **Contradiction**: A case where two reliable evidence sources make conflicting claims about the same concept
- **Method Transfer**: A technique proven in one domain that is applicable to an analogous unsolved problem in another domain
- **Reasoning Chain**: A traceable path from source documents through graph nodes and edges to a conclusion
- **Deep Report**: A publication-quality research report with all 15 required sections, inline citations, and evidence traceability
- **MERGE_MAP**: The existing hardcoded dictionary in knowledge_graph.py that normalizes variant label phrasings to canonical forms
