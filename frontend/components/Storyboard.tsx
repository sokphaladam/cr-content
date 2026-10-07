"use client";

import { Check, ChevronLeft, CircleAlert, Clapperboard, Languages, Pause, Play, Plus, Trash2 } from "lucide-react";
import { useCallback, useState } from "react";
import { api, type DraftData, type Lang, type Options, type VideoScript } from "@/lib/api";
import { useVoicePreview } from "@/lib/useVoicePreview";
import { SceneCard, type DraftScene } from "./SceneCard";
import { Button, Field, IconButton, Spinner, useToast } from "./ui";

export interface Draft {
  id: string | null; // folder name in drafts/, null until first saved
  title: string;
  scenes: DraftScene[];
  caption: string;
  hashtags: string; // edited as free text, split on render
  lang: Lang;
  topic: string;
  voice: string; // "" = language default
  rate: string;
  music: string;
}

export type SaveState = "idle" | "saving" | "saved" | "error";

let uidCounter = 0;
const uid = () => `s${++uidCounter}`;
const emptyScene = () => ({ narration: "", visual_query: "", on_screen_text: "", media: "", uid: uid() });

export function toDraft(
  script: VideoScript,
  lang: Lang,
  topic: string,
  extra: Partial<Pick<Draft, "id" | "voice" | "rate" | "music">> = {},
): Draft {
  const scenes = script.scenes.length ? script.scenes : [{ narration: "", visual_query: "", on_screen_text: "", media: "" }];
  return {
    id: extra.id ?? null,
    voice: extra.voice ?? "",
    rate: extra.rate ?? "+5%",
    music: extra.music ?? "",
    title: script.title,
    scenes: scenes.map((s) => ({ ...s, media: s.media ?? "", uid: uid() })),
    caption: script.caption,
    hashtags: script.hashtags.map((h) => `#${h}`).join(" "),
    lang,
    topic,
  };
}

/** What gets written to drafts/<id>/draft.json: everything, including unfinished scenes. */
export function toDraftData(d: Draft): DraftData {
  return {
    script: {
      title: d.title,
      scenes: d.scenes.map(({ narration, visual_query, on_screen_text, media }) => ({ narration, visual_query, on_screen_text, media })),
      caption: d.caption,
      hashtags: d.hashtags.split(/[\s,]+/).map((h) => h.replace(/^#/, "")).filter(Boolean),
    },
    lang: d.lang,
    topic: d.topic,
    voice: d.voice,
    rate: d.rate,
    music: d.music,
  };
}

/** What gets rendered: only scenes with narration, trimmed. */
function toScript(d: Draft): VideoScript {
  return {
    title: d.title.trim() || "Untitled video",
    scenes: d.scenes
      .filter((s) => s.narration.trim())
      .map((s) => ({
        narration: s.narration.trim(),
        visual_query: s.visual_query.trim() || "abstract background",
        on_screen_text: s.on_screen_text.trim(),
        media: s.media,
      })),
    caption: d.caption.trim(),
    hashtags: d.hashtags.split(/[\s,]+/).map((h) => h.replace(/^#/, "")).filter(Boolean),
  };
}

const SAMPLE: Record<Lang, string> = {
  en: "Did you know octopuses have three hearts? Follow for more.",
  km: "តើអ្នកដឹងទេ ថាមឹកដៃប្រាំបី មានបេះដូងបី? តាមដានយើង ដើម្បីដឹងបន្ថែម។",
};
const RATES = [
  { value: "-10%", label: "Slower" },
  { value: "+0%", label: "Normal" },
  { value: "+5%", label: "Slightly fast" },
  { value: "+15%", label: "Fast" },
];

const REGION: Record<string, string> = { "en-US": "English (US)", "en-GB": "English (UK)", "en-AU": "English (Australia)", "km-KH": "Khmer" };

/** "en-US-AndrewMultilingualNeural" -> "Andrew Multilingual" */
function voiceName(v: string) {
  return v.split("-").slice(2).join(" ").replace(/Neural$/, "").replace(/([a-z])([A-Z])/g, "$1 $2");
}

/** Voices grouped by region, keeping the engine's order (recommended voices first). */
function groupVoices(voices: string[]) {
  const groups = new Map<string, string[]>();
  for (const v of voices) {
    const region = v.split("-").slice(0, 2).join("-");
    groups.set(region, [...(groups.get(region) ?? []), v]);
  }
  return [...groups.entries()];
}

function SaveStatus({ state, saved }: { state: SaveState; saved: boolean }) {
  if (state === "saving")
    return (
      <span role="status" className="flex shrink-0 items-center gap-1.5 text-[12.5px] text-ink-soft">
        <Spinner className="size-3.5" /> Saving
      </span>
    );
  if (state === "error")
    return (
      <span role="alert" className="flex shrink-0 items-center gap-1.5 text-[12.5px] font-semibold text-danger">
        <CircleAlert className="size-3.5" /> Not saved. Is the engine running?
      </span>
    );
  if (!saved)
    return <span className="hidden shrink-0 text-[12.5px] text-ink-soft md:inline">Your edits will be saved as a new draft</span>;
  return (
    <span role="status" className="flex shrink-0 items-center gap-1 text-[12.5px] text-ink-soft">
      <Check className="size-3.5 text-ok" /> Saved
    </span>
  );
}

export function Storyboard({
  draft,
  setDraft,
  options,
  rendering,
  saveState,
  activeUid,
  onActive,
  onBack,
  onNewDraft,
  onDeleteDraft,
  onRender,
}: {
  draft: Draft;
  setDraft: (update: (d: Draft) => Draft) => void;
  options: Options;
  rendering: boolean;
  saveState: SaveState;
  activeUid: string | null;
  onActive: (uid: string) => void;
  onBack: () => void;
  onNewDraft: (draft: Draft, notice: string) => void;
  onDeleteDraft: () => void;
  onRender: (script: VideoScript, settings: { voice: string; rate: string; music: string }) => Promise<string | null>;
}) {
  const toast = useToast();
  const voices = options.langs[draft.lang].voices;
  const voice = voices.includes(draft.voice) ? draft.voice : (voices[0] ?? "");
  const rate = draft.rate || "+5%";
  const music = draft.music || (options.music.length ? "" : "none");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [translating, setTranslating] = useState(false);

  const onPreviewError = useCallback((m: string) => toast(m, "error"), [toast]);
  const preview = useVoicePreview(onPreviewError);
  const listenState = (id: string) => (preview.active === id ? (preview.loading ? "loading" : "playing") : "idle");

  const other: Lang = draft.lang === "km" ? "en" : "km";
  const otherLabel = other === "km" ? "ខ្មែរ" : "English";

  const updateScene = (i: number, patch: Partial<DraftScene>) =>
    setDraft((d) => ({ ...d, scenes: d.scenes.map((s, j) => (j === i ? { ...s, ...patch } : s)) }));
  const moveScene = (i: number, dir: -1 | 1) =>
    setDraft((d) => {
      const scenes = [...d.scenes];
      const j = i + dir;
      if (j < 0 || j >= scenes.length) return d;
      [scenes[i], scenes[j]] = [scenes[j], scenes[i]];
      return { ...d, scenes };
    });
  const removeScene = (i: number) => setDraft((d) => (d.scenes.length > 1 ? { ...d, scenes: d.scenes.filter((_, j) => j !== i) } : d));
  const addScene = () => {
    const s = emptyScene();
    setDraft((d) => ({ ...d, scenes: [...d.scenes, s] }));
    onActive(s.uid);
    setTimeout(() => document.getElementById(`narration-${s.uid}`)?.focus(), 0);
  };

  async function translate() {
    const script = toScript(draft);
    if (!script.scenes.length) return toast("Write the voiceover for at least one scene first.", "error");
    preview.stop();
    setTranslating(true);
    try {
      const translated = await api.translate(script, other);
      // a translation is a new draft, so the original-language draft is kept
      onNewDraft(
        toDraft(translated, other, draft.topic, { rate: draft.rate, music: draft.music }),
        `Translated to ${options.langs[other].name} and saved as a new draft. The original is still in Drafts.`,
      );
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setTranslating(false);
    }
  }

  async function render() {
    const script = toScript(draft);
    if (!script.scenes.length) return toast("Write the voiceover for at least one scene first.", "error");
    preview.stop();
    const error = await onRender(script, { voice, rate, music });
    if (error) toast(error, "error");
  }

  const filled = draft.scenes.filter((s) => s.narration.trim()).length;

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Header */}
      <header className="flex h-14 shrink-0 items-center gap-2 border-b border-line bg-panel px-3 sm:px-5">
        <IconButton label="Back to start" onClick={onBack}>
          <ChevronLeft className="size-5" />
        </IconButton>
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <span className="truncate text-sm font-semibold" lang={draft.lang}>
            {draft.title || "Untitled draft"}
          </span>
          <SaveStatus state={saveState} saved={draft.id !== null} />
        </div>
        <Button size="sm" icon={<Languages className="size-3.5" />} onClick={translate} loading={translating}>
          <span className="hidden sm:inline">Translate to&nbsp;</span>
          <span lang={other}>{otherLabel}</span>
        </Button>
        {draft.id && (
          <Button
            size="sm"
            variant="danger"
            aria-label={confirmDelete ? "Confirm delete draft" : "Delete draft"}
            icon={<Trash2 className="size-3.5" />}
            onClick={() => {
              if (!confirmDelete) {
                setConfirmDelete(true);
                setTimeout(() => setConfirmDelete(false), 3000);
                return;
              }
              preview.stop();
              onDeleteDraft();
            }}
          >
            <span className={confirmDelete ? "" : "hidden md:inline"}>{confirmDelete ? "Confirm delete" : "Delete"}</span>
          </Button>
        )}
      </header>

      {/* Editor */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto grid max-w-[880px] gap-6 px-4 py-6 sm:px-8 sm:py-8">
          <div className="grid gap-1.5">
            <label htmlFor="title" className="field-label">
              Title
            </label>
            <textarea
              id="title"
              lang={draft.lang}
              rows={1}
              value={draft.title}
              onChange={(e) => setDraft((d) => ({ ...d, title: e.target.value.replace(/\n/g, " ") }))}
              placeholder="Video title"
              className="field-sizing-content w-full resize-none rounded-lg border border-transparent bg-transparent px-0 py-1 font-display text-[clamp(24px,2.6vw,32px)] leading-tight font-extrabold tracking-[-0.02em] hover:border-line hover:px-3 focus:border-cobalt focus:bg-panel focus:px-3 focus:outline-none"
            />
            <p className="m-0 text-[13px] text-ink-soft">
              {options.langs[draft.lang].name}, {draft.scenes.length} scene{draft.scenes.length === 1 ? "" : "s"}
              {filled < draft.scenes.length && `, ${draft.scenes.length - filled} without voiceover (skipped when rendering)`}
            </p>
          </div>

          <ol className="m-0 grid list-none gap-3 p-0">
            {draft.scenes.map((s, i) => (
              <SceneCard
                key={s.uid}
                scene={s}
                index={i}
                total={draft.scenes.length}
                lang={draft.lang}
                active={s.uid === activeUid}
                listenState={listenState(s.uid)}
                onActivate={() => onActive(s.uid)}
                onChange={(patch) => updateScene(i, patch)}
                onMove={(dir) => moveScene(i, dir)}
                onRemove={() => removeScene(i)}
                onListen={() => preview.toggle(s.uid, s.narration, voice, rate)}
              />
            ))}
          </ol>
          <Button variant="secondary" icon={<Plus className="size-4" />} onClick={addScene} className="justify-self-start border-dashed">
            Add scene
          </Button>

          <section className="grid gap-4 rounded-xl border border-line bg-panel p-4 sm:p-5">
            <h2 className="m-0 font-display text-base font-bold">Post details</h2>
            <Field label="Caption" htmlFor="caption">
              <textarea id="caption" lang={draft.lang} rows={2} className="field-input resize-y" value={draft.caption} onChange={(e) => setDraft((d) => ({ ...d, caption: e.target.value }))} />
            </Field>
            <Field label="Hashtags" hint="separate with spaces" htmlFor="hashtags">
              <input id="hashtags" className="field-input" value={draft.hashtags} onChange={(e) => setDraft((d) => ({ ...d, hashtags: e.target.value }))} />
            </Field>
          </section>
        </div>
      </div>

      {/* Render bar */}
      <footer className="shrink-0 border-t border-line bg-panel px-3 py-3 sm:px-5">
        <div className="mx-auto flex max-w-[880px] flex-wrap items-end gap-3">
          <div className="grid min-w-[150px] flex-[2] gap-1">
            <label className="field-label" htmlFor="voice">
              Voice
            </label>
            <div className="flex gap-1.5">
              <select
                id="voice"
                className="field-input h-10 py-0"
                value={voice}
                onChange={(e) => {
                  preview.stop();
                  setDraft((d) => ({ ...d, voice: e.target.value }));
                }}
              >
                {groupVoices(voices).map(([region, list]) => (
                  <optgroup key={region} label={REGION[region] ?? region}>
                    {list.map((v) => (
                      <option key={v} value={v}>
                        {voiceName(v)}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              <Button
                aria-label={listenState("voice") === "playing" ? "Stop voice preview" : "Listen to this voice"}
                title="Listen to this voice"
                className="w-10 px-0!"
                icon={listenState("voice") === "loading" ? <Spinner /> : listenState("voice") === "playing" ? <Pause className="size-4 fill-current" /> : <Play className="size-4 fill-current" />}
                onClick={() => preview.toggle("voice", draft.scenes.find((s) => s.narration.trim())?.narration || SAMPLE[draft.lang], voice, rate)}
              />
            </div>
          </div>
          <div className="grid min-w-[145px] flex-1 gap-1">
            <label className="field-label" htmlFor="rate">
              Speed
            </label>
            <select
              id="rate"
              className="field-input h-10 py-0"
              value={rate}
              onChange={(e) => {
                preview.stop();
                setDraft((d) => ({ ...d, rate: e.target.value }));
              }}
            >
              {RATES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>
          <div className="grid min-w-[125px] flex-1 gap-1">
            <label className="field-label" htmlFor="music">
              Music
            </label>
            <select id="music" className="field-input h-10 py-0" value={music} onChange={(e) => setDraft((d) => ({ ...d, music: e.target.value }))}>
              {options.music.length > 0 && <option value="">Random track</option>}
              <option value="none">No music</option>
              {options.music.map((m) => (
                <option key={m} value={m}>
                  {m.replace(/\.mp3$/i, "")}
                </option>
              ))}
            </select>
          </div>
          <Button variant="primary" onClick={render} loading={rendering} icon={<Clapperboard className="size-4" />} className="w-full sm:w-auto">
            {rendering ? "Rendering…" : "Render video"}
          </Button>
        </div>
      </footer>
    </div>
  );
}
