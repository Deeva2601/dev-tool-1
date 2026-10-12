from contextpack.models import FileRecord


def directory_tree(paths: list[str]) -> str:
    """Render a POSIX path list as a text tree. Paths must use forward slashes."""
    root: dict = {}
    for path in sorted(paths):
        node = root
        for part in path.split("/"):
            node = node.setdefault(part, {})

    lines: list[str] = ["."]

    def walk(node: dict, prefix: str) -> None:
        items = list(node.items())
        for index, (name, child) in enumerate(items):
            last = index == len(items) - 1
            branch = "└── " if last else "├── "
            lines.append(f"{prefix}{branch}{name}")
            if child:
                walk(child, prefix + ("    " if last else "│   "))

    walk(root, "")
    return "\n".join(lines)


def render_markdown(
    root_name: str,
    files: list[FileRecord],
    skipped: list[str],
    tree: str,
    total_bytes: int,
    total_tokens: int,
) -> str:
    parts = [
        f"# Context digest: {root_name}",
        "",
        "## Summary",
        "",
        f"- Files included: {len(files)}",
        f"- Files skipped: {len(skipped)}",
        f"- Bytes: {total_bytes}",
        f"- Tokens (cl100k_base): {total_tokens}",
        "",
        "## Directory structure",
        "",
        "```text",
        tree,
        "```",
        "",
        "## Files",
        "",
    ]
    for record in files:
        parts.extend(
            [
                f"### {record.relative_path}",
                "",
                f"<!-- bytes: {record.size_bytes} tokens: {record.tokens} mode: {record.applied_mode} rank: {record.rank:.0f} -->",
                "",
                f"```{record.language}",
                record.content.rstrip("\n"),
                "```",
                "",
            ]
        )
    if skipped:
        parts.extend(["## Skipped", ""])
        parts.extend(f"- {item}" for item in skipped)
        parts.append("")
    return "\n".join(parts)