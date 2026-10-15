import { useMemo, useState } from "react";
import { clearHistory, diffFiles, type HistoryEntry } from "./history";
import type { PackResponse } from "../../lib/types";

export function HistoryPanel({
  history,
  result,
  onChange,
}: {
  history: HistoryEntry[];
  result: PackResponse | null;
  onChange: (next: HistoryEntry[]) => void;
}) {
  const [selected, setSelected] = useState("");
  const older = history.find((item) => item.id === selected) ?? null;
  const diff = useMemo(() => {
    if (!older || !result) return null;
    return diffFiles(
      older.files,
      result.files.map((file) => ({ path: file.path, tokens: file.tokens, mode: file.mode })),
    );
  }, [older, result]);

  if (history.length === 0) return null;

  return (
    <section className="panel">
      <div className="toolbar">
        <h2>Recent packs</h2>
        <button
          type="button"
          onClick={() => {
            clearHistory();
            onChange([]);
            setSelected("");
          }}
        >
          Clear history
        </button>
      </div>
      <ul className="files">
        {history.map((item) => (
          <li key={item.id}>
            <button type="button" className="file-head" onClick={() => setSelected(item.id)}>
              <code>{item.source}</code>
              <span className="badges">
                <em>{item.mode}</em>
                <em>{item.fileCount} files</em>
                <em>{item.totalTokens} tok</em>
                <em>{new Date(item.at).toLocaleString()}</em>
              </span>
            </button>
          </li>
        ))}
      </ul>
      {diff && older ? (
        <div className="diff">
          <p className="stats">
            Compared with {older.source} · {new Date(older.at).toLocaleString()}
          </p>
          <DiffList title="Added" items={diff.added} />
          <DiffList title="Removed" items={diff.removed} />
          <h2>Token changes</h2>
          {diff.changed.length === 0 ? (
            <p className="muted">None</p>
          ) : (
            <ul className="skipped">
              {diff.changed.map((item) => (
                <li key={item.path}>
                  {item.path}: {item.before} → {item.after}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <p className="muted">Select a past pack to diff its file list against the current result.</p>
      )}
    </section>
  );
}

function DiffList({ title, items }: { title: string; items: string[] }) {
  return (
    <>
      <h2>
        {title} ({items.length})
      </h2>
      {items.length === 0 ? (
        <p className="muted">None</p>
      ) : (
        <ul className="skipped">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </>
  );
}
