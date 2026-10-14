"use client";

import { Check, ChevronLeft, CircleAlert, Clapperboard, Copy, Dices, GalleryHorizontal, Languages, Music2, Paintbrush, Pause, Play, Plus, Redo2, Trash2, Undo2, Wand2 } from "lucide-react";
import { useCallback, useState } from "react";
import { api, DEFAULT_CAPTIONS, pinnedComment, type ArtStyle, type CaptionStyle, type DraftData, type Lang, type Options, type VideoScript } from "@/lib/api";
import type { DraftTimeline } from "@/lib/useDraftTimeline";
import { useVoicePreview } from "@/lib/useVoicePreview";
import { ArtStylePicker, artBlocker, useArtStatus } from "./ArtControls";
import { PictureReview } from "./PictureReview";
import { MusicFinder } from "./MusicFinder";
import { SceneCard, type DraftScene } from "./SceneCard";
import { Timeline } from "./Timeline";
import { Transcript } from "./Transcript";
import { Button, Field, IconButton, Segmented, Spinner, useToast } from "./ui";

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
  mood: string; // content plan's Music / Mood: picks the background track
  key_visual: string; // content plan's Key Visual: the cover is taken from the scene keyUid
  keyUid: string | null;
  captions: CaptionStyle;
  facts: string[];
  sources: string;
  pinned_comment: string;
  art_style: ArtStyle | ""; // "" = stock footage; else scenes without chosen media are drawn in this look
  art_bible: string; // the director's notes that keep every picture in one style
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
  const scenes = (script.scenes.length ? script.scenes : [{ narration: "", visual_query: "", on_screen_text: "", media: "" }]).map(
    (s) => ({ ...s, media: s.media ?? "", uid: uid() }),
  );
  return {
    id: extra.id ?? null,
    voice: extra.voice ?? "",
    rate: extra.rate ?? "+5%",
    music: extra.music ?? "",
    title: script.title,
    scenes,
    caption: script.caption,
    hashtags: script.hashtags.map((h) => `#${h}`).join(" "),
    lang,
    topic,
    mood: script.mood ?? "",
    key_visual: script.key_visual ?? "",
    keyUid: scenes[(script.key_scene ?? 0) - 1]?.uid ?? null,
    captions: { ...DEFAULT_CAPTIONS, ...script.captions },
    facts: script.facts ?? [],
    sources: script.sources ?? "",
    pinned_comment: script.pinned_comment ?? "",
    art_style: script.art_style ?? "",
    art_bible: script.art_bible ?? "",
  };
}

/** The content plan's mood and key visual, with the key scene's 1-based position among `scenes` (0 when it's gone). */
function planFields(
  d: Draft,
  scenes: DraftScene[],
): Pick<VideoScript, "mood" | "key_visual" | "key_scene" | "captions" | "facts" | "sources" | "pinned_comment" | "art_style" | "art_bible"> {
  return {
    mood: d.mood,
    key_visual: d.key_visual,
    key_scene: scenes.findIndex((s) => s.uid === d.keyUid) + 1,
    captions: d.captions,
    facts: d.facts.map((f) => f.trim()).filter(Boolean),
    sources: d.sources.trim(),
    pinned_comment: d.pinned_comment.trim(),
    art_style: d.art_style,
    art_bible: d.art_bible,
  };
}

/** What gets written to drafts/<id>/draft.json: everything, including unfinished scenes. */
export function toDraftData(d: Draft): DraftData {
  return {
    script: {
      title: d.title,
      scenes: d.scenes.map(({ uid: _, ...scene }) => scene), // eslint-disable-line @typescript-eslint/no-unused-vars
      caption: d.caption,
      hashtags: d.hashtags.split(/[\s,]+/).map((h) => h.replace(/^#/, "")).filter(Boolean),
      ...planFields(d, d.scenes),
    },
    lang: d.lang,
    topic: d.topic,
    voice: d.voice,
    rate: d.rate,
    music: d.music,
  };
}

/** What gets rendered: scenes with narration (or a silent beat's length), trimmed. */
function toScript(d: Draft): VideoScript {
  const kept = d.scenes.filter((s) => s.narration.trim() || s.seconds);
  return {
    title: d.title.trim() || "Untitled video",
    ...planFields(d, kept),
    scenes: kept.map((s) => ({
      narration: s.narration.trim(),
      visual_query: s.visual_query.trim() || "abstract background",
      on_screen_text: s.on_screen_text.trim(),
      media: s.media,
      seconds: s.seconds,
      keywords: s.keywords,
      cuts: s.cuts,
      cuts_key: s.cuts_key,
      media_start: s.media_start,
      layout: s.layout,
      media2: s.media2,
      broll: s.broll,
      texts: s.texts?.filter((t) => t.text.trim()),
      art_prompt: s.art_prompt?.trim(),
      art_seed: s.art_seed,
      motion: s.motion,
      effects: s.effects,
    })),
    caption: d.caption.trim(),
    hashtags: d.hashtags.split(/[\s,]+/).map((h) => h.replace(/^#/, "")).filter(Boolean),
  };
}

/** The voice and speed a draft renders with (its own, or the language's default voice). */
export function draftVoice(draft: Pick<Draft, "lang" | "voice" | "rate">, options: Options) {
  const voices = options.langs[draft.lang].voices;
  return { voice: voices.includes(draft.voice) ? draft.voice : (voices[0] ?? ""), rate: draft.rate || "+5%" };
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

/** "playful-sneaky-pizzicato_Sneaky-Snitch.mp3" -> "playful sneaky pizzicato · Sneaky Snitch" */
const trackName = (file: string) => file.replace(/\.mp3$/i, "").replace("_", " · ").replace(/-/g, " ");

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

/** The content plan's fact-check notes and the comment to pin under the video, made from them. */
function FactCheck({ draft, setDraft }: { draft: Draft; setDraft: (update: (d: Draft) => Draft) => void }) {
  const toast = useToast();
  const notes = draft.facts.join("\n");
  return (
    <section aria-labelledby="fact-check" className="grid gap-4 card p-4 sm:p-5">
      <div className="grid gap-0.5">
        <h2 id="fact-check" className="card-title m-0">
          Fact check
        </h2>
        <p className="m-0 text-base text-ink-soft">Notes to keep the voiceover accurate. They aren&apos;t in the video; share them in a pinned comment.</p>
      </div>
      <Field label="Notes" hint="one per line" htmlFor="facts">
        <textarea
          id="facts"
          rows={Math.min(Math.max(draft.facts.length, 2), 8)}
          className="field-input resize-y text-base leading-relaxed"
          value={notes}
          placeholder="e.g. Based on Humphrey et al. (2020), Scientific Reports."
          onChange={(e) => setDraft((d) => ({ ...d, facts: e.target.value.split("\n") }))}
        />
      </Field>
      <Field label="Pinned comment" hint="paste it under the video and pin it" htmlFor="pinned">
        <textarea
          id="pinned"
          rows={4}
          className="field-input resize-y text-base leading-relaxed"
          value={draft.pinned_comment}
          onChange={(e) => setDraft((d) => ({ ...d, pinned_comment: e.target.value }))}
        />
      </Field>
      <div className="-mt-2 flex flex-wrap gap-1.5">
        <Button size="sm" variant="ghost" disabled={!draft.facts.some((f) => f.trim())} onClick={() => setDraft((d) => ({ ...d, pinned_comment: pinnedComment(d.facts) }))}>
          Make from notes
        </Button>
        <Button
          size="sm"
          variant="ghost"
          icon={<Copy className="size-3.5" />}
          disabled={!draft.pinned_comment.trim()}
          onClick={() =>
            navigator.clipboard.writeText(draft.pinned_comment).then(
              () => toast("Comment copied", "success"),
              () => toast("Couldn't copy. Select the text and copy it.", "error"),
            )
          }
        >
          Copy
        </Button>
      </div>
    </section>
  );
}

function SaveStatus({ state, saved }: { state: SaveState; saved: boolean }) {
  if (state === "saving")
    return (
      <span role="status" className="flex shrink-0 items-center gap-1.5 text-sm text-ink-soft">
        <Spinner className="size-3.5" /> Saving
      </span>
    );
  if (state === "error")
    return (
      <span role="alert" className="flex shrink-0 items-center gap-1.5 text-sm font-semibold text-danger">
        <CircleAlert className="size-3.5" /> Not saved. Is the engine running?
      </span>
    );
  if (!saved)
    return <span className="hidden shrink-0 text-sm text-ink-soft md:inline">Your edits will be saved as a new draft</span>;
  return (
    <span role="status" className="flex shrink-0 items-center gap-1 text-sm text-ink-soft">
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
  timeline,
  history,
  onMusicAdded,
}: {
  draft: Draft;
  setDraft: (update: (d: Draft) => Draft) => void;
  options: Options;
  rendering: boolean;
  saveState: SaveState;
  activeUid: string | null;
  onActive: (uid: string, seek?: boolean) => void; // seek: also move the preview's playhead to the scene
  onBack: () => void;
  onNewDraft: (draft: Draft, notice: string) => void;
  onDeleteDraft: () => void;
  onRender: (script: VideoScript, settings: { voice: string; rate: string; music: string }) => Promise<string | null>;
  timeline: DraftTimeline;
  history: { canUndo: boolean; canRedo: boolean; undo: () => void; redo: () => void };
  onMusicAdded: () => void; // a track was added to the music library: reload the list
}) {
  const toast = useToast();
  const voices = options.langs[draft.lang].voices;
  const { voice, rate } = draftVoice(draft, options);
  const music = draft.music || (options.music.length ? "" : "none");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [mode, setMode] = useState<"scenes" | "transcript">("scenes");
  const [findingMusic, setFindingMusic] = useState(false);

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
        { ...toDraft(translated, other, draft.topic, { rate: draft.rate, music: draft.music }), art_style: draft.art_style, art_bible: draft.art_bible },
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
  const art = useArtStatus();
  const [planning, setPlanning] = useState(false);
  const [drawingAll, setDrawingAll] = useState<string>(""); // "2/6" while drawing every scene

  /** Claude writes a picture prompt, camera move and effects for every scene (all at once, so they match). */
  async function planPictures(replace: boolean) {
    if (!draft.art_style) return;
    setPlanning(true);
    try {
      const planned = await api.artPlan(toDraftData(draft).script, replace);
      setDraft((d) => ({
        ...d,
        art_bible: planned.art_bible ?? d.art_bible,
        scenes: d.scenes.map((s, i) => {
          const p = planned.scenes[i];
          return p ? { ...s, art_prompt: p.art_prompt ?? s.art_prompt, motion: p.motion ?? s.motion, effects: p.effects ?? s.effects } : s;
        }),
      }));
      toast("Pictures planned. Draw them one by one, or all at once.", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setPlanning(false);
    }
  }

  // scenes that get an AI picture: no stock footage chosen for them (or an AI picture already)
  const drawable = (sc: DraftScene) => !sc.media || sc.media.startsWith("cache/gen/");
  const promptOf = (sc: DraftScene) => (sc.art_prompt || sc.visual_query || "").trim();
  const [reviewing, setReviewing] = useState<number | null>(null); // the one-by-one view, from this scene
  const [confirmRedraw, setConfirmRedraw] = useState(false);

  /** Draw one scene's picture (a new take: another seed). True when it worked. */
  async function drawScene(uid: string, newTake: boolean) {
    const style = draft.art_style;
    const scene = draft.scenes.find((sc) => sc.uid === uid);
    const prompt = scene ? promptOf(scene) : "";
    if (!style || !prompt) return false;
    try {
      const seed = newTake ? Math.floor(Math.random() * 2 ** 31) + 1 : scene!.art_seed || undefined;
      const m = await api.artDraw({ prompt, style, seed });
      setDraft((d) => ({
        ...d,
        scenes: d.scenes.map((sc) => (sc.uid === uid ? { ...sc, media: m.media, media_start: 0, art_seed: m.seed, art_prompt: prompt } : sc)),
      }));
      return true;
    } catch (e) {
      toast((e as Error).message, "error");
      return false;
    }
  }

  /** Draw every scene that has a prompt but no picture yet, one after another; when all have one, `redraw` draws a
   *  new take of every AI picture. */
  async function drawAll(redraw = false) {
    if (!draft.art_style) return;
    const todo = draft.scenes.filter((sc) => drawable(sc) && promptOf(sc) && (redraw || !sc.media));
    if (!todo.length) return toast("Plan pictures first: no scene has a picture prompt yet.", "info");
    for (const [k, scene] of todo.entries()) {
      setDrawingAll(`${k + 1}/${todo.length}`);
      if (!(await drawScene(scene.uid, redraw))) break;
    }
    setDrawingAll("");
  }

  const artScenes = draft.scenes.filter(drawable);
  const undrawn = artScenes.filter((sc) => !sc.media && promptOf(sc)).length;
  const allDrawn = artScenes.length > 0 && artScenes.every((sc) => sc.media);

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Header */}
      <header className="flex h-14 shrink-0 items-center gap-2 border-b border-line bg-panel px-3 sm:px-5">
        <IconButton label="Back to start" onClick={onBack}>
          <ChevronLeft className="size-5" />
        </IconButton>
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <span className="truncate text-md font-semibold" lang={draft.lang}>
            {draft.title || "Untitled draft"}
          </span>
          <SaveStatus state={saveState} saved={draft.id !== null} />
        </div>
        <IconButton label="Undo (Ctrl+Z)" onClick={history.undo} disabled={!history.canUndo}>
          <Undo2 className="size-4" />
        </IconButton>
        <IconButton label="Redo (Ctrl+Shift+Z)" onClick={history.redo} disabled={!history.canRedo}>
          <Redo2 className="size-4" />
        </IconButton>
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
              className="field-sizing-content w-full resize-none rounded-lg border border-transparent bg-transparent px-0 py-1 page-title hover:border-line hover:px-3 focus:border-cobalt focus:bg-panel focus:px-3 focus:outline-none"
            />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="m-0 text-base text-ink-soft">
                {options.langs[draft.lang].name}, {draft.scenes.length} scene{draft.scenes.length === 1 ? "" : "s"}
                {filled < draft.scenes.length && `, ${draft.scenes.length - filled} without voiceover (skipped when rendering)`}
              </p>
              <Segmented
                name="editor-mode"
                size="sm"
                value={mode}
                onChange={(m) => {
                  preview.stop();
                  setMode(m);
                }}
                options={[
                  { value: "scenes", label: "Scenes" },
                  { value: "transcript", label: "Transcript" },
                ]}
              />
            </div>
          </div>

          <section className="grid gap-3 card p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="card-title m-0">Visuals</h2>
              {draft.art_style && (
                <div className="flex flex-wrap items-center gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    icon={<Wand2 className="size-3.5" />}
                    loading={planning}
                    disabled={!options.keys.anthropic}
                    title="Claude plans one consistent look, then a picture, camera move and effects for every scene"
                    onClick={() => planPictures(draft.scenes.some((s) => s.art_prompt))}
                  >
                    {draft.scenes.some((s) => s.art_prompt) ? "Re-plan pictures" : "Plan pictures"}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    icon={<GalleryHorizontal className="size-3.5" />}
                    disabled={!!artBlocker(art.status, draft.art_style) || planning || !!drawingAll || !artScenes.some(promptOf)}
                    title="Draw and check each picture in turn: keep it, or ask for another take"
                    onClick={() => {
                      const first = artScenes.findIndex((sc) => !sc.media);
                      setReviewing(first < 0 ? 0 : first);
                    }}
                  >
                    One by one
                  </Button>
                  <Button
                    size="sm"
                    variant={confirmRedraw ? "danger" : "ghost"}
                    icon={allDrawn ? <Dices className="size-3.5" /> : <Paintbrush className="size-3.5" />}
                    loading={!!drawingAll}
                    disabled={!!artBlocker(art.status, draft.art_style) || planning}
                    title={allDrawn ? "A new take of every AI picture (replaces the current ones)" : "Draw every scene that has no picture yet"}
                    onClick={() => {
                      if (!allDrawn) return void drawAll();
                      if (!confirmRedraw) {
                        setConfirmRedraw(true);
                        setTimeout(() => setConfirmRedraw(false), 3000);
                        return;
                      }
                      setConfirmRedraw(false);
                      void drawAll(true);
                    }}
                  >
                    {drawingAll
                      ? `Drawing ${drawingAll}…`
                      : allDrawn
                        ? confirmRedraw
                          ? `Replace all ${artScenes.length}?`
                          : "Redraw all"
                        : undrawn < artScenes.length && undrawn > 0
                          ? `Draw the other ${undrawn}`
                          : "Draw all"}
                  </Button>
                </div>
              )}
            </div>
            <ArtStylePicker value={draft.art_style} onChange={(v) => setDraft((d) => ({ ...d, art_style: v }))} status={art.status} reload={art.reload} />
            {draft.art_style && draft.art_bible && (
              <details className="text-sm">
                <summary className="cursor-pointer font-semibold text-ink-soft">Look of the video (keeps every picture consistent)</summary>
                <textarea
                  aria-label="Look of the video"
                  rows={3}
                  className="field-input mt-1.5 resize-y text-sm leading-snug"
                  value={draft.art_bible}
                  onChange={(e) => setDraft((d) => ({ ...d, art_bible: e.target.value }))}
                />
              </details>
            )}
          </section>

          {reviewing !== null && draft.art_style && (
            <PictureReview
              items={artScenes.map((sc) => ({
                label: `Scene ${draft.scenes.indexOf(sc) + 1}`,
                text: sc.narration,
                prompt: sc.art_prompt || sc.visual_query || "",
                media: sc.media || null,
              }))}
              start={reviewing}
              aspect="9:16"
              blocker={artBlocker(art.status, draft.art_style)}
              onDraw={(k, newTake) => drawScene(artScenes[k].uid, newTake)}
              onPrompt={(k, prompt) => updateScene(draft.scenes.indexOf(artScenes[k]), { art_prompt: prompt })}
              onClose={() => setReviewing(null)}
            />
          )}

          {mode === "transcript" ? (
            <Transcript draft={draft} setDraft={setDraft} timeline={timeline} onActive={(uid) => onActive(uid, false)} />
          ) : (
            <>
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
                    artStyle={draft.art_style}
                    artStatus={art.status}
                  />
                ))}
              </ol>
              <Button variant="secondary" icon={<Plus className="size-4" />} onClick={addScene} className="justify-self-start border-dashed">
                Add scene
              </Button>
            </>
          )}

          <section className="grid gap-4 card p-4 sm:p-5">
            <h2 className="card-title m-0">Post details</h2>
            <Field label="Caption" htmlFor="caption">
              <textarea id="caption" lang={draft.lang} rows={2} className="field-input resize-y" value={draft.caption} onChange={(e) => setDraft((d) => ({ ...d, caption: e.target.value }))} />
            </Field>
            <Field label="Hashtags" hint="separate with spaces" htmlFor="hashtags">
              <input id="hashtags" className="field-input" value={draft.hashtags} onChange={(e) => setDraft((d) => ({ ...d, hashtags: e.target.value }))} />
            </Field>
            <Field label="Sources" hint="added to the description as “Sources: …”" htmlFor="sources">
              <input
                id="sources"
                className="field-input"
                value={draft.sources}
                placeholder="e.g. Humphrey et al. (2020), Scientific Reports"
                onChange={(e) => setDraft((d) => ({ ...d, sources: e.target.value }))}
              />
            </Field>
          </section>

          <FactCheck draft={draft} setDraft={setDraft} />
        </div>
      </div>

      <Timeline draft={draft} setDraft={setDraft} timeline={timeline} onActive={onActive} activeUid={activeUid} />

      {/* Render bar */}
      <footer className="shrink-0 border-t border-line bg-panel px-3 py-3 sm:px-5">
        {findingMusic && (
          <div className="mx-auto mb-3 max-w-[880px]">
            <MusicFinder
              initialQuery={draft.mood || draft.title}
              ready={!!options.keys.jamendo}
              onClose={() => setFindingMusic(false)}
              onPicked={(file) => {
                setDraft((d) => ({ ...d, music: file }));
                onMusicAdded();
              }}
            />
          </div>
        )}
        <div className="mx-auto flex max-w-[880px] flex-wrap items-end gap-3">
          <div className="grid min-w-[180px] flex-[2] gap-1">
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
          <div className="grid min-w-[130px] flex-1 gap-1">
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
          <div className="grid min-w-[180px] flex-[1.4] gap-1">
            <label className="field-label" htmlFor="music">
              Music
            </label>
            <div className="flex gap-1.5">
              <select id="music" className="field-input h-10 min-w-0 py-0" value={music} onChange={(e) => setDraft((d) => ({ ...d, music: e.target.value }))}>
                {options.music.length > 0 && <option value="">{draft.mood ? "Matches the mood" : "Random track"}</option>}
                <option value="none">No music</option>
                {music && music !== "none" && !options.music.includes(music) && <option value={music}>{trackName(music)}</option>}
                {options.music.map((m) => (
                  <option key={m} value={m}>
                    {trackName(m)}
                  </option>
                ))}
              </select>
              <Button
                aria-label="Find free music"
                title="Find free music on Jamendo"
                aria-expanded={findingMusic}
                className="w-10 px-0!"
                icon={<Music2 className="size-4" />}
                onClick={() => setFindingMusic((f) => !f)}
              />
            </div>
          </div>
          <Button variant="primary" onClick={render} loading={rendering} icon={<Clapperboard className="size-4" />} className="w-full sm:w-auto">
            {rendering ? "Rendering…" : "Render video"}
          </Button>
        </div>
      </footer>
    </div>
  );
}
