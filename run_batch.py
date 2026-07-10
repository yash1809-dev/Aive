"""
run_batch.py — Full AIVE batch pipeline
Generates 100 opportunities, runs the critic, ranks survivors,
and produces a summary report.

Usage:
    python run_batch.py              # 100 opportunities (default)
    python run_batch.py --count 50   # custom count
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--skip-generate", action="store_true",
                        help="Skip generation and run critic on existing opportunities")
    parser.add_argument("--skip-critic", action="store_true",
                        help="Skip critic and just rank existing survived opportunities")
    args = parser.parse_args()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    print(f"\n{'='*60}")
    print(f"AIVE Batch Pipeline — {timestamp}")
    print(f"Target: {args.count} opportunities")
    print(f"{'='*60}\n")

    # ── Step 1: Generate ──────────────────────────────────────────────────────
    if not args.skip_generate:
        print("STEP 1 — Generating opportunities...")
        from agents.opportunity_finder import run as generate
        opportunities = generate(count=args.count)
        print(f"  Generated: {len(opportunities)}")
    else:
        print("STEP 1 — Skipped (using existing opportunities)")

    # ── Step 2: Critic ────────────────────────────────────────────────────────
    if not args.skip_critic:
        print("\nSTEP 2 — Running Critic...")
        from agents.critic import run as criticize
        critic_stats = criticize()
        total = critic_stats.get("total", 0)
        survived = critic_stats.get("survived", 0)
        rejected = critic_stats.get("rejected", 0)
        kill_rate = critic_stats.get("kill_rate", 0)
        print(f"  Total:    {total}")
        print(f"  Survived: {survived}")
        print(f"  Rejected: {rejected}")
        print(f"  Kill rate: {kill_rate:.0f}%")
    else:
        print("\nSTEP 2 — Skipped")

    # ── Step 3: Rank survivors ────────────────────────────────────────────────
    print("\nSTEP 3 — Ranking survivors...")
    import sqlite3
    with sqlite3.connect(ROOT / "data" / "aive.db") as conn:
        conn.row_factory = sqlite3.Row
        survivors = conn.execute("""
            SELECT id, title, problem, technology, market, reasoning,
                   novelty_score, timing_score, market_score, feasibility,
                   confidence_score, critic_verdict, critic_notes, created_at
            FROM opportunities
            WHERE critic_verdict = 'survived'
            ORDER BY (novelty_score + timing_score + market_score + feasibility + confidence_score) DESC
        """).fetchall()

    survivors = [dict(r) for r in survivors]

    if not survivors:
        print("  No survivors. Consider loosening critic thresholds or improving extraction.")
    else:
        print(f"  {len(survivors)} survivors ranked by composite score:\n")
        for i, s in enumerate(survivors[:10], 1):
            composite = (
                s.get("novelty_score", 0) +
                s.get("timing_score", 0) +
                s.get("market_score", 0) +
                s.get("feasibility", 0) +
                s.get("confidence_score", 0)
            )
            print(f"  #{i:2d}  [{composite:3.0f}] {s['title'][:65]}")

    # ── Step 4: Save ranked report ────────────────────────────────────────────
    report = {
        "timestamp": timestamp,
        "total_generated": args.count,
        "total_survived": len(survivors),
        "survivors": survivors,
    }
    out = ROOT / "data" / "exports" / f"batch_report_{timestamp}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport saved: {out.name}")

    # ── Step 5: Top 5 summary ─────────────────────────────────────────────────
    if survivors:
        print(f"\n{'='*60}")
        print("TOP 5 OPPORTUNITIES")
        print(f"{'='*60}")
        for opp in survivors[:5]:
            composite = sum([
                opp.get("novelty_score", 0), opp.get("timing_score", 0),
                opp.get("market_score", 0), opp.get("feasibility", 0),
                opp.get("confidence_score", 0),
            ])
            print(f"\nTitle:     {opp['title']}")
            print(f"Problem:   {opp['problem'][:100]}")
            print(f"Technology:{opp['technology'][:100]}")
            print(f"Market:    {opp['market'][:80]}")
            print(f"Score:     {composite}/50  (N:{opp.get('novelty_score',0)} T:{opp.get('timing_score',0)} M:{opp.get('market_score',0)} F:{opp.get('feasibility',0)} C:{opp.get('confidence_score',0)})")
            print(f"{'─'*60}")

    print(f"\nDone. Next: python run_aues.py")


if __name__ == "__main__":
    main()
