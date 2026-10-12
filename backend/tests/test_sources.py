import subprocess
from pathlib import Path

import pytest

from contextpack.models import PackConfig
from contextpack.sources import SourceError, is_remote, normalize_remote, pack_source, write_agent_file


def test_normalize_github_short_form() -> None:
    assert normalize_remote("octocat/Hello-World") == "https://github.com/octocat/Hello-World.git"
    assert normalize_remote("https://github.com/octocat/Hello-World") == "https://github.com/octocat/Hello-World"
    assert is_remote("octocat/Hello-World")
    assert not is_remote(".")


def test_clone_file_url_and_pack(tmp_path: Path) -> None:
    git = _git_available()
    if git is None:
        pytest.skip("git is not installed")
    origin = tmp_path / "origin"
    origin.mkdir()
    (origin / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    _run(["git", "init"], origin)
    _run(["git", "add", "app.py"], origin)
    _run(["git", "-c", "user.email=dev@example.com", "-c", "user.name=dev", "commit", "-m", "init"], origin)

    result = pack_source(origin.as_uri(), PackConfig(root=tmp_path), token=None, branch=None)
    assert [item.relative_path for item in result.files] == ["app.py"]
    assert "VALUE = 1" in result.files[0].content


def test_bad_remote_does_not_echo_token(tmp_path: Path) -> None:
    if _git_available() is None:
        pytest.skip("git is not installed")
    with pytest.raises(SourceError) as raised:
        pack_source("https://example.invalid/not/a-repo.git", PackConfig(root=tmp_path), token="super-secret-token")
    assert "super-secret-token" not in str(raised.value)


def test_agent_file(tmp_path: Path) -> None:
    from contextpack.models import FileRecord, PackResult

    digest = tmp_path / "digest.md"
    digest.write_text("# digest\n", encoding="utf-8")
    result = PackResult(
        root=str(tmp_path),
        files=[
            FileRecord(
                relative_path="app.py",
                size_bytes=8,
                language="python",
                content="VALUE = 1\n",
                tokens=3,
                applied_mode="full",
                rank=10,
            )
        ],
        skipped=["secret.txt (ignored)"],
        tree=".\n└── app.py",
        markdown="# digest\n",
        total_bytes=8,
        total_tokens=3,
    )
    written = write_agent_file(digest, result)
    text = written.read_text(encoding="utf-8")
    assert written.name == "digest.AGENTS.md"
    assert "`app.py` (full)" in text
    assert "secret.txt (ignored)" in text


def _git_available() -> str | None:
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return "git"


def _run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True, capture_output=True)