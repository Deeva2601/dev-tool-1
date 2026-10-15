import { useMemo, useState } from "react";
import {
  Check,
  ChevronDown,
  ChevronRight,
  Clipboard,
  Download,
  FileCode2,
  PackageCheck,
  RotateCcw,
  WandSparkles,
} from "lucide-react";
import { agentText } from "./agentText";
import { copyText, downloadText } from "./download";
import { highlight } from "./highlight";
import type { DigestFormat, FileSummary, PackResponse } from "../../lib/types";

const EXTENSION: Record<DigestFormat, string> = {
  markdown: "md",
  xml: "xml",
  json: "json",
};

const MIME: Record<DigestFormat, string> = {
  markdown: "text/markdown",
  xml: "application/xml",
  json: "application/json",
};

export function ResultView({
  result,
  format,
  onPackAnother,
}: {
  result: PackResponse;
  format: DigestFormat;
  onPackAnother: () => void;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const digestName = `contextpack.${EXTENSION[format]}`;
  const instructions = useMemo(() => agentText(result, digestName), [result, digestName]);

  async function handleCopy() {
    try {
      await copyText(result.document);
      setNotice("Digest copied to clipboard.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not copy the digest.");
    }
  }

  return (
    <main className="results-page">
      <section className="results-intro">
        <div>
          <p className="eyebrow">Digest ready</p>
          <h1 className="page-title">Your repository context is packed.</h1>
          <p className="results-description">
            Review the generated digest, inspect included files, or download a ready-to-share context bundle.
          </p>
        </div>
        <div className="results-actions">
          <button className="secondary-button" type="button" onClick={handleCopy}>
            <Clipboard aria-hidden="true" /> Copy digest
          </button>
          <button
            className="primary-button"
            type="button"
            onClick={() => downloadText(digestName, result.document, MIME[format])}
          >
            <Download aria-hidden="true" /> Download digest
          </button>
        </div>
      </section>

      {notice ? <p className="result-notice" role="status">{notice}</p> : null}

      <section className="stats-grid" aria-label="Digest summary">
        <StatCard label="Files included" value={formatNumber(result.files.length)} />
        <StatCard label="Tokens" value={formatNumber(result.total_tokens)} />
        <StatCard label="Source size" value={formatBytes(result.total_bytes)} />
        <StatCard label="Skipped" value={formatNumber(result.skipped.length)} />
      </section>

      <div className="results-grid">
        <section className="panel">
          <div className="panel-heading">
            <div><p className="eyebrow">Included files</p><h2 className="section-title">Repository map</h2></div>
            <span className="soft-badge"><PackageCheck aria-hidden="true" /> {result.files.length} files</span>
          </div>
          <div className="file-list">
            {result.files.length ? result.files.map((file) => (
              <FileRow
                key={file.path}
                file={file}
                expanded={expanded === file.path}
                onToggle={() => setExpanded(expanded === file.path ? null : file.path)}
              />
            )) : <p className="empty-copy">The service returned no file metadata. The raw digest is still available.</p>}
          </div>
        </section>

        <aside className="side-stack">
          <section className="panel">
            <div className="panel-heading">
              <div><p className="eyebrow">Next step</p><h2 className="section-title">Give your AI agent a map</h2></div>
              <WandSparkles aria-hidden="true" />
            </div>
            <p className="panel-copy">Download instructions to keep alongside the digest when sharing project context with an AI agent.</p>
            <button
              className="secondary-button full-width"
              type="button"
              onClick={() => downloadText("AGENTS.md", instructions, "text/markdown")}
            >
              <Download aria-hidden="true" /> Download AGENTS.md
            </button>
          </section>

          {result.skipped.length > 0 ? (
            <section className="panel">
              <div className="panel-heading">
                <div><p className="eyebrow">Excluded</p><h2 className="section-title">Skipped files</h2></div>
              </div>
              <ul className="skipped-list">
                {result.skipped.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </section>
          ) : null}
        </aside>
      </div>

      <section className="panel raw-output">
        <div className="panel-heading">
          <div><p className="eyebrow">Raw output</p><h2 className="section-title">Digest preview</h2></div>
          <button
            className="text-button"
            type="button"
            onClick={() => downloadText("contextpack.json", JSON.stringify(result, null, 2), "application/json")}
          >
            Download JSON <Download aria-hidden="true" />
          </button>
        </div>
        <pre className="digest-preview">{result.document}</pre>
      </section>

      <div className="results-bottom">
        <span><Check aria-hidden="true" /> Your digest is ready to use.</span>
        <button className="secondary-button" type="button" onClick={onPackAnother}>
          <RotateCcw aria-hidden="true" /> Pack another repository
        </button>
      </div>
    </main>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return <div className="stat-card"><span>{label}</span><strong>{value}</strong></div>;
}

function FileRow({
  file,
  expanded,
  onToggle,
}: {
  file: FileSummary;
  expanded: boolean;
  onToggle: () => void;
}) {
  const content = useMemo(
    () => expanded ? highlight(file.content, file.language) : "",
    [expanded, file.content, file.language],
  );

  return (
    <div className="file-row">
      <button className="file-toggle" type="button" onClick={onToggle} aria-expanded={expanded}>
        {expanded ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
        <FileCode2 aria-hidden="true" />
        <span>{file.path}</span>
        <small>{file.tokens.toLocaleString()} tokens</small>
      </button>
      {expanded ? <pre className="file-preview" dangerouslySetInnerHTML={{ __html: content }} /> : null}
    </div>
  );
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat().format(value);
}

function formatBytes(bytes: number): string {
  if (bytes < 1000) return `${formatNumber(bytes)} B`;
  if (bytes < 1_000_000) return `${(bytes / 1000).toFixed(1)} KB`;
  return `${(bytes / 1_000_000).toFixed(1)} MB`;
}
