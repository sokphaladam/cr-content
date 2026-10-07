// Typed client for the Python engine (crcontent/web.py). The browser calls it directly.
export const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export type Lang = "en" | "km";

export interface Scene {
  narration: string;
  visual_query: string;
  on_screen_text: string;
  media: string; // "" = automatic footage, otherwise a project-relative path
}

export interface VideoScript {
  title: string;
  scenes: Scene[];
  caption: string;
  hashtags: string[];
}

export interface Options {
  langs: Record<Lang, { name: string; voices: string[] }>;
  music: string[];
  keys: { anthropic: boolean; stock: "" | "pexels" | "pixabay" };
}

export interface Job {
  id: string;
  status: "queued" | "running" | "done" | "error";
  step: number;
  log: string[];
  title: string;
  video?: string;
  error?: string;
}

export interface VideoSummary {
  name: string;
  title: string;
  lang: Lang;
  created: string;
  video: boolean;
  thumb: boolean;
  thumb_v: number; // changes when the thumbnail is redrawn (cache buster)
}

export interface VideoDetail extends VideoSummary {
  script: VideoScript | null;
  post: string;
  duration: number; // seconds
  thumb_text: string; // headline last used for the thumbnail
  thumb_at: number; // seconds into the video of the thumbnail frame
}

export interface StockResult {
  source: "pexels" | "pixabay";
  id: number;
  kind: "video" | "photo";
  thumb: string;
  duration?: number;
  author: string;
}

export interface MediaInfo {
  media: string;
  url: string;
  kind: "video" | "photo";
}

export interface DraftData {
  script: VideoScript;
  lang: Lang;
  topic: string;
  voice: string;
  rate: string;
  music: string;
}

export interface DraftSummary {
  id: string;
  title: string;
  lang: Lang;
  updated: string;
  scenes: number;
  cover: string; // first scene background (project path) or ""
}

export class ApiError extends Error {}

// Quick calls give up after this long, so a request lost while the engine restarts can't hang the UI.
// Claude, upload and render calls pass `timeout: 0` (no limit).
const TIMEOUT_MS = 15_000;

async function request<T>(path: string, init: RequestInit & { json?: unknown; timeout?: number } = {}): Promise<T> {
  const { json, timeout = TIMEOUT_MS, ...rest } = init;
  let res: Response;
  try {
    res = await fetch(API_BASE + path, {
      ...rest,
      headers: json !== undefined ? { "Content-Type": "application/json", ...rest.headers } : rest.headers,
      body: json !== undefined ? JSON.stringify(json) : rest.body,
      signal: timeout ? AbortSignal.timeout(timeout) : rest.signal,
    });
  } catch (e) {
    if ((e as Error).name === "TimeoutError") throw new ApiError("The video engine didn't answer in time. Try again.");
    throw new ApiError("Can't reach the video engine. Start it with: npm run dev (in frontend/), or python app.py");
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

/** URL for a project-relative file (uploads/..., cache/...) or an output folder file. */
export const fileUrl = (projectPath: string) =>
  `${API_BASE}/${projectPath.split("/").map(encodeURIComponent).join("/")}`;
export const outputUrl = (folder: string, file: string) =>
  `${API_BASE}/media/${encodeURIComponent(folder)}/${file}`;

export const api = {
  options: () => request<Options>("/api/options"),
  writeScript: (body: { topic: string; lang: Lang; scenes: number; seconds: number; style: string }) =>
    request<VideoScript>("/api/script", { method: "POST", json: body, timeout: 0 }),
  importScript: (text: string) =>
    request<{ script: VideoScript; lang: Lang; method: "claude" | "basic" }>("/api/import", { method: "POST", json: { text, lang: "auto" }, timeout: 0 }),
  translate: (script: VideoScript, target: Lang) =>
    request<VideoScript>("/api/translate", { method: "POST", json: { script, target }, timeout: 0 }),
  ideas: (narration: string, current: string) =>
    request<{ queries: string[] }>("/api/ideas", { method: "POST", json: { narration, current }, timeout: 0 }),
  footage: (q: string, kind: "video" | "photo") =>
    request<{ results: StockResult[] }>(`/api/footage?q=${encodeURIComponent(q)}&kind=${kind}`),
  pick: (r: StockResult) =>
    request<MediaInfo>("/api/footage/pick", { method: "POST", json: { source: r.source, kind: r.kind, id: r.id }, timeout: 0 }),
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<MediaInfo>("/api/upload", { method: "POST", body: form, timeout: 0 });
  },
  render: (body: { script: VideoScript; topic: string; lang: Lang; voice: string; rate: string; music: string; draft_id: string }) =>
    request<{ id: string }>("/api/render", { method: "POST", json: body, timeout: 0 }),
  drafts: () => request<DraftSummary[]>("/api/drafts"),
  draft: (id: string) => request<DraftData & { id: string }>(`/api/drafts/${encodeURIComponent(id)}`),
  createDraft: (d: DraftData) => request<{ id: string; updated: string }>("/api/drafts", { method: "POST", json: d }),
  saveDraft: (id: string, d: DraftData) =>
    request<{ id: string; updated: string }>(`/api/drafts/${encodeURIComponent(id)}`, { method: "PUT", json: d }),
  deleteDraft: (id: string) => request<unknown>(`/api/drafts/${encodeURIComponent(id)}`, { method: "DELETE" }),
  job: (id: string) => request<Job>(`/api/jobs/${id}`),
  videos: () => request<VideoSummary[]>("/api/videos"),
  video: (name: string) => request<VideoDetail>(`/api/videos/${encodeURIComponent(name)}`),
  makeThumbnail: (name: string, text: string, at: number) =>
    request<VideoSummary>(`/api/videos/${encodeURIComponent(name)}/thumbnail`, { method: "POST", json: { text, at }, timeout: 60_000 }),
  deleteVideo: (name: string) => request<unknown>(`/api/videos/${encodeURIComponent(name)}`, { method: "DELETE" }),
  /** Returns an mp3 blob for the voice preview. */
  speak: async (text: string, voice: string, rate: string): Promise<Blob> => {
    let res: Response;
    try {
      res = await fetch(`${API_BASE}/api/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voice, rate }),
      });
    } catch {
      throw new ApiError("Can't reach the video engine.");
    }
    if (!res.ok) throw new ApiError((await res.json().catch(() => ({}))).detail ?? `Preview failed (${res.status})`);
    return res.blob();
  },
};
