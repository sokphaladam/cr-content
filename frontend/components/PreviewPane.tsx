"use client";

import { Check, Copy, Download, ImageIcon, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { API_BASE, api, fileUrl, outputUrl, type Job, type Lang, type Scene, type VideoDetail, type VideoSummary } from "@/lib/api";
import { isImagePath } from "@/lib/format";
import { Button, IconButton, Segmented, buttonClass, useToast } from "./ui";

const STEPS = ["Script", "Voiceover", "Footage", "Captions", "Final render"];

/** 9:16 phone frame; children are positioned inside the screen. Uses container units so overlays scale with it. */
function Phone({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto aspect-[9/16] w-full max-w-[300px] shrink-0 rounded-[32px] bg-ink p-2 shadow-[0_24px_48px_-24px_rgb(24_32_46/0.55)]">
      <div className="@container relative h-full w-full overflow-hidden rounded-[25px] bg-[#222b3b] text-white">{children}</div>
    </div>
  );
}

/** Approximation of the rendered frame: background, headline box, caption with one highlighted word. */
function ScenePreview({ scene, index, total, lang }: { scene: Scene; index: number; total: number; lang: Lang }) {
  const words = scene.narration.trim().split(/\s+/).filter(Boolean);
  const group = lang === "km" ? words.slice(0, 1) : words.slice(0, 3);
  const font = lang === "km" ? "var(--font-khmer)" : "Arial, Helvetica, sans-serif";
  const media = scene.media;
  return (
    <>
      {media ? (
        isImagePath(media) ? (
          // eslint-disable-next-line @next/next/no-img-element -- local engine file
          <img src={fileUrl(media)} alt="" className="absolute inset-0 h-full w-full object-cover brightness-90" />
        ) : (
          <video key={media} src={fileUrl(media)} muted loop autoPlay playsInline className="absolute inset-0 h-full w-full object-cover brightness-90" />
        )
      ) : (
        <div className="absolute inset-0 bg-[linear-gradient(160deg,#1e3c72,#2a5298_45%,#6a11cb)]">
          <p className="absolute inset-x-0 bottom-[14%] px-[8cqw] text-center text-[3.6cqw] leading-snug text-white/70">
            Auto footage{scene.visual_query ? <>: “{scene.visual_query}”</> : " from the search words"}
          </p>
        </div>
      )}
      {scene.on_screen_text && (
        <div className="absolute inset-x-0 top-[12%] flex justify-center px-[7cqw]">
          <span
            lang={lang}
            style={{ fontFamily: font }}
            className="bg-black/90 px-[2.4cqw] py-[1.2cqw] text-center text-[6.8cqw] leading-tight font-bold uppercase"
          >
            {scene.on_screen_text}
          </span>
        </div>
      )}
      {group.length > 0 && (
        <p
          lang={lang}
          style={{ fontFamily: font, WebkitTextStroke: "0.55cqw #000", paintOrder: "stroke fill" }}
          className="absolute inset-x-0 top-[57%] px-[8cqw] text-center text-[8.5cqw] leading-tight font-bold"
        >
          {group.map((w, i) => (
            <span key={i} className={i === 0 ? "text-caption" : ""}>
              {w}
              {i < group.length - 1 ? " " : ""}
            </span>
          ))}
        </p>
      )}
      <span className="absolute top-[3.5cqw] right-[4cqw] rounded-full bg-black/55 px-[2.2cqw] py-[0.8cqw] text-[3.4cqw] font-semibold">
        {index + 1} / {total}
      </span>
    </>
  );
}

function Progress({ job, title }: { job: Job | null; title: string }) {
  const log = useRef<HTMLPreElement>(null);
  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [job?.log.length]);
  const step = job?.step ?? 0;
  const finished = job?.status === "done";
  return (
    <div className="flex h-full flex-col gap-3.5 px-5 pt-7 pb-4">
      <p className="m-0 font-display text-[17px] leading-tight font-bold">{title}</p>
      <ol className="m-0 grid list-none gap-2 p-0">
        {STEPS.map((label, i) => {
          const n = i + 1;
          const done = finished || n < step;
          const active = !finished && n === step;
          return (
            <li key={label} className={`flex items-center gap-2.5 text-sm ${done ? "text-white/85" : active ? "font-semibold text-white" : "text-white/45"}`}>
              <span
                className={`grid size-[22px] place-items-center rounded-full text-xs font-semibold ${
                  done ? "bg-white/15" : active ? "animate-pulse bg-caption text-ink" : "border border-white/30"
                }`}
              >
                {done ? <Check className="size-3.5" /> : n}
              </span>
              {label}
            </li>
          );
        })}
      </ol>
      <pre ref={log} aria-live="polite" className="m-0 flex-1 overflow-auto font-mono text-[11px] leading-normal break-words whitespace-pre-wrap text-white/55">
        {job?.log.length ? job.log.join("\n") : job?.status === "queued" ? "Waiting for the previous render to finish…" : "Starting…"}
        {job?.status === "error" && <span className="mt-2 block text-[#ff9a8f]">{job.error}</span>}
      </pre>
    </div>
  );
}

function PostCard({ detail, onDelete }: { detail: VideoDetail; onDelete: (name: string) => void }) {
  const toast = useToast();
  const [confirmDelete, setConfirmDelete] = useState(false);
  return (
    <section aria-label="Post text" className="mx-auto w-full max-w-[300px] rounded-xl border border-line bg-panel">
      <pre lang={detail.lang} className="m-0 max-h-[160px] overflow-auto p-3.5 font-sans text-[13px] leading-relaxed whitespace-pre-wrap">
        {detail.post || "No caption saved for this video."}
      </pre>
      <div className="flex items-center gap-0.5 border-t border-line p-1.5">
        <Button
          size="sm"
          variant="ghost"
          icon={<Copy className="size-3.5" />}
          onClick={async () => {
            await navigator.clipboard.writeText(detail.post);
            toast("Caption and hashtags copied", "success");
          }}
        >
          Copy
        </Button>
        {detail.video && (
          <a className={buttonClass("ghost", "sm")} href={`${API_BASE}/api/videos/${encodeURIComponent(detail.name)}/download`}>
            <Download className="size-3.5" />
            Download
          </a>
        )}
        {confirmDelete ? (
          <Button size="sm" variant="danger" className="ml-auto" icon={<Trash2 className="size-3.5" />} onClick={() => onDelete(detail.name)}>
            Confirm
          </Button>
        ) : (
          <IconButton
            label="Delete video"
            tone="danger"
            className="ml-auto"
            onClick={() => {
              setConfirmDelete(true);
              setTimeout(() => setConfirmDelete(false), 3000);
            }}
          >
            <Trash2 className="size-4" />
          </IconButton>
        )}
      </div>
    </section>
  );
}

/** Cover image: pick a frame and a headline, then redraw thumbnail.jpg on the engine. */
function ThumbnailCard({ detail, onChange }: { detail: VideoDetail; onChange: (summary: VideoSummary) => void }) {
  const toast = useToast();
  // an older engine doesn't send the thumbnail fields: fall back to sensible defaults
  const duration = detail.duration ?? 0;
  const initial = { text: detail.thumb_text ?? detail.title, at: detail.thumb_at ?? Math.min(1, duration / 2), v: detail.thumb_v ?? 0 };
  const [text, setText] = useState(initial.text);
  const [at, setAt] = useState(initial.at);
  const [saved, setSaved] = useState(initial);
  const [busy, setBusy] = useState(false);
  const frame = useRef<HTMLVideoElement>(null);
  const changed = text !== saved.text || at !== saved.at;
  const pickingFrame = at !== saved.at;

  useEffect(() => {
    if (frame.current) frame.current.currentTime = at;
  }, [at, pickingFrame]);

  async function generate() {
    setBusy(true);
    try {
      const summary = await api.makeThumbnail(detail.name, text, at);
      setSaved({ text, at, v: summary.thumb_v });
      onChange(summary);
      toast("Thumbnail updated", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Thumbnail" className="mx-auto grid w-full max-w-[300px] gap-3 rounded-xl border border-line bg-panel p-3.5">
      <div className="flex gap-3">
        <div className="relative aspect-[9/16] w-[84px] shrink-0 overflow-hidden rounded-md bg-ink">
          {pickingFrame ? (
            <video
              ref={frame}
              src={`${outputUrl(detail.name, "video.mp4")}?v=${encodeURIComponent(detail.created)}`}
              muted
              playsInline
              preload="auto"
              onLoadedMetadata={(e) => (e.currentTarget.currentTime = at)}
              className="h-full w-full object-cover"
            />
          ) : detail.thumb ? (
            // eslint-disable-next-line @next/next/no-img-element -- local engine file
            <img src={`${outputUrl(detail.name, "thumbnail.jpg")}?v=${saved.v}`} alt="Current thumbnail" className="h-full w-full object-cover" />
          ) : (
            <span className="grid h-full place-items-center text-white/60">
              <ImageIcon className="size-5" />
            </span>
          )}
        </div>
        <div className="grid min-w-0 flex-1 content-start gap-2">
          <label className="field-label" htmlFor="thumb-text">
            Thumbnail headline
          </label>
          <textarea
            id="thumb-text"
            lang={detail.lang}
            rows={3}
            maxLength={120}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="No headline: just the frame"
            className="field-input resize-none py-1.5 text-[13px] leading-snug"
          />
        </div>
      </div>
      <div className="grid gap-1">
        <label className="field-label flex justify-between" htmlFor="thumb-at">
          Frame <span className="font-normal text-ink-soft tabular-nums">{at.toFixed(1)} s</span>
        </label>
        <input
          id="thumb-at"
          type="range"
          min={0}
          max={Math.max(0.1, duration - 0.1)}
          step={0.1}
          value={at}
          onChange={(e) => setAt(+e.target.value)}
          className="h-6 w-full accent-cobalt"
        />
      </div>
      <div className="flex items-center gap-1.5">
        <Button size="sm" variant={changed ? "primary" : "secondary"} icon={<ImageIcon className="size-3.5" />} loading={busy} onClick={generate}>
          {detail.thumb ? "Regenerate" : "Generate"}
        </Button>
        {detail.thumb && (
          <a className={buttonClass("ghost", "sm")} href={`${API_BASE}/api/videos/${encodeURIComponent(detail.name)}/thumbnail.jpg`}>
            <Download className="size-3.5" />
            Download
          </a>
        )}
      </div>
    </section>
  );
}

export type PreviewView = "scene" | "video";

export function PreviewPane({
  scene,
  sceneIndex,
  sceneCount,
  lang,
  rendering,
  job,
  jobTitle,
  detail,
  view,
  onView,
  onDeleteVideo,
  onThumbnail,
}: {
  scene: Scene | null;
  sceneIndex: number;
  sceneCount: number;
  lang: Lang;
  rendering: boolean;
  job: Job | null;
  jobTitle: string;
  detail: VideoDetail | null;
  view: PreviewView;
  onView: (v: PreviewView) => void;
  onDeleteVideo: (name: string) => void;
  onThumbnail: (summary: VideoSummary) => void;
}) {
  const showProgress = rendering || job?.status === "error";
  const canToggle = !!scene && !!detail?.video && !showProgress;
  const showVideo = !showProgress && !!detail?.video && (view === "video" || !scene);

  return (
    <div className="grid content-start gap-4 p-5">
      <div className="flex h-8 items-center justify-between">
        <h2 className="m-0 font-display text-base font-bold">
          {showProgress ? "Rendering" : showVideo ? "Video" : "Preview"}
        </h2>
        {canToggle && (
          <Segmented
            size="sm"
            name="preview-view"
            value={view}
            onChange={onView}
            options={[
              { value: "scene", label: "Scene" },
              { value: "video", label: "Video" },
            ]}
          />
        )}
      </div>

      <Phone>
        {showProgress ? (
          <Progress job={job} title={jobTitle} />
        ) : showVideo && detail ? (
          <video
            key={detail.name}
            src={`${outputUrl(detail.name, "video.mp4")}?v=${encodeURIComponent(detail.created)}`}
            controls
            playsInline
            className="block h-full w-full bg-black object-cover"
          />
        ) : scene ? (
          <ScenePreview scene={scene} index={sceneIndex} total={sceneCount} lang={lang} />
        ) : (
          <div className="grid h-full place-items-center p-7 text-center">
            <p className="m-0 font-display text-2xl leading-tight font-extrabold">
              <mark>Your video</mark> shows up here
            </p>
          </div>
        )}
      </Phone>

      {!showProgress && !showVideo && scene && (
        <p className="m-0 text-center text-xs text-ink-soft">Approximate look of the scene you&apos;re editing. Click a scene to preview it.</p>
      )}
      {showVideo && detail && <ThumbnailCard key={`thumb-${detail.name}`} detail={detail} onChange={onThumbnail} />}
      {showVideo && detail && <PostCard key={`post-${detail.name}`} detail={detail} onDelete={onDeleteVideo} />}
    </div>
  );
}
