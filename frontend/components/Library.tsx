"use client";

import { FileText, Film, Music, Plus } from "lucide-react";
import { fileUrl, outputUrl, type DraftSummary, type VideoSummary } from "@/lib/api";
import { isImagePath, langCode, relativeTime } from "@/lib/format";
import { Button, Tabs } from "./ui";

export type LibraryTab = "drafts" | "videos";

function Row({
  current,
  onClick,
  thumb,
  title,
  lang,
  meta,
}: {
  current: boolean;
  onClick: () => void;
  thumb: React.ReactNode;
  title: string;
  lang: string;
  meta: string;
}) {
  return (
    <li>
      <button
        type="button"
        aria-current={current || undefined}
        onClick={onClick}
        className={`grid w-full cursor-pointer grid-cols-[36px_minmax(0,1fr)] items-center gap-3 rounded-lg border-0 p-2 text-left transition-colors ${
          current ? "bg-panel shadow-[inset_3px_0_0_var(--color-cobalt),0_1px_2px_rgb(24_32_46/0.06)]" : "bg-transparent hover:bg-ink/[0.04]"
        }`}
      >
        {thumb}
        <span className="min-w-0">
          <span lang={lang} className="line-clamp-2 text-[13.5px] leading-snug font-semibold text-ink">
            {title}
          </span>
          <span className="mt-0.5 flex items-center gap-1.5 text-xs text-ink-soft">
            <span lang={lang === "km" ? "km" : undefined} className="rounded bg-ink/[0.06] px-1 leading-4 font-semibold">
              {langCode(lang)}
            </span>
            <span className="truncate">{meta}</span>
          </span>
        </span>
      </button>
    </li>
  );
}

function Thumb({ src, fallback }: { src?: string; fallback: React.ReactNode }) {
  return (
    <span
      className="grid aspect-[9/16] w-9 place-items-center overflow-hidden rounded-md bg-ink/[0.08] bg-cover bg-center text-ink-soft"
      style={src ? { backgroundImage: `url('${src}')` } : undefined}
    >
      {!src && fallback}
    </span>
  );
}

function Empty({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <li className="grid justify-items-center gap-2 px-4 py-10 text-center text-[13px] text-ink-soft">
      <span className="grid size-10 place-items-center rounded-full bg-ink/[0.06]">{icon}</span>
      {text}
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
  onNew: () => void;
}) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="grid gap-3 px-4 pt-4">
        <Button variant="primary" icon={<Plus className="size-4" />} onClick={onNew} className="w-full">
          New video
        </Button>
        <Tabs
          label="Library"
          value={tab}
          onChange={onTab}
          items={[
            { value: "drafts", label: "Drafts", count: drafts?.length },
            { value: "videos", label: "Videos", count: videos?.length },
          ]}
        />
      </div>

      <ul className="m-0 grid min-h-0 flex-1 list-none content-start gap-0.5 overflow-y-auto p-2">
        {tab === "drafts" &&
          (drafts === null ? (
            <li className="p-4 text-[13px] text-ink-soft">Loading…</li>
          ) : drafts.length === 0 ? (
            <Empty icon={<FileText className="size-5" />} text="Scripts you write or paste, and songs you add, are saved here automatically." />
          ) : (
            drafts.map((d) =>
              d.kind === "song" ? (
                <Row
                  key={d.id}
                  current={d.id === selectedDraft}
                  onClick={() => onSelectSong(d.id)}
                  title={d.title}
                  lang={d.lang}
                  meta={`song, ${d.versions ? `${d.versions} video${d.versions === 1 ? "" : "s"}` : "no video yet"}, ${relativeTime(d.updated)}`}
                  thumb={<Thumb src={d.thumb ? `${outputUrl(d.thumb, "thumbnail.jpg")}?v=${d.thumb_v ?? 0}` : undefined} fallback={<Music className="size-4" />} />}
                />
              ) : (
                <Row
                  key={d.id}
                  current={d.id === selectedDraft}
                  onClick={() => onSelectDraft(d.id)}
                  title={d.title}
                  lang={d.lang}
                  meta={`${d.scenes} scene${d.scenes === 1 ? "" : "s"}, ${relativeTime(d.updated)}`}
                  thumb={<Thumb src={d.cover && isImagePath(d.cover) ? fileUrl(d.cover) : undefined} fallback={<FileText className="size-4" />} />}
                />
              ),
            )
          ))}
        {tab === "videos" &&
          (videos === null ? (
            <li className="p-4 text-[13px] text-ink-soft">Loading…</li>
          ) : videos.length === 0 ? (
            <Empty icon={<Film className="size-5" />} text="Videos you render appear here." />
          ) : (
            videos.map((v) => (
              <Row
                key={v.name}
                current={v.name === selectedVideo}
                onClick={() => onSelectVideo(v.name)}
                title={v.title}
                lang={v.lang}
                meta={v.video || v.audio ? `${v.kind === "music_video" ? "music video, " : v.kind === "song" ? "song, " : ""}${relativeTime(v.created)}` : "script only"}
                thumb={
                  <Thumb
                    src={v.thumb ? `${outputUrl(v.name, "thumbnail.jpg")}?v=${v.thumb_v}` : undefined}
                    fallback={v.kind !== "video" ? <Music className="size-4" /> : <Film className="size-4" />}
                  />
                }
              />
            ))
          ))}
      </ul>
    </div>
  );
}
