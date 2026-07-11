"""
engines/reasoning_engine.py
===========================
Reasoning Engine — performs analogical and cross-domain reasoning over the knowledge graph
to identify hidden patterns and suggest novel hypothesis connections.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List
from engines.base_engine import BaseEngine

from db.init_db import DB_PATH


class ReasoningEngine(BaseEngine):
    """
    Reasoning Engine: Models semantic relationships, performs path traversal,
    and identifies analogical cross-domain patterns (e.g., Clinical NLP applied to Vocational training).
    """

    def __init__(self, db_path: Path = DB_PATH):
        super().__init__("ReasoningEngine")
        self.db_path = db_path

    @property
    def mission(self) -> str:
        return "Analyze relationships and infer connections across different domain clusters in the knowledge graph."

    @property
    def responsibilities(self) -> list[str]:
        return [
            "Detect cross-domain analogical connections.",
            "Traverse semantic paths between problems and technologies.",
            "Formulate candidate hypotheses for the Discovery Engine."
        ]

    @property
    def inputs(self) -> list[str]:
        return ["source_node_id", "target_node_id", "max_hops"]

    @property
    def outputs(self) -> list[str]:
        return ["reasoning_paths", "hypotheses"]

    def find_all_paths(self, start_id: str, end_id: str, max_hops: int = 3) -> List[List[Dict[str, Any]]]:
        """
        Find all paths between two nodes up to max_hops length.
        """
        # Load graph topology from SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            edges = conn.execute("SELECT from_node, to_node, relationship, weight FROM edges").fetchall()
            nodes = conn.execute("SELECT id, label, node_type FROM nodes").fetchall()

        node_map = {n["id"]: {"label": n["label"], "type": n["node_type"]} for n in nodes}
        
        # Build adjacency list
        adj: Dict[str, List[Dict[str, Any]]] = {}
        for edge in edges:
            fn, tn = edge["from_node"], edge["to_node"]
            adj.setdefault(fn, []).append({"to": tn, "rel": edge["relationship"], "weight": edge["weight"]})
            adj.setdefault(tn, []).append({"to": fn, "rel": edge["relationship"], "weight": edge["weight"]})

        # DFS path finding
        paths = []
        
        def dfs(curr: str, target: str, path: List[Dict[str, Any]], visited: set):
            if len(path) > max_hops:
                return
            if curr == target:
                paths.append(list(path))
                return
            
            for neighbor in adj.get(curr, []):
                next_node = neighbor["to"]
                if next_node not in visited:
                    visited.add(next_node)
                    path.append({
                        "from": curr,
                        "from_label": node_map.get(curr, {}).get("label", curr),
                        "relation": neighbor["rel"],
                        "to": next_node,
                        "to_label": node_map.get(next_node, {}).get("label", next_node),
                        "weight": neighbor["weight"]
                    })
                    dfs(next_node, target, path, visited)
                    path.pop()
                    visited.remove(next_node)

        dfs(start_id, end_id, [], {start_id})
        return paths

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        action = inputs.get("action", "find_paths")
        start_id = inputs.get("source_node_id")
        end_id = inputs.get("target_node_id")
        max_hops = inputs.get("max_hops", 3)

        if action == "find_paths" and start_id and end_id:
            paths = self.find_all_paths(start_id, end_id, max_hops=max_hops)
            return {"status": "success", "paths": paths, "path_count": len(paths)}
        else:
            return {"status": "error", "message": "Missing source_node_id or target_node_id"}
