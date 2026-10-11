from pathlib import Path

from contextpack.models import PackConfig
from contextpack.pipeline import pack


def test_pack_skips_git_noise_and_counts_real_files(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("bare = false\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("secret.txt\n", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("do-not-include\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "leftpad.js").write_text("module.exports = 1\n", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
    source = tmp_path / "src"
    source.mkdir()
    (source / "app.py").write_text("def hello() -> str:\n    return 'hi'\n", encoding="utf-8")

    result = pack(PackConfig(root=tmp_path))

    included = [item.relative_path for item in result.files]
    assert included == [".gitignore", "src/app.py"]

    app = next(item for item in result.files if item.relative_path == "src/app.py")
    assert app.language == "python"
    assert app.tokens > 0
    assert "def hello" in result.markdown
    assert "do-not-include" not in result.markdown

    # Noise must not be *included* as file content
    assert not any(item.relative_path.endswith("leftpad.js") for item in result.files)
    assert not any(item.relative_path.endswith("package-lock.json") for item in result.files)
    assert not any(item.relative_path.endswith("logo.png") for item in result.files)

    # It may appear only in the skipped list
    assert any("leftpad.js" in line and "ignored" in line for line in result.skipped)
    assert any("logo.png" in line and "binary" in line for line in result.skipped)
    assert any(line.startswith("secret.txt") for line in result.skipped)

def test_extra_exclude(tmp_path: Path) -> None:
    (tmp_path / "keep.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "drop.py").write_text("y = 2\n", encoding="utf-8")
    result = pack(PackConfig(root=tmp_path, extra_excludes=["drop.py"]))
    assert [item.relative_path for item in result.files] == ["keep.py"]