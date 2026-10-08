"use client";

import { Check, Copy, Download, Film, ImageIcon, ListMusic, Music, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { API_BASE, api, fileUrl, outputUrl, type Job, type Lang, type Scene, type ThumbStyle, type ThumbSuggestion, type ThumbSuggestions, type VideoDetail, type VideoSummary } from "@/lib/api";
import { isImagePath, relativeTime } from "@/lib/format";
import { Button, IconButton, Segmented, buttonClass, useToast } from "./ui";
import { VideoIdea } from "./VideoIdea";

const STEPS = ["Script", "Voiceover", "Footage", "Captions", "Final render"];
const SONG_STEPS = ["Lyrics", "Compose"];
const MUSIC_VIDEO_STEPS = ["Lyric timing", "Beats and footage", "Captions", "Final render"];
const SYNC_STEPS = ["Read lyrics", "Lyric timing"];
const stepsFor = (job: Job | null) =>
  job?.kind === "song" ? SONG_STEPS : job?.kind === "song_video" ? MUSIC_VIDEO_STEPS : job?.kind === "lyrics_sync" ? SYNC_STEPS : STEPS;

function SongPlayer({ detail }: { detail: VideoDetail }) {
  return (
    <div className="flex h-full flex-col justify-end gap-4 bg-gradient-to-b from-[#2a1b4a] via-[#1b2a4a] to-black p-5">
      <Music className="size-10 text-white/40" />
      <div className="grid gap-1">
        <p lang={detail.lang} className="m-0 font-display text-2xl leading-tight font-extrabold">{detail.title}</p>
        {detail.song && (detail.song.genre || detail.song.bpm > 0) && (
          <p className="m-0 text-[13px] text-white/60">{[detail.song.genre, detail.song.bpm > 0 ? `${detail.song.bpm} bpm` : ""].filter(Boolean).join(", ")}</p>
        )}
      </div>
      <audio key={detail.name} src={outputUrl(detail.name, "song.mp3")} controls className="w-full" />
    </div>
  );
}

function SongCard({
  detail,
  onDelete,
  onMakeVideo,
  onOpenTiming,
  onSelectVideo,
}: {
  detail: VideoDetail;
  onDelete: (name: string) => void;
  onMakeVideo: (name: string, idea: string) => void;
  onOpenTiming: (name: string) => void;
  onSelectVideo: (name: string) => void;
}) {
  const own = detail.source === "upload";
  const versions = detail.versions ?? [];
  const [idea, setIdea] = useState(detail.idea ?? "");
  return (
    <section className="grid gap-3 rounded-xl border border-line bg-panel p-3.5">
      <div className="grid gap-1.5">
        <Button variant="secondary" icon={<ListMusic className="size-4" />} onClick={() => onOpenTiming(detail.name)}>
          Edit lyric timing
        </Button>
        <VideoIdea id={`idea-${detail.name}`} value={idea} onChange={setIdea} />
        <Button variant={versions.length ? "secondary" : "primary"} icon={<Film className="size-4" />} onClick={() => onMakeVideo(detail.name, idea)}>
          {versions.length ? "Make a new version" : "Make music video"}
        </Button>
        <p className="m-0 text-xs text-ink-soft">
          {detail.aspect === "16:9" ? "16:9 landscape" : "9:16 vertical"}. Footage cut on the beat with karaoke lyrics, using the timing as it is now. Takes a few
          minutes{own ? ", longer for a full song" : ""}. Earlier versions are kept.
        </p>
      </div>
      {versions.length > 0 && (
        <div className="grid gap-1">
          <h3 className="m-0 text-sm font-semibold">Music videos ({versions.length})</h3>
          <ul className="m-0 grid list-none gap-0.5 p-0">
            {versions.map((v, i) => (
              <li key={v.name}>
                <button
                  type="button"
                  onClick={() => onSelectVideo(v.name)}
                  className="flex w-full cursor-pointer items-center gap-2.5 rounded-lg border-0 bg-transparent p-1.5 text-left hover:bg-ink/[0.04]"
                >
                  <span
                    className={`grid h-9 shrink-0 place-items-center overflow-hidden rounded bg-ink/[0.08] bg-cover bg-center text-ink-soft ${v.aspect === "16:9" ? "aspect-video" : "aspect-[9/16]"}`}
                    style={v.thumb ? { backgroundImage: `url('${outputUrl(v.name, "thumbnail.jpg")}?v=${v.thumb_v}')` } : undefined}
                  >
                    {!v.thumb && <Film className="size-3.5" />}
                  </span>
                  <span className="min-w-0 text-[13px]">
                    <span className="block font-semibold text-ink">Version {versions.length - i}</span>
                    <span className="block text-xs text-ink-soft">{relativeTime(v.created)}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      <h3 className="m-0 text-sm font-semibold">Lyrics</h3>
      <div lang={detail.lang} className="grid max-h-[260px] gap-3 overflow-auto text-[13px] leading-relaxed">
        {detail.song?.sections.map((s, i) => (
          <div key={i}>
            <p className="m-0 text-xs font-semibold text-ink-soft">
              {s.name}
              {s.seconds > 0 ? ` · ${s.seconds}s` : ""}
            </p>
            {s.lyrics.filter((l) => l.trim()).length ? (
              s.lyrics.filter((l) => l.trim()).map((l, j) => <p key={j} className="m-0">{l}</p>)
            ) : (
              <p className="m-0 text-ink-soft italic">instrumental</p>
            )}
          </div>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-1">
        <a className={buttonClass("ghost", "sm")} href={`${API_BASE}/api/videos/${encodeURIComponent(detail.name)}/song`}>
          <Download className="size-3.5" /> Song
        </a>
        {detail.stems.vocals && (
          <a className={buttonClass("ghost", "sm")} href={`${API_BASE}/api/videos/${encodeURIComponent(detail.name)}/stem/vocals`}>
            <Download className="size-3.5" /> Vocals
          </a>
        )}
        {detail.stems.instrumental && (
          <a className={buttonClass("ghost", "sm")} href={`${API_BASE}/api/videos/${encodeURIComponent(detail.name)}/stem/instrumental`}>
            <Download className="size-3.5" /> Instrumental
          </a>
        )}
        <Button
          size="sm"
          variant="danger"
          className="ml-auto"
          title={versions.length ? "Deletes the song and its timing. Its music videos stay in Videos." : undefined}
          icon={<Trash2 className="size-3.5" />}
          onClick={() => onDelete(detail.name)}
        >
          Delete song
        </Button>
      </div>
    </section>
  );
}

/** 9:16 phone frame (or a 16:9 screen for landscape music videos); children are positioned inside the screen.
 * Uses container units so overlays scale with it. */
function Phone({ children, landscape = false }: { children: React.ReactNode; landscape?: boolean }) {
  return (
    <div
      className={`mx-auto w-full shrink-0 bg-ink shadow-[0_24px_48px_-24px_rgb(24_32_46/0.55)] ${
        landscape ? "aspect-video rounded-xl p-1.5" : "aspect-[9/16] max-w-[300px] rounded-[32px] p-2"
      }`}
    >
      <div className={`@container relative h-full w-full overflow-hidden bg-[#222b3b] text-white ${landscape ? "rounded-lg" : "rounded-[25px]"}`}>{children}</div>
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
        {stepsFor(job).map((label, i) => {
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

const THUMB_STYLES: { value: ThumbStyle; label: string }[] = [
  { value: "bold", label: "Bold" },
  { value: "box", label: "Box" },
  { value: "stacked", label: "Stacked" },
];

/** Cover image: get ideas (Claude headline x best frame x style) or pick a frame and headline, then redraw thumbnail.jpg. */
function ThumbnailCard({ detail, onChange }: { detail: VideoDetail; onChange: (summary: VideoSummary) => void }) {
  const toast = useToast();
  // an older engine doesn't send the thumbnail fields: fall back to sensible defaults
  const duration = detail.duration ?? 0;
  const initial = {
    text: detail.thumb_text ?? detail.title,
    at: detail.thumb_at ?? Math.min(1, duration / 2),
    style: detail.thumb_style ?? ("bold" as ThumbStyle),
    emphasis: detail.thumb_emphasis ?? "",
    v: detail.thumb_v ?? 0,
  };
  const [text, setText] = useState(initial.text);
  const [at, setAt] = useState(initial.at);
  const [style, setStyle] = useState(initial.style);
  const [emphasis, setEmphasis] = useState(initial.emphasis);
  const [saved, setSaved] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [ideas, setIdeas] = useState<ThumbSuggestions | null>(detail.thumb_suggestions ?? null);
  const [ideasV, setIdeasV] = useState(0); // cache buster for re-rendered preview images
  const [suggesting, setSuggesting] = useState(false);
  const frame = useRef<HTMLVideoElement>(null);
  const changed = text !== saved.text || at !== saved.at || style !== saved.style || emphasis !== saved.emphasis;
  const pickingFrame = at !== saved.at;

  useEffect(() => {
    if (frame.current) frame.current.currentTime = at;
  }, [at, pickingFrame]);

  async function generate(cover = { text, at, style, emphasis }) {
    setBusy(true);
    try {
      const summary = await api.makeThumbnail(detail.name, cover);
      setText(cover.text);
      setAt(cover.at);
      setStyle(cover.style);
      setEmphasis(cover.emphasis);
      setSaved({ ...cover, v: summary.thumb_v });
      onChange(summary);
      toast("Thumbnail updated", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function suggest() {
    setSuggesting(true);
    try {
      setIdeas(await api.suggestThumbnails(detail.name));
      setIdeasV(Date.now());
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setSuggesting(false);
    }
  }

  const isCurrent = (i: ThumbSuggestion) =>
    i.text === saved.text && i.at === saved.at && i.style === saved.style && i.emphasis === saved.emphasis;

  return (
    <section aria-label="Thumbnail" className="mx-auto grid w-full max-w-[300px] gap-3 rounded-xl border border-line bg-panel p-3.5">
      <div className="grid gap-2">
        <div className="flex items-center justify-between gap-2">
          <span className="field-label">Cover ideas</span>
          <Button size="sm" variant={ideas ? "ghost" : "primary"} icon={<Sparkles className="size-3.5" />} loading={suggesting} onClick={suggest}>
            {ideas ? "New ideas" : "Suggest covers"}
          </Button>
        </div>
        {suggesting && !ideas && <p className="m-0 text-[12.5px] text-ink-soft">Finding the best frames and writing headlines…</p>}
        {ideas && (
          <>
            <div className={`grid grid-cols-4 gap-1.5 ${suggesting ? "opacity-50" : ""}`}>
              {ideas.items.map((idea) => (
                <button
                  key={idea.file}
                  type="button"
                  disabled={busy || suggesting}
                  onClick={() => generate({ text: idea.text, at: idea.at, style: idea.style, emphasis: idea.emphasis })}
                  title={`Use “${idea.text}” (${idea.style}, ${idea.at.toFixed(1)} s)`}
                  aria-label={`Use cover: ${idea.text}`}
                  className={`relative ${detail.aspect === "16:9" ? "aspect-video" : "aspect-[9/16]"} cursor-pointer overflow-hidden rounded-md bg-ink outline outline-offset-1 transition hover:brightness-110 disabled:cursor-wait ${
                    isCurrent(idea) ? "outline-2 outline-cobalt" : "outline-1 outline-line"
                  }`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element -- local engine file */}
                  <img src={`${outputUrl(detail.name, idea.file)}?v=${ideasV}`} alt="" className="h-full w-full object-cover" />
                  {isCurrent(idea) && (
                    <span className="absolute top-1 right-1 grid size-4 place-items-center rounded-full bg-cobalt text-white">
                      <Check className="size-3" />
                    </span>
                  )}
                </button>
              ))}
            </div>
            <p className="m-0 text-[12px] text-ink-soft">{ideas.note || "Click one to use it, then fine-tune below."}</p>
          </>
        )}
      </div>
      <div className="flex gap-3">
        <div className={`relative shrink-0 overflow-hidden rounded-md bg-ink ${detail.aspect === "16:9" ? "aspect-video w-[132px]" : "aspect-[9/16] w-[84px]"}`}>
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
        <label className="field-label" htmlFor="thumb-emphasis">
          Highlight
        </label>
        <input
          id="thumb-emphasis"
          lang={detail.lang}
          maxLength={60}
          value={emphasis}
          onChange={(e) => setEmphasis(e.target.value)}
          placeholder="Auto: a number or the key word"
          className="field-input h-8 text-[13px]"
        />
      </div>
      <div className="grid justify-items-start gap-1">
        <span className="field-label">Style</span>
        <Segmented name="thumb-style" size="sm" value={style} options={THUMB_STYLES} onChange={setStyle} />
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
        <Button size="sm" variant={changed ? "primary" : "secondary"} icon={<ImageIcon className="size-3.5" />} loading={busy} onClick={() => generate()}>
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
  onMakeMusicVideo,
  onOpenTiming,
  onSelectVideo,
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
  onMakeMusicVideo: (name: string, idea: string) => void;
  onOpenTiming: (name: string) => void;
  onSelectVideo: (name: string) => void;
}) {
  const showProgress = rendering || job?.status === "error";
  const canToggle = !!scene && !!detail?.video && !showProgress;
  const showVideo = !showProgress && !!detail?.video && (view === "video" || !scene);
  const isSong = !showProgress && !scene && detail?.kind === "song" && detail.audio;
  const showSong = isSong && !showVideo;

  return (
    <div className="grid content-start gap-4 p-5">
      <div className="flex h-8 items-center justify-between">
        <h2 className="m-0 font-display text-base font-bold">
          {showProgress ? (job?.kind === "song" ? "Composing" : job?.kind === "lyrics_sync" ? "Syncing lyrics" : "Rendering") : showVideo ? (detail?.kind === "music_video" ? "Music video" : "Video") : showSong ? "Song" : "Preview"}
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

      <Phone landscape={!showProgress && !scene && detail?.aspect === "16:9"}>
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
        ) : showSong && detail ? (
          <SongPlayer detail={detail} />
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
      {showVideo && detail?.kind === "music_video" && (
        <section className="grid gap-1.5 rounded-xl border border-line bg-panel p-3.5">
          {detail.song_folder ? (
            <>
              <Button variant="secondary" icon={<ListMusic className="size-4" />} onClick={() => onOpenTiming(detail.song_folder)}>
                Edit lyric timing
              </Button>
              {detail.idea && (
                <p className="m-0 text-xs text-ink-soft">
                  Made with the idea: <span className="text-ink">{detail.idea}</span>
                </p>
              )}
              <p className="m-0 text-xs text-ink-soft">This video stays as it is. Fix the timing, then make a new version from the song.</p>
            </>
          ) : (
            <p className="m-0 text-xs text-ink-soft">The song this video was made from has been deleted, so its timing can&apos;t be edited.</p>
          )}
        </section>
      )}
      {isSong && detail && (
        <SongCard key={`song-${detail.name}`} detail={detail} onDelete={onDeleteVideo} onMakeVideo={onMakeMusicVideo} onOpenTiming={onOpenTiming} onSelectVideo={onSelectVideo} />
      )}
      {showVideo && detail && <PostCard key={`post-${detail.name}`} detail={detail} onDelete={onDeleteVideo} />}
    </div>
  );
}
