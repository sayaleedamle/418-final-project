"""PubMed client using NCBI E-utilities.

No API key is required, but setting NCBI_API_KEY in the environment raises the
rate limit from 3 req/s to 10 req/s.
"""

from __future__ import annotations

import logging
import os
import time
import xml.etree.ElementTree as ET

import requests

from .base import EvidenceSource, SearchResult

log = logging.getLogger(__name__)

_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EFETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_TIMEOUT = 15  # seconds


def _ncbi_params(extra: dict) -> dict:
    params = {"tool": "truthcheck", "email": "truthcheck@example.com", **extra}
    key = os.getenv("NCBI_API_KEY")
    if key:
        params["api_key"] = key
    return params


class PubMedClient(EvidenceSource):
    """Search PubMed and return structured abstracts."""

    def __init__(self, extra_filter: str = "") -> None:
        # extra_filter is appended to every query, e.g. '"Cochrane Database Syst Rev"[Journal]'
        self._filter = extra_filter

    def search(self, query: str, max_results: int = 3) -> list[SearchResult]:
        query = f"({query}) AND {self._filter}" if self._filter else query

        # Step 1 — get PMIDs
        try:
            r = requests.get(
                _ESEARCH,
                params=_ncbi_params({
                    "db": "pubmed",
                    "term": query,
                    "retmax": max_results,
                    "retmode": "json",
                    "sort": "relevance",
                }),
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            log.warning("PubMed esearch failed: %s", exc)
            return []

        pmids = r.json().get("esearchresult", {}).get("idlist", [])
        if not pmids:
            return []

        time.sleep(0.34)  # respect 3 req/s default rate limit

        # Step 2 — fetch abstracts
        try:
            r = requests.get(
                _EFETCH,
                params=_ncbi_params({
                    "db": "pubmed",
                    "id": ",".join(pmids),
                    "rettype": "abstract",
                    "retmode": "xml",
                }),
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            log.warning("PubMed efetch failed: %s", exc)
            return []

        return _parse_pubmed_xml(r.text)


def _parse_pubmed_xml(xml_text: str) -> list[SearchResult]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        log.warning("PubMed XML parse error: %s", exc)
        return []

    results = []
    for article in root.findall(".//PubmedArticle"):
        pmid    = _text(article, ".//PMID")
        title   = _text(article, ".//ArticleTitle") or "Untitled"
        # Concatenate all AbstractText sections (structured abstracts have multiple)
        parts   = [el.text or "" for el in article.findall(".//AbstractText")]
        abstract = " ".join(p.strip() for p in parts if p.strip()) or "No abstract available."

        results.append(SearchResult(
            source  = f"PubMed PMID:{pmid}",
            title   = title,
            url     = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            excerpt = abstract[:500] + ("…" if len(abstract) > 500 else ""),
            pmid    = pmid,
        ))
    return results


def _text(el: ET.Element, path: str) -> str:
    found = el.find(path)
    return (found.text or "").strip() if found is not None else ""
