from pathlib import Path

import typer

from contextpack.compress import parse_rule
from contextpack.models import PackConfig
from contextpack.pipeline import pack, write_result


def main(
    path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Directory to pack.",
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write digest to this file."),
    max_file_bytes: int = typer.Option(512_000, "--max-file-bytes"),
    exclude: list[str] = typer.Option([], "--exclude", "-e", help="Extra gitignore-style pattern."),
    no_gitignore: bool = typer.Option(False, "--no-gitignore"),
    mode: str = typer.Option("full", "--mode", help="full, skeleton, or outline."),
    skeleton: bool = typer.Option(False, "--skeleton", help="Shortcut for --mode skeleton."),
    focus: list[str] = typer.Option([], "--focus", "-f", help="Glob kept verbatim. Repeatable."),
    rule: list[str] = typer.Option([], "--rule", "-r", help="PATTERN=full|skeleton|outline. Last match wins."),
    max_tokens: int | None = typer.Option(None, "--max-tokens", help="Hard cap for the sum of file tokens."),
    entry: list[str] = typer.Option([], "--entry", help="Extra entrypoint glob. Repeatable."),
) -> None:
    """Pack a local directory into one markdown digest."""
    if mode not in {"full", "skeleton", "outline"}:
        raise typer.BadParameter("mode must be full, skeleton, or outline")
    if skeleton and mode != "full":
        raise typer.BadParameter("pass either --skeleton or --mode, not both")
    if skeleton:
        mode = "skeleton"
    for item in rule:
        parse_rule(item)

    result = pack(
        PackConfig(
            root=path,
            output=output,
            max_file_bytes=max_file_bytes,
            respect_gitignore=not no_gitignore,
            extra_excludes=exclude,
            mode=mode,  # type: ignore[arg-type]
            focus=focus,
            rules=rule,
            max_tokens=max_tokens,
            entries=entry,
        )
    )
    written = write_result(result, output)
    typer.echo(
        f"files={len(result.files)} skipped={len(result.skipped)} "
        f"bytes={result.total_bytes} tokens={result.total_tokens}"
    )
    if written is not None:
        typer.echo(f"wrote {written}")
    else:
        typer.echo(result.markdown)


def app() -> None:
    typer.run(main)


if __name__ == "__main__":
    app()