"""Record human feedback on opportunities — closes the learning loop."""

import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.init_db import DB_PATH


def save_feedback(
    opportunity_id: str,
    novel: int,
    feasible: int,
    valuable: int,
    surprising: int,
    would_build: int = 0,
    notes: str = "",
) -> str:
    fid = f"fb_{uuid.uuid4().hex[:8]}"
    rating = round((novel + feasible + valuable + surprising) / 4)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO opportunity_feedback
            (id, opportunity_id, human_rating, novel, feasible, valuable, surprising, would_build, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fid,
                opportunity_id,
                rating,
                novel,
                feasible,
                valuable,
                surprising,
                would_build,
                notes,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    return fid


def main():
    if len(sys.argv) < 7:
        print("Usage: python agents/record_feedback.py <opp_id> <novel> <feasible> <valuable> <surprising> [would_build] [notes]")
        return
    fid = save_feedback(
        sys.argv[1],
        int(sys.argv[2]),
        int(sys.argv[3]),
        int(sys.argv[4]),
        int(sys.argv[5]),
        int(sys.argv[6]) if len(sys.argv) > 6 else 0,
        sys.argv[7] if len(sys.argv) > 7 else "",
    )
    print(f"Feedback saved: {fid}")


if __name__ == "__main__":
    main()
