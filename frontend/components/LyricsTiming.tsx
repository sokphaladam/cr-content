"use client";

import {
  Check,
  ChevronLeft,
  CircleAlert,
  Crosshair,
  Film,
  Keyboard,
  ListPlus,
  Maximize2,
  Minus,
  Music,
  Pause,
  Play,
  Plus,
  Redo2,
  RefreshCw,
  Repeat,
  SkipBack,
  SkipForward,
  Trash2,
  Undo2,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { api, outputUrl, type Aspect, type Lang, type LyricsTiming as Timing, type MusicVideoSettings, type SongArtSlot, type TimedLine, type VideoSummary } from "@/lib/api";
import { DraftHistory } from "@/lib/draftHistory";
import {
  audioPeaks,
  fmt,
  GAP,
  lineEnd,
  lineStart,
  MIN_LINE,
  newUid,
  parseTime,
  pictureClips,
  respan,
  retext,
  round,
  setLastWordEnd,
  setWordStart,
  settle,
  shift,
  spread,
  type Row,
} from "@/lib/lyricTiming";
import { LyricMonitor } from "./LyricMonitor";
import { LyricTimeline, MAX_PPS, MIN_PPS } from "./LyricTimeline";
import { MusicVideoOptions } from "./MusicVideoOptions";
import { Button, IconButton, Message, Spinner, useToast } from "./ui";

/** A time you can type ("1:23.45" or seconds). Commits on Enter or when it loses focus; Escape cancels. */
function TimeInput({
  value,
  onCommit,
  label,
  compact = false,
}: {
  value: number;
  onCommit: (t: number) => void;
  label: string;
  compact?: boolean; // borderless until hovered, for the dense line list
}) {
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
      className={`rounded-md border text-center font-mono tabular-nums text-ink transition-colors focus:border-cobalt focus:bg-panel focus:outline-none ${
        compact ? "h-7 w-[4.25rem] bg-transparent text-xs hover:border-line" : "h-8 w-[5.25rem] bg-panel text-sm"
      } ${bad ? "border-danger" : compact ? "border-transparent" : "border-line"}`}
    />
  );
}

/** A small on/off button for the transport bar. */
function Toggle({ pressed, onClick, icon, children, title }: { pressed: boolean; onClick: () => void; icon?: ReactNode; children: ReactNode; title: string }) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      title={title}
      onClick={onClick}
      className={`inline-flex h-8 shrink-0 cursor-pointer items-center gap-1.5 rounded-lg border px-2.5 text-sm font-semibold whitespace-nowrap transition-colors ${
        pressed ? "border-cobalt/40 bg-cobalt-soft text-cobalt" : "border-transparent bg-transparent text-ink-soft hover:bg-ink/[0.05] hover:text-ink"
      }`}
    >
      {icon}
      {children}
    </button>
  );
}

const Kbd = ({ children }: { children: ReactNode }) => (
  <kbd className="inline-grid min-w-[1.4rem] place-items-center rounded border border-line border-b-2 bg-sunken px-1 font-mono text-2xs text-ink">{children}</kbd>
);

const SHORTCUTS: [string[], string][] = [
  [["Space"], "Play / pause"],
  [["←", "→"], "Back / forward 1 s (Shift: 5 s)"],
  [["↑", "↓"], "Previous / next line"],
  [["Enter"], "Play the selected line"],
  [["["], "Selected line starts at the playhead"],
  [["]"], "Selected line ends at the playhead"],
  [[",", "."], "Nudge the selected line 0.1 s (Shift: 0.5 s)"],
  [["L"], "Loop the selected line"],
  [["N"], "Add a line at the playhead"],
  [["Del"], "Delete the selected line"],
  [["Ctrl", "Z"], "Undo (Ctrl+Shift+Z to redo)"],
  [["Ctrl", "Wheel"], "Zoom the timeline"],
];

type Save = "idle" | "saving" | "saved" | "error";
const SPEEDS = [0.5, 0.75, 1];

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
  onResync: () => Promise<string | null>;
  onMakeVideo: (settings: MusicVideoSettings) => Promise<string | null>;
}) {
  const toast = useToast();
  const [settings, setSettings] = useState(initialSettings);
  const [making, setMaking] = useState(false); // the "make music video" sheet is open
  const [lines, setLines] = useState<Row[] | null>(null);
  const [method, setMethod] = useState<Timing["timing"]>("");
  const [loadError, setLoadError] = useState("");
  const [save, setSave] = useState<Save>("idle");
  const [error, setError] = useState("");
  const [now, setNow] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [follow, setFollow] = useState(true);
  const [ripple, setRipple] = useState(true); // retiming a line moves every line after it by the same amount
  const [loop, setLoop] = useState(false); // replay the selected line
  const [speed, setSpeed] = useState(1);
  const [pps, setPps] = useState(40); // timeline zoom, pixels per second
  const [peaks, setPeaks] = useState<Float32Array | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [confirmResync, setConfirmResync] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [showKeys, setShowKeys] = useState(false);
  const [bigMonitor, setBigMonitor] = useState(false);
  const [slots, setSlots] = useState<SongArtSlot[]>([]); // the planned pictures (the art plan)
  const [renders, setRenders] = useState<VideoSummary[] | null>(null); // music videos made from the song, newest first
  const [fresh, setFresh] = useState<string | null>(null); // just-added line: focus its text
  const audio = useRef<HTMLAudioElement>(null);
  const list = useRef<HTMLOListElement>(null);
  const dirty = useRef(false);
  const pending = useRef<Promise<unknown>>(Promise.resolve());
  const linesRef = useRef<Row[] | null>(null);
  const [history] = useState(() => new DraftHistory<Row[]>());
  const historyFlags = useSyncExternalStore(history.subscribe, history.flags, () => "00");
  const canUndo = historyFlags[0] === "1";
  const canRedo = historyFlags[1] === "1";

  useEffect(() => {
    linesRef.current = lines;
  }, [lines]);

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

  // the song's planned pictures and its music videos, for the monitor and the timeline's video tracks
  useEffect(() => {
    let alive = true;
    api
      .songArtPlan(name)
      .then((r) => alive && setSlots(r.plan?.slots ?? []))
      .catch(() => {});
    api
      .video(name)
      .then((d) => alive && setRenders(d.versions.filter((v) => v.video)))
      .catch(() => alive && setRenders([]));
    return () => {
      alive = false;
    };
  }, [name]);

  // the waveform for the timeline (optional: without it the lyric blocks still work)
  useEffect(() => {
    const ctl = new AbortController();
    audioPeaks(outputUrl(name, "song.mp3"), ctl.signal)
      .then(setPeaks)
      .catch(() => undefined);
    return () => ctl.abort();
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

  const edit = useCallback(
    (update: (ls: Row[]) => Row[]) => {
      dirty.current = true;
      setSave("idle");
      setLines((ls) => {
        if (!ls) return ls;
        history.record(ls);
        return update(ls);
      });
    },
    [history],
  );
  const restore = (to: Row[] | null) => {
    if (!to) return;
    dirty.current = true;
    setSave("idle");
    setLines(to);
  };
  const undo = () => linesRef.current && restore(history.undo(linesRef.current));
  const redo = () => linesRef.current && restore(history.redo(linesRef.current));

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
    retime(uid, (l) => (ripple ? shift(l, t - lineStart(l)) : respan(l, t, Math.max(lineEnd(l), t + MIN_LINE))), "start");
  const endAt = (uid: string, t: number) => retime(uid, (l) => respan(l, lineStart(l), Math.max(t, lineStart(l) + MIN_LINE)), "end");
  const nudge = (uid: string, by: number) => retime(uid, (l) => shift(l, by), "start");

  const editLine = (uid: string, update: (l: Row) => Row) => edit((ls) => settle(ls.map((l) => (l.uid === uid ? update(l) : l)), uid));

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
    setSelected(uid);
    setFresh(uid);
  };
  const addAfter = (uid: string) => {
    if (!lines) return;
    const i = lines.findIndex((l) => l.uid === uid);
    if (i < 0) return;
    const start = lineEnd(lines[i]) + 0.2;
    const next = lines[i + 1] ? lineStart(lines[i + 1]) - 0.1 : start + 2;
    addLine(start, Math.max(start + 0.6, Math.min(start + 2, next)));
  };
  const removeLine = (uid: string) => {
    if (!lines) return;
    const i = lines.findIndex((l) => l.uid === uid);
    if (i < 0) return;
    edit((ls) => ls.filter((l) => l.uid !== uid));
    setSelected(lines[i + 1]?.uid ?? lines[i - 1]?.uid ?? null);
    toast(`Deleted “${lines[i].text}”. Press Ctrl+Z to bring it back.`);
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

  useEffect(() => {
    if (audio.current) audio.current.playbackRate = speed;
  }, [speed]);

  const seek = useCallback((t: number, play = false) => {
    const a = audio.current;
    if (!a) return;
    a.currentTime = Math.max(0, t);
    setNow(a.currentTime);
    if (play) void a.play();
  }, []);
  const togglePlay = () => (audio.current?.paused ? void audio.current.play() : audio.current?.pause());

  const total = Math.max(duration, lines?.length ? lineEnd(lines[lines.length - 1]) + 2 : 0, 1);
  const active = lines ? lines.findLastIndex((l) => lineStart(l) - 0.3 <= now && now <= lineEnd(l) + 0.6) : -1;
  const selIndex = lines && selected ? lines.findIndex((l) => l.uid === selected) : -1;
  const sel = selIndex >= 0 && lines ? lines[selIndex] : null;

  // the list follows the song
  useEffect(() => {
    if (!follow || !playing || active < 0 || !lines) return;
    list.current?.querySelector(`[data-uid="${lines[active].uid}"]`)?.scrollIntoView({ block: "center", behavior: "smooth" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, follow, playing]);
  // ... and the selection
  useEffect(() => {
    if (selected) list.current?.querySelector(`[data-uid="${selected}"]`)?.scrollIntoView({ block: "nearest" });
  }, [selected]);

  // loop the selected line
  const selStart = sel ? lineStart(sel) : 0;
  const selEnd = sel ? lineEnd(sel) : 0;
  useEffect(() => {
    if (loop && playing && sel && now > selEnd + 0.25) seek(selStart - 0.4);
  }, [loop, playing, sel, now, selStart, selEnd, seek]);

  const clips = lines && settings.art_style !== "" ? pictureClips(slots, lines, sections, total) : [];
  const toCheck = lines?.filter((l) => l.check) ?? [];
  /** Play the next line the sync wasn't sure about (after the playhead, else from the top). */
  const playNextToCheck = () => {
    const next = toCheck.find((l) => lineStart(l) > now + 0.5) ?? toCheck[0];
    if (!next) return;
    setSelected(next.uid);
    seek(lineStart(next) - 1.5, true);
  };
  const jumpLine = (dir: -1 | 1) => {
    if (!lines?.length) return;
    const target = dir < 0 ? lines.findLast((l) => lineStart(l) < now - 0.3) : lines.find((l) => lineStart(l) > now + 0.05);
    if (target) seek(lineStart(target), playing);
  };
  const selectStep = (dir: -1 | 1) => {
    if (!lines?.length) return;
    const from = selIndex >= 0 ? selIndex : active >= 0 ? active : dir > 0 ? -1 : lines.length;
    const next = lines[Math.min(lines.length - 1, Math.max(0, from + dir))];
    setSelected(next.uid);
    seek(lineStart(next), false);
  };

  // keyboard shortcuts (not while typing in a field, and not while the video sheet is open)
  const onKey = useRef<(e: KeyboardEvent) => void>(() => {});
  useEffect(() => {
    onKey.current = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (making || el.closest("input, textarea, select, [contenteditable=true]")) return;
      const mod = e.ctrlKey || e.metaKey;
      const k = e.key;
      if (mod && k.toLowerCase() === "z") (e.shiftKey ? redo : undo)();
      else if (mod && k.toLowerCase() === "y") redo();
      else if (mod || e.altKey) return;
      else if (k === " ") {
        if (el.closest("button")) return; // let the focused button handle it
        togglePlay();
      } else if (k === "ArrowLeft" || k === "ArrowRight") seek(now + (k === "ArrowLeft" ? -1 : 1) * (e.shiftKey ? 5 : 1));
      else if (k === "ArrowUp" || k === "ArrowDown") selectStep(k === "ArrowUp" ? -1 : 1);
      else if (k === "n" || k === "N") addLine(now, now + 2);
      else if (!sel) return;
      else if (k === "Enter") seek(lineStart(sel) - 0.4, true);
      else if (k === "[") startAt(sel.uid, now);
      else if (k === "]") {
        if (now > lineStart(sel)) endAt(sel.uid, now);
      }
      else if (k === "," || k === "<") nudge(sel.uid, e.shiftKey ? -0.5 : -0.1);
      else if (k === "." || k === ">") nudge(sel.uid, e.shiftKey ? 0.5 : 0.1);
      else if (k === "l" || k === "L") setLoop((v) => !v);
      else if (k === "Delete" || k === "Backspace") removeLine(sel.uid);
      else if (k === "Escape") setSelected(null);
      else return;
      e.preventDefault();
    };
  });
  useEffect(() => {
    const handler = (e: KeyboardEvent) => onKey.current(e);
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (!making) return;
    const close = (e: KeyboardEvent) => e.key === "Escape" && setMaking(false);
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [making]);

  const methodText =
    method === "edited"
      ? "Timing edited"
      : method === "exact"
        ? "Timed from the song's word timings"
        : method === "even"
          ? "Spaced evenly (auto-sync unavailable)"
          : lines?.length
            ? "Timed automatically"
            : "Not timed yet";


  const resync = async () => {
    if (method === "edited" && !confirmResync) {
      setConfirmResync(true);
      setTimeout(() => setConfirmResync(false), 4000);
      return;
    }
    setConfirmResync(false);
    setError("");
    const err = await onResync();
    if (err) setError(err);
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-paper">
      {/* ---------- toolbar ---------- */}
      <header className="pane-header gap-3 px-2 sm:px-3">
        <div className="flex min-w-0 items-center gap-1.5">
          <IconButton label="Back to start" onClick={onBack}>
            <ChevronLeft className="size-5" />
          </IconButton>
          <div className="min-w-0">
            <h1 lang={lang} className="m-0 truncate text-md leading-tight font-semibold">
              {title}
            </h1>
            <p className="m-0 flex items-center gap-1.5 truncate text-xs text-ink-soft">
              <Music className="size-3 shrink-0" />
              <span className="truncate">
                Lyric timing{lines ? ` · ${lines.length} lines · ${methodText}` : ""}
              </span>
              <span aria-live="polite" className="flex shrink-0 items-center gap-1">
                {save !== "idle" && <span aria-hidden className={`size-1.5 rounded-full ${save === "error" ? "bg-danger" : save === "saving" ? "bg-warn" : "bg-ok"}`} />}
                {save === "saving" ? "Saving…" : save === "saved" ? "Saved" : save === "error" ? "Couldn't save" : ""}
              </span>
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <IconButton label="Undo (Ctrl+Z)" disabled={!canUndo} onClick={undo}>
            <Undo2 className="size-4" />
          </IconButton>
          <IconButton label="Redo (Ctrl+Shift+Z)" disabled={!canRedo} onClick={redo}>
            <Redo2 className="size-4" />
          </IconButton>
          <span aria-hidden className="mx-1 h-5 w-px bg-line" />
          <Button size="sm" variant="ghost" disabled={busy || !lines} icon={<RefreshCw className="size-3.5" />} onClick={resync} title="Time the lyrics to the song again automatically">
            <span className={confirmResync ? "" : "hidden md:inline"}>{confirmResync ? "Replace my edits?" : lines?.length ? "Sync again" : "Sync lyrics"}</span>
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
            {confirmDelete && "Confirm delete"}
          </Button>
          <Button
            variant="primary"
            size="sm"
            loading={busy}
            disabled={!lines?.length}
            aria-expanded={making}
            icon={<Film className="size-3.5" />}
            onClick={() => setMaking((m) => !m)}
          >
            <span className="hidden sm:inline">Make {aspect === "16:9" ? "16:9" : "9:16"} video</span>
            <span className="sm:hidden">Video</span>
          </Button>
        </div>
      </header>
      {error && (
        <div className="shrink-0 border-b border-danger/30 bg-danger/[0.06] px-4 py-2">
          <Message text={error} error />
        </div>
      )}

      <audio
        ref={audio}
        src={outputUrl(name, "song.mp3")}
        preload="auto"
        className="hidden"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onLoadedMetadata={(e) => {
          setDuration(e.currentTarget.duration || 0);
          e.currentTarget.playbackRate = speed;
        }}
        onSeeked={(e) => setNow(e.currentTarget.currentTime)}
        onTimeUpdate={(e) => !playing && setNow(e.currentTarget.currentTime)}
      />

      <div className="@container relative flex min-h-0 flex-1 flex-col">
        {/* ---------- workspace: lyric list | monitor + inspector ---------- */}
        <div
          className={`min-h-0 flex-1 overflow-y-auto @4xl:grid @4xl:overflow-hidden ${
            bigMonitor ? "@4xl:grid-cols-[minmax(0,1fr)_minmax(24rem,42%)]" : "@4xl:grid-cols-[minmax(0,1fr)_minmax(19rem,24rem)]"
          }`}
        >
          <aside className="flex flex-col gap-3 border-line p-3 *:shrink-0 @4xl:order-last @4xl:min-h-0 @4xl:overflow-y-auto @4xl:border-l @4xl:bg-panel">
            {/* monitor */}
            {lines && (
              <LyricMonitor
                lang={lang}
                aspect={aspect}
                lines={lines}
                sections={sections}
                now={now}
                playing={playing}
                settings={settings}
                slots={slots}
                clips={clips}
                latest={renders === null ? undefined : (renders[0] ?? null)}
                big={bigMonitor}
                onBig={() => setBigMonitor((v) => !v)}
              />
            )}
            {/* inspector */}
            {sel ? (
              <section aria-label={`Line ${selIndex + 1}`} className="grid gap-3 card p-3 @4xl:border-0 @4xl:p-0 @4xl:shadow-none">
                <div className="flex items-center justify-between gap-2">
                  <h2 className="card-title m-0">
                    Line {selIndex + 1} <span className="font-sans text-sm font-normal text-ink-soft">of {lines!.length}</span>
                  </h2>
                  <select
                    aria-label="Part of the song"
                    value={sel.section}
                    onChange={(e) => editLine(sel.uid, (l) => ({ ...l, section: Number(e.target.value) }))}
                    className="field-input h-8 w-auto max-w-[10rem] py-0 text-sm"
                  >
                    {sections.map((s, i) => (
                      <option key={i} value={i}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
                <input
                  lang={lang}
                  aria-label="Line text"
                  className="field-input h-9"
                  value={sel.text}
                  onChange={(e) => editLine(sel.uid, (l) => retext(l, e.target.value))}
                />

                {sel.check && (
                  <div className="flex items-center gap-2 rounded-lg border border-warn/40 bg-warn/[0.08] px-2.5 py-1.5 text-sm">
                    <CircleAlert className="size-4 shrink-0 text-warn" />
                    <span className="min-w-0 flex-1">The sync isn&apos;t sure about this line.</span>
                    <Button size="sm" variant="secondary" icon={<Check className="size-3.5" />} onClick={() => editLine(sel.uid, (l) => ({ ...l, check: false }))}>
                      Looks right
                    </Button>
                  </div>
                )}

                <div className="grid grid-cols-[3rem_auto_minmax(0,1fr)] items-center gap-x-2 gap-y-1.5 well p-2.5">
                  <span className="field-label">Start</span>
                  <TimeInput label="Line start" value={selStart} onCommit={(t) => startAt(sel.uid, t)} />
                  <Button size="sm" variant="ghost" className="justify-self-start" title="Start at the playhead ( [ )" disabled={now >= selEnd} onClick={() => startAt(sel.uid, now)} icon={<Crosshair className="size-3.5" />}>
                    Playhead
                  </Button>
                  <span className="field-label">End</span>
                  <TimeInput label="Line end" value={selEnd} onCommit={(t) => endAt(sel.uid, t)} />
                  <Button size="sm" variant="ghost" className="justify-self-start" title="End at the playhead ( ] )" disabled={now <= selStart} onClick={() => endAt(sel.uid, now)} icon={<Crosshair className="size-3.5" />}>
                    Playhead
                  </Button>
                  <span className="field-label">Nudge</span>
                  <div className="col-span-2 flex items-center gap-1">
                    {[-0.5, -0.1, 0.1, 0.5].map((by) => (
                      <button
                        key={by}
                        type="button"
                        title={`Move the line ${Math.abs(by)} s ${by < 0 ? "earlier" : "later"}`}
                        onClick={() => nudge(sel.uid, by)}
                        className="h-7 flex-1 cursor-pointer rounded-md border border-line bg-panel font-mono text-xs text-ink tabular-nums hover:border-line-strong"
                      >
                        {by > 0 ? "+" : "−"}
                        {Math.abs(by)}
                      </button>
                    ))}
                  </div>
                  <span className="col-span-3 text-xs text-ink-soft">
                    Length {(selEnd - selStart).toFixed(2)} s{ripple ? " · later lines move with it" : ""}
                  </span>
                </div>

                <div className="grid gap-1.5">
                  <span className="field-label">Words</span>
                  <ul className="m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(6.5rem,1fr))] gap-1.5 p-0">
                    {sel.words.map((w, k) => (
                      <li
                        key={k}
                        className={`grid min-w-0 justify-items-center gap-1 rounded-md border px-1 py-1 ${w.start <= now && now < w.end ? "border-cobalt bg-cobalt/[0.08]" : "border-line bg-panel"}`}
                      >
                        <button
                          type="button"
                          lang={lang}
                          title="Play from this word"
                          onClick={() => seek(w.start - 0.3, true)}
                          className="max-w-full cursor-pointer truncate rounded border-0 bg-transparent px-1 text-sm font-semibold text-ink hover:bg-ink/[0.06]"
                        >
                          {w.text}
                        </button>
                        <span className="flex items-center">
                          <TimeInput compact label={`“${w.text}” starts`} value={w.start} onCommit={(t) => editLine(sel.uid, (l) => setWordStart(l, k, t))} />
                          <IconButton label={`“${w.text}” starts at the playhead`} className="size-6" onClick={() => editLine(sel.uid, (l) => setWordStart(l, k, now))}>
                            <Crosshair className="size-3" />
                          </IconButton>
                        </span>
                      </li>
                    ))}
                    <li className="grid content-end justify-items-center gap-1 rounded-md border border-dashed border-line px-1 py-1">
                      <span className="text-xs text-ink-soft">line ends</span>
                      <span className="flex items-center">
                        <TimeInput compact label="Last word ends" value={selEnd} onCommit={(t) => retime(sel.uid, (l) => setLastWordEnd(l, t), "end")} />
                        <IconButton label="Line ends at the playhead" className="size-6" onClick={() => retime(sel.uid, (l) => setLastWordEnd(l, now), "end")}>
                          <Crosshair className="size-3" />
                        </IconButton>
                      </span>
                    </li>
                  </ul>
                  <p className="m-0 text-xs text-ink-soft">Each word lights up at its start time. Play the line and click the crosshair the moment a word is sung.</p>
                </div>

                <div className="flex flex-wrap gap-1.5">
                  <Button size="sm" variant="secondary" icon={<Play className="size-3.5" />} onClick={() => seek(selStart - 0.4, true)}>
                    Play line
                  </Button>
                  <Toggle pressed={loop} onClick={() => setLoop((v) => !v)} icon={<Repeat className="size-3.5" />} title="Replay this line until you turn it off (L)">
                    Loop
                  </Toggle>
                  <span className="flex-1" />
                  <IconButton label="Add a line after this one" onClick={() => addAfter(sel.uid)}>
                    <ListPlus className="size-4" />
                  </IconButton>
                  <IconButton label="Delete this line (Del)" tone="danger" onClick={() => removeLine(sel.uid)}>
                    <Trash2 className="size-4" />
                  </IconButton>
                </div>
              </section>
            ) : (
              lines &&
              lines.length > 0 && (
                <div className="hidden gap-2 text-sm text-ink-soft @4xl:grid">
                  <p className="m-0">
                    Select a line in the list or on the timeline to edit its words and timing. Drag a block on the timeline to move a line, or drag its edges to
                    trim it.
                  </p>
                  <p className="m-0">
                    With <strong className="text-ink">Ripple</strong> on, every line after the one you change moves by the same amount, so fixing the first line
                    that&apos;s off usually fixes the rest.
                  </p>
                </div>
              )
            )}
          </aside>

          {/* lyric list */}
          <section aria-label="Lyrics" className="flex min-h-0 flex-col @4xl:overflow-hidden">
            <div className="sticky top-0 z-10 flex h-11 shrink-0 items-center gap-2 border-b border-line bg-paper/95 px-3 backdrop-blur">
              <span className="text-sm font-semibold text-ink">Lines</span>
              {toCheck.length > 0 && (
                <button
                  type="button"
                  onClick={playNextToCheck}
                  title="Play the next line the sync wasn't sure about"
                  className="inline-flex h-6 cursor-pointer items-center gap-1 rounded-full border border-warn/40 bg-warn/[0.1] px-2 text-xs font-semibold text-ink hover:bg-warn/[0.18]"
                >
                  <CircleAlert className="size-3 text-warn" />
                  {toCheck.length} to check
                  <Play className="size-3" />
                </button>
              )}
              <span className="flex-1" />
              <Button size="sm" variant="ghost" disabled={!lines} icon={<ListPlus className="size-3.5" />} onClick={() => addLine(now, now + 2)} title="Add a line at the playhead (N)">
                Add at {fmt(now)}
              </Button>
            </div>

            <div className="min-h-0 flex-1 px-2 py-2 @4xl:overflow-y-auto">
              {loadError && <Message text={loadError} error />}
              {!lines && !loadError && (
                <p className="m-0 flex items-center gap-2 p-3 text-md text-ink-soft">
                  <Spinner /> Loading the lyrics…
                </p>
              )}
              {lines && lines.length === 0 && (
                <div className="grid justify-items-center gap-2 p-8 text-center">
                  <p className="m-0 text-md text-ink-soft">The lyrics aren&apos;t timed to the song yet.</p>
                  <Button variant="primary" size="sm" icon={<RefreshCw className="size-3.5" />} disabled={busy} onClick={resync}>
                    Sync lyrics
                  </Button>
                </div>
              )}
              {lines && lines.length > 0 && (
                <ol ref={list} className="m-0 grid list-none gap-px p-0">
                  {lines.map((line, i) => {
                    const start = lineStart(line);
                    const end = lineEnd(line);
                    const newSection = i === 0 || lines[i - 1].section !== line.section;
                    const isSel = line.uid === selected;
                    const isActive = i === active;
                    return (
                      <li key={line.uid} className="grid">
                        {newSection && (
                          <p className="m-0 mt-2 mb-1 px-2 text-2xs font-semibold tracking-wider text-ink-soft uppercase first:mt-0">{sections[line.section] ?? ""}</p>
                        )}
                        <div
                          data-uid={line.uid}
                          onClick={() => setSelected(line.uid)}
                          className={`group relative grid grid-cols-[1.5rem_auto_minmax(0,1fr)_auto] items-center gap-1.5 rounded-md border py-0.5 pr-1 pl-1.5 transition-colors ${
                            isSel
                              ? "border-cobalt/50 bg-cobalt-soft"
                              : line.check
                                ? "border-warn/40 bg-warn/[0.06] hover:bg-warn/[0.1]"
                                : "border-transparent hover:bg-ink/[0.04]"
                          }`}
                        >
                          {isActive && <span aria-hidden className="absolute inset-y-1 -left-px w-[3px] rounded-full bg-caption" />}
                          <span className="grid place-items-center font-mono text-2xs text-ink-soft tabular-nums">
                            {line.check ? <CircleAlert aria-label="Needs checking" className="size-3.5 text-warn" /> : i + 1}
                          </span>
                          <span className="flex items-center">
                            <TimeInput compact label={`Line ${i + 1} start`} value={start} onCommit={(t) => startAt(line.uid, t)} />
                            <span aria-hidden className="text-ink-soft/50">–</span>
                            <TimeInput compact label={`Line ${i + 1} end`} value={end} onCommit={(t) => endAt(line.uid, t)} />
                          </span>
                          <input
                            lang={lang}
                            aria-label={`Line ${i + 1} text`}
                            data-line-text={line.uid}
                            value={line.text}
                            onChange={(e) => editLine(line.uid, (l) => retext(l, e.target.value))}
                            onFocus={() => setSelected(line.uid)}
                            className={`h-8 min-w-0 rounded-md border border-transparent bg-transparent px-2 text-md text-ink transition-colors hover:border-line focus:border-cobalt focus:bg-panel focus:outline-none ${
                              isActive ? "font-semibold" : ""
                            }`}
                          />
                          <span className={`flex items-center transition-opacity ${isSel ? "opacity-100" : "opacity-0 group-focus-within:opacity-100 group-hover:opacity-100"}`}>
                            <IconButton label="Play from this line" className="size-7" onClick={() => seek(start - 0.4, true)}>
                              <Play className="size-3.5" />
                            </IconButton>
                            <IconButton label="Delete this line" tone="danger" className="size-7" onClick={() => removeLine(line.uid)}>
                              <Trash2 className="size-3.5" />
                            </IconButton>
                          </span>
                        </div>
                      </li>
                    );
                  })}
                </ol>
              )}
            </div>
          </section>
        </div>

        {/* ---------- transport + timeline ---------- */}
        <div className="shrink-0 border-t border-line bg-panel">
          <div className="flex min-h-12 flex-wrap items-center gap-x-2 gap-y-1 border-b border-line px-2 py-1.5">
            <div className="flex items-center gap-0.5">
              <IconButton label="Previous line" onClick={() => jumpLine(-1)}>
                <SkipBack className="size-4" />
              </IconButton>
              <button
                type="button"
                aria-label={playing ? "Pause" : "Play"}
                title={`${playing ? "Pause" : "Play"} (Space)`}
                onClick={togglePlay}
                className="grid size-9 cursor-pointer place-items-center rounded-full bg-cobalt text-white transition-colors hover:bg-cobalt-deep"
              >
                {playing ? <Pause className="size-4" /> : <Play className="size-4 translate-x-px" />}
              </button>
              <IconButton label="Next line" onClick={() => jumpLine(1)}>
                <SkipForward className="size-4" />
              </IconButton>
            </div>
            <span className="rounded-md bg-sunken px-2 py-1 font-mono text-sm text-ink tabular-nums">
              {fmt(now, 2)} <span className="text-ink-soft">/ {fmt(total, 1)}</span>
            </span>
            <select
              aria-label="Playback speed"
              title="Slow the song down to time words precisely"
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              className="h-8 cursor-pointer rounded-lg border border-line bg-panel px-1.5 text-sm font-semibold text-ink"
            >
              {SPEEDS.map((s) => (
                <option key={s} value={s}>
                  {s}×
                </option>
              ))}
            </select>
            <span aria-hidden className="mx-1 hidden h-5 w-px bg-line sm:block" />
            <Toggle pressed={follow} onClick={() => setFollow((v) => !v)} title="Scroll the list and timeline with the song">
              Follow
            </Toggle>
            <Toggle pressed={ripple} onClick={() => setRipple((v) => !v)} title="When you change a line's time, every line after it moves by the same amount">
              Ripple
            </Toggle>
            <Toggle pressed={loop} onClick={() => setLoop((v) => !v)} icon={<Repeat className="size-3.5" />} title="Replay the selected line (L)">
              Loop
            </Toggle>
            <span className="flex items-center gap-0.5 text-sm text-ink-soft" title="Move every line at once">
              <span className="hidden pl-1 lg:inline">All lines</span>
              <IconButton label="All lines 0.1 s earlier" className="size-7" disabled={!lines?.length} onClick={() => edit((ls) => ls.map((l) => shift(l, -0.1)))}>
                <Minus className="size-3.5" />
              </IconButton>
              <IconButton label="All lines 0.1 s later" className="size-7" disabled={!lines?.length} onClick={() => edit((ls) => ls.map((l) => shift(l, 0.1)))}>
                <Plus className="size-3.5" />
              </IconButton>
            </span>
            <span className="flex-1" />
            <div className="flex items-center gap-0.5">
              <IconButton label="Zoom out" className="size-7" onClick={() => setPps((p) => Math.max(MIN_PPS, p / 1.5))}>
                <ZoomOut className="size-3.5" />
              </IconButton>
              <input
                type="range"
                aria-label="Timeline zoom"
                min={Math.log(MIN_PPS)}
                max={Math.log(MAX_PPS)}
                step={0.01}
                value={Math.log(pps)}
                onChange={(e) => setPps(Math.exp(Number(e.target.value)))}
                className="hidden w-24 md:block"
              />
              <IconButton label="Zoom in" className="size-7" onClick={() => setPps((p) => Math.min(MAX_PPS, p * 1.5))}>
                <ZoomIn className="size-3.5" />
              </IconButton>
              <IconButton
                label="Fit the whole song"
                className="size-7"
                onClick={() => {
                  const w = document.querySelector<HTMLElement>('[aria-label="Timeline"]')?.clientWidth ?? 800;
                  setPps(Math.max(MIN_PPS, (w - 56) / total));
                }}
              >
                <Maximize2 className="size-3.5" />
              </IconButton>
              <div className="relative">
                <IconButton label="Keyboard shortcuts" aria-expanded={showKeys} className="size-7" onClick={() => setShowKeys((v) => !v)}>
                  <Keyboard className="size-4" />
                </IconButton>
                {showKeys && (
                  <div role="dialog" aria-label="Keyboard shortcuts" className="popover absolute right-0 bottom-9 z-30 w-[19rem] p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="card-title">Shortcuts</span>
                      <IconButton label="Close" className="size-6" onClick={() => setShowKeys(false)}>
                        <X className="size-3.5" />
                      </IconButton>
                    </div>
                    <dl className="m-0 grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-1.5 text-sm">
                      {SHORTCUTS.map(([keys, what]) => (
                        <div key={what} className="contents">
                          <dt className="flex gap-1">
                            {keys.map((k) => (
                              <Kbd key={k}>{k}</Kbd>
                            ))}
                          </dt>
                          <dd className="m-0 text-ink-soft">{what}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                )}
              </div>
            </div>
          </div>
          {lines && (
            <LyricTimeline
              lines={lines}
              sections={sections}
              lang={lang}
              duration={total}
              now={now}
              playing={playing}
              follow={follow}
              selected={selected}
              peaks={peaks}
              clips={clips}
              slots={slots}
              renderSrc={renders?.[0] ? outputUrl(renders[0].name, "video.mp4") : null}
              aspect={aspect}
              pps={pps}
              onZoom={setPps}
              onSeek={(t) => seek(t)}
              onSelect={setSelected}
              onMove={(uid, start) => {
                retime(uid, (l) => shift(l, start - lineStart(l)), "start");
                history.seal();
              }}
              onTrim={(uid, edge, t) => {
                if (edge === "end") endAt(uid, t);
                else editLine(uid, (l) => ({ ...respan(l, t, lineEnd(l)), check: false }));
                history.seal();
              }}
            />
          )}
        </div>

        {/* ---------- make music video sheet ---------- */}
        {making && (
          <>
            <div aria-hidden className="absolute inset-0 z-30 bg-ink/30" onClick={() => setMaking(false)} />
            <div role="dialog" aria-modal="true" aria-label="Make music video" className="absolute inset-y-0 right-0 z-40 flex w-[min(32rem,100%)] flex-col border-l border-line bg-panel shadow-(--shadow-pop)">
              <div className="pane-header">
                <div className="min-w-0">
                  <h2 className="pane-title m-0">Music video</h2>
                  <p className="m-0 text-xs text-ink-soft">
                    {aspect} · uses the timing you see here{save === "saving" ? " (saving…)" : ""}
                  </p>
                </div>
                <IconButton label="Close" onClick={() => setMaking(false)}>
                  <X className="size-5" />
                </IconButton>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto p-4">
                <MusicVideoOptions
                  name={name}
                  lang={lang}
                  aspect={aspect}
                  sample={lines?.find((l) => l.text.trim())?.text ?? title}
                  sections={sections}
                  value={settings}
                  onChange={setSettings}
                />
              </div>
              <div className="grid shrink-0 gap-2 border-t border-line px-4 py-3">
                <Message text={error} error />
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
          </>
        )}
      </div>
    </div>
  );
}
