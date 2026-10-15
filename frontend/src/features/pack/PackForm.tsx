import type { FormEvent } from "react";
import type { Compression, DigestFormat, Preset } from "../../lib/types";

export type PackFormValues = {
  source: string;
  mode: Compression;
  format: DigestFormat;
  maxTokens: string;
  respectGitignore: boolean;
  redactSecrets: boolean;
  focus: string;
  rules: string;
  entries: string;
  presets: Preset[];
  presetName: string;
  selectedPreset: string;
  busy: boolean;
};

export type PackFormHandlers = {
  setSource: (v: string) => void;
  setMode: (v: Compression) => void;
  setFormat: (v: DigestFormat) => void;
  setMaxTokens: (v: string) => void;
  setRespectGitignore: (v: boolean) => void;
  setRedactSecrets: (v: boolean) => void;
  setFocus: (v: string) => void;
  setRules: (v: string) => void;
  setEntries: (v: string) => void;
  setPresetName: (v: string) => void;
  setSelectedPreset: (v: string) => void;
  onSavePreset: () => void;
  onDeletePreset: () => void;
  onSubmit: (event: FormEvent) => void;
};

export function PackForm({
  values,
  handlers,
}: {
  values: PackFormValues;
  handlers: PackFormHandlers;
}) {
  const {
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
  } = values;
  const {
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
  } = handlers;

  return (
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
              if (found) {
                setMode(found.mode);
                setFormat(found.format);
                setMaxTokens(found.maxTokens);
                setRespectGitignore(found.respectGitignore);
                setRedactSecrets(found.redactSecrets);
                setFocus(found.focus);
                setRules(found.rules);
                setEntries(found.entries);
              }
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
  );
}
