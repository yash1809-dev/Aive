"""
validation/base_test.py
=======================
Abstract base class for all AIVE Validation Suite test modules.

Every Test_Module (T1–T10) must inherit from TestBase and implement
the abstract `run()` method. The base class provides:

  - load_fixtures()      — reads a JSON fixture file, raises FixtureError on problems
  - compute_pass()       — pure function: compares scores against pass_threshold
  - _validate_result()   — post-run assertion that result.passed == compute_pass(scores)
  - _run_standalone()    — classmethod for __main__ usage in each subclass
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from validation.models import TestResult


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class FixtureError(Exception):
    """
    Raised by load_fixtures() when a fixture file is missing,
    contains invalid JSON, or does not deserialise to a dict.
    """


# ---------------------------------------------------------------------------
# TestBase
# ---------------------------------------------------------------------------

class TestBase(ABC):
    """
    Abstract base class for all AIVE validation test modules.

    Subclasses MUST define the following class attributes:
        test_id         (str)  — short identifier, e.g. "T1"
        test_name       (str)  — human-readable name
        pass_threshold  (dict) — mapping of metric key → threshold value.
                                 Keys ending in "_max" use an upper-bound
                                 check (score <= threshold); all others use
                                 a lower-bound check (score >= threshold).

    Subclasses MUST implement:
        run(config, fixtures) -> TestResult
    """

    # Subclasses must override these
    test_id: ClassVar[str] = ""
    test_name: ClassVar[str] = ""
    pass_threshold: ClassVar[dict[str, float]] = {}

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def run(self, config: dict, fixtures: dict) -> TestResult:
        """
        Execute the test and return a TestResult.

        Args:
            config:   Runtime configuration (e.g. run_id, LLM settings).
            fixtures: Pre-loaded fixture data for this test.

        Returns:
            A populated TestResult.  Subclasses should call
            self._validate_result(result) before returning.
        """

    # ------------------------------------------------------------------
    # Fixture loading
    # ------------------------------------------------------------------

    def load_fixtures(self, fixture_path: Path) -> dict:
        """
        Read a JSON fixture file and return its contents as a dict.

        Args:
            fixture_path: Path to the JSON fixture file.

        Returns:
            The parsed fixture data as a dict.

        Raises:
            FixtureError: If the file does not exist, contains invalid
                          JSON, or does not deserialise to a dict.
        """
        path = Path(fixture_path)

        if not path.exists():
            raise FixtureError(
                f"Fixture file not found: {path}"
            )

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise FixtureError(
                f"Could not read fixture file {path}: {exc}"
            ) from exc

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise FixtureError(
                f"Fixture file contains invalid JSON ({path}): {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise FixtureError(
                f"Fixture file must deserialise to a JSON object (dict), "
                f"got {type(data).__name__}: {path}"
            )

        return data

    # ------------------------------------------------------------------
    # Pass computation
    # ------------------------------------------------------------------

    def compute_pass(self, scores: dict) -> bool:
        """
        Determine whether all threshold conditions are satisfied.

        Rules:
          - Keys ending in "_max": score must be <= threshold (upper bound).
          - All other keys:        score must be >= threshold (lower bound).

        Args:
            scores: Mapping of metric key → numeric score.

        Returns:
            True if every threshold condition is met, False otherwise.

        Raises:
            KeyError: If a key present in pass_threshold is absent from scores.
        """
        for key, threshold in self.pass_threshold.items():
            if key not in scores:
                raise KeyError(
                    f"compute_pass: score key '{key}' is required by "
                    f"pass_threshold but was not found in scores. "
                    f"Available keys: {list(scores.keys())}"
                )

            score = scores[key]

            if key.endswith("_max"):
                if score > threshold:
                    return False
            else:
                if score < threshold:
                    return False

        return True

    # ------------------------------------------------------------------
    # Post-run validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_result(result: TestResult) -> None:
        """
        Assert that result.passed is consistent with compute_pass(result.scores).

        This is a static helper — it reconstructs the threshold comparison
        directly from result.threshold so that it works without needing
        an instance with pass_threshold set.

        Args:
            result: The TestResult to validate.

        Raises:
            AssertionError: If result.passed does not equal the verdict
                            derived from result.scores and result.threshold.
        """
        # Recompute the expected pass verdict from the result's own threshold
        expected_pass = True
        for key, threshold in result.threshold.items():
            if key not in result.scores:
                # If a threshold key is missing from scores we cannot verify;
                # skip rather than raise so errored tests still get recorded.
                continue
            score = result.scores[key]
            if key.endswith("_max"):
                if score > threshold:
                    expected_pass = False
                    break
            else:
                if score < threshold:
                    expected_pass = False
                    break

        if result.passed != expected_pass:
            raise AssertionError(
                f"TestResult consistency error for {result.test_id!r}: "
                f"result.passed={result.passed!r} but compute_pass derived "
                f"from scores and threshold gives {expected_pass!r}. "
                f"scores={result.scores!r}, threshold={result.threshold!r}"
            )

    # ------------------------------------------------------------------
    # Standalone execution helper
    # ------------------------------------------------------------------

    @classmethod
    def _run_standalone(
        cls,
        default_fixtures_path: Path,
        config: dict | None = None,
    ) -> None:
        """
        Convenience classmethod for ``if __name__ == "__main__"`` blocks.

        Instantiates the subclass, runs it with default config and the
        given fixtures path, calls _validate_result(), then prints the
        TestResult as indented JSON to stdout.

        Args:
            default_fixtures_path: Path to the fixture file to load.
            config:                Optional config dict. Defaults to {}.
        """
        instance = cls()
        cfg = config if config is not None else {}

        fixtures = instance.load_fixtures(default_fixtures_path)
        result = instance.run(cfg, fixtures)
        cls._validate_result(result)

        # Serialise TestResult to indented JSON for human-readable output
        output = {
            "test_id": result.test_id,
            "test_name": result.test_name,
            "run_id": result.run_id,
            "passed": result.passed,
            "scores": result.scores,
            "threshold": result.threshold,
            "details": result.details,
            "error": result.error,
            "created_at": result.created_at,
        }
        print(json.dumps(output, indent=2, default=str))
