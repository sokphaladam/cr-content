"use client";

import { ArrowDown, ArrowUp, Clapperboard, Film, ImageIcon, Palette, Pause, Play, Search, Sparkles, Trash2, Type, Upload, X } from "lucide-react";
import { useId, useRef, useState } from "react";
import { api, fileUrl, type ArtStatus, type ArtStyle, type ArtSubject, type BRoll, type Lang, type Scene, type StockResult, type TextOverlay } from "@/lib/api";
import { isImagePath } from "@/lib/format";
import { ScenePicture } from "./ArtControls";
import { Button, Chip, IconButton, Segmented, Spinner } from "./ui";

export type DraftScene = Scene & { uid: string };

function MediaSlot({ media, onClick, ai = false }: { media: string; onClick: () => void; ai?: boolean }) {
  const video = useRef<HTMLVideoElement>(null);
  if (!media) {
    return (
      <button
        type="button"
        onClick={onClick}
        title={ai ? "An AI picture is drawn for this scene when you render" : "Footage is picked automatically from the search words"}
        aria-label="Choose background for this scene"
        className="grid aspect-[9/16] w-full cursor-pointer place-items-center rounded-lg border border-dashed border-ink-soft/50 bg-paper p-0 text-ink-soft transition-colors hover:border-cobalt hover:text-cobalt"
      >
        <span className="grid justify-items-center gap-1 text-xs font-semibold">
          {ai ? <Sparkles className="size-4" aria-hidden /> : <ImageIcon className="size-4" aria-hidden />}
          {ai ? "AI" : "Auto"}
        </span>
      </button>
    );
  }
  const url = fileUrl(media);
  return (
    <button
      type="button"
      onClick={onClick}
      title="Change background"
      aria-label="Change background for this scene"
      onMouseEnter={() => video.current?.play().catch(() => {})}
      onMouseLeave={() => video.current?.pause()}
      className="relative aspect-[9/16] w-full cursor-pointer overflow-hidden rounded-lg border-0 bg-media p-0 ring-cobalt hover:ring-2"
    >
      {isImagePath(media) ? (
        // eslint-disable-next-line @next/next/no-img-element -- local engine file, not a Next-optimizable asset
        <img src={url} alt="" className="block h-full w-full object-cover" />
      ) : (
        <video ref={video} src={`${url}#t=0.5`} muted playsInline preload="metadata" className="block h-full w-full object-cover" />
      )}
      <span className="absolute bottom-1 left-1">
        <Chip tone="caption">{media.startsWith("cache/gen/") ? "AI" : isImagePath(media) ? "Photo" : "Video"}</Chip>
      </span>
    </button>
  );
}

interface Finder {
  q: string;
  setQ: (q: string) => void;
  kind: "video" | "photo";
  setKind: (k: "video" | "photo") => void;
  results: StockResult[] | null;
  search: (query?: string, kind?: "video" | "photo") => Promise<void>;
}

/** Stock search state for one scene. */
function useFinder(setStatus: (text: string, error?: boolean) => void): Finder {
  const [q, setQ] = useState("");
  const [kind, setKind] = useState<"video" | "photo">("video");
  const [results, setResults] = useState<StockResult[] | null>(null);

  async function search(query = q, k = kind) {
    if (!query.trim()) return;
    setResults(null);
    setStatus("Searching…");
    try {
      const data = await api.footage(query.trim(), k);
      setResults(data.results);
      setStatus(data.results.length ? "" : "Nothing found. Try simpler words, or ask Claude for ideas.");
    } catch (err) {
      setResults([]);
      setStatus((err as Error).message, true);
    }
  }

  return { q, setQ, kind, setKind, results, search };
}

function Picker({
  finder,
  narration,
  onPicked,
  onClose,
  setStatus,
}: {
  finder: Finder;
  narration: string;
  onPicked: (media: string, query: string) => void;
  onClose: () => void;
  setStatus: (text: string, error?: boolean) => void;
}) {
  const { q, setQ, kind, setKind, results, search } = finder;
  const [ideas, setIdeas] = useState<string[]>([]);
  const [ideasBusy, setIdeasBusy] = useState(false);
  const [picking, setPicking] = useState<number | null>(null);
  const [designing, setDesigning] = useState<"still" | "motion" | null>(null);
  const radioName = useId();

  async function pick(r: StockResult) {
    setPicking(r.id);
    setStatus("Downloading…");
    try {
      const m = await api.pick(r);
      onPicked(m.media, q.trim());
      setStatus(`${m.kind === "photo" ? "Photo" : "Video"} set for this scene.`);
    } catch (err) {
      setStatus((err as Error).message, true);
    } finally {
      setPicking(null);
    }
  }

  async function design(animate: boolean) {
    setDesigning(animate ? "motion" : "still");
    setStatus(animate ? "Claude is animating this background, then it's rendered to video… about two minutes." : "Claude is drawing this background… about a minute.");
    try {
      const m = await api.designFootage(q.trim(), narration, animate);
      onPicked(m.media, q.trim());
      setStatus(animate ? "Claude's animated background set for this scene." : "Claude's artwork set for this scene.");
    } catch (err) {
      setStatus((err as Error).message, true);
    } finally {
      setDesigning(null);
    }
  }

  async function askIdeas() {
    setIdeasBusy(true);
    try {
      setIdeas((await api.ideas(narration, q)).queries);
    } catch (err) {
      setStatus((err as Error).message, true);
    } finally {
      setIdeasBusy(false);
    }
  }

  return (
    <div className="grid gap-3 well p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Segmented
          size="sm"
          name={radioName}
          value={kind}
          onChange={(k) => {
            setKind(k);
            void search(q, k);
          }}
          options={[
            { value: "video", label: "Videos" },
            { value: "photo", label: "Photos" },
          ]}
        />
        <form
          className="flex min-w-[200px] flex-1 items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void search();
          }}
        >
          <div className="relative flex-1">
            <Search aria-hidden className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-ink-soft" />
            <input aria-label="Search footage" className="field-input h-8 py-0 pl-8 text-base" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <Button size="sm" type="submit">
            Search
          </Button>
        </form>
        <Button size="sm" variant="ghost" icon={<Sparkles className="size-3.5" />} onClick={askIdeas} loading={ideasBusy}>
          Ideas
        </Button>
        <Button
          size="sm"
          variant="ghost"
          icon={<Palette className="size-3.5" />}
          onClick={() => design(false)}
          loading={designing === "still"}
          disabled={picking !== null || designing !== null || (!q.trim() && !narration.trim())}
          title="Claude draws an original background from the search words and the narration"
        >
          Design with Claude
        </Button>
        <Button
          size="sm"
          variant="ghost"
          icon={<Clapperboard className="size-3.5" />}
          onClick={() => design(true)}
          loading={designing === "motion"}
          disabled={picking !== null || designing !== null || (!q.trim() && !narration.trim())}
          title="Claude designs a moving background (drifting light, particles, parallax) and renders it as a looping video clip"
        >
          Animate
        </Button>
        <IconButton label="Close footage search" onClick={onClose}>
          <X className="size-4" />
        </IconButton>
      </div>

      {ideas.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {ideas.map((idea) => (
            <button
              key={idea}
              type="button"
              onClick={() => {
                setQ(idea);
                void search(idea);
              }}
              className="h-7 cursor-pointer rounded-full border border-line bg-panel px-3 text-sm font-medium text-ink hover:border-cobalt hover:text-cobalt"
            >
              {idea}
            </button>
          ))}
        </div>
      )}

      {results === null && q && (
        <div className="grid h-24 place-items-center text-ink-soft">
          <Spinner />
        </div>
      )}
      {results && results.length > 0 && (
        <ul className="m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(76px,1fr))] gap-1.5 p-0">
          {results.map((r) => (
            <li key={`${r.source}-${r.id}`}>
              <button
                type="button"
                onClick={() => pick(r)}
                disabled={picking !== null}
                aria-label={`Use this ${r.kind}${r.author ? ` by ${r.author}` : ""}`}
                style={{ backgroundImage: `url('${r.thumb}')` }}
                className="relative grid aspect-[9/16] w-full cursor-pointer place-items-center overflow-hidden rounded-lg border-2 border-transparent bg-media bg-cover bg-center p-0 transition hover:border-cobalt focus-visible:border-cobalt disabled:cursor-progress"
              >
                {picking === r.id && (
                  <span className="grid size-8 place-items-center rounded-full bg-black/60 text-white">
                    <Spinner />
                  </span>
                )}
                {r.kind === "video" && (
                  <span className="absolute right-1 bottom-1 rounded bg-black/65 px-1 py-0.5 text-2xs leading-none text-white">{r.duration}s</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="m-0 text-sm text-ink-soft">Free stock media: click one to use it for this scene. Or let Claude draw an original background, still or animated.</p>
    </div>
  );
}

type PickTarget = "media" | "media2" | "broll";
const PICK_TITLE: Record<PickTarget, string> = { media: "this scene", media2: "the bottom clip", broll: "a cutaway" };

const NEW_TEXT: TextOverlay = { text: "", at: 0, duration: 2, x: 0.5, y: 0.4, size: "m", color: "#FFFFFF", box: false };

/** Seconds field for an overlay's start or length. */
function SecondsInput({ label, value, onChange, min = 0 }: { label: string; value: number; onChange: (v: number) => void; min?: number }) {
  return (
    <label className="flex items-center gap-1 text-sm text-ink-soft">
      {label}
      <input
        type="number"
        min={min}
        step={0.1}
        value={Number(value.toFixed(2))}
        onChange={(e) => onChange(Math.max(min, Number(e.target.value) || 0))}
        className="field-input h-7 w-16 px-1.5 py-0 text-sm tabular-nums"
      />
      s
    </label>
  );
}

export function SceneCard({
  scene,
  index,
  total,
  lang,
  active,
  listenState,
  onActivate,
  onChange,
  onMove,
  onRemove,
  onListen,
  artStyle = "",
  artStatus = null,
  artSubject,
  usedMedia,
}: {
  scene: DraftScene;
  index: number;
  total: number;
  lang: Lang;
  active: boolean;
  listenState: "idle" | "loading" | "playing";
  onActivate: () => void;
  onChange: (patch: Partial<Scene>) => void;
  onMove: (dir: -1 | 1) => void;
  onRemove: () => void;
  onListen: () => void;
  artStyle?: ArtStyle | ""; // the draft draws its scenes in this look ("" = stock footage)
  artSubject?: ArtSubject; // the video's real subject, checked in every picture that shows it
  usedMedia?: string[]; // what the other scenes show
  artStatus?: ArtStatus | null;
}) {
  const [pickFor, setPickFor] = useState<PickTarget | null>(null);
  const [status, setStatusState] = useState<{ text: string; error?: boolean }>({ text: "" });
  const setStatus = (text: string, error = false) => setStatusState({ text, error });
  const finder = useFinder(setStatus);
  const hook = index === 0;
  const layout = scene.layout ?? "fill";
  const broll = scene.broll ?? [];
  const texts = scene.texts ?? [];
  const layoutName = useId();

  function openPicker(target: PickTarget) {
    if (pickFor === target) return setPickFor(null);
    setPickFor(target);
    if (finder.results === null && scene.visual_query.trim()) {
      finder.setQ(scene.visual_query);
      void finder.search(scene.visual_query, finder.kind);
    } else if (!finder.q) {
      finder.setQ(scene.visual_query);
    }
  }

  function picked(media: string, query: string) {
    if (pickFor === "media2") onChange({ media2: media });
    else if (pickFor === "broll") onChange({ broll: [...broll, { media, at: 0.5, duration: 2 }] });
    else onChange({ media, visual_query: query || scene.visual_query, media_start: 0 });
    setPickFor(null);
  }

  async function upload(file: File, target: PickTarget) {
    setStatus(`Uploading ${file.name}…`);
    try {
      const m = await api.upload(file);
      if (target === "broll") onChange({ broll: [...broll, { media: m.media, at: 0.5, duration: 2 }] });
      else onChange({ media: m.media, media_start: 0 });
      setStatus(`${m.kind === "photo" ? "Photo" : "Video"} uploaded.`);
    } catch (err) {
      setStatus((err as Error).message, true);
    }
  }

  const setBroll = (k: number, patch: Partial<BRoll>) => onChange({ broll: broll.map((b, j) => (j === k ? { ...b, ...patch } : b)) });
  const setText = (k: number, patch: Partial<TextOverlay>) => onChange({ texts: texts.map((t, j) => (j === k ? { ...t, ...patch } : t)) });
  const ListenIcon = listenState === "loading" ? Spinner : listenState === "playing" ? Pause : Play;
  const uploadButton = (target: PickTarget, label: string) => (
    <label className="relative cursor-pointer">
      <span className="inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-base font-semibold text-ink-soft transition-colors hover:bg-ink/[0.05] hover:text-ink">
        <Upload className="size-3.5" aria-hidden />
        {label}
      </span>
      <input
        type="file"
        className="sr-only"
        accept="video/mp4,video/quicktime,video/webm,image/jpeg,image/png,image/webp"
        onChange={(e) => {
          const f = e.target.files?.[0];
          e.target.value = "";
          if (f) void upload(f, target);
        }}
      />
    </label>
  );

  return (
    <li
      onFocusCapture={onActivate}
      onPointerDown={onActivate}
      className={`@container group grid grid-cols-[64px_minmax(0,1fr)] gap-x-3 gap-y-3 rounded-xl border bg-panel p-3 transition-shadow ${
        active ? "border-cobalt/60 ring-3 ring-cobalt/15" : "border-line hover:border-line-strong"
      }`}
    >
      <div className="grid content-start gap-2">
        <MediaSlot media={scene.media} ai={!!artStyle} onClick={() => openPicker("media")} />
        {layout === "split" && (
          <>
            <MediaSlot media={scene.media2 ?? ""} onClick={() => openPicker("media2")} />
            <span className="text-center text-xs text-ink-soft">Bottom</span>
          </>
        )}
      </div>

      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-display text-lg font-extrabold text-ink">Scene {index + 1}</span>
            {hook && <Chip tone="caption">Hook</Chip>}
          </div>
          <div className="flex items-center gap-0.5 opacity-70 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
            <IconButton label="Move scene up" onClick={() => onMove(-1)} disabled={index === 0}>
              <ArrowUp className="size-4" />
            </IconButton>
            <IconButton label="Move scene down" onClick={() => onMove(1)} disabled={index === total - 1}>
              <ArrowDown className="size-4" />
            </IconButton>
            <IconButton label="Remove scene" tone="danger" onClick={onRemove} disabled={total === 1}>
              <Trash2 className="size-4" />
            </IconButton>
          </div>
        </div>

        <div className="grid gap-1.5">
          <label className="field-label" htmlFor={`narration-${scene.uid}`}>
            Voiceover
          </label>
          <textarea
            id={`narration-${scene.uid}`}
            lang={lang}
            rows={2}
            value={scene.narration}
            onChange={(e) => onChange({ narration: e.target.value })}
            placeholder="What the voice says in this scene"
            className="field-input field-sizing-content min-h-[68px] resize-none text-lg leading-relaxed"
          />
        </div>

        <div className="grid gap-3 @sm:grid-cols-2">
          <div className="grid gap-1.5">
            <label className="field-label" htmlFor={`headline-${scene.uid}`}>
              Headline <span className="font-normal text-ink-soft/80">optional</span>
            </label>
            <input id={`headline-${scene.uid}`} lang={lang} className="field-input h-9 py-0 text-base" value={scene.on_screen_text} onChange={(e) => onChange({ on_screen_text: e.target.value })} placeholder="Text at the top" />
          </div>
          <div className="grid gap-1.5">
            <label className="field-label" htmlFor={`visual-${scene.uid}`}>
              Footage search
            </label>
            <input id={`visual-${scene.uid}`} className="field-input h-9 py-0 text-base" value={scene.visual_query} onChange={(e) => onChange({ visual_query: e.target.value })} placeholder="e.g. octopus underwater" />
          </div>
        </div>

        {artStyle && (!scene.media || scene.media.startsWith("cache/gen/")) && (
          <ScenePicture scene={scene} style={artStyle} status={artStatus} subject={artSubject} used={usedMedia} onChange={onChange} />
        )}

        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <span className="field-label">Layout</span>
          <Segmented
            name={layoutName}
            size="sm"
            value={layout}
            onChange={(v) => onChange({ layout: v })}
            options={[
              { value: "fill", label: "Fill" },
              { value: "fit", label: "Fit" },
              { value: "split", label: "Split" },
            ]}
          />
          {(scene.media_start ?? 0) > 0 && (
            <button type="button" className="cursor-pointer bg-transparent p-0 text-sm text-ink-soft underline" onClick={() => onChange({ media_start: 0 })}>
              Starts {scene.media_start!.toFixed(1)}s into the clip. Reset
            </button>
          )}
        </div>

        <div className="-ml-2.5 flex flex-wrap items-center gap-1">
          <Button size="sm" variant="ghost" onClick={onListen} aria-label={`Listen to scene ${index + 1}`} icon={<ListenIcon className={listenState === "loading" ? "size-3.5" : "size-3.5 fill-current"} />}>
            {listenState === "playing" ? "Stop" : "Listen"}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => openPicker("media")} icon={<Search className="size-3.5" />} aria-expanded={pickFor === "media"}>
            Find footage
          </Button>
          {uploadButton("media", "Upload")}
          {scene.media && !scene.media.startsWith("cache/gen/") && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                onChange({ media: "", media_start: 0 });
                setStatus("");
              }}
            >
              {artStyle ? "Use AI picture" : "Use auto footage"}
            </Button>
          )}
          {layout === "split" && scene.media2 && (
            <Button size="sm" variant="ghost" onClick={() => onChange({ media2: "" })}>
              Auto bottom clip
            </Button>
          )}
          <Button size="sm" variant="ghost" icon={<Film className="size-3.5" />} onClick={() => openPicker("broll")} aria-expanded={pickFor === "broll"}>
            Add B-roll
          </Button>
          <Button size="sm" variant="ghost" icon={<Type className="size-3.5" />} onClick={() => onChange({ texts: [...texts, { ...NEW_TEXT }] })}>
            Add text
          </Button>
          {status.text && (
            <span role="status" className={`ml-1 text-sm ${status.error ? "text-danger" : "text-ink-soft"}`}>
              {status.text}
            </span>
          )}
        </div>

        {broll.length > 0 && (
          <ul aria-label="B-roll" className="m-0 grid list-none gap-1.5 p-0">
            {broll.map((b, k) => (
              <li key={k} className="flex flex-wrap items-center gap-2 rounded-lg bg-sunken px-2 py-1.5">
                <span className="h-9 w-6 shrink-0 overflow-hidden rounded bg-media">
                  {isImagePath(b.media) ? (
                    // eslint-disable-next-line @next/next/no-img-element -- local engine file
                    <img src={fileUrl(b.media)} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <video src={`${fileUrl(b.media)}#t=0.5`} muted preload="metadata" className="h-full w-full object-cover" />
                  )}
                </span>
                <span className="text-sm font-semibold">B-roll</span>
                <SecondsInput label="at" value={b.at} onChange={(v) => setBroll(k, { at: v })} />
                <SecondsInput label="for" value={b.duration} min={0.2} onChange={(v) => setBroll(k, { duration: v })} />
                <IconButton label="Remove this B-roll" tone="danger" onClick={() => onChange({ broll: broll.filter((_, j) => j !== k) })}>
                  <X className="size-3.5" />
                </IconButton>
              </li>
            ))}
          </ul>
        )}

        {texts.length > 0 && (
          <ul aria-label="Text on screen" className="m-0 grid list-none gap-1.5 p-0">
            {texts.map((t, k) => (
              <li key={k} className="grid gap-1.5 rounded-lg bg-sunken px-2 py-1.5">
                <div className="flex items-center gap-2">
                  <input
                    lang={lang}
                    aria-label="Text"
                    autoFocus={!t.text}
                    className="field-input h-8 min-w-0 flex-1 py-0 text-base"
                    value={t.text}
                    placeholder="Text on screen"
                    onChange={(e) => setText(k, { text: e.target.value })}
                  />
                  <input type="color" aria-label="Text colour" className="size-8 cursor-pointer rounded border border-line bg-panel p-0.5" value={t.color} onChange={(e) => setText(k, { color: e.target.value.toUpperCase() })} />
                  <IconButton label="Remove this text" tone="danger" onClick={() => onChange({ texts: texts.filter((_, j) => j !== k) })}>
                    <X className="size-3.5" />
                  </IconButton>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <SecondsInput label="at" value={t.at} onChange={(v) => setText(k, { at: v })} />
                  <SecondsInput label="for" value={t.duration} min={0.2} onChange={(v) => setText(k, { duration: v })} />
                  <select aria-label="Text size" className="field-input h-7 w-auto py-0 text-sm" value={t.size} onChange={(e) => setText(k, { size: e.target.value as TextOverlay["size"] })}>
                    <option value="s">Small</option>
                    <option value="m">Medium</option>
                    <option value="l">Large</option>
                  </select>
                  <label className="flex items-center gap-1 text-sm text-ink-soft">
                    <input type="checkbox" className="size-3.5 accent-cobalt" checked={t.box} onChange={(e) => setText(k, { box: e.target.checked })} />
                    Box
                  </label>
                  <span className="text-xs text-ink-soft">Drag it on the preview to place it.</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {pickFor && (
        <div className="col-span-2 grid gap-1.5">
          <p className="m-0 text-sm font-semibold text-ink-soft">
            Footage for {PICK_TITLE[pickFor]}
            {pickFor === "broll" && <span className="ml-2 inline-block align-middle">{uploadButton("broll", "Upload a cutaway")}</span>}
          </p>
          <Picker finder={finder} narration={scene.narration} setStatus={setStatus} onClose={() => setPickFor(null)} onPicked={picked} />
        </div>
      )}
    </li>
  );
}
