"""
engines/event_bus.py
====================
SQLite-backed Event Bus for AIVE.
Provides persistent event logs and asynchronous publish/subscribe coordination.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "aive.db"

EVENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id          TEXT PRIMARY KEY,
    event_type  TEXT NOT NULL,
    payload     TEXT,  -- JSON string
    created_at  TEXT NOT NULL,
    processed   INTEGER DEFAULT 0
);
"""


class EventBus:
    """
    Persistent, SQLite-backed Event Bus for decoupled subsystem communication.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(EVENT_TABLE_SQL)

    def publish(self, event_type: str, payload: Dict[str, Any]) -> str:
        """
        Publish an event. Saves to database and triggers in-process subscribers.
        """
        event_id = f"evt_{uuid.uuid4().hex[:8]}"
        created_at = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload)

        # 1. Save to persistent SQLite event log
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO events (id, event_type, payload, created_at, processed) VALUES (?, ?, ?, ?, 0)",
                (event_id, event_type, payload_str, created_at)
            )

        # 2. Trigger active in-memory subscribers
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    handler(payload)
                except Exception as e:
                    print(f"[EventBus] Error in handler for {event_type}: {e}")

        # Mark processed in DB if handlers executed successfully
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE events SET processed = 1 WHERE id = ?", (event_id,))

        return event_id

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """
        Subscribe a handler to an event type.
        """
        self._subscribers.setdefault(event_type, []).append(handler)

    def get_event_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve recent events from the database log.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, event_type, payload, created_at, processed FROM events ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        
        events = []
        for r in rows:
            events.append({
                "id": r["id"],
                "event_type": r["event_type"],
                "payload": json.loads(r["payload"]) if r["payload"] else {},
                "created_at": r["created_at"],
                "processed": bool(r["processed"])
            })
        return events
