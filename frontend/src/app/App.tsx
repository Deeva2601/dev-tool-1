import { useEffect, useState, type FormEvent } from "react";
import { lines } from "../lib/lines";
import { HistoryPanel } from "../features/history/HistoryPanel";
import { loadHistory, rememberPack, type HistoryEntry } from "../features/history/history";
import { packSource } from "../lib/api";
import { loadPresets, savePresets } from "../lib/presets";
import type { Compression, DigestFormat, PackResponse, Preset } from "../lib/types";
import { ResultView } from "../features/result/ResultView";
import { PackForm } from "../features/pack/PackForm";

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
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    setPresets(loadPresets());
  }, []);

    useEffect(() => {
    setPresets(loadPresets());
    setHistory(loadHistory());
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
      setHistory(
        rememberPack(
          source.trim(),
          mode,
          format,
          parsed,
          packed,
        ),
      );
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

      <PackForm
        values={{
          source,
          mode,
          format,
          maxTokens,
          respectGitignore,
          redactSecrets,
          focus,
          rules,
          entries,
          presets,
          presetName,
          selectedPreset,
          busy,
        }}
        handlers={{
          setSource,
          setMode,
          setFormat,
          setMaxTokens,
          setRespectGitignore,
          setRedactSecrets,
          setFocus,
          setRules,
          setEntries,
          setPresetName,
          setSelectedPreset,
          onSavePreset,
          onDeletePreset,
          onSubmit,
        }}
      />

      {error ? <p className="error">{error}</p> : null}

      {result ? <ResultView result={result} format={format} /> : null}
      <HistoryPanel history={history} result={result} onChange={setHistory} />

    </main>
  );
}
