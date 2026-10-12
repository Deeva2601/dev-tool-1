import json
from xml.sax.saxutils import escape
from contextpack.models import FileRecord, PackResult

# render_markdown still builds result.markdown. XML and JSON are rendered after that, from the same PackResult.


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


def render_xml(result: PackResult) -> str:
    files = []
    for record in result.files:
        files.append(
            "\n".join(
                [
                    f'  <file path="{escape(record.relative_path)}" language="{escape(record.language)}" bytes="{record.size_bytes}" tokens="{record.tokens}" mode="{escape(record.applied_mode)}" rank="{record.rank:.0f}">',
                    "    <![CDATA[",
                    record.content.replace("]]>", "]]]]><![CDATA[>"),
                    "    ]]>",
                    "  </file>",
                ]
            )
        )
    skipped = "\n".join(f"  <skipped>{escape(item)}</skipped>" for item in result.skipped)
    body = "\n".join(files)
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<digest>\n"
        f"  <summary files=\"{len(result.files)}\" skipped=\"{len(result.skipped)}\" "
        f"bytes=\"{result.total_bytes}\" tokens=\"{result.total_tokens}\"/>\n"
        f"  <tree><![CDATA[\n{result.tree}\n  ]]></tree>\n"
        f"{body}\n"
        f"{skipped}\n"
        "</digest>\n"
    )


def render_json(result: PackResult) -> str:
    payload = {
        "summary": {
            "files": len(result.files),
            "skipped": len(result.skipped),
            "bytes": result.total_bytes,
            "tokens": result.total_tokens,
        },
        "tree": result.tree,
        "files": [
            {
                "path": record.relative_path,
                "language": record.language,
                "bytes": record.size_bytes,
                "tokens": record.tokens,
                "mode": record.applied_mode,
                "rank": record.rank,
                "content": record.content,
            }
            for record in result.files
        ],
        "skipped": result.skipped,
    }
    return json.dumps(payload, indent=2) + "\n"


def render_document(result: PackResult, fmt: str) -> str:
    if fmt == "xml":
        return render_xml(result)
    if fmt == "json":
        return render_json(result)
    return result.markdown