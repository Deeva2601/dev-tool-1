from pathlib import Path

from contextpack.models import PackConfig
from contextpack.pipeline import pack
from contextpack.skeleton import skeletonize


def test_python_keeps_signature_and_docstring() -> None:
    source = (
        "class UserService:\n"
        "    def create(self, name: str) -> str:\n"
        '        """Create a user."""\n'
        "        value = name.strip()\n"
        "        return value\n"
    )
    out = skeletonize(source, "python")
    assert "def create(self, name: str) -> str:" in out
    assert '"""Create a user."""' in out
    assert "name.strip" not in out
    assert "return value" not in out
    assert "..." in out


def test_javascript_strips_method_body() -> None:
    source = (
        "export class Api {\n"
        "  fetchUser(id) {\n"
        "    const url = '/users/' + id;\n"
        "    return fetch(url);\n"
        "  }\n"
        "}\n"
    )
    out = skeletonize(source, "javascript")
    assert "fetchUser(id)" in out
    assert "const url" not in out
    assert "/* ... */" in out


def test_typescript_arrow_and_nested() -> None:
    source = (
        "export const load = async (id: string): Promise<string> => {\n"
        "  const inner = () => {\n"
        "    return id.trim();\n"
        "  };\n"
        "  return inner();\n"
        "};\n"
    )
    out = skeletonize(source, "typescript")
    assert "export const load = async (id: string): Promise<string> =>" in out
    assert "id.trim" not in out
    assert "/* ... */" in out


def test_unknown_language_is_unchanged() -> None:
    source = "hello: world\n"
    assert skeletonize(source, "yaml") == source


def test_pack_skeleton_flag(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        "def hello() -> str:\n    return 'hi'\n",
        encoding="utf-8",
    )
    (tmp_path / "note.md").write_text("return 'hi'\n", encoding="utf-8")

    full = pack(PackConfig(root=tmp_path, skeleton=False))
    slim = pack(PackConfig(root=tmp_path, skeleton=True))

    full_py = next(item for item in full.files if item.relative_path == "app.py")
    slim_py = next(item for item in slim.files if item.relative_path == "app.py")
    slim_md = next(item for item in slim.files if item.relative_path == "note.md")

    assert "return 'hi'" in full_py.content
    assert "return 'hi'" not in slim_py.content
    assert "def hello() -> str:" in slim_py.content
    assert slim_py.tokens < full_py.tokens
    assert slim_md.content == "return 'hi'\n"