# Contextpack

> Turn any GitHub repository — or a local folder — into a single, token-counted digest that fits inside an LLM context window.

---

## Table of contents

1. [What it does](#what-it-does)
2. [How it works — end to end](#how-it-works--end-to-end)
3. [Architecture](#architecture)
   - [Request flow](#request-flow)
   - [Backend pipeline](#backend-pipeline)
   - [Frontend layout](#frontend-layout)
   - [Production serving](#production-serving)
4. [Repository layout](#repository-layout)
5. [Environment variables](#environment-variables)
6. [Contributing](#contributing)
   - [Prerequisites](#prerequisites)
   - [Run locally](#run-locally)
   - [Project rules](#project-rules)
   - [Backend changes](#backend-changes)
   - [Frontend changes](#frontend-changes)
   - [Opening a pull request](#opening-a-pull-request)
   - [First-PR ideas](#first-pr-ideas)

---

## What it does

A user pastes `owner/repo` (or a full `https://github.com/...` URL) into the web form and presses **Pack**. The server:

1. Shallow-clones the repository (or reads the local folder).
2. Discovers every source file, respects `.gitignore`, and redacts secrets.
3. Ranks files by likely relevance using import-graph analysis.
4. Applies a compression mode — **full** (verbatim), **skeleton** (signatures only), or **outline** (names only) — per-file or globally.
5. Fits everything inside an optional token budget, dropping lowest-ranked files first.
6. Serialises the result as **Markdown**, **XML**, or **JSON**.

The browser receives one JSON object and renders it: collapsible file list with syntax highlighting, skipped-file list, copy/download buttons, a ready-made `AGENTS.md`, saved presets, and a history panel with file-level diffs between runs.

---

## How it works — end to end

```
User browser (port 5173 in dev, same origin in prod)
  |
  |  POST /pack   { source, mode, format, max_tokens, ... }
  |
  v
FastAPI  (port 8000)
  |
  +-- sources.py      resolve local path or git-clone to a temp dir
  +-- discover.py     walk files, apply gitignore + exclude globs
  +-- secrets.py      redact tokens, keys, passwords
  +-- compress.py     choose mode per file from --rule globs
  +-- skeleton.py     tree-sitter: strip bodies to signatures or names
  +-- tokens.py       tiktoken: count tokens per file
  +-- rank.py         score files by import/reference centrality
  +-- budget.py       drop lowest-ranked files until under max_tokens
  +-- formatters.py   render markdown / xml / json document
  +-- api.py          validate, rate-limit, shape the HTTP response
  |
  |  JSON  { root, document, files[], skipped[], total_bytes, total_tokens }
  |
  v
Browser renders result
  +-- ResultView     collapsible files, highlight.js, copy/download digest
  +-- HistoryPanel   last 20 packs, file-list diff against current
  +-- PackForm       all inputs, preset save/load/delete
```

---

## Architecture

### Request flow

```
                 +---------------------------+
                 |  Browser                  |
                 |  React + Vite             |
                 |  fetch("/pack", ...)      |
                 +-------------+-------------+
                               |
                               | POST /pack (JSON)
              dev: Vite proxy  |
              prod: same host  |
                               v
                 +---------------------------+
                 |  FastAPI  (port 8000)     |
                 |  api.py                  |
                 |  - rate-limit (limiter)  |
                 |  - validate source type  |
                 |  - build PackConfig      |
                 +-------------+-------------+
                               |
                               v
                 +---------------------------+
                 |  sources.py              |
                 |  local dir  OR           |
                 |  git clone -> temp dir   |
                 +-------------+-------------+
                               |
                               v
                 +---------------------------+
                 |  pipeline.pack()         |
                 |  (see pipeline table)    |
                 +-------------+-------------+
                               |  PackResult
                               v
                 +---------------------------+
                 |  api.py shapes response  |
                 |  PackResponse JSON       |
                 +---------------------------+
```

### Backend pipeline

Each call to `pipeline.pack()` runs these stages in order:

| Stage | Module | What it does |
|---|---|---|
| **Discover** | `discover.py` | Walk the directory tree. Skip files matching `.gitignore` or above `max_file_bytes`. Detect language from extension. |
| **Redact** | `secrets.py` | Regex-replace tokens, passwords, and API keys with `[REDACTED]`. |
| **Compress** | `compress.py` | Apply the compression mode. `full` = verbatim. `skeleton` = strip function/method bodies via tree-sitter (Python, JS, TS). `outline` = keep only names and signatures. Per-file rules override the global mode. |
| **Rank** | `rank.py` | Score each file by how many other files import it (import-graph centrality). Files in the `focus` list get a pinned high score. |
| **Budget** | `budget.py` | Count tokens with tiktoken. If `max_tokens` is set, drop the lowest-ranked files until the total fits. |
| **Format** | `formatters.py` | Render the final document — a directory tree header followed by every kept file's content — as Markdown, XML, or JSON. |

### Frontend layout

```
frontend/src/
  main.tsx                     — mounts <App />
  app/
    App.tsx                    — all state, submit logic, history recording
    App.css                    — all styles (single file, no framework)
  features/
    pack/
      PackForm.tsx             — every form input; receives state + setters as props
    result/
      ResultView.tsx           — digest toolbar, file list, skipped list, agent panel
      highlight.ts             — highlight.js wrapper (language registration + aliases)
      download.ts              — downloadText / copyText helpers
      agentText.ts             — builds the AGENTS.md string
    history/
      HistoryPanel.tsx         — recent packs list and file-diff view
      history.ts               — localStorage load / save / diff logic
  lib/
    api.ts                     — packSource(): the single fetch("/pack") call
    lines.ts                   — splits textarea text into a non-empty line array
    presets.ts                 — localStorage preset load/save
    types.ts                   — shared TypeScript types (mirrors API schema)
```

**State lives in `App.tsx`.** `PackForm` receives every field value and setter as props. `rememberPack` is called in `App.tsx` after a successful pack so history is always recorded at the same level as `packSource`. Do not move that call.

### Production serving

The `dockerfile` uses a two-stage build:

```
Stage 1  node:22-alpine
  COPY frontend/package*.json  ->  npm ci
  COPY frontend/               ->  npm run build
  Output: frontend/dist/

Stage 2  python:3.12-slim
  COPY backend/
  COPY --from=stage1 frontend/dist  ->  /app/frontend/dist
  pip install -e .
  ENV CONTEXTPACK_STATIC=/app/frontend/dist
  CMD uvicorn contextpack.api:app ...
```

FastAPI's `_mount_frontend()` in `api.py` serves `/assets/*` as static files and catches every other path with a catch-all that returns `index.html`. There is no separate static server in production. **`fetch("/pack")` is correct** — no base URL, no port number.

---

## Repository layout

```
dev-tool-1/
  dockerfile              two-stage Docker build (do not edit)
  README.md               this file
  backend/
    pyproject.toml        Python package metadata and dependencies
    src/contextpack/
      api.py              FastAPI app, /health and /pack endpoints
      budget.py           token-budget trimming
      cli.py              Typer CLI  (contextpack pack ...)
      compress.py         mode selection and rule parsing
      discover.py         file walker, gitignore, language detection
      formatters.py       Markdown / XML / JSON document rendering
      limits.py           in-memory rate limiter
      models.py           Pydantic models: PackConfig, FileRecord, PackResult
      pipeline.py         orchestrates all stages into pack()
      rank.py             import-graph ranking
      secrets.py          secret redaction
      skeleton.py         tree-sitter skeleton / outline extraction
      sources.py          local-path resolve + git-clone
      tokens.py           tiktoken wrapper
    tests/                pytest test suite
  frontend/
    vite.config.ts        Vite config + dev proxy (do not remove)
    src/                  see Frontend layout above
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `CONTEXTPACK_ALLOW_LOCAL` | `1` dev / `0` Docker | Set to `1` to allow local directory paths. Never ship `1` in production. |
| `CONTEXTPACK_TOKEN` | — | GitHub personal access token for private repos. Use the env var, not the CLI flag. |
| `CONTEXTPACK_STATIC` | auto-detected | Path to the built `frontend/dist/` directory FastAPI serves. |
| `CONTEXTPACK_MAX_FILES` | `2000` | Hard cap on files per pack request. |
| `CONTEXTPACK_CLONE_TIMEOUT` | `60` | Seconds before a `git clone` is killed. |
| `CONTEXTPACK_MAX_DOCUMENT_CHARS` | `2000000` | Maximum characters allowed in the rendered digest. |
| `PORT` | `8000` | Port uvicorn listens on (used in the Docker CMD). |

---

## Contributing

### Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | >= 3.11 | Use a virtual environment |
| Node.js | >= 22 | LTS recommended |
| git | any recent | Required at runtime for cloning |
| uv *(optional)* | any | Faster than pip for backend setup |

### Run locally

You need **two terminals** running at the same time.

**Terminal 1 — API**

```powershell
cd backend

# create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1       # Windows PowerShell
# source .venv/bin/activate        # macOS / Linux

# install the package in editable mode with dev extras
pip install -e ".[dev]"

# allow local directory sources (laptop only — never commit this to prod)
$env:CONTEXTPACK_ALLOW_LOCAL = "1"

uvicorn contextpack.api:app --app-dir src --reload --port 8000
```

**Terminal 2 — UI**

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/pack` and `/health` to `http://127.0.0.1:8000` automatically — no extra config needed.

> **Troubleshooting:** If the form loads but Pack returns "failed to fetch", the API in Terminal 1 is not running or crashed. Check its output.

**CLI (no browser needed)**

```powershell
cd backend
.\.venv\Scripts\Activate.ps1

# pack a local folder and print to stdout
contextpack pack .

# save to a file with skeleton compression
contextpack pack owner/repo --mode skeleton --output digest.md

# also write a sibling AGENTS.md
contextpack pack owner/repo --output digest.md --agent

# cap at 60 000 tokens, XML output
contextpack pack owner/repo --max-tokens 60000 --format xml --output digest.xml
```

**Run backend tests**

```powershell
cd backend
pytest
```

---

### Project rules

These apply to every change in the repository.

1. **Do not change the public API shape.** Request fields (`source`, `mode`, `format`, `max_tokens`, `respect_gitignore`, `redact_secrets`, `focus`, `rules`, `entries`) and response fields (`root`, `document`, `files[].path/language/bytes/tokens/mode/rank/content`, `skipped`, `total_bytes`, `total_tokens`) are the contract between frontend and backend. Rename them only when every caller is updated in the same commit.
2. **Do not edit the `dockerfile`.** Production depends on the exact `COPY frontend/` + `npm ci` + `npm run build` sequence.
3. **`fetch("/pack")` stays as-is.** No hardcoded hostnames or ports.
4. **localStorage keys are fixed:** `contextpack.presets` and `contextpack.history`. Changing them silently breaks existing users' saved data.
5. **History never stores file bodies or the full digest.** Only `path`, `tokens`, and `mode` per file. Large repos would blow browser storage quotas.
6. **TypeScript strict mode is on.** No `any`. No type assertions that hide real errors.
7. **No new dependencies without team agreement.** The frontend stack is intentionally minimal (React, Vite, highlight.js). The backend already pulls in everything it needs.

---

### Backend changes

Branch from the default branch and scope changes to `backend/`.

```powershell
git checkout -b backend/<short-description>
```

Checklist before opening a PR:

- [ ] `pytest` passes with no new failures.
- [ ] If you added or changed a pipeline stage, update the **Backend pipeline** table in this README.
- [ ] If you added or renamed a field in `PackRequest` or `PackResponse`, update `frontend/src/lib/types.ts` in the same commit.
- [ ] Secret-redaction defaults (`redact_secrets=True`) and gitignore defaults (`respect_gitignore=True`) must not be flipped.
- [ ] `CONTEXTPACK_ALLOW_LOCAL` defaults to `"0"` in production code paths; `"1"` is for local dev only.

---

### Frontend changes

Branch from the default branch and scope changes to `frontend/`.

```powershell
git checkout -b ui/<short-description>
```

**Where to look:**

| I want to change... | Edit this file |
|---|---|
| Form inputs, labels, preset controls | `features/pack/PackForm.tsx` |
| File list, badges, copy/download buttons | `features/result/ResultView.tsx` |
| History list and diff view | `features/history/HistoryPanel.tsx` |
| Colors, spacing, typography, layout | `app/App.css` |
| Submit logic, state wiring | `app/App.tsx` — change carefully |
| API call | `lib/api.ts` — only change with a matching backend change |

Checklist before opening a PR:

- [ ] `npm run build` (inside `frontend/`) completes with zero TypeScript errors.
- [ ] Pack a small public repo — `octocat/Hello-World` works. Result renders correctly.
- [ ] Open a file. Syntax highlighting appears.
- [ ] Copy digest, download the digest, download `AGENTS.md` all work.
- [ ] Save a preset, reload the page, select it — fields restore. `source` stays empty (presets do not store the source).
- [ ] Pack twice — history shows both runs, diff lists added and removed paths.
- [ ] Resize the browser below 720 px — nothing overlaps or clips.
- [ ] `node_modules/` and `dist/` are not in the commit.

---

### Opening a pull request

1. **Title:** `[backend]` or `[ui]` prefix, then a short imperative phrase.
   - `[ui] Add helper text under Focus and Rules fields`
   - `[backend] Add YAML language detection`
2. **Description** should cover:
   - What changed and why.
   - For UI PRs: a screenshot at normal desktop width and one at 375 px.
   - A line confirming `npm run build` (UI) or `pytest` (backend) passed locally.
3. **Scope:** Change only the folder matching your branch prefix unless a maintainer explicitly asked for more.
4. **One concern per PR.** A visual polish PR should not also change pipeline logic.

---

### First-PR ideas

Good starting points — all purely visual, no API or pipeline changes needed:

- **Better field help text** — add a short description under the Focus, Rules, and Entrypoints textareas explaining the expected format (`glob=skeleton`, one per line, etc.).
- **Empty state** — show a friendly message in the file list when a pack returns zero included files.
- **Loading indicator** — add a spinner or animated text while `busy` is true. The Pack button is already disabled; this is a pure CSS/JSX change.
- **Mobile layout polish** — the form is already single-column under 720 px. Improve padding, touch target sizes, and label spacing on a real phone screen.
- **Skipped count badge** — show the skipped file count on the Skipped section heading so users notice it without scrolling.
