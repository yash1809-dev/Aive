"""
ingest/fetch_economic_signals.py
=================================
Economic Intelligence Layer — the fourth ingestion source.

Covers: procurement signals, competitor intelligence, regulation,
resource constraints, and economic timing signals.

Run: python ingest/fetch_economic_signals.py
"""
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.init_db import DB_PATH

ECONOMIC_SIGNALS = [
    # ── Budget & Procurement ──────────────────────────────────────────────────
    {
        "title": "US K-12 EdTech Procurement: ESSER Cliff 2024",
        "problem": "School budget cuts",
        "solution": "Budget-neutral EdTech with proven ROI",
        "technology": "Budget-neutral EdTech",
        "keywords": json.dumps(["ESSER", "school budget", "procurement", "K-12 funding"]),
        "industry": json.dumps(["K-12 School Districts", "EdTech Vendors"]),
        "impact": "US K-12 edtech spending dropped 30% in 2024 as $190B ESSER funds expired",
        "beneficiaries": json.dumps(["Budget-conscious school districts", "Low-cost EdTech vendors"]),
        "summary": "ESSER cliff created a procurement crisis. Schools cut expensive AI tools. Products must prove ROI under $5/student/year to survive.",
        "source": "EdSurge 2024, RAND Corporation",
    },
    {
        "title": "School Procurement: 18-Month Sales Cycle, 7 Stakeholders",
        "problem": "EdTech adoption friction",
        "solution": "Bottom-up teacher adoption triggering district purchase",
        "technology": "Freemium teacher tools",
        "keywords": json.dumps(["school procurement", "sales cycle", "district purchasing", "teacher adoption"]),
        "industry": json.dumps(["EdTech Sales Teams", "K-12 School Districts", "IT Departments"]),
        "impact": "Average K-12 EdTech sales cycle is 18 months with 7 stakeholder touchpoints",
        "beneficiaries": json.dumps(["Product-led EdTech vendors", "Freemium EdTech tools"]),
        "summary": "EdSurge: average K-12 sales cycle is 18 months. Only 2% of piloted tools reach district-wide adoption. Bottom-up teacher adoption (like Google Classroom) is the only proven path.",
        "source": "EdSurge Procurement Report 2024",
    },
    {
        "title": "EdTech Funding Collapse: 73% Drop Since 2021 Peak",
        "problem": "EdTech funding drought",
        "solution": "Revenue-generating EdTech with demonstrated ROI",
        "technology": "B2B SaaS EdTech",
        "keywords": json.dumps(["edtech funding", "venture capital", "EdTech market"]),
        "industry": json.dumps(["EdTech Startups", "Venture Capital"]),
        "impact": "Global EdTech funding fell from $20B (2021) to $5.4B (2023)",
        "beneficiaries": json.dumps(["Profitable EdTech companies", "Bootstrapped EdTech tools"]),
        "summary": "VCs now require 12-month payback and clear district contracts. Consumer EdTech is essentially unfundable.",
        "source": "HolonIQ EdTech Report 2024",
    },

    # ── Teacher Workforce ─────────────────────────────────────────────────────
    {
        "title": "US Teacher Shortage: 55,000 Unfilled Positions 2024",
        "problem": "Teacher shortage",
        "solution": "AI tools that multiply teacher effectiveness",
        "technology": "AI teacher assistant",
        "keywords": json.dumps(["teacher shortage", "workforce crisis", "rural schools", "special education"]),
        "industry": json.dumps(["Rural K-12 Districts", "Special Education Programs", "State Departments of Education"]),
        "impact": "55,000+ unfilled teacher positions in 2024, special education most acute",
        "beneficiaries": json.dumps(["Understaffed school districts", "Special education directors"]),
        "summary": "NCES: 55,000+ unfilled teaching positions in 2024. Districts actively purchasing AI tools to reduce per-teacher workload. Direct procurement trigger.",
        "source": "NCES 2024 Teacher Vacancy Survey",
    },
    {
        "title": "Special Education IEP Crisis: 7.5M Students",
        "problem": "IEP generation burden",
        "solution": "Automated IEP drafting with human review",
        "technology": "NLP IEP generation",
        "keywords": json.dumps(["IEP", "special education", "IDEA", "special ed shortage"]),
        "industry": json.dumps(["Special Education Directors", "K-12 School Districts"]),
        "impact": "7.5M US students with IEPs, each taking 8-12 hours to write manually",
        "beneficiaries": json.dumps(["Special education administrators", "School psychologists"]),
        "summary": "Automating IEP drafting could save 60M teacher-hours annually. Clear procurement via district special ed budgets.",
        "source": "NCES 2024 Special Education Data",
    },

    # ── Regulation ────────────────────────────────────────────────────────────
    {
        "title": "FERPA Enforcement: PowerSchool Breach Exposed 62M Records",
        "problem": "Student data privacy breach",
        "solution": "On-premise AI with no external data transmission",
        "technology": "On-device AI inference",
        "keywords": json.dumps(["FERPA", "student data breach", "data privacy", "cloud AI risk"]),
        "industry": json.dumps(["K-12 School Districts", "University IT Departments"]),
        "impact": "PowerSchool breach (2024) exposed 62M student records; DOE issued new FERPA guidance",
        "beneficiaries": json.dumps(["Privacy-first EdTech vendors", "On-premise AI providers"]),
        "summary": "Creates immediate procurement preference for on-premise or data-isolated AI solutions. Cloud-only tools face growing district resistance.",
        "source": "PowerSchool breach disclosure 2025, DOE FERPA guidance",
    },
    {
        "title": "EU AI Act: Education AI Classified High-Risk by August 2026",
        "problem": "AI regulation compliance",
        "solution": "GDPR-compliant AI with audit trails",
        "technology": "Compliant AI systems",
        "keywords": json.dumps(["EU AI Act", "GDPR", "high-risk AI", "EdTech regulation"]),
        "industry": json.dumps(["European EdTech Vendors", "Universities", "K-12 Schools"]),
        "impact": "EU AI Act classifies education AI as high-risk; conformity assessments required by August 2026",
        "beneficiaries": json.dumps(["Privacy-compliant EdTech vendors", "EU school districts"]),
        "summary": "EU AI Act Article 6: all AI in education requires conformity assessment, audit trail, and human oversight by August 2026. Creates compliance purchasing urgency across EU.",
        "source": "EU AI Act Official Journal 2024",
    },
    {
        "title": "CIPA + COPPA: 6-9 Month IT Approval Barrier for K-12",
        "problem": "School IT compliance burden",
        "solution": "CIPA-compliant AI with US data residency",
        "technology": "Compliant cloud infrastructure",
        "keywords": json.dumps(["CIPA", "COPPA", "student data", "IT compliance", "school firewall"]),
        "industry": json.dumps(["K-12 IT Departments", "School District Administrators"]),
        "impact": "CIPA vetting averages 6-9 months; combined with COPPA creates 12-18 month procurement barrier",
        "beneficiaries": json.dumps(["Compliant EdTech vendors", "District IT directors"]),
        "summary": "CIPA + COPPA + state data residency laws = 12-18 month procurement barrier for any new EdTech tool. The single biggest adoption constraint that founders underestimate.",
        "source": "FCC CIPA guidelines, COSN IT Survey 2024",
    },

    # ── Academic Integrity ────────────────────────────────────────────────────
    {
        "title": "ChatGPT Academic Integrity Crisis: 89% of Universities Updated Policies",
        "problem": "Academic integrity under LLM pressure",
        "solution": "AI-native assessment that can't be gamed by LLMs",
        "technology": "LLM-resistant assessment",
        "keywords": json.dumps(["academic integrity", "AI detection", "assessment reform", "Turnitin"]),
        "industry": json.dumps(["Universities", "K-12 High Schools", "Exam Boards"]),
        "impact": "89% of US universities updated academic integrity policies in 2024",
        "beneficiaries": json.dumps(["AI detection vendors", "Oral exam platforms", "Process-based assessment"]),
        "summary": "QS survey: 89% of universities revised policies in 2024. Turnitin flagged 6M+ AI submissions. Procurement demand for LLM-resistant tools is urgent.",
        "source": "QS Intelligence Unit 2024, Turnitin AI Impact Report 2024",
    },

    # ── Technology Cost Signals ───────────────────────────────────────────────
    {
        "title": "LLM Inference Cost: 99% Drop in 18 Months (2023-2025)",
        "problem": "AI deployment cost barrier",
        "solution": "Affordable on-device AI inference",
        "technology": "Quantized LLM inference",
        "keywords": json.dumps(["inference cost", "llama.cpp", "quantization", "on-device AI"]),
        "industry": json.dumps(["EdTech Vendors", "Developing Market Schools", "Offline Learning Markets"]),
        "impact": "GPT-4 equivalent inference cost fell from $0.06/1K tokens to $0.0006 — 100x reduction",
        "beneficiaries": json.dumps(["Low-cost EdTech vendors", "Offline AI builders", "Emerging market schools"]),
        "summary": "LLM costs dropped 99% in 18 months. llama.cpp runs 7B models on laptops. Offline AI tutoring is now economically viable for the first time.",
        "source": "Epoch AI Inference Cost Tracking 2025",
    },
    {
        "title": "EdTech MVP Build Cost: $150K-$500K in 3-6 Months",
        "problem": "High EdTech development cost",
        "solution": "LLM API-based EdTech with minimal custom ML",
        "technology": "LLM API integration",
        "keywords": json.dumps(["EdTech cost", "MVP cost", "startup resource", "LLM API"]),
        "industry": json.dumps(["EdTech Startups", "Angel Investors", "Accelerators"]),
        "impact": "LLM APIs reduce EdTech MVP cost from $1M+ to $150K-$500K",
        "beneficiaries": json.dumps(["Early-stage EdTech founders", "Bootstrapped startups"]),
        "summary": "Using GPT-4o or Llama 3 APIs, a grading/tutoring/assessment MVP can be built in 3-6 months for $150K-$500K. Seed-stage viable. Fundamentally different from 2019.",
        "source": "YC EdTech cohort analysis 2024, a16z EdTech report",
    },

    # ── Competitor Intelligence ───────────────────────────────────────────────
    {
        "title": "Gradescope (Turnitin): AI Grading Market Leader, Weak in K-12",
        "problem": "Manual grading is slow and inconsistent",
        "solution": "AI-assisted grading with rubric scoring",
        "technology": "AI grading rubric automation",
        "keywords": json.dumps(["Gradescope", "Turnitin", "AI grading", "rubric", "assignment feedback"]),
        "industry": json.dumps(["Universities", "K-12 High Schools"]),
        "impact": "Gradescope (Turnitin) serves 500+ universities at $3-8/student/year",
        "beneficiaries": json.dumps(["University professors", "Teaching assistants"]),
        "summary": "Market leader in AI grading. Weakness: expensive for K-12, poor K-12 LMS integration, weak formative assessment. Primary competitor any grading tool must beat.",
        "source": "Turnitin acquisition 2021, Gradescope pricing",
    },
    {
        "title": "MagicSchool AI: 3M Teachers, $10M ARR, Bottom-Up Growth",
        "problem": "Teacher administrative time waste",
        "solution": "AI copilot for lesson planning and differentiation",
        "technology": "GPT-4 teacher workflow automation",
        "keywords": json.dumps(["MagicSchool", "teacher AI", "lesson planning", "AI copilot"]),
        "industry": json.dumps(["K-12 Teachers", "School Districts"]),
        "impact": "MagicSchool reached 3M+ teachers in 18 months via freemium",
        "beneficiaries": json.dumps(["K-12 teachers", "Instructional coaches"]),
        "summary": "Fastest-growing teacher AI tool. Weakness: automates tasks but doesn't close feedback loop with student data or district reporting. New tools must differentiate from MagicSchool.",
        "source": "MagicSchool AI press releases 2024, Crunchbase",
    },
    {
        "title": "Turnitin: 16,000 Institutions, Dominates Academic Integrity",
        "problem": "AI-written academic work detection",
        "solution": "ML-based AI writing detection",
        "technology": "AI content detection classifier",
        "keywords": json.dumps(["Turnitin", "AI detection", "plagiarism", "academic integrity"]),
        "industry": json.dumps(["Universities", "K-12 High Schools", "Exam Boards"]),
        "impact": "Turnitin: 16,000+ institutional clients, 6M+ AI submissions flagged in 2024",
        "beneficiaries": json.dumps(["University administrators", "Academic integrity officers"]),
        "summary": "Turnitin dominates with deep LMS integrations (Canvas, Blackboard, Moodle). New tools must integrate with Turnitin or offer capabilities it explicitly cannot: oral exams, real-time process monitoring.",
        "source": "Turnitin Annual Report 2024",
    },

    # ── India / Global South ──────────────────────────────────────────────────
    {
        "title": "India NEP 2020: $6B EdTech Opportunity, 250M DIKSHA Users",
        "problem": "Education access gap in India",
        "solution": "Multilingual AI tutoring at scale",
        "technology": "Multilingual LLM tutoring",
        "keywords": json.dumps(["NEP 2020", "India education", "DIKSHA", "multilingual"]),
        "industry": json.dumps(["Indian State Governments", "NCERT", "Private Tutoring Centers"]),
        "impact": "NEP 2020 mandates mother-tongue instruction; DIKSHA has 250M registered users",
        "beneficiaries": json.dumps(["Indian EdTech vendors", "State education ministries"]),
        "summary": "India NEP mandates mother-tongue instruction creating $6B multilingual AI tutoring opportunity. DIKSHA is the government procurement gateway for compliant vendors.",
        "source": "NEP 2020 Implementation Report, HolonIQ India 2024",
    },
]


def ingest_signals(signals: list[dict] = ECONOMIC_SIGNALS) -> int:
    """Insert economic signals into items table. Skips existing titles."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        inserted = 0
        for signal in signals:
            existing = conn.execute(
                "SELECT id FROM items WHERE title=? AND type='economic_signal'",
                (signal["title"],)
            ).fetchone()
            if existing:
                continue

            item_id = f"econ_{uuid.uuid4().hex[:8]}"
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                INSERT INTO items (
                    id, title, type, source_url,
                    problem, solution, technology, keywords,
                    industry, impact, beneficiaries, summary,
                    extracted_at, extraction_status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                item_id, signal["title"], "economic_signal",
                signal.get("source", ""),
                signal["problem"], signal["solution"], signal["technology"],
                signal["keywords"], signal["industry"],
                signal["impact"], signal["beneficiaries"], signal["summary"],
                now, "done",
            ))
            inserted += 1
            print(f"  Ingested: {signal['title'][:70]}")
    return inserted


if __name__ == "__main__":
    print("Ingesting economic intelligence signals...")
    n = ingest_signals()
    print(f"\nInserted {n} new signals (skipped existing)")
    print("Run: python rebuild_graph.py")
