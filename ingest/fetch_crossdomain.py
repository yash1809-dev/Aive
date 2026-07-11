"""
ingest/fetch_crossdomain.py
============================
Fetches papers from arXiv domains COMPLETELY DIFFERENT from Edtech.

The core thesis of AIVE: "Valuable opportunities exist at the intersection
of disconnected domains." A graph that only contains Edtech × Edtech
intersections will only discover Edtech × Edtech opportunities —
which are already well-covered by Turnitin, Gradescope, Khanmigo, etc.

True discovery requires orthogonal domains where the Critic cannot say
"Turnitin already does this."

Target domains (NONE of these overlap with existing Edtech corpus):
  1. Healthcare AI / Clinical Decision Support
  2. Climate Science / Carbon Capture / Energy Transition
  3. Manufacturing / Industrial AI / Process Optimization
  4. Drug Discovery / Computational Biology
  5. Materials Science / Advanced Materials
  6. Legal Tech / Regulatory Compliance AI
  7. Agricultural Tech / Food Systems AI

Run:
    python ingest/fetch_crossdomain.py

Next steps are printed at the end.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ingest.fetch_papers import fetch_and_save

# Each domain is intentionally chosen to be orthogonal to Edtech.
# The queries are specific enough to avoid generic "AI" papers.
CROSS_DOMAINS = [
    {
        "name": "Clinical Decision Support AI",
        "query": 'all:"clinical decision support" AND (all:"machine learning" OR all:"large language model")',
        "count": 15,
    },
    {
        "name": "AI Drug Discovery",
        "query": 'all:"drug discovery" AND (all:"deep learning" OR all:"generative model" OR all:"molecular")',
        "count": 15,
    },
    {
        "name": "Climate AI / Carbon Capture",
        "query": 'all:"carbon capture" OR all:"climate modeling" OR all:"energy transition" AND all:"machine learning"',
        "count": 12,
    },
    {
        "name": "Manufacturing Process AI",
        "query": 'all:"predictive maintenance" OR all:"process optimization" OR all:"industrial AI" AND all:"machine learning"',
        "count": 12,
    },
    {
        "name": "Materials Science AI",
        "query": 'all:"materials discovery" OR all:"battery materials" OR all:"alloy design" AND all:"machine learning"',
        "count": 10,
    },
    {
        "name": "Legal AI / Contract Analysis",
        "query": 'all:"legal AI" OR all:"contract analysis" OR all:"regulatory compliance" AND all:"large language model"',
        "count": 10,
    },
    {
        "name": "Agricultural AI / Precision Farming",
        "query": 'all:"precision agriculture" OR all:"crop yield" OR all:"food security" AND all:"machine learning"',
        "count": 8,
    },
    {
        "name": "Biomedical NLP",
        "query": 'all:"biomedical NLP" OR all:"clinical NLP" OR all:"electronic health records" AND all:"large language model"',
        "count": 10,
    },
]


def main():
    total_fetched = 0
    total_saved = 0

    print("=" * 60)
    print("AIVE Cross-Domain Ingest")
    print("Fetching papers from non-Edtech domains...")
    print("=" * 60)
    print()

    for domain in CROSS_DOMAINS:
        print(f"  [{domain['name']}]")
        print(f"    query: {domain['query'][:80]}...")
        try:
            result = fetch_and_save(count=domain["count"], query=domain["query"])
            print(f"    fetched={result['fetched']}  new={result['saved']}")
            total_fetched += result["fetched"]
            total_saved += result["saved"]
        except Exception as exc:
            print(f"    [ERROR] {exc}")
        print()

    print("=" * 60)
    print(f"Total fetched: {total_fetched}")
    print(f"Total new:     {total_saved}")
    print()
    print("Next steps:")
    print("  1. python3 agents/research_analyst.py 999   (extract all pending)")
    print("  2. python3 agents/concept_extractor.py      (re-extract concepts, clear cache first)")
    print("  3. python3 agents/graph_builder.py          (rebuild graph)")
    print("  4. python3 agents/opportunity_finder.py 40  (generate cross-domain candidates)")
    print("  5. python3 agents/critic.py                 (apply critic filter)")


if __name__ == "__main__":
    main()
