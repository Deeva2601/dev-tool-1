export type Compression = "full" | "skeleton" | "outline";
export type DigestFormat = "markdown" | "xml" | "json";

export type PackRequest = {
  source: string;
  mode: Compression;
  format: DigestFormat;
  max_tokens: number | null;
  respect_gitignore: boolean;
  redact_secrets: boolean;
  focus: string[];
  rules: string[];
  entries: string[];
};

export type FileSummary = {
  path: string;
  language: string;
  bytes: number;
  tokens: number;
  mode: string;
  rank: number;
  content: string;
};

export type PackResponse = {
  root: string;
  document: string;
  files: FileSummary[];
  skipped: string[];
  total_bytes: number;
  total_tokens: number;
};

export type Preset = {
  name: string;
  mode: Compression;
  format: DigestFormat;
  maxTokens: string;
  respectGitignore: boolean;
  redactSecrets: boolean;
  focus: string;
  rules: string;
  entries: string;
};