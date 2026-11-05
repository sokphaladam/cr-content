import type { Clip, TrackName, TrackState } from "./api";

/** The timeline's global clips (graphics, sound effects): pure edits, so a drag or a key press is one draft update
 *  (and one undo step). Times in seconds from the video's start, rounded to 1/100 s like the render reads them. */

export const MIN_LEN = 0.1;
export const SNAP_PX = 8; // how close (on screen) an edge must come to a snap point to stick to it
export const DEFAULT_TRACK: TrackState = { mute: false, solo: false, volume: 1, locked: false, hidden: false };

const r = (v: number) => Math.round(v * 100) / 100;

export const trackOf = (tracks: Partial<Record<TrackName, TrackState>> | undefined, name: TrackName): TrackState => ({
  ...DEFAULT_TRACK,
  ...tracks?.[name],
});

/** Whether a lane is heard in the preview: not muted, and soloed when any lane is (solo is monitoring only). */
export function audible(tracks: Partial<Record<TrackName, TrackState>> | undefined, name: TrackName): boolean {
  const t = trackOf(tracks, name);
  const anySolo = (["voice", "music", "sfx"] as TrackName[]).some((n) => trackOf(tracks, n).solo);
  return !t.mute && (!anySolo || t.solo);
}

export function newId(clips: Clip[]): string {
  let n = clips.length + 1;
  while (clips.some((c) => c.id === `clip-${n}`)) n++;
  return `clip-${n}`;
}

export function makeClip(clips: Clip[], track: Clip["track"], start: number, over: Partial<Clip> = {}): Clip {
  return {
    id: newId(clips),
    track,
    start: r(Math.max(0, start)),
    duration: track === "sfx" ? 1 : 3,
    source_in: 0,
    sound: "",
    template: "",
    props: {},
    gain: 1,
    fade_in: 0,
    fade_out: 0,
    layer: 0,
    ...over,
  };
}

/** `t` moved onto the nearest of `targets` within `tolerance` seconds (else unchanged). */
export function snap(t: number, targets: number[], tolerance: number): number {
  let best = t;
  let gap = tolerance;
  for (const x of targets) {
    if (Math.abs(x - t) <= gap) {
      gap = Math.abs(x - t);
      best = x;
    }
  }
  return best;
}

/** Where clip edges stick: the other clips' starts and ends, plus `extra` (the playhead, scene cuts, words). */
export function snapTargets(clips: Clip[], except: string, extra: number[]): number[] {
  return [...extra, ...clips.filter((c) => c.id !== except).flatMap((c) => [c.start, c.start + c.duration])];
}

/** The clip moved so it starts at `start` (or, snapped by its end, ends at a target). */
export function moveTo(c: Clip, start: number, targets: number[], tolerance: number): Clip {
  const byStart = snap(start, targets, tolerance);
  const byEnd = snap(start + c.duration, targets, tolerance) - c.duration;
  const s = byStart !== start ? byStart : byEnd !== start ? byEnd : start;
  return { ...c, start: r(Math.max(0, s)) };
}

/** Its head trimmed to `at` (the end stays put). A sound starts later into its file; it can't go before the file's start. */
export function trimStart(c: Clip, at: number): Clip {
  const end = c.start + c.duration;
  let s = Math.min(Math.max(at, 0), end - MIN_LEN);
  if (c.track === "sfx") s = Math.max(s, c.start - c.source_in);
  const delta = s - c.start;
  return { ...c, start: r(s), duration: r(end - s), source_in: c.track === "sfx" ? r(c.source_in + delta) : c.source_in };
}

/** Its tail trimmed (or extended) to `at`. A sound can't run past the end of its file (`sourceLength`, when known). */
export function trimEnd(c: Clip, at: number, sourceLength?: number): Clip {
  let d = Math.max(at - c.start, MIN_LEN);
  if (c.track === "sfx" && sourceLength) d = Math.min(d, Math.max(sourceLength - c.source_in, MIN_LEN));
  return { ...c, duration: r(d) };
}

/** Two clips cut at `at`, or null when `at` isn't inside it. The sound carries on from where it was cut. */
export function split(c: Clip, at: number, id: string): [Clip, Clip] | null {
  if (at <= c.start + MIN_LEN || at >= c.start + c.duration - MIN_LEN) return null;
  const first = { ...c, duration: r(at - c.start), fade_out: 0 };
  const second = {
    ...c,
    id,
    start: r(at),
    duration: r(c.start + c.duration - at),
    source_in: c.track === "sfx" ? r(c.source_in + at - c.start) : c.source_in,
    fade_in: 0,
  };
  return [first, second];
}

/** A copy with a new id, in the first gap on its lane after it (never on top of another clip of that lane). */
export function duplicate(c: Clip, clips: Clip[]): Clip {
  let start = c.start + c.duration;
  for (let moved = true; moved; ) {
    moved = false;
    for (const o of clips) {
      if (o.track === c.track && o.start < start + c.duration - 1e-6 && o.start + o.duration > start + 1e-6) {
        start = o.start + o.duration;
        moved = true;
      }
    }
  }
  return { ...c, id: newId(clips), start: r(start), props: { ...c.props } };
}

/** `clips` with the clip `id` replaced by `make(it)` (several clips, e.g. after a split; none, to delete it). */
export function replace(clips: Clip[], id: string, make: (c: Clip) => Clip[]): Clip[] {
  return clips.flatMap((c) => (c.id === id ? make(c).map(touched) : [c]));
}

/** An Edit Director clip the creator changed is theirs from then on: re-planning keeps it. */
export const touched = (c: Clip): Clip => (c.origin === "director" ? { ...c, origin: "edited" } : c);

/** The clip `id` split at `at` (unchanged when `at` isn't inside it). */
export function splitAt(clips: Clip[], id: string, at: number): Clip[] {
  const c = clips.find((x) => x.id === id);
  const parts = c && split(c, at, newId(clips));
  return parts ? replace(clips, id, () => parts) : clips;
}

/** A copy of the clip `id` added right after it (it's the last clip of the result). */
export function duplicateIn(clips: Clip[], id: string): Clip[] {
  const c = clips.find((x) => x.id === id);
  return c ? [...clips, touched(duplicate(c, clips))] : clips;
}
