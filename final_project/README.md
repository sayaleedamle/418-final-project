# TruthCheck

A fact-checking agent for **health and nutrition claims** in long-form
educational YouTube videos.

## Scope

TruthCheck identifies health and nutrition claims in YouTube videos and
categorizes them against established medical consensus. Specifically:

- Claims with **clear scientific consensus** are verified against
  authoritative sources (PubMed, Cochrane systematic reviews, CDC, WHO,
  NIH, Mayo Clinic) and labeled `consensus_supported` or
  `consensus_contradicted`.
- Claims where **credentialed researchers actively disagree** are
  surfaced as `contested` with representative sources from each
  position. TruthCheck does **not** arbitrate ongoing scientific
  debates.
- Personal preferences, anecdotes, and untested protocols are flagged
  as `out_of_scope`.
- Non-health claims (history, politics, current events, general
  science) are flagged as `out_of_scope` and not evaluated.

This scope is deliberate. A fact-checker that confidently picks sides
in genuine scientific debates is worse than one that distinguishes
*"there is no debate to arbitrate"* from *"there is a debate, and here
are the positions."* The `contested` verdict is a feature, not a
hedge.

## Pipeline

```
YouTube URL
   │
   ▼
[1] Transcript fetch          (youtube-transcript-api)
   │
   ▼
[2] Claim extraction          (LLM — health/nutrition claims only)
   │
   ▼
[3] Evidence retrieval        (PubMed · Cochrane · CDC/WHO · Examine.com)
   │
   ▼
[4] Consensus evaluation      (LLM — is there consensus? does claim agree?)
   │
   ▼
[5] Structured report         (JSON + Markdown, with citations)
```

## Quick start

```bash
pip install -e .
cp .env.example .env   # fill in ANTHROPIC_API_KEY
truthcheck https://www.youtube.com/watch?v=VIDEO_ID
```

## Verdict taxonomy

| Verdict | Meaning |
|---|---|
| `consensus_supported` | Claim aligns with established medical consensus |
| `consensus_contradicted` | Claim contradicts established medical consensus |
| `contested` | Credentialed experts disagree; positions surfaced |
| `unverifiable` | Insufficient evidence in authoritative sources |
| `out_of_scope` | Not a health/nutrition claim, or pure opinion/anecdote |

## Project layout

```
truthcheck/
  agents/       # Orchestrator + sub-agents for each pipeline stage
  tools/        # Transcript fetcher, citation formatter
  sources/      # Per-source clients (pubmed, cochrane, health_orgs)
  prompts/      # Prompt templates for each LLM call
  utils/        # Logging, retries, schema validation
tests/          # Unit + integration tests
examples/       # Sample reports on known videos
docs/           # Architecture notes, evaluation methodology
```

## Status

Skeleton — see `docs/ARCHITECTURE.md` for build order.