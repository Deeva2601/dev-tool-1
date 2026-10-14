import { useEffect, useState, type FormEvent } from "react";
import { lines } from "./lines";
import { packSource } from "./api";
import { loadPresets, savePresets } from "./presets";
import type { Compression, DigestFormat, PackResponse, Preset } from "./types";
import { ResultView } from "./ResultView.tsx";
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
  const [focus, setFocus] = useState("");
  const [rules, setRules] = useState("");
  const [entries, setEntries] = useState("");
  const [presets, setPresets] = useState<Preset[]>([]);
  const [presetName, setPresetName] = useState("");
  const [selectedPreset, setSelectedPreset] = useState("");

  useEffect(() => {
    setPresets(loadPresets());
  }, []);

  function currentPreset(name: string): Preset {
    return {
      name,
      mode,
      format,
      maxTokens,
      respectGitignore,
      redactSecrets,
      focus,
      rules,
      entries,
    };
  }

  function applyPreset(preset: Preset) {
    setMode(preset.mode);
    setFormat(preset.format);
    setMaxTokens(preset.maxTokens);
    setRespectGitignore(preset.respectGitignore);
    setRedactSecrets(preset.redactSecrets);
    setFocus(preset.focus);
    setRules(preset.rules);
    setEntries(preset.entries);
  }

  function onSavePreset() {
    const name = presetName.trim();
    if (!name) return;
    const next = [...presets.filter((item) => item.name !== name), currentPreset(name)];
    setPresets(next);
    savePresets(next);
    setSelectedPreset(name);
  }

  function onDeletePreset() {
    const next = presets.filter((item) => item.name !== selectedPreset);
    setPresets(next);
    savePresets(next);
    setSelectedPreset("");
  }

  
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
        focus: lines(focus),
        rules: lines(rules),
        entries: lines(entries),
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
                <label>
          Focus globs (one per line, kept verbatim)
          <textarea value={focus} onChange={(event) => setFocus(event.target.value)} rows={3} placeholder={"src/main.py"} />
        </label>
        <label>
          Rules (one per line, first match wins)
          <textarea
            value={rules}
            onChange={(event) => setRules(event.target.value)}
            rows={3}
            placeholder={"src/hot.py=outline\nsrc/**=skeleton"}
          />
        </label>
        <label>
          Extra entrypoints
          <textarea value={entries} onChange={(event) => setEntries(event.target.value)} rows={2} placeholder={"src/cli.py"} />
        </label>

        <div className="row">
          <label>
            Preset
            <select
              value={selectedPreset}
              onChange={(event) => {
                const name = event.target.value;
                setSelectedPreset(name);
                const found = presets.find((item) => item.name === name);
                if (found) applyPreset(found);
              }}
            >
              <option value="">Select</option>
              {presets.map((item) => (
                <option key={item.name} value={item.name}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Preset name
            <input value={presetName} onChange={(event) => setPresetName(event.target.value)} placeholder="review" />
          </label>
          <div className="actions preset-actions">
            <button type="button" onClick={onSavePreset} disabled={presetName.trim() === ""}>
              Save preset
            </button>
            <button type="button" onClick={onDeletePreset} disabled={selectedPreset === ""}>
              Delete
            </button>
          </div>
        </div>

        <button type="submit" disabled={busy || source.trim() === ""}>
          {busy ? "Packing…" : "Pack"}
        </button>
      </form>

      {error ? <p className="error">{error}</p> : null}

      {result ? <ResultView result={result} format={format} /> : null}

    </main>
  );
}