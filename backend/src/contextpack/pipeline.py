from pathlib import Path

from contextpack.budget import fit_budget, prepare_item
from contextpack.compress import is_focus_pinned, mode_for
from contextpack.discover import iter_source_files, language_for, load_spec
from contextpack.formatters import directory_tree, render_document, render_markdown
from contextpack.models import FileRecord, PackConfig, PackResult
from contextpack.tokens import count_tokens
from contextpack.rank import rank_paths
from contextpack.secrets import redact


def pack(config: PackConfig) -> PackResult:
    root = config.root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    spec = load_spec(root, config.respect_gitignore, config.extra_excludes)
    prepared = []
    skipped: list[str] = []

    for path, relative, reason in iter_source_files(root, spec, config.max_file_bytes):
        if path is None:
            skipped.append(f"{relative} ({reason})")
            continue
        raw_text = path.read_text(encoding="utf-8", errors="replace")
        if config.redact_secrets:
            raw_text = redact(raw_text)
        language = language_for(path)
        prepared.append(
            prepare_item(
                relative_path=relative,
                size_bytes=path.stat().st_size,
                language=language,
                raw=raw_text,
                mode=mode_for(relative, config),
                pinned=is_focus_pinned(relative, config),
            )
        ) 
    scores = rank_paths(
        [(item.relative_path, item.raw, item.language) for item in prepared],
        config.entries,
    )
    for item in prepared:
        item.rank = scores.get(item.relative_path, 0.0)

    fitted = fit_budget(prepared, config.max_tokens)
    skipped.extend(fitted.omitted)

    files = [
        FileRecord(
            relative_path=item.relative_path,
            size_bytes=item.size_bytes,
            language=item.language,
            content=item.content,
            tokens=item.tokens,
            applied_mode=item.mode,
            rank=item.rank,
        )
        for item in fitted.kept
    ]
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
    result = PackResult(
        root=str(root),
        files=files,
        skipped=skipped,
        tree=tree,
        markdown=markdown,
        total_bytes=total_bytes,
        total_tokens=total_tokens,
    )
    if config.format != "markdown":
        result.markdown = render_document(result, config.format)
    return result

    


def write_result(result: PackResult, output: Path | None) -> Path | None:
    if output is None:
        return None
    destination = output.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(result.markdown, encoding="utf-8")
    return destination