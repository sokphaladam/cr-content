"use client";

import { ChevronDown, Clapperboard, Info } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, type CutPace, type DirectedSection, type SongDirection, type Tape, type TapeFrame } from "@/lib/api";
import { Button, Message, Segmented } from "./ui";

const PACE_OPTIONS: { value: CutPace; label: string }[] = [
  { value: "slow", label: "Slow" },
  { value: "normal", label: "Normal" },
  { value: "fast", label: "Fast" },
];

const TAPE_OPTIONS: { value: Tape; label: string }[] = [
  { value: "", label: "Clean picture" },
  { value: "play", label: "VHS playback" },
  { value: "rewind", label: "Rewinding" },
  { value: "static_in", label: "Static clearing" },
  { value: "static", label: "TV static" },
];

const FRAME_OPTIONS: { value: TapeFrame; label: string }[] = [
  { value: "full", label: "Full" },
  { value: "4:3", label: "4:3 home video" },
];

/** How a section looks as an old tape: VHS playback or a rewind, worn more each replay, in a home-video frame. */
function TapeControls({ id, row, onChange }: { id: string; row: DirectedSection; onChange: (patch: Partial<DirectedSection>) => void }) {
  const tape = row.tape ?? "";
  const playing = tape === "play" || tape === "rewind";
  const wear = row.wear ?? 0;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm">
      <label className="flex items-center gap-1.5">
        <span className="text-ink-soft">Tape</span>
        <select
          className="field-input h-8 py-0 text-sm"
          value={tape}
          onChange={(e) => onChange({ tape: e.target.value as Tape })}
        >
          {TAPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <Segmented name={`${id}-frame`} size="sm" value={row.frame ?? "full"} options={FRAME_OPTIONS} onChange={(frame) => onChange({ frame })} />
      {playing && (
        <>
          <label className="flex items-center gap-1.5" title="How worn the tape looks: more noise, faded colour and skipped frames">
            <span className="text-ink-soft">Wear</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={wear}
              onChange={(e) => onChange({ wear: Number(e.target.value) })}
              className="w-24 accent-cobalt"
            />
            <span className="w-8 tabular-nums text-ink-soft">{Math.round(wear * 100)}%</span>
          </label>
          <input
            aria-label="Date stamp"
            placeholder="Date stamp, e.g. MAY 31 1998"
            maxLength={40}
            value={row.stamp ?? ""}
            onChange={(e) => onChange({ stamp: e.target.value.toUpperCase() })}
            className="field-input h-8 w-48 py-0 text-sm"
          />
        </>
      )}
      <label className="flex items-center gap-1.5" title="The person nearest the camera loses colour and turns to a ghost (more with wear)">
        <input type="checkbox" checked={!!row.fade} onChange={(e) => onChange({ fade: e.target.checked })} className="accent-cobalt" />
        <span>Fade the person</span>
      </label>
    </div>
  );
}

/**
 * Your idea as a shot list: Claude reads the concept and writes what each section of the song shows and how fast it
 * cuts (one Claude call), plus the characters every picture shares. Everything is editable; the pictures, the cuts
 * and the footage then follow it.
 */
export function ShotList({
  name,
  sections,
  idea,
  direction,
  onChange,
  onDirected,
}: {
  name: string; // the song's folder
  sections: string[]; // section names, in song order
  idea: string;
  direction: SongDirection | null | undefined;
  onChange: (d: SongDirection | null) => void;
  onDirected: (d: SongDirection) => void; // a new shot list: apply its look and lyric style
}) {
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(true);
  const [message, setMessage] = useState<{ text: string; error?: boolean }>({ text: "" });
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => void (saveTimer.current && clearTimeout(saveTimer.current)), []);

  const current = !!direction && direction.idea === idea.trim() && direction.sections.length === sections.length;

  async function direct() {
    setBusy(true);
    setMessage({ text: "Claude is turning your idea into a shot list… about 30 seconds." });
    try {
      const d = await api.directIdea(name, idea);
      onChange(d);
      onDirected(d);
      setOpen(true);
      setMessage({ text: "" });
    } catch (e) {
      setMessage({ text: (e as Error).message, error: true });
    } finally {
      setBusy(false);
    }
  }

  function edit(next: SongDirection) {
    onChange(next);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      api.saveDirection(name, next).catch((e) => setMessage({ text: (e as Error).message, error: true }));
    }, 700);
  }

  const setRow = (i: number, patch: Partial<SongDirection["sections"][number]>) =>
    direction && edit({ ...direction, sections: direction.sections.map((r, k) => (k === i ? { ...r, ...patch } : r)) });

  const ready = idea.trim().length >= 20;
  return (
    <div className="grid gap-1.5">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant={current ? "ghost" : "secondary"}
          icon={<Clapperboard className="size-3.5" />}
          loading={busy}
          disabled={!ready}
          title="Claude turns your idea into a scene and cutting pace for every part of the song (one Claude call)"
          onClick={direct}
        >
          {current ? "Direct again" : "Direct my idea"}
        </Button>
        {current && (
          <button
            type="button"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
            className="flex cursor-pointer items-center gap-1 border-0 bg-transparent p-0 text-sm font-semibold text-cobalt"
          >
            <ChevronDown className={`size-3.5 transition-transform ${open ? "rotate-180" : ""}`} /> Shot list · {sections.length} parts
          </button>
        )}
      </div>
      {!current && (
        <p className="m-0 text-sm text-ink-soft">
          {direction && direction.idea !== idea.trim()
            ? "You changed the idea since the shot list was made, so it isn't used. Direct again to update it."
            : "Write what each part of the song shows (Intro, Verses, Chorus…), then Direct my idea: every part gets its scene and cutting speed, and the pictures follow it."}
        </p>
      )}
      <Message text={message.text} error={message.error} />

      {current && open && direction && (
        <div className="grid gap-2 rounded-lg border border-line p-2.5">
          {direction.notes.length > 0 && (
            <ul className="m-0 grid list-none gap-1 rounded-md bg-cobalt/[0.06] p-2 text-sm leading-snug text-ink">
              {direction.notes.map((n, i) => (
                <li key={i} className="flex gap-1.5">
                  <Info className="mt-0.5 size-3.5 shrink-0 text-cobalt" aria-hidden />
                  {n}
                </li>
              ))}
            </ul>
          )}
          <ol className="m-0 grid list-none gap-2 p-0">
            {direction.sections.map((row, i) => (
              <li key={i} className="grid gap-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-semibold">{sections[i]}</span>
                  <Segmented name={`${name}-pace-${i}`} size="sm" value={row.pace} options={PACE_OPTIONS} onChange={(pace) => setRow(i, { pace })} />
                </div>
                <textarea
                  aria-label={`${sections[i]}: what it shows`}
                  rows={2}
                  value={row.scene}
                  onChange={(e) => setRow(i, { scene: e.target.value })}
                  className="field-input field-sizing-content min-h-[44px] resize-none text-sm leading-snug"
                />
                <TapeControls id={`${name}-tape-${i}`} row={row} onChange={(patch) => setRow(i, patch)} />
              </li>
            ))}
          </ol>
          <label className="grid gap-1">
            <span className="field-label">Characters and world</span>
            <textarea
              rows={2}
              value={direction.bible}
              onChange={(e) => edit({ ...direction, bible: e.target.value })}
              className="field-input field-sizing-content min-h-[52px] resize-none text-sm leading-snug"
            />
            <span className="text-xs text-ink-soft">Every picture shows these same people, car and places. Pace: how fast that part cuts on the beat. Tape: play a part as an old VHS tape (AI pictures only).</span>
          </label>
        </div>
      )}
    </div>
  );
}
