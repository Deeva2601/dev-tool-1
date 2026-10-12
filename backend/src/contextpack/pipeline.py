from pathlib import Path

from contextpack.discover import iter_source_files, language_for, load_spec
from contextpack.formatters import directory_tree, render_markdown
from contextpack.models import FileRecord, PackConfig, PackResult
from contextpack.tokens import count_tokens
from contextpack.skeleton import skeletonize


def pack(config: PackConfig) -> PackResult:
    root = config.root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    spec = load_spec(root, config.respect_gitignore, config.extra_excludes)
    files: list[FileRecord] = []
    skipped: list[str] = []

    for path, relative, reason in iter_source_files(root, spec, config.max_file_bytes):
        if path is None:
            skipped.append(f"{relative} ({reason})")
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        if config.skeleton:
            content = skeletonize(content, language_for(path))
        files.append(
            FileRecord(
                relative_path=relative,
                size_bytes=path.stat().st_size,
                language=language_for(path),
                content=content,
                tokens=count_tokens(content),
            )
        )

    files.sort(key=lambda item: item.relative_path)
    tree = directory_tree([item.relative_path for item in files])
    total_bytes = sum(item.size_bytes for item in files)
    total_tokens = sum(item.tokens for item in files)
    markdown = render_markdown(
        root_name=root.name,
        files=files,
        skipped=skipped,
        tree=tree,
        total_bytes=total_bytes,
        total_tokens=total_tokens,
    )
    return PackResult(
        root=str(root),
        files=files,
        skipped=skipped,
        tree=tree,
        markdown=markdown,
        total_bytes=total_bytes,
        total_tokens=total_tokens,
    )


def write_result(result: PackResult, output: Path | None) -> Path | None:
    if output is None:
        return None
    destination = output.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(result.markdown, encoding="utf-8")
    return destination