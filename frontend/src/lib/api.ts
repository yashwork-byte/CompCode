// Thin client for the CodeComp FastAPI backend.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface FunctionHit {
  function: string;
  file: string;
  language: string;
  code: string;
}

export interface IndexResult {
  repo: string;
  num_functions: number;
  languages: string[];
}

export interface QueryResult {
  answer: string;
  route: string;
  functions: FunctionHit[];
}

// A single-file edit proposed by the graph, awaiting human review.
export interface EditPlan {
  file: string;
  new_content: string;
  diff: string;
  rationale: string;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(
      `Cannot reach the backend at ${API_URL}. Is the API running?`,
    );
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      /* ignore parse errors */
    }
    throw new Error(detail);
  }

  return res.json() as Promise<T>;
}

export function indexRepo(repo: string, token?: string) {
  return post<IndexResult>("/index", { repo, token: token || null });
}

export function newThreadId(): string {
  return (crypto.randomUUID?.() ?? Math.random().toString(36).slice(2)).replace(/-/g, "");
}

export interface StreamHandlers {
  onMeta?: (meta: { route: string; functions: FunctionHit[] }) => void;
  onToken?: (text: string) => void;
  // Edit workflow paused for review — carries the proposed diff + thread id.
  onInterrupt?: (data: { thread_id: string; type: string; plan: EditPlan }) => void;
  onDone?: (data: { status: string; answer: string }) => void;
  onError: (message: string) => void;
}

// Shared SSE consumer for /query/stream and /resume.
async function streamSSE(path: string, body: unknown, handlers: StreamHandlers) {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    handlers.onError(`Cannot reach the backend at ${API_URL}. Is the API running?`);
    return;
  }

  if (!res.ok || !res.body) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      /* ignore */
    }
    handlers.onError(detail);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      let event = "message";
      let data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (!data) continue;

      const payload = JSON.parse(data);
      if (event === "meta") handlers.onMeta?.(payload);
      else if (event === "token") handlers.onToken?.(payload.text);
      else if (event === "interrupt") handlers.onInterrupt?.(payload);
      else if (event === "done") handlers.onDone?.(payload);
      else if (event === "error") handlers.onError(payload.detail);
    }
  }
}

// Start a query. `meta` arrives first, then `token` deltas, then either
// `interrupt` (edit awaiting review) or `done`.
export function queryRepoStream(
  repo: string,
  query: string,
  token: string | undefined,
  threadId: string,
  handlers: StreamHandlers,
) {
  return streamSSE(
    "/query/stream",
    { repo, query, token: token || null, thread_id: threadId },
    handlers,
  );
}

// Resume a paused edit review with the human's decision.
export function resumeStream(
  threadId: string,
  decision: "approve" | "reject",
  feedback: string | undefined,
  handlers: StreamHandlers,
) {
  return streamSSE(
    "/resume",
    { thread_id: threadId, decision, feedback: feedback || null },
    handlers,
  );
}
