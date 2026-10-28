"use client";

import { Copy, Download, FileText, Film, MonitorPlay, Ellipsis, Music, Plus, Search, SquarePen, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { API_BASE, fileUrl, outputUrl, type DraftSummary, type VideoSummary } from "@/lib/api";
import { isImagePath, langCode } from "@/lib/format";
import { Button, Tabs } from "./ui";

export type LibraryTab = "drafts" | "videos";
/** short: vertical 9:16 (TikTok, Reels, Shorts); video: landscape 16:9 (YouTube); song: lyrics and audio, no video yet */
type ItemType = "short" | "video" | "song";
type Filter = "all" | ItemType;

const TYPE_LABEL: Record<ItemType, string> = { short: "Short", video: "Video", song: "Song" };
const FILTER_LABEL: Record<Filter, string> = { all: "All", short: "Shorts", video: "Videos", song: "Songs" };

interface Item {
  key: string;
  type: ItemType;
  title: string;
  lang: string;
  when: string; // ISO date the item is grouped and sorted by
  detail: string;
  thumb?: string;
  musicVideo?: boolean;
  onClick: () => void;
  current: boolean;
  download?: { href: string; label: string };
  onDuplicate?: () => void;
  onDelete: () => void;
  deleteHint?: string; // what deleting leaves behind, shown on the confirm step
}

/** "⋯" button on a row: open, duplicate, download, delete (delete asks once more). The menu is position:fixed
 * so the scrolling list never clips it. */
export function RowMenu({ item }: { item: Pick<Item, "title" | "current" | "onClick" | "onDelete" | "deleteHint" | "onDuplicate" | "download"> }) {
  const [at, setAt] = useState<{ top: number; right: number; up: boolean } | null>(null);
  const [confirm, setConfirm] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const close = () => {
    setAt(null);
    setConfirm(false);
  };

  useEffect(() => {
    if (!at) return;
    menu.current?.querySelector<HTMLElement>("[role=menuitem]")?.focus();
    const onDown = (e: PointerEvent) => {
      if (!menu.current?.contains(e.target as Node) && !trigger.current?.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        close();
        trigger.current?.focus();
      } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const items = [...(menu.current?.querySelectorAll<HTMLElement>("[role=menuitem]") ?? [])];
        const i = items.indexOf(document.activeElement as HTMLElement);
        items[(i + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length]?.focus();
      }
    };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", close);
    window.addEventListener("scroll", close, true);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", close);
      window.removeEventListener("scroll", close, true);
    };
  }, [at]);

  const entry = "flex w-full cursor-pointer items-center gap-2 rounded-md border-0 bg-transparent px-2.5 py-1.5 text-left text-base no-underline";
  const run = (fn: () => void) => () => {
    close();
    fn();
  };

  return (
    <>
      <button
        ref={trigger}
        type="button"
        aria-label={`Actions for ${item.title}`}
        title="Actions"
        aria-haspopup="menu"
        aria-expanded={!!at}
        onClick={() => {
          if (at) return close();
          const r = trigger.current!.getBoundingClientRect();
          const up = r.bottom + 180 > window.innerHeight;
          setAt({ top: up ? r.top - 4 : r.bottom + 4, right: window.innerWidth - r.right, up });
        }}
        className={`absolute top-1.5 right-1.5 grid size-7 cursor-pointer place-items-center rounded-md border-0 text-ink-soft transition-opacity hover:bg-ink/[0.07] hover:text-ink ${
          at || item.current ? `opacity-100 ${at ? "bg-ink/[0.07]" : "bg-transparent"}` : "bg-transparent [@media(hover:hover)]:not-group-hover:not-group-focus-within:opacity-0"
        }`}
      >
        <Ellipsis className="size-4" />
      </button>
      {at && (
        <div
          ref={menu}
          role="menu"
          aria-label={`Actions for ${item.title}`}
          style={{ top: at.top, right: at.right, transform: at.up ? "translateY(-100%)" : undefined }}
          className="fixed z-50 grid w-[200px] gap-0.5 popover rounded-lg p-1"
        >
          <button type="button" role="menuitem" className={`${entry} text-ink hover:bg-ink/[0.05] focus-visible:bg-ink/[0.05]`} onClick={run(item.onClick)}>
            <SquarePen className="size-3.5 text-ink-soft" /> Open
          </button>
          {item.onDuplicate && (
            <button type="button" role="menuitem" className={`${entry} text-ink hover:bg-ink/[0.05] focus-visible:bg-ink/[0.05]`} onClick={run(item.onDuplicate)}>
              <Copy className="size-3.5 text-ink-soft" /> Duplicate
            </button>
          )}
          {item.download && (
            <a role="menuitem" href={item.download.href} className={`${entry} text-ink hover:bg-ink/[0.05] focus-visible:bg-ink/[0.05]`} onClick={() => close()}>
              <Download className="size-3.5 text-ink-soft" /> {item.download.label}
            </a>
          )}
          <div aria-hidden className="mx-1 my-0.5 h-px bg-line" />
          <button
            type="button"
            role="menuitem"
            title={item.deleteHint}
            className={`${entry} text-danger hover:bg-danger/[0.07] focus-visible:bg-danger/[0.07] ${confirm ? "bg-danger/[0.07] font-semibold" : ""}`}
            onClick={() => (confirm ? run(item.onDelete)() : setConfirm(true))}
          >
            <Trash2 className="size-3.5" /> {confirm ? "Click again to delete" : "Delete"}
          </button>
          {confirm && item.deleteHint && <p className="m-0 px-2.5 pt-0.5 pb-1.5 text-xs leading-snug text-ink-soft">{item.deleteHint}</p>}
        </div>
      )}
    </>
  );
}

/** "Today", "Yesterday", "Earlier this week", "October", "September 2025" */
function dateGroup(iso: string, now = new Date()): { key: string; label: string } {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return { key: "0", label: "Older" };
  const day = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const days = Math.round((day(now) - day(d)) / 86_400_000);
  if (days <= 0) return { key: "a", label: "Today" };
  if (days === 1) return { key: "b", label: "Yesterday" };
  const weekday = (now.getDay() + 6) % 7; // days since Monday
  if (days <= weekday) return { key: "c", label: "Earlier this week" };
  if (days <= weekday + 7) return { key: "d", label: "Last week" };
  const month = d.toLocaleDateString(undefined, d.getFullYear() === now.getFullYear() ? { month: "long" } : { month: "long", year: "numeric" });
  return { key: `m${d.getFullYear()}-${String(d.getMonth()).padStart(2, "0")}`, label: month };
}

/** Short time stamp next to an item; its date group already says the day: "14:05", "Mon", "Oct 6". */
function stamp(iso: string, now = new Date()): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const days = (now.getTime() - d.getTime()) / 86_400_000;
  if (d.toDateString() === now.toDateString() || days < 1.5) return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  if (days < 7) return d.toLocaleDateString(undefined, { weekday: "short" });
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function TypeIcon({ type, className = "size-4" }: { type: ItemType; className?: string }) {
  if (type === "song") return <Music className={className} />;
  if (type === "video") return <MonitorPlay className={className} />;
  return <Film className={className} />;
}

function Row({ item }: { item: Item }) {
  const landscape = item.type === "video";
  return (
    <li className="group relative">
      <button
        type="button"
        aria-current={item.current || undefined}
        onClick={item.onClick}
        className={`relative grid w-full cursor-pointer grid-cols-[52px_minmax(0,1fr)] items-center gap-3 rounded-lg border-0 py-1.5 pr-2 pl-2 text-left transition-colors ${
          item.current ? "bg-panel shadow-(--shadow-card)" : "bg-transparent hover:bg-ink/[0.04]"
        }`}
      >
        {item.current && <span aria-hidden className="absolute top-2 bottom-2 left-0 w-[3px] rounded-r bg-caption" />}
        <span className="grid h-[60px] place-items-center">
          <span
            className={`grid place-items-center overflow-hidden rounded-md bg-ink/[0.07] bg-cover bg-center text-ink-soft ${landscape ? "aspect-video w-[52px]" : "aspect-[9/16] w-[34px]"}`}
            style={item.thumb ? { backgroundImage: `url('${item.thumb}')` } : undefined}
          >
            {!item.thumb && <TypeIcon type={item.type} />}
          </span>
        </span>
        <span className="min-w-0">
          <span lang={item.lang} className="line-clamp-2 pr-6 text-base leading-snug font-semibold text-ink">
            {item.title}
          </span>
          <span className="mt-1 flex items-center gap-1.5 text-xs text-ink-soft">
            <span className="inline-flex items-center gap-1 font-semibold text-ink/75">
              <TypeIcon type={item.type} className="size-3" />
              {item.musicVideo ? "Music video" : TYPE_LABEL[item.type]}
            </span>
            <span lang={item.lang === "km" ? "km" : undefined} className="rounded bg-ink/[0.06] px-1 leading-4 font-semibold">
              {langCode(item.lang)}
            </span>
            {item.detail && <span className="truncate">{item.detail}</span>}
            <span className="ml-auto shrink-0 tabular-nums">{stamp(item.when)}</span>
          </span>
        </span>
      </button>
      <RowMenu item={item} />
    </li>
  );
}

export function Library({
  tab,
  onTab,
  drafts,
  videos,
  selectedDraft,
  selectedVideo,
  onSelectDraft,
  onSelectSong,
  onSelectVideo,
  onDuplicateDraft,
  onDeleteDraft,
  onDeleteVideo,
  onNew,
}: {
  tab: LibraryTab;
  onTab: (t: LibraryTab) => void;
  drafts: DraftSummary[] | null;
  videos: VideoSummary[] | null;
  selectedDraft: string | null;
  selectedVideo: string | null;
  onSelectDraft: (id: string) => void;
  onSelectSong: (name: string) => void;
  onSelectVideo: (name: string) => void;
  onDuplicateDraft: (id: string) => void;
  onDeleteDraft: (id: string) => void;
  onDeleteVideo: (name: string, isSong: boolean) => void;
  onNew: () => void;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");

  const items: Item[] | null = useMemo(() => {
    if (tab === "drafts") {
      return (
        drafts?.map((d): Item =>
          d.kind === "song"
            ? {
                key: d.id,
                type: "song",
                title: d.title,
                lang: d.lang,
                when: d.updated,
                detail: d.versions ? `${d.versions} video${d.versions === 1 ? "" : "s"}` : "no video yet",
                thumb: d.thumb ? `${outputUrl(d.thumb, "thumbnail.jpg")}?v=${d.thumb_v ?? 0}` : undefined,
                onClick: () => onSelectSong(d.id),
                current: d.id === selectedDraft,
                download: { href: `${API_BASE}/api/videos/${encodeURIComponent(d.id)}/song`, label: "Download song" },
                onDelete: () => onDeleteVideo(d.id, true),
                deleteHint: d.versions ? "Deletes the song and its timing. Its music videos stay in Videos." : undefined,
              }
            : {
                key: d.id,
                type: "short",
                title: d.title,
                lang: d.lang,
                when: d.updated,
                detail: `${d.scenes} scene${d.scenes === 1 ? "" : "s"}`,
                thumb: d.cover && isImagePath(d.cover) ? fileUrl(d.cover) : undefined,
                onClick: () => onSelectDraft(d.id),
                current: d.id === selectedDraft,
                onDuplicate: () => onDuplicateDraft(d.id),
                onDelete: () => onDeleteDraft(d.id),
              },
        ) ?? null
      );
    }
    return (
      videos?.map((v): Item => ({
        key: v.name,
        type: v.aspect === "16:9" ? "video" : "short",
        musicVideo: v.kind === "music_video",
        title: v.title,
        lang: v.lang,
        when: v.created,
        detail: v.video || v.audio ? "" : v.kind === "long_video" ? "storyboard" : v.kind === "short" ? "pre-flight" : "not rendered",
        thumb: v.thumb ? `${outputUrl(v.name, "thumbnail.jpg")}?v=${v.thumb_v}` : undefined,
        onClick: () => onSelectVideo(v.name),
        current: v.name === selectedVideo,
        download: v.video ? { href: `${API_BASE}/api/videos/${encodeURIComponent(v.name)}/download`, label: "Download video" } : undefined,
        onDelete: () => onDeleteVideo(v.name, v.kind === "song"),
        deleteHint: v.kind === "song" ? "Its music videos stay in Videos." : "Removes the video file and its thumbnail.",
      })) ?? null
    );
  }, [tab, drafts, videos, selectedDraft, selectedVideo, onSelectDraft, onSelectSong, onSelectVideo, onDuplicateDraft, onDeleteDraft, onDeleteVideo]);

  // only offer the types this list actually has
  const types = useMemo(() => (["short", "video", "song"] as ItemType[]).filter((t) => items?.some((i) => i.type === t)), [items]);
  const activeFilter: Filter = filter !== "all" && !types.includes(filter) ? "all" : filter;

  const groups = useMemo(() => {
    if (!items) return null;
    const q = query.trim().toLowerCase();
    const shown = items
      .filter((i) => (activeFilter === "all" || i.type === activeFilter) && (!q || i.title.toLowerCase().includes(q)))
      .sort((a, b) => (a.when < b.when ? 1 : -1));
    const out: { key: string; label: string; items: Item[] }[] = [];
    for (const item of shown) {
      const g = dateGroup(item.when);
      const last = out.at(-1);
      if (last?.key === g.key) last.items.push(item);
      else out.push({ ...g, items: [item] });
    }
    return out;
  }, [items, query, activeFilter]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="pane-header">
        <h2 className="pane-title m-0">Library</h2>
        <Button size="sm" variant="primary" icon={<Plus className="size-4" />} onClick={onNew}>
          New
        </Button>
      </div>
      <div className="grid gap-3 px-4 pt-3">
        <label className="relative block">
          <span className="sr-only">Search {tab}</span>
          <Search aria-hidden className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-ink-soft" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={tab === "drafts" ? "Search drafts" : "Search videos"}
            className="field-input h-9 py-0 pr-8 pl-8 text-base [&::-webkit-search-cancel-button]:hidden"
          />
          {query && (
            <button
              type="button"
              aria-label="Clear search"
              onClick={() => setQuery("")}
              className="absolute top-1/2 right-1.5 grid size-6 -translate-y-1/2 cursor-pointer place-items-center rounded border-0 bg-transparent text-ink-soft hover:text-ink"
            >
              <X className="size-3.5" />
            </button>
          )}
        </label>
        <Tabs
          label="Library"
          value={tab}
          onChange={onTab}
          items={[
            { value: "drafts", label: "Drafts", count: drafts?.length },
            { value: "videos", label: "Videos", count: videos?.length },
          ]}
        />
        {types.length > 1 && (
          <div role="group" aria-label="Show" className="-mt-1 flex flex-wrap gap-1.5">
            {(["all", ...types] as Filter[]).map((f) => {
              const on = activeFilter === f;
              const count = f === "all" ? items?.length : items?.filter((i) => i.type === f).length;
              return (
                <button
                  key={f}
                  type="button"
                  aria-pressed={on}
                  onClick={() => setFilter(f)}
                  className={`inline-flex h-7 cursor-pointer items-center gap-1 rounded-full border px-2.5 text-sm font-semibold transition-colors ${
                    on ? "border-ink bg-ink text-on-ink" : "border-line bg-panel text-ink-soft hover:border-line-strong hover:text-ink"
                  }`}
                >
                  {f !== "all" && <TypeIcon type={f} className="size-3.5" />}
                  {FILTER_LABEL[f]}
                  <span className={on ? "text-on-ink/70" : "text-ink-soft/80"}>{count}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      <div className="mt-2 min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        {groups === null ? (
          <p className="m-0 p-4 text-base text-ink-soft">Loading…</p>
        ) : groups.length === 0 ? (
          <div className="grid justify-items-center gap-2 px-4 py-10 text-center text-base text-ink-soft">
            <span className="grid size-10 place-items-center rounded-full bg-ink/[0.06]">
              {query ? <Search className="size-5" /> : tab === "drafts" ? <FileText className="size-5" /> : <Film className="size-5" />}
            </span>
            {query
              ? `Nothing matches “${query}”.`
              : tab === "drafts"
                ? "Scripts you write or paste, and songs you add, are saved here automatically."
                : "Videos you render appear here."}
          </div>
        ) : (
          groups.map((g) => (
            <section key={g.key} aria-label={g.label} className="mt-1">
              <h3 className="group-label sticky top-0 z-[1] m-0 flex items-baseline justify-between bg-paper/95 px-2 pt-2 pb-1 backdrop-blur-sm">
                {g.label}
                <span className="font-normal">{g.items.length}</span>
              </h3>
              <ul className="m-0 grid list-none gap-0.5 p-0">
                {g.items.map((item) => (
                  <Row key={item.key} item={item} />
                ))}
              </ul>
            </section>
          ))
        )}
      </div>
    </div>
  );
}
