"use client";

import { Play, Plus, Sparkles, Square, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, type Clip, type SoundSuggestion, type VideoScript } from "@/lib/api";
import { refreshCatalog, useCatalog } from "./ClipInspector";
import { clock } from "./Transcript";
import { Button, Field, useToast } from "./ui";

/** Plays one library sound, start to end (one at a time). */
function usePlayer() {
  const el = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState("");
  useEffect(() => () => el.current?.pause(), []);
  return {
    playing,
    toggle(name: string) {
      const a = (el.current ??= new Audio());
      if (playing === name) {
        a.pause();
        return setPlaying("");
      }
      a.src = api.sfxUrl(name);
      a.onended = () => setPlaying("");
      a.play().then(() => setPlaying(name), () => setPlaying(""));
    },
  };
}

/** The Audio tab's sound design (M6): how far the music dips under the voice, suggested sounds tied to the story,
 *  the sound library to audition and add, and importing a licensed sound. Everything added is an ordinary,
 *  undoable timeline clip. */
export function SoundPanel({
  script,
  lengths,
  draftId,
  musicDuck,
  onMusicDuck,
  onAdd,
}: {
  script: VideoScript;
  lengths: number[];
  draftId: string;
  musicDuck: number;
  onMusicDuck: (v: number) => void;
  onAdd: (clips: Partial<Clip>[]) => void; // at their own start, or the playhead when they have none
}) {
  const cat = useCatalog();
  const toast = useToast();
  const player = usePlayer();
  const [busy, setBusy] = useState(false);
  const [ai, setAi] = useState(true);
  const [found, setFound] = useState<{ source: string; note: string; events: SoundSuggestion[] } | null>(null);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const label = (name: string) => cat?.sounds.find((s) => s.name === name)?.label ?? name;

  async function suggest() {
    setBusy(true);
    try {
      const r = await api.suggestSounds({ script, lengths, draft: draftId, ai });
      setFound(r);
      setPicked(new Set(r.events.flatMap((e, k) => (e.essential ? [k] : []))));
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4">
      <label className="grid gap-1 text-sm">
        <span className="field-label">Music under the voice: dips {Math.round(musicDuck * 100)}%</span>
        <input type="range" min={0} max={1} step={0.05} value={musicDuck} onChange={(e) => onMusicDuck(Number(e.target.value))} className="accent-cobalt" />
        <span className="text-xs text-ink-soft">How far the music ducks while the voice speaks (and under sounds set to dip it). 0 = it never dips.</span>
      </label>

      <section aria-label="Suggested sounds" className="grid gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="secondary" loading={busy} icon={<Sparkles className="size-3.5" />} onClick={() => void suggest()}>
            Suggest sounds
          </Button>
          <label className="flex items-center gap-1.5 text-xs text-ink-soft">
            <input type="checkbox" className="size-3.5 accent-cobalt" checked={ai} onChange={(e) => setAi(e.target.checked)} />
            Ask Gemini (sends the script text and story beats)
          </label>
        </div>
        {found && (
          <div className="grid gap-1.5 rounded-lg border border-line p-2">
            <p className="m-0 text-xs text-ink-soft">{found.note}</p>
            {found.events.length === 0 ? (
              <p className="m-0 text-sm text-ink-soft">No sound needed: nothing here stands out enough to emphasise.</p>
            ) : (
              <>
                <ul className="m-0 grid list-none gap-1 p-0">
                  {found.events.map((e, k) => (
                    <li key={k}>
                      <label className="flex cursor-pointer items-start gap-2 text-sm">
                        <input
                          type="checkbox"
                          className="mt-0.5 size-4 accent-cobalt"
                          checked={picked.has(k)}
                          onChange={() => setPicked((p) => (p.has(k) ? new Set([...p].filter((x) => x !== k)) : new Set([...p, k])))}
                        />
                        <span className="grid gap-0.5">
                          <span>
                            <span className="font-mono text-xs text-ink-soft">{clock(e.start)}</span> <b>{label(e.sound)}</b>
                            <span className="ml-1 text-xs text-ink-soft">{e.essential ? "essential" : "optional"}{e.duck ? " · dips the music" : ""}</span>
                          </span>
                          <span className="text-xs text-ink-soft">{e.reason}</span>
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
                <Button
                  size="sm"
                  variant="primary"
                  disabled={!picked.size}
                  onClick={() => {
                    onAdd(found.events.filter((_, k) => picked.has(k)).map((e) => ({
                      start: e.start, sound: e.sound, duration: e.duration, gain: e.gain, fade_in: e.fade_in, fade_out: e.fade_out,
                      duck: e.duck, essential: e.essential, note: e.reason,
                    })));
                    setFound(null);
                  }}
                >
                  Add {picked.size} sound{picked.size === 1 ? "" : "s"}
                </Button>
              </>
            )}
          </div>
        )}
      </section>

      <section aria-label="Sound library" className="grid gap-2">
        <h3 className="m-0 field-label">Sound library</h3>
        {!cat ? (
          <p className="m-0 text-sm text-ink-soft">Loading…</p>
        ) : (
          cat.categories.map((group) => {
            const sounds = cat.sounds.filter((s) => s.category === group);
            if (!sounds.length) return null;
            return (
              <div key={group} className="grid gap-1">
                <span className="text-xs font-semibold tracking-wide text-ink-soft uppercase">{group}</span>
                <ul className="m-0 grid list-none gap-1 p-0">
                  {sounds.map((s) => (
                    <li key={s.name} className="flex items-start gap-1.5 rounded-md p-1 hover:bg-ink/[0.04]">
                      <Button size="sm" variant="ghost" aria-label={`${player.playing === s.name ? "Stop" : "Play"} ${s.label}`} onClick={() => player.toggle(s.name)}
                        icon={player.playing === s.name ? <Square className="size-3.5" /> : <Play className="size-3.5" />} />
                      <span className="grid min-w-0 flex-1 gap-0.5">
                        <span className="truncate text-sm font-semibold">
                          {s.label} <span className="font-normal text-ink-soft">{s.duration.toFixed(1)} s</span>
                        </span>
                        <span className="text-2xs text-ink-soft">{s.description || s.licence}{s.credit && ` · ${s.credit}`}</span>
                      </span>
                      <Button size="sm" variant="ghost" aria-label={`Add ${s.label} at the playhead`} title="Add at the playhead" icon={<Plus className="size-3.5" />}
                        onClick={() => onAdd([{ sound: s.name, duration: Math.min(s.duration, s.ambient ? 5 : s.duration), fade_in: s.ambient ? 0.4 : 0, fade_out: s.ambient ? 1 : 0.1, gain: s.ambient ? 0.6 : 1 }])} />
                    </li>
                  ))}
                </ul>
              </div>
            );
          })
        )}
      </section>

      <ImportSound />
    </div>
  );
}

/** Add a sound file to the library, with the licence it comes under: a sound with no known licence isn't taken. */
function ImportSound() {
  const cat = useCatalog();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [form, setForm] = useState({ label: "", category: "action", licence: "", credit: "", source: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const needsCredit = !!cat?.needs_credit.includes(form.licence);
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));
  if (!open)
    return (
      <Button size="sm" variant="ghost" icon={<Upload className="size-3.5" />} onClick={() => setOpen(true)} className="justify-self-start">
        Import a sound…
      </Button>
    );
  return (
    <form
      className="grid gap-2 rounded-lg border border-line p-2"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!file) return setError("Pick a sound file.");
        setBusy(true);
        setError("");
        try {
          const made = await api.importSound(file, form);
          refreshCatalog();
          toast(`${made.label} is in the library.`, "success");
          setOpen(false);
          setFile(null);
          setForm({ label: "", category: "action", licence: "", credit: "", source: "" });
        } catch (err) {
          setError((err as Error).message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <h3 className="m-0 field-label">Import a sound</h3>
      <input type="file" accept=".wav,.mp3,.ogg,.flac,.m4a,audio/*" aria-label="Sound file" onChange={(e) => {
        const f = e.target.files?.[0] ?? null;
        setFile(f);
        if (f && !form.label) setForm((x) => ({ ...x, label: f.name.replace(/\.[^.]+$/, "").slice(0, 60) }));
      }} />
      <Field label="Name" htmlFor="sfx-label">
        <input id="sfx-label" className="field-input h-8 py-0 text-sm" maxLength={60} value={form.label} onChange={set("label")} required />
      </Field>
      <Field label="Category" htmlFor="sfx-category">
        <select id="sfx-category" className="field-input h-8 py-0 text-sm" value={form.category} onChange={set("category")}>
          {cat?.categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </Field>
      <Field label="Licence" htmlFor="sfx-licence" hint="required: a sound with no known licence can't be used">
        <select id="sfx-licence" className="field-input h-8 py-0 text-sm" value={form.licence} onChange={set("licence")} required>
          <option value="">Pick the licence it comes under</option>
          {cat?.licences.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
      </Field>
      <Field label="Credit" htmlFor="sfx-credit" hint={needsCredit ? "required by this licence: it goes into the description" : "optional"}>
        <input id="sfx-credit" className="field-input h-8 py-0 text-sm" maxLength={200} value={form.credit} onChange={set("credit")} required={needsCredit} placeholder="Who made it, as the source asks" />
      </Field>
      <Field label="Source" htmlFor="sfx-source" hint="optional">
        <input id="sfx-source" type="url" className="field-input h-8 py-0 text-sm" maxLength={300} value={form.source} onChange={set("source")} placeholder="https://…" />
      </Field>
      {error && <p role="alert" className="m-0 text-sm font-semibold text-danger">{error}</p>}
      <div className="flex gap-1.5">
        <Button size="sm" variant="primary" type="submit" loading={busy}>Import</Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
      </div>
    </form>
  );
}
