"use client";

import {
  ArrowDown,
  ArrowUp,
  AudioLines,
  Captions,
  Check,
  ChevronLeft,
  CircleAlert,
  Clapperboard,
  Copy,
  Dices,
  GalleryHorizontal,
  ImageIcon,
  Languages,
  ListVideo,
  Music2,
  Paintbrush,
  Palette,
  Pause,
  Play,
  Plus,
  Redo2,
  ScrollText,
  Send,
  Share2,
  SlidersHorizontal,
  Trash2,
  Undo2,
  Wand2,
} from "lucide-react";
import { useCallback, useState, useSyncExternalStore, type ReactNode } from "react";
import { api, DEFAULT_CAPTIONS, fileUrl, pinnedComment, type ArtStyle, type CaptionStyle, type DraftData, type Lang, type Options, type VideoScript } from "@/lib/api";
import { usePaneWidth } from "@/lib/appearance";
import { isImagePath } from "@/lib/format";
import type { DraftTimeline } from "@/lib/useDraftTimeline";
import { useVoicePreview } from "@/lib/useVoicePreview";
import { USE_HINT, USE_LABEL, useMonetizableOnly, type MusicUse } from "@/lib/musicLicence";
import { ArtStylePicker, artBlocker, useArtStatus } from "./ArtControls";
import { PictureReview } from "./PictureReview";
import { MusicFinder } from "./MusicFinder";
import { CaptionPanel } from "./LivePreview";
import { SceneCard, type DraftScene } from "./SceneCard";
import { Timeline } from "./Timeline";
import { Transcript, clock } from "./Transcript";
import { Button, Chip, Field, IconButton, ResizeHandle, Segmented, Spinner, useToast } from "./ui";

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
  art_subject: string; // the real subject the pictures must get right (checked in each)
  art_avoid: string; // what the image model must not draw instead
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
    art_subject: script.art_subject ?? "",
    art_avoid: script.art_avoid ?? "",
  };
}

/** The content plan's mood and key visual, with the key scene's 1-based position among `scenes` (0 when it's gone). */
function planFields(
  d: Draft,
  scenes: DraftScene[],
): Pick<
  VideoScript,
  "mood" | "key_visual" | "key_scene" | "captions" | "facts" | "sources" | "pinned_comment" | "art_style" | "art_bible" | "art_subject" | "art_avoid"
> {
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
    art_subject: d.art_subject,
    art_avoid: d.art_avoid,
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
  stage,
  exportPanel,
  exportKey,
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
  stage: ReactNode; // the player in the middle of the editor
  exportPanel: ReactNode | null; // the rendered video's cover, post text and publishing (null until there is one)
  exportKey: string | null; // which rendered video exportPanel is about: a new one opens the Export tab
}) {
  const toast = useToast();
  const voices = options.langs[draft.lang].voices;
  const { voice, rate } = draftVoice(draft, options);
  const music = draft.music || (options.music.length ? "" : "none");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [leftTab, setLeftTab] = useState<LeftTab>("scenes");
  const [rightTab, setRightTab] = useState<RightTab>("scene");
  const [narrowTab, setNarrowTab] = useState<LeftTab | RightTab>("scene");
  const wide = useMinWidth(1024);
  // the side panels can be dragged wider or narrower; the widths are remembered
  const leftPane = usePaneWidth("editor-project", 300, 240, 560);
  const rightPane = usePaneWidth("editor-inspector", 380, 300, 560);
  // a video just rendered (or opened): show its Export panel
  const [seenExport, setSeenExport] = useState(exportKey);
  if (exportKey !== seenExport) {
    setSeenExport(exportKey);
    if (exportKey) {
      setRightTab("export");
      setNarrowTab("export");
    }
  }
  const [findingMusic, setFindingMusic] = useState(false);
  // the music menu lists only tracks a monetized video may use, unless you turn the filter off
  const [safeOnly, setSafeOnly] = useMonetizableOnly();
  const licenceOf = (m: string): MusicUse => options.music_use?.[m] ?? "unknown";
  const listed = safeOnly ? options.music.filter((m) => licenceOf(m) === "ok") : options.music;
  const hidden = options.music.length - listed.length;

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
  const reorderScene = (from: number, to: number) =>
    setDraft((d) => {
      const scenes = [...d.scenes];
      const [moved] = scenes.splice(from, 1);
      scenes.splice(to, 0, moved);
      return { ...d, scenes };
    });
  /** Select a scene: the preview jumps to it and the inspector shows it. */
  const activate = (uid: string) => {
    onActive(uid);
    setRightTab("scene");
    if (!wide) setNarrowTab("scene");
  };
  const removeScene = (i: number) => setDraft((d) => (d.scenes.length > 1 ? { ...d, scenes: d.scenes.filter((_, j) => j !== i) } : d));
  const addScene = () => {
    const s = emptyScene();
    setDraft((d) => ({ ...d, scenes: [...d.scenes, s] }));
    activate(s.uid);
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
        { ...toDraft(translated, other, draft.topic, { rate: draft.rate, music: draft.music }), art_style: draft.art_style, art_bible: draft.art_bible, art_subject: draft.art_subject, art_avoid: draft.art_avoid },
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
  async function planPictures(replace: boolean, quiet = false) {
    if (!draft.art_style) return null;
    setPlanning(true);
    try {
      const script = toDraftData(draft).script;
      if (!draft.art_bible) {
        // never planned: a prompt that is just the footage search words (drawn before planning) is planned afresh
        script.scenes = script.scenes.map((s) => (s.art_prompt?.trim() === s.visual_query.trim() ? { ...s, art_prompt: "" } : s));
      }
      const planned = await api.artPlan(script, replace);
      const scenes = draft.scenes.map((s, i) => {
        const p = planned.scenes[i];
        return p ? { ...s, art_prompt: p.art_prompt ?? s.art_prompt, motion: p.motion ?? s.motion, effects: p.effects ?? s.effects } : s;
      });
      const plan = {
        art_bible: planned.art_bible ?? draft.art_bible,
        art_subject: planned.art_subject ?? draft.art_subject,
        art_avoid: planned.art_avoid ?? draft.art_avoid,
      };
      setDraft((d) => ({
        ...d,
        ...plan,
        scenes: d.scenes.map((s) => {
          const p = scenes.find((x) => x.uid === s.uid);
          return p ? { ...s, art_prompt: p.art_prompt, motion: p.motion, effects: p.effects } : s;
        }),
      }));
      if (!quiet) toast("Pictures planned. Draw them one by one, or all at once.", "success");
      return { ...plan, scenes };
    } catch (e) {
      toast((e as Error).message, "error");
      return null;
    } finally {
      setPlanning(false);
    }
  }

  /** The draft as it will be drawn: planned first (when it never was and Claude is connected), so every picture
   *  gets a real prompt, and the video's subject is checked in each picture and drawn from a real photo. */
  async function plannedDraft() {
    if (draft.art_bible || !options.keys.anthropic) return draft;
    toast("Planning the pictures first (Claude)…", "info");
    const plan = await planPictures(false, true);
    return plan ? { ...draft, ...plan } : null;
  }

  // scenes that get an AI picture: no stock footage chosen for them (or an AI picture already)
  const drawable = (sc: DraftScene) => !sc.media || sc.media.startsWith("cache/gen/");
  const promptOf = (sc: DraftScene) => (sc.art_prompt || sc.visual_query || "").trim();
  const [reviewing, setReviewing] = useState<number | null>(null); // the one-by-one view, from this scene
  const [confirmRedraw, setConfirmRedraw] = useState(false);

  /** Draw one scene's picture (a new take: another seed). True when it worked. */
  async function drawScene(uid: string, newTake: boolean, from: Pick<Draft, "scenes" | "art_subject" | "art_avoid"> = draft) {
    const style = draft.art_style;
    const scene = from.scenes.find((sc) => sc.uid === uid);
    const prompt = scene ? promptOf(scene) : "";
    if (!style || !prompt) return false;
    try {
      const seed = newTake ? Math.floor(Math.random() * 2 ** 31) + 1 : scene!.art_seed || undefined;
      const m = await api.artDraw({ prompt, style, seed, subject: from.art_subject, avoid: from.art_avoid });
      if (m.score !== null && m.score < 8) toast(`Scene ${from.scenes.findIndex((sc) => sc.uid === uid) + 1}: ${m.problem} (${m.score}/10 after 3 takes)`, "error");
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
    const from = await plannedDraft();
    if (!from) return;
    const todo = from.scenes.filter((sc) => drawable(sc) && promptOf(sc) && (redraw || !sc.media));
    if (!todo.length) return toast("Plan pictures first: no scene has a picture prompt yet.", "info");
    for (const [k, scene] of todo.entries()) {
      setDrawingAll(`${k + 1}/${todo.length}`);
      if (!(await drawScene(scene.uid, redraw, from))) break;
    }
    setDrawingAll("");
  }

  const artScenes = draft.scenes.filter(drawable);
  const undrawn = artScenes.filter((sc) => !sc.media && promptOf(sc)).length;
  const allDrawn = artScenes.length > 0 && artScenes.every((sc) => sc.media);

  const lengths = Object.fromEntries(timeline.segments.map((s) => [s.scene.uid, s.length]));
  const totalSeconds = timeline.segments.reduce((sum, s) => sum + s.length, 0);
  const activeIndex = Math.max(0, draft.scenes.findIndex((s) => s.uid === activeUid));
  const activeScene = draft.scenes[activeIndex];

  const audioPanel = (
    <div className="grid gap-4 p-3">
      <div className="grid gap-1">
        <label className="field-label" htmlFor="voice">
          Voice
        </label>
        <div className="flex gap-1.5">
          <select
            id="voice"
            className="field-input h-9 min-w-0 py-0"
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
            className="h-9 w-9 shrink-0 px-0!"
            icon={listenState("voice") === "loading" ? <Spinner /> : listenState("voice") === "playing" ? <Pause className="size-4 fill-current" /> : <Play className="size-4 fill-current" />}
            onClick={() => preview.toggle("voice", draft.scenes.find((s) => s.narration.trim())?.narration || SAMPLE[draft.lang], voice, rate)}
          />
        </div>
      </div>
      <div className="grid justify-items-start gap-1">
        <span className="field-label">Speed</span>
        <Segmented
          name="rate"
          size="sm"
          value={rate}
          onChange={(v) => {
            preview.stop();
            setDraft((d) => ({ ...d, rate: v }));
          }}
          options={RATES}
        />
      </div>
      <div className="grid gap-1">
        <label className="field-label" htmlFor="music">
          Music
        </label>
        <div className="flex gap-1.5">
          <select id="music" className="field-input h-9 min-w-0 py-0" value={music} onChange={(e) => setDraft((d) => ({ ...d, music: e.target.value }))}>
            {options.music.length > 0 && <option value="">{draft.mood ? "Matches the mood" : "Random track"}</option>}
            <option value="none">No music</option>
            {music && music !== "none" && !listed.includes(music) && (
              <option value={music}>
                {trackName(music)}
                {licenceOf(music) !== "ok" ? ` (${USE_LABEL[licenceOf(music) as Exclude<MusicUse, "ok">]})` : ""}
              </option>
            )}
            {listed.map((m) => (
              <option key={m} value={m}>
                {trackName(m)}
                {licenceOf(m) !== "ok" ? ` (${USE_LABEL[licenceOf(m) as Exclude<MusicUse, "ok">]})` : ""}
              </option>
            ))}
          </select>
          <Button
            aria-label="Find free music"
            title="Find free music on Jamendo"
            aria-expanded={findingMusic}
            className="h-9 w-9 shrink-0 px-0!"
            icon={<Music2 className="size-4" />}
            onClick={() => setFindingMusic((f) => !f)}
          />
        </div>
        <label className="flex items-center gap-1.5 text-xs text-ink-soft" title="Hide tracks whose licence doesn't allow monetized videos (non-commercial or no-derivatives)">
          <input type="checkbox" className="size-3.5" checked={safeOnly} onChange={(e) => setSafeOnly(e.target.checked)} />
          Monetizable only{safeOnly && hidden > 0 ? ` (${hidden} hidden)` : ""}
        </label>
        {music && music !== "none" && licenceOf(music) !== "ok" && (
          <p role="status" className="m-0 flex items-start gap-1 text-xs text-warn">
            <CircleAlert className="mt-px size-3.5 shrink-0" />
            {USE_HINT[licenceOf(music) as Exclude<MusicUse, "ok">]}
          </p>
        )}
      </div>
      {findingMusic && (
        <MusicFinder
          initialQuery={draft.mood || draft.title}
          ready={!!options.keys.jamendo}
          onClose={() => setFindingMusic(false)}
          onPicked={(file) => {
            setDraft((d) => ({ ...d, music: file }));
            onMusicAdded();
          }}
        />
      )}
    </div>
  );

  const visualsPanel = (
    <div className="grid gap-3 p-3">
      <ArtStylePicker value={draft.art_style} onChange={(v) => setDraft((d) => ({ ...d, art_style: v }))} status={art.status} reload={art.reload} />
      {draft.art_style && (
        <div className="grid gap-1.5">
          <Button
            size="sm"
            variant="secondary"
            icon={<Wand2 className="size-3.5" />}
            loading={planning}
            disabled={!options.keys.anthropic}
            title="Claude plans one consistent look, then a picture, camera move and effects for every scene"
            onClick={() => planPictures(draft.scenes.some((s) => s.art_prompt))}
          >
            {draft.scenes.some((s) => s.art_prompt) ? "Re-plan pictures" : "Plan pictures"}
          </Button>
          <div className="grid grid-cols-2 gap-1.5">
            <Button
              size="sm"
              variant="secondary"
              icon={<GalleryHorizontal className="size-3.5" />}
              disabled={!!artBlocker(art.status, draft.art_style) || planning || !!drawingAll || !artScenes.some(promptOf)}
              title="Draw and check each picture in turn: keep it, or ask for another take"
              onClick={async () => {
                if (!(await plannedDraft())) return;
                const first = artScenes.findIndex((sc) => !sc.media);
                setReviewing(first < 0 ? 0 : first);
              }}
            >
              One by one
            </Button>
            <Button
              size="sm"
              variant={confirmRedraw ? "danger" : "secondary"}
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
        </div>
      )}
      {draft.art_style && draft.art_bible && (
        <div className="grid gap-2">
          <label className="grid gap-1">
            <span className="field-label">Look of the video</span>
            <textarea rows={4} className="field-input resize-y text-sm leading-snug" value={draft.art_bible} onChange={(e) => setDraft((d) => ({ ...d, art_bible: e.target.value }))} />
          </label>
          <label className="grid gap-1">
            <span className="field-label">
              Real subject <span className="font-normal">checked in each picture showing it, and drawn from a real photo of it</span>
            </span>
            <input
              className="field-input h-9 text-sm"
              value={draft.art_subject}
              placeholder="peacock mantis shrimp: green and orange body, eyes on stalks, folded club arms"
              onChange={(e) => setDraft((d) => ({ ...d, art_subject: e.target.value }))}
            />
          </label>
          <label className="grid gap-1">
            <span className="field-label">
              Never draw <span className="font-normal">look-alikes the model draws instead</span>
            </span>
            <input
              className="field-input h-9 text-sm"
              value={draft.art_avoid}
              placeholder="snail shell, lobster, crayfish, isopod, beetle"
              onChange={(e) => setDraft((d) => ({ ...d, art_avoid: e.target.value }))}
            />
          </label>
        </div>
      )}
    </div>
  );

  const postPanel = (
    <div className="grid gap-4 p-3">
      <Field label="Caption" htmlFor="caption">
        <textarea id="caption" lang={draft.lang} rows={3} className="field-input resize-y" value={draft.caption} onChange={(e) => setDraft((d) => ({ ...d, caption: e.target.value }))} />
      </Field>
      <Field label="Hashtags" hint="separate with spaces" htmlFor="hashtags">
        <input id="hashtags" className="field-input" value={draft.hashtags} onChange={(e) => setDraft((d) => ({ ...d, hashtags: e.target.value }))} />
      </Field>
      <Field label="Sources" hint="added to the description" htmlFor="sources">
        <input
          id="sources"
          className="field-input"
          value={draft.sources}
          placeholder="e.g. Humphrey et al. (2020), Scientific Reports"
          onChange={(e) => setDraft((d) => ({ ...d, sources: e.target.value }))}
        />
      </Field>
      <FactCheck draft={draft} setDraft={setDraft} />
    </div>
  );

  const panels: Record<LeftTab | RightTab, ReactNode> = {
    scenes: (
      <SceneBin
        scenes={draft.scenes}
        lang={draft.lang}
        activeUid={activeUid}
        lengths={lengths}
        onActive={activate}
        onMove={moveScene}
        onReorder={reorderScene}
        onRemove={removeScene}
        onAdd={addScene}
      />
    ),
    script: (
      <div className="p-3">
        <Transcript draft={draft} setDraft={setDraft} timeline={timeline} onActive={(uid) => onActive(uid, false)} />
      </div>
    ),
    visuals: visualsPanel,
    audio: audioPanel,
    post: postPanel,
    scene: activeScene ? (
      <ul className="m-0 list-none p-3">
        <SceneCard
          key={activeScene.uid}
          scene={activeScene}
          index={activeIndex}
          total={draft.scenes.length}
          lang={draft.lang}
          active={false}
          listenState={listenState(activeScene.uid)}
          onActivate={() => undefined}
          onChange={(patch) => updateScene(activeIndex, patch)}
          onMove={(dir) => moveScene(activeIndex, dir)}
          onRemove={() => removeScene(activeIndex)}
          onListen={() => preview.toggle(activeScene.uid, activeScene.narration, voice, rate)}
          artStyle={draft.art_style}
          artStatus={art.status}
          artSubject={{ subject: draft.art_subject, avoid: draft.art_avoid }}
          usedMedia={draft.scenes.filter((o) => o.uid !== activeScene.uid && o.media).map((o) => o.media)}
        />
      </ul>
    ) : null,
    captions: (
      <div className="p-3">
        <CaptionPanel style={draft.captions} onChange={(patch) => setDraft((d) => ({ ...d, captions: { ...d.captions, ...patch } }))} options={options} lang={draft.lang} />
      </div>
    ),
    export: exportPanel ? (
      <div className="p-3">{exportPanel}</div>
    ) : (
      <p className="m-0 p-4 text-base text-ink-soft">Render the video to pick its cover, write the post text and publish it from here.</p>
    ),
  };

  const rightTabs = exportPanel ? RIGHT_TABS : RIGHT_TABS.filter((t) => t.value !== "export");
  const inspectorTab = rightTabs.some((t) => t.value === rightTab) ? rightTab : "scene";
  const narrowTabs = [RIGHT_TABS[0], ...LEFT_TABS, ...rightTabs.slice(1)];

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Toolbar */}
      <header className="flex h-12 shrink-0 items-center gap-1.5 border-b border-line bg-panel px-2 sm:px-3">
        <IconButton label="Back to start" onClick={onBack}>
          <ChevronLeft className="size-5" />
        </IconButton>
        <input
          aria-label="Video title"
          lang={draft.lang}
          value={draft.title}
          placeholder="Untitled video"
          onChange={(e) => setDraft((d) => ({ ...d, title: e.target.value }))}
          className="h-8 min-w-[120px] flex-1 truncate rounded-md border border-transparent bg-transparent px-2 text-md font-semibold text-ink hover:border-line focus:border-cobalt focus:bg-paper focus:outline-none lg:max-w-[420px]"
        />
        <span className="hidden shrink-0 text-sm text-ink-soft tabular-nums xl:inline">
          {options.langs[draft.lang].name} · {draft.scenes.length} scene{draft.scenes.length === 1 ? "" : "s"}
          {totalSeconds > 0 && ` · ${clock(totalSeconds)}`}
          {filled < draft.scenes.length && ` · ${draft.scenes.length - filled} without voiceover`}
        </span>
        <SaveStatus state={saveState} saved={draft.id !== null} />
        <div className="ml-auto flex shrink-0 items-center gap-1">
          <IconButton label="Undo (Ctrl+Z)" onClick={history.undo} disabled={!history.canUndo}>
            <Undo2 className="size-4" />
          </IconButton>
          <IconButton label="Redo (Ctrl+Shift+Z)" onClick={history.redo} disabled={!history.canRedo}>
            <Redo2 className="size-4" />
          </IconButton>
          <span aria-hidden className="mx-1 h-5 w-px bg-line" />
          <Button size="sm" variant="ghost" icon={<Languages className="size-3.5" />} onClick={translate} loading={translating}>
            <span className="hidden md:inline">Translate to&nbsp;</span>
            <span lang={other}>{otherLabel}</span>
          </Button>
          {draft.id && (
            <Button
              size="sm"
              variant={confirmDelete ? "danger" : "ghost"}
              aria-label={confirmDelete ? "Confirm delete draft" : "Delete draft"}
              title="Delete draft"
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
              {confirmDelete && "Confirm delete"}
            </Button>
          )}
          <Button size="sm" variant="primary" onClick={render} loading={rendering} icon={<Clapperboard className="size-3.5" />}>
            {rendering ? "Rendering…" : "Render"}
          </Button>
        </div>
      </header>

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

      {wide ? (
        <div className="flex min-h-0 flex-1">
          {/* Project: scenes, script, visuals, audio, post */}
          <aside aria-label="Project" className="relative flex min-h-0 shrink-0 flex-col border-r border-line bg-paper" style={{ width: leftPane.width }}>
            <PanelTabs label="Project" value={leftTab} onChange={setLeftTab} items={LEFT_TABS} />
            <div role="tabpanel" className="min-h-0 flex-1 overflow-y-auto">
              {panels[leftTab]}
            </div>
            <ResizeHandle edge="right" label="Resize project panel" width={leftPane.width} min={240} max={560} onResize={leftPane.setWidth} onReset={leftPane.reset} />
          </aside>

          {/* Stage */}
          <section aria-label="Preview" className="min-w-0 flex-1 bg-sunken">
            {stage}
          </section>

          {/* Inspector: the selected scene, the caption look, the finished video */}
          <aside aria-label="Inspector" className="relative flex min-h-0 shrink-0 flex-col border-l border-line bg-paper" style={{ width: rightPane.width }}>
            <PanelTabs label="Inspector" value={inspectorTab} onChange={setRightTab} items={rightTabs} />
            <div role="tabpanel" className="min-h-0 flex-1 overflow-y-auto">
              {panels[inspectorTab]}
            </div>
            <ResizeHandle edge="left" label="Resize inspector" width={rightPane.width} min={300} max={560} onResize={rightPane.setWidth} onReset={rightPane.reset} />
          </aside>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <section aria-label="Preview" className="h-[62dvh] shrink-0 bg-sunken">
            {stage}
          </section>
          <PanelTabs label="Editor" value={narrowTabs.some((t) => t.value === narrowTab) ? narrowTab : "scene"} onChange={setNarrowTab} items={narrowTabs} />
          <div role="tabpanel" className="bg-paper">
            {panels[narrowTabs.some((t) => t.value === narrowTab) ? narrowTab : "scene"]}
          </div>
        </div>
      )}

      <Timeline draft={draft} setDraft={setDraft} timeline={timeline} onActive={activate} activeUid={activeUid} />
    </div>
  );
}

type LeftTab = "scenes" | "script" | "visuals" | "audio" | "post";
type RightTab = "scene" | "captions" | "export";

const LEFT_TABS: { value: LeftTab; label: string; icon: ReactNode }[] = [
  { value: "scenes", label: "Scenes", icon: <ListVideo className="size-4" /> },
  { value: "script", label: "Script", icon: <ScrollText className="size-4" /> },
  { value: "visuals", label: "Visuals", icon: <Palette className="size-4" /> },
  { value: "audio", label: "Audio", icon: <AudioLines className="size-4" /> },
  { value: "post", label: "Post", icon: <Send className="size-4" /> },
];
const RIGHT_TABS: { value: RightTab; label: string; icon: ReactNode }[] = [
  { value: "scene", label: "Scene", icon: <SlidersHorizontal className="size-4" /> },
  { value: "captions", label: "Captions", icon: <Captions className="size-4" /> },
  { value: "export", label: "Export", icon: <Share2 className="size-4" /> },
];

/** Compact icon tabs along the top of an editor panel. */
function PanelTabs<T extends string>({
  value,
  onChange,
  items,
  label,
}: {
  value: T;
  onChange: (v: T) => void;
  items: { value: T; label: string; icon: ReactNode }[];
  label: string;
}) {
  return (
    <div role="tablist" aria-label={label} className="flex shrink-0 overflow-x-auto border-b border-line bg-panel px-1">
      {items.map((it) => {
        const active = it.value === value;
        return (
          <button
            key={it.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(it.value)}
            className={`-mb-px flex min-w-[56px] flex-1 cursor-pointer flex-col items-center gap-0.5 border-b-2 bg-transparent px-1 pt-2 pb-1.5 text-2xs font-semibold transition-colors ${
              active ? "border-cobalt text-ink" : "border-transparent text-ink-soft hover:text-ink"
            }`}
          >
            {it.icon}
            <span className="truncate">{it.label}</span>
          </button>
        );
      })}
    </div>
  );
}

/** Whether the window is at least `px` wide (the editor's three panels need room; below that they stack). */
function useMinWidth(px: number) {
  return useSyncExternalStore(
    (onChange) => {
      const query = window.matchMedia(`(min-width: ${px}px)`);
      query.addEventListener("change", onChange);
      return () => query.removeEventListener("change", onChange);
    },
    () => window.matchMedia(`(min-width: ${px}px)`).matches,
    () => true,
  );
}

function SceneThumb({ media }: { media: string }) {
  if (!media)
    return (
      <span className="grid h-full w-full place-items-center text-white/50">
        <ImageIcon className="size-3.5" />
      </span>
    );
  return isImagePath(media) ? (
    // eslint-disable-next-line @next/next/no-img-element -- local engine file
    <img src={fileUrl(media)} alt="" className="h-full w-full object-cover" />
  ) : (
    <video src={`${fileUrl(media)}#t=0.5`} muted playsInline preload="metadata" className="h-full w-full object-cover" />
  );
}

/** The scenes as a compact list, like an editor's media bin: click one to edit it, drag to reorder. */
function SceneBin({
  scenes,
  lang,
  activeUid,
  lengths,
  onActive,
  onMove,
  onReorder,
  onRemove,
  onAdd,
}: {
  scenes: DraftScene[];
  lang: Lang;
  activeUid: string | null;
  lengths: Record<string, number>;
  onActive: (uid: string) => void;
  onMove: (i: number, dir: -1 | 1) => void;
  onReorder: (from: number, to: number) => void;
  onRemove: (i: number) => void;
  onAdd: () => void;
}) {
  const [dragging, setDragging] = useState<number | null>(null);
  const [over, setOver] = useState<number | null>(null);
  return (
    <div className="grid gap-2 p-2">
      <ol className="m-0 grid list-none gap-1 p-0">
        {scenes.map((s, i) => {
          const active = s.uid === activeUid;
          return (
            <li
              key={s.uid}
              draggable
              onDragStart={(e) => {
                setDragging(i);
                e.dataTransfer.effectAllowed = "move";
              }}
              onDragOver={(e) => {
                if (dragging === null) return;
                e.preventDefault();
                setOver(i);
              }}
              onDrop={(e) => {
                e.preventDefault();
                if (dragging !== null && dragging !== i) onReorder(dragging, i);
                setDragging(null);
                setOver(null);
              }}
              onDragEnd={() => {
                setDragging(null);
                setOver(null);
              }}
              className={`group relative rounded-lg ${dragging === i ? "opacity-50" : ""} ${over === i && dragging !== i ? "ring-2 ring-cobalt/60" : ""}`}
            >
              <button
                type="button"
                onClick={() => onActive(s.uid)}
                aria-current={active ? "true" : undefined}
                className={`flex w-full cursor-pointer items-start gap-2.5 rounded-lg border p-1.5 text-left transition-colors ${
                  active ? "border-cobalt/60 bg-cobalt/[0.08]" : "border-transparent bg-transparent hover:bg-ink/[0.04]"
                }`}
              >
                <span className="relative aspect-[9/16] w-10 shrink-0 overflow-hidden rounded bg-media">
                  <SceneThumb media={s.media} />
                </span>
                <span className="grid min-w-0 flex-1 gap-0.5">
                  <span className="flex items-center gap-1.5 text-sm font-bold text-ink">
                    Scene {i + 1}
                    {i === 0 && <Chip tone="caption">Hook</Chip>}
                    <span className="ml-auto font-mono text-2xs font-normal text-ink-soft tabular-nums">{lengths[s.uid] ? `${lengths[s.uid].toFixed(1)}s` : ""}</span>
                  </span>
                  <span lang={lang} className="line-clamp-2 text-sm leading-snug text-ink-soft">
                    {s.narration.trim() || <em>No voiceover</em>}
                  </span>
                  {s.on_screen_text.trim() && (
                    <span lang={lang} className="truncate text-2xs font-semibold tracking-wide text-ink-soft/80 uppercase">
                      {s.on_screen_text}
                    </span>
                  )}
                </span>
              </button>
              <div className="absolute right-1 bottom-1 hidden items-center gap-0.5 rounded-md bg-panel shadow-sm group-focus-within:flex group-hover:flex">
                <IconButton label="Move scene up" onClick={() => onMove(i, -1)} disabled={i === 0}>
                  <ArrowUp className="size-3.5" />
                </IconButton>
                <IconButton label="Move scene down" onClick={() => onMove(i, 1)} disabled={i === scenes.length - 1}>
                  <ArrowDown className="size-3.5" />
                </IconButton>
                <IconButton label="Remove scene" tone="danger" onClick={() => onRemove(i)} disabled={scenes.length === 1}>
                  <Trash2 className="size-3.5" />
                </IconButton>
              </div>
            </li>
          );
        })}
      </ol>
      <Button size="sm" variant="secondary" icon={<Plus className="size-3.5" />} onClick={onAdd} className="border-dashed">
        Add scene
      </Button>
    </div>
  );
}
