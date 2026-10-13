"use client";

import { ChevronDown, Clapperboard, Info } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, type CutPace, type SongDirection } from "@/lib/api";
import { Button, Message, Segmented } from "./ui";

const PACE_OPTIONS: { value: CutPace; label: string }[] = [
  { value: "slow", label: "Slow" },
  { value: "normal", label: "Normal" },
  { value: "fast", label: "Fast" },
];

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
            className="flex cursor-pointer items-center gap-1 border-0 bg-transparent p-0 text-[12.5px] font-semibold text-cobalt"
          >
            <ChevronDown className={`size-3.5 transition-transform ${open ? "rotate-180" : ""}`} /> Shot list · {sections.length} parts
          </button>
        )}
      </div>
      {!current && (
        <p className="m-0 text-xs text-ink-soft">
          {direction && direction.idea !== idea.trim()
            ? "You changed the idea since the shot list was made, so it isn't used. Direct again to update it."
            : "Write what each part of the song shows (Intro, Verses, Chorus…), then Direct my idea: every part gets its scene and cutting speed, and the pictures follow it."}
        </p>
      )}
      <Message text={message.text} error={message.error} />

      {current && open && direction && (
        <div className="grid gap-2 rounded-lg border border-line p-2.5">
          {direction.notes.length > 0 && (
            <ul className="m-0 grid list-none gap-1 rounded-md bg-cobalt/[0.06] p-2 text-[12px] leading-snug text-ink">
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
                  <span className="text-[12.5px] font-semibold">{sections[i]}</span>
                  <Segmented name={`${name}-pace-${i}`} size="sm" value={row.pace} options={PACE_OPTIONS} onChange={(pace) => setRow(i, { pace })} />
                </div>
                <textarea
                  aria-label={`${sections[i]}: what it shows`}
                  rows={2}
                  value={row.scene}
                  onChange={(e) => setRow(i, { scene: e.target.value })}
                  className="field-input field-sizing-content min-h-[44px] resize-none text-[12.5px] leading-snug"
                />
              </li>
            ))}
          </ol>
          <label className="grid gap-1">
            <span className="field-label">Characters and world</span>
            <textarea
              rows={2}
              value={direction.bible}
              onChange={(e) => edit({ ...direction, bible: e.target.value })}
              className="field-input field-sizing-content min-h-[52px] resize-none text-[12.5px] leading-snug"
            />
            <span className="text-[11.5px] text-ink-soft">Every picture shows these same people, car and places. Pace: how fast that part cuts on the beat.</span>
          </label>
        </div>
      )}
    </div>
  );
}
