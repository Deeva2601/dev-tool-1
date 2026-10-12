from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

Compression = Literal["full", "skeleton", "outline"]


class PackConfig(BaseModel):
    root: Path
    output: Path | None = None
    max_file_bytes: int = 512_000
    respect_gitignore: bool = True
    extra_excludes: list[str] = Field(default_factory=list)
    mode: Compression = "full"
    focus: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    max_tokens: int | None = None
    entries: list[str] = Field(default_factory=list)


class FileRecord(BaseModel):
    relative_path: str
    size_bytes: int
    language: str
    content: str
    tokens: int
    applied_mode: str = "full"
    rank: float = 0.0


class PackResult(BaseModel):
    root: str
    files: list[FileRecord]
    skipped: list[str]
    tree: str
    markdown: str
    total_bytes: int
    total_tokens: int