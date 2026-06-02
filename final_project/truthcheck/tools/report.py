"""Render a FactCheckReport as Markdown."""

from __future__ import annotations

from truthcheck.agents.orchestrator import FactCheckReport

_VERDICT_EMOJI = {
    "consensus_supported":    "✅",
    "consensus_contradicted": "❌",
    "contested":              "⚠️",
    "unverifiable":           "❓",
    "out_of_scope":           "⬜",
}


def format_markdown(report: FactCheckReport) -> str:
    counts = report.counts
    lines: list[str] = [
        f"# TruthCheck Report",
        f"",
        f"**Video:** <{report.video_url}>  ",
        f"**Claims evaluated:** {report.total_claims}  ",
        f"**Supported:** {counts['supported']} · "
        f"**Contradicted:** {counts['contradicted']} · "
        f"**Misleading/Contested:** {counts['misleading']} · "
        f"**Unverifiable:** {counts['unverifiable']}",
        f"",
        f"---",
        f"",
    ]

    for i, claim in enumerate(report.claims, 1):
        emoji = _VERDICT_EMOJI.get(claim.verdict, "❓")
        ts = f" *(~{int(claim.timestamp_s)}s)*" if claim.timestamp_s is not None else ""
        lines += [
            f"## {i}. {emoji} `{claim.verdict}`{ts}",
            f"",
            f"> {claim.claim}",
            f"",
            f"{claim.explanation}",
            f"",
        ]

        if claim.context:
            lines += [
                f"**Context:** {claim.context}",
                f"",
            ]

        if claim.citations:
            lines.append("**Citations:**")
            for cit in claim.citations:
                link = f"[{cit.source}]({cit.url})" if cit.url else cit.source
                excerpt = f" — {cit.excerpt}" if cit.excerpt else ""
                lines.append(f"- {link}{excerpt}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)
