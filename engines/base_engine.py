"""
engines/base_engine.py
======================
Abstract base class for all AIVE engines.
Implements observability, structured inputs/outputs, and failure logging.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

# Configure structured logging for engines
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)


class BaseEngine(ABC):
    """
    Abstract Base Class for all core engines in the Discovery Operating System.
    """

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)

    @property
    @abstractmethod
    def mission(self) -> str:
        """Clear description of the engine's core objective."""
        pass

    @property
    @abstractmethod
    def responsibilities(self) -> list[str]:
        """Specific capabilities and tasks owned by this engine."""
        pass

    @property
    @abstractmethod
    def inputs(self) -> list[str]:
        """Expected inputs (e.g. ['KnowledgeObject', 'GraphNode'])."""
        pass

    @property
    @abstractmethod
    def outputs(self) -> list[str]:
        """Expected outputs (e.g. ['OpportunityObject', 'ValidationResult'])."""
        pass

    def log_failure(self, task_name: str, error: Exception, context: Dict[str, Any] = None):
        """Standardized failure mode logging for observability."""
        self.logger.error(
            f"Failure in task '{task_name}': {str(error)} | Context: {context or {}}"
        )

    @abstractmethod
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the engine's core cognitive workload."""
        pass
