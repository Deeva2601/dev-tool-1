import { useEffect, useState, type FormEvent } from "react";
import {
  AlertCircle,
  Check,
  ChevronDown,
  GitBranch,
  FolderGit2,
  LoaderCircle,
  Search,
  ShieldCheck,
  Sparkles,
  Terminal,
} from "lucide-react";
import { packSource } from "../lib/api";
import type { Compression, DigestFormat, PackResponse } from "../lib/types";
import { ResultView } from "../features/result/ResultView";
import "./App.css";

const modes: { value: Compression; label: string; description: string }[] = [
  { value: "full", label: "Full context", description: "Code and documentation" },
  { value: "skeleton", label: "Skeleton", description: "Structure and signatures" },
  { value: "outline", label: "Outline", description: "Files and headings only" },
];

type HealthState = "checking" | "connected" | "unavailable";

export default function App() {
  const [source, setSource] = useState("");
  const [mode, setMode] = useState<Compression>("full");
  const [format, setFormat] = useState<DigestFormat>("markdown");
  const [maxTokens, setMaxTokens] = useState("");
  const [respectGitignore, setRespectGitignore] = useState(true);
  const [redactSecrets, setRedactSecrets] = useState(true);
  const [health, setHealth] = useState<HealthState>("checking");
  const [healthCheck, setHealthCheck] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PackResponse | null>(null);
  const [resultFormat, setResultFormat] = useState<DigestFormat>("markdown");

  useEffect(() => {
    let cancelled = false;
    let retryTimer: number;
    let requestController: AbortController | null = null;

    async function checkHealth() {
      const controller = new AbortController();
      requestController = controller;
      const requestTimeout = window.setTimeout(() => controller.abort(), 5000);
      try {
        const response = await fetch("/health", { signal: controller.signal });
        if (!cancelled) setHealth(response.ok ? "connected" : "unavailable");
      } catch {
        if (!cancelled) setHealth("unavailable");
      } finally {
        window.clearTimeout(requestTimeout);
        if (!cancelled) retryTimer = window.setTimeout(checkHealth, 10_000);
      }
    }

    void checkHealth();
    return () => {
      cancelled = true;
      requestController?.abort();
      window.clearTimeout(retryTimer);
    };
  }, [healthCheck]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedSource = source.trim();
    if (!trimmedSource) {
      setError("Add a local folder path or Git repository URL to continue.");
      return;
    }

    const tokenCount = maxTokens.trim() === "" ? null : Number(maxTokens);
    if (tokenCount !== null && (!Number.isInteger(tokenCount) || tokenCount < 1)) {
      setError("Maximum tokens must be a positive whole number.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const packed = await packSource({
        source: trimmedSource,
        mode,
        format,
        max_tokens: tokenCount,
        respect_gitignore: respectGitignore,
        redact_secrets: redactSecrets,
        focus: [],
        rules: [],
        entries: [],
      });
      setResult(packed);
      setResultFormat(format);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Packing failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  function resetOptions() {
    setMode("full");
    setFormat("markdown");
    setMaxTokens("");
    setRespectGitignore(true);
    setRedactSecrets(true);
  }

  function packAnother() {
    setResult(null);
    setError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <main className="app-shell">
      <div className="page-container">
        <header className="site-header">
          {result ? (
            <button className="brand-mark brand-button" onClick={packAnother} aria-label="Back to Contextpack setup">
              <BrandMark />
            </button>
          ) : (
            <a className="brand-mark" href="#home" aria-label="Contextpack home">
              <BrandMark />
            </a>
          )}
          {!result ? (
            <a href="#how-it-works" className="header-link">
              How it works <ChevronDown aria-hidden="true" />
            </a>
          ) : (
            <button className="secondary-button" type="button" onClick={packAnother}>
              <span aria-hidden="true">↺</span> Pack another repository
            </button>
          )}
        </header>

        {result ? (
          <ResultView result={result} format={resultFormat} onPackAnother={packAnother} />
        ) : (
          <>
            <section className="hero-grid" id="home">
              <div className="hero-copy">
                <p className="eyebrow"><Terminal aria-hidden="true" /> Repository context for AI</p>
                <h1 className="hero-title">Turn any codebase into <span>clear context.</span></h1>
                <p className="hero-description">
                  Pack a repository into a focused, token-counted digest your AI tools can actually use.
                </p>
                <div className={`health-pill health-${health}`} role="status" aria-live="polite">
                  {health === "checking" ? <LoaderCircle className="spin" aria-hidden="true" /> : null}
                  {health === "connected" ? <Check aria-hidden="true" /> : null}
                  {health === "unavailable" ? <AlertCircle aria-hidden="true" /> : null}
                  <span>
                    {health === "checking" ? "Checking the Contextpack service…" : null}
                    {health === "connected" ? "Service connected and ready" : null}
                    {health === "unavailable" ? "Service unavailable — start the backend to pack a repository" : null}
                  </span>
                  {health === "unavailable" ? (
                    <button
                      type="button"
                      onClick={() => {
                        setHealth("checking");
                        setHealthCheck((count) => count + 1);
                      }}
                    >
                      Retry
                    </button>
                  ) : null}
                </div>
              </div>
              <div className="hero-orb" aria-hidden="true">
                <div className="orb-grid">
                  <FolderGit2 />
                  <span>repo</span>
                  <span>context</span>
                  <span>ready</span>
                </div>
              </div>
            </section>

            <form onSubmit={onSubmit} className="workspace-card" id="create">
              <div className="workspace-heading">
                <div>
                  <p className="eyebrow">Create a digest</p>
                  <h2 className="section-title">Where should we start?</h2>
                </div>
                <span className="step-badge">01 / 01</span>
              </div>

              <label className="field-label" htmlFor="source">Repository source</label>
              <div className="source-input">
                <Search aria-hidden="true" />
                <input
                  id="source"
                  value={source}
                  onChange={(event) => setSource(event.target.value)}
                  placeholder="C:\path\to\project or https://github.com/org/repo"
                  autoComplete="off"
                  required
                />
                <GitBranch aria-hidden="true" />
              </div>
              <p className="field-hint">Use a local folder path or a public Git repository URL.</p>

              <div className="options-grid">
                <fieldset>
                  <legend className="field-label">Packing mode</legend>
                  <div className="option-stack">
                    {modes.map((item) => (
                      <label
                        key={item.value}
                        className={`option-card ${mode === item.value ? "option-selected" : ""}`}
                      >
                        <input
                          type="radio"
                          name="mode"
                          value={item.value}
                          checked={mode === item.value}
                          onChange={() => setMode(item.value)}
                        />
                        <span>
                          <strong>{item.label}</strong>
                          <small>{item.description}</small>
                        </span>
                      </label>
                    ))}
                  </div>
                </fieldset>

                <div className="advanced-fields">
                  <label className="field-label" htmlFor="format">Output format</label>
                  <select id="format" value={format} onChange={(event) => setFormat(event.target.value as DigestFormat)}>
                    <option value="markdown">Markdown</option>
                    <option value="xml">XML</option>
                    <option value="json">JSON</option>
                  </select>

                  <label className="field-label" htmlFor="tokens">Maximum tokens <span>(optional)</span></label>
                  <input
                    id="tokens"
                    type="number"
                    min="1"
                    step="1"
                    inputMode="numeric"
                    placeholder="No limit"
                    value={maxTokens}
                    onChange={(event) => setMaxTokens(event.target.value)}
                  />

                  <label className="check-row">
                    <input
                      type="checkbox"
                      checked={respectGitignore}
                      onChange={(event) => setRespectGitignore(event.target.checked)}
                    />
                    <span>Respect .gitignore</span>
                  </label>
                  <label className="check-row">
                    <input
                      type="checkbox"
                      checked={redactSecrets}
                      onChange={(event) => setRedactSecrets(event.target.checked)}
                    />
                    <span><ShieldCheck aria-hidden="true" /> Redact likely secrets</span>
                  </label>
                  <button className="reset-options" type="button" onClick={resetOptions}>Reset options</button>
                </div>
              </div>

              {error ? <div className="error-box" role="alert"><AlertCircle aria-hidden="true" />{error}</div> : null}

              <button className="primary-button pack-button" type="submit" disabled={busy || source.trim() === ""}>
                {busy ? <LoaderCircle className="spin" aria-hidden="true" /> : <Sparkles aria-hidden="true" />}
                {busy ? "Packing repository…" : "Create context digest"}
              </button>
              <p className="privacy-note"><ShieldCheck aria-hidden="true" /> Your settings are sent only to the Contextpack service.</p>
            </form>

            <section id="how-it-works" className="how-section">
              <div>
                <p className="eyebrow">Simple by design</p>
                <h2 className="section-title">From repository to ready-to-use context.</h2>
              </div>
              <div className="how-grid">
                <article><span>01</span><h3>Point to your code</h3><p>Start with a local project or Git repository URL.</p></article>
                <article><span>02</span><h3>Choose the signal</h3><p>Keep the full code, or create a lighter structural outline.</p></article>
                <article><span>03</span><h3>Share the digest</h3><p>Copy or download a token-counted context bundle.</p></article>
              </div>
            </section>

            <footer className="site-footer">Contextpack <span>•</span> Built for thoughtful AI-assisted development</footer>
          </>
        )}
      </div>
    </main>
  );
}

function BrandMark() {
  return (
    <>
      <span className="brand-mark-icon" aria-hidden="true">
        <span className="logo-slice logo-slice-a" />
        <span className="logo-slice logo-slice-b" />
        <span className="logo-dot" />
      </span>
      <span>Contextpack</span>
    </>
  );
}
