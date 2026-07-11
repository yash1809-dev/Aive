"""
engines/knowledge_engine.py
============================
Knowledge Engine — manages the Knowledge Object lifecycle in AIVE.
Handles creation, versioning, provenance tracking, and retrieval of
all first-class knowledge entities (items, nodes, opportunities).

Every object is immutable by default. Updates create new versions.
Deletion is never permitted — objects are superseded.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from engines.base_engine import BaseEngine

from db.init_db import DB_PATH


class KnowledgeEngine(BaseEngine):
    """
    Manages the entire Knowledge Object lifecycle for AIVE.
    Items, Nodes, Edges, and Opportunities are first-class Knowledge Objects.
    """

    def __init__(self, db_path: Path = DB_PATH):
        super().__init__("KnowledgeEngine")
        self.db_path = db_path

    @property
    def mission(self) -> str:
        return "Manage the lifecycle, versioning, and provenance of all Knowledge Objects in AIVE."

    @property
    def responsibilities(self) -> list[str]:
        return [
            "Create and version Knowledge Objects with full provenance.",
            "Retrieve objects by type, domain, or validation state.",
            "Supersede outdated objects without deleting them.",
            "Expose search and filtering across the knowledge base.",
        ]

    @property
    def inputs(self) -> list[str]:
        return ["action", "object_type", "filters", "data"]

    @property
    def outputs(self) -> list[str]:
        return ["objects", "object_id", "version", "provenance"]

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _provenance(self, agent: str, source: str = "") -> str:
        return json.dumps({
            "created_by": agent,
            "source": source,
            "created_at": self._now(),
        })

    # ── Item Knowledge Objects ─────────────────────────────────────────────────

    def list_items(self, filters: Dict[str, Any] = None) -> List[Dict]:
        filters = filters or {}
        clauses, params = [], []

        if "type" in filters:
            clauses.append("type = ?")
            params.append(filters["type"])
        if "ko_type" in filters:
            clauses.append("ko_type = ?")
            params.append(filters["ko_type"])
        if "validation_state" in filters:
            clauses.append("validation_state = ?")
            params.append(filters["validation_state"])
        if "domain" in filters:
            clauses.append("industry LIKE ?")
            params.append(f"%{filters['domain']}%")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        limit = filters.get("limit", 100)
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM items {where} ORDER BY extracted_at DESC LIMIT ?",
                params,
            ).fetchall()
        return [dict(r) for r in rows]

    def get_item(self, item_id: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        return dict(row) if row else None

    def supersede_item(self, item_id: str, updates: Dict[str, Any], agent: str) -> str:
        """
        Create a new version of an existing item with updated fields.
        The old version is preserved with validation_state='superseded'.
        Returns the new item ID.
        """
        existing = self.get_item(item_id)
        if not existing:
            raise ValueError(f"Item not found: {item_id}")

        new_id = f"{item_id}_v{existing.get('version', 1) + 1}"
        new_version = existing.get("version", 1) + 1

        with sqlite3.connect(self.db_path) as conn:
            # Mark old as superseded
            conn.execute(
                "UPDATE items SET validation_state='superseded' WHERE id=?",
                (item_id,)
            )
            # Insert new version
            merged = {**existing, **updates}
            merged["id"] = new_id
            merged["version"] = new_version
            merged["provenance"] = self._provenance(agent, source=f"supersedes:{item_id}")
            merged["validation_state"] = "unvalidated"
            conn.execute(
                """INSERT OR IGNORE INTO items
                (id, title, source, source_url, type, raw_text, summary, problem,
                 solution, technology, keywords, industry, impact, beneficiaries,
                 year, extracted_at, extraction_status, ko_type, confidence, version,
                 provenance, validation_state)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    merged["id"], merged["title"], merged.get("source"),
                    merged.get("source_url"), merged["type"], merged.get("raw_text"),
                    merged.get("summary"), merged.get("problem"), merged.get("solution"),
                    merged.get("technology"), merged.get("keywords"), merged.get("industry"),
                    merged.get("impact"), merged.get("beneficiaries"), merged.get("year"),
                    self._now(), "done", merged.get("ko_type", "document"),
                    merged.get("confidence", 0.5), new_version,
                    merged["provenance"], "unvalidated"
                )
            )
        self.logger.info(f"Superseded {item_id} → {new_id} (v{new_version}) by {agent}")
        return new_id

    # ── Node Knowledge Objects ─────────────────────────────────────────────────

    def list_nodes(self, node_type: str = None, limit: int = 200) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if node_type:
                rows = conn.execute(
                    "SELECT * FROM nodes WHERE node_type=? LIMIT ?", (node_type, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM nodes LIMIT ?", (limit,)
                ).fetchall()
        return [dict(r) for r in rows]

    def node_stats(self) -> Dict[str, int]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT node_type, COUNT(*) as cnt FROM nodes GROUP BY node_type"
            ).fetchall()
        return {r[0]: r[1] for r in rows}

    def orphan_count(self) -> int:
        """Returns count of nodes with zero edges."""
        with sqlite3.connect(self.db_path) as conn:
            r = conn.execute("""
                SELECT COUNT(*) FROM nodes n
                WHERE NOT EXISTS (
                    SELECT 1 FROM edges e
                    WHERE e.from_node = n.id OR e.to_node = n.id
                )
            """).fetchone()
        return r[0]

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        action = inputs.get("action", "list")
        obj_type = inputs.get("object_type", "items")
        filters = inputs.get("filters", {})
        data = inputs.get("data", {})
        agent = inputs.get("agent", "system")

        if action == "list":
            if obj_type == "nodes":
                return {"objects": self.list_nodes(node_type=filters.get("node_type"))}
            elif obj_type == "node_stats":
                return {"stats": self.node_stats(), "orphan_count": self.orphan_count()}
            else:
                return {"objects": self.list_items(filters=filters)}

        elif action == "get":
            return {"object": self.get_item(inputs.get("id", ""))}

        elif action == "supersede":
            new_id = self.supersede_item(inputs["id"], data, agent=agent)
            return {"new_id": new_id}

        else:
            return {"error": f"Unknown action: {action}"}
