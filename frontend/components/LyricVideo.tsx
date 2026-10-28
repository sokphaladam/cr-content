"use client";

import { Check, Copy, Music2, Pause, Play, Plus, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, lyricPreviewUrl, lyricStreamUrl, songFileUrl, type Job, type LyricSong, type LyricSongDetail } from "@/lib/api";
import { LyricPicturesCard } from "./LyricPictures";
import { RowMenu } from "./Library";
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

const RENDER_STEPS = ["text", "checklist", "thumbnail", "video", "short", "instrumental"];

const clock = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

/** Seconds since the job first showed up here. */
function useElapsed(running: boolean) {
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    if (!running) return;
    const t0 = Date.now();
    const t = setInterval(() => setSecs(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(t);
  }, [running]);
  return secs;
}

function JobStatus({ job }: { job: Job }) {
  const elapsed = useElapsed(job.status !== "error");
  const current = [...job.log].reverse().find((l) => l.startsWith("== "))?.slice(3).trim() ?? "";
  const tail = job.log.filter((l) => !l.startsWith("== ")).slice(-4);
  // timing is a job of its own; a render runs the other steps
  const steps = current === "analyze" || !current ? ["analyze"] : RENDER_STEPS;
  const at = Math.max(0, steps.indexOf(current));
  // the render prints "40%" lines while it draws frames
  const sub = [...job.log].reverse().map((l) => /^\s*(\d{1,3})%\s*$/.exec(l)?.[1]).find((m) => m !== undefined);
  const stepFrac = job.progress ?? (sub !== undefined && current === "video" ? Math.min(1, Number(sub) / 100) : null);
  const pct = Math.round(((at + (stepFrac ?? 0)) / steps.length) * 100);
  const detail = job.detail && !(job.detail in STEP_LABEL) ? job.detail : "";
  const slow = (current === "analyze" || !current) && !detail;
  return (
    <div className="well grid gap-3 p-3 text-base" role="status" aria-live="polite">
      {job.status === "error" ? (
        <p className="font-semibold text-danger">{job.error || "Something went wrong."}</p>
      ) : (
        <>
          <div className="flex items-center justify-between gap-3">
            <p className="m-0 flex items-center gap-2 font-semibold">
              <Spinner /> {STEP_LABEL[current] ?? "Starting"}…
              {steps.length > 1 && <span className="font-normal text-ink-soft">step {at + 1} of {steps.length}</span>}
            </p>
            <span className="text-sm text-ink-soft tabular-nums">{stepFrac != null || steps.length > 1 ? `${pct}% · ` : ""}{clock(elapsed)}</span>
          </div>
          <div role="progressbar" aria-label="Progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} className="h-1.5 overflow-hidden rounded-full bg-ink/[0.08]">
            <div
              className={`h-full rounded-full bg-cobalt transition-[width] duration-500 ${stepFrac == null && steps.length === 1 ? "w-1/3 animate-pulse" : ""}`}
              style={stepFrac == null && steps.length === 1 ? undefined : { width: `${Math.max(pct, 3)}%` }}
            />
          </div>
          {detail && <p className="m-0 text-sm text-ink-soft">{detail}</p>}
          {steps.length > 1 && (
            <ol className="m-0 flex list-none flex-wrap gap-x-4 gap-y-1 p-0 text-sm">
              {steps.map((s, i) => (
                <li key={s} className={i < at ? "text-ink-soft" : i === at ? "font-semibold" : "text-ink-soft/60"}>
                  {i < at ? "✓ " : i === at ? "● " : "○ "}{STEP_LABEL[s]}
                </li>
              ))}
            </ol>
          )}
          {slow && <p className="m-0 text-sm text-ink-soft">The first run downloads the lyric-timing model, which takes a few minutes. Later runs are much quicker.</p>}
        </>
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

const KIND_COLOUR: Record<string, string> = {
  chorus: "#c02a75", "pre-chorus": "#a8368a", verse: "#1d6f86", bridge: "#b9741a", intro: "#5c6680", outro: "#3c4660",
};

/** The song as a bar of its sections, with where the video puts the subscribe pill (just after the first chorus) and
 *  the end-screen space (the last 20 s). Click it to preview that moment. */
function SongStrip({ d, at, onAt }: { d: LyricSongDetail; at: number; onAt: (t: number) => void }) {
  const dur = d.duration ?? 0;
  if (!dur) return null;
  const pct = (t: number) => `${Math.min(Math.max(t / dur, 0), 1) * 100}%`;
  const chorusEnd = d.chorus.end;
  return (
    <div className="grid gap-1">
      <div
        className="relative h-14 w-full cursor-pointer overflow-hidden rounded-lg border border-line bg-sunken"
        role="slider" aria-label="Song position" aria-valuemin={0} aria-valuemax={Math.round(dur)} aria-valuenow={Math.round(at)} tabIndex={-1}
        onClick={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          onAt(Math.round(((e.clientX - r.left) / r.width) * dur));
        }}
      >
        {d.sections.map((s) => (
          <div key={`${s.tag}-${s.start}`} title={`${s.tag} ${clock(Math.round(s.start))}`} className="absolute inset-y-0 flex items-center overflow-hidden border-r border-white/30 px-1.5 text-xs font-semibold whitespace-nowrap text-white"
            style={{ left: pct(s.start), width: pct(s.end - s.start), background: KIND_COLOUR[s.kind] ?? "#5c6680" }}>
            {(s.end - s.start) / dur > 0.045 ? s.tag : ""}
          </div>
        ))}
        {chorusEnd != null && (
          <div title="Subscribe pill" className="absolute inset-y-0 border-l-2 border-amber-300" style={{ left: pct(chorusEnd + 0.3), width: pct(4), background: "repeating-linear-gradient(135deg,#ffe18a 0 4px,#ffe18a00 4px 8px)" }} />
        )}
        <div title="End-screen space (last 20 s)" className="absolute inset-y-0" style={{ left: pct(dur - 20), right: 0, background: "repeating-linear-gradient(135deg,#39d5e099 0 4px,#39d5e000 4px 8px)" }} />
        <div className="absolute -inset-y-1 w-0.5 bg-ink" style={{ left: pct(at) }} />
      </div>
      <div className="flex flex-wrap gap-x-4 text-xs text-ink-soft">
        <span><i className="mr-1 inline-block size-2.5 rounded-sm align-middle" style={{ background: "#ffe18a" }} />Subscribe pill</span>
        <span><i className="mr-1 inline-block size-2.5 rounded-sm align-middle" style={{ background: "#39d5e0aa" }} />End-screen space</span>
      </div>
    </div>
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
  const [at, setAt] = useState(0);
  const [picBust, setPicBust] = useState(""); // changes when a picture does, so the preview frame is drawn again
  const [shown, setShown] = useState(0); // the time the preview frame is drawn at: moves when the slider is let go
  const [playing, setPlaying] = useState(false); // the timeline is playing in the preview (a live stream + the song)
  const [from, setFrom] = useState(0); // the second the stream started from
  const [run, setRun] = useState(0); // a new number = a new stream (play, seek, or a new look while playing)
  const audioRef = useRef<HTMLAudioElement>(null);
  const synced = useRef(false); // the song starts with the stream's first frame

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
  const look = { style: form.lyric_style, grade: form.mood_grade, neon: !!form.neon_intro, playing: !!form.now_playing,
    pulse: form.beat_pulse, parts: form.pulse_parts, when: form.pulse_when };
  /** (Re)start the stream from second `t`; the song joins when its first frame arrives. */
  const playFrom = (t: number) => {
    synced.current = false;
    audioRef.current?.pause();
    setAt(t);
    setFrom(t);
    setRun((n) => n + 1);
    setPlaying(true);
  };
  const stopPlaying = () => {
    audioRef.current?.pause();
    setPlaying(false);
    setShown(at);
  };
  const LOOK_KEYS = ["lyric_style", "mood_grade", "beat_pulse", "pulse_parts", "pulse_when", "neon_intro", "now_playing"];
  const set = (k: keyof typeof form, v: string) => {
    setForm({ ...form, [k]: v });
    if (playing && LOOK_KEYS.includes(k)) playFrom(at); // a new look while playing: carry on from here in it
  };
  const previewSrc = lyricPreviewUrl(slug, shown, look, picBust);
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

          <section className="card grid gap-3 p-4">
            <h2 className="card-title">2. Style and mood</h2>
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,34rem)]">
              <div className="grid content-start gap-3">
                <Field label="Lyric style" htmlFor="sv-style">
                  <select id="sv-style" className="field-input" value={form.lyric_style || "classic"} onChange={(e) => set("lyric_style", e.target.value)}>
                    {Object.entries(d.styles).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
                  </select>
                </Field>
                <Field label="Mood grade" htmlFor="sv-grade">
                  <select id="sv-grade" className="field-input" value={form.mood_grade || "neon"} onChange={(e) => set("mood_grade", e.target.value)}>
                    {Object.entries(d.grades).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
                  </select>
                </Field>
                <fieldset className="m-0 grid gap-2 border-0 p-0">
                  <legend className="mb-1 p-0 text-base font-semibold">Beat effect</legend>
                  <Field label="Strength" htmlFor="sv-pulse">
                    <select id="sv-pulse" className="field-input" value={form.beat_pulse || "subtle"} onChange={(e) => set("beat_pulse", e.target.value)}>
                      {Object.entries(d.pulse.levels).map(([k, label]) => <option key={k} value={k}>{label}{d.suggestion?.pulse === k ? " (suggested)" : ""}</option>)}
                    </select>
                  </Field>
                  {(form.beat_pulse || "subtle") !== "off" && (
                    <>
                      <div className="flex flex-wrap gap-x-4 gap-y-1">
                        {Object.entries(d.pulse.parts).map(([k, label]) => {
                          const all = Object.keys(d.pulse.parts);
                          const on = (form.pulse_parts ? form.pulse_parts.split(",") : all).includes(k);
                          return (
                            <label key={k} className="flex items-center gap-2 text-base">
                              <input type="checkbox" className="size-4 accent-cobalt" checked={on}
                                onChange={() => set("pulse_parts", all.filter((g) => (g === k ? !on : (form.pulse_parts ? form.pulse_parts.split(",") : all).includes(g))).join(",") || "none")} />
                              {label}
                            </label>
                          );
                        })}
                      </div>
                      <Field label="When" htmlFor="sv-when">
                        <select id="sv-when" className="field-input" value={form.pulse_when || "always"} onChange={(e) => set("pulse_when", e.target.value)}>
                          {Object.entries(d.pulse.when).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
                        </select>
                      </Field>
                    </>
                  )}
                  <p className="m-0 text-sm text-ink-soft">On each beat the picture brightens and pushes in a little, and chorus lines glow. Subtle is calm; Strong suits club and rock songs.</p>
                </fieldset>
                {d.suggestion && (() => {
                  const sg = d.suggestion;
                  const same = (form.mood_grade || "neon") === sg.grade && (form.lyric_style || "classic") === sg.style && (form.beat_pulse || "subtle") === sg.pulse;
                  return (
                    <p className="well m-0 flex flex-wrap items-center gap-x-3 gap-y-1 p-3 text-sm">
                      <span>Suggested for this {sg.reason}: <b>{d.grades[sg.grade]}</b> · <b>{d.styles[sg.style]?.split(" (")[0]}</b> lyrics</span>
                      {same ? <span className="text-ink-soft">In use</span> : (
                        <Button size="sm" variant="secondary" onClick={() => setForm({ ...form, mood_grade: sg.grade, lyric_style: sg.style, beat_pulse: sg.pulse })}>Use this</Button>
                      )}
                    </p>
                  );
                })()}
                <div className="flex flex-wrap gap-x-6 gap-y-1">
                  <label className="flex items-center gap-2 text-base"><input type="checkbox" className="size-4 accent-cobalt" checked={!!form.neon_intro} onChange={(e) => set("neon_intro", e.target.checked ? "1" : "")} /> Neon title intro</label>
                  <label className="flex items-center gap-2 text-base"><input type="checkbox" className="size-4 accent-cobalt" checked={!!form.now_playing} onChange={(e) => set("now_playing", e.target.checked ? "1" : "")} /> Now-playing card</label>
                </div>
                <p className="m-0 -mt-1 text-sm text-ink-soft">
                  Neon title intro: the song&apos;s name flickers on like a sign over the first seconds and fades before the singing starts (only when the song starts with a quiet intro). Now-playing card: a dark card in the top-left corner with the title, a progress bar and a spinning record.
                </p>
              </div>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img key={playing ? `play|${run}` : `${form.lyric_style}|${form.mood_grade}|${form.beat_pulse}|${form.pulse_parts}|${form.pulse_when}|${form.neon_intro}|${form.now_playing}|${shown}|${picBust}`}
                src={playing ? lyricStreamUrl(slug, from, look) : previewSrc} alt={playing ? "The lyric video playing" : "Preview frame of the lyric video"}
                onLoad={() => {
                  // the stream's first frame is up: the song starts with it, and the playhead follows the song
                  if (!playing || synced.current) return;
                  synced.current = true;
                  const a = audioRef.current;
                  if (a && d.audio) {
                    a.currentTime = from;
                    void a.play().catch(() => {});
                  }
                }}
                className="well w-full rounded-lg bg-black" style={{ aspectRatio: "16/9" }} />
              {d.audio && (
                <audio ref={audioRef} src={songFileUrl(slug, d.audio)} preload="auto"
                  onTimeUpdate={(e) => { if (playing && synced.current) setAt(Math.round(e.currentTarget.currentTime * 10) / 10); }}
                  onEnded={() => { setPlaying(false); setShown(0); setAt(0); }} />
              )}
            </div>
            <div className="grid gap-2 border-t border-line pt-4">
            <div className="grid gap-2">
              <div className="flex flex-wrap items-center gap-3">
                <Button size="sm" variant="primary" icon={playing ? <Pause className="size-3.5" /> : <Play className="size-3.5" />}
                  onClick={() => (playing ? stopPlaying() : playFrom(at >= (d.duration ?? 0) - 2 ? 0 : at))}>{playing ? "Pause" : "Play"}</Button>
                <span className="text-base font-semibold tabular-nums">{clock(Math.round(at))} <span className="font-normal text-ink-soft">/ {clock(Math.round(d.duration ?? 0))}</span></span>
                <span className="text-sm text-ink-soft">{playing ? "Playing the timeline with the song" : "Plays this look from the time on the timeline"}</span>
              </div>
              <SongStrip d={d} at={at} onAt={(t) => { if (playing) playFrom(t); else { setAt(t); setShown(t); } }} />
              <input id="sv-at" type="range" className="w-full accent-cobalt" aria-label="Song position" min={0} max={Math.max(Math.floor(d.duration ?? 0) - 1, 1)} step={1} value={at}
                onChange={(e) => setAt(Number(e.target.value))}
                onPointerUp={() => (playing ? playFrom(at) : setShown(at))} onKeyUp={() => (playing ? playFrom(at) : setShown(at))} />
            </div>
            <p className="m-0 text-sm text-ink-soft">The frame is drawn the way the render will draw it. Pick a time inside a sung line to see the lyric style. Save changes to keep it; the Short (9:16) uses the same look.</p>
            </div>
          </section>

          <LyricPicturesCard slug={slug} onTest={(t) => { if (playing) playFrom(Math.round(t)); else { setAt(Math.round(t)); setShown(Math.round(t)); } window.scrollTo({ top: 0, behavior: "smooth" }); }}
            onChanged={() => { setPicBust(String(Date.now())); void load(); }} />


          <section className="card grid gap-4 p-4">
            <h2 className="card-title">4. Make the videos</h2>
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

  async function remove(s: LyricSong) {
    try {
      await api.deleteLyricSong(s.slug);
      if (sel === s.slug) {
        setSel("new");
        setJob(null);
      }
      toast(`Deleted ${s.title}`, "success");
    } catch (e) {
      toast((e as Error).message, "error");
    }
    void loadList();
  }

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
            <li key={s.slug} className="group relative">
              <button type="button" onClick={() => { setSel(s.slug); setJob(null); }} aria-current={sel === s.slug}
                className={`w-full cursor-pointer rounded-lg border-0 py-2 pr-10 pl-3 text-left text-base ${sel === s.slug ? "bg-cobalt/10 font-semibold" : "bg-transparent hover:bg-ink/[0.05]"}`}>
                <span className="block truncate">{s.title}</span>
                <span className="text-sm text-ink-soft">{s.rendered ? "Rendered" : s.analyzed ? "Ready to render" : "Not timed yet"}</span>
              </button>
              <RowMenu item={{
                title: s.title, current: sel === s.slug,
                onClick: () => { setSel(s.slug); setJob(null); },
                deleteHint: "Deletes the song's folder: its audio, lyrics, pictures and every video made from it.",
                onDelete: () => void remove(s),
              }} />
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
