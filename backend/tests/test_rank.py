from pathlib import Path

from contextpack.models import PackConfig
from contextpack.pipeline import pack
from contextpack.rank import rank_paths


def test_entry_outranks_import_which_outranks_orphan() -> None:
    files = [
        ("main.py", "import helper\n", "python"),
        ("helper.py", "VALUE = 1\n", "python"),
        ("orphan.py", "VALUE = 2\n", "python"),
    ]
    scores = rank_paths(files, [])
    assert scores["main.py"] > scores["helper.py"] > scores["orphan.py"]


def test_python_relative_import() -> None:
    files = [
        ("pkg/a.py", "from .b import name\n", "python"),
        ("pkg/b.py", "name = 'b'\n", "python"),
    ]
    scores = rank_paths(files, ["pkg/a.py"])
    assert scores["pkg/a.py"] > scores["pkg/b.py"]


def test_js_relative_import() -> None:
    files = [
        ("index.ts", "import { run } from './util'\n", "typescript"),
        ("util.ts", "export const run = () => 1\n", "typescript"),
    ]
    scores = rank_paths(files, [])
    assert scores["index.ts"] > scores["util.ts"]


def test_budget_downgrades_orphan_before_larger_entry(tmp_path: Path) -> None:
    entry = "import helper\n\n" + "\n".join(f"MARKER_{i} = {i}" for i in range(40)) + "\n"
    (tmp_path / "main.py").write_text(entry, encoding="utf-8")
    (tmp_path / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "orphan.py").write_text(
        "def orphan() -> int:\n    return 1\n",
        encoding="utf-8",
    )

    full = pack(PackConfig(root=tmp_path, mode="full"))
    fitted = pack(PackConfig(root=tmp_path, mode="full", max_tokens=full.total_tokens - 1))
    modes = {item.relative_path: item.applied_mode for item in fitted.files}
    assert modes["main.py"] == "full"
    assert modes.get("orphan.py", "outline") != "full" or any(
        "orphan.py" in line for line in fitted.skipped
    )