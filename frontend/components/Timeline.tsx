"use client";

import { ChevronDown, ChevronUp, Pause, Play, ZoomIn, ZoomOut } from "lucide-react";
import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { api, fileUrl } from "@/lib/api";
import { isImagePath } from "@/lib/format";
import { cutBefore, type DraftTimeline, type Segment } from "@/lib/useDraftTimeline";
import type { DraftScene } from "./SceneCard";
import type { Draft } from "./Storyboard";
import { clock } from "./Transcript";
import { Button, IconButton } from "./ui";

type Strip = { duration: number; frames: number; sprite: string };
type Peaks = { rate: number; peaks: number[] };
const VIDEO_H = 52;

/** What a pointer drag on the timeline is doing. */
type Drag =
  | { kind: "slip"; uid: string; x: number; from: number; max: number }
  | { kind: "scene"; uid: string; x: number; over: number }
  | { kind: "item"; uid: string; list: "broll" | "texts"; k: number; x: number; at: number; duration: number; edge: boolean; max: number };

/** Filmstrips and waveforms, fetched once per clip / voiceover. */
function useCache<T>(keys: string[], load: (key: string) => Promise<T>) {
  const [items, setItems] = useState<Record<string, T | null>>({});
  const missing = keys.filter((k) => !(k in items));
  const missingKey = missing.join("|");
  useEffect(() => {
    if (!missingKey) return;
    let cancelled = false;
    for (const key of missingKey.split("|")) {
      load(key)
        .then((v) => !cancelled && setItems((all) => ({ ...all, [key]: v })))
        .catch(() => !cancelled && setItems((all) => ({ ...all, [key]: null })));
    }
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- missingKey captures the keys to load
  }, [missingKey]);
  return items;
}

function Waveform({ seg, peaks, pps }: { seg: Segment; peaks: Peaks; pps: number }) {
  const bars: string[] = [];
  const every = Math.max(1, Math.round(peaks.rate / Math.min(pps, peaks.rate))); // about one bar per pixel
  for (let i = 0; i < peaks.peaks.length; i += every) {
    const t = i / peaks.rate;
    if (seg.cuts.some(([a, b]) => t >= a && t < b)) continue;
    const x = (t - cutBefore(seg.cuts, t)) * pps;
    const h = Math.max(1, peaks.peaks[i] * 26);
    bars.push(`M${x.toFixed(1)} ${15 - h / 2}v${h}`);
  }
  return (
    <svg aria-hidden className="absolute inset-y-0 left-0 h-full" width={seg.length * pps} viewBox={`0 0 ${seg.length * pps} 30`} preserveAspectRatio="none">
      <path d={bars.join("")} stroke="currentColor" strokeWidth={1} strokeLinecap="round" />
    </svg>
  );
}

/**
 * The draft on a time axis: scene blocks with filmstrips of their footage, cutaways and text, the voiceover's
 * waveform and the playhead. Click to jump there; drag a block's left edge to start its footage later in the clip,
 * drag a block to reorder scenes, drag B-roll and text to retime them (their right edge changes how long they last).
 */
export function Timeline({
  draft,
  setDraft,
  timeline,
  onActive,
  activeUid,
}: {
  draft: Draft;
  setDraft: (update: (d: Draft) => Draft) => void;
  timeline: DraftTimeline;
  onActive: (uid: string) => void;
  activeUid: string | null;
}) {
  const [open, setOpen] = useState(true);
  const [pps, setPps] = useState(40); // pixels per second
  const [drag, setDrag] = useState<Drag | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const { segments, total, now, playing } = timeline;
  const shown = segments.filter((s) => s.length > 0);

  const activate = timeline.activate;
  useEffect(() => {
    if (open) activate();
  }, [open, activate]);

  const strips = useCache<Strip>([...new Set(shown.flatMap((s) => [s.footage, ...(s.scene.broll ?? []).map((b) => b.media)]).filter((p): p is string => !!p))], api.filmstrip);
  const waves = useCache<Peaks>(shown.flatMap((s) => (s.voice ? [s.voice.key] : [])), api.voiceoverPeaks);

  // keep the playhead in view while playing
  useEffect(() => {
    const el = scroller.current;
    if (!el || !playing) return;
    const x = now * pps;
    if (x < el.scrollLeft || x > el.scrollLeft + el.clientWidth - 40) el.scrollLeft = Math.max(0, x - 80);
  }, [now, pps, playing]);

  const patchScene = (uid: string, patch: (s: DraftScene) => Partial<DraftScene>) =>
    setDraft((d) => ({ ...d, scenes: d.scenes.map((s) => (s.uid === uid ? { ...s, ...patch(s) } : s)) }));

  function timeAt(clientX: number) {
    const el = scroller.current!;
    return Math.max(0, (clientX - el.getBoundingClientRect().left + el.scrollLeft) / pps);
  }

  function begin(e: ReactPointerEvent<HTMLElement>, d: Drag) {
    if (e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    setDrag(d);
  }

  function move(e: ReactPointerEvent<HTMLElement>) {
    if (!drag) return;
    const dt = (e.clientX - drag.x) / pps;
    if (drag.kind === "slip") {
      patchScene(drag.uid, () => ({ media_start: Math.round(Math.min(Math.max(drag.from + dt, 0), drag.max) * 10) / 10 }));
    } else if (drag.kind === "scene") {
      const t = timeAt(e.clientX);
      const over = segments.findIndex((s) => s.length > 0 && t < s.start + s.length / 2);
      setDrag({ ...drag, over: over < 0 ? segments.length : over });
    } else {
      const round = (v: number) => Math.round(v * 10) / 10;
      patchScene(drag.uid, (s) => ({
        [drag.list]: (s[drag.list] ?? []).map((item, j) =>
          j !== drag.k
            ? item
            : drag.edge
              ? { ...item, duration: round(Math.min(Math.max(drag.duration + dt, 0.2), drag.max - drag.at)) }
              : { ...item, at: round(Math.min(Math.max(drag.at + dt, 0), Math.max(drag.max - drag.duration, 0))) },
        ),
      }));
    }
  }

  function end(e: ReactPointerEvent<HTMLElement>) {
    if (!drag) return;
    if (drag.kind === "scene") {
      const from = draft.scenes.findIndex((s) => s.uid === drag.uid);
      let to = drag.over;
      if (Math.abs(e.clientX - drag.x) < 4) onActive(drag.uid); // a click, not a drag
      else if (from >= 0 && to !== from && to !== from + 1) {
        if (to > from) to -= 1;
        setDraft((d) => {
          const scenes = [...d.scenes];
          const [moved] = scenes.splice(from, 1);
          scenes.splice(to, 0, moved);
          return { ...d, scenes };
        });
      }
    }
    setDrag(null);
  }

  const width = Math.max(total, 1) * pps + 120;
  const ticks = Array.from({ length: Math.ceil(total) + 1 }, (_, s) => s);
  const labelEvery = pps >= 60 ? 1 : pps >= 25 ? 5 : 10;

  return (
    <section aria-label="Timeline" className="shrink-0 border-t border-line bg-panel">
      <div className="flex h-10 items-center gap-2 px-3">
        <Button size="sm" variant="ghost" icon={open ? <ChevronDown className="size-3.5" /> : <ChevronUp className="size-3.5" />} onClick={() => setOpen((o) => !o)}>
          {open ? "Hide timeline" : "Timeline"}
        </Button>
        {open && (
          <>
            <IconButton label={playing ? "Pause" : "Play"} onClick={timeline.toggle}>
              {playing ? <Pause className="size-4 fill-current" /> : <Play className="size-4 fill-current" />}
            </IconButton>
            <span className="font-mono text-sm text-ink-soft tabular-nums">
              {clock(now)} / {clock(total)}
            </span>
            {drag?.kind === "slip" && (
              <span className="text-sm text-ink-soft">
                Footage starts {(draft.scenes.find((s) => s.uid === drag.uid)?.media_start ?? 0).toFixed(1)}s into the clip
              </span>
            )}
            <div className="ml-auto flex items-center gap-1">
              <IconButton label="Zoom out" onClick={() => setPps((p) => Math.max(10, Math.round(p / 1.5)))}>
                <ZoomOut className="size-4" />
              </IconButton>
              <input type="range" aria-label="Zoom" min={10} max={200} value={pps} onChange={(e) => setPps(Number(e.target.value))} className="w-24 accent-cobalt" />
              <IconButton label="Zoom in" onClick={() => setPps((p) => Math.min(200, Math.round(p * 1.5)))}>
                <ZoomIn className="size-4" />
              </IconButton>
            </div>
          </>
        )}
      </div>
      {open && (
        <div
          ref={scroller}
          className="relative overflow-x-auto overflow-y-hidden px-0 pb-2 select-none"
          onPointerDown={(e) => {
            if (e.button === 0 && e.target === e.currentTarget) timeline.seekTime(timeAt(e.clientX));
          }}
        >
          {!shown.length ? (
            <p className="m-0 px-3 py-6 text-base text-ink-soft">{timeline.loading ? "Making the voiceover…" : "Write a voiceover to see the timeline."}</p>
          ) : (
            <div
              className="relative"
              style={{ width }}
              onPointerMove={move}
              onPointerUp={end}
              onPointerDown={(e) => e.button === 0 && e.target === e.currentTarget && timeline.seekTime(timeAt(e.clientX))}
            >
              {/* ruler */}
              <div className="relative h-5 cursor-pointer" onPointerDown={(e) => timeline.seekTime(timeAt(e.clientX))}>
                {ticks.map((s) => (
                  <span key={s} className="absolute top-0 h-full border-l border-line" style={{ left: s * pps, height: s % labelEvery ? 6 : 12 }}>
                    {s % labelEvery === 0 && <span className="absolute top-0 left-1 font-mono text-2xs text-ink-soft">{s}</span>}
                  </span>
                ))}
              </div>

              {/* video */}
              <div className="relative" style={{ height: VIDEO_H }}>
                {shown.map((seg) => {
                  const s = seg.scene;
                  const strip = seg.footage ? strips[seg.footage] : null;
                  const photo = seg.footage && isImagePath(seg.footage);
                  const frameW = strip && strip.duration ? (pps * strip.duration) / strip.frames : 0;
                  const dragged = drag?.kind === "scene" && drag.uid === s.uid;
                  return (
                    <div
                      key={s.uid}
                      role="button"
                      tabIndex={0}
                      aria-label={`Scene ${seg.index + 1}, ${seg.length.toFixed(1)} seconds. Drag to reorder.`}
                      onKeyDown={(e) => e.key === "Enter" && onActive(s.uid)}
                      onPointerDown={(e) => begin(e, { kind: "scene", uid: s.uid, x: e.clientX, over: seg.index })}
                      className={`absolute top-0 h-full cursor-grab overflow-hidden rounded-md border-2 bg-[#222b3b] ${
                        s.uid === activeUid ? "border-cobalt" : "border-panel"
                      } ${dragged ? "opacity-60" : ""}`}
                      style={{
                        left: seg.start * pps,
                        width: Math.max(seg.length * pps - 2, 4),
                        backgroundImage: strip ? `url('${fileUrl(strip.sprite)}')` : undefined,
                        backgroundSize: photo ? "auto 100%" : frameW ? `${frameW * strip!.frames}px 100%` : undefined,
                        backgroundRepeat: "repeat-x",
                        backgroundPositionX: frameW ? -(s.media_start ?? 0) * pps : 0,
                      }}
                    >
                      <span className="pointer-events-none absolute top-1 left-2 rounded bg-black/60 px-1 text-2xs font-semibold text-white">
                        {seg.index + 1}
                        {s.layout && s.layout !== "fill" ? ` · ${s.layout === "fit" ? "Fit" : "Split"}` : ""}
                      </span>
                      {seg.footage && !photo && (
                        <span
                          role="slider"
                          aria-label="Where the footage starts in the clip"
                          aria-valuenow={s.media_start ?? 0}
                          title="Drag to start the footage later in the clip"
                          onPointerDown={(e) => begin(e, { kind: "slip", uid: s.uid, x: e.clientX, from: s.media_start ?? 0, max: Math.max((strip?.duration ?? 0) - 0.5, 0) })}
                          className="absolute inset-y-0 left-0 w-2 cursor-ew-resize bg-white/80 hover:bg-caption"
                        />
                      )}
                    </div>
                  );
                })}
                {drag?.kind === "scene" && (
                  <span
                    className="pointer-events-none absolute -top-1 h-[calc(100%+8px)] w-0.5 bg-cobalt"
                    style={{ left: (drag.over < segments.length ? segments[drag.over].start : total) * pps - 1 }}
                  />
                )}
              </div>

              {/* B-roll and text */}
              {(["broll", "texts"] as const).map((list) => (
                <div key={list} className="relative mt-1 h-5">
                  {shown.flatMap((seg) =>
                    (seg.scene[list] ?? []).map((item, k) => (
                      <div
                        key={`${seg.scene.uid}-${k}`}
                        title={list === "broll" ? "B-roll: drag to move, drag the right edge to change its length" : `Text “${"text" in item ? item.text : ""}”: drag to move`}
                        onPointerDown={(e) =>
                          begin(e, { kind: "item", uid: seg.scene.uid, list, k, x: e.clientX, at: item.at, duration: item.duration, edge: false, max: seg.length })
                        }
                        className={`absolute top-0 h-full cursor-grab overflow-hidden rounded px-1.5 text-2xs leading-5 font-semibold whitespace-nowrap ${
                          list === "broll" ? "bg-cobalt/80 text-white" : "bg-caption text-media"
                        }`}
                        style={{ left: (seg.start + item.at) * pps, width: Math.max(item.duration * pps, 6) }}
                      >
                        {list === "broll" ? "B-roll" : "text" in item ? item.text || "Text" : ""}
                        <span
                          onPointerDown={(e) =>
                            begin(e, { kind: "item", uid: seg.scene.uid, list, k, x: e.clientX, at: item.at, duration: item.duration, edge: true, max: seg.length })
                          }
                          className="absolute inset-y-0 right-0 w-1.5 cursor-ew-resize bg-black/25"
                        />
                      </div>
                    )),
                  )}
                </div>
              ))}

              {/* voice */}
              <div className="relative mt-1 h-[30px] text-cobalt/70">
                {shown.map((seg) => {
                  const peaks = seg.voice ? waves[seg.voice.key] : null;
                  return (
                    <div key={seg.scene.uid} className="absolute top-0 h-full overflow-hidden rounded bg-cobalt/[0.06]" style={{ left: seg.start * pps, width: Math.max(seg.length * pps - 2, 4) }}>
                      {peaks && <Waveform seg={seg} peaks={peaks} pps={pps} />}
                    </div>
                  );
                })}
              </div>

              {/* playhead */}
              <span className="pointer-events-none absolute top-0 bottom-0 w-0.5 bg-danger" style={{ left: now * pps }} />
            </div>
          )}
        </div>
      )}
    </section>
  );
}
