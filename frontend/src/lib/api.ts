import type { PackRequest, PackResponse } from "./types";

export async function packSource(body: PackRequest): Promise<PackResponse> {
  const response = await fetch("/pack", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload: unknown = await response.json();
  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : response.statusText;
    throw new Error(detail);
  }
  return payload as PackResponse;
}
