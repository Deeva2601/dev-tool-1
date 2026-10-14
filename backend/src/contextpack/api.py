"""HTTP adapter. All packing still goes through pack_source."""

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextpack.compress import parse_rule
from contextpack.models import Compression, PackConfig
from contextpack.limits import limiter
from contextpack.sources import SourceError, is_public_github, is_remote, pack_source

MAX_FILES = int(os.environ.get("CONTEXTPACK_MAX_FILES", "2000"))
CLONE_TIMEOUT = int(os.environ.get("CONTEXTPACK_CLONE_TIMEOUT", "60"))
MAX_DOCUMENT_CHARS = int(os.environ.get("CONTEXTPACK_MAX_DOCUMENT_CHARS", "2000000"))


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
    content: str



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

def pack_endpoint(body: PackRequest,request: Request) -> PackResponse:
    client = request.client.host if request.client else "unknown"
    if not limiter.allow(client):
        raise HTTPException(status_code=429, detail="Too many pack requests. Try again in a minute.")

    remote = is_remote(body.source)

    # When local paths are disabled we only accept public GitHub URLs.
    if not _local_allowed():
        # If the request is a local directory, reject with a clear message.
        if not remote:
            raise HTTPException(
                status_code=400,
                detail="Local paths are disabled on this server.",
            )
        # If the request is remote but not a public GitHub URL, reject.
        if not is_public_github(body.source):
            raise HTTPException(
                status_code=400,
                detail="Only https://github.com/owner/repo is accepted on this server.",
            )

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
        result = pack_source(
            body.source,
            config,
            token=token,
            branch=body.branch,
            timeout=CLONE_TIMEOUT if remote else None,
        )
    except (SourceError, NotADirectoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if len(result.files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Pack has {len(result.files)} files; limit is {MAX_FILES}.",
        )
    if len(result.markdown) > MAX_DOCUMENT_CHARS:
        raise HTTPException(
            status_code=400,
            detail="Digest is larger than the server limit. Lower max tokens.",
        )

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
                content=item.content,
            )
            for item in result.files
        ],
        skipped=result.skipped,
        total_bytes=result.total_bytes,
        total_tokens=result.total_tokens,
    )

    # Duplicate response block removed – retained the earlier PackResponse implementation.


def _local_allowed() -> bool:
    return os.environ.get("CONTEXTPACK_ALLOW_LOCAL", "1") != "0"


_STATIC = Path(
    os.environ.get(
        "CONTEXTPACK_STATIC",
        str(Path(__file__).resolve().parents[3] / "frontend" / "dist"),
    )
).resolve()


def _mount_frontend() -> None:
    if not (_STATIC / "index.html").is_file():
        return
    assets = _STATIC / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend(full_path: str) -> FileResponse:
        if full_path:
            candidate = (_STATIC / full_path).resolve()
            if candidate.is_file() and _STATIC in candidate.parents:
                return FileResponse(candidate)
        return FileResponse(_STATIC / "index.html")


_mount_frontend()