"use client";

import { Check, Copy, Music2, Plus, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, songFileUrl, type Job, type LyricSong, type LyricSongDetail } from "@/lib/api";
import { Button, Field, FileInput, Spinner, useToast } from "./ui";

const STEP_LABEL: Record<string, string> = {
  analyze: "Timing the lyrics",
  text: "Writing the upload text",
  checklist: "Checklist",
  thumbnail: "Thumbnail",
  video: "Lyric video",
  short: "Short (9:16)",
  instrumental: "Instrumental video",
};
const VIDEOS: [string, string][] = [
  ["lyric_trim.mp4", "Lyric video, starts at the first vocal"],
  ["lyric_preview.mp4", "Lyric video, 8 s chorus preview first"],
  ["lyric_full.mp4", "Lyric video"],
  ["short_chorus.mp4", "Short / Reel (9:16)"],
  ["instrumental.mp4", "Instrumental"],
];

/** Poll a job until it finishes. */
function useJob(id: string | null, onFinish: (job: Job) => void) {
  const [job, setJob] = useState<Job | null>(null);
  const finish = useRef(onFinish);
  useEffect(() => {
    finish.current = onFinish;
  }, [onFinish]);
  useEffect(() => {
    if (!id) return;
    let stop = false;
    const tick = async () => {
      try {
        const j = await api.job(id);
        if (stop) return;
        setJob(j);
        if (j.status === "done" || j.status === "error") {
          finish.current(j);
          return;
        }
      } catch {
        // the engine may be busy; try again
      }
      if (!stop) setTimeout(tick, 1500);
    };
    void tick();
    return () => {
      stop = true;
    };
  }, [id]);
  return id ? job : null;
}

function JobStatus({ job }: { job: Job }) {
  const current = [...job.log].reverse().find((l) => l.startsWith("== "))?.slice(3).trim() ?? "";
  const tail = job.log.filter((l) => !l.startsWith("== ")).slice(-4);
  return (
    <div className="well grid gap-2 p-3 text-base" role="status">
      {job.status === "error" ? (
        <p className="font-semibold text-danger">{job.error || "Something went wrong."}</p>
      ) : (
        <p className="flex items-center gap-2 font-semibold">
          <Spinner /> {STEP_LABEL[current] ?? "Starting"}… (the first run downloads the lyric-timing model, which takes a few minutes)
        </p>
      )}
      {tail.length > 0 && <pre className="max-h-32 overflow-auto text-sm whitespace-pre-wrap text-ink-soft">{tail.join("\n")}</pre>}
    </div>
  );
}

function NewSong({ onCreated }: { onCreated: (slug: string, job: string) => void }) {
  const toast = useToast();
  const [audio, setAudio] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [style, setStyle] = useState("");
  const [lyrics, setLyrics] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!audio) return toast("Choose the song's mp3 or wav first.", "error");
    setBusy(true);
    try {
      const r = await api.createLyricSong(audio, lyrics, title, style);
      onCreated(r.slug, r.job);
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="card grid gap-4 p-4">
      <h2 className="card-title">New lyric video</h2>
      <p className="page-intro">Upload the song from Suno and paste its lyrics. The tool times every line to the music, then you check it before it renders.</p>
      <Field label="Song file" htmlFor="lv-audio">
        <FileInput id="lv-audio" accept=".mp3,.wav,audio/*" file={audio?.name ?? ""} onFile={(f) => { setAudio(f); if (!title) setTitle(f.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ")); }} onReject={(m) => toast(m, "error")} disabled={busy} />
      </Field>
      <Field label="Title" htmlFor="lv-title">
        <input id="lv-title" className="field-input" value={title} onChange={(e) => setTitle(e.target.value)} disabled={busy} />
      </Field>
      <Field label="Suno style prompt" htmlFor="lv-style" hint="optional: picks the genre and colours">
        <textarea id="lv-style" rows={2} className="field-input" value={style} onChange={(e) => setStyle(e.target.value)} disabled={busy} placeholder="Psychedelic synth-pop, dreamy male falsetto…" />
      </Field>
      <Field label="Lyrics" htmlFor="lv-lyrics" hint="paste from Suno, with the [Verse] / [Chorus] tags">
        <textarea id="lv-lyrics" rows={14} required className="field-input font-mono text-base" value={lyrics} onChange={(e) => setLyrics(e.target.value)} disabled={busy} placeholder={"[Verse 1]\nI see your light from a thousand miles\n…\n[Chorus]\n…"} />
      </Field>
      <div>
        <Button type="submit" variant="primary" loading={busy} icon={<Music2 className="size-4" />}>
          Time the lyrics
        </Button>
      </div>
    </form>
  );
}

const fmt = (s: number | null | undefined) => (s == null ? "" : String(s));

function SongView({ slug, job, onJob, onChanged }: { slug: string; job: string | null; onJob: (id: string) => void; onChanged: () => void }) {
  const toast = useToast();
  const [d, setD] = useState<LyricSongDetail | null>(null);
  const [form, setForm] = useState<LyricSongDetail["song"] | null>(null);
  const [cs, setCs] = useState("");
  const [ce, setCe] = useState("");
  const [draft, setDraft] = useState(true);
  const [ai, setAi] = useState<"template" | "gemini">("template");
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [bust, setBust] = useState("");

  const load = useCallback(async () => {
    try {
      const x = await api.lyricSong(slug);
      setD(x);
      setForm(x.song);
      setCs(fmt(x.chorus.start));
      setCe(fmt(x.chorus.end));
      setBust(String(Date.now()));
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }, [slug, toast]);
  useEffect(() => {
    const t = setTimeout(() => void load(), 0); // a timer callback, so the first load isn't a setState in the effect body
    return () => clearTimeout(t);
  }, [load]);

  const running = useJob(job, () => {
    void load();
    onChanged();
  });
  const busy = !!running && running.status !== "done" && running.status !== "error";

  async function save(): Promise<boolean> {
    if (!form) return false;
    setSaving(true);
    try {
      const body: Parameters<typeof api.editLyricSong>[1] = { song: form };
      if (cs !== "" && ce !== "") {
        body.chorus_start = Number(cs);
        body.chorus_end = Number(ce);
      }
      const x = await api.editLyricSong(slug, body);
      setD(x);
      onChanged();
      return true;
    } catch (e) {
      toast((e as Error).message, "error");
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function render() {
    if (!(await save())) return;
    try {
      onJob((await api.renderLyricSong(slug, { draft, ai, no_video: false })).job);
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  if (!d || !form) return <div className="grid place-items-center p-10"><Spinner className="size-6" /></div>;
  const set = (k: keyof typeof form, v: string) => setForm({ ...form, [k]: v });
  const videos = VIDEOS.filter(([f]) => d.files.includes(f));

  return (
    <div className="grid gap-4">
      {running && (busy || running.status === "error") && <JobStatus job={running} />}

      {!d.analyzed ? (
        !busy && (
          <div className="card grid gap-3 p-4">
            <p>This song hasn&apos;t been timed yet.</p>
            <div>
              <Button variant="primary" onClick={async () => onJob((await api.reanalyzeLyricSong(slug)).job)}>Time the lyrics</Button>
            </div>
          </div>
        )
      ) : (
        <>
          <section className="card grid gap-4 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="card-title">1. Check the song</h2>
              <span className="text-base text-ink-soft tabular-nums">
                {d.bpm ? `${d.bpm} bpm` : ""}{d.duration ? ` · ${Math.floor(d.duration / 60)}:${String(Math.round(d.duration % 60)).padStart(2, "0")}` : ""}{d.vocal_start != null ? ` · vocal starts at ${d.vocal_start}s` : ""}
              </span>
            </div>
            {d.warnings.length > 0 && (
              <ul className="well grid gap-1 p-3 text-base text-ink-soft">
                {d.warnings.map((w) => <li key={w}>{w}</li>)}
              </ul>
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Title" htmlFor="sv-title"><input id="sv-title" className="field-input" value={form.title} onChange={(e) => set("title", e.target.value)} /></Field>
              <Field label="Genre" htmlFor="sv-genre">
                <select id="sv-genre" className="field-input" value={form.genre} onChange={(e) => set("genre", e.target.value)}>
                  <option value="">(not recognised)</option>
                  {["nu-disco", "psych-pop", "psych-rock", "late-night"].map((g) => <option key={g}>{g}</option>)}
                </select>
              </Field>
              <Field label="Mood phrase" htmlFor="sv-mood"><input id="sv-mood" className="field-input" value={form.mood_phrase} onChange={(e) => set("mood_phrase", e.target.value)} /></Field>
              <Field label="Scene theme" htmlFor="sv-scene"><input id="sv-scene" className="field-input" value={form.scene_theme} onChange={(e) => set("scene_theme", e.target.value)} /></Field>
              <Field label="Subscribe line" htmlFor="sv-sub"><input id="sv-sub" className="field-input" value={form.subscribe_line} onChange={(e) => set("subscribe_line", e.target.value)} /></Field>
              <Field label="Playlist" htmlFor="sv-pl"><input id="sv-pl" className="field-input" value={form.playlist} onChange={(e) => set("playlist", e.target.value)} /></Field>
              <Field label="Suno plan" htmlFor="sv-plan">
                <select id="sv-plan" className="field-input" value={form.plan} onChange={(e) => set("plan", e.target.value)}>
                  <option value="">(not set)</option>
                  <option>Pro</option>
                  <option>Premier</option>
                </select>
              </Field>
              <Field label="Made on Suno" htmlFor="sv-gen"><input id="sv-gen" type="date" className="field-input" value={form.generated_on} onChange={(e) => set("generated_on", e.target.value)} /></Field>
              <Field label="Chorus starts (s)" htmlFor="sv-cs"><input id="sv-cs" type="number" step="0.1" min={0} className="field-input" value={cs} onChange={(e) => setCs(e.target.value)} /></Field>
              <Field label="Chorus ends (s)" htmlFor="sv-ce"><input id="sv-ce" type="number" step="0.1" min={0} className="field-input" value={ce} onChange={(e) => setCe(e.target.value)} /></Field>
            </div>
            <details>
              <summary className="cursor-pointer text-base font-semibold text-ink-soft">Timed lyrics (lyrics.lrc)</summary>
              <pre className="well mt-2 max-h-72 overflow-auto p-3 text-sm whitespace-pre-wrap">{d.lyrics}</pre>
            </details>
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => void save()} loading={saving}>Save changes</Button>
              <Button variant="ghost" icon={<RefreshCw className="size-4" />} disabled={busy} onClick={async () => onJob((await api.reanalyzeLyricSong(slug)).job)}>Time the lyrics again</Button>
            </div>
          </section>

          <section className="card grid gap-4 p-4">
            <h2 className="card-title">2. Make the videos</h2>
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-base">
              <label className="flex items-center gap-2"><input type="checkbox" className="size-4 accent-cobalt" checked={draft} onChange={(e) => setDraft(e.target.checked)} /> Quick draft (half size, fast)</label>
              <label className="flex items-center gap-2">Upload text
                <select className="field-input h-9 w-auto py-0" value={ai} onChange={(e) => setAi(e.target.value as "template" | "gemini")}>
                  <option value="template">Fixed template</option>
                  <option value="gemini">Written by Gemini</option>
                </select>
              </label>
            </div>
            <div>
              <Button variant="primary" loading={busy} onClick={render}>{draft ? "Render a draft" : "Render the full videos"}</Button>
            </div>
          </section>

          {/* no players while a job runs: an open video file can't be replaced by the render on Windows */}
          {!busy && (videos.length > 0 || d.files.includes("thumbnail.jpg")) && (
            <section className="card grid gap-4 p-4">
              <h2 className="card-title">Results</h2>
              <div className="grid gap-4 md:grid-cols-2">
                {d.files.includes("thumbnail.jpg") && (
                  <figure className="grid gap-1.5">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={songFileUrl(slug, "out/thumbnail.jpg", bust)} alt="Thumbnail" className="w-full rounded-lg border border-line" />
                    <figcaption className="text-sm text-ink-soft">Thumbnail (1280×720)</figcaption>
                  </figure>
                )}
                {videos.map(([f, label]) => (
                  <figure key={f} className="grid gap-1.5">
                    <video src={songFileUrl(slug, `out/${f}`, bust)} controls preload="none" className={`w-full rounded-lg bg-black ${f.startsWith("short") ? "max-h-[28rem] object-contain" : ""}`} />
                    <figcaption className="text-sm text-ink-soft">{label} · <a className="underline" href={songFileUrl(slug, `out/${f}`)} download>download</a></figcaption>
                  </figure>
                ))}
              </div>
              {d.upload_text && (
                <div className="grid gap-2">
                  <div className="flex items-center justify-between">
                    <h3 className="field-label">Upload text</h3>
                    <Button size="sm" variant="ghost" icon={copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                      onClick={() => { void navigator.clipboard.writeText(d.upload_text); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>
                      {copied ? "Copied" : "Copy"}
                    </Button>
                  </div>
                  <pre className="well max-h-72 overflow-auto p-3 text-sm whitespace-pre-wrap">{d.upload_text}</pre>
                </div>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}

/** The lyric video tab: upload a song and its lyrics, check the timing, render the lyric video, Short and thumbnail. */
export function LyricVideo() {
  const toast = useToast();
  const [songs, setSongs] = useState<LyricSong[]>([]);
  const [sel, setSel] = useState<string | "new">("new");
  const [job, setJob] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    try {
      setSongs(await api.lyricSongs());
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }, [toast]);
  useEffect(() => {
    const t = setTimeout(() => void loadList(), 0);
    return () => clearTimeout(t);
  }, [loadList]);

  return (
    <div className="flex h-full min-h-0 flex-col lg:flex-row">
      <aside className="shrink-0 border-b border-line bg-panel lg:w-64 lg:border-r lg:border-b-0">
        <div className="pane-header">
          <h1 className="pane-title">Lyric videos</h1>
          <Button size="sm" icon={<Plus className="size-4" />} onClick={() => { setSel("new"); setJob(null); }}>New</Button>
        </div>
        <ul className="max-h-40 overflow-y-auto p-2 lg:max-h-none">
          {songs.length === 0 && <li className="p-2 text-base text-ink-soft">No songs yet.</li>}
          {songs.map((s) => (
            <li key={s.slug}>
              <button type="button" onClick={() => { setSel(s.slug); setJob(null); }} aria-current={sel === s.slug}
                className={`w-full cursor-pointer rounded-lg border-0 px-3 py-2 text-left text-base ${sel === s.slug ? "bg-cobalt/10 font-semibold" : "bg-transparent hover:bg-ink/[0.05]"}`}>
                <span className="block truncate">{s.title}</span>
                <span className="text-sm text-ink-soft">{s.rendered ? "Rendered" : s.analyzed ? "Ready to render" : "Not timed yet"}</span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <main className="min-h-0 flex-1 overflow-y-auto bg-paper p-4">
        <div className="mx-auto grid max-w-3xl gap-4">
          {sel === "new" ? (
            <NewSong onCreated={(slug, j) => { setSel(slug); setJob(j); void loadList(); }} />
          ) : (
            <SongView key={sel} slug={sel} job={job} onJob={setJob} onChanged={() => void loadList()} />
          )}
        </div>
      </main>
    </div>
  );
}
