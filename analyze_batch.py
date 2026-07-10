"""
analyze_batch.py — T27 + T28 analysis on the completed batch
T27: Opportunity Diversity (unique themes)
T28: Opportunity Compression (unique vs redundant)
"""
import json
import sqlite3
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent

# ── Load opportunities ─────────────────────────────────────────────────────
opps = json.loads((ROOT / "data" / "exports" / "opportunities_batch1.json").read_text())
critic = json.loads((ROOT / "data" / "exports" / "critic_results.json").read_text())

# Build verdict map
verdict_map = {}
for opp in critic.get("survived", []):
    verdict_map[opp["id"]] = "SURVIVED"
for opp in critic.get("rejected", []):
    verdict_map[opp["id"]] = "REJECTED"

print(f"\n{'='*65}")
print("T27 — OPPORTUNITY DIVERSITY TEST")
print(f"{'='*65}")

# Cluster by problem_node (primary axis) and technology_node (secondary)
problem_clusters = Counter()
tech_clusters = Counter()
theme_map = {}

for opp in opps:
    prob = opp.get("problem", "")[:60]
    tech = opp.get("technology", "")[:60]
    # Assign to a theme bucket based on problem keywords
    if "grading" in prob.lower() or "grading" in opp.get("title","").lower():
        theme = "Teacher Grading Workload"
    elif "integrity" in prob.lower() or "integrity" in opp.get("title","").lower() or "dishonest" in prob.lower() or "plagiar" in prob.lower():
        theme = "Academic Integrity"
    elif "knowledge trac" in prob.lower() or "knowledge trac" in tech.lower() or "procurement" in prob.lower():
        theme = "EdTech Procurement / Knowledge Tracing"
    elif "urban" in prob.lower() or "litigation" in prob.lower() or "municipal" in opp.get("market","").lower():
        theme = "Out-of-Domain (timed out)"
    else:
        theme = "Other EdTech"
    problem_clusters[theme] += 1
    theme_map[opp["id"]] = theme

print(f"\nTotal opportunities: {len(opps)}")
print(f"\nTheme distribution:")
for theme, count in problem_clusters.most_common():
    pct = count / len(opps) * 100
    bar = "█" * count
    print(f"  {theme:<40} {bar} {count} ({pct:.0f}%)")

unique_themes = len([t for t in problem_clusters if t != "Out-of-Domain (timed out)"])
print(f"\nUnique in-domain themes: {unique_themes}")
print(f"Interpretation: ", end="")
if unique_themes <= 2:
    print("⚠️  BAD — graph stuck in local optimum")
elif unique_themes <= 4:
    print("⚠️  MODERATE — narrow coverage")
elif unique_themes <= 7:
    print("✅ GOOD — reasonable diversity")
else:
    print("✅ EXCELLENT — broad coverage")

print(f"\n{'='*65}")
print("T28 — OPPORTUNITY COMPRESSION TEST")
print(f"{'='*65}")

# Check for semantic duplicates by comparing problem+technology similarity
seen_combos = {}
duplicates = []
unique_opps = []

for opp in opps:
    # Create a simplified key for deduplication
    prob_key = opp.get("problem_node", "")
    tech_key = opp.get("technology_node", "")
    combo = f"{prob_key}|{tech_key}"

    if combo in seen_combos:
        duplicates.append({
            "duplicate": opp.get("title"),
            "original": seen_combos[combo]
        })
    else:
        seen_combos[combo] = opp.get("title")
        unique_opps.append(opp)

print(f"\nTotal generated:    {len(opps)}")
print(f"Unique (by graph node pair): {len(unique_opps)}")
print(f"Duplicates:         {len(duplicates)}")

if duplicates:
    print(f"\nDuplicate pairs:")
    for d in duplicates:
        print(f"  DUPLICATE: {d['duplicate'][:60]}")
        print(f"  ORIGINAL:  {d['original'][:60]}")

uniqueness_rate = len(unique_opps) / len(opps) * 100
print(f"\nUniqueness rate: {uniqueness_rate:.0f}%")
print(f"Interpretation: ", end="")
if uniqueness_rate >= 80:
    print("✅ GOOD — low redundancy")
elif uniqueness_rate >= 60:
    print("⚠️  MODERATE — some redundancy")
else:
    print("❌ HIGH REDUNDANCY — graph traversal generating same pairs repeatedly")

print(f"\n{'='*65}")
print("FULL OPPORTUNITY TABLE")
print(f"{'='*65}")
print(f"\n{'Title':<45} {'Buyer':<30} {'Economic Signal':<35} {'Novelty':>7} {'Verdict':<10}")
print("-" * 130)

for opp in sorted(opps, key=lambda x: x.get("novelty_score", 0), reverse=True):
    title = opp.get("title", "")[:44]
    buyer = opp.get("buyer", "")[:29]
    econ = opp.get("economic_signal", "")[:34]
    novelty = opp.get("novelty_score", 0)
    verdict = verdict_map.get(opp["id"], "REJECTED")
    print(f"{title:<45} {buyer:<30} {econ:<35} {novelty:>7} {verdict:<10}")

print(f"\n{'='*65}")
print("SUMMARY")
print(f"{'='*65}")
survived = sum(1 for v in verdict_map.values() if v == "SURVIVED")
rejected = sum(1 for v in verdict_map.values() if v == "REJECTED")
print(f"Generated:    {len(opps)}")
print(f"Survived:     {survived}")
print(f"Rejected:     {rejected}")
print(f"Kill rate:    {rejected/len(opps)*100:.0f}%")
print(f"Unique themes:{unique_themes}")
print(f"Uniqueness:   {uniqueness_rate:.0f}%")
print(f"\nBottleneck diagnosis:")
if unique_themes <= 2:
    print("  → DATASET DIVERSITY: Graph is over-concentrated. Ingest new domains.")
elif survived == 0:
    print("  → CRITIC TOO STRICT or OPPORTUNITIES TOO OBVIOUS: All rejected on 'saturated market'.")
elif uniqueness_rate < 60:
    print("  → GRAPH TRAVERSAL: Generating same node pairs repeatedly. Expand search space.")
else:
    print("  → PIPELINE HEALTHY: Improve extraction quality and dataset coverage.")
