Save this as `frontend/FRONTEND.md` and send her that file.

```md
# Contextpack frontend

Guide for anyone changing the UI. The product already works in production. Your job is look, layout, and clarity. Do not change how packing works.

## What this screen does

A person pastes a GitHub repo (`owner/repo` or a full GitHub URL). They pick how aggressive the digest should be, then press Pack. The page shows:

- a short summary (file count, skipped count, bytes, tokens)
- each included file, openable, with syntax highlighting
- badges: compression mode, token count, rank
- the skipped-file list
- a side panel of agent instructions
- buttons: copy digest, download the digest, download `AGENTS.md`
- saved presets (this browser only)
- recent packs and a file-list diff against the current result

The backend does the real work (clone, ignore rules, skeleton, token budget). The frontend only sends one POST and renders the JSON.

## How the pieces talk

```text
Browser (Vite, port 5173 in dev)
    POST /pack
        |
        |  dev: Vite proxy
        v
FastAPI (port 8000)
    clones the repo, packs it, returns JSON
```

In production there is no Vite server. FastAPI serves the built files in `frontend/dist` and the same page calls `POST /pack` on the same host. Do not add a hardcoded `http://localhost:8000` in the UI. `fetch("/pack")` is correct in both dev and production.

## Run it on your machine

You need two terminals.

Terminal 1, API:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:CONTEXTPACK_ALLOW_LOCAL = "1"
uvicorn contextpack.api:app --app-dir src --reload --port 8000
```

`ALLOW_LOCAL=1` is only for your laptop, so you can pack a folder on disk. Production sets this to `0`. Never commit that as `0`→`1` in a way that ships.

Terminal 2, UI:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

Check `frontend/vite.config.ts`. It must keep this proxy:

```ts
proxy: {
  "/health": "http://127.0.0.1:8000",
  "/pack": "http://127.0.0.1:8000",
}
```

If the form loads but Pack fails with "failed to fetch", the API is not running.

## Stack — do not replace it

| Piece | Choice |
|---|---|
| Build | Vite |
| UI | React + TypeScript |
| Highlighting | `highlight.js` (already installed) |
| Router | none |
| State library | none (`useState` only) |
| CSS framework | none (plain CSS) |
| Backend | do not edit it for a visual change |

Add a dependency only if the team agrees. A font from Google Fonts in `index.html`, or a small icon set, is fine. Replacing the app with Next.js, Tailwind-by-rewriting-everything, or a component kit in the first PR is not.

## Where to edit

Code lives under `frontend/src/`. Two layouts are valid. Use whichever is in the repo when you clone.

### If files are still flat

| File | What you may change | What you must not change |
|---|---|---|
| `App.tsx` | layout, labels, grouping of fields | field names sent to the API, when `packSource` is called, `rememberPack` after success |
| `App.css` | all visual design | — |
| `ResultView.tsx` | how files, badges, buttons, and the agent panel look | highlight/copy/download behavior |
| `HistoryPanel.tsx` | how history and the diff look | diff rules (added / removed / token change) |
| `main.tsx` | leave it | mounts `<App />` only |
| `api.ts` | leave it | `POST /pack` |
| `types.ts` | leave it unless the API grew a field | request and response shapes |
| `presets.ts`, `history.ts` | leave the storage format | keys below |
| `highlight.ts`, `download.ts`, `agentText.ts`, `lines.ts` | leave them | — |

### If the folder was already split

| Path | Owns |
|---|---|
| `app/App.tsx` | puts the form, result, and history on the page |
| `app/App.css` | visual design |
| `features/pack/PackForm.tsx` | every input |
| `features/result/ResultView.tsx` | digest UI |
| `features/history/HistoryPanel.tsx` | recent packs and diff |
| `lib/api.ts`, `lib/types.ts` | do not restyle these; they are not UI |

Same rule: move JSX and CSS. Do not rename JSON fields.

## What the form sends

`POST /pack` with JSON:

| Field | UI control | Notes |
|---|---|---|
| `source` | text, required | `owner/repo` or `https://github.com/owner/repo` |
| `mode` | select | `full`, `skeleton`, or `outline` |
| `format` | select | `markdown`, `xml`, or `json` |
| `max_tokens` | text, optional | empty means no cap; otherwise a positive integer |
| `respect_gitignore` | checkbox | default on |
| `redact_secrets` | checkbox | default on |
| `focus` | textarea | one glob per line, files kept in full |
| `rules` | textarea | one per line, `glob=full`, `glob=skeleton`, or `glob=outline`. First match wins |
| `entries` | textarea | one extra entrypoint path per line |

Presets save those controls except `source`. They are not accounts. They live in this browser only.

localStorage keys, do not rename:

- `contextpack.presets`
- `contextpack.history`

History stores path, mode, and token count per file. It does **not** store file contents or the full digest. A big repo would blow the browser quota. When you redraw history, keep it that way.

## What the API returns

Use these. Do not invent fields.

| Field | Use in the UI |
|---|---|
| `document` | the full digest string (copy + download) |
| `files[]` | list rows. Each has `path`, `language`, `bytes`, `tokens`, `mode`, `rank`, `content` |
| `skipped[]` | human-readable skip reasons |
| `total_bytes`, `total_tokens` | summary line |
| `root` | folder name on the server; usually not worth showing |

Errors: the API returns `{ "detail": "..." }`. Show `detail`. Do not replace it with a generic "Something went wrong" unless `detail` is missing.

## Safe UI changes

All of these are in-scope and do not need a backend change:

- Typography, color, spacing, dark/light, empty states
- Clearer labels and one-line help under Focus, Rules, and Entrypoints
- A better layout on a phone (the form is already a single column under 720px; improve it, do not remove the breakpoint)
- Reordering sections (summary, files, skipped, agent panel)
- Loading state while `busy` is true (Pack already disables the button)
- Showing the error closer to the field that caused it
- Keyboard: Enter submits, Esc closes an open file — only if Pack still submits once

## Do not do these in a UI PR

- Change `fetch("/pack")` to another path or host
- Remove the Vite proxy
- Store `document` or `file.content` in `localStorage`
- Add login, a database, or a new backend route
- Change preset or history JSON shape (old browsers would break)
- Turn off secret redaction or gitignore by default
- Deploy with `CONTEXTPACK_ALLOW_LOCAL=1`

## Check your work

```powershell
cd frontend
npm run build
```

Then, with the API running:

1. Pack a small public repo, for example `octocat/Hello-World` or `owner/repo`.
2. Open one file. Highlighting still appears.
3. Copy digest, download the digest, download `AGENTS.md`.
4. Save a preset, reload the page, load that preset. Fields come back. Source stays empty.
5. Pack again with a focus glob. History shows both runs. Diff lists added and removed paths.
6. Resize below 720px. Nothing overlaps.

If `npm run build` fails, the PR is not ready. Production builds this folder inside Docker.

## How to contribute

1. Branch from the default branch: `git checkout -b ui/<short-name>`.
2. Change only `frontend/` unless a maintainer asked for more.
3. Keep TypeScript strict. No `any`.
4. Match the existing style: function components, no new global state.
5. Open a PR that says what changed visually and confirms `npm run build` passed.
6. Do not commit `node_modules/` or `dist/`.

A good first PR is visual only: spacing, type, colors, and clearer helper text on Focus / Rules / Entrypoints, with screenshots of desktop and a narrow window.
```