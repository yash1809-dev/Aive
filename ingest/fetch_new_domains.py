"""
ingest/fetch_new_domains.py
============================
Fetches papers from arXiv in domains that are currently under-represented
in the AIVE knowledge graph — specifically domains with real problems but
sparse startup coverage, which is where genuinely novel opportunities emerge.

Target domains:
  1. Special education / IEP generation / learning disabilities
  2. Rural and offline education access
  3. Vocational / workforce training with AI
  4. Adult literacy and continuing education
  5. Healthcare education (medical training, clinical simulation)

Run:
    python ingest/fetch_new_domains.py

This will fetch ~10 papers per domain (50 total) and save them to the DB
with extraction_status='pending'. Run agents/research_analyst.py after.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ingest.fetch_papers import fetch_and_save

DOMAIN_QUERIES = [
    {
        "name": "Special Education / IEP",
        "query": 'all:"special education" AND (all:AI OR all:"machine learning" OR all:"large language model")',
        "count": 10,
    },
    {
        "name": "Rural / Offline Education",
        "query": 'all:"rural education" OR all:"offline learning" OR all:"low resource education" AND all:AI',
        "count": 10,
    },
    {
        "name": "Vocational / Workforce AI",
        "query": 'all:"vocational training" OR all:"workforce development" OR all:"skills training" AND all:AI',
        "count": 10,
    },
    {
        "name": "Adult Literacy",
        "query": 'all:"adult literacy" OR all:"adult learning" OR all:"continuing education" AND all:AI',
        "count": 8,
    },
    {
        "name": "Healthcare Education / Clinical Training",
        "query": 'all:"medical education" OR all:"clinical simulation" OR all:"nursing education" AND all:AI',
        "count": 10,
    },
    {
        "name": "Language Learning / ELL",
        "query": 'all:"language learning" OR all:"second language" OR all:"English language learner" AND all:AI',
        "count": 8,
    },
]


def main():
    total_fetched = 0
    total_saved = 0

    print("Fetching papers from under-represented domains...\n")
    for domain in DOMAIN_QUERIES:
        print(f"  [{domain['name']}] query: {domain['query'][:80]}...")
        try:
            result = fetch_and_save(count=domain["count"], query=domain["query"])
            print(f"    Fetched: {result['fetched']}  Saved (new): {result['saved']}")
            total_fetched += result["fetched"]
            total_saved += result["saved"]
        except Exception as exc:
            print(f"    [ERROR] {exc}")

    print(f"\nTotal fetched: {total_fetched}")
    print(f"Total new:     {total_saved}")
    print(f"\nNext steps:")
    print(f"  1. python agents/research_analyst.py --all   (extract new papers)")
    print(f"  2. del data\\concept_cache.json               (force full re-extraction)")
    print(f"  3. python agents/graph_builder.py            (rebuild graph with new domains)")
    print(f"  4. python run_batch.py --count 100           (generate new opportunities)")


if __name__ == "__main__":
    main()
