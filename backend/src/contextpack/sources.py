"""Resolve a local directory or clone a Git URL, then pack it."""

import os
import re
import subprocess
import tempfile
from pathlib import Path

from contextpack.models import PackConfig, PackResult
from contextpack.pipeline import pack

_OWNER_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_GITHUB = re.compile(
    r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?/?$"
)


def is_public_github(source: str) -> bool:
    text = source.strip().rstrip("/")
    if _OWNER_REPO.match(text):
        return True
    return bool(_GITHUB.match(text))


class SourceError(RuntimeError):
    pass


def normalize_remote(source: str) -> str:
    text = source.strip()
    if text.startswith(("https://", "http://", "ssh://", "git@", "file://")):
        return text
    if _OWNER_REPO.match(text):
        return f"https://github.com/{text}.git"
    raise SourceError(f"Not a local directory or Git URL: {source}")


def is_remote(source: str) -> bool:
    text = source.strip()
    if Path(text).is_dir():
        return False
    return text.startswith(("https://", "http://", "ssh://", "git@", "file://")) or bool(
        _OWNER_REPO.match(text)
    )


def pack_source(source: str, config: PackConfig, token: str | None = None, branch: str | None = None, timeout: int | None = None) -> PackResult:
    if not is_remote(source):
        root = Path(source).expanduser()
        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {root}")
        return pack(config.model_copy(update={"root": root}))

    with tempfile.TemporaryDirectory(prefix="contextpack-") as tmp:
        destination = Path(tmp) / "repo"
        clone_repo(source, destination, token=token, branch=branch)
        return pack(config.model_copy(update={"root": destination}))


def clone_repo(source: str, destination: Path, token: str | None = None, branch: str | None = None, timeout: int | None = None,) -> None:
    url = normalize_remote(source)
    command = ["git", "clone", "--depth", "1", "--quiet"]
    if branch:
        command.extend(["--branch", branch])
    if token:
        command.extend(["-c", f"http.extraheader=AUTHORIZATION: bearer {token}"])
    command.extend([url, str(destination)])
    try:
        subprocess.run(command, check=True, capture_output=True, env=os.environ.copy(), timeout=timeout)
    except FileNotFoundError as exc:
        raise SourceError("git is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or b"").decode("utf-8", errors="replace").strip()
        if token:
            detail = detail.replace(token, "[REDACTED]")
        raise SourceError(detail or f"git clone failed with status {exc.returncode}") from exc


def write_agent_file(digest_path: Path, result: PackResult) -> Path:
    target = digest_path.with_name(f"{digest_path.stem}.AGENTS.md")
    names = "\n".join(f"- `{item.relative_path}` ({item.applied_mode})" for item in result.files)
    skipped = "\n".join(f"- {item}" for item in result.skipped) or "- none"
    target.write_text(
        "\n".join(
            [
                "# Context digest",
                "",
                f"Read `{digest_path.name}` before answering questions about this repository.",
                "Treat that file as the only source snapshot. Do not invent files that are not listed.",
                "Files marked `outline` or `skeleton` omit implementation bodies.",
                "",
                "## Included",
                "",
                names or "- none",
                "",
                "## Skipped",
                "",
                skipped,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return target