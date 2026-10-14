"use client";

import { ChevronLeft, Music, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import type { Lang, Options, SongScript, SongSection } from "@/lib/api";
import { Button, Field, IconButton, Message } from "./ui";

/** Comma-separated tags, edited as free text so typing isn't reformatted under the cursor. */
function TagsInput({ id, value, onChange, placeholder }: { id: string; value: string[]; onChange: (v: string[]) => void; placeholder?: string }) {
  const [text, setText] = useState(value.join(", "));
  const parse = (t: string) => t.split(",").map((x) => x.trim()).filter(Boolean);
  // Resync when the value changes from outside (e.g. a section above was removed).
  if (parse(text).join("\n") !== value.join("\n")) setText(value.join(", "));
  return (
    <input
      id={id}
      className="field-input"
      value={text}
      placeholder={placeholder}
      onChange={(e) => {
        setText(e.target.value);
        onChange(parse(e.target.value));
      }}
    />
  );
}

function SectionCard({
  index,
  section,
  lang,
  onChange,
  onRemove,
}: {
  index: number;
  section: SongSection;
  lang: Lang;
  onChange: (s: SongSection) => void;
  onRemove: (() => void) | null;
}) {
  const id = `section-${index}`;
  return (
    <li className="grid gap-4 card p-4 sm:p-5">
      <div className="grid items-end gap-4 sm:grid-cols-[minmax(0,1fr)_110px_auto]">
        <Field label="Section" htmlFor={`${id}-name`}>
          <input id={`${id}-name`} className="field-input font-semibold" value={section.name} onChange={(e) => onChange({ ...section, name: e.target.value })} />
        </Field>
        <Field label="Seconds" htmlFor={`${id}-sec`}>
          <input
            id={`${id}-sec`}
            type="number"
            min={3}
            max={120}
            className="field-input"
            value={section.seconds}
            onChange={(e) => onChange({ ...section, seconds: Math.max(3, Math.min(120, Math.round(+e.target.value || 3))) })}
          />
        </Field>
        {onRemove && (
          <IconButton label="Remove section" tone="danger" onClick={onRemove} className="mb-1">
            <Trash2 className="size-4" />
          </IconButton>
        )}
      </div>
      <Field label="Lyrics" hint="one sung line per row; empty = instrumental" htmlFor={`${id}-lyrics`}>
        <textarea
          id={`${id}-lyrics`}
          lang={lang}
          rows={Math.max(3, section.lyrics.length + 1)}
          className="field-input resize-y py-2.5 leading-relaxed"
          value={section.lyrics.join("\n")}
          onChange={(e) => onChange({ ...section, lyrics: e.target.value.split("\n") })}
        />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Sound for this part" hint="comma separated" htmlFor={`${id}-styles`}>
          <TagsInput id={`${id}-styles`} value={section.styles} onChange={(styles) => onChange({ ...section, styles })} placeholder="stripped back, soft piano" />
        </Field>
        <Field label="Footage search" htmlFor={`${id}-visual`}>
          <input id={`${id}-visual`} className="field-input" value={section.visual_query} onChange={(e) => onChange({ ...section, visual_query: e.target.value })} />
        </Field>
      </div>
    </li>
  );
}

export function SongEditor({
  song,
  setSong,
  lang,
  options,
  composing,
  onBack,
  onDelete,
  onCompose,
}: {
  song: SongScript;
  setSong: (update: (s: SongScript) => SongScript) => void;
  lang: Lang;
  options: Options;
  composing: boolean;
  onBack: () => void;
  onDelete: (() => void) | null; // null until the song is composed (nothing saved to delete yet)
  onCompose: (stems: boolean) => Promise<string | null>;
}) {
  const [stems, setStems] = useState(true);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState("");
  const total = song.sections.reduce((n, s) => n + s.seconds, 0);
  const keyMissing = !options.keys.elevenlabs;
  const set = (patch: Partial<SongScript>) => setSong((s) => ({ ...s, ...patch }));
  const setSection = (i: number, section: SongSection) =>
    setSong((s) => ({ ...s, sections: s.sections.map((x, j) => (j === i ? section : x)) }));

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex h-14 shrink-0 items-center gap-2 border-b border-line bg-panel px-3 sm:px-5">
        <IconButton label="Back to start" onClick={onBack}>
          <ChevronLeft className="size-5" />
        </IconButton>
        <span className="min-w-0 flex-1 truncate text-md font-semibold" lang={lang}>
          {song.title || "Untitled song"}
        </span>
        <span className="text-base text-ink-soft">
          {song.sections.length} sections, {total} s
        </span>
        {onDelete && (
          <Button
            size="sm"
            variant="danger"
            aria-label={confirmDelete ? "Confirm delete song" : "Delete song"}
            title="Deletes the song. Its music videos stay in Videos."
            disabled={composing}
            icon={<Trash2 className="size-3.5" />}
            onClick={() => {
              if (!confirmDelete) {
                setConfirmDelete(true);
                setTimeout(() => setConfirmDelete(false), 3000);
                return;
              }
              onDelete();
            }}
          >
            <span className={confirmDelete ? "" : "hidden md:inline"}>{confirmDelete ? "Confirm delete" : "Delete"}</span>
          </Button>
        )}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto grid max-w-[760px] gap-5 px-4 py-6 sm:px-8">
          <section className="grid gap-4 card p-4 sm:p-5">
            <Field label="Title" htmlFor="song-title">
              <input id="song-title" lang={lang} className="field-input text-xl font-semibold" value={song.title} onChange={(e) => set({ title: e.target.value })} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-[1fr_1fr_100px]">
              <Field label="Genre" htmlFor="song-genre">
                <input id="song-genre" className="field-input" value={song.genre} onChange={(e) => set({ genre: e.target.value })} />
              </Field>
              <Field label="Mood" htmlFor="song-mood">
                <input id="song-mood" className="field-input" value={song.mood} onChange={(e) => set({ mood: e.target.value })} />
              </Field>
              <Field label="BPM" htmlFor="song-bpm">
                <input id="song-bpm" type="number" min={40} max={220} className="field-input" value={song.bpm} onChange={(e) => set({ bpm: Math.round(+e.target.value || 100) })} />
              </Field>
            </div>
            <Field label="Singer voice" htmlFor="song-vocal-edit">
              <input id="song-vocal-edit" className="field-input" value={song.vocal} onChange={(e) => set({ vocal: e.target.value })} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Overall sound" hint="comma separated" htmlFor="song-styles">
                <TagsInput id="song-styles" value={song.styles} onChange={(styles) => set({ styles })} />
              </Field>
              <Field label="Avoid" hint="comma separated" htmlFor="song-avoid">
                <TagsInput id="song-avoid" value={song.avoid} onChange={(avoid) => set({ avoid })} />
              </Field>
            </div>
          </section>

          <ol className="m-0 grid list-none gap-4 p-0">
            {song.sections.map((s, i) => (
              <SectionCard
                key={i}
                index={i}
                section={s}
                lang={lang}
                onChange={(x) => setSection(i, x)}
                onRemove={song.sections.length > 1 ? () => setSong((so) => ({ ...so, sections: so.sections.filter((_, j) => j !== i) })) : null}
              />
            ))}
          </ol>
          <Button
            variant="ghost"
            icon={<Plus className="size-4" />}
            className="justify-self-start"
            onClick={() =>
              setSong((s) => ({ ...s, sections: [...s.sections, { name: "Chorus", lyrics: [], styles: [], seconds: 10, visual_query: "" }] }))
            }
          >
            Add section
          </Button>

          <section className="grid gap-3 card p-4 sm:p-5">
            <label className="flex items-center gap-2 text-md">
              <input type="checkbox" checked={stems} onChange={(e) => setStems(e.target.checked)} className="size-4 accent-cobalt" />
              Also split vocals and instrumental (uses extra ElevenLabs credits)
            </label>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="primary"
                loading={composing}
                disabled={keyMissing}
                icon={<Music className="size-4" />}
                onClick={async () => {
                  setError("");
                  const err = await onCompose(stems);
                  if (err) setError(err);
                }}
              >
                {composing ? "Composing…" : "Compose song"}
              </Button>
              <span className="text-base text-ink-soft">Takes about 30 seconds to 2 minutes.</span>
            </div>
            <Message
              text={error || (keyMissing ? "ElevenLabs isn't connected. Add ELEVENLABS_API_KEY to .env and restart the engine." : "")}
              error={!!error || keyMissing}
            />
          </section>
        </div>
      </div>
    </div>
  );
}
