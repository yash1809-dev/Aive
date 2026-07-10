"""
validation/score_recorder.py
============================
Persistence layer for the AIVE Validation Suite.

Writes and reads TestResult objects to/from data/validation.db.
Never opens a write connection to data/aive.db.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from validation.models import SuiteReport, TestResult
from validation.db.init_validation_db import init_db

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "validation.db"
EXPORTS_DIR = ROOT / "data" / "exports"


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class RecordingError(Exception):
    """Raised when a TestResult cannot be written to the validation database."""


# ---------------------------------------------------------------------------
# ScoreRecorder
# ---------------------------------------------------------------------------

class ScoreRecorder:
    """
    Handles all reads and writes to data/validation.db.

    Every public method calls _ensure_db() so the database and schema are
    created on first use without requiring an explicit setup step.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else DB_PATH

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_db(self) -> None:
        """Initialise the database and schema if they do not exist yet."""
        init_db(self._db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _row_to_test_result(row: sqlite3.Row) -> TestResult:
        return TestResult(
            test_id=row["test_id"],
            test_name=row["test_name"] or "",
            run_id=row["run_id"],
            passed=bool(row["passed"]),
            scores=json.loads(row["scores_json"] or "{}"),
            threshold=json.loads(row["threshold_json"] or "{}"),
            details=json.loads(row["details_json"] or "{}"),
            error=row["error"],
            created_at=row["created_at"] or "",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def new_run(self, label: str = "") -> str:
        """
        Insert a new row into test_runs and return the unique run_id.

        Args:
            label: Optional human-readable label for this run.

        Returns:
            A 12-character hex run_id.
        """
        self._ensure_db()
        run_id = uuid.uuid4().hex[:12]
        created_at = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO test_runs (run_id, label, created_at,
                                       total_tests, passed, failed, errored)
                VALUES (?, ?, ?, 0, 0, 0, 0)
                """,
                (run_id, label, created_at),
            )

        return run_id

    def record(self, run_id: str, result: TestResult) -> None:
        """
        Insert a TestResult into test_results.

        Args:
            run_id: The run this result belongs to.
            result: The TestResult to persist.

        Raises:
            RecordingError: On a duplicate (run_id, test_id) pair.
                            Also writes a JSON fallback file to
                            data/exports/validation_fallback_{run_id}.json.
        """
        self._ensure_db()
        row_id = uuid.uuid4().hex
        created_at = (
            result.created_at
            if result.created_at
            else datetime.now(timezone.utc).isoformat()
        )

        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO test_results
                        (id, run_id, test_id, test_name, passed,
                         scores_json, threshold_json, details_json,
                         error, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row_id,
                        run_id,
                        result.test_id,
                        result.test_name,
                        1 if result.passed else 0,
                        json.dumps(result.scores),
                        json.dumps(result.threshold),
                        json.dumps(result.details),
                        result.error,
                        created_at,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            self._write_fallback(run_id, result)
            raise RecordingError(
                f"Duplicate (run_id, test_id): ({run_id!r}, {result.test_id!r})"
            ) from exc

    def get_run(self, run_id: str) -> list[TestResult]:
        """
        Return all TestResult objects recorded under run_id.

        Args:
            run_id: The run to query.

        Returns:
            A list of TestResult objects (may be empty).
        """
        self._ensure_db()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM test_results WHERE run_id = ? ORDER BY created_at",
                (run_id,),
            ).fetchall()
        return [self._row_to_test_result(r) for r in rows]

    def get_history(self, test_id: str, limit: int = 10) -> list[TestResult]:
        """
        Return the most recent `limit` TestResult objects for a given test_id.

        Args:
            test_id: The test identifier (e.g. 'T1').
            limit:   Maximum number of results to return.

        Returns:
            A list of TestResult objects, newest first.
        """
        self._ensure_db()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM test_results
                WHERE test_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (test_id, limit),
            ).fetchall()
        return [self._row_to_test_result(r) for r in rows]

    def generate_report(self, run_id: str) -> SuiteReport:
        """
        Assemble a SuiteReport from all stored results for run_id.

        Args:
            run_id: The run to report on.

        Returns:
            A populated SuiteReport dataclass.

        Raises:
            ValueError: If run_id does not exist in test_runs.
        """
        self._ensure_db()

        with self._connect() as conn:
            run_row = conn.execute(
                "SELECT * FROM test_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()

        if run_row is None:
            raise ValueError("run_id not found")

        results = self.get_run(run_id)

        passed = sum(1 for r in results if r.passed and r.error is None)
        errored = sum(1 for r in results if r.error is not None)
        failed = len(results) - passed - errored
        total_tests = len(results)

        pass_rate = passed / total_tests if total_tests > 0 else 0.0

        created_at = datetime.now(timezone.utc).isoformat()

        return SuiteReport(
            run_id=run_id,
            label=run_row["label"] or "",
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            errored=errored,
            pass_rate=pass_rate,
            results=results,
            summary="",
            created_at=created_at,
        )

    # ------------------------------------------------------------------
    # Fallback helper
    # ------------------------------------------------------------------

    def _write_fallback(self, run_id: str, result: TestResult) -> None:
        """Write a JSON fallback file when a RecordingError occurs."""
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        fallback_path = EXPORTS_DIR / f"validation_fallback_{run_id}.json"

        payload = {
            "run_id": run_id,
            "test_id": result.test_id,
            "test_name": result.test_name,
            "passed": result.passed,
            "scores": result.scores,
            "threshold": result.threshold,
            "details": result.details,
            "error": result.error,
            "created_at": result.created_at,
        }

        with open(fallback_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
