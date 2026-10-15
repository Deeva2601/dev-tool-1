import type { Compression, DigestFormat, PackResponse } from "../../lib/types";

const KEY = "contextpack.history";
const LIMIT = 20;

export type HistoryFile = {
  path: string;
  tokens: number;
  mode: string;
};

export type HistoryEntry = {
  id: string;
  at: string;
  source: string;
  mode: Compression;
  format: DigestFormat;
  maxTokens: number | null;
  totalTokens: number;
  totalBytes: number;
  fileCount: number;
  skippedCount: number;
  files: HistoryFile[];
};

export type FileDiff = {
  added: string[];
  removed: string[];
  changed: { path: string; before: number; after: number }[];
};

export function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as HistoryEntry[]) : [];
  } catch {
    return [];
  }
}

export function rememberPack(
  source: string,
  mode: Compression,
  format: DigestFormat,
  maxTokens: number | null,
  result: PackResponse,
): HistoryEntry[] {
  const entry: HistoryEntry = {
    id: crypto.randomUUID(),
    at: new Date().toISOString(),
    source,
    mode,
    format,
    maxTokens,
    totalTokens: result.total_tokens,
    totalBytes: result.total_bytes,
    fileCount: result.files.length,
    skippedCount: result.skipped.length,
    files: result.files.map((file) => ({
      path: file.path,
      tokens: file.tokens,
      mode: file.mode,
    })),
  };
  const next = [entry, ...loadHistory()].slice(0, LIMIT);
  localStorage.setItem(KEY, JSON.stringify(next));
  return next;
}

export function clearHistory(): void {
  localStorage.removeItem(KEY);
}

export function diffFiles(older: HistoryFile[], newer: HistoryFile[]): FileDiff {
  const before = new Map(older.map((file) => [file.path, file.tokens]));
  const after = new Map(newer.map((file) => [file.path, file.tokens]));
  const added: string[] = [];
  const removed: string[] = [];
  const changed: FileDiff["changed"] = [];
  for (const [path, tokens] of after) {
    if (!before.has(path)) added.push(path);
    else if (before.get(path) !== tokens) {
      changed.push({ path, before: before.get(path) ?? 0, after: tokens });
    }
  }
  for (const path of before.keys()) {
    if (!after.has(path)) removed.push(path);
  }
  added.sort();
  removed.sort();
  changed.sort((a, b) => a.path.localeCompare(b.path));
  return { added, removed, changed };
}
