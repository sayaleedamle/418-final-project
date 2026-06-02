"""
TruthCheck pipeline evaluation.

Runs the fact-checking pipeline on a set of videos, collects verdict
distributions, evidence retrieval stats, and prints a summary table.

Usage
-----
    python evaluate.py                    # all 6 EDA videos, 5 claims each
    python evaluate.py --max-claims 3     # faster: 3 claims per video
    python evaluate.py --output eval.json # also save raw results

Output
------
    - Per-video verdict counts
    - Aggregate verdict distribution
    - Evidence retrieval coverage (% claims with ≥1 real citation)
    - Sample claims for each verdict type
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Make sure the package is importable when run from the project root
sys.path.insert(0, str(Path(__file__).parent))

from truthcheck.agents.orchestrator import FactCheckReport, TruthCheckAgent
from truthcheck.config import Config

# ── EDA video corpus ─────────────────────────────────────────────────────────

VIDEOS = [
    ("Ib9JmKG7Q9c", "What, Why & How of Healthy Eating",         "Nutrition Made Simple"),
    ("Q4qWzbP0q7I", "How Foods & Nutrients Control Our Moods",    "Huberman Lab"),
    ("0NqpAOWLsZc", "Heart Disease & Longevity Claims",           "Nutrition Made Simple"),
    ("4tkd_J_tWyc", "Best Longevity Diet & Supplements",          "Nutrition Made Simple"),
    ("E7W4OQfJWdw", "Nutrients for Brain Health & Performance",   "Huberman Lab"),
    ("tLS6t3FVOTI", "Rational Approach to Supplementation",       "Huberman Lab"),
]

_VERDICT_ORDER = [
    "consensus_supported",
    "consensus_contradicted",
    "contested",
    "unverifiable",
    "out_of_scope",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _evidence_covered(report: FactCheckReport) -> int:
    """Number of claims that have at least one citation with a real URL."""
    return sum(
        1 for c in report.claims
        if any(cit.url for cit in c.citations)
    )


def _print_table(rows: list[list], headers: list[str]) -> None:
    widths = [max(len(str(r[i])) for r in ([headers] + rows)) for i in range(len(headers))]
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    def row_str(r):
        return "|" + "|".join(f" {str(v):<{w}} " for v, w in zip(r, widths)) + "|"
    print(sep)
    print(row_str(headers))
    print(sep)
    for r in rows:
        print(row_str(r))
    print(sep)


# ── Main ──────────────────────────────────────────────────────────────────────

async def evaluate(max_claims: int) -> list[dict]:
    config = Config.from_env()
    config.configure_logging()
    agent = TruthCheckAgent.from_config(config)

    all_results = []
    for video_id, title, channel in VIDEOS:
        url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"\n▶  {title} ({channel})")
        try:
            report = await agent.check(url, max_claims=max_claims)
        except Exception as exc:
            print(f"   ERROR: {exc}")
            continue

        verdict_counts = Counter(c.verdict for c in report.claims)
        covered = _evidence_covered(report)

        result = {
            "video_id":       video_id,
            "title":          title,
            "channel":        channel,
            "total_claims":   report.total_claims,
            "verdicts":       dict(verdict_counts),
            "evidence_cover": covered,
            "claims":         [c.model_dump() for c in report.claims],
        }
        all_results.append(result)

        print(f"   Claims: {report.total_claims}  |  Evidence coverage: {covered}/{report.total_claims}")
        for v in _VERDICT_ORDER:
            n = verdict_counts.get(v, 0)
            if n:
                print(f"   {v}: {n}")

    return all_results


def print_summary(results: list[dict], max_claims: int) -> None:
    print("\n\n" + "=" * 70)
    print("  EVALUATION SUMMARY")
    print("=" * 70)

    # Per-video table
    headers = ["Video", "Claims", "Supported", "Contradicted", "Contested", "Unverifiable", "Evidence%"]
    rows = []
    agg: dict[str, int] = defaultdict(int)
    total_claims = 0
    total_covered = 0

    for r in results:
        v = r["verdicts"]
        n = r["total_claims"]
        cov = r["evidence_cover"]
        total_claims += n
        total_covered += cov
        for k, val in v.items():
            agg[k] += val
        rows.append([
            r["title"][:35],
            n,
            v.get("consensus_supported", 0),
            v.get("consensus_contradicted", 0),
            v.get("contested", 0),
            v.get("unverifiable", 0),
            f"{100*cov//n}%" if n else "—",
        ])

    print()
    _print_table(rows, headers)

    # Aggregate
    print(f"\nAggregate across {len(results)} videos ({total_claims} claims, max {max_claims} per video):\n")
    for v in _VERDICT_ORDER:
        n = agg.get(v, 0)
        pct = 100 * n // total_claims if total_claims else 0
        bar = "█" * (pct // 5)
        print(f"  {v:<28} {n:3d}  {pct:3d}%  {bar}")
    print(f"\n  Evidence coverage: {total_covered}/{total_claims} claims had ≥1 real citation URL")

    # Sample claims per verdict type
    print("\n\nSAMPLE CLAIMS BY VERDICT")
    print("-" * 70)
    seen: dict[str, bool] = {}
    for r in results:
        for claim in r["claims"]:
            v = claim["verdict"]
            if v not in seen:
                seen[v] = True
                print(f"\n[{v}]")
                print(f"  Claim:       {claim['claim'][:100]}")
                print(f"  Explanation: {claim['explanation'][:120]}…")
                if claim["citations"]:
                    cit = claim["citations"][0]
                    print(f"  Citation:    {cit['source']}  {cit.get('url','')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate TruthCheck pipeline")
    parser.add_argument("--max-claims", type=int, default=5,
                        help="Max claims per video (default: 5)")
    parser.add_argument("--output", type=str, default=None,
                        help="Save raw results to a JSON file")
    args = parser.parse_args()

    results = asyncio.run(evaluate(args.max_claims))

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2))
        print(f"\nRaw results saved to {args.output}")

    print_summary(results, args.max_claims)


if __name__ == "__main__":
    main()
