"""
engines/novelty_engine.py
=========================
Novelty Engine — adversarially attempts to disprove every candidate
by searching the existing knowledge graph for semantic equivalents,
prior art, and known competitor products.

Philosophy: "Its objective is not to prove novelty. Its objective is
to reject false novelty." — AIVE Constitution
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from engines.base_engine import BaseEngine

from db.init_db import DB_PATH

# N0=Known, N1=MinorVariation, N2=ObviousCombination,
# N3=WeaklyExplored, N4=NonObviousSynthesis, N5=PotentialFrontier
NOVELTY_LEVELS = ["N0", "N1", "N2", "N3", "N4", "N5"]


class NoveltyEngine(BaseEngine):
    """
    Adversarially scores each discovery candidate for novelty by
    searching for semantic equivalents in the existing graph and known
    competitor tables.
    """

    def __init__(self, db_path: Path = DB_PATH):
        super().__init__("NoveltyEngine")
        self.db_path = db_path

    @property
    def mission(self) -> str:
        return "Reject false novelty by searching for prior art, semantic equivalents, and known competitors."

    @property
    def responsibilities(self) -> list[str]:
        return [
            "Detect duplicate opportunity candidates.",
            "Search existing graph for semantic label overlap.",
            "Assign novelty level N0–N5 based on differentiation score.",
        ]

    @property
    def inputs(self) -> list[str]:
        return ["opportunity"]

    @property
    def outputs(self) -> list[str]:
        return ["novelty_level", "novelty_score", "similar_candidates", "is_novel"]

    def _get_known_titles(self) -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT title FROM opportunities"
            ).fetchall()
        return [r[0].lower() for r in rows]

    def _get_competitor_labels(self) -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT label FROM nodes WHERE node_type='Competitor'"
            ).fetchall()
        return [r[0].lower() for r in rows]

    def _token_overlap(self, a: str, b: str) -> float:
        """Simple Jaccard token overlap between two strings."""
        ta = set(a.lower().split())
        tb = set(b.lower().split())
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / len(ta | tb)

    def score_novelty(self, title: str, technology: str, competitors: List[str]) -> Dict[str, Any]:
        known_titles = self._get_known_titles()
        graph_competitors = self._get_competitor_labels()

        # 1. Check title similarity against existing opportunities
        max_title_overlap = max(
            (self._token_overlap(title, t) for t in known_titles), default=0.0
        )

        # 2. Check if technology is a known competitor
        tech_lower = technology.lower()
        is_known_competitor = any(
            comp in tech_lower or tech_lower in comp
            for comp in graph_competitors + [c.lower() for c in competitors]
        )

        # 3. Score
        if max_title_overlap > 0.7 or is_known_competitor:
            level = "N0"
            score = 1
        elif max_title_overlap > 0.5:
            level = "N1"
            score = 3
        elif max_title_overlap > 0.3:
            level = "N2"
            score = 5
        elif max_title_overlap > 0.1:
            level = "N3"
            score = 7
        elif competitors:
            level = "N4"
            score = 8
        else:
            level = "N5"
            score = 9

        return {
            "novelty_level": level,
            "novelty_score": score,
            "max_title_overlap": round(max_title_overlap, 3),
            "is_known_competitor": is_known_competitor,
            "is_novel": score >= 5,
        }

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        opp = inputs.get("opportunity", {})
        title = opp.get("title", "")
        technology = opp.get("technology", "")
        competitors = json.loads(opp.get("existing_competitors", "[]")) if isinstance(
            opp.get("existing_competitors"), str
        ) else (opp.get("existing_competitors") or [])

        result = self.score_novelty(title, technology, competitors)
        self.logger.info(
            f"Novelty: '{title[:50]}' → {result['novelty_level']} (score={result['novelty_score']})"
        )
        return result
