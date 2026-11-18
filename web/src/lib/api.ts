// The API's shapes, written to match the Pydantic models in src/docintel/.
// If a Python model changes, change the type here too.

import { EventSourceParserStream } from "eventsource-parser/stream";

export type FieldInfo = { name: string; label: string; group: string }; // api/fields.py

export type Sample = {
  // api/samples.py
  id: string;
  title: string;
  contract_type: string;
  pages: number;
  scan: boolean;
  doc_id: string;
};

export type Rect = [number, number, number, number]; // x0, y0, x1, y1 in PDF points, y from the bottom

export type Highlight = {
  // domain/locate.py
  quote_index: number;
  page: number; // from 1
  page_size: [number, number]; // width, height in PDF points
  rects: Rect[];
};

export type Issue = {
  // domain/validate/issues.py
  field: string;
  rule: string;
  severity: "error" | "warn";
  detail: string;
};

export type Value = string | string[] | null; // api/schemas.py

export type FieldResult = {
  // domain/pipeline.py
  found: boolean;
  value: Value;
  quotes: string[];
  needs_review: boolean;
  issues: Issue[];
  highlights: Highlight[];
  evidence: string[];
  evidence_highlights: Highlight[];
};

export type ExtractResult = {
  request_id: string;
  document: { filename: string; sha256: string; sample_id: string | null };
  fields: Record<string, FieldResult>;
  needs_review: boolean;
  parser: string;
  pages: number;
  cost_usd: number;
  latency_ms: number;
};

export type ReviewSaved = {
  // api/schemas.py
  review_id: string;
  field: string;
  action: "accept" | "modify";
  old: Value;
  new: Value;
};

// The events of POST /v1/extract/stream. An answer that is not a stream also becomes an `error` event.
export type StreamEvent =
  | { event: "stage"; data: { name: "parse" | "extract" | "check"; status: "start" | "done"; parser?: string; pages?: number } }
  | { event: "attempt"; data: { n: number; errors: number } }
  | { event: "result"; data: ExtractResult }
  | { event: "error"; data: { status: number; detail: string } };

export type Input = { sampleId: string } | { pdf: File };

/** An HTTP error with FastAPI's message, so the UI can show it. */
export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** FastAPI puts a message in `detail`: a string, or a list of problems for a 422. */
function detailText(body: unknown): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d?.msg ?? String(d)).join("; ");
  return "the server gave no reason";
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, detailText(body));
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export const getFields = () => call<FieldInfo[]>("/v1/fields");
export const getSamples = () => call<Sample[]>("/v1/samples");
export const samplePdfUrl = (id: string) => `/v1/samples/${encodeURIComponent(id)}/pdf`;

export type ReviewInput = { request_id: string; field: string; action: "accept" | "modify"; value?: Value };

export const postReview = (body: ReviewInput) =>
  call<ReviewSaved>("/v1/reviews", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const deleteReview = (reviewId: string) =>
  call<void>(`/v1/reviews/${encodeURIComponent(reviewId)}`, { method: "DELETE" });

/**
 * Start an extract and call `onEvent` for each event, in order.
 * EventSource can only send GET, and this needs a POST with a file, so it is fetch plus a parser.
 */
export async function streamExtract(
  input: Input,
  fields: string[],
  allFields: number,
  onEvent: (e: StreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const form = new FormData();
  if ("sampleId" in input) form.append("sample_id", input.sampleId);
  else form.append("pdf", input.pdf);
  if (fields.length < allFields) fields.forEach((f) => form.append("fields", f)); // none = all 12

  const response = await fetch("/v1/extract/stream", { method: "POST", body: form, signal });
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => null);
    onEvent({ event: "error", data: { status: response.status, detail: detailText(body) } });
    return;
  }
  const events = response.body.pipeThrough(new TextDecoderStream()).pipeThrough(new EventSourceParserStream());
  for await (const message of events) {
    onEvent({ event: message.event, data: JSON.parse(message.data) } as StreamEvent);
  }
}
