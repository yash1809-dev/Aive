"""
packs/base_pack.py
==================
Base class for AIVE Intelligence Packs.

An Intelligence Pack is a domain-specific knowledge module that:
  - Provides domain-specific arXiv queries for ingestion
  - Contributes domain ontology (known concepts, competitors, regulations)
  - Contributes domain-specific Critic rules (kill conditions)
  - Validates concept extraction quality for that domain

Intelligence Packs make AIVE multi-domain without polluting
the core engine with domain-specific logic.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BasePack(ABC):
    """Abstract base for all domain Intelligence Packs."""

    @property
    @abstractmethod
    def domain_name(self) -> str:
        """Human-readable domain name (e.g. 'Healthcare AI')."""
        pass

    @property
    @abstractmethod
    def arxiv_queries(self) -> List[Dict[str, Any]]:
        """
        List of arXiv queries for this domain.
        Each dict: { "name": str, "query": str, "count": int }
        """
        pass

    @property
    @abstractmethod
    def known_competitors(self) -> List[str]:
        """Named existing products/companies in this domain."""
        pass

    @property
    @abstractmethod
    def known_regulations(self) -> List[str]:
        """Regulatory frameworks relevant to this domain."""
        pass

    @property
    @abstractmethod
    def key_economic_signals(self) -> List[str]:
        """Market forces driving timing in this domain."""
        pass

    @property
    @abstractmethod
    def critic_kill_conditions(self) -> List[str]:
        """Domain-specific Critic rejection rules."""
        pass

    def describe(self) -> Dict[str, Any]:
        return {
            "domain": self.domain_name,
            "query_count": len(self.arxiv_queries),
            "competitors": self.known_competitors,
            "regulations": self.known_regulations,
            "economic_signals": self.key_economic_signals,
            "critic_rules": self.critic_kill_conditions,
        }
