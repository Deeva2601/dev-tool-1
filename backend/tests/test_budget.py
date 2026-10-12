from pathlib import Path

from contextpack.models import PackConfig
from contextpack.pipeline import pack


def _source(name: str, body_lines: int) -> str:
    body = "\n".join(f"    x{i} = {i}" for i in range(body_lines))
    return f"def {name}() -> int:\n{body}\n    return 1\n"


def test_budget_downgrades_largest_file_first(tmp_path: Path) -> None:
    (tmp_path / "big.py").write_text(_source("big", 40), encoding="utf-8")
    (tmp_path / "small.py").write_text(_source("small", 2), encoding="utf-8")

    full = pack(PackConfig(root=tmp_path, mode="full"))
    assert full.total_tokens > 30

    fitted = pack(PackConfig(root=tmp_path, mode="full", max_tokens=full.total_tokens - 1))
    modes = {item.relative_path: item.applied_mode for item in fitted.files}
    assert modes["big.py"] in {"skeleton", "outline"}
    assert "return 1" not in next(item.content for item in fitted.files if item.relative_path == "big.py")
    assert fitted.total_tokens <= full.total_tokens - 1 or modes["small.py"] != "full"


def test_focus_file_is_not_downgraded(tmp_path: Path) -> None:
    (tmp_path / "keep.py").write_text(_source("keep", 30), encoding="utf-8")
    (tmp_path / "other.py").write_text(_source("other", 30), encoding="utf-8")

    result = pack(
        PackConfig(root=tmp_path, mode="full", focus=["keep.py"], max_tokens=40)
    )
    keep = next(item for item in result.files if item.relative_path == "keep.py")
    assert keep.applied_mode == "full"
    assert "return 1" in keep.content
    if any(item.relative_path == "other.py" for item in result.files):
        other = next(item for item in result.files if item.relative_path == "other.py")
        assert other.applied_mode != "full"
    else:
        assert any("other.py" in line and "over-budget" in line for line in result.skipped)


def test_tiny_budget_omits_unpinned_file(tmp_path: Path) -> None:
    (tmp_path / "only.py").write_text(_source("only", 20), encoding="utf-8")
    result = pack(PackConfig(root=tmp_path, mode="outline", max_tokens=1))
    assert result.files == []
    assert any("only.py" in line and "over-budget" in line for line in result.skipped)


def test_no_budget_keeps_full_source(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(_source("hello", 3), encoding="utf-8")
    result = pack(PackConfig(root=tmp_path))
    app = result.files[0]
    assert app.applied_mode == "full"
    assert "return 1" in app.content