from pathlib import Path

import pathspec

# Directories and files that are never useful as model context.
DEFAULT_EXCLUDES = [
    ".git/",
    ".hg/",
    ".svn/",
    ".idea/",
    ".vscode/",
    "node_modules/",
    "vendor/",
    "dist/",
    "build/",
    "coverage/",
    ".next/",
    ".nuxt/",
    ".venv/",
    "venv/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "*.pyc",
    "*.pyo",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
    "Cargo.lock",
    "poetry.lock",
    "Pipfile.lock",
    "composer.lock",
    "Gemfile.lock",
]

BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".svgz",
    ".pdf", ".zip", ".tar", ".gz", ".tgz", ".bz2", ".7z", ".rar",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp3", ".mp4", ".mov", ".avi", ".webm", ".wav",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".wasm",
    ".sqlite", ".db", ".parquet", ".class", ".jar",
}

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".swift": "swift",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
}


def language_for(path: Path) -> str:
    return LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "text")


def load_spec(root: Path, respect_gitignore: bool, extra: list[str]) -> pathspec.PathSpec:
    lines = list(DEFAULT_EXCLUDES)
    lines.extend(extra)
    if respect_gitignore:
        gitignore = root / ".gitignore"
        if gitignore.is_file():
            lines.extend(gitignore.read_text(encoding="utf-8", errors="replace").splitlines())
    return pathspec.PathSpec.from_lines("gitignore", lines)


def is_binary(path: Path) -> bool:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return True
    try:
        sample = path.read_bytes()[:8192]
    except OSError:
        return True
    return b"\x00" in sample


def iter_source_files(root: Path, spec: pathspec.PathSpec, max_file_bytes: int):
    """Yield (absolute_path, relative_posix) for text files under root.

    Skipped relative paths are yielded as the third value when the file is rejected.
    """
    root = root.resolve()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if spec.match_file(relative):
            yield None, relative, "ignored"
            continue
        try:
            size = path.stat().st_size
        except OSError:
            yield None, relative, "unreadable"
            continue
        if size > max_file_bytes:
            yield None, relative, f"oversize:{size}"
            continue
        if is_binary(path):
            yield None, relative, "binary"
            continue
        yield path, relative, None