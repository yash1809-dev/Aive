"""
engines/workspace_runtime.py
============================
Workspace Runtime — coordinates active research environments, resource allocation,
background discovery triggers, and time-machine version branching.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from engines.base_engine import BaseEngine

ROOT = Path(__file__).resolve().parent.parent
MASTER_DB_PATH = ROOT / "data" / "aive.db"


class WorkspaceRuntime(BaseEngine):
    """
    Coordinates workspaces, background triggers, and time-machine checkpoints.
    Ensures each workspace behaves like a living research environment.
    """

    def __init__(self, db_path: Path = MASTER_DB_PATH):
        super().__init__("WorkspaceRuntime")
        self.db_path = db_path

    @property
    def mission(self) -> str:
        return "Initialize, coordinate, and persist active research environments and their version history."

    @property
    def responsibilities(self) -> list[str]:
        return [
            "Initialize new active workspaces.",
            "Record Time-Machine state checkpoints.",
            "List and restore historical workspace versions.",
            "Transition workspace status (active, archived).",
        ]

    @property
    def inputs(self) -> list[str]:
        return ["action", "workspace_id", "workspace_name"]

    @property
    def outputs(self) -> list[str]:
        return ["workspace", "version_history", "restored_state"]

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_workspace(self, name: str) -> Dict[str, Any]:
        workspace_id = f"ws_{uuid.uuid4().hex[:8]}"
        created_at = self._now()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO workspaces (id, name, status, created_at, updated_at) VALUES (?, ?, 'active', ?, ?)",
                (workspace_id, name, created_at, created_at)
            )
        # Initialize the workspace-specific DB file
        try:
            from db.init_db import init_db
            ws_db_path = ROOT / "data" / f"aive_{workspace_id}.db"
            init_db(ws_db_path)
        except Exception as e:
            self.logger.error(f"Failed to initialize workspace DB: {e}")
        self.logger.info(f"Workspace '{name}' ({workspace_id}) initialized.")
        return {"id": workspace_id, "name": name, "status": "active", "created_at": created_at}

    def checkpoint_workspace(self, workspace_id: str, created_by: str) -> Dict[str, Any]:
        """
        Record a Time-Machine snapshot of all current nodes, edges, and opportunities.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            nodes = [dict(r) for r in conn.execute("SELECT * FROM nodes").fetchall()]
            edges = [dict(r) for r in conn.execute("SELECT * FROM edges").fetchall()]
            opps = [dict(r) for r in conn.execute("SELECT * FROM opportunities").fetchall()]

            # Determine next version
            r = conn.execute(
                "SELECT MAX(version) FROM workspace_history WHERE workspace_id=?",
                (workspace_id,)
            ).fetchone()
            next_version = (r[0] or 0) + 1

            snapshot = json.dumps({
                "nodes": nodes,
                "edges": edges,
                "opportunities": opps
            })

            history_id = f"hist_{uuid.uuid4().hex[:8]}"
            created_at = self._now()

            conn.execute(
                """INSERT INTO workspace_history (id, workspace_id, version, snapshot_data, created_at, created_by)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (history_id, workspace_id, next_version, snapshot, created_at, created_by)
            )
            
            # Update workspace timestamp
            conn.execute(
                "UPDATE workspaces SET updated_at=? WHERE id=?",
                (created_at, workspace_id)
            )

        self.logger.info(f"Workspace {workspace_id} checkpointed: version {next_version}")
        return {"history_id": history_id, "version": next_version, "created_at": created_at}

    def get_history(self, workspace_id: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, version, created_at, created_by FROM workspace_history WHERE workspace_id=? ORDER BY version DESC",
                (workspace_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def restore_version(self, workspace_id: str, version: int) -> Dict[str, Any]:
        """
        Restore the workspace graph/opportunities to a specific version from history.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT snapshot_data FROM workspace_history WHERE workspace_id=? AND version=?",
                (workspace_id, version)
            ).fetchone()

            if not row:
                raise ValueError(f"Version {version} not found for workspace {workspace_id}")

            snapshot = json.loads(row["snapshot_data"])

            # Clear current runtime graph state
            conn.execute("DELETE FROM edges")
            conn.execute("DELETE FROM nodes")
            conn.execute("DELETE FROM opportunities")

            # Restore nodes
            for n in snapshot["nodes"]:
                conn.execute(
                    "INSERT INTO nodes (id, label, node_type, source_items) VALUES (?, ?, ?, ?)",
                    (n["id"], n["label"], n["node_type"], n["source_items"])
                )

            # Restore edges
            for e in snapshot["edges"]:
                conn.execute(
                    "INSERT INTO edges (id, from_node, to_node, relationship, weight, evidence) VALUES (?, ?, ?, ?, ?, ?)",
                    (e["id"], e["from_node"], e["to_node"], e["relationship"], e["weight"], e["evidence"])
                )

            # Restore opportunities
            for opp in snapshot["opportunities"]:
                conn.execute(
                    """INSERT INTO opportunities (
                        id, title, problem, technology, market, reasoning, timing_signal,
                        evidence, existing_competitors, novelty_score, timing_score,
                        market_score, feasibility, confidence_score, edge_confidence,
                        critic_verdict, critic_notes, created_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        opp["id"], opp["title"], opp["problem"], opp["technology"], opp["market"],
                        opp["reasoning"], opp["timing_signal"], opp["evidence"], opp["existing_competitors"],
                        opp["novelty_score"], opp["timing_score"], opp["market_score"], opp["feasibility"],
                        opp["confidence_score"], opp["edge_confidence"], opp["critic_verdict"],
                        opp["critic_notes"], opp["created_at"]
                    )
                )

        self.logger.info(f"Workspace {workspace_id} restored to version {version}")
        return {"status": "restored", "version": version}

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        action = inputs.get("action", "list_workspaces")
        workspace_id = inputs.get("workspace_id")
        name = inputs.get("workspace_name", "New Workspace")
        created_by = inputs.get("created_by", "system")

        if action == "create":
            return self.create_workspace(name)
        elif action == "checkpoint" and workspace_id:
            return self.checkpoint_workspace(workspace_id, created_by)
        elif action == "history" and workspace_id:
            return {"history": self.get_history(workspace_id)}
        elif action == "restore" and workspace_id and "version" in inputs:
            return self.restore_version(workspace_id, int(inputs["version"]))
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT * FROM workspaces").fetchall()
            return {"workspaces": [dict(r) for r in rows]}
