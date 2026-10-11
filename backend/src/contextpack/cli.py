from pathlib import Path

import typer

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
) -> None:
    """Pack a local directory into one markdown digest."""
    result = pack(
        PackConfig(
            root=path,
            output=output,
            max_file_bytes=max_file_bytes,
            respect_gitignore=not no_gitignore,
            extra_excludes=exclude,
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
    """Console script entrypoint."""
    typer.run(main)


if __name__ == "__main__":
    app()