import { useState, type FormEvent } from "react";
import { packSource } from "./api";
import type { Compression, DigestFormat, PackResponse } from "./types";
import "./App.css";

export default function App() {
  const [source, setSource] = useState("");
  const [mode, setMode] = useState<Compression>("full");
  const [format, setFormat] = useState<DigestFormat>("markdown");
  const [maxTokens, setMaxTokens] = useState("");
  const [respectGitignore, setRespectGitignore] = useState(true);
  const [redactSecrets, setRedactSecrets] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PackResponse | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const parsed = maxTokens.trim() === "" ? null : Number(maxTokens);
      if (parsed !== null && (!Number.isInteger(parsed) || parsed < 1)) {
        throw new Error("Max tokens must be a positive integer.");
      }
      const packed = await packSource({
        source: source.trim(),
        mode,
        format,
        max_tokens: parsed,
        respect_gitignore: respectGitignore,
        redact_secrets: redactSecrets,
      });
      setResult(packed);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Pack failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <header>
        <h1>Contextpack</h1>
        <p>Pack a local folder or a Git URL into one LLM digest.</p>
      </header>

      <form onSubmit={onSubmit} className="panel">
        <label>
          Source
          <input
            value={source}
            onChange={(event) => setSource(event.target.value)}
            placeholder="D:\dev-tool-1\backend  or  owner/repo"
            required
          />
        </label>

        <div className="row">
          <label>
            Mode
            <select value={mode} onChange={(event) => setMode(event.target.value as Compression)}>
              <option value="full">full</option>
              <option value="skeleton">skeleton</option>
              <option value="outline">outline</option>
            </select>
          </label>
          <label>
            Format
            <select value={format} onChange={(event) => setFormat(event.target.value as DigestFormat)}>
              <option value="markdown">markdown</option>
              <option value="xml">xml</option>
              <option value="json">json</option>
            </select>
          </label>
          <label>
            Max tokens
            <input
              value={maxTokens}
              onChange={(event) => setMaxTokens(event.target.value)}
              inputMode="numeric"
              placeholder="optional"
            />
          </label>
        </div>

        <div className="checks">
          <label>
            <input
              type="checkbox"
              checked={respectGitignore}
              onChange={(event) => setRespectGitignore(event.target.checked)}
            />
            Respect .gitignore
          </label>
          <label>
            <input
              type="checkbox"
              checked={redactSecrets}
              onChange={(event) => setRedactSecrets(event.target.checked)}
            />
            Redact secrets
          </label>
        </div>

        <button type="submit" disabled={busy || source.trim() === ""}>
          {busy ? "Packing…" : "Pack"}
        </button>
      </form>

      {error ? <p className="error">{error}</p> : null}

      {result ? (
        <section className="result">
          <p className="stats">
            {result.files.length} files · {result.skipped.length} skipped · {result.total_bytes} bytes ·{" "}
            {result.total_tokens} tokens
          </p>
          <ul className="files">
            {result.files.map((file) => (
              <li key={file.path}>
                <code>{file.path}</code>
                <span>
                  {file.mode} · {file.tokens} tok · rank {Math.round(file.rank)}
                </span>
              </li>
            ))}
          </ul>
          <pre className="digest">{result.document}</pre>
        </section>
      ) : null}
    </main>
  );
}