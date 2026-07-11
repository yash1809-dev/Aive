"""
engines/memory_engine.py
========================
Memory Engine — manages persistent discovery history, human feedback,
and rejected ideas, allowing past decisions to influence future reasoning.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List
from engines.base_engine import BaseEngine

from db.init_db import DB_PATH


class MemoryEngine(BaseEngine):
    """
    Memory Engine: Manages the short-term and long-term memory of generated
    opportunities, human ratings, and criticism reasoning.
    """

    def __init__(self, db_path: Path = DB_PATH):
        super().__init__("MemoryEngine")
        self.db_path = db_path

    @property
    def mission(self) -> str:
        return "Store and recall generated opportunities, evaluations, and historical failures."

    @property
    def responsibilities(self) -> list[str]:
        return [
            "Log feedback and evaluations from humans.",
            "Record rejected ideas and reasons for failure.",
            "Provide search interfaces for previous discoveries."
        ]

    @property
    def inputs(self) -> list[str]:
        return ["query", "limit", "opportunity_id", "feedback"]

    @property
    def outputs(self) -> list[str]:
        return ["history", "rejected_ideas", "saved_status"]

    def log_feedback(self, opportunity_id: str, feedback: Dict[str, Any]) -> str:
        """
        Record human evaluation rating on a generated opportunity.
        """
        import uuid
        from datetime import datetime, timezone
        feedback_id = f"fb_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO opportunity_feedback (
                    id, opportunity_id, human_rating, novel, feasible, valuable, surprising, would_build, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback_id,
                    opportunity_id,
                    feedback.get("human_rating"),
                    feedback.get("novel"),
                    feedback.get("feasible"),
                    feedback.get("valuable"),
                    feedback.get("surprising"),
                    feedback.get("would_build", 0),
                    feedback.get("notes", ""),
                    now
                )
            )
        self.logger.info(f"Logged feedback {feedback_id} for opportunity {opportunity_id}")
        return feedback_id

    def get_rejected_ideas(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve all ideas rejected by the Critic.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT r.id, r.opportunity_id, r.reason, r.rejected_at, o.title, o.problem, o.technology
                FROM rejected_ideas r
                JOIN opportunities o ON r.opportunity_id = o.id
                ORDER BY r.rejected_at DESC LIMIT ?
                """,
                (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def search_past_discoveries(self, query: str = "", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search previous opportunities.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if query:
                rows = conn.execute(
                    """
                    SELECT * FROM opportunities 
                    WHERE (title LIKE ? OR problem LIKE ? OR technology LIKE ?)
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (f"%{query}%", f"%{query}%", f"%{query}%", limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM opportunities ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
        return [dict(row) for row in rows]

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        action = inputs.get("action", "search")
        query = inputs.get("query", "")
        limit = inputs.get("limit", 10)
        opp_id = inputs.get("opportunity_id")
        feedback = inputs.get("feedback")

        if action == "log_feedback" and opp_id and feedback:
            fb_id = self.log_feedback(opp_id, feedback)
            return {"status": "success", "feedback_id": fb_id}
        elif action == "get_rejected":
            rejected = self.get_rejected_ideas(limit=limit)
            return {"rejected_ideas": rejected}
        elif action == "search":
            history = self.search_past_discoveries(query=query, limit=limit)
            return {"history": history}
        else:
            err = ValueError(f"Unknown action: {action}")
            self.log_failure("run", err)
            return {"status": "failure", "error": str(err)}
