"""Pick full, skeleton, or outline text for one file."""

import pathspec

from contextpack.models import Compression, PackConfig
from contextpack.skeleton import outline, skeletonize

_MODES = {"full", "skeleton", "outline"}


def parse_rule(raw: str) -> tuple[str, Compression]:
    if "=" not in raw:
        raise ValueError(f"Rule must be PATTERN=MODE, got {raw!r}")
    pattern, mode = raw.rsplit("=", 1)
    pattern = pattern.strip()
    mode = mode.strip()
    if not pattern or mode not in _MODES:
        raise ValueError(f"Rule must be PATTERN=full|skeleton|outline, got {raw!r}")
    return pattern, mode  # type: ignore[return-value]


def _matches(patterns: list[str], relative: str) -> bool:
    if not patterns:
        return False
    spec = pathspec.PathSpec.from_lines("gitignore", patterns)
    return bool(spec.match_file(relative))


def mode_for(relative: str, config: PackConfig) -> Compression:
    for pattern, mode in (parse_rule(rule) for rule in config.rules):
        if _matches([pattern], relative):
            return mode
    if _matches(config.focus, relative):
        return "full"
    return config.mode

def is_focus_pinned(relative: str, config: PackConfig) -> bool:
    """True when focus, not a rule, is what selected this file's mode."""
    for pattern, _mode in (parse_rule(rule) for rule in config.rules):
        if _matches([pattern], relative):
            return False
    return _matches(config.focus, relative)


def compress(source: str, language: str, mode: Compression) -> str:
    if mode == "full":
        return source
    if mode == "skeleton":
        return skeletonize(source, language)
    return outline(source, language)