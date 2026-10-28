"use client";

import { Camera, Download, Dices, Paintbrush, Sparkles } from "lucide-react";
import { useCallback, useEffect, useId, useState } from "react";
import { api, ART_STYLES, MOOD_EFFECTS, type ArtStatus, type ArtStyle, type ArtSubject, type Aspect, type Effect, type Motion, type Scene } from "@/lib/api";
import { Button, Segmented } from "./ui";

/** Local AI art status (GPU, downloaded looks); live from the engine's event stream while a model downloads. */
export function useArtStatus() {
  const [status, setStatus] = useState<ArtStatus | null>(null);
  const reload = useCallback(() => {
    api.artStatus().then(setStatus).catch(() => setStatus(null));
  }, []);
  useEffect(reload, [reload]);
  const downloading = !!status && (!!status.addon?.installing || Object.values(status.styles).some((s) => s.downloading));
  useEffect(() => {
    if (!downloading) return;
    const stream = new EventSource(api.artProgressUrl);
    stream.onmessage = (e) => {
      try {
        setStatus(JSON.parse(e.data) as ArtStatus);
      } catch {
        /* a cut-off event: the next one comes a quarter second later */
      }
    };
    // the engine ends the stream once nothing is downloading; don't let the browser reconnect, just refresh
    stream.onerror = () => {
      stream.close();
      reload();
    };
    return () => stream.close();
  }, [downloading, reload]);
  return { status, reload };
}

const gb = (bytes: number) => (bytes / 1e9).toFixed(2);
const mbps = (bytes: number) => `${(bytes / 1e6).toFixed(1)} MB/s`;
const eta = (sec: number) => (sec >= 3600 ? `${Math.floor(sec / 3600)} h ${Math.round((sec % 3600) / 60)} min` : sec >= 60 ? `${Math.round(sec / 60)} min` : `${sec} s`);

/** A model download's bar: "4.2 of 6.9 GB · 61%", from the bytes on disk. */
export function DownloadProgress({ progress, label }: { progress: ArtStatus["styles"][ArtStyle]["progress"]; label: string }) {
  if (!progress) return null;
  const exact = progress.total ? Math.min(100, (progress.done / progress.total) * 100) : 0;
  const pct = Math.floor(exact);
  return (
    <div className="grid w-full max-w-[360px] gap-1">
      <div
        role="progressbar"
        aria-label={`Downloading the ${label} model`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        className="h-1.5 overflow-hidden rounded-full bg-ink/[0.08]"
      >
        <div className="h-full rounded-full bg-cobalt transition-[width] duration-300 ease-linear" style={{ width: `${exact}%` }} />
      </div>
      <span className="text-sm text-ink-soft tabular-nums">
        {gb(progress.done)} of {progress.total ? `${gb(progress.total)} GB · ${pct}%` : "about 7 GB"}
        {progress.active && !!progress.speed && ` · ${mbps(progress.speed)}`}
        {progress.active && progress.eta != null && ` · ${eta(progress.eta)} left`}
        {!progress.active && pct < 100 && " · paused (press Download to resume)"}
      </span>
    </div>
  );
}

/** The AI add-on's install: one bar for the whole download, then the unpacking step. */
export function AddonProgress({ addon }: { addon: NonNullable<ArtStatus["addon"]> }) {
  const pct = addon.total ? Math.min(100, (addon.done / addon.total) * 100) : 0;
  const left = addon.speed && addon.total > addon.done ? Math.round((addon.total - addon.done) / addon.speed) : null;
  return (
    <div className="grid w-full max-w-[420px] gap-1">
      <div role="progressbar" aria-label="Installing the AI add-on" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.floor(pct)} className="h-1.5 overflow-hidden rounded-full bg-ink/[0.08]">
        <div className={`h-full rounded-full bg-cobalt transition-[width] duration-300 ease-linear ${addon.total ? "" : "w-1/3 animate-pulse"}`} style={addon.total ? { width: `${pct}%` } : undefined} />
      </div>
      <span className="text-sm text-ink-soft tabular-nums">
        {addon.stage || "Starting…"}
        {addon.total > 0 && ` · ${gb(addon.done)} of ${gb(addon.total)} GB`}
        {!!addon.speed && ` · ${mbps(addon.speed)}`}
        {left != null && ` · ${eta(left)} left`}
      </span>
    </div>
  );
}

/** Why a look can't draw yet ("" = ready). */
export function artBlocker(status: ArtStatus | null, style: ArtStyle | ""): string {
  if (!style) return "";
  if (!status) return "Checking the AI art engine…";
  if (status.addon?.scope === "music") return "AI scene art needs an Apple Silicon Mac (M1 or newer). Stock footage will be used.";
  if (!status.installed) {
    if (status.addon?.installing) return "Installing the AI add-on…";
    return status.addon?.needed
      ? `AI scene art needs the AI add-on (one-time, ${status.addon.size}). Install it in Settings → AI features.`
      : "AI scene art isn't installed on this computer.";
  }
  if (!status.gpu) return "AI scene art needs an NVIDIA graphics card or an Apple Silicon Mac, and none was found. Stock footage will be used.";
  const s = status.styles[style];
  if (s.downloading) return `Downloading the ${s.label} model…`;
  if (!s.downloaded) return `The ${s.label} model isn't downloaded yet (about 7 GB, one time).`;
  return "";
}

/** Stock footage or one of the AI looks, with the model download right there when it's missing. */
export function ArtStylePicker({
  value,
  onChange,
  status,
  reload,
  stockLabel = "Stock footage",
}: {
  value: ArtStyle | "";
  onChange: (v: ArtStyle | "") => void;
  status: ArtStatus | null;
  reload: () => void;
  stockLabel?: string;
}) {
  const name = useId();
  const [error, setError] = useState("");
  const blocker = artBlocker(status, value);
  const style = value ? status?.styles[value] : undefined;
  return (
    <div className="grid gap-2">
      <Segmented
        name={name}
        size="sm"
        value={value || "stock"}
        onChange={(v) => onChange(v === "stock" ? "" : (v as ArtStyle))}
        options={[{ value: "stock", label: stockLabel }, ...ART_STYLES.map((s) => ({ value: s.value, label: s.label }))]}
      />
      {value && (
        <p className="m-0 flex flex-wrap items-center gap-2 text-sm text-ink-soft">
          {blocker || `${ART_STYLES.find((s) => s.value === value)?.hint}. Drawn on your ${status?.gpu ?? "GPU"}, free.`}
          {style && !style.downloaded && !style.downloading && status?.installed && status.gpu && (
            <Button
              size="sm"
              icon={<Download className="size-3.5" />}
              onClick={async () => {
                setError("");
                try {
                  await api.artDownload(value);
                  reload();
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            >
              Download model
            </Button>
          )}
          {(error || style?.error) && <span className="text-danger">{error || style?.error}</span>}
        </p>
      )}
      {value && style && !style.downloaded && <DownloadProgress progress={style.progress} label={style.label} />}
    </div>
  );
}

const MOTION_ORDER: Motion[] = ["dolly_3d", "orbit_3d", "rise_3d", "push_in", "pull_out", "pan_left", "pan_right", "tilt_up", "tilt_down", "still", "breathe"];

/** A scene's AI picture: its prompt, draw / another take, the camera move and atmosphere effects. */
export function ScenePicture({
  scene,
  style,
  status,
  aspect = "9:16",
  subject,
  used = [],
  onChange,
}: {
  scene: Scene & { uid: string };
  style: ArtStyle;
  subject?: ArtSubject; // the video's real subject: a picture showing it is checked, and drawn again when wrong
  used?: string[]; // media the video's other scenes use (so a real photo isn't repeated)
  status: ArtStatus | null;
  aspect?: Aspect;
  onChange: (patch: Partial<Scene>) => void;
}) {
  const [drawing, setDrawing] = useState(false);
  const [wrong, setWrong] = useState(false); // the last take still didn't show the real subject
  const [finding, setFinding] = useState(false);
  const [message, setMessage] = useState<{ text: string; error?: boolean }>({ text: "" });
  const blocker = artBlocker(status, style);
  const effects = scene.effects ?? [];
  const drawn = scene.media.startsWith("cache/gen/");

  // a picture drawn earlier: check it shows the real subject (once per picture; the engine keeps the verdict), so a
  // wrong animal is flagged here instead of only in the finished video
  const media = scene.media;
  const prompt = (scene.art_prompt || scene.visual_query).trim();
  const subjectText = subject?.subject.trim() ?? "";
  useEffect(() => {
    if (!drawn || !subjectText || !prompt) return;
    let alive = true;
    api
      .artCheck(media, subjectText, prompt)
      .then((r) => {
        if (!alive || r.score === null) return;
        const bad = r.score < 8;
        setWrong(bad);
        if (bad) setMessage({ text: `This picture doesn't look like a ${subjectText.split(":")[0].trim()} (${r.score}/10): ${r.problem}`, error: true });
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [drawn, media, subjectText, prompt]);

  async function draw(newTake: boolean) {
    const prompt = (scene.art_prompt || scene.visual_query).trim();
    if (!prompt) return setMessage({ text: "Describe the picture first, or press Plan pictures above.", error: true });
    setDrawing(true);
    setMessage({ text: "Drawing… about 30 seconds (longer the first time, while the model loads)." });
    try {
      const seed = newTake ? Math.floor(Math.random() * 2 ** 31) : scene.art_seed || undefined;
      const m = await api.artDraw({ prompt, style, seed, aspect, ...subject });
      onChange({ media: m.media, media_start: 0, art_seed: m.seed, art_prompt: prompt });
      setWrong(m.score !== null && m.score < 8);
      setMessage(
        m.score !== null && m.score < 8
          ? { text: `Still not quite right after 3 takes (${m.score}/10): ${m.problem} Use a real photo instead, or edit the prompt.`, error: true }
          : { text: "" },
      );
    } catch (e) {
      setMessage({ text: (e as Error).message, error: true });
    } finally {
      setDrawing(false);
    }
  }

  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2 rounded-lg border border-line/70 bg-sunken p-2.5">
      <div className="flex items-center justify-between gap-2">
        <label className="field-label" htmlFor={`art-${scene.uid}`}>
          Picture
        </label>
        <div className="flex flex-wrap items-center gap-1">
          <Button size="sm" variant="ghost" icon={<Paintbrush className="size-3.5" />} loading={drawing} disabled={!!blocker} onClick={() => draw(false)}>
            {drawn ? "Redraw" : "Draw"}
          </Button>
          <Button size="sm" variant="ghost" icon={<Dices className="size-3.5" />} disabled={!!blocker || drawing} onClick={() => draw(true)} title="The same prompt, a different picture">
            Another take
          </Button>
        </div>
      </div>
      <textarea
        id={`art-${scene.uid}`}
        rows={2}
        value={scene.art_prompt ?? ""}
        onChange={(e) => onChange({ art_prompt: e.target.value })}
        placeholder={scene.media ? "Your chosen footage is used for this scene." : "Written by Gemini when you press Plan pictures or render. Or describe it yourself."}
        className="field-input field-sizing-content min-h-[52px] resize-none text-base leading-snug"
      />
      <div className="flex flex-wrap items-center gap-1.5">
        <select
          aria-label="Camera move"
          className="field-input h-7 w-auto py-0 text-sm"
          value={scene.motion || ""}
          onChange={(e) => onChange({ motion: e.target.value as Motion | "" })}
        >
          <option value="">Camera: auto</option>
          {MOTION_ORDER.map((m) => (
            <option key={m} value={m}>
              {status?.motions[m] ?? m}
            </option>
          ))}
        </select>
        {MOOD_EFFECTS.filter((e) => e !== "speed_lines" || style === "anime").map((e: Effect) => {
          const on = effects.includes(e);
          return (
            <button
              key={e}
              type="button"
              aria-pressed={on}
              onClick={() => onChange({ effects: on ? effects.filter((x) => x !== e) : [...effects, e] })}
              className={`inline-flex h-7 cursor-pointer items-center gap-1 rounded-full border px-2.5 text-sm font-semibold transition-colors ${
                on ? "border-cobalt bg-cobalt/10 text-cobalt" : "border-line bg-panel text-ink-soft hover:border-line-strong hover:text-ink"
              }`}
            >
              {on && <Sparkles className="size-3" aria-hidden />}
              {status?.effects[e] ?? e}
            </button>
          );
        })}
      </div>
      {(message.text || blocker) && (
        <p role={message.error ? "alert" : "status"} className={`m-0 text-sm ${message.error ? "text-danger" : "text-ink-soft"}`}>
          {message.text || blocker}
        </p>
      )}
      {wrong && subject?.subject && (
        <Button
          size="sm"
          variant="secondary"
          className="justify-self-start"
          icon={<Camera className="size-3.5" />}
          loading={finding}
          title="A real clip or photo of the subject (stock, else Wikimedia Commons), checked to really show it; its credit goes into the description"
          onClick={async () => {
            setFinding(true);
            try {
              const m = await api.artReal(subject.subject, used);
              onChange({ media: m.media, media_start: 0 });
              setWrong(false);
              setMessage({ text: m.credit ? `Real photo in. ${m.credit} (added to the description).` : "Real footage in." });
            } catch (e) {
              setMessage({ text: (e as Error).message, error: true });
            } finally {
              setFinding(false);
            }
          }}
        >
          <span className="truncate" title={`Use a real photo of the ${subject.subject.split(":")[0].trim()}`}>
            Use a real photo
          </span>
        </Button>
      )}
    </div>
  );
}
