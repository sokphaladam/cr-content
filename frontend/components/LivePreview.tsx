"use client";

import { Pause, Play, RotateCcw } from "lucide-react";
import { useEffect, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent } from "react";
import { DEFAULT_CAPTIONS, fileUrl, keyword, type CaptionStyle, type Lang, type Options, type Scene, type TextOverlay } from "@/lib/api";
import { isImagePath } from "@/lib/format";
import { cutBefore, type DraftTimeline, type Segment } from "@/lib/useDraftTimeline";
import { clock } from "./Transcript";
import { Button, IconButton, Segmented, Spinner } from "./ui";

// The render's look (crcontent/captions.py), in container units of a 1080 x 1920 frame
const LANG_CAPTION = { en: { size: 92, words: 3 }, km: { size: 100, words: 1 } } as const;
const SIZE = { s: 0.8, m: 1, l: 1.25 } as const;
const OVERLAY_SIZE = { s: 0.6, m: 0.85, l: 1.2 } as const;
const cq = (px: number) => `${(px / 1080) * 100}cqw`;
const fontOf = (style: CaptionStyle, lang: Lang) => (style.font ? `"${style.font}"` : lang === "km" ? "var(--font-khmer)" : "Arial, Helvetica, sans-serif");
const cased = (text: string, style: CaptionStyle, lang: Lang) =>
  lang === "km" ? text : style.case === "upper" ? text.toUpperCase() : style.case === "lower" ? text.toLowerCase() : text;

/** CSS for how caption letters stand off the footage, matching the render's outline choices. */
function letterStyle(style: CaptionStyle, px: number): CSSProperties {
  switch (style.outline) {
    case "box":
      return { background: "rgb(0 0 0 / 0.67)", padding: `0 ${cq(px / 7)}`, boxDecorationBreak: "clone", WebkitBoxDecorationBreak: "clone" };
    case "shadow":
      return { textShadow: `${cq(px / 22)} ${cq(px / 22)} ${cq(3)} rgb(0 0 0 / 0.56)` };
    case "glow":
      return { WebkitTextStroke: `${cq((px / 18) * 2)} ${style.highlight}bf`, paintOrder: "stroke fill", textShadow: `0 0 ${cq(10)} ${style.highlight}` };
    default:
      return { WebkitTextStroke: `${cq(Math.round((px * 7) / 92) * 2)} #000`, paintOrder: "stroke fill", textShadow: `${cq(3)} ${cq(3)} 0 rgb(0 0 0 / 0.5)` };
  }
}

/** The caption on screen `t` seconds into a scene's voiceover; when paused between words, the last one shown. */
function captionAt(seg: Segment, t: number, perGroup: number, hold: boolean) {
  const v = seg.voice;
  if (!v) return null;
  // the render drops words that fall inside a cut, then groups the rest
  const words = v.words.filter((w) => !seg.cuts.some(([a, b]) => (w.start + w.end) / 2 >= a && (w.start + w.end) / 2 < b));
  const groups: (typeof words)[] = [];
  for (let i = 0; i < words.length; i += perGroup) groups.push(words.slice(i, i + perGroup));
  if (!groups.length) return null;
  let g = groups.findLastIndex((group) => group[0].start <= t);
  if (g < 0 && hold) g = 0;
  if (g < 0) return null;
  const end = g + 1 < groups.length ? groups[g + 1][0].start : groups[g].at(-1)!.end + 0.15;
  if (t >= end && !hold) return null;
  return { index: g, words: groups[g], spoken: groups[g].findLastIndex((w) => w.start <= t) };
}

/** One clip or photo, kept at `time` seconds in (looped) while the timeline plays or is scrubbed. */
function Media({ src, time, playing, className = "", zoom = 1 }: { src: string; time: number; playing: boolean; className?: string; zoom?: number }) {
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const el = video.current;
    if (!el || !el.duration) return;
    const want = time % el.duration;
    if (Math.abs(el.currentTime - want) > (playing ? 0.35 : 0.05)) el.currentTime = want;
    if (playing && el.paused) el.play().catch(() => {});
    if (!playing && !el.paused) el.pause();
  }, [time, playing]);
  if (isImagePath(src)) {
    // eslint-disable-next-line @next/next/no-img-element -- local engine file
    return <img src={fileUrl(src)} alt="" style={{ transform: zoom !== 1 ? `scale(${zoom})` : undefined }} className={`h-full w-full ${className}`} />;
  }
  return (
    <video
      ref={video}
      key={src}
      src={fileUrl(src)}
      muted
      loop
      playsInline
      preload="auto"
      onLoadedMetadata={(e) => (e.currentTarget.currentTime = time % e.currentTarget.duration)}
      className={`h-full w-full ${className}`}
    />
  );
}

/** The scene's footage in its layout: fill (cropped), fit (whole clip over a blurred copy) or split (two clips). */
function Footage({ seg, offset, playing }: { seg: Segment; offset: number; playing: boolean }) {
  const scene = seg.scene;
  const src = seg.footage;
  const time = offset + (scene.media_start ?? 0);
  const grade = "brightness-[0.94] saturate-[1.1]";
  if (scene.layout === "split") {
    return (
      <div className="absolute inset-0 grid grid-rows-2">
        <div className="relative overflow-hidden bg-[#222b3b]">{src && <Media src={src} time={time} playing={playing} className={`object-cover ${grade}`} />}</div>
        <div className="relative overflow-hidden bg-[#222b3b]">
          {seg.footage2 && <Media src={seg.footage2} time={offset} playing={playing} className={`object-cover ${grade}`} />}
        </div>
      </div>
    );
  }
  if (!src) return null;
  if (scene.layout === "fit") {
    return (
      <div className="absolute inset-0 overflow-hidden">
        <Media src={src} time={time} playing={playing} className="absolute inset-0 scale-110 object-cover blur-[3cqw] brightness-[0.8]" />
        <Media src={src} time={time} playing={playing} className={`absolute inset-0 object-contain ${grade}`} />
      </div>
    );
  }
  // a still photo gets the render's slow push-in, 1 -> 1.18 over the scene
  const zoom = isImagePath(src) ? 1 + 0.18 * Math.min(offset / Math.max(seg.length, 0.1), 1) : 1;
  return (
    <div className="absolute inset-0 overflow-hidden">
      <Media src={src} time={time} playing={playing} zoom={zoom} className={`object-cover ${grade}`} />
    </div>
  );
}

/** Drag something on the frame: reports its position as fractions of the frame (snapped to the middle lines). */
function useDrag(frame: React.RefObject<HTMLDivElement | null>, onMove: (x: number, y: number) => void) {
  const [dragging, setDragging] = useState(false);
  const snap = (v: number) => (Math.abs(v - 0.5) < 0.02 ? 0.5 : v);
  return {
    dragging,
    handlers: {
      onPointerDown(e: ReactPointerEvent<HTMLElement>) {
        if (e.button !== 0) return;
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.setPointerCapture(e.pointerId);
        setDragging(true);
      },
      onPointerMove(e: ReactPointerEvent<HTMLElement>) {
        const box = frame.current?.getBoundingClientRect();
        if (!dragging || !box) return;
        onMove(snap((e.clientX - box.left) / box.width), snap((e.clientY - box.top) / box.height));
      },
      onPointerUp(e: ReactPointerEvent<HTMLElement>) {
        e.currentTarget.releasePointerCapture(e.pointerId);
        setDragging(false);
      },
    },
  };
}

function Draggable({
  frame,
  onMove,
  className,
  style,
  label,
  children,
}: {
  frame: React.RefObject<HTMLDivElement | null>;
  onMove?: (x: number, y: number) => void;
  className: string;
  style: CSSProperties;
  label: string;
  children: React.ReactNode;
}) {
  const drag = useDrag(frame, onMove ?? (() => {}));
  if (!onMove)
    return (
      <div className={className} style={style}>
        {children}
      </div>
    );
  return (
    <div
      {...drag.handlers}
      title={label}
      className={`${className} cursor-grab touch-none rounded outline-offset-2 hover:outline hover:outline-2 hover:outline-dashed hover:outline-white/70 ${drag.dragging ? "cursor-grabbing outline outline-2 outline-dashed outline-white" : ""}`}
      style={style}
    >
      {children}
    </div>
  );
}

export interface FrameEdits {
  captions: CaptionStyle;
  setCaptions: (patch: Partial<CaptionStyle>) => void;
  patchScene: (uid: string, patch: (s: Scene) => Partial<Scene>) => void;
}

/** The frame at the playhead, drawn like the render. With `edit`, captions, headline and text can be dragged. */
export function LiveFrame({ timeline, lang, edit }: { timeline: DraftTimeline; lang: Lang; edit?: FrameEdits }) {
  const frame = useRef<HTMLDivElement>(null);
  const { segments, pos, playing } = timeline;
  const seg = segments[pos.i] ?? segments[0];
  const style = { ...DEFAULT_CAPTIONS, ...edit?.captions };
  if (!seg) return null;
  const scene = seg.scene;
  const offset = pos.t - cutBefore(seg.cuts, pos.t);
  const px = LANG_CAPTION[lang].size * SIZE[style.size];
  const font = fontOf(style, lang);
  const caption = captionAt(seg, pos.t, style.words || LANG_CAPTION[lang].words, !playing);
  const keys = new Set(scene.keywords ?? []);
  const counted = segments.filter((s) => s.length > 0);
  const broll = (scene.broll ?? []).find((b) => offset >= b.at && offset < b.at + b.duration);
  const texts = (scene.texts ?? []).map((t, k) => ({ t, k })).filter(({ t }) => t.text.trim() && offset >= t.at && offset < t.at + t.duration);
  const moveText = (k: number) => (x: number, y: number) =>
    edit?.patchScene(scene.uid, (s) => ({ texts: (s.texts ?? []).map((t, j) => (j === k ? { ...t, x, y } : t)) }));

  return (
    <div ref={frame} className="absolute inset-0">
      {seg.footage || scene.layout === "split" ? (
        <Footage seg={seg} offset={offset} playing={playing} />
      ) : (
        <div className="absolute inset-0 bg-[linear-gradient(160deg,#1e3c72,#2a5298_45%,#6a11cb)]">
          <p className="absolute inset-x-0 bottom-[14%] px-[8cqw] text-center text-[3.6cqw] leading-snug text-white/70">
            {timeline.findingFootage ? "Finding footage…" : scene.media ? "" : `No stock clip for “${scene.visual_query}” yet. The render draws a background instead.`}
          </p>
        </div>
      )}
      {broll && (
        <div className="absolute inset-0 overflow-hidden">
          <Media src={broll.media} time={offset - broll.at} playing={playing} className="object-cover brightness-[0.94] saturate-[1.1]" />
        </div>
      )}
      {scene.on_screen_text && (
        <Draggable
          frame={frame}
          label="Drag to move the headlines"
          onMove={edit && ((_, y) => edit.setCaptions({ headline_y: Math.min(Math.max(y - 0.02, 0.03), 0.85) }))}
          className="absolute left-1/2 w-max max-w-[85%] -translate-x-1/2"
          style={{ top: `${style.headline_y * 100}%` }}
        >
          <span
            lang={lang}
            style={{ fontFamily: font, fontSize: cq(px * 0.8), padding: `${cq(px * 0.8 * 0.15)} ${cq(px * 0.8 * 0.35)}` }}
            className="block bg-black/90 text-center leading-tight font-bold uppercase"
          >
            {scene.on_screen_text}
          </span>
        </Draggable>
      )}
      {texts.map(({ t, k }) => (
        <TextItem key={k} t={t} lang={lang} font={font} frame={frame} onMove={edit && moveText(k)} />
      ))}
      {caption && (
        <Draggable
          frame={frame}
          label="Drag to move the captions"
          onMove={edit && ((_, y) => edit.setCaptions({ y: Math.min(Math.max(y, 0.08), 0.92) }))}
          className="absolute inset-x-0 -translate-y-1/2"
          style={{ top: `${style.y * 100}%`, paddingInline: cq(90) }}
        >
          <p
            key={`${seg.index}-${caption.index}`}
            lang={lang}
            style={{ fontFamily: font, fontSize: cq(px), color: style.color }}
            className="m-0 animate-[caption-pop_90ms_ease-out] text-center leading-tight font-bold"
          >
            <span style={letterStyle(style, px)}>
              {caption.words.map((w, j) => (
                <span key={j} style={{ color: j === caption.spoken && (playing || pos.t >= w.start) ? style.highlight : keys.has(keyword(w.text)) ? style.keyword : undefined }}>
                  {cased(w.text, style, lang)}
                  {j < caption.words.length - 1 ? " " : ""}
                </span>
              ))}
            </span>
          </p>
        </Draggable>
      )}
      {counted.length > 0 && (
        <span className="pointer-events-none absolute top-[3.5cqw] right-[4cqw] rounded-full bg-black/55 px-[2.2cqw] py-[0.8cqw] text-[3.4cqw] font-semibold">
          {counted.indexOf(seg) + 1 || "–"} / {counted.length}
        </span>
      )}
    </div>
  );
}

function TextItem({
  t,
  lang,
  font,
  frame,
  onMove,
}: {
  t: TextOverlay;
  lang: Lang;
  font: string;
  frame: React.RefObject<HTMLDivElement | null>;
  onMove?: (x: number, y: number) => void;
}) {
  const px = LANG_CAPTION[lang].size * OVERLAY_SIZE[t.size];
  const look: CSSProperties = t.box
    ? { background: "rgb(0 0 0 / 0.8)", padding: `0 ${cq((px * 14) / 92)}` }
    : { WebkitTextStroke: `${cq(((px * 6) / 92) * 2)} #000`, paintOrder: "stroke fill", textShadow: `${cq(2)} ${cq(2)} 0 rgb(0 0 0 / 0.5)` };
  return (
    <Draggable
      frame={frame}
      label="Drag to move this text"
      onMove={onMove}
      className="absolute w-max max-w-[90%] -translate-x-1/2 -translate-y-1/2"
      style={{ left: `${t.x * 100}%`, top: `${t.y * 100}%` }}
    >
      <span lang={lang} style={{ fontFamily: font, fontSize: cq(px), color: t.color, ...look }} className="block text-center leading-tight font-bold">
        {t.text}
      </span>
    </Draggable>
  );
}

/** Background music the way the render mixes it in (looped, at a quarter volume; the render also ducks it under the voice). */
function useMusic(file: string, timeline: DraftTimeline) {
  const audio = useRef<HTMLAudioElement | null>(null);
  const { playing, now } = timeline;
  const pick = file && file !== "none" ? file : "";
  useEffect(() => {
    if (!pick) return;
    const el = new Audio(fileUrl(`assets/music/${pick}`));
    el.loop = true;
    el.volume = 0.25;
    audio.current = el;
    return () => {
      el.pause();
      audio.current = null;
    };
  }, [pick]);
  useEffect(() => {
    const el = audio.current;
    if (!el) return;
    if (!playing) return void el.pause();
    const want = el.duration ? now % el.duration : now;
    if (Math.abs(el.currentTime - want) > 0.5) el.currentTime = want;
    if (el.paused) el.play().catch(() => {});
  }, [playing, now]);
}

/** Play/pause, a scrubber over the whole video and the timeline's status, under the phone frame. */
export function LiveControls({ timeline, music }: { timeline: DraftTimeline; music: string }) {
  useMusic(music, timeline);
  const { playing, now, total, loading, pending, error } = timeline;
  return (
    <div className="grid gap-2">
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="primary"
          aria-label={playing ? "Pause preview" : "Play preview"}
          loading={pending && loading}
          icon={playing ? <Pause className="size-3.5 fill-current" /> : <Play className="size-3.5 fill-current" />}
          onClick={timeline.toggle}
        />
        <input
          type="range"
          aria-label="Position in the video"
          min={0}
          max={Math.max(total, 0.01)}
          step={0.01}
          value={Math.min(now, total)}
          disabled={!total}
          onChange={(e) => timeline.seekTime(Number(e.target.value))}
          className="h-1.5 min-w-0 flex-1 cursor-pointer accent-cobalt"
        />
        <span className="shrink-0 font-mono text-[11.5px] text-ink-soft tabular-nums">
          {clock(now)} / {clock(total)}
        </span>
      </div>
      {error ? (
        <p role="alert" className="m-0 flex items-center gap-2 text-xs text-danger">
          {error}
          <button type="button" className="cursor-pointer bg-transparent p-0 font-semibold text-danger underline" onClick={timeline.retry}>
            Try again
          </button>
        </p>
      ) : loading ? (
        <p role="status" className="m-0 flex items-center gap-1.5 text-xs text-ink-soft">
          <Spinner className="size-3" /> Making the voiceover…
        </p>
      ) : (
        <p className="m-0 text-center text-xs text-ink-soft">
          {timeline.active ? "Drag the captions, headline or text on the preview to move them." : "Press play to preview the whole video with its voiceover."}
          {music === "" && timeline.active && " Music is picked at random when rendering, so it isn't previewed."}
        </p>
      )}
    </div>
  );
}

const OUTLINE_LABELS: Record<CaptionStyle["outline"], string> = { outline: "Outline", box: "Box", shadow: "Shadow", glow: "Glow" };

/** Caption look for the whole video: a preset, then font, size, colours, outline, case and words per caption. */
export function CaptionPanel({ style, onChange, options, lang }: { style: CaptionStyle; onChange: (patch: Partial<CaptionStyle>) => void; options: Options; lang: Lang }) {
  const presets = options.captions?.presets ?? {};
  const fonts = options.styles?.fonts[lang] ?? [];
  const words = style.words || LANG_CAPTION[lang].words;
  return (
    <section aria-labelledby="caption-style" className="grid gap-3 rounded-xl border border-line bg-panel p-3.5">
      <div className="flex items-center justify-between">
        <h3 id="caption-style" className="m-0 font-display text-[14.5px] font-bold">
          Captions
        </h3>
        <IconButton label="Put captions and headlines back in place" onClick={() => onChange({ y: DEFAULT_CAPTIONS.y, headline_y: DEFAULT_CAPTIONS.headline_y })}>
          <RotateCcw className="size-3.5" />
        </IconButton>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {Object.entries(presets).map(([name, p]) => {
          const { label, ...look } = p;
          return (
            <button
              key={name}
              type="button"
              aria-pressed={style.preset === name}
              onClick={() => onChange({ ...look, font: look.font && fonts.includes(look.font) ? look.font : "", preset: name })}
              className={`h-7 cursor-pointer rounded-full border px-3 text-[12.5px] font-semibold ${
                style.preset === name ? "border-ink bg-ink text-white" : "border-line bg-panel text-ink hover:border-cobalt hover:text-cobalt"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <label className="grid gap-1">
          <span className="field-label">Font</span>
          <select className="field-input h-8 py-0 text-[12.5px]" value={style.font} onChange={(e) => onChange({ font: e.target.value })}>
            <option value="">Default</option>
            {fonts.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1">
          <span className="field-label">Outline</span>
          <select className="field-input h-8 py-0 text-[12.5px]" value={style.outline} onChange={(e) => onChange({ outline: e.target.value as CaptionStyle["outline"] })}>
            {Object.entries(OUTLINE_LABELS).map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1">
          <span className="field-label">Words at a time</span>
          <select className="field-input h-8 py-0 text-[12.5px]" value={words} onChange={(e) => onChange({ words: Number(e.target.value) })}>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <div className="grid gap-1">
          <span className="field-label">Size</span>
          <Segmented
            name="caption-size"
            size="sm"
            value={style.size}
            onChange={(v) => onChange({ size: v })}
            options={[
              { value: "s", label: "S" },
              { value: "m", label: "M" },
              { value: "l", label: "L" },
            ]}
          />
        </div>
      </div>
      {lang !== "km" && (
        <Segmented
          name="caption-case"
          size="sm"
          value={style.case}
          onChange={(v) => onChange({ case: v })}
          options={[
            { value: "as_is", label: "As written" },
            { value: "upper", label: "UPPER" },
            { value: "lower", label: "lower" },
          ]}
        />
      )}
      <div className="flex flex-wrap gap-3">
        {(
          [
            ["color", "Text"],
            ["highlight", "Spoken word"],
            ["keyword", "Keywords"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="flex items-center gap-1.5 text-[12.5px] font-semibold">
            <input type="color" className="size-7 cursor-pointer rounded border border-line bg-panel p-0.5" value={style[key]} onChange={(e) => onChange({ [key]: e.target.value.toUpperCase() })} />
            {label}
          </label>
        ))}
      </div>
    </section>
  );
}
