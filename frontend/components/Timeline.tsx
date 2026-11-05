"use client";

import { ChevronDown, ChevronUp, Copy, Eye, EyeOff, Lock, LockOpen, Pause, Play, Plus, Scissors, Trash2, ZoomIn, ZoomOut } from "lucide-react";
import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";
import { api, fileUrl, type Clip, type TrackName, type TrackState } from "@/lib/api";
import { duplicateIn, makeClip, moveTo, replace, snap, SNAP_PX, snapTargets, splitAt, trackOf, trimEnd, trimStart } from "@/lib/clips";
import { templateDefaults } from "@/lib/templates";
import { soundLength, useCatalog } from "./ClipInspector";
import { isImagePath } from "@/lib/format";
import { cutBefore, type DraftTimeline, type Segment } from "@/lib/useDraftTimeline";
import type { ItemRef } from "./LivePreview";
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
  | { kind: "item"; uid: string; list: "broll" | "texts"; k: number; x: number; at: number; duration: number; edge: boolean; max: number }
  | { kind: "clip"; id: string; mode: "move" | "start" | "end"; x: number; orig: Clip; moved: boolean };

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

/** A sound clip's waveform: the trimmed part of its file. */
function ClipWave({ c, peaks, pps }: { c: Clip; peaks: Peaks; pps: number }) {
  const bars: string[] = [];
  const every = Math.max(1, Math.round(peaks.rate / Math.min(pps, peaks.rate)));
  const from = Math.floor(c.source_in * peaks.rate);
  const to = Math.min(peaks.peaks.length, Math.ceil((c.source_in + c.duration) * peaks.rate));
  for (let i = from; i < to; i += every) {
    const h = Math.max(1, Math.min(peaks.peaks[i] * c.gain, 1) * 10);
    bars.push(`M${((i / peaks.rate - c.source_in) * pps).toFixed(1)} ${12 - h}v${h * 2}`);
  }
  return (
    <svg aria-hidden className="pointer-events-none absolute inset-y-0 left-0 h-full opacity-60" width={c.duration * pps} viewBox={`0 0 ${c.duration * pps} 24`} preserveAspectRatio="none">
      <path d={bars.join("")} stroke="currentColor" strokeWidth={1} />
    </svg>
  );
}

/** A small toggle in a lane's header (mute, solo, lock, hide). */
function LaneToggle({ on, label, onClick, children }: { on: boolean; label: string; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      aria-label={label}
      title={label}
      onClick={onClick}
      className={`grid h-5 min-w-5 cursor-pointer place-items-center rounded px-0.5 text-2xs font-bold ${on ? "bg-cobalt/25 text-ink" : "bg-transparent text-ink-soft hover:bg-ink/10"}`}
    >
      {children}
    </button>
  );
}

const LANES: Record<TrackName, string> = { voice: "Voice", music: "Music", graphics: "Graphics", sfx: "Sounds" };

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
  activeItem = null,
  onSelectItem,
  activeClip = null,
  onSelectClip,
}: {
  draft: Draft;
  setDraft: (update: (d: Draft) => Draft) => void;
  timeline: DraftTimeline;
  onActive: (uid: string) => void;
  activeUid: string | null;
  activeItem?: ItemRef | null;
  onSelectItem?: (item: ItemRef) => void; // a click (not a drag) or Enter on a B-roll / text clip
  activeClip?: string | null; // the selected graphic / sound clip
  onSelectClip?: (id: string, seek: boolean) => void; // seek: also move the playhead to it (a click, not a drag)
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
  const cat = useCatalog();
  const clips = draft.clips ?? [];
  const tracks = draft.tracks ?? {};
  const sfxWaves = useCache<Peaks>([...new Set(clips.filter((c) => c.track === "sfx" && c.sound).map((c) => c.sound))], api.sfxPeaks);
  const setClips = (f: (cs: Clip[]) => Clip[]) => setDraft((d) => ({ ...d, clips: f(d.clips ?? []) }));
  const setTrack = (name: TrackName, patch: Partial<TrackState>) =>
    setDraft((d) => ({ ...d, tracks: { ...d.tracks, [name]: { ...trackOf(d.tracks, name), ...patch } } }));
  // where clip edges stick: the playhead, scene cuts and every spoken word's start
  const marks = [
    now,
    ...shown.flatMap((s) => [s.start, s.start + s.length]),
    ...shown.flatMap((s) =>
      (s.voice?.words ?? []).filter((w) => !s.cuts.some(([a, b]) => w.start >= a && w.start < b)).map((w) => s.start + w.start - cutBefore(s.cuts, w.start)),
    ),
  ];
  const sel = clips.find((c) => c.id === activeClip) ?? null;
  const selLocked = !sel || trackOf(tracks, sel.track).locked;
  const doSplit = () => {
    if (sel && !selLocked) setClips((cs) => splitAt(cs, sel.id, now));
  };
  const doDuplicate = () => {
    if (!sel || selLocked) return;
    const next = duplicateIn(clips, sel.id);
    setClips(() => next);
    onSelectClip?.(next[next.length - 1].id, false);
  };
  const doDelete = () => {
    if (sel && !selLocked) setClips((cs) => cs.filter((c) => c.id !== sel.id));
  };
  const addClip = (track: Clip["track"]) => {
    if (trackOf(tracks, track).locked) return;
    const first = cat?.sounds.find((x) => !x.ambient) ?? cat?.sounds[0];
    const c =
      track === "sfx"
        ? makeClip(clips, "sfx", now, { sound: first?.name ?? "", duration: Math.min(1, first?.duration ?? 1) })
        : makeClip(clips, "graphics", now, {
            template: "KineticTitle",
            template_version: cat?.templates.KineticTitle?.version ?? 0,
            duration: cat?.templates.KineticTitle?.seconds ?? 3,
            props: templateDefaults(cat?.templates.KineticTitle),
          });
    setClips((cs) => [...cs, c]);
    onSelectClip?.(c.id, false);
  };
  // keys for the selected clip (not while typing): Delete, S splits at the playhead, Ctrl+D duplicates, arrows nudge
  const keys = useRef({ doSplit, doDuplicate, doDelete, sel, selLocked });
  useEffect(() => {
    keys.current = { doSplit, doDuplicate, doDelete, sel, selLocked };
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const k = keys.current;
      const el = e.target as HTMLElement | null;
      if (!k.sel || (el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName)))) return;
      const c = k.sel;
      if (e.key === "Delete" || e.key === "Backspace") k.doDelete();
      else if (e.key.toLowerCase() === "s" && !e.ctrlKey && !e.metaKey) k.doSplit();
      else if (e.key.toLowerCase() === "d" && (e.ctrlKey || e.metaKey)) k.doDuplicate();
      else if ((e.key === "ArrowLeft" || e.key === "ArrowRight") && !k.selLocked) {
        const step = (e.shiftKey ? 1 : 0.1) * (e.key === "ArrowLeft" ? -1 : 1);
        setDraft((d) => ({ ...d, clips: replace(d.clips ?? [], c.id, (x) => [{ ...x, start: Math.max(0, Math.round((x.start + step) * 100) / 100) }]) }));
      } else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setDraft]);

  function beginClip(e: ReactPointerEvent<HTMLElement>, c: Clip, mode: "move" | "start" | "end") {
    if (e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();
    onSelectClip?.(c.id, false);
    if (trackOf(tracks, c.track).locked) return; // selectable, not editable
    e.currentTarget.setPointerCapture(e.pointerId);
    setDrag({ kind: "clip", id: c.id, mode, x: e.clientX, orig: c, moved: false });
  }

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
    if (drag.kind === "clip") {
      if (!drag.moved && Math.abs(e.clientX - drag.x) < 4) return; // still a click
      const tol = SNAP_PX / pps;
      const o = drag.orig;
      const targets = snapTargets(clips, o.id, marks);
      const next =
        drag.mode === "move"
          ? moveTo(o, o.start + dt, targets, tol)
          : drag.mode === "start"
            ? trimStart(o, snap(o.start + dt, targets, tol))
            : trimEnd(o, snap(o.start + o.duration + dt, targets, tol), o.track === "sfx" ? soundLength(cat, o.sound) : undefined);
      if (!drag.moved) setDrag({ ...drag, moved: true });
      setClips((cs) => replace(cs, o.id, () => [next]));
    } else if (drag.kind === "slip") {
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
              ? { ...item, ...(drag.list === "broll" && { basis: 0 }), duration: round(Math.min(Math.max(drag.duration + dt, 0.2), drag.max - drag.at)) }
              : { ...item, ...(drag.list === "broll" && { basis: 0 }), at: round(Math.min(Math.max(drag.at + dt, 0), Math.max(drag.max - drag.duration, 0))) },
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
    } else if (drag.kind === "clip" && !drag.moved) {
      onSelectClip?.(drag.id, true); // a click: jump to it
    } else if (drag.kind === "item" && Math.abs(e.clientX - drag.x) < 4) {
      onSelectItem?.({ uid: drag.uid, list: drag.list, k: drag.k }); // a click, not a drag
    }
    setDrag(null);
  }

  const laneHead = (name: TrackName, cls: string) => {
    const t = trackOf(tracks, name);
    const audio = name !== "graphics";
    const clipLane = name === "graphics" || name === "sfx";
    const label = LANES[name];
    return (
      <div className={`flex items-center gap-0.5 pr-1 ${cls}`}>
        <span className="min-w-0 flex-1 truncate font-semibold text-ink-soft">{label}</span>
        {audio && (
          <LaneToggle on={t.mute} label={`Mute ${label.toLowerCase()}`} onClick={() => setTrack(name, { mute: !t.mute })}>
            M
          </LaneToggle>
        )}
        {audio && (
          <LaneToggle on={t.solo} label={`Solo ${label.toLowerCase()} (preview only)`} onClick={() => setTrack(name, { solo: !t.solo })}>
            S
          </LaneToggle>
        )}
        {audio && (
          <input
            type="range"
            min={0}
            max={2}
            step={0.05}
            value={t.volume}
            aria-label={`${label} volume`}
            title={`${label} ${Math.round(t.volume * 100)}%`}
            onChange={(e) => setTrack(name, { volume: Number(e.target.value) })}
            className="w-10 accent-cobalt"
          />
        )}
        {name === "graphics" && (
          <LaneToggle on={t.hidden} label={t.hidden ? "Show the graphics" : "Hide the graphics (left out of the render)"} onClick={() => setTrack(name, { hidden: !t.hidden })}>
            {t.hidden ? <EyeOff className="size-3" /> : <Eye className="size-3" />}
          </LaneToggle>
        )}
        {clipLane && (
          <LaneToggle on={t.locked} label={t.locked ? `Unlock ${label.toLowerCase()}` : `Lock ${label.toLowerCase()}`} onClick={() => setTrack(name, { locked: !t.locked })}>
            {t.locked ? <Lock className="size-3" /> : <LockOpen className="size-3" />}
          </LaneToggle>
        )}
        {clipLane && (
          <LaneToggle on={false} label={name === "graphics" ? "Add a graphic at the playhead" : "Add a sound effect at the playhead"} onClick={() => addClip(name)}>
            <Plus className="size-3" />
          </LaneToggle>
        )}
      </div>
    );
  };
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
            {sel && (
              <div role="group" aria-label="Selected clip" className="flex items-center gap-0.5">
                <IconButton label="Split at the playhead (S)" disabled={selLocked} onClick={doSplit}>
                  <Scissors className="size-4" />
                </IconButton>
                <IconButton label="Duplicate (Ctrl+D)" disabled={selLocked} onClick={doDuplicate}>
                  <Copy className="size-4" />
                </IconButton>
                <IconButton label="Delete (Delete key)" tone="danger" disabled={selLocked} onClick={doDelete}>
                  <Trash2 className="size-4" />
                </IconButton>
              </div>
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
        <div className="flex">
        {shown.length > 0 && (
          <div role="group" aria-label="Timeline lanes" className="grid w-48 shrink-0 content-start border-r border-line pl-2 text-2xs">
            <div className="h-5" />
            <div className="flex items-center font-semibold text-ink-soft" style={{ height: VIDEO_H }}>Scenes</div>
            <div className="mt-1 flex h-5 items-center font-semibold text-ink-soft">B-roll</div>
            <div className="mt-1 flex h-5 items-center font-semibold text-ink-soft">Text</div>
            {laneHead("graphics", "mt-1 h-6")}
            {laneHead("sfx", "mt-1 h-6")}
            {laneHead("voice", "mt-1 h-[30px]")}
            {laneHead("music", "mt-1 h-5")}
          </div>
        )}
        <div
          ref={scroller}
          className="relative min-w-0 flex-1 overflow-x-auto overflow-y-hidden px-0 pb-2 select-none"
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
                    (seg.scene[list] ?? []).map((item, k) => {
                      const selected = activeItem?.uid === seg.scene.uid && activeItem.list === list && activeItem.k === k;
                      return (
                      <div
                        key={`${seg.scene.uid}-${k}`}
                        role="button"
                        tabIndex={0}
                        aria-pressed={selected}
                        aria-label={`Scene ${seg.index + 1}, ${list === "broll" ? `B-roll ${k + 1}` : `text “${"text" in item ? item.text : ""}”`}, from ${item.at.toFixed(1)} s for ${item.duration.toFixed(1)} s`}
                        onKeyDown={(e) => {
                          if (e.key !== "Enter" && e.key !== " ") return;
                          e.preventDefault();
                          onSelectItem?.({ uid: seg.scene.uid, list, k });
                        }}
                        title={list === "broll" ? "B-roll: click to select, drag to move, drag the right edge to change its length" : `Text “${"text" in item ? item.text : ""}”: click to select, drag to move`}
                        onPointerDown={(e) =>
                          begin(e, { kind: "item", uid: seg.scene.uid, list, k, x: e.clientX, at: item.at, duration: item.duration, edge: false, max: seg.length })
                        }
                        className={`absolute top-0 h-full cursor-grab overflow-hidden rounded px-1.5 text-2xs leading-5 font-semibold whitespace-nowrap ${
                          list === "broll" ? "bg-cobalt/80 text-white" : "bg-caption text-media"
                        } ${selected ? "z-10 outline-2 outline-offset-1 outline-ink" : ""}`}
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
                      );
                    }),
                  )}
                </div>
              ))}

              {/* graphics and sound effects: clips on the video's own clock */}
              {(["graphics", "sfx"] as const).map((lane) => {
                const t = trackOf(tracks, lane);
                return (
                  <div key={lane} className="relative mt-1 h-6">
                    {clips
                      .filter((c) => c.track === lane)
                      .map((c) => {
                        const selected = c.id === activeClip;
                        const main = c.props.text ?? c.props.title ?? c.props.label ?? c.props.shown ?? c.props.place ?? c.props.left_label;
                        const label = lane === "sfx" ? cat?.sounds.find((x) => x.name === c.sound)?.label ?? (c.sound || "No sound") : `${cat?.templates[c.template]?.label ?? (c.template || "Graphic")}${main ? ` · ${main}` : ""}`;
                        const wave = lane === "sfx" ? sfxWaves[c.sound] : null;
                        return (
                          <div
                            key={c.id}
                            role="button"
                            tabIndex={0}
                            aria-pressed={selected}
                            aria-label={`${lane === "sfx" ? "Sound" : "Graphic"} ${label}, from ${c.start.toFixed(1)} s for ${c.duration.toFixed(1)} s${t.locked ? ", locked" : ""}`}
                            title={t.locked ? "This lane is locked" : "Click to select, drag to move, drag an edge to trim. S splits it at the playhead, Delete removes it."}
                            onKeyDown={(e) => {
                              if (e.key !== "Enter" && e.key !== " ") return;
                              e.preventDefault();
                              onSelectClip?.(c.id, true);
                            }}
                            onPointerDown={(e) => beginClip(e, c, "move")}
                            className={`absolute top-0 h-full overflow-hidden rounded text-2xs leading-6 font-semibold whitespace-nowrap ${
                              lane === "sfx" ? "bg-ok/75 text-media" : "bg-[#7c3aed]/85 text-white"
                            } ${t.locked ? "cursor-default" : "cursor-grab"} ${lane === "graphics" && t.hidden ? "opacity-40" : ""} ${
                              selected ? "z-10 outline-2 outline-offset-1 outline-ink" : ""
                            }`}
                            style={{ left: c.start * pps, width: Math.max(c.duration * pps, 6) }}
                          >
                            {wave && <ClipWave c={c} peaks={wave} pps={pps} />}
                            {c.fade_in > 0 && <span aria-hidden className="pointer-events-none absolute inset-y-0 left-0 bg-gradient-to-r from-black/45 to-transparent" style={{ width: c.fade_in * pps }} />}
                            {c.fade_out > 0 && <span aria-hidden className="pointer-events-none absolute inset-y-0 right-0 bg-gradient-to-l from-black/45 to-transparent" style={{ width: c.fade_out * pps }} />}
                            <span className="pointer-events-none relative px-1.5">{label}</span>
                            {!t.locked && (
                              <>
                                <span aria-hidden onPointerDown={(e) => beginClip(e, c, "start")} className="absolute inset-y-0 left-0 w-1.5 cursor-ew-resize bg-black/25" />
                                <span aria-hidden onPointerDown={(e) => beginClip(e, c, "end")} className="absolute inset-y-0 right-0 w-1.5 cursor-ew-resize bg-black/25" />
                              </>
                            )}
                          </div>
                        );
                      })}
                  </div>
                );
              })}

              {/* voice */}
              <div className="relative mt-1 h-[30px] text-cobalt/70">
                {shown.map((seg) => {
                  const peaks = seg.voice ? waves[seg.voice.key] : null;
                  return (
                    <div
                      key={seg.scene.uid}
                      onPointerDown={(e) => e.button === 0 && onActive(seg.scene.uid)}
                      title={`Scene ${seg.index + 1} voiceover: click to select the scene`}
                      className={`absolute top-0 h-full cursor-pointer overflow-hidden rounded ${seg.scene.uid === activeUid ? "bg-cobalt/[0.16]" : "bg-cobalt/[0.06]"}`}
                      style={{ left: seg.start * pps, width: Math.max(seg.length * pps - 2, 4) }}
                    >
                      {peaks && <Waveform seg={seg} peaks={peaks} pps={pps} />}
                    </div>
                  );
                })}
              </div>

              {/* music: the background track under the whole video */}
              <div className="relative mt-1 h-5">
                <div
                  className={`absolute top-0 h-full truncate rounded px-1.5 text-2xs leading-5 font-semibold text-ink-soft ${trackOf(tracks, "music").mute ? "bg-ink/[0.03] line-through" : "bg-ink/[0.08]"}`}
                  style={{ left: 0, width: Math.max(total * pps - 2, 4) }}
                >
                  {draft.music === "none" ? "No music" : draft.music || "Music picked at render"}
                </div>
              </div>

              {/* playhead */}
              <span className="pointer-events-none absolute top-0 bottom-0 w-0.5 bg-danger" style={{ left: now * pps }} />
            </div>
          )}
        </div>
        </div>
      )}
    </section>
  );
}
