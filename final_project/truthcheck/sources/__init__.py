"""Evidence-source clients for TruthCheck.

Each client implements EvidenceSource.search(query, max_results) and
returns a list of SearchResult objects with source label, URL, and excerpt.

    from truthcheck.sources import all_sources
    results = []
    for src in all_sources():
        results.extend(src.search("omega-3 cardiovascular benefit"))
"""

from .base import EvidenceSource, SearchResult
from .cochrane import CochraneClient
from .health_orgs import HealthOrgsClient
from .pubmed import PubMedClient


def all_sources() -> list[EvidenceSource]:
    """Return one instance of every configured evidence source."""
    return [
        PubMedClient(),
        CochraneClient(),
        HealthOrgsClient(),
    ]


__all__ = [
    "EvidenceSource",
    "SearchResult",
    "PubMedClient",
    "CochraneClient",
    "HealthOrgsClient",
    "all_sources",
]
