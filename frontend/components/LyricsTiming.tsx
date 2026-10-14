"use client";

import { Check, ChevronDown, ChevronLeft, CircleAlert, Crosshair, Film, ListPlus, Minus, Pause, Play, Plus, RefreshCw, Trash2, Undo2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, outputUrl, type Aspect, type Lang, type LyricsTiming as Timing, type MusicVideoSettings, type TimedLine, type TimedWord } from "@/lib/api";
import { Button, IconButton, Message, Spinner } from "./ui";
import { MusicVideoOptions } from "./MusicVideoOptions";

/** A line in the editor: a stable id keeps inputs and open word panels attached while lines are added or re-sorted. */
type Row = TimedLine & { uid: string };

const fmt = (t: number, digits = 1) => {
  const m = Math.floor(Math.max(0, t) / 60);
  const s = Math.max(0, t) - m * 60;
  return `${m}:${s.toFixed(digits).padStart(digits + 3, "0")}`;
};
/** "1:23.45", "83.45" or "1:23" -> seconds; null when it isn't a time. */
function parseTime(text: string): number | null {
  const m = text.trim().match(/^(?:(\d+):)?(\d+(?:[.,]\d*)?)$/);
  if (!m) return null;
  return (m[1] ? Number(m[1]) * 60 : 0) + Number(m[2].replace(",", "."));
}
const lineStart = (l: TimedLine) => l.words[0]?.start ?? 0;
const lineEnd = (l: TimedLine) => l.words[l.words.length - 1]?.end ?? 0;
const round = (t: number) => Math.round(t * 100) / 100;
const byStart = (a: Row, b: Row) => lineStart(a) - lineStart(b);
const GAP = 0.05; // smallest pause kept between two lines
let uidCounter = 0;
const newUid = () => `l${++uidCounter}`;

function shift<T extends TimedLine>(line: T, by: number): T {
  const by2 = Math.max(by, -lineStart(line)); // never before 0:00
  return { ...line, words: line.words.map((w) => ({ ...w, start: round(w.start + by2), end: round(w.end + by2) })) };
}

/** Stretch the line's words to fit [start, end], keeping their relative timing. */
function respan<T extends TimedLine>(line: T, start: number, end: number): T {
  const s0 = lineStart(line);
  const k = (end - start) / Math.max(lineEnd(line) - s0, 0.01);
  return { ...line, words: line.words.map((w) => ({ ...w, start: round(start + (w.start - s0) * k), end: round(start + (w.end - s0) * k) })) };
}

/** Keep lines in order and never overlapping after line `uid` changed: the line before it is cut short where it
 * now starts, and lines after it that it now runs into are pushed later (each just enough to clear the one before). */
function settle(ls: Row[], uid: string): Row[] {
  const out = [...ls].sort(byStart);
  const i = out.findIndex((l) => l.uid === uid);
  if (i < 0) return out;
  const prev = out[i - 1];
  if (prev && lineEnd(prev) > lineStart(out[i]) - GAP) {
    const end = Math.max(lineStart(out[i]) - GAP, lineStart(prev) + 0.3);
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
function spread(text: string, start: number, end: number): TimedWord[] {
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
function retext<T extends TimedLine>(line: T, text: string): T {
  const words = spread(text, lineStart(line), lineEnd(line));
  return words.length ? { ...line, text, words } : { ...line, text };
}

/** Word `i` starts at `t`: the word before it ends there, so the highlight moves on without a gap. */
function setWordStart<T extends TimedLine>(line: T, i: number, t: number): T {
  const words = line.words.map((w) => ({ ...w }));
  const lo = i > 0 ? words[i - 1].start + 0.02 : 0;
  const hi = words[i].end - 0.02;
  const at = round(Math.min(Math.max(t, lo), hi));
  words[i].start = at;
  if (i > 0) words[i - 1].end = at;
  return { ...line, words, check: false };
}

function setLastWordEnd<T extends TimedLine>(line: T, t: number): T {
  const words = line.words.map((w) => ({ ...w }));
  const last = words[words.length - 1];
  last.end = round(Math.max(t, last.start + 0.05));
  return { ...line, words, check: false };
}

/** A time you can type ("1:23.45" or seconds). Commits on Enter or when it loses focus; Escape cancels. */
function TimeInput({ value, onCommit, label, className = "" }: { value: number; onCommit: (t: number) => void; label: string; className?: string }) {
  const [text, setText] = useState<string | null>(null); // null = not being edited, show the value
  const [bad, setBad] = useState(false);
  const commit = () => {
    if (text === null) return;
    const t = parseTime(text);
    if (t === null) {
      setBad(true);
      return;
    }
    setText(null);
    setBad(false);
    if (Math.abs(t - value) >= 0.005) onCommit(t);
  };
  return (
    <input
      aria-label={label}
      title={`${label}: type a time like 1:23.45`}
      inputMode="decimal"
      value={text ?? fmt(value, 2)}
      onFocus={(e) => {
        setText(fmt(value, 2));
        e.currentTarget.select();
      }}
      onChange={(e) => {
        setText(e.target.value);
        setBad(false);
      }}
      onBlur={() => {
        commit();
        setText(null);
        setBad(false);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
        if (e.key === "Escape") {
          setText(null);
          setBad(false);
          e.currentTarget.blur();
        }
      }}
      className={`h-7 w-[4.6rem] rounded-md border bg-panel px-1.5 text-center font-mono text-sm tabular-nums text-ink focus:border-cobalt focus:outline-none ${
        bad ? "border-danger" : "border-line"
      } ${className}`}
    />
  );
}

type Save = "idle" | "saving" | "saved" | "error";

export function LyricsTiming({
  name,
  title,
  lang,
  aspect,
  sections,
  settings: initialSettings,
  busy,
  onBack,
  onDelete,
  onResync,
  onMakeVideo,
}: {
  name: string;
  title: string;
  lang: Lang;
  aspect: Aspect;
  sections: string[];
  settings: MusicVideoSettings; // idea, look and lyric style the song's last music video used
  busy: boolean; // a job (sync or render) is running
  onBack: () => void;
  onDelete: () => void;
  onResync:() => Promise<string | null>;
  onMakeVideo: (settings: MusicVideoSettings) => Promise<string | null>;
}) {
  const [settings, setSettings] = useState(initialSettings);
  const [making, setMaking] = useState(false); // the "make music video" panel is open
  const [lines, setLines] = useState<Row[] | null>(null);
  const [method, setMethod] = useState<Timing["timing"]>("");
  const [loadError, setLoadError] = useState("");
  const [save, setSave] = useState<Save>("idle");
  const [error, setError] = useState("");
  const [now, setNow] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [follow, setFollow] = useState(true);
  const [ripple, setRipple] = useState(true); // retiming a line moves every line after it by the same amount
  const [confirmResync, setConfirmResync] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [open, setOpen] = useState<Set<string>>(new Set()); // lines showing their words
  const [fresh, setFresh] = useState<string | null>(null); // just-added line: focus its text
  const [deleted, setDeleted] = useState<{ row: Row; index: number } | null>(null);
  const audio = useRef<HTMLAudioElement>(null);
  const list = useRef<HTMLOListElement>(null);
  const dirty = useRef(false);
  const pending = useRef<Promise<unknown>>(Promise.resolve());

  useEffect(() => {
    let cancelled = false;
    api
      .lyrics(name)
      .then((d) => {
        if (cancelled) return;
        setLines((d.lines ?? []).map((l) => ({ ...l, uid: newUid() })));
        setMethod(d.timing);
      })
      .catch((e: Error) => !cancelled && setLoadError(e.message));
    return () => {
      cancelled = true;
    };
  }, [name]);

  const toSave = (ls: Row[]): TimedLine[] => ls.map((l) => ({ section: l.section, text: l.text, words: l.words, check: !!l.check }));

  // Autosave shortly after each change; the music video always uses the latest saved timing.
  useEffect(() => {
    if (!lines || !dirty.current) return;
    const timer = setTimeout(() => {
      setSave("saving");
      pending.current = api
        .saveLyrics(name, toSave(lines))
        .then(() => {
          dirty.current = false;
          setSave("saved");
          setMethod("edited");
        })
        .catch(() => setSave("error"));
    }, 700);
    return () => clearTimeout(timer);
  }, [lines, name]);

  const edit = useCallback((update: (ls: Row[]) => Row[]) => {
    dirty.current = true;
    setSave("idle");
    setLines((ls) => (ls ? update(ls) : ls));
  }, []);
  /** Change a line's timing. With `ripple` on, every line after it moves by as much as its start (or end) moved. */
  const retime = (uid: string, update: (l: Row) => Row, edge: "start" | "end") =>
    edit((ls) => {
      const i = ls.findIndex((l) => l.uid === uid);
      if (i < 0) return ls;
      const next = { ...update(ls[i]), check: false }; // retimed by hand = checked
      let by = round(edge === "start" ? lineStart(next) - lineStart(ls[i]) : lineEnd(next) - lineEnd(ls[i]));
      // moving earlier: the lines after keep their spacing, so they stop when the first of them reaches 0:00
      if (ls[i + 1]) by = Math.max(by, -lineStart(ls[i + 1]));
      return settle(ls.map((l, j) => (j === i ? next : ripple && j > i && by ? shift(l, by) : l)), uid);
    });
  /** Line starts at `t`: with ripple the whole line moves there (keeping its length), else it stretches to its end. */
  const startAt = (uid: string, t: number) =>
    retime(uid, (l) => (ripple ? shift(l, t - lineStart(l)) : respan(l, t, Math.max(lineEnd(l), t + 0.3))), "start");
  const endAt = (uid: string, t: number) => retime(uid, (l) => respan(l, lineStart(l), Math.max(t, lineStart(l) + 0.3)), "end");

  const editLine = (uid: string, update: (l: Row) => Row) =>
    edit((ls) => settle(ls.map((l) => (l.uid === uid ? update(l) : l)), uid));

  /** Insert a line with placeholder text sung over [start, end], in the section of the line before it. */
  const addLine = (start: number, end: number) => {
    const uid = newUid();
    edit((ls) => {
      const before = ls.filter((l) => lineStart(l) <= start).at(-1) ?? ls[0];
      const text = "New line";
      // fit into the pause before the next line when there is room for it
      const nextStart = ls.find((l) => lineStart(l) > start)?.words[0].start ?? Infinity;
      const fit = Math.min(end, nextStart - GAP);
      const row = { uid, section: before?.section ?? 0, text, words: spread(text, round(start), round(fit - start >= 0.6 ? fit : end)) };
      return settle([...ls, row], uid);
    });
    setFresh(uid);
    setDeleted(null);
  };
  const addAfter = (i: number) => {
    if (!lines) return;
    const start = lineEnd(lines[i]) + 0.2;
    const next = lines[i + 1] ? lineStart(lines[i + 1]) - 0.1 : start + 2;
    addLine(start, Math.max(start + 0.6, Math.min(start + 2, next)));
  };
  const removeLine = (i: number) => {
    if (!lines) return;
    setDeleted({ row: lines[i], index: i });
    edit((ls) => ls.filter((_, j) => j !== i));
  };

  useEffect(() => {
    if (!fresh) return;
    const input = list.current?.querySelector<HTMLInputElement>(`[data-line-text="${fresh}"]`);
    if (input) {
      input.scrollIntoView({ block: "center", behavior: "smooth" });
      input.focus();
      input.select();
      setFresh(null);
    }
  }, [fresh, lines]);

  // Playhead: smooth while playing (the timeupdate event only fires ~4 times a second).
  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    const tick = () => {
      if (audio.current) setNow(audio.current.currentTime);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing]);

  const active = lines ? lines.findLastIndex((l) => lineStart(l) - 0.3 <= now && now <= lineEnd(l) + 0.6) : -1;

  useEffect(() => {
    if (!follow || !playing || active < 0) return;
    list.current?.querySelector(`[data-line="${active}"]`)?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [active, follow, playing]);

  const seek = (t: number, play = true) => {
    const a = audio.current;
    if (!a) return;
    a.currentTime = Math.max(0, t);
    setNow(a.currentTime);
    if (play) void a.play();
  };

  const nowLine = active >= 0 && lines ? lines[active] : null;
  const toCheck = lines?.filter((l) => l.check) ?? [];
  /** Play the next line the sync wasn't sure about (after the playhead, else from the top). */
  const playNextToCheck = () => {
    const next = toCheck.find((l) => lineStart(l) > now + 0.5) ?? toCheck[0];
    if (!next) return;
    list.current?.querySelector(`[data-line-text="${next.uid}"]`)?.scrollIntoView({ block: "center", behavior: "smooth" });
    seek(lineStart(next) - 1.5);
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex h-14 shrink-0 items-center gap-2 border-b border-line bg-panel px-3 sm:px-5">
        <IconButton label="Back to start" onClick={onBack}>
          <ChevronLeft className="size-5" />
        </IconButton>
        <span className="min-w-0 flex-1 truncate text-md font-semibold" lang={lang}>
          {title}
        </span>
        <span className="hidden text-base text-ink-soft sm:inline" aria-live="polite">
          {save === "saving" ? "Saving…" : save === "saved" ? "Timing saved" : save === "error" ? "Couldn't save" : ""}
        </span>
        <Button
          variant="primary"
          size="sm"
          loading={busy}
          disabled={!lines?.length}
          aria-expanded={making}
          icon={<Film className="size-3.5" />}
          onClick={() => setMaking((m) => !m)}
        >
          Make {aspect === "16:9" ? "16:9" : "9:16"} music video
        </Button>
        <Button
          size="sm"
          variant="danger"
          aria-label={confirmDelete ? "Confirm delete song" : "Delete song"}
          title="Deletes the song and its timing. Its music videos stay in Videos."
          disabled={busy}
          icon={<Trash2 className="size-3.5" />}
          onClick={async () => {
            if (!confirmDelete) {
              setConfirmDelete(true);
              setTimeout(() => setConfirmDelete(false), 3000);
              return;
            }
            audio.current?.pause();
            await pending.current; // let an in-flight timing save finish first
            onDelete();
          }}
        >
          <span className={confirmDelete ? "" : "hidden md:inline"}>{confirmDelete ? "Confirm delete" : "Delete"}</span>
        </Button>
      </header>

      {making && (
        <div className="max-h-[62vh] shrink-0 overflow-y-auto border-b border-line bg-panel px-4 py-3 sm:px-8">
          <div className="mx-auto grid max-w-[760px] gap-2">
            <MusicVideoOptions
              name={name}
              lang={lang}
              aspect={aspect}
              sample={lines?.find((l) => l.text.trim())?.text ?? title}
              sections={sections}
              value={settings}
              onChange={setSettings}
            />
            <div className="flex justify-end gap-2">
              <Button size="sm" variant="ghost" onClick={() => setMaking(false)}>
                Cancel
              </Button>
              <Button
                size="sm"
                variant="primary"
                loading={busy}
                icon={<Film className="size-3.5" />}
                onClick={async () => {
                  setError("");
                  await pending.current;
                  if (dirty.current && lines) await api.saveLyrics(name, toSave(lines)).catch(() => undefined);
                  const err = await onMakeVideo(settings);
                  if (err) setError(err);
                  else setMaking(false);
                }}
              >
                Make video
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* player + what's being sung right now */}
      <div className="shrink-0 border-b border-line bg-[#141a26] px-4 py-4 text-white sm:px-8">
        <div className="mx-auto grid max-w-[760px] gap-3">
          <p lang={lang} className="m-0 min-h-[2.6em] text-center font-display text-[clamp(18px,2.4vw,26px)] leading-snug font-bold">
            {nowLine ? (
              nowLine.words.map((w, i) => (
                <span key={i} className={w.start <= now ? "text-caption" : "text-white"}>
                  {w.text}{" "}
                </span>
              ))
            ) : (
              <span className="text-white/40">{playing ? "♪" : "Play the song to check the timing"}</span>
            )}
          </p>
          <div className="flex items-center gap-3">
            <IconButton
              label={playing ? "Pause" : "Play"}
              className="size-10 bg-white/10 text-white hover:bg-white/20 hover:text-white"
              onClick={() => (audio.current?.paused ? void audio.current.play() : audio.current?.pause())}
            >
              {playing ? <Pause className="size-5" /> : <Play className="size-5" />}
            </IconButton>
            <audio
              ref={audio}
              src={outputUrl(name, "song.mp3")}
              controls
              className="h-10 min-w-0 flex-1"
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              onSeeked={(e) => setNow(e.currentTarget.currentTime)}
              onTimeUpdate={(e) => !playing && setNow(e.currentTarget.currentTime)}
            />
            <span className="w-14 text-right font-mono text-md tabular-nums text-white/70">{fmt(now)}</span>
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto grid max-w-[760px] gap-4 px-4 py-5 sm:px-8">
          {loadError && <Message text={loadError} error />}
          {!lines && !loadError && (
            <p className="m-0 flex items-center gap-2 text-md text-ink-soft">
              <Spinner /> Loading the lyrics…
            </p>
          )}

          {lines && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-base text-ink-soft">
              <span>
                {lines.length} lines ·{" "}
                {method === "edited"
                  ? "timing edited"
                  : method === "exact"
                    ? "timed from the song's own word timings"
                  : method === "even"
                    ? "spaced evenly (auto-sync unavailable)"
                    : lines.length
                      ? "timed automatically"
                      : "not timed yet"}
              </span>
              <span className="flex items-center gap-1">
                All lines
                <IconButton label="All lines 0.1 s earlier" onClick={() => edit((ls) => ls.map((l) => shift(l, -0.1)))}>
                  <Minus className="size-3.5" />
                </IconButton>
                <IconButton label="All lines 0.1 s later" onClick={() => edit((ls) => ls.map((l) => shift(l, 0.1)))}>
                  <Plus className="size-3.5" />
                </IconButton>
              </span>
              <label className="flex items-center gap-1.5">
                <input type="checkbox" checked={follow} onChange={(e) => setFollow(e.target.checked)} className="size-4 accent-cobalt" />
                Follow the song
              </label>
              <label className="flex items-center gap-1.5" title="When you change a line's time, every line after it moves by the same amount">
                <input type="checkbox" checked={ripple} onChange={(e) => setRipple(e.target.checked)} className="size-4 accent-cobalt" />
                Move later lines too
              </label>
              <span className="ml-auto flex flex-wrap items-center gap-1">
                <Button size="sm" variant="ghost" icon={<ListPlus className="size-3.5" />} onClick={() => addLine(now, now + 2)}>
                  Add line at {fmt(now)}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy}
                  icon={<RefreshCw className="size-3.5" />}
                  onClick={async () => {
                    if (method === "edited" && !confirmResync) {
                      setConfirmResync(true);
                      return;
                    }
                    setConfirmResync(false);
                    setError("");
                    const err = await onResync();
                    if (err) setError(err);
                  }}
                >
                  {confirmResync ? "Replace my edits? Click again" : lines.length ? "Sync again" : "Sync lyrics"}
                </Button>
              </span>
            </div>
          )}
          <Message text={error} error />
          {toCheck.length > 0 && (
            <p className="m-0 flex flex-wrap items-center gap-2 rounded-lg border border-warn/40 bg-warn/[0.08] px-3 py-2 text-base text-ink" role="status">
              <CircleAlert className="size-4 shrink-0 text-warn" />
              <span className="min-w-0 flex-1">
                The sync isn&apos;t sure about <strong>{toCheck.length}</strong> line{toCheck.length === 1 ? "" : "s"}. Listen to {toCheck.length === 1 ? "it" : "them"}; fix
                the timing or press <strong>Looks right</strong>.
              </span>
              <Button size="sm" variant="secondary" icon={<Play className="size-3.5" />} onClick={playNextToCheck}>
                Play next to check
              </Button>
            </p>
          )}
          {deleted && (
            <p className="m-0 flex items-center gap-2 rounded-lg bg-ink/[0.05] px-3 py-1.5 text-base text-ink-soft" role="status">
              <span className="min-w-0 flex-1 truncate">
                Deleted “<span lang={lang}>{deleted.row.text}</span>”
              </span>
              <Button
                size="sm"
                variant="ghost"
                icon={<Undo2 className="size-3.5" />}
                onClick={() => {
                  const { row, index } = deleted;
                  edit((ls) => [...ls.slice(0, index), row, ...ls.slice(index)]);
                  setDeleted(null);
                }}
              >
                Undo
              </Button>
            </p>
          )}

          {lines && (
            <ol ref={list} className="@container m-0 grid list-none gap-1.5 p-0">
              {lines.map((line, i) => {
                const start = lineStart(line);
                const end = lineEnd(line);
                const newSection = i === 0 || lines[i - 1].section !== line.section;
                const isActive = i === active;
                const expanded = open.has(line.uid);
                return (
                  <li key={line.uid} data-line={i} className="grid gap-1.5">
                    {newSection && <p className="m-0 mt-3 text-sm font-semibold tracking-wide text-ink-soft uppercase">{sections[line.section] ?? ""}</p>}
                    <div
                      className={`grid gap-1.5 rounded-lg border px-2 py-1.5 ${
                        isActive ? "border-cobalt bg-cobalt/[0.06]" : line.check ? "border-warn/60 bg-warn/[0.06]" : "border-line bg-panel"
                      }`}
                    >
                      {line.check && (
                        <div className="flex items-center gap-2 text-sm text-ink-soft">
                          <CircleAlert className="size-3.5 shrink-0 text-warn" />
                          <span className="flex-1">Not sure about this line&apos;s timing. Play it to check.</span>
                          <Button size="sm" variant="ghost" icon={<Check className="size-3.5" />} onClick={() => editLine(line.uid, (l) => ({ ...l, check: false }))}>
                            Looks right
                          </Button>
                        </div>
                      )}
                      <div className="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-2 gap-y-1 @3xl:grid-cols-[auto_minmax(0,1fr)_auto]">
                        <div className="flex items-center gap-1">
                          <IconButton label="Play from this line" onClick={() => seek(start - 0.6)}>
                            <Play className="size-3.5" />
                          </IconButton>
                          <TimeInput label={`Line ${i + 1} start`} value={start} onCommit={(t) => startAt(line.uid, t)} />
                          <span className="text-ink-soft/60">–</span>
                          <TimeInput label={`Line ${i + 1} end`} value={end} onCommit={(t) => endAt(line.uid, t)} />
                        </div>
                        <input
                          lang={lang}
                          aria-label={`Line ${i + 1} text`}
                          data-line-text={line.uid}
                          className="field-input h-9 min-w-0"
                          value={line.text}
                          onChange={(e) => editLine(line.uid, (l) => retext(l, e.target.value))}
                        />
                        <div className="col-span-2 flex flex-wrap items-center justify-end gap-0.5 @3xl:col-span-1">
                          <IconButton label="0.1 s earlier" onClick={() => retime(line.uid, (l) => shift(l, -0.1), "start")}>
                            <Minus className="size-3.5" />
                          </IconButton>
                          <IconButton label="0.1 s later" onClick={() => retime(line.uid, (l) => shift(l, 0.1), "start")}>
                            <Plus className="size-3.5" />
                          </IconButton>
                          <Button size="sm" variant="ghost" title="This line starts at the playhead" disabled={now >= end} onClick={() => startAt(line.uid, now)}>
                            Start here
                          </Button>
                          <Button size="sm" variant="ghost" title="This line ends at the playhead" disabled={now <= start} onClick={() => endAt(line.uid, now)}>
                            End here
                          </Button>
                          <IconButton
                            label={expanded ? "Hide word timing" : "Word timing"}
                            aria-expanded={expanded}
                            onClick={() =>
                              setOpen((s) => {
                                const next = new Set(s);
                                if (next.has(line.uid)) next.delete(line.uid);
                                else next.add(line.uid);
                                return next;
                              })
                            }
                          >
                            <ChevronDown className={`size-4 transition-transform ${expanded ? "rotate-180" : ""}`} />
                          </IconButton>
                          <IconButton label="Add a line after this one" onClick={() => addAfter(i)}>
                            <ListPlus className="size-3.5" />
                          </IconButton>
                          <IconButton label="Delete this line" tone="danger" onClick={() => removeLine(i)}>
                            <Trash2 className="size-3.5" />
                          </IconButton>
                        </div>
                      </div>

                      {expanded && (
                        <div className="grid gap-1.5 border-t border-line pt-2">
                          <ul className="m-0 flex list-none flex-wrap gap-1.5 p-0">
                            {line.words.map((w, k) => (
                              <li
                                key={k}
                                className={`grid justify-items-center gap-1 rounded-md border px-1.5 py-1 ${
                                  w.start <= now && now < w.end ? "border-cobalt bg-cobalt/[0.08]" : "border-line"
                                }`}
                              >
                                <button
                                  type="button"
                                  lang={lang}
                                  title="Play from this word"
                                  onClick={() => seek(w.start - 0.3)}
                                  className="cursor-pointer rounded border-0 bg-transparent px-1 text-base font-semibold text-ink hover:bg-ink/[0.06]"
                                >
                                  {w.text}
                                </button>
                                <span className="flex items-center gap-0.5">
                                  <TimeInput label={`“${w.text}” starts`} value={w.start} onCommit={(t) => editLine(line.uid, (l) => setWordStart(l, k, t))} />
                                  <IconButton label={`“${w.text}” starts at the playhead`} className="size-6" onClick={() => editLine(line.uid, (l) => setWordStart(l, k, now))}>
                                    <Crosshair className="size-3" />
                                  </IconButton>
                                </span>
                              </li>
                            ))}
                            <li className="grid content-end justify-items-center gap-1 px-1 py-1">
                              <span className="text-sm text-ink-soft">line ends</span>
                              <span className="flex items-center gap-0.5">
                                <TimeInput label="Last word ends" value={end} onCommit={(t) => retime(line.uid, (l) => setLastWordEnd(l, t), "end")} />
                                <IconButton label="Line ends at the playhead" className="size-6" onClick={() => retime(line.uid, (l) => setLastWordEnd(l, now), "end")}>
                                  <Crosshair className="size-3" />
                                </IconButton>
                              </span>
                            </li>
                          </ul>
                          <p className="m-0 text-sm text-ink-soft">
                            Each word lights up at its start time. Play the song and click <Crosshair className="inline size-3" /> the moment a word is sung, or type a time.
                          </p>
                        </div>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
          {lines && (
            <p className="m-0 text-base text-ink-soft">
              Play the song and watch the line above the player. If a line is early or late, nudge it with − / +, type its start and end, or pause where it
              really starts and press <strong>Start here</strong>. With <strong>Move later lines too</strong> on, every line after it moves by the same
              amount, so fixing the first line that&apos;s off usually fixes the rest. Open a line&apos;s word timing to time each word. Missing a line? Pause where it&apos;s sung and
              press <strong>Add line</strong>. Changes save automatically and the next music video uses them.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
