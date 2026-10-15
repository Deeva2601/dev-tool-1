import type { PackResponse } from "../../lib/types";

export function agentText(result: PackResponse, digestName: string): string {
  const included =
    result.files.map((file) => `- \`${file.path}\` (${file.mode})`).join("\n") || "- none";
  const skipped = result.skipped.map((item) => `- ${item}`).join("\n") || "- none";
  return [
    "# Context digest",
    "",
    `Read \`${digestName}\` before answering questions about this repository.`,
    "Treat that file as the only source snapshot. Do not invent files that are not listed.",
    "Files marked `outline` or `skeleton` omit implementation bodies.",
    "",
    "## Included",
    "",
    included,
    "",
    "## Skipped",
    "",
    skipped,
    "",
  ].join("\n");
}
