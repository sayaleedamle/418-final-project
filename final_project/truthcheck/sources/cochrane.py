"""Cochrane Reviews client.

Cochrane systematic reviews are indexed in PubMed under the journal
"Cochrane Database of Systematic Reviews". This client filters PubMed
searches to that journal, giving real Cochrane citations without needing
a separate Cochrane API key.
"""

from __future__ import annotations

from .base import EvidenceSource, SearchResult
from .pubmed import PubMedClient

# PubMed journal filter for Cochrane systematic reviews
_COCHRANE_FILTER = '"Cochrane Database Syst Rev"[Journal]'


class CochraneClient(EvidenceSource):
    """Search Cochrane systematic reviews via PubMed."""

    def __init__(self) -> None:
        self._pubmed = PubMedClient(extra_filter=_COCHRANE_FILTER)

    def search(self, query: str, max_results: int = 3) -> list[SearchResult]:
        results = self._pubmed.search(query, max_results=max_results)
        # Re-label source to make provenance clear
        for r in results:
            r.source = f"Cochrane ({r.source})"
        return results
