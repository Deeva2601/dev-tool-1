import os
from pathlib import Path

import typer

from contextpack.compress import parse_rule
from contextpack.models import PackConfig
from contextpack.pipeline import write_result
from contextpack.sources import SourceError, pack_source, write_agent_file


def main(
    source: str = typer.Argument(..., help="Local directory, owner/repo, or Git URL."),
    output: Path | None = typer.Option(None, "--output", "-o"),
    max_file_bytes: int = typer.Option(512_000, "--max-file-bytes"),
    exclude: list[str] = typer.Option([], "--exclude", "-e"),
    no_gitignore: bool = typer.Option(False, "--no-gitignore"),
    mode: str = typer.Option("full", "--mode"),
    skeleton: bool = typer.Option(False, "--skeleton"),
    focus: list[str] = typer.Option([], "--focus", "-f"),
    rule: list[str] = typer.Option([], "--rule", "-r"),
    max_tokens: int | None = typer.Option(None, "--max-tokens"),
    entry: list[str] = typer.Option([], "--entry"),
    output_format: str = typer.Option("markdown", "--format"),
    no_redact: bool = typer.Option(False, "--no-redact"),
    branch: str | None = typer.Option(None, "--branch"),
    token: str | None = typer.Option(
        None,
        "--token",
        envvar="CONTEXTPACK_TOKEN",
        help="GitHub token for a private clone. Prefer the env var.",
    ),
    agent: bool = typer.Option(False, "--agent", help="Write a sibling .AGENTS.md next to --output."),
) -> None:
    """Pack a local directory or Git repository into one digest."""
    if mode not in {"full", "skeleton", "outline"}:
        raise typer.BadParameter("mode must be full, skeleton, or outline")
    if skeleton and mode != "full":
        raise typer.BadParameter("pass either --skeleton or --mode, not both")
    if skeleton:
        mode = "skeleton"
    if output_format not in {"markdown", "xml", "json"}:
        raise typer.BadParameter("format must be markdown, xml, or json")
    if agent and output is None:
        raise typer.BadParameter("--agent requires --output")
    for item in rule:
        parse_rule(item)

    config = PackConfig(
        root=Path("."),
        output=output,
        max_file_bytes=max_file_bytes,
        respect_gitignore=not no_gitignore,
        extra_excludes=exclude,
        mode=mode,  # type: ignore[arg-type]
        focus=focus,
        rules=rule,
        max_tokens=max_tokens,
        entries=entry,
        format=output_format,  # type: ignore[arg-type]
        redact_secrets=not no_redact,
    )
    try:
        result = pack_source(source, config, token=token or os.environ.get("CONTEXTPACK_TOKEN"), branch=branch)
    except (SourceError, NotADirectoryError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    written = write_result(result, output)
    typer.echo(
        f"files={len(result.files)} skipped={len(result.skipped)} "
        f"bytes={result.total_bytes} tokens={result.total_tokens}"
    )
    if written is not None:
        typer.echo(f"wrote {written}")
        if agent:
            instructions = write_agent_file(written, result)
            typer.echo(f"wrote {instructions}")
    else:
        typer.echo(result.markdown)


def app() -> None:
    typer.run(main)