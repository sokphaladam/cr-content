"use client";

import { useEffect, useLayoutEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { ImageIcon } from "lucide-react";
import { fmt, lineEnd, lineStart, MIN_LINE, PEAKS_PER_SECOND, round, type PictureClip, type Row } from "@/lib/lyricTiming";
import { fileUrl, type Aspect, type Lang, type SongArtSlot } from "@/lib/api";
import { useFilmstrip } from "@/lib/useFilmstrip";

export const MIN_PPS = 2;
export const MAX_PPS = 400;
const PAD = 48; // room after the song's end, so its last line can be dragged and trimmed
const SNAP_PX = 7;

type Drag = { uid: string; mode: "move" | "start" | "end"; x0: number; start0: number; end0: number; moved: boolean };
type Preview = { uid: string; start: number; end: number } | null;

/** Ruler spacing: the smallest step that keeps labels at least ~72px apart. */
function rulerStep(pps: number) {
  return [0.5, 1, 2, 5, 10, 15, 30, 60, 120].find((s) => s * pps >= 72) ?? 300;
}

const FRAME_H = 40; // filmstrip frame height in px (the render lane is 2.75rem)

/** The song as tracks: a time ruler, its sections, the last render as a filmstrip, the planned pictures, one block per
 *  lyric line (drag to move, drag an edge to trim) and the waveform. Click or drag on the ruler or waveform to move the playhead; Ctrl + wheel zooms around the pointer. */
export function LyricTimeline({
  lines,
  sections,
  lang,
  duration,
  now,
  playing,
  follow,
  selected,
  peaks,
  clips,
  slots,
  renderSrc,
  aspect,
  pps,
  onZoom,
  onSeek,
  onSelect,
  onMove,
  onTrim,
}: {
  lines: Row[];
  sections: string[];
  lang: Lang;
  duration: number;
  now: number;
  playing: boolean;
  follow: boolean;
  selected: string | null;
  peaks: Float32Array | null;
  clips: PictureClip[]; // the planned pictures placed on the song
  slots: SongArtSlot[];
  renderSrc: string | null; // the last rendered music video, for the filmstrip
  aspect: Aspect;
  pps: number; // zoom: pixels per second
  onZoom: (pps: number) => void;
  onSeek: (t: number) => void;
  onSelect: (uid: string) => void;
  onMove: (uid: string, start: number) => void;
  onTrim: (uid: string, edge: "start" | "end", t: number) => void;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [view, setView] = useState({ left: 0, width: 800 });
  const [drag, setDrag] = useState<Drag | null>(null);
  const [preview, setPreview] = useState<Preview>(null);
  const zoomAnchor = useRef<{ t: number; x: number } | null>(null);
  const scrubbing = useRef(false);
  const width = Math.ceil(duration * pps) + PAD;

  // filmstrip of the last render: one frame per tile, only for what's on screen
  const frameW = (FRAME_H * (aspect === "16:9" ? 16 : 9)) / (aspect === "16:9" ? 9 : 16);
  const frameStep = [0.5, 1, 2, 5, 10, 15, 30, 60].find((s) => s * pps >= frameW) ?? 120;
  const frameTimes: number[] = [];
  if (renderSrc) {
    const from = Math.max(0, Math.floor(view.left / pps / frameStep) - 1) * frameStep;
    const to = Math.min(duration, (view.left + view.width) / pps + frameStep);
    for (let t = from; t <= to; t += frameStep) frameTimes.push(round(t));
  }
  const frames = useFilmstrip(renderSrc, frameTimes, FRAME_H * 2);

  // track the visible window (the waveform only draws what's on screen)
  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const update = () => setView({ left: el.scrollLeft, width: el.clientWidth });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    el.addEventListener("scroll", update, { passive: true });
    return () => {
      ro.disconnect();
      el.removeEventListener("scroll", update);
    };
  }, []);

  // keep the time under the pointer in place while zooming
  useLayoutEffect(() => {
    const a = zoomAnchor.current;
    const el = scroller.current;
    if (!a || !el) return;
    el.scrollLeft = a.t * pps - a.x;
    zoomAnchor.current = null;
  }, [pps]);

  // Ctrl/⌘ + wheel zooms (a non-passive listener, so the page itself doesn't zoom)
  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      const x = e.clientX - el.getBoundingClientRect().left;
      zoomAnchor.current = { t: (el.scrollLeft + x) / pps, x };
      onZoom(Math.min(MAX_PPS, Math.max(MIN_PPS, pps * (e.deltaY < 0 ? 1.2 : 1 / 1.2))));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [pps, onZoom]);

  // follow the playhead while playing
  useEffect(() => {
    const el = scroller.current;
    if (!el || !follow || !playing || drag) return;
    const x = now * pps;
    if (x < el.scrollLeft + 24 || x > el.scrollLeft + el.clientWidth - 64) el.scrollLeft = x - el.clientWidth * 0.2;
  }, [now, pps, follow, playing, drag]);

  // bring the selected line into view when it's picked elsewhere (the list, the keyboard)
  useEffect(() => {
    const el = scroller.current;
    const line = lines.find((l) => l.uid === selected);
    if (!el || !line || drag) return;
    const a = lineStart(line) * pps;
    const b = lineEnd(line) * pps;
    if (a < el.scrollLeft || b > el.scrollLeft + el.clientWidth) el.scrollTo({ left: Math.max(0, a - 80), behavior: "smooth" });
    // only when the selection changes, not on every edit of it
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  // waveform
  useEffect(() => {
    const c = canvas.current;
    if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    const w = view.width;
    const h = c.clientHeight;
    if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) {
      c.width = Math.round(w * dpr);
      c.height = Math.round(h * dpr);
    }
    const g = c.getContext("2d");
    if (!g) return;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    const css = getComputedStyle(c);
    const played = css.getPropertyValue("--wave-played").trim() || "#6079ff";
    const rest = css.getPropertyValue("--wave-rest").trim() || "#98a1b1";
    const mid = h / 2;
    if (!peaks) {
      g.fillStyle = rest;
      g.globalAlpha = 0.35;
      g.fillRect(0, mid - 0.5, w, 1);
      return;
    }
    for (let x = 0; x < w; x++) {
      const t0 = (view.left + x) / pps;
      const t1 = (view.left + x + 1) / pps;
      if (t0 > duration) break;
      const i0 = Math.floor(t0 * PEAKS_PER_SECOND);
      const i1 = Math.max(i0 + 1, Math.floor(t1 * PEAKS_PER_SECOND));
      let p = 0;
      for (let i = i0; i < i1 && i < peaks.length; i++) p = Math.max(p, peaks[i]);
      const bar = Math.max(1, p * (h - 6));
      g.fillStyle = t0 < now ? played : rest;
      g.globalAlpha = t0 < now ? 0.9 : 0.55;
      g.fillRect(x, mid - bar / 2, 1, bar);
    }
  }, [peaks, view, pps, now, duration]);

  const timeAt = (clientX: number) => {
    const el = scroller.current!;
    return Math.min(duration, Math.max(0, (clientX - el.getBoundingClientRect().left + el.scrollLeft) / pps));
  };

  const scrub = {
    onPointerDown: (e: ReactPointerEvent) => {
      if (e.button !== 0) return;
      e.currentTarget.setPointerCapture(e.pointerId);
      scrubbing.current = true;
      onSeek(timeAt(e.clientX));
    },
    onPointerMove: (e: ReactPointerEvent) => scrubbing.current && onSeek(timeAt(e.clientX)),
    onPointerUp: () => {
      scrubbing.current = false;
    },
  };

  /** Snap `t` to the playhead or a neighbouring line's edge when it's within a few pixels of one. */
  const snap = (t: number, uid: string) => {
    const targets = [now];
    for (const l of lines) if (l.uid !== uid) targets.push(lineStart(l), lineEnd(l));
    let best = t;
    let dist = SNAP_PX / pps;
    for (const s of targets) if (Math.abs(s - t) < dist) [best, dist] = [s, Math.abs(s - t)];
    return best;
  };

  const startDrag = (e: ReactPointerEvent, line: Row, mode: Drag["mode"]) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    setDrag({ uid: line.uid, mode, x0: e.clientX, start0: lineStart(line), end0: lineEnd(line), moved: false });
    onSelect(line.uid);
  };
  const moveDrag = (e: ReactPointerEvent) => {
    if (!drag) return;
    const dx = e.clientX - drag.x0;
    if (!drag.moved && Math.abs(dx) < 3) return;
    const dt = dx / pps;
    const len = drag.end0 - drag.start0;
    let start = drag.start0;
    let end = drag.end0;
    if (drag.mode === "move") {
      start = Math.max(0, drag.start0 + dt);
      const snappedStart = snap(start, drag.uid);
      const snappedEnd = snap(start + len, drag.uid);
      start = snappedStart !== start ? snappedStart : snappedEnd !== start + len ? snappedEnd - len : start;
      start = Math.max(0, start);
      end = start + len;
    } else if (drag.mode === "start") {
      start = Math.min(drag.end0 - MIN_LINE, Math.max(0, snap(drag.start0 + dt, drag.uid)));
    } else {
      end = Math.max(drag.start0 + MIN_LINE, snap(drag.end0 + dt, drag.uid));
    }
    setDrag({ ...drag, moved: true });
    setPreview({ uid: drag.uid, start: round(start), end: round(end) });
  };
  const endDrag = () => {
    if (drag?.moved && preview) {
      if (drag.mode === "move") onMove(drag.uid, preview.start);
      else onTrim(drag.uid, drag.mode, drag.mode === "start" ? preview.start : preview.end);
    }
    setDrag(null);
    setPreview(null);
  };

  // sections: one band per run of lines in the same section
  const bands: { name: string; start: number; end: number; key: string }[] = [];
  for (const l of lines) {
    const last = bands.at(-1);
    if (last && last.name === (sections[l.section] ?? "")) last.end = lineEnd(l);
    else bands.push({ name: sections[l.section] ?? "", start: lineStart(l), end: lineEnd(l), key: l.uid });
  }

  const rows = ["1.5rem", "1.25rem", renderSrc ? "2.75rem" : "", clips.length ? "2.75rem" : "", "3.25rem", "3rem"].filter(Boolean).join(" ");
  const step = rulerStep(pps);
  const ticks: number[] = [];
  for (let t = 0; t <= duration + 0.001; t += step) ticks.push(t);
  const minor = step / (step >= 10 ? 5 : step >= 2 ? 4 : 5);

  return (
    <div className="flex min-h-0 select-none">
      <div aria-hidden className="grid w-[4.5rem] shrink-0 border-r border-line text-2xs font-semibold tracking-wide text-ink-soft uppercase" style={{ gridTemplateRows: rows }}>
        <span />
        <span className="flex items-center px-2.5">Parts</span>
        {renderSrc && <span className="flex items-center px-2.5">Render</span>}
        {clips.length > 0 && <span className="flex items-center px-2.5">Pictures</span>}
        <span className="flex items-center px-2.5">Lyrics</span>
        <span className="flex items-center px-2.5">Audio</span>
      </div>
      <div ref={scroller} className="relative min-w-0 flex-1 overflow-x-auto overflow-y-hidden" role="group" aria-label="Timeline">
        <div className="relative grid" style={{ width, gridTemplateRows: rows }}>
          {/* ruler */}
          <div
            {...scrub}
            className="relative cursor-text border-b border-line bg-sunken"
            style={{ backgroundImage: `repeating-linear-gradient(to right, var(--color-line) 0 1px, transparent 1px ${minor * pps}px)`, backgroundSize: `100% 30%`, backgroundRepeat: "repeat-x", backgroundPosition: "bottom" }}
          >
            {ticks.map((t) => (
              <span key={t} className="absolute top-0 bottom-0 border-l border-line-strong pl-1 font-mono text-2xs leading-[1.1rem] text-ink-soft tabular-nums" style={{ left: t * pps }}>
                {fmt(t, step < 1 ? 1 : 0)}
              </span>
            ))}
          </div>

          {/* sections */}
          <div {...scrub} className="relative cursor-text">
            {bands.map((b) => (
              <span
                key={b.key}
                title={b.name}
                className="absolute top-[3px] bottom-[3px] overflow-hidden rounded-sm bg-ink/[0.07] px-1.5 text-2xs leading-[0.9rem] font-semibold text-ink-soft"
                style={{ left: b.start * pps, width: Math.max(2, (b.end - b.start) * pps) }}
              >
                <span className="block truncate">{b.name}</span>
              </span>
            ))}
          </div>

          {/* the last render, as a filmstrip */}
          {renderSrc && (
            <div {...scrub} className="relative cursor-text overflow-hidden border-t border-line bg-black/80">
              {frameTimes.map((t) =>
                frames[t] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={t}
                    src={frames[t]}
                    alt=""
                    draggable={false}
                    className="pointer-events-none absolute top-[3px] bottom-[3px] border-r border-black object-cover"
                    style={{ left: t * pps, width: frameStep * pps }}
                  />
                ) : (
                  <span key={t} className="absolute top-[3px] bottom-[3px] border-r border-black bg-white/[0.06]" style={{ left: t * pps, width: frameStep * pps }} />
                ),
              )}
            </div>
          )}

          {/* planned pictures */}
          {clips.length > 0 && (
            <div {...scrub} className="relative cursor-text border-t border-line">
              {clips.map((c, i) => {
                const slot = slots[c.slot];
                const pic = slot?.picture;
                const w = Math.max(2, (c.end - c.start) * pps);
                const showing = c.start <= now && now < c.end;
                return (
                  <div
                    key={i}
                    title={`${c.section} · ${fmt(c.start, 1)}–${fmt(c.end, 1)} · ${slot?.prompt ?? ""}${pic ? "" : " (not drawn yet)"}`}
                    className={`absolute top-[3px] bottom-[3px] overflow-hidden rounded-sm border ${
                      pic ? "border-black/60 bg-media" : "border-dashed border-line-strong bg-ink/[0.04]"
                    } ${showing ? "ring-2 ring-caption/80" : ""}`}
                    style={{
                      left: c.start * pps,
                      width: w,
                      backgroundImage: pic && pic.kind === "photo" ? `url("${fileUrl(pic.media)}")` : undefined,
                      backgroundSize: "auto 100%",
                      backgroundRepeat: "repeat-x",
                    }}
                  >
                    {!pic && w > 24 && (
                      <span className="flex h-full items-center gap-1 px-1.5 text-2xs text-ink-soft">
                        <ImageIcon className="size-3 shrink-0" />
                        <span className="truncate">{slot?.prompt}</span>
                      </span>
                    )}
                    {pic && w > 48 && (
                      <span className="absolute bottom-0 left-0 max-w-full truncate rounded-tr-sm bg-black/60 px-1 text-2xs leading-tight text-white/85">{c.section}</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* lyric blocks */}
          <div {...scrub} className="relative cursor-text border-y border-line bg-ink/[0.025]">
            {lines.map((l, i) => {
              const p = preview?.uid === l.uid ? preview : null;
              const s = p ? p.start : lineStart(l);
              const e = p ? p.end : lineEnd(l);
              const w = Math.max(3, (e - s) * pps);
              const isSel = l.uid === selected;
              const singing = s <= now && now <= e;
              const tone = isSel
                ? "border-cobalt bg-cobalt text-white"
                : l.check
                  ? "border-warn/70 bg-warn/20 text-ink"
                  : "border-cobalt/40 bg-cobalt/15 text-ink hover:border-cobalt/80";
              return (
                <div
                  key={l.uid}
                  role="button"
                  tabIndex={-1}
                  aria-label={`Line ${i + 1}: ${l.text}, ${fmt(s, 2)} to ${fmt(e, 2)}`}
                  title={`${l.text}\n${fmt(s, 2)} – ${fmt(e, 2)} (${(e - s).toFixed(2)} s)`}
                  onPointerDown={(ev) => startDrag(ev, l, "move")}
                  onPointerMove={moveDrag}
                  onPointerUp={endDrag}
                  onPointerCancel={endDrag}
                  onDoubleClick={() => onSeek(s)}
                  className={`group absolute top-1.5 bottom-1.5 cursor-grab overflow-hidden rounded-md border text-xs leading-tight active:cursor-grabbing ${tone} ${
                    singing && !isSel ? "ring-2 ring-caption/80" : ""
                  } ${p ? "z-10 shadow-(--shadow-pop)" : ""}`}
                  style={{ left: s * pps, width: w }}
                >
                  {w > 22 && (
                    <span lang={lang} className="pointer-events-none block truncate px-1.5 pt-1 font-semibold">
                      {l.text}
                    </span>
                  )}
                  {w > 60 && <span className="pointer-events-none block truncate px-1.5 font-mono text-2xs opacity-70">{(e - s).toFixed(1)} s</span>}
                  <span
                    aria-hidden
                    onPointerDown={(ev) => startDrag(ev, l, "start")}
                    className={`absolute inset-y-0 left-0 w-1.5 cursor-ew-resize ${isSel ? "bg-white/40" : "bg-transparent group-hover:bg-cobalt/50"}`}
                  />
                  <span
                    aria-hidden
                    onPointerDown={(ev) => startDrag(ev, l, "end")}
                    className={`absolute inset-y-0 right-0 w-1.5 cursor-ew-resize ${isSel ? "bg-white/40" : "bg-transparent group-hover:bg-cobalt/50"}`}
                  />
                </div>
              );
            })}
          </div>

          {/* waveform: a viewport-wide canvas that stays put while the tracks scroll under it */}
          <div {...scrub} className="relative cursor-text">
            <canvas
              ref={canvas}
              aria-hidden
              className="sticky left-0 block h-full [--wave-played:var(--color-cobalt)] [--wave-rest:var(--color-ink-soft)]"
              style={{ width: view.width }}
            />
          </div>

          {/* playhead */}
          <div aria-hidden className="pointer-events-none absolute top-0 bottom-0 z-20 w-px bg-caption" style={{ left: now * pps }}>
            <span className="absolute -top-px -left-[5px] size-0 border-x-[5px] border-t-[7px] border-x-transparent border-t-caption" />
          </div>
          {preview && (
            <div aria-hidden className="pointer-events-none absolute top-0 z-20 -translate-x-1/2 rounded bg-ink px-1.5 py-px font-mono text-2xs text-on-ink tabular-nums" style={{ left: (drag?.mode === "end" ? preview.end : preview.start) * pps }}>
              {fmt(drag?.mode === "end" ? preview.end : preview.start, 2)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
