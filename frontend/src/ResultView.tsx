import { useMemo, useState } from "react";
import { agentText } from "./agentText";
import { copyText, downloadText } from "./download";
import { highlight } from "./highlight";
import type { DigestFormat, FileSummary, PackResponse } from "./types";

const EXT: Record<DigestFormat, string> = {
  markdown: "md",
  xml: "xml",
  json: "json",
};

const MIME: Record<DigestFormat, string> = {
  markdown: "text/markdown",
  xml: "application/xml",
  json: "application/json",
};

export function ResultView({ result, format }: { result: PackResponse; format: DigestFormat }) {
  const [open, setOpen] = useState<string | null>(result.files[0]?.path ?? null);
  const [notice, setNotice] = useState<string | null>(null);
  const digestName = `digest.${EXT[format]}`;
  const instructions = useMemo(() => agentText(result, digestName), [result, digestName]);

  async function copyDigest() {
    await copyText(result.document);
    setNotice("Digest copied.");
  }

  return (
    <section className="result">
      <div className="toolbar">
        <p className="stats">
          {result.files.length} files · {result.skipped.length} skipped · {result.total_bytes} bytes ·{" "}
          {result.total_tokens} tokens
        </p>
        <div className="actions">
          <button type="button" onClick={copyDigest}>
            Copy digest
          </button>
          <button type="button" onClick={() => downloadText(digestName, result.document, MIME[format])}>
            Download
          </button>
          <button type="button" onClick={() => downloadText("digest.AGENTS.md", instructions, "text/markdown")}>
            Download AGENTS.md
          </button>
        </div>
      </div>
      {notice ? <p className="notice">{notice}</p> : null}

      <div className="split">
        <div>
          <h2>Files</h2>
          <ul className="files">
            {result.files.map((file) => (
              <FileRow
                key={file.path}
                file={file}
                open={open === file.path}
                onToggle={() => setOpen(open === file.path ? null : file.path)}
              />
            ))}
          </ul>
          <h2>Skipped</h2>
          {result.skipped.length === 0 ? (
            <p className="muted">None</p>
          ) : (
            <ul className="skipped">
              {result.skipped.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </div>
        <aside>
          <h2>Agent instructions</h2>
          <pre className="digest small">{instructions}</pre>
        </aside>
      </div>
    </section>
  );
}

function FileRow({ file, open, onToggle }: { file: FileSummary; open: boolean; onToggle: () => void }) {
  const html = useMemo(() => (open ? highlight(file.content, file.language) : ""), [open, file.content, file.language]);
  return (
    <li>
      <button type="button" className="file-head" onClick={onToggle}>
        <code>{file.path}</code>
        <span className="badges">
          <em>{file.mode}</em>
          <em>{file.tokens} tok</em>
          <em>rank {Math.round(file.rank)}</em>
        </span>
      </button>
      {open ? <pre className="digest code" dangerouslySetInnerHTML={{ __html: html }} /> : null}
    </li>
  );
}