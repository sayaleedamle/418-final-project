"""TruthCheck orchestrator — runs the full fact-checking pipeline.

Pipeline
--------
1. Extract video ID from URL or bare ID string
2. Fetch English transcript (youtube-transcript-api)
3. Send transcript to Gemini → extract health/nutrition claims as JSON
4. Evaluate each claim concurrently against scientific consensus
5. Return a structured FactCheckReport
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from truthcheck.config import Config
from truthcheck.sources import all_sources
from truthcheck.tools.transcript import (
    TranscriptFetchError as TranscriptFetchError,  # re-exported for CLI
    extract_video_id,
    fetch_transcript,
)

log = logging.getLogger(__name__)

_MAX_CONCURRENT_CALLS = 4
_MAX_NCBI_CALLS = 2  # NCBI free tier: 3 req/s; stay conservative

# Generic words that add noise to PubMed keyword searches
_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "have",
    "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "can", "that", "this", "these", "those", "in", "on",
    "at", "to", "for", "of", "with", "by", "from", "and", "or", "but",
    "not", "no", "it", "its", "when", "where", "who", "which", "how",
    "what", "than", "also", "tend", "tends", "people", "individuals",
    "suggests", "associated", "association", "effect", "effects", "often",
    "primarily", "generally", "typically", "commonly", "usually", "more",
    "less", "some", "any", "all", "both", "each", "they", "their", "there",
    "then", "as", "such", "so", "if", "up", "out", "about", "into",
}


def _search_query(claim: str, max_terms: int = 6) -> str:
    """Distil a claim sentence into a short PubMed keyword query."""
    words = re.findall(r"[a-zA-Z]{3,}", claim)
    seen: set[str] = set()
    terms: list[str] = []
    for w in words:
        lw = w.lower()
        if lw not in _STOP_WORDS and lw not in seen:
            seen.add(lw)
            terms.append(w)
        if len(terms) == max_terms:
            break
    return " ".join(terms)

_JSON_CONFIG = types.GenerateContentConfig(
    response_mime_type="application/json",
    temperature=0.1,
)

_TEXT_CONFIG = types.GenerateContentConfig(temperature=0.0)

_SEARCH_TERMS_PROMPT = """\
You are a biomedical librarian. Extract 4-6 specific medical/scientific keywords \
for a PubMed literature search about the health claim below.

Return ONLY the keywords as a short query string — no explanation, no punctuation, \
no quotes. Use terms that would appear in PubMed paper titles or abstracts.

Examples:
  Claim: "Omega-3 fatty acids reduce the risk of cardiovascular disease."
  Query: omega-3 fatty acids cardiovascular risk reduction

  Claim: "Vitamin D deficiency is linked to increased risk of depression."
  Query: vitamin D deficiency depression mental health

Claim: {claim}
Query:"""


# ── Data models ──────────────────────────────────────────────────────────────

class Citation(BaseModel):
    source: str
    url: str | None = None
    excerpt: str | None = None


class FactCheckedClaim(BaseModel):
    claim: str
    timestamp_s: float | None = None
    context: str = ""
    verdict: str  # consensus_supported | consensus_contradicted | contested | unverifiable | out_of_scope
    explanation: str
    citations: list[Citation] = Field(default_factory=list)
    evidence_query: str = ""  # PubMed keyword query used for evidence retrieval


class FactCheckReport(BaseModel):
    video_id: str
    video_url: str
    total_claims: int
    claims: list[FactCheckedClaim]

    @property
    def counts(self) -> dict[str, int]:
        _map = {
            "consensus_supported":    "supported",
            "consensus_contradicted": "contradicted",
            "contested":              "misleading",
            "unverifiable":           "unverifiable",
        }
        result: dict[str, int] = {
            "supported": 0,
            "misleading": 0,
            "contradicted": 0,
            "unverifiable": 0,
        }
        for c in self.claims:
            key = _map.get(c.verdict)
            if key:
                result[key] += 1
        return result


# ── Prompt templates ─────────────────────────────────────────────────────────

_EXTRACT_PROMPT = """\
You are a health and nutrition fact-checking assistant.

Extract every specific, checkable factual claim about health, nutrition, medicine, or \
biology from the transcript below.

Note: the transcript may be from auto-generated captions and could lack punctuation \
or have irregular sentence boundaries. Read it carefully for meaning regardless.

Rules:
- Only extract claims verifiable against published scientific literature.
- Exclude personal opinions, anecdotes, lifestyle preferences, and non-health topics.
- Each claim must be a single declarative sentence in the third person.

Return a JSON array. Each element must have exactly these keys:
  "claim"       – the specific factual assertion as one sentence
  "timestamp_s" – approximate position in seconds (null if unknown)
  "context"     – 1–2 surrounding sentences providing context

Transcript:
{transcript}
"""

_EVALUATE_PROMPT = """\
You are a biomedical fact-checker.

Evaluate the health/nutrition claim below using the retrieved evidence snippets provided.
Classify it with one of these verdicts:
  consensus_supported     – strong cross-source evidence supports the claim
  consensus_contradicted  – strong cross-source evidence refutes the claim
  contested               – credentialed researchers actively disagree; no clear consensus
  unverifiable            – insufficient published evidence to evaluate
  out_of_scope            – not a verifiable health/nutrition claim

Claim: "{claim}"
Context: "{context}"

Retrieved evidence:
{evidence}

Return only valid JSON with exactly these keys:
  "verdict"      – one of the five values above
  "explanation"  – 2–3 sentences citing the evidence basis
  "citations"    – array of up to 3 objects drawn from the evidence above: \
{{"source": "...", "url": "...", "excerpt": "..."}}
"""


# ── Utilities ─────────────────────────────────────────────────────────────────

def _parse_json_response(text: str) -> Any:
    """Strip markdown fences from a Gemini response then parse as JSON."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


# ── Agent ─────────────────────────────────────────────────────────────────────

class TruthCheckAgent:
    def __init__(self, client: genai.Client, model: str, config: Config) -> None:
        self._client = client
        self._model = model
        self._config = config
        self._sem: asyncio.Semaphore | None = None  # created per-call inside the running loop

    @classmethod
    def from_config(cls, config: Config) -> TruthCheckAgent:
        client = genai.Client(api_key=config.gemini_api_key)
        return cls(client, config.model, config)

    async def check(
        self,
        video: str,
        max_claims: int | None = None,
        transcript: str | None = None,
    ) -> FactCheckReport:
        # Both semaphores must be created inside the running event loop
        self._sem      = asyncio.Semaphore(_MAX_CONCURRENT_CALLS)
        self._ncbi_sem = asyncio.Semaphore(_MAX_NCBI_CALLS)  # shared across ALL claims
        video_id = extract_video_id(video)
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        if transcript:
            log.info("Using provided transcript (%d chars)", len(transcript))
        else:
            log.info("Fetching transcript for %s", video_id)
            loop = asyncio.get_running_loop()
            transcript = await loop.run_in_executor(None, fetch_transcript, video_id)

        log.info("Extracting claims (%d chars of transcript)", len(transcript))
        raw_claims = await self._extract_claims(transcript)

        if max_claims is not None:
            raw_claims = raw_claims[:max_claims]

        log.info("Evaluating %d claim(s)", len(raw_claims))
        checked = await asyncio.gather(*[self._evaluate_claim(c) for c in raw_claims])

        return FactCheckReport(
            video_id=video_id,
            video_url=video_url,
            total_claims=len(checked),
            claims=list(checked),
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _gemini(self, prompt: str) -> str:
        """Run a single Gemini JSON call inside the concurrency semaphore."""
        loop = asyncio.get_running_loop()
        async with self._sem:
            response = await loop.run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=_JSON_CONFIG,
                ),
            )
        return response.text

    async def _gemini_text(self, prompt: str) -> str:
        """Run a plain-text (non-JSON) Gemini call inside the concurrency semaphore."""
        loop = asyncio.get_running_loop()
        async with self._sem:
            response = await loop.run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=_TEXT_CONFIG,
                ),
            )
        return response.text.strip()

    async def _make_search_query(self, claim: str) -> str:
        """Use Gemini to extract concise PubMed keywords from a claim.

        Falls back to the mechanical _search_query if the LLM call fails.
        """
        try:
            prompt = _SEARCH_TERMS_PROMPT.format(claim=claim)
            result = await self._gemini_text(prompt)
            # Take first line only, strip stray punctuation
            query = result.splitlines()[0].strip().strip('"').strip("'")
            if query:
                return query
        except Exception as exc:
            log.warning("Search term extraction failed, using fallback: %s", exc)
        return _search_query(claim)

    async def _fetch_evidence(self, claim: str) -> tuple[str, str]:
        """Returns (evidence_text, query_used)."""
        """Query all evidence sources sequentially, one claim at a time.

        Sources are queried one-after-another (not concurrently) so we never
        exceed NCBI's 3 req/s rate limit.  The ncbi_sem ensures only
        _MAX_NCBI_CALLS claims are doing NCBI work simultaneously.
        """
        query = await self._make_search_query(claim)
        log.info("Evidence query: '%s...' → '%s'", claim[:40], query)
        snippets: list[str] = []

        async with self._ncbi_sem:
            for src in all_sources():
                try:
                    results = await asyncio.to_thread(src.search, query, 2)
                    log.info("  %s → %d result(s)", type(src).__name__, len(results))
                    for r in results:
                        snippets.append(
                            f"[{r.source}] {r.title}\n{r.url or ''}\n{r.excerpt}"
                        )
                except Exception as exc:
                    log.warning("  %s failed: %s", type(src).__name__, exc)

        if not snippets:
            log.warning("Zero evidence retrieved for: %s", query)
        return "\n\n".join(snippets) if snippets else "No evidence retrieved.", query

    async def _extract_claims(self, transcript: str) -> list[dict]:
        prompt = _EXTRACT_PROMPT.format(transcript=transcript)
        try:
            text = await self._gemini(prompt)
            claims = _parse_json_response(text)
            return claims if isinstance(claims, list) else []
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("Claim extraction parse error: %s", exc)
            return []

    async def _evaluate_claim(self, raw: dict) -> FactCheckedClaim:
        claim_text = raw.get("claim", "")
        context    = raw.get("context", "")
        timestamp_s = raw.get("timestamp_s")

        evidence, evidence_query = await self._fetch_evidence(claim_text)
        prompt = _EVALUATE_PROMPT.format(
            claim=claim_text, context=context, evidence=evidence
        )
        try:
            text = await self._gemini(prompt)
            data = _parse_json_response(text)
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("Evaluation parse error for '%s': %s", claim_text[:60], exc)
            data = {
                "verdict":     "unverifiable",
                "explanation": "LLM response could not be parsed.",
                "citations":   [],
            }

        return FactCheckedClaim(
            claim=claim_text,
            timestamp_s=float(timestamp_s) if timestamp_s is not None else None,
            context=context,
            verdict=data.get("verdict", "unverifiable"),
            explanation=data.get("explanation", ""),
            citations=[
                Citation(**c)
                for c in data.get("citations", [])
                if isinstance(c, dict)
            ],
            evidence_query=evidence_query,
        )
