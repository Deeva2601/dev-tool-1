"""Score files from static imports and entrypoint distance."""

import posixpath
import re
from collections import deque

import pathspec

DEFAULT_ENTRY_GLOBS = [
    "main.py",
    "__main__.py",
    "app.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "cli.py",
    "index.js",
    "index.ts",
    "index.tsx",
    "index.mjs",
    "main.js",
    "main.ts",
]

_PY_IMPORT = re.compile(r"(?m)^[ \t]*import[ \t]+([\w.]+)")
_PY_FROM = re.compile(r"(?m)^[ \t]*from[ \t]+(\.*)([\w.]*)[ \t]+import[ \t]+(.+)")
_JS_SPEC = re.compile(
    r"""(?:import|export)\s+(?:[^'"\n]+?\s+from\s+)?['"](\.[^'"]+)['"]|require\(\s*['"](\.[^'"]+)['"]\s*\)"""
)
_JS_EXTS = (
    "",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    "/index.ts",
    "/index.tsx",
    "/index.js",
    "/index.jsx",
    "/index.mjs",
)

_UNREACHABLE = 10_000


def rank_paths(files: list[tuple[str, str, str]], entry_globs: list[str]) -> dict[str, float]:
    """Return a score per relative path. Higher means keep it fuller for longer."""
    known = {path for path, _raw, _lang in files}
    graph: dict[str, set[str]] = {path: set() for path in known}
    for path, raw, language in files:
        for dep in _imports(raw, language, path, known):
            graph[path].add(dep)

    spec = pathspec.PathSpec.from_lines("gitignore", [*DEFAULT_ENTRY_GLOBS, *entry_globs])
    distance: dict[str, int] = {}
    queue: deque[str] = deque()
    for path in sorted(known):
        if spec.match_file(path):
            distance[path] = 0
            queue.append(path)
    while queue:
        current = queue.popleft()
        for dep in sorted(graph[current]):
            if dep not in distance:
                distance[dep] = distance[current] + 1
                queue.append(dep)

    indegree = {path: 0 for path in known}
    for deps in graph.values():
        for dep in deps:
            indegree[dep] += 1

    return {
        path: float((_UNREACHABLE - distance.get(path, _UNREACHABLE)) * 100 + indegree[path])
        for path in known
    }


def _imports(raw: str, language: str, path: str, known: set[str]) -> set[str]:
    if language == "python":
        found = _python_imports(raw, path)
    elif language in {"javascript", "jsx", "typescript", "tsx"}:
        found = _js_imports(raw, path)
    else:
        return set()
    return {item for item in found if item in known}


def _python_imports(raw: str, path: str) -> set[str]:
    found: set[str] = set()
    for match in _PY_IMPORT.finditer(raw):
        found.update(_python_candidates(match.group(1).split(".")))
    for match in _PY_FROM.finditer(raw):
        dots, module, names = match.group(1), match.group(2), match.group(3)
        if dots:
            parts = path.split("/")[:-1]
            up = len(dots) - 1
            if up > len(parts):
                continue
            base = parts[: len(parts) - up]
            if module:
                base.extend(module.split("."))
            found.update(_python_candidates(base))
            if not module:
                for name in re.findall(r"[A-Za-z_]\w*", names.split("#", 1)[0]):
                    found.update(_python_candidates([*base, name]))
        else:
            pieces = module.split(".")
            found.update(_python_candidates(pieces))
            for name in re.findall(r"[A-Za-z_]\w*", names.split("#", 1)[0]):
                found.update(_python_candidates([*pieces, name]))
    return found


def _python_candidates(parts: list[str]) -> set[str]:
    if not parts:
        return set()
    stem = "/".join(parts)
    return {f"{stem}.py", f"{stem}/__init__.py"}


def _js_imports(raw: str, path: str) -> set[str]:
    found: set[str] = set()
    parent = posixpath.dirname(path)
    for match in _JS_SPEC.finditer(raw):
        spec = match.group(1) or match.group(2)
        if not spec:
            continue
        base = posixpath.normpath(posixpath.join(parent, spec))
        if base.startswith("../") or base == "..":
            continue
        for ext in _JS_EXTS:
            found.add(f"{base}{ext}")
    return found