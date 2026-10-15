import type { Preset } from "./types";

const KEY = "contextpack.presets";

export function loadPresets(): Preset[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as Preset[]) : [];
  } catch {
    return [];
  }
}

export function savePresets(presets: Preset[]): void {
  localStorage.setItem(KEY, JSON.stringify(presets));
}
