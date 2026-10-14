"use client";

import { Highlighter, Pause, Play, RotateCcw, Scissors, Trash2 } from "lucide-react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { keyword, type SceneVoice } from "@/lib/api";
import type { DraftTimeline, Segment } from "@/lib/useDraftTimeline";
import type { DraftScene } from "./SceneCard";
import type { Draft } from "./Storyboard";
import { Button, Spinner, useToast } from "./ui";

const MIN_PAUSE = 0.3; // gaps at least this long show as a pause chip
const KEEP = 0.12; // a cut pause keeps this much silence so the words don't run together

type Selection = { uid: string; anchor: number; from: number; to: number };

const overlaps = (cuts: [number, number][], [a, b]: [number, number]) => cuts.some(([x, y]) => x < b && y > a);

export function clock(sec: number) {
  const m = Math.floor(sec / 60);
  return `${m}:${(sec - m * 60).toFixed(1).padStart(4, "0")}`;
}

/** Word j as written in the narration, with the punctuation after it (the voiceover's words have none). */
function written(narration: string, v: SceneVoice, j: number) {
  const at = v.words[j].at;
  if (!at) return v.words[j].text;
  const next = v.words.slice(j + 1).find((w) => w.at)?.at?.[0] ?? narration.length;
  return narration.slice(at[0], next).trim();
}

/** The gap after word j of a voiceover as a cut that leaves KEEP seconds of silence. */
function gapCut(v: SceneVoice, j: number): [number, number] {
  return [v.words[j].end + KEEP / 2, v.words[j + 1].start - KEEP / 2];
}

/**
 * The draft as one transcript: every spoken word with its timing, the pauses between them, and the player it shares
 * with the live preview. Click a word to play from it, select words to delete them (the narration is rewritten) or
 * mark them as keywords (green in the captions), click a pause to cut it. The render uses the same voiceover.
 */
export function Transcript({
  draft,
  setDraft,
  timeline,
  onActive,
}: {
  draft: Draft;
  setDraft: (update: (d: Draft) => Draft) => void;
  timeline: DraftTimeline;
  onActive: (uid: string) => void;
}) {
  const toast = useToast();
  const { segments, total, now, pos, playing, loading, error, toggle } = timeline;
  const [selection, setSelection] = useState<Selection | null>(null);
  const box = useRef<HTMLDivElement>(null);

  const activate = timeline.activate;
  useEffect(() => activate(), [activate]);

  // ---------- edits ----------
  const patchScene = (uid: string, patch: (s: DraftScene) => Partial<DraftScene>) =>
    setDraft((d) => ({ ...d, scenes: d.scenes.map((s) => (s.uid === uid ? { ...s, ...patch(s) } : s)) }));
  const selected = () => {
    const seg = selection && segments.find((s) => s.scene.uid === selection.uid);
    return seg?.voice ? { seg, words: seg.voice.words.slice(selection!.from, selection!.to + 1) } : null;
  };

  function deleteSelection() {
    const sel = selected();
    const first = sel?.words[0]?.at;
    const last = sel?.words.at(-1)?.at;
    if (!sel || !first || !last) return toast("Those words can't be found in the narration. Edit them in the scene instead.", "error");
    const text = sel.seg.scene.narration;
    // the deleted words take a comma after them along; a full stop stays, pulled up against the word before
    let end = last[1];
    while (end < text.length && /[,;:]/.test(text[end])) end += 1;
    while (end < text.length && /\s/.test(text[end])) end += 1;
    let after = text.slice(end);
    const before = !after || /^[.!?…।។៕,;:]/.test(after) ? text.slice(0, first[0]).replace(/[\s,;:]+$/, "") : text.slice(0, first[0]);
    if (!before.trim()) after = after.replace(/^[\s.!?…।។៕,;:]+/, ""); // the opening words went
    else if (/[.!?…।។៕]$/.test(before)) after = after.replace(/^[.!?…।។៕]+/, ""); // a whole sentence went: no ".."
    const narration = before + after;
    timeline.stop();
    patchScene(sel.seg.scene.uid, () => ({ narration, cuts: [], cuts_key: "" })); // the cuts belonged to the old voiceover
    setSelection(null);
    timeline.seek(sel.seg.index, 0);
    if (!narration.trim()) toast("That scene has no voiceover now, so it's skipped when rendering.");
  }

  function toggleKeywords() {
    const sel = selected();
    const keys = (sel?.words ?? []).map((w) => keyword(w.text)).filter(Boolean);
    if (!sel || !keys.length) return;
    patchScene(sel.seg.scene.uid, (s) => {
      const have = new Set(s.keywords ?? []);
      const all = keys.every((k) => have.has(k));
      keys.forEach((k) => (all ? have.delete(k) : have.add(k)));
      return { keywords: [...have] };
    });
  }

  function toggleCut(seg: Segment, j: number) {
    const gap = gapCut(seg.voice!, j);
    const on = overlaps(seg.cuts, gap);
    patchScene(seg.scene.uid, () => ({
      cuts: on ? seg.cuts.filter((c) => !overlaps([c], gap)) : [...seg.cuts, gap],
      cuts_key: seg.voice!.key,
    }));
  }

  /** Speech cleanup: cut every pause of MIN_PAUSE or longer down to KEEP. */
  function cleanup() {
    const cutsFor = new Map<string, { cuts: [number, number][]; key: string }>();
    let count = 0;
    for (const seg of segments) {
      const v = seg.voice;
      if (!v) continue;
      const cuts = [...seg.cuts];
      v.words.slice(0, -1).forEach((w, j) => {
        const gap = gapCut(v, j);
        if (v.words[j + 1].start - w.end >= MIN_PAUSE && !overlaps(cuts, gap)) {
          cuts.push(gap);
          count += 1;
        }
      });
      cutsFor.set(seg.scene.uid, { cuts, key: v.key });
    }
    setDraft((d) => ({
      ...d,
      scenes: d.scenes.map((s) => {
        const c = cutsFor.get(s.uid);
        return c ? { ...s, cuts: c.cuts, cuts_key: c.key } : s;
      }),
    }));
    toast(count ? `Cut ${count} pause${count === 1 ? "" : "s"}` : "No long pauses left", "success");
  }

  const anyCuts = segments.some((s) => s.cuts.length);
  const restore = () => setDraft((d) => ({ ...d, scenes: d.scenes.map((s) => ({ ...s, cuts: [], cuts_key: "" })) }));

  function select(seg: Segment, j: number, extend: boolean) {
    setSelection(
      extend && selection?.uid === seg.scene.uid
        ? { ...selection, from: Math.min(selection.anchor, j), to: Math.max(selection.anchor, j) }
        : { uid: seg.scene.uid, anchor: j, from: j, to: j },
    );
    timeline.seek(seg.index, seg.voice!.words[j].start);
  }

  function onKey(e: KeyboardEvent<HTMLDivElement>) {
    if (e.target !== e.currentTarget) return; // a focused pause chip handles its own keys
    const sel = selected();
    if (e.key === " ") {
      e.preventDefault();
      toggle();
    } else if ((e.key === "Delete" || e.key === "Backspace") && sel) {
      e.preventDefault();
      deleteSelection();
    } else if (e.key.toLowerCase() === "h" && sel) {
      e.preventDefault();
      toggleKeywords();
    } else if (e.key === "Escape") {
      setSelection(null);
    } else if ((e.key === "ArrowLeft" || e.key === "ArrowRight") && sel && selection) {
      e.preventDefault();
      const step = e.key === "ArrowLeft" ? -1 : 1;
      // shift moves the end away from the anchor; a plain arrow steps off the selection's own edge
      const moving = selection.anchor === selection.from ? selection.to : selection.from;
      const from = e.shiftKey ? moving : step < 0 ? selection.from : selection.to;
      select(sel.seg, Math.min(Math.max(from + step, 0), sel.seg.voice!.words.length - 1), e.shiftKey);
    }
  }

  const voiced = segments.some((s) => s.voice);
  const selectedCount = selection ? selection.to - selection.from + 1 : 0;

  return (
    <div className="grid gap-3">
      <div className="sticky top-0 z-10 flex flex-wrap items-center gap-2 card px-2 py-2">
        <Button
          size="sm"
          variant="primary"
          aria-label={playing ? "Pause" : "Play"}
          icon={playing ? <Pause className="size-3.5 fill-current" /> : <Play className="size-3.5 fill-current" />}
          disabled={!voiced}
          onClick={toggle}
        />
        <span className="min-w-[96px] font-mono text-sm text-ink-soft tabular-nums">
          {clock(now)} / {clock(total)}
        </span>
        {loading && (
          <span role="status" className="flex items-center gap-1.5 text-sm text-ink-soft">
            <Spinner className="size-3.5" /> Making voiceover…
          </span>
        )}
        <div className="ml-auto flex flex-wrap items-center gap-1">
          {selection ? (
            <>
              <span className="px-1 text-sm text-ink-soft">
                {selectedCount} word{selectedCount === 1 ? "" : "s"}
              </span>
              <Button size="sm" variant="ghost" icon={<Highlighter className="size-3.5" />} title="Keyword colour in the captions (H)" onClick={toggleKeywords}>
                Highlight
              </Button>
              <Button size="sm" variant="ghost" icon={<Trash2 className="size-3.5" />} title="Delete from the voiceover (Delete)" onClick={deleteSelection}>
                Delete
              </Button>
            </>
          ) : (
            <>
              {anyCuts && (
                <Button size="sm" variant="ghost" icon={<RotateCcw className="size-3.5" />} onClick={restore}>
                  Restore pauses
                </Button>
              )}
              <Button size="sm" variant="secondary" icon={<Scissors className="size-3.5" />} disabled={!voiced} onClick={cleanup}>
                Speech cleanup
              </Button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div role="alert" className="flex flex-wrap items-center gap-2 rounded-lg border border-danger/30 bg-danger/[0.06] px-3 py-2 text-base text-danger">
          {error}
          <Button size="sm" variant="ghost" onClick={timeline.retry}>
            Try again
          </Button>
        </div>
      )}

      <div
        ref={box}
        tabIndex={0}
        role="group"
        aria-label="Transcript. Space plays, click a word to play from it, shift-click to select more, H highlights, Delete removes."
        onKeyDown={onKey}
        lang={draft.lang}
        className="grid gap-5 card px-4 py-4 text-lg leading-[2.1] focus-visible:outline-2 focus-visible:outline-cobalt sm:px-6"
      >
        {segments.map((seg) => {
          const s = seg.scene;
          const v = seg.voice;
          const keys = new Set(s.keywords ?? []);
          const atPlayhead = pos.i === seg.index && (playing || pos.t > 0);
          return (
            <section key={s.uid} aria-label={`Scene ${seg.index + 1}`}>
              <h3 className="m-0 mb-0.5 flex items-center gap-2 text-xs leading-5 font-semibold tracking-wide text-ink-soft uppercase">
                <button type="button" className="cursor-pointer bg-transparent p-0 uppercase hover:text-ink" onClick={() => onActive(s.uid)}>
                  Scene {seg.index + 1}
                </button>
                {seg.length > 0 && <span className="font-normal tabular-nums">{clock(seg.start)}</span>}
              </h3>
              {!s.narration.trim() ? (
                <p className="m-0 text-base text-ink-soft">{s.seconds ? `Silent beat, ${s.seconds.toFixed(1)}s` : "No voiceover (skipped when rendering)"}</p>
              ) : !v ? (
                <p className="m-0 text-ink-soft/70">{s.narration}</p>
              ) : (
                <p className="m-0">
                  {v.words.map((w, j) => {
                    const next = v.words[j + 1];
                    const gap = next ? next.start - w.end : 0;
                    const cut = !!next && overlaps(seg.cuts, gapCut(v, j));
                    const spoken = atPlayhead && pos.t >= w.start && pos.t < (next ? next.start : w.end + 0.2);
                    const picked = selection?.uid === s.uid && j >= selection.from && j <= selection.to;
                    return (
                      <span key={j}>
                        <span
                          onMouseDown={(e) => {
                            // keep the keyboard shortcuts working without the browser scrolling the box into view
                            e.preventDefault();
                            box.current?.focus({ preventScroll: true });
                          }}
                          onClick={(e) => {
                            select(seg, j, e.shiftKey);
                            onActive(s.uid);
                          }}
                          className={`cursor-pointer rounded px-[3px] py-0.5 transition-colors ${
                            spoken ? "bg-caption text-media" : picked ? "bg-cobalt/15 ring-1 ring-cobalt/40" : "hover:bg-ink/[0.06]"
                          } ${keys.has(keyword(w.text)) ? "font-semibold text-ok" : ""}`}
                        >
                          {written(s.narration, v, j)}
                        </span>{" "}
                        {next && gap >= MIN_PAUSE && (
                          <>
                            <button
                              type="button"
                              title={cut ? "Pause cut. Click to restore it." : "Click to cut this pause"}
                              aria-pressed={cut}
                              onClick={() => toggleCut(seg, j)}
                              className={`mx-0.5 inline-flex h-5 cursor-pointer items-center rounded px-1.5 align-middle font-mono text-xs leading-none tabular-nums ${
                                cut ? "bg-ink/[0.04] text-ink-soft/60 line-through" : "bg-ink/[0.08] text-ink-soft hover:bg-ink/[0.14]"
                              }`}
                            >
                              {gap.toFixed(2)}s
                            </button>{" "}
                          </>
                        )}
                      </span>
                    );
                  })}
                </p>
              )}
            </section>
          );
        })}
      </div>
      <p className="m-0 text-sm leading-snug text-ink-soft">
        Click a word to play from it; shift-click to select several. <b>H</b> marks them as keywords (green in the captions), <b>Delete</b> removes them
        from the voiceover. Click a pause to cut it. The render uses this exact voiceover.
      </p>
    </div>
  );
}
