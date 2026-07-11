"""
ingest/pack_ingest.py
=====================
Pack-driven ingestion. Reads all active Intelligence Packs
and fetches their arXiv queries into the database.

Usage:
    python ingest/pack_ingest.py               # All active packs
    python ingest/pack_ingest.py --pack healthcare  # Single pack
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ingest.fetch_papers import fetch_and_save
from packs import ACTIVE_PACKS


def ingest_pack(pack) -> dict:
    total_fetched, total_saved = 0, 0
    print(f"\n[{pack.domain_name}] Starting ingestion...")

    for q in pack.arxiv_queries:
        print(f"  Query: {q['name']} ({q['count']} papers)")
        try:
            result = fetch_and_save(count=q["count"], query=q["query"])
            print(f"    fetched={result['fetched']}  new={result['saved']}")
            total_fetched += result["fetched"]
            total_saved += result["saved"]
        except Exception as e:
            print(f"    [ERROR] {e}")

    return {"pack": pack.domain_name, "fetched": total_fetched, "saved": total_saved}


def main():
    parser = argparse.ArgumentParser(description="AIVE Pack-Driven Ingestion")
    parser.add_argument("--pack", type=str, default=None, help="Pack domain name to run (partial match)")
    args = parser.parse_args()

    packs_to_run = ACTIVE_PACKS
    if args.pack:
        packs_to_run = [p for p in ACTIVE_PACKS if args.pack.lower() in p.domain_name.lower()]
        if not packs_to_run:
            print(f"No pack found matching '{args.pack}'. Available: {[p.domain_name for p in ACTIVE_PACKS]}")
            return

    print("=" * 60)
    print(f"AIVE Pack Ingest — {len(packs_to_run)} pack(s) active")
    print("=" * 60)

    grand_total_fetched = 0
    grand_total_saved = 0

    for pack in packs_to_run:
        result = ingest_pack(pack)
        grand_total_fetched += result["fetched"]
        grand_total_saved += result["saved"]

    print("\n" + "=" * 60)
    print(f"Total fetched: {grand_total_fetched}")
    print(f"Total new:     {grand_total_saved}")
    print("\nNext steps:")
    print("  python3 agents/research_analyst.py 999  # Extract all pending")
    print("  python3 agents/graph_builder.py          # Rebuild graph")
    print("  python3 run.py daily                     # Full pipeline")


if __name__ == "__main__":
    main()
