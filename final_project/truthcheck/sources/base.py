"""Shared types for evidence-source clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    source: str          # human-readable label, e.g. "PubMed PMID:12345"
    title: str
    url: str | None
    excerpt: str         # abstract snippet or key finding (≤500 chars)
    pmid: str | None = None


class EvidenceSource(ABC):
    """Abstract base — every source client must implement `search`."""

    @abstractmethod
    def search(self, query: str, max_results: int = 3) -> list[SearchResult]:
        """Return up to *max_results* results relevant to *query*."""
