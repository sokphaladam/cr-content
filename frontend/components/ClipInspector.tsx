"use client";

import { Copy, Play, Scissors, Square, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { API_BASE, api, type Clip, type GraphicStill, type Lang, type TemplateField, type TimelineCatalog } from "@/lib/api";
import { MIN_LEN } from "@/lib/clips";
import { fieldError, templateDefaults, templateErrors } from "@/lib/templates";
import { SecondsInput } from "./SceneCard";
import { Button, Field } from "./ui";

let catalog: Promise<TimelineCatalog> | null = null;
const catalogListeners = new Set<(c: TimelineCatalog) => void>();

/** Ask the engine again (after a sound is imported): every open useCatalog() gets the new one. */
export function refreshCatalog() {
  catalog = null;
  loadCatalog().then((c) => catalogListeners.forEach((l) => l(c)), () => {});
}

function loadCatalog() {
  catalog ??= api.timelineCatalog().catch((e) => {
    catalog = null; // try again next time
    throw e;
  });
  return catalog;
}

/** The sounds and graphic templates timeline clips can use (asked of the engine once per session). */
export function useCatalog(): TimelineCatalog | null {
  const [cat, setCat] = useState<TimelineCatalog | null>(null);
  useEffect(() => {
    let live = true;
    const update = (c: TimelineCatalog) => live && setCat(c);
    catalogListeners.add(update);
    loadCatalog().then(update, () => {});
    return () => {
      live = false;
      catalogListeners.delete(update);
    };
  }, []);
  return cat;
}

export const soundLength = (cat: TimelineCatalog | null, name: string) => cat?.sounds.find((s) => s.name === name)?.duration;

/** Plays a sound clip alone, as it will sound in the video (its trimmed part, gain and fades). */
function useAudition(clip: Clip) {
  const [on, setOn] = useState(false);
  const el = useRef<HTMLAudioElement | null>(null);
  const timer = useRef(0);
  const stop = () => {
    el.current?.pause();
    window.clearInterval(timer.current);
    setOn(false);
  };
  useEffect(() => stop, []);
  return {
    on,
    toggle() {
      if (on) return stop();
      const a = (el.current ??= new Audio());
      a.src = api.sfxUrl(clip.sound);
      a.currentTime = clip.source_in;
      const begun = performance.now();
      const level = () => {
        const t = (performance.now() - begun) / 1000;
        if (t >= clip.duration) return stop();
        const fade = Math.min(1, clip.fade_in ? t / clip.fade_in : 1, clip.fade_out ? (clip.duration - t) / clip.fade_out : 1);
        a.volume = Math.min(1, Math.max(0, clip.gain * 0.8 * fade));
      };
      level();
      a.play().then(() => setOn(true), () => setOn(false));
      timer.current = window.setInterval(level, 30);
    },
  };
}

const GROUPS = { content: "Content", style: "Style", position: "Position", motion: "Motion" } as const;

/** One template field, typed: text, number, colour or a choice, with its problem under it. */
function PropField({ f, value, onChange }: { f: TemplateField; value: string | number; onChange: (v: string | number) => void }) {
  const id = `prop-${f.key}`;
  const error = fieldError(f, value);
  return (
    <div className="grid min-w-0 gap-1">
      <label htmlFor={id} className="text-sm text-ink-soft">
        {f.label}
        {f.max_len ? <span className="ml-1 text-2xs">({String(value).length}/{f.max_len})</span> : null}
      </label>
      {f.type === "choice" ? (
        <select id={id} className="field-input h-8 py-0 text-sm" value={String(value)} onChange={(e) => onChange(e.target.value)} aria-invalid={!!error}>
          {f.options?.map((o) => (
            <option key={o} value={o}>{o.replace(/_/g, " ")}</option>
          ))}
        </select>
      ) : f.type === "color" ? (
        <div className="flex items-center gap-1.5">
          <input type="color" aria-label={`${f.label} picker`} value={/^#[0-9A-Fa-f]{6}$/.test(String(value)) ? String(value) : "#000000"}
            onChange={(e) => onChange(e.target.value.toUpperCase())} className="size-8 cursor-pointer rounded border border-line bg-panel p-0.5" />
          <input id={id} className="field-input h-8 py-0 font-mono text-sm" value={String(value)} onChange={(e) => onChange(e.target.value)} aria-invalid={!!error} />
        </div>
      ) : f.type === "number" ? (
        <input id={id} type="number" step={f.step ?? "any"} min={f.min} max={f.max} className="field-input h-8 py-0 text-sm"
          value={value} onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))} aria-invalid={!!error} />
      ) : (
        <input id={id} className="field-input h-8 py-0 text-sm" value={String(value)} onChange={(e) => onChange(e.target.value)} aria-invalid={!!error} />
      )}
      {error && <span role="alert" className="text-xs font-semibold text-danger">{error}</span>}
    </div>
  );
}

/** The properties of the selected graphic or sound clip on the timeline. Every change is one undoable edit. */
export function ClipInspector({
  clip,
  locked,
  onChange,
  onSplit,
  onDuplicate,
  onDelete,
}: {
  clip: Clip;
  locked: boolean; // its lane is locked: shown, not editable
  onChange: (patch: Partial<Clip>) => void;
  onSplit: () => void; // at the playhead
  onDuplicate: () => void;
  onDelete: () => void;
}) {
  const cat = useCatalog();
  const audition = useAudition(clip);
  const sound = clip.track === "sfx";
  const maxLen = sound ? soundLength(cat, clip.sound) : undefined;
  const info = sound ? cat?.sounds.find((s) => s.name === clip.sound) : undefined;
  const def = cat?.templates[clip.template];
  const errors = cat && !sound ? templateErrors(def, clip.props) : {};
  const setProp = (k: string, v: string | number) => onChange({ props: { ...clip.props, [k]: v } });
  return (
    <div className="grid gap-3 p-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="m-0 text-md font-bold">{sound ? "Sound effect" : "Graphic"} <span className="font-mono text-xs font-normal text-ink-soft">{clip.id}</span></h3>
        {locked && <span className="text-xs text-ink-soft">Lane locked</span>}
      </div>
      <fieldset disabled={locked} className="m-0 grid gap-3 border-0 p-0">
        {sound ? (
          <Field label="Sound" htmlFor="clip-sound">
            <div className="flex gap-1.5">
              <select
                id="clip-sound"
                className="field-input h-9 py-0 text-base"
                value={clip.sound}
                onChange={(e) => {
                  const len = soundLength(cat, e.target.value);
                  onChange({ sound: e.target.value, source_in: 0, ...(len && { duration: Math.min(clip.duration, len) }) });
                }}
              >
                {!info && <option value={clip.sound}>{clip.sound ? `${clip.sound} (missing)` : "Pick a sound"}</option>}
                {cat?.categories.map((group) => (
                  <optgroup key={group} label={group}>
                    {cat.sounds
                      .filter((s) => s.category === group)
                      .map((s) => (
                        <option key={s.name} value={s.name}>
                          {s.label} ({s.duration.toFixed(1)} s)
                        </option>
                      ))}
                  </optgroup>
                ))}
              </select>
              <Button size="sm" variant="secondary" disabled={!clip.sound} icon={audition.on ? <Square className="size-3.5" /> : <Play className="size-3.5" />} onClick={audition.toggle}>
                {audition.on ? "Stop" : "Audition"}
              </Button>
            </div>
            {info ? (
              <span className="text-xs text-ink-soft">
                {info.description && `${info.description} `}
                <span className="font-semibold">{info.licence}</span>
                {info.credit && ` · credit: ${info.credit} (added to the description)`}
              </span>
            ) : (
              clip.sound && <span role="alert" className="text-xs font-semibold text-danger">This sound isn&apos;t in the library any more: the render leaves it out.</span>
            )}
          </Field>
        ) : (
          <Field label="Template" htmlFor="clip-template">
            <select
              id="clip-template"
              className="field-input h-9 py-0 text-base"
              value={clip.template}
              onChange={(e) => {
                const next = cat?.templates[e.target.value];
                onChange({ template: e.target.value, template_version: next?.version ?? 0, props: templateDefaults(next) });
              }}
            >
              {!def && <option value={clip.template}>{clip.template || "Pick a template"}</option>}
              {Object.entries(cat?.templates ?? {}).map(([t, d]) => (
                <option key={t} value={t}>{d.label}</option>
              ))}
            </select>
            {def && <span className="text-xs text-ink-soft">{def.description}</span>}
            {errors.template && <span role="alert" className="text-xs font-semibold text-danger">{errors.template}</span>}
          </Field>
        )}

        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <SecondsInput label="Starts at" value={clip.start} onChange={(v) => onChange({ start: v })} />
          <SecondsInput
            label="Length"
            value={clip.duration}
            min={MIN_LEN}
            onChange={(v) => onChange({ duration: maxLen ? Math.min(v, Math.max(maxLen - clip.source_in, MIN_LEN)) : v })}
          />
          {sound && (
            <SecondsInput
              label="From"
              value={clip.source_in}
              onChange={(v) => onChange({ source_in: maxLen ? Math.min(v, Math.max(maxLen - MIN_LEN, 0)) : v })}
            />
          )}
        </div>

        {sound ? (
          <>
            <label className="grid gap-1 text-sm text-ink-soft">
              <span>Gain {Math.round(clip.gain * 100)}%</span>
              <input type="range" min={0} max={2} step={0.05} value={clip.gain} onChange={(e) => onChange({ gain: Number(e.target.value) })} className="accent-cobalt" />
            </label>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
              <SecondsInput label="Fade in" value={clip.fade_in} onChange={(v) => onChange({ fade_in: Math.min(v, clip.duration / 2) })} />
              <SecondsInput label="Fade out" value={clip.fade_out} onChange={(v) => onChange({ fade_out: Math.min(v, clip.duration / 2) })} />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="size-4 accent-cobalt" checked={!!clip.duck} onChange={(e) => onChange({ duck: e.target.checked })} />
              Dip the music while it plays
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="size-4 accent-cobalt" checked={clip.essential !== false} onChange={(e) => onChange({ essential: e.target.checked })} />
              Essential to the story <span className="text-xs text-ink-soft">(off: a nice-to-have you can drop)</span>
            </label>
            {clip.note && <p className="m-0 text-xs text-ink-soft">Why: {clip.note}</p>}
          </>
        ) : (
          <>
            {Object.keys(errors).length > 0 && (
              <p role="alert" className="m-0 rounded-md border border-danger/50 bg-danger/[0.06] p-2 text-sm text-danger">
                This graphic can&apos;t render until the fields marked below are fixed; the render would leave it out.
              </p>
            )}
            {(["content", "style", "position", "motion"] as const).map((group) => {
              const fields = def?.fields.filter((f) => f.group === group) ?? [];
              if (!fields.length) return null;
              return (
                <fieldset key={group} className="m-0 grid gap-2 border-0 border-t border-line p-0 pt-2">
                  <legend className="mb-1 text-xs font-semibold tracking-wide text-ink-soft uppercase">{GROUPS[group]}</legend>
                  <div className={group === "position" ? "grid grid-cols-2 gap-2" : "grid gap-2"}>
                    {fields.map((f) => (
                      <PropField key={f.key} f={f} value={clip.props[f.key] ?? f.default} onChange={(v) => setProp(f.key, v)} />
                    ))}
                  </div>
                </fieldset>
              );
            })}
            <label className="flex items-center gap-2 text-sm text-ink-soft">
              Layer
              <input type="number" step={1} value={clip.layer} onChange={(e) => onChange({ layer: Math.round(Number(e.target.value) || 0) })} className="field-input h-7 w-16 px-1.5 py-0 text-sm" />
              <span className="text-xs">higher draws on top</span>
            </label>
            <p className="m-0 text-xs text-ink-soft">
              The preview shows a still frame of it, drawn by Remotion (the same drawing the render uses); the motion
              itself plays in the rendered video.
            </p>
          </>
        )}

        <div className="flex flex-wrap gap-1.5">
          <Button size="sm" variant="ghost" icon={<Scissors className="size-3.5" />} onClick={onSplit} title="Split at the playhead (S)">Split</Button>
          <Button size="sm" variant="ghost" icon={<Copy className="size-3.5" />} onClick={onDuplicate} title="Duplicate (Ctrl+D)">Duplicate</Button>
          <Button size="sm" variant="danger" icon={<Trash2 className="size-3.5" />} onClick={onDelete} title="Delete (Delete key)">Delete</Button>
        </div>
      </fieldset>
    </div>
  );
}

/** The graphics templates with a preview frame of each (their default look) and what they're for: pick one to add it
 *  at the playhead. */
export function GraphicsBin({ lang, onAdd }: { lang: Lang; onAdd: (template: string) => void }) {
  const cat = useCatalog();
  const [thumbs, setThumbs] = useState<Record<string, GraphicStill>>({});
  useEffect(() => {
    if (!cat) return;
    let live = true;
    const names = Object.keys(cat.templates);
    api
      .graphicStills(names.map((t) => ({ template: t, props: templateDefaults(cat.templates[t]), seconds: cat.templates[t].seconds, version: cat.templates[t].version })), lang)
      .then(({ items }) => live && setThumbs(Object.fromEntries(names.map((t, k) => [t, items[k]]))))
      .catch((e) => live && setThumbs(Object.fromEntries(names.map((t) => [t, { failed: (e as Error).message }]))));
    return () => {
      live = false;
    };
  }, [cat, lang]);
  if (!cat) return <p className="m-0 p-3 text-sm text-ink-soft">Loading the graphics…</p>;
  return (
    <ul aria-label="Graphics templates" className="m-0 grid list-none grid-cols-2 gap-2 p-2">
      {Object.entries(cat.templates).map(([t, d]) => {
        const thumb = thumbs[t];
        return (
          <li key={t}>
            <button
              type="button"
              onClick={() => onAdd(t)}
              title={`Add a ${d.label.toLowerCase()} at the playhead`}
              className="grid w-full cursor-pointer gap-1 rounded-lg border border-line bg-transparent p-1.5 text-left hover:border-cobalt/60 hover:bg-cobalt/[0.06]"
            >
              <span className="relative grid aspect-[9/16] w-full place-items-center overflow-hidden rounded bg-[linear-gradient(160deg,#3b4658,#1d2430)]">
                {thumb && "url" in thumb ? (
                  // eslint-disable-next-line @next/next/no-img-element -- the engine's cached PNG
                  <img src={`${API_BASE}${thumb.url}`} alt="" className="absolute inset-0 h-full w-full" />
                ) : (
                  <span className="px-1 text-center text-2xs text-white/70">{!thumb ? "Drawing…" : "failed" in thumb ? `No preview: ${thumb.failed}` : "No preview"}</span>
                )}
              </span>
              <span className="text-sm font-semibold text-ink">{d.label}</span>
              <span className="line-clamp-3 text-2xs leading-snug text-ink-soft">{d.description}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
