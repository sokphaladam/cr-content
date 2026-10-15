import type { SongArtSlot, TimedLine, TimedWord } from "./api";

/** A line in the editor: a stable id keeps inputs and selection attached while lines are added or re-sorted. */
export type Row = TimedLine & { uid: string };

export const fmt = (t: number, digits = 1) => {
  const m = Math.floor(Math.max(0, t) / 60);
  const s = Math.max(0, t) - m * 60;
  return `${m}:${s.toFixed(digits).padStart(digits ? digits + 3 : 2, "0")}`;
};
/** "1:23.45", "83.45" or "1:23" -> seconds; null when it isn't a time. */
export function parseTime(text: string): number | null {
  const m = text.trim().match(/^(?:(\d+):)?(\d+(?:[.,]\d*)?)$/);
  if (!m) return null;
  return (m[1] ? Number(m[1]) * 60 : 0) + Number(m[2].replace(",", "."));
}
export const lineStart = (l: TimedLine) => l.words[0]?.start ?? 0;
export const lineEnd = (l: TimedLine) => l.words[l.words.length - 1]?.end ?? 0;
export const round = (t: number) => Math.round(t * 100) / 100;
const byStart = (a: Row, b: Row) => lineStart(a) - lineStart(b);
export const GAP = 0.05; // smallest pause kept between two lines
export const MIN_LINE = 0.3; // shortest a line can be
let uidCounter = 0;
export const newUid = () => `l${++uidCounter}`;

export function shift<T extends TimedLine>(line: T, by: number): T {
  const by2 = Math.max(by, -lineStart(line)); // never before 0:00
  return { ...line, words: line.words.map((w) => ({ ...w, start: round(w.start + by2), end: round(w.end + by2) })) };
}

/** Stretch the line's words to fit [start, end], keeping their relative timing. */
export function respan<T extends TimedLine>(line: T, start: number, end: number): T {
  const s0 = lineStart(line);
  const k = (end - start) / Math.max(lineEnd(line) - s0, 0.01);
  return { ...line, words: line.words.map((w) => ({ ...w, start: round(start + (w.start - s0) * k), end: round(start + (w.end - s0) * k) })) };
}

/** Keep lines in order and never overlapping after line `uid` changed: the line before it is cut short where it
 * now starts, and lines after it that it now runs into are pushed later (each just enough to clear the one before). */
export function settle(ls: Row[], uid: string): Row[] {
  const out = [...ls].sort(byStart);
  const i = out.findIndex((l) => l.uid === uid);
  if (i < 0) return out;
  const prev = out[i - 1];
  if (prev && lineEnd(prev) > lineStart(out[i]) - GAP) {
    const end = Math.max(lineStart(out[i]) - GAP, lineStart(prev) + MIN_LINE);
    out[i - 1] = respan(prev, lineStart(prev), end);
    if (lineEnd(out[i - 1]) > lineStart(out[i]) - GAP) out[i] = shift(out[i], lineEnd(out[i - 1]) + GAP - lineStart(out[i]));
  }
  for (let j = i + 1; j < out.length; j++) {
    const need = round(lineEnd(out[j - 1]) + GAP - lineStart(out[j]));
    if (need <= 0) break; // from here on the lines were already in order
    out[j] = shift(out[j], need);
  }
  return out;
}

/** Spread `text`'s words over [start, end], longer words getting more time. */
export function spread(text: string, start: number, end: number): TimedWord[] {
  const tokens = text.trim().split(/\s+/).filter(Boolean);
  const span = Math.max(end - start, 0.2);
  const total = tokens.reduce((n, t) => n + t.length + 1, 0);
  let t = start;
  return tokens.map((tok) => {
    const len = (span * (tok.length + 1)) / total;
    const w = { text: tok, start: round(t), end: round(t + len) };
    t += len;
    return w;
  });
}

/** New text: spread its words over the line's current span. */
export function retext<T extends TimedLine>(line: T, text: string): T {
  const words = spread(text, lineStart(line), lineEnd(line));
  return words.length ? { ...line, text, words } : { ...line, text };
}

/** Word `i` starts at `t`: the word before it ends there, so the highlight moves on without a gap. */
export function setWordStart<T extends TimedLine>(line: T, i: number, t: number): T {
  const words = line.words.map((w) => ({ ...w }));
  const lo = i > 0 ? words[i - 1].start + 0.02 : 0;
  const hi = words[i].end - 0.02;
  const at = round(Math.min(Math.max(t, lo), hi));
  words[i].start = at;
  if (i > 0) words[i - 1].end = at;
  return { ...line, words, check: false };
}

export function setLastWordEnd<T extends TimedLine>(line: T, t: number): T {
  const words = line.words.map((w) => ({ ...w }));
  const last = words[words.length - 1];
  last.end = round(Math.max(t, last.start + 0.05));
  return { ...line, words, check: false };
}

/** Peak level per 1/PEAKS_PER_SECOND of the song, for drawing its waveform. */
export const PEAKS_PER_SECOND = 100;
export async function audioPeaks(url: string, signal: AbortSignal): Promise<Float32Array> {
  const data = await (await fetch(url, { signal })).arrayBuffer();
  const ctx = new AudioContext();
  try {
    const buf = await ctx.decodeAudioData(data);
    const ch = [...Array(buf.numberOfChannels).keys()].map((c) => buf.getChannelData(c));
    const step = Math.max(1, Math.floor(buf.sampleRate / PEAKS_PER_SECOND));
    const peaks = new Float32Array(Math.ceil(buf.length / step));
    let max = 0.0001;
    for (let p = 0; p < peaks.length; p++) {
      let peak = 0;
      const end = Math.min(buf.length, (p + 1) * step);
      for (let i = p * step; i < end; i += 4) for (const c of ch) peak = Math.max(peak, Math.abs(c[i]));
      peaks[p] = peak;
      max = Math.max(max, peak);
    }
    for (let p = 0; p < peaks.length; p++) peaks[p] /= max;
    return peaks;
  } finally {
    void ctx.close();
  }
}

/** A planned picture placed on the song's timeline: `slot` indexes the art plan's slots. */
export type PictureClip = { slot: number; start: number; end: number; section: string };

/** Where each planned picture is on screen. A slot first shows at its own start; a section sung again ("Chorus #2")
 *  shows its pictures again at the same offsets into the repeat, so repeats follow the lyric timing. */
export function pictureClips(slots: SongArtSlot[], lines: Row[], sections: string[], duration: number): PictureClip[] {
  const runs: { name: string; start: number; nth: number }[] = [];
  const seen: Record<string, number> = {};
  lines.forEach((l, i) => {
    if (i > 0 && lines[i - 1].section === l.section) return;
    const name = sections[l.section] ?? "";
    seen[name] = (seen[name] ?? 0) + 1;
    runs.push({ name, start: lineStart(l), nth: seen[name] });
  });
  const clips: Omit<PictureClip, "end">[] = slots.map((s, i) => ({ slot: i, start: s.start, section: s.section }));
  for (const run of runs) {
    if (run.nth < 2) continue;
    const first = runs.find((r) => r.name === run.name && r.nth === 1);
    if (!first) continue;
    slots.forEach((s, i) => {
      if (s.section === run.name && s.also.includes(`${run.name} #${run.nth}`))
        clips.push({ slot: i, start: round(run.start + (s.start - first.start)), section: `${run.name} #${run.nth}` });
    });
  }
  clips.sort((a, b) => a.start - b.start);
  return clips.map((c, i) => ({ ...c, end: Math.min(duration, clips[i + 1]?.start ?? duration) })).filter((c) => c.end > c.start);
}
