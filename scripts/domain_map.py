import json
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "aive.db"
OUT = ROOT / "data" / "exports" / "domain_map_day5.md"


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT title, problem, technology, keywords, industry, impact
        FROM items WHERE type='paper' AND extraction_status='done'
        ORDER BY title
        """
    ).fetchall()

    keywords = Counter()
    industries = Counter()
    problems = []
    technologies = []

    for row in rows:
        problems.append(row["problem"])
        technologies.append(row["technology"])
        for kw in json.loads(row["keywords"] or "[]"):
            keywords[kw.lower()] += 1
        for ind in json.loads(row["industry"] or "[]"):
            industries[ind.lower()] += 1

    lines = [
        "# AIVE Domain Map — Day 5",
        "",
        f"**Papers extracted:** {len(rows)}",
        "",
        "## Recurring Problems",
        "",
    ]
    for i, p in enumerate(problems, 1):
        lines.append(f"{i}. {p}")

    lines += ["", "## Recurring Technologies", ""]
    for i, t in enumerate(technologies, 1):
        lines.append(f"{i}. {t}")

    lines += ["", "## Top Keywords", ""]
    for kw, count in keywords.most_common(15):
        lines.append(f"- {kw} ({count})")

    lines += ["", "## Top Industries", ""]
    for ind, count in industries.most_common(10):
        lines.append(f"- {ind} ({count})")

    lines += [
        "",
        "## Emerging Pattern Map (manual synthesis)",
        "",
        "```",
        "Teacher / Learner Gaps",
        "    ├── Unstructured LLM tutoring (no curriculum)",
        "    ├── Cold-start in knowledge tracing",
        "    ├── Misconceptions in STEM assessment",
        "    └── Academic integrity + LLM misuse",
        "",
        "Technologies",
        "    ├── Socratic dialogue + PPO curriculum sequencing",
        "    ├── Knowledge graphs (prerequisite, Bayesian, Neo4j)",
        "    ├── Automated essay scoring / difficulty estimation",
        "    └── Local fine-tuned LLMs (LLaMA, Breeze-7B)",
        "",
        "Markets / Contexts",
        "    ├── K-12 / STEM / special education",
        "    ├── Higher ed (software engineering, urban planning)",
        "    └── Rural / offline / privacy-preserving settings",
        "",
        "Potential Connection (preview)",
        "    Teacher shortage + Socratic LLM + offline models → Offline AI tutor",
        "```",
        "",
        "## One-Page Test",
        "",
        "Can you explain all 20 papers using the pattern map above?",
        "If yes → extractor works. If no → noise.",
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"Papers: {len(rows)}")


if __name__ == "__main__":
    main()
