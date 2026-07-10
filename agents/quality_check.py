"""Day 4 quality gate: extract 3 papers, score fields, decide if prompt is good enough."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.research_analyst import run

FIELDS = ["problem", "technology", "keywords", "industry", "impact"]
GENERIC_BANNED = {
    "ai", "artificial intelligence", "machine learning", "education",
    "paper discusses", "this paper", "research",
}


def flag_generic(value: str | list, field: str = "") -> list[str]:
    flags = []
    text = json.dumps(value).lower() if isinstance(value, list) else value.lower()
    for banned in GENERIC_BANNED:
        if banned in text:
            flags.append(f"generic: '{banned}'")
    if field == "technology" and isinstance(value, str) and len(value.split()) < 8:
        flags.append("technology too short (< 8 words)")
    elif field != "technology" and isinstance(value, str) and len(value.split()) < 6:
        flags.append("too short (< 6 words)")
    if isinstance(value, list) and len(value) < 3:
        flags.append("too few keywords (< 3)")
    return flags


def auto_score(result: dict) -> dict:
    scores = {}
    flags = {}
    for field in FIELDS:
        value = result.get(field, "")
        field_flags = flag_generic(value, field)
        flags[field] = field_flags
        if field_flags:
            scores[field] = 5
        elif field == "keywords" and len(value) >= 4:
            scores[field] = 8
        elif isinstance(value, str) and len(value.split()) >= 10:
            scores[field] = 8
        else:
            scores[field] = 7
    scores["average"] = round(sum(scores.values()) / len(FIELDS), 1)
    return {"scores": scores, "flags": flags}


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"=== Day 4 Quality Check ({count} papers) ===\n")

    results = run(limit=count)
    if not results:
        print("No pending papers to extract.")
        return

    report = []
    for i, result in enumerate(results, 1):
        analysis = auto_score(result)
        report.append({"paper": i, "id": result["id"], "title": result["title"], **analysis})
        print(f"Paper {i}: {result['title'][:60]}")
        print(f"  Problem:    {result.get('problem', '')[:100]}")
        print(f"  Technology: {result.get('technology', '')[:100]}")
        print(f"  Keywords:   {result.get('keywords', [])}")
        print(f"  Impact:     {result.get('impact', '')[:100]}")
        print(f"  Auto-scores: {analysis['scores']}")
        if any(analysis["flags"].values()):
            print(f"  Flags: {analysis['flags']}")
        print()

    avg = sum(r["scores"]["average"] for r in report) / len(report)
    print(f"Average across {len(report)} papers: {avg}/10")
    print()
    if avg >= 8:
        print("PASS — Run on all 20: python agents/research_analyst.py 20")
    else:
        print("FAIL — Improve prompt in research_analyst.py before scaling.")
        print("To retry: reset papers with agents/reset_extractions.py")

    out = ROOT / "data" / "exports" / "quality_check_day4.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"results": results, "report": report, "average": avg}, indent=2), encoding="utf-8")
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
