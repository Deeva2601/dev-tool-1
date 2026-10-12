from pathlib import Path

import pytest

from contextpack.compress import mode_for, parse_rule
from contextpack.models import PackConfig
from contextpack.pipeline import pack
from contextpack.skeleton import outline


def test_parse_rule_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        parse_rule("src/**")
    with pytest.raises(ValueError):
        parse_rule("src/**=tiny")


def test_rule_beats_focus_and_default() -> None:
    config = PackConfig(
        root=Path("."),
        mode="skeleton",
        focus=["src/**"],
        rules=["src/hot.py=outline", "src/**=full"],
    )
    assert mode_for("src/hot.py", config) == "outline"
    assert mode_for("src/other.py", config) == "full"
    assert mode_for("README.md", config) == "skeleton"


def test_python_outline_has_signatures_only() -> None:
    source = (
        "import os\n"
        "\n"
        "class UserService:\n"
        "    def create(self, name: str) -> str:\n"
        '        """Create a user."""\n'
        "        return name.strip()\n"
    )
    out = outline(source, "python")
    assert out.startswith("import os\n")
    assert "class UserService:" in out
    assert "def create(self, name: str) -> str: ..." in out
    assert "strip" not in out
    assert "Create a user" not in out


def test_focus_keeps_file_verbatim(tmp_path: Path) -> None:
    (tmp_path / "keep.py").write_text("def keep() -> int:\n    return 1\n", encoding="utf-8")
    (tmp_path / "drop.py").write_text("def drop() -> int:\n    return 2\n", encoding="utf-8")
    result = pack(PackConfig(root=tmp_path, mode="skeleton", focus=["keep.py"]))
    keep = next(item for item in result.files if item.relative_path == "keep.py")
    drop = next(item for item in result.files if item.relative_path == "drop.py")
    assert "return 1" in keep.content
    assert "return 2" not in drop.content
    assert "def drop() -> int:" in drop.content


def test_outline_mode_on_pack(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        "def hello() -> str:\n    return 'hi'\n",
        encoding="utf-8",
    )
    result = pack(PackConfig(root=tmp_path, mode="outline"))
    app = next(item for item in result.files if item.relative_path == "app.py")
    assert "def hello() -> str: ..." in app.content
    assert "return" not in app.content