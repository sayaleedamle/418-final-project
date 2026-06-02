"""Health-organisation evidence client: CDC · WHO · NIH.

CDC, WHO, and NIH guidelines and reports are indexed in PubMed. Each sub-client
filters PubMed searches to that organisation's publications, so no separate
API credentials are needed.

Usage:
    client = HealthOrgsClient()
    results = client.search("vitamin D supplementation")
    # Returns results from CDC, WHO, and NIH combined, de-duplicated by PMID.
"""

from __future__ import annotations

import logging

from .base import EvidenceSource, SearchResult
from .pubmed import PubMedClient

log = logging.getLogger(__name__)

# PubMed affiliation / journal filters for each organisation
_FILTERS: dict[str, str] = {
    "CDC": '("Centers for Disease Control"[Affiliation] OR "MMWR"[Journal])',
    "WHO": '("World Health Organization"[Affiliation] OR "Bull World Health Organ"[Journal])',
    "NIH": '("National Institutes of Health"[Affiliation] OR "National Cancer Institute"[Affiliation])',
}


class _OrgClient(EvidenceSource):
    def __init__(self, label: str, pubmed_filter: str) -> None:
        self._label  = label
        self._pubmed = PubMedClient(extra_filter=pubmed_filter)

    def search(self, query: str, max_results: int = 2) -> list[SearchResult]:
        results = self._pubmed.search(query, max_results=max_results)
        for r in results:
            r.source = f"{self._label} ({r.source})"
        return results


class HealthOrgsClient(EvidenceSource):
    """Aggregate CDC + WHO + NIH results, de-duplicated by PMID."""

    def __init__(self) -> None:
        self._clients = [
            _OrgClient(label, filt)
            for label, filt in _FILTERS.items()
        ]

    def search(self, query: str, max_results: int = 3) -> list[SearchResult]:
        seen_pmids: set[str] = set()
        combined:   list[SearchResult] = []

        per_org = max(1, max_results // len(self._clients))
        for client in self._clients:
            try:
                for result in client.search(query, max_results=per_org):
                    if result.pmid and result.pmid in seen_pmids:
                        continue
                    if result.pmid:
                        seen_pmids.add(result.pmid)
                    combined.append(result)
                    if len(combined) >= max_results:
                        return combined
            except Exception as exc:
                log.warning("%s search failed: %s", client._label, exc)

        return combined
