"""HTTP adapter. All packing still goes through pack_source."""

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from contextpack.compress import parse_rule
from contextpack.models import Compression, PackConfig
from contextpack.sources import SourceError, is_remote, pack_source

app = FastAPI(title="contextpack", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class PackRequest(BaseModel):
    source: str = Field(min_length=1, max_length=500)
    mode: Compression = "full"
    format: Literal["markdown", "xml", "json"] = "markdown"
    max_tokens: int | None = Field(default=None, ge=1)
    max_file_bytes: int = Field(default=512_000, ge=1, le=5_000_000)
    respect_gitignore: bool = True
    extra_excludes: list[str] = Field(default_factory=list)
    focus: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    entries: list[str] = Field(default_factory=list)
    redact_secrets: bool = True
    branch: str | None = None


class FileSummary(BaseModel):
    path: str
    language: str
    bytes: int
    tokens: int
    mode: str
    rank: float


class PackResponse(BaseModel):
    root: str
    document: str
    files: list[FileSummary]
    skipped: list[str]
    total_bytes: int
    total_tokens: int


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/pack", response_model=PackResponse)
def pack_endpoint(body: PackRequest) -> PackResponse:
    if not _local_allowed() and not is_remote(body.source):
        raise HTTPException(status_code=400, detail="Local paths are disabled on this server.")
    for rule in body.rules:
        try:
            parse_rule(rule)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    token = os.environ.get("CONTEXTPACK_TOKEN")
    config = PackConfig(
        root=Path("."),
        mode=body.mode,
        format=body.format,
        max_tokens=body.max_tokens,
        max_file_bytes=body.max_file_bytes,
        respect_gitignore=body.respect_gitignore,
        extra_excludes=body.extra_excludes,
        focus=body.focus,
        rules=body.rules,
        entries=body.entries,
        redact_secrets=body.redact_secrets,
    )
    try:
        result = pack_source(body.source, config, token=token, branch=body.branch)
    except (SourceError, NotADirectoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PackResponse(
        root=result.root,
        document=result.markdown,
        files=[
            FileSummary(
                path=item.relative_path,
                language=item.language,
                bytes=item.size_bytes,
                tokens=item.tokens,
                mode=item.applied_mode,
                rank=item.rank,
            )
            for item in result.files
        ],
        skipped=result.skipped,
        total_bytes=result.total_bytes,
        total_tokens=result.total_tokens,
    )


def _local_allowed() -> bool:
    return os.environ.get("CONTEXTPACK_ALLOW_LOCAL", "1") != "0"