"""TruthCheck CLI entry point.

Usage:
    truthcheck <video-url-or-id> [--output report.json] [--format json|markdown]
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console

from truthcheck.agents.orchestrator import TruthCheckAgent
from truthcheck.config import Config
from truthcheck.tools.report import format_markdown
from truthcheck.tools.transcript import TranscriptFetchError

console = Console()


@click.command()
@click.argument("video", metavar="VIDEO_URL_OR_ID")
@click.option(
    "-o", "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write the report to a file instead of stdout.",
)
@click.option(
    "-f", "--format", "fmt",
    type=click.Choice(["json", "markdown"]),
    default="markdown",
    help="Output format (default: markdown).",
)
@click.option(
    "--max-claims", type=int, default=None,
    help="Cap the number of claims fact-checked (useful for quick demos).",
)
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
def main(video: str, output: Path | None, fmt: str, max_claims: int | None, verbose: bool) -> None:
    """Fact-check a YouTube video and produce a structured report."""
    try:
        config = Config.from_env()
    except RuntimeError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        sys.exit(2)

    if verbose:
        config = config.with_log_level("DEBUG")  # if you add this helper

    try:
        report = asyncio.run(_run(video, config, max_claims))
    except TranscriptFetchError as e:
        console.print(f"[red]Could not fetch transcript:[/red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("[yellow]Interrupted.[/yellow]")
        sys.exit(130)

    rendered = report.model_dump_json(indent=2) if fmt == "json" else format_markdown(report)

    if output:
        output.write_text(rendered, encoding="utf-8")
        console.print(f"[green]Report written to[/green] {output}")
    else:
        console.print(rendered)

    counts = report.counts
    console.print(
        f"\n[bold]Summary:[/bold] {counts['supported']} supported · "
        f"{counts['misleading']} misleading · "
        f"{counts['contradicted']} contradicted · "
        f"{counts['unverifiable']} unverifiable"
    )


async def _run(video: str, config: Config, max_claims: int | None):
    agent = TruthCheckAgent.from_config(config)
    return await agent.check(video, max_claims=max_claims)


if __name__ == "__main__":
    main()