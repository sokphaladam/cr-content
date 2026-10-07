"use client";

import { ArrowDown, ArrowUp, ImageIcon, Pause, Play, Search, Sparkles, Trash2, Upload, X } from "lucide-react";
import { useId, useRef, useState } from "react";
import { api, fileUrl, type Lang, type Scene, type StockResult } from "@/lib/api";
import { isImagePath } from "@/lib/format";
import { Button, Chip, IconButton, Segmented, Spinner } from "./ui";

export type DraftScene = Scene & { uid: string };

function MediaSlot({ media, onClick }: { media: string; onClick: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  if (!media) {
    return (
      <button
        type="button"
        onClick={onClick}
        title="Footage is picked automatically from the search words"
        aria-label="Choose background for this scene"
        className="grid aspect-[9/16] w-full cursor-pointer place-items-center rounded-lg border border-dashed border-ink-soft/50 bg-paper p-0 text-ink-soft transition-colors hover:border-cobalt hover:text-cobalt"
      >
        <span className="grid justify-items-center gap-1 text-[11px] font-semibold">
          <ImageIcon className="size-4" aria-hidden />
          Auto
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
      className="relative aspect-[9/16] w-full cursor-pointer overflow-hidden rounded-lg border-0 bg-ink p-0 ring-cobalt hover:ring-2"
    >
      {isImagePath(media) ? (
        // eslint-disable-next-line @next/next/no-img-element -- local engine file, not a Next-optimizable asset
        <img src={url} alt="" className="block h-full w-full object-cover" />
      ) : (
        <video ref={video} src={`${url}#t=0.5`} muted playsInline preload="metadata" className="block h-full w-full object-cover" />
      )}
      <span className="absolute bottom-1 left-1">
        <Chip tone="caption">{isImagePath(media) ? "Photo" : "Video"}</Chip>
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
    <div className="grid gap-3 rounded-xl border border-line bg-paper/70 p-3">
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
            <input aria-label="Search footage" className="field-input h-8 py-0 pl-8 text-[13px]" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <Button size="sm" type="submit">
            Search
          </Button>
        </form>
        <Button size="sm" variant="ghost" icon={<Sparkles className="size-3.5" />} onClick={askIdeas} loading={ideasBusy}>
          Ideas
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
              className="h-7 cursor-pointer rounded-full border border-line bg-panel px-3 text-[12.5px] font-medium text-ink hover:border-cobalt hover:text-cobalt"
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
                className="relative grid aspect-[9/16] w-full cursor-pointer place-items-center overflow-hidden rounded-lg border-2 border-transparent bg-ink bg-cover bg-center p-0 transition hover:border-cobalt focus-visible:border-cobalt disabled:cursor-progress"
              >
                {picking === r.id && (
                  <span className="grid size-8 place-items-center rounded-full bg-black/60 text-white">
                    <Spinner />
                  </span>
                )}
                {r.kind === "video" && (
                  <span className="absolute right-1 bottom-1 rounded bg-black/65 px-1 py-0.5 text-[10.5px] leading-none text-white">{r.duration}s</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="m-0 text-xs text-ink-soft">Free stock media. Click one to use it for this scene.</p>
    </div>
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
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [status, setStatusState] = useState<{ text: string; error?: boolean }>({ text: "" });
  const setStatus = (text: string, error = false) => setStatusState({ text, error });
  const finder = useFinder(setStatus);
  const hook = index === 0;

  function togglePicker() {
    if (pickerOpen) return setPickerOpen(false);
    setPickerOpen(true);
    if (finder.results === null && scene.visual_query.trim()) {
      finder.setQ(scene.visual_query);
      void finder.search(scene.visual_query, finder.kind);
    } else if (!finder.q) {
      finder.setQ(scene.visual_query);
    }
  }

  async function upload(file: File) {
    setStatus(`Uploading ${file.name}…`);
    try {
      const m = await api.upload(file);
      onChange({ media: m.media });
      setStatus(`${m.kind === "photo" ? "Photo" : "Video"} uploaded.`);
    } catch (err) {
      setStatus((err as Error).message, true);
    }
  }

  const ListenIcon = listenState === "loading" ? Spinner : listenState === "playing" ? Pause : Play;

  return (
    <li
      onFocusCapture={onActivate}
      onPointerDown={onActivate}
      className={`group grid grid-cols-[64px_minmax(0,1fr)] gap-x-4 gap-y-3 rounded-xl border bg-panel p-4 transition-shadow sm:grid-cols-[76px_minmax(0,1fr)] ${
        active ? "border-cobalt/60 shadow-[0_0_0_3px_rgb(47_79_216/0.12)]" : "border-line hover:border-ink-soft/40"
      }`}
    >
      <div className="grid content-start gap-2">
        <MediaSlot media={scene.media} onClick={togglePicker} />
      </div>

      <div className="grid min-w-0 content-start gap-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-display text-[15px] font-extrabold text-ink">Scene {index + 1}</span>
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
            className="field-input field-sizing-content min-h-[68px] resize-none text-[15px] leading-relaxed"
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="grid gap-1.5">
            <label className="field-label" htmlFor={`headline-${scene.uid}`}>
              Headline <span className="font-normal text-ink-soft/80">optional</span>
            </label>
            <input id={`headline-${scene.uid}`} lang={lang} className="field-input h-9 py-0 text-[13.5px]" value={scene.on_screen_text} onChange={(e) => onChange({ on_screen_text: e.target.value })} placeholder="Text at the top" />
          </div>
          <div className="grid gap-1.5">
            <label className="field-label" htmlFor={`visual-${scene.uid}`}>
              Footage search
            </label>
            <input id={`visual-${scene.uid}`} className="field-input h-9 py-0 text-[13.5px]" value={scene.visual_query} onChange={(e) => onChange({ visual_query: e.target.value })} placeholder="e.g. octopus underwater" />
          </div>
        </div>

        <div className="-ml-2.5 flex flex-wrap items-center gap-1">
          <Button size="sm" variant="ghost" onClick={onListen} aria-label={`Listen to scene ${index + 1}`} icon={<ListenIcon className={listenState === "loading" ? "size-3.5" : "size-3.5 fill-current"} />}>
            {listenState === "playing" ? "Stop" : "Listen"}
          </Button>
          <Button size="sm" variant="ghost" onClick={togglePicker} icon={<Search className="size-3.5" />} aria-expanded={pickerOpen}>
            Find footage
          </Button>
          <label className={`relative cursor-pointer`}>
            <span className="inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-[13px] font-semibold text-ink-soft transition-colors hover:bg-ink/[0.05] hover:text-ink">
              <Upload className="size-3.5" aria-hidden />
              Upload
            </span>
            <input
              type="file"
              className="sr-only"
              accept="video/mp4,video/quicktime,video/webm,image/jpeg,image/png,image/webp"
              onChange={(e) => {
                const f = e.target.files?.[0];
                e.target.value = "";
                if (f) void upload(f);
              }}
            />
          </label>
          {scene.media && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                onChange({ media: "" });
                setStatus("");
              }}
            >
              Use auto footage
            </Button>
          )}
          {status.text && (
            <span role="status" className={`ml-1 text-[12.5px] ${status.error ? "text-danger" : "text-ink-soft"}`}>
              {status.text}
            </span>
          )}
        </div>
      </div>

      {pickerOpen && (
        <div className="col-span-2">
          <Picker
            finder={finder}
            narration={scene.narration}
            setStatus={setStatus}
            onClose={() => setPickerOpen(false)}
            onPicked={(media, query) => {
              onChange({ media, visual_query: query || scene.visual_query });
              setPickerOpen(false);
            }}
          />
        </div>
      )}
    </li>
  );
}
