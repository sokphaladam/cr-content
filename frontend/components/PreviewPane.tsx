"use client";

import { Check, Copy, Download, Film, ImageIcon, ImageUp, ListMusic, Music, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { API_BASE, api, fileUrl, outputUrl, type Job, type Lang, type MusicVideoSettings, type Options, type PostSuggestion, type Scene, type ThumbStyle, type ThumbSuggestion, type ThumbSuggestions, type VideoDetail, type VideoSummary } from "@/lib/api";
import { isImagePath, relativeTime } from "@/lib/format";
import type { DraftTimeline } from "@/lib/useDraftTimeline";
import { Button, IconButton, Segmented, buttonClass, useToast } from "./ui";
import { CaptionPanel, LiveControls, LiveFrame, type FrameEdits } from "./LivePreview";
import { MusicVideoOptions } from "./MusicVideoOptions";
import { PublishCard } from "./PublishCard";

const STEPS = ["Script", "Voiceover", "Footage", "Captions", "Final render"];
const SONG_STEPS = ["Lyrics", "Compose", "Lyric timing"];
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
          <p className="m-0 text-base text-white/60">{[detail.song.genre, detail.song.bpm > 0 ? `${detail.song.bpm} bpm` : ""].filter(Boolean).join(", ")}</p>
        )}
      </div>
      <audio key={detail.name} src={outputUrl(detail.name, "song.mp3")} controls className="w-full" />
    </div>
  );
}

/** The idea, look, lyric style and visuals a song's last music video used: the starting point for the next one. */
export function settingsOf(detail: Pick<VideoDetail, "idea" | "look" | "lyric_style" | "art_style" | "pictures" | "direction" | "cold_open" | "now_playing">): MusicVideoSettings {
  return {
    idea: detail.idea ?? "",
    look: detail.look ?? "",
    lyric_style: detail.lyric_style ?? null,
    art_style: detail.art_style ?? "",
    pictures: detail.pictures ?? "normal",
    direction: detail.direction ?? null,
    cold_open: detail.cold_open ?? false,
    now_playing: detail.now_playing ?? false,
  };
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
  onMakeVideo: (name: string, settings: MusicVideoSettings) => void;
  onOpenTiming: (name: string) => void;
  onSelectVideo: (name: string) => void;
}) {
  const own = detail.source === "upload";
  const versions = detail.versions ?? [];
  const [settings, setSettings] = useState<MusicVideoSettings>(() => settingsOf(detail));
  const sample = detail.song?.sections.flatMap((s) => s.lyrics).find((l) => l.trim()) ?? detail.title;
  return (
    <section className="grid gap-3 card p-3.5">
      <div className="grid gap-1.5">
        <Button variant="secondary" icon={<ListMusic className="size-4" />} onClick={() => onOpenTiming(detail.name)}>
          Edit lyric timing
        </Button>
        <MusicVideoOptions
          name={detail.name}
          lang={detail.lang}
          aspect={detail.aspect}
          sample={sample}
          sections={detail.song?.sections.map((s) => s.name) ?? []}
          value={settings}
          onChange={setSettings}
        />
        <Button variant={versions.length ? "secondary" : "primary"} icon={<Film className="size-4" />} onClick={() => onMakeVideo(detail.name, settings)}>
          {versions.length ? "Make a new version" : "Make music video"}
        </Button>
        <p className="m-0 text-sm text-ink-soft">
          {detail.aspect === "16:9" ? "16:9 landscape" : "9:16 vertical"}. Footage cut on the beat with karaoke lyrics, using the timing as it is now. Takes a few
          minutes{own ? ", longer for a full song" : ""}. Earlier versions are kept.
        </p>
      </div>
      {versions.length > 0 && (
        <div className="grid gap-1">
          <h3 className="m-0 text-md font-semibold">Music videos ({versions.length})</h3>
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
                  <span className="min-w-0 text-base">
                    <span className="block font-semibold text-ink">Version {versions.length - i}</span>
                    <span className="block text-sm text-ink-soft">{relativeTime(v.created)}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      <h3 className="m-0 text-md font-semibold">Lyrics</h3>
      <div lang={detail.lang} className="grid max-h-[260px] gap-3 overflow-auto text-base leading-relaxed">
        {detail.song?.sections.map((s, i) => (
          <div key={i}>
            <p className="m-0 text-sm font-semibold text-ink-soft">
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
function Phone({ children, landscape = false, fit = false }: { children: React.ReactNode; landscape?: boolean; fit?: boolean }) {
  // fit: as wide as its parent allows (the editor's stage sizes the parent to the space it has)
  return (
    <div
      className={`mx-auto w-full shrink-0 bg-media shadow-[0_24px_48px_-24px_rgb(24_32_46/0.55)] ${
        landscape ? "aspect-video rounded-xl p-1.5" : `aspect-[9/16] rounded-[32px] p-2 ${fit ? "" : "max-w-[300px]"}`
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
      <p className="m-0 font-display text-xl leading-tight font-bold">{title}</p>
      <ol className="m-0 grid list-none gap-2 p-0">
        {stepsFor(job).map((label, i) => {
          const n = i + 1;
          const done = finished || n < step;
          const active = !finished && n === step;
          return (
            <li key={label} className={`flex items-center gap-2.5 text-md ${done ? "text-white/85" : active ? "font-semibold text-white" : "text-white/45"}`}>
              <span
                className={`grid size-[22px] place-items-center rounded-full text-sm font-semibold ${
                  done ? "bg-white/15" : active ? "animate-pulse bg-caption text-media" : "border border-white/30"
                }`}
              >
                {done ? <Check className="size-3.5" /> : n}
              </span>
              {label}
            </li>
          );
        })}
      </ol>
      <pre ref={log} aria-live="polite" className="m-0 flex-1 overflow-auto font-mono text-xs leading-normal break-words whitespace-pre-wrap text-white/55">
        {job?.log.length ? job.log.join("\n") : job?.status === "queued" ? "Waiting for the previous render to finish…" : "Starting…"}
        {job?.status === "error" && <span className="mt-2 block text-[#ff9a8f]">{job.error}</span>}
      </pre>
    </div>
  );
}

/** The content plan's fact-check notes of a rendered video, and the comment to pin under it. */
function FactsCard({ detail }: { detail: VideoDetail }) {
  const toast = useToast();
  const facts = detail.script?.facts ?? [];
  const comment = detail.script?.pinned_comment ?? "";
  if (!facts.length && !comment) return null;
  return (
    <section aria-labelledby={`facts-${detail.name}`} className="grid gap-2 card p-3.5">
      <h3 id={`facts-${detail.name}`} className="m-0 font-display text-md font-bold">
        Fact check
      </h3>
      {facts.length > 0 && (
        <ul className="m-0 grid gap-1 pl-4 text-sm leading-snug text-ink-soft">
          {facts.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      )}
      {comment && (
        <>
          <p className="m-0 rounded-lg bg-paper px-2.5 py-2 text-sm leading-snug whitespace-pre-line">{comment}</p>
          <Button
            size="sm"
            variant="secondary"
            icon={<Copy className="size-3.5" />}
            className="justify-self-start"
            onClick={() =>
              navigator.clipboard.writeText(comment).then(
                () => toast("Comment copied. Paste it under the video and pin it.", "success"),
                () => toast("Couldn't copy. Select the text and copy it.", "error"),
              )
            }
          >
            Copy pinned comment
          </Button>
        </>
      )}
    </section>
  );
}

function PostCard({ detail, onDelete }: { detail: VideoDetail; onDelete: (name: string) => void }) {
  const toast = useToast();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [post, setPost] = useState(detail.post);
  const [postIdea, setPostIdea] = useState("");
  const [options, setOptions] = useState<PostSuggestion[] | null>(null);
  const [suggesting, setSuggesting] = useState(false);
  const [saving, setSaving] = useState(-1); // index of the option being saved

  async function suggest() {
    setSuggesting(true);
    try {
      setOptions((await api.suggestPosts(detail.name, postIdea)).items);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setSuggesting(false);
    }
  }

  async function use(option: PostSuggestion, i: number) {
    setSaving(i);
    try {
      setPost((await api.savePost(detail.name, option)).post);
      toast("Post text updated", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setSaving(-1);
    }
  }

  const isCurrent = (o: PostSuggestion) => post.startsWith(`${o.title}

${o.description}
`);

  // post.txt is the title line, then the description: kept apart here, so the description you paste into YouTube or
  // TikTok doesn't open by repeating the title (uploads from the app already send them separately)
  const [postTitle, ...rest] = post.split("\n");
  const description = rest.join("\n").trim();

  return (
    <section aria-label="Post text" className="mx-auto w-full max-w-[300px] card">
      {post ? (
        <div className="grid max-h-[200px] gap-1.5 overflow-auto p-3.5">
          <span className="text-2xs font-semibold tracking-wide text-ink-soft uppercase">Title</span>
          <p lang={detail.lang} className="m-0 font-display text-md leading-snug font-bold">{postTitle}</p>
          <span className="mt-1 text-2xs font-semibold tracking-wide text-ink-soft uppercase">Description</span>
          <p lang={detail.lang} className="m-0 text-base leading-relaxed whitespace-pre-wrap">{description}</p>
        </div>
      ) : (
        <p className="m-0 p-3.5 text-base text-ink-soft">No caption saved for this video.</p>
      )}
      <div className="grid gap-2 border-t border-line p-3.5">
        <label className="field-label" htmlFor={`post-idea-${detail.name}`}>
          Title direction <span className="font-normal">optional</span>
        </label>
        <textarea
          id={`post-idea-${detail.name}`}
          lang={detail.lang}
          rows={2}
          maxLength={600}
          value={postIdea}
          onChange={(e) => setPostIdea(e.target.value)}
          placeholder="Mysterious and curious, aimed at travel lovers, mention the 3 tips"
          className="field-input resize-y py-1.5 text-base leading-snug"
        />
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm text-ink-soft">Tone, audience or words to include.</span>
          <Button size="sm" variant={options && !postIdea ? "ghost" : "primary"} icon={<Sparkles className="size-3.5" />} loading={suggesting} onClick={suggest}>
            {options ? "New ideas" : "Suggest titles"}
          </Button>
        </div>
        {suggesting && <p className="m-0 text-sm text-ink-soft">Claude is writing titles and descriptions from different angles…</p>}
        {options && (
          <ul className={`m-0 grid list-none gap-2 p-0 ${suggesting ? "opacity-50" : ""}`}>
            {options.map((o, i) => (
              <li key={`${i}-${o.title}`} className={`grid gap-1.5 rounded-lg border p-2.5 ${isCurrent(o) ? "border-cobalt" : "border-line"}`}>
                <span className="text-2xs font-semibold tracking-wide text-ink-soft uppercase">
                  {i === 0 ? `${o.angle} · Top pick` : o.angle}
                </span>
                <p lang={detail.lang} className="m-0 font-display text-md leading-snug font-bold">{o.title}</p>
                <p lang={detail.lang} className="m-0 text-sm leading-snug whitespace-pre-wrap text-ink-soft">{o.description}</p>
                <p className="m-0 text-sm leading-snug text-cobalt">{o.hashtags.map((h) => `#${h}`).join(" ")}</p>
                <div className="flex gap-0.5">
                  <Button
                    size="sm"
                    variant={isCurrent(o) ? "ghost" : "secondary"}
                    icon={<Check className="size-3.5" />}
                    loading={saving === i}
                    disabled={saving !== -1 || isCurrent(o)}
                    onClick={() => use(o, i)}
                  >
                    {isCurrent(o) ? "In use" : "Use this"}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    icon={<Copy className="size-3.5" />}
                    onClick={async () => {
                      await navigator.clipboard.writeText(o.title);
                      toast("Title copied", "success");
                    }}
                  >
                    Title
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="flex items-center gap-0.5 border-t border-line p-1.5">
        <Button
          size="sm"
          variant="ghost"
          icon={<Copy className="size-3.5" />}
          disabled={!post}
          onClick={async () => {
            await navigator.clipboard.writeText(postTitle);
            toast("Title copied", "success");
          }}
        >
          Title
        </Button>
        <Button
          size="sm"
          variant="ghost"
          icon={<Copy className="size-3.5" />}
          disabled={!post}
          onClick={async () => {
            await navigator.clipboard.writeText(description);
            toast("Description and hashtags copied", "success");
          }}
        >
          Description
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
  { value: "designed", label: "Designed" },
  { value: "magazine", label: "Magazine" }, // one-cover music videos: the character in front of huge words (else Bold)
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
    image: detail.thumb_image ?? "",
    v: detail.thumb_v ?? 0,
  };
  const [text, setText] = useState(initial.text);
  const [at, setAt] = useState(initial.at);
  const [style, setStyle] = useState(initial.style);
  const [emphasis, setEmphasis] = useState(initial.emphasis);
  const [image, setImage] = useState(initial.image); // photo instead of a video frame ("" = the frame at `at`)
  const [coverIdea, setCoverIdea] = useState(detail.thumb_suggestions?.idea ?? "");
  const [uploading, setUploading] = useState(false);
  const [saved, setSaved] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [ideas, setIdeas] = useState<ThumbSuggestions | null>(detail.thumb_suggestions ?? null);
  const [ideasV, setIdeasV] = useState(0); // cache buster for re-rendered preview images
  const [suggesting, setSuggesting] = useState(false);
  const frame = useRef<HTMLVideoElement>(null);
  const changed =
    text !== saved.text || at !== saved.at || style !== saved.style || emphasis !== saved.emphasis || image !== saved.image;
  const pickingFrame = !image && (at !== saved.at || !!saved.image);

  useEffect(() => {
    if (frame.current) frame.current.currentTime = at;
  }, [at, pickingFrame]);

  async function generate(cover: { text: string; at: number; style: ThumbStyle; emphasis: string; image: string; design?: string } = { text, at, style, emphasis, image }) {
    setBusy(true);
    try {
      const summary = await api.makeThumbnail(detail.name, cover);
      setText(cover.text);
      setAt(cover.at);
      setStyle(cover.style);
      setEmphasis(cover.emphasis);
      setImage(cover.image);
      setSaved({ text: cover.text, at: cover.at, style: cover.style, emphasis: cover.emphasis, image: cover.image, v: summary.thumb_v });
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
      setIdeas(await api.suggestThumbnails(detail.name, coverIdea));
      setIdeasV(Date.now());
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setSuggesting(false);
    }
  }

  async function uploadPhoto(file: File) {
    setUploading(true);
    try {
      const media = await api.upload(file);
      if (media.kind !== "photo") throw new Error("Use a photo (jpg, png or webp) for the thumbnail.");
      setImage(media.media);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setUploading(false);
    }
  }

  const isCurrent = (i: ThumbSuggestion) =>
    i.text === saved.text && i.at === saved.at && i.style === saved.style && i.emphasis === saved.emphasis && (i.image ?? "") === saved.image;

  return (
    <section aria-label="Thumbnail" className="mx-auto grid w-full max-w-[300px] gap-3 card p-3.5">
      <div className="grid gap-2">
        <label className="field-label" htmlFor={`cover-idea-${detail.name}`}>
          Cover idea <span className="font-normal">optional</span>
        </label>
        <textarea
          id={`cover-idea-${detail.name}`}
          lang={detail.lang}
          rows={2}
          maxLength={600}
          value={coverIdea}
          onChange={(e) => setCoverIdea(e.target.value)}
          placeholder="A silhouette against a neon city at night, the headline asks a question"
          className="field-input resize-y py-1.5 text-base leading-snug"
        />
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm text-ink-soft">Describe the picture, words or mood you want.</span>
          <Button size="sm" variant={ideas && !coverIdea ? "ghost" : "primary"} icon={<Sparkles className="size-3.5" />} loading={suggesting} onClick={suggest}>
            {ideas ? "New ideas" : "Suggest covers"}
          </Button>
        </div>
        {suggesting && <p className="m-0 text-sm text-ink-soft">Claude is picking frames, writing headlines and designing each cover… about a minute.</p>}
        {ideas && (
          <>
            <div className={`grid grid-cols-4 gap-1.5 ${suggesting ? "opacity-50" : ""}`}>
              {ideas.items.map((idea) => (
                <button
                  key={idea.file}
                  type="button"
                  disabled={busy || suggesting}
                  onClick={() => generate({ text: idea.text, at: idea.at, style: idea.style, emphasis: idea.emphasis, image: idea.image ?? "", design: idea.design })}
                  title={`Use “${idea.text}” (${idea.style}, ${idea.image ? "stock photo" : `${idea.at.toFixed(1)} s`})`}
                  aria-label={`Use cover: ${idea.text}`}
                  className={`relative ${detail.aspect === "16:9" ? "aspect-video" : "aspect-[9/16]"} cursor-pointer overflow-hidden rounded-md bg-media outline outline-offset-1 transition hover:brightness-110 disabled:cursor-wait ${
                    isCurrent(idea) ? "outline-2 outline-cobalt" : "outline-1 outline-line"
                  }`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element -- local engine file */}
                  <img src={`${outputUrl(detail.name, idea.file)}?v=${ideasV}`} alt="" className="h-full w-full object-cover" />
                  {idea.image && (
                    <span className="absolute inset-x-0 bottom-0 bg-black/60 py-px text-center text-2xs font-semibold text-white">Photo</span>
                  )}
                  {isCurrent(idea) && (
                    <span className="absolute top-1 right-1 grid size-4 place-items-center rounded-full bg-cobalt text-white">
                      <Check className="size-3" />
                    </span>
                  )}
                </button>
              ))}
            </div>
            <p className="m-0 text-sm text-ink-soft">{ideas.note || "Click one to use it, then fine-tune below."}</p>
          </>
        )}
      </div>
      <div className="flex gap-3">
        <div className={`relative shrink-0 overflow-hidden rounded-md bg-media ${detail.aspect === "16:9" ? "aspect-video w-[132px]" : "aspect-[9/16] w-[84px]"}`}>
          {image && image !== saved.image ? (
            // eslint-disable-next-line @next/next/no-img-element -- local engine file
            <img src={fileUrl(image)} alt="Chosen background photo" className="h-full w-full object-cover" />
          ) : pickingFrame ? (
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
            className="field-input resize-none py-1.5 text-base leading-snug"
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
          className="field-input h-8 text-base"
        />
      </div>
      <div className="grid justify-items-start gap-1">
        <span className="field-label">Style</span>
        <Segmented name="thumb-style" size="sm" value={style} options={THUMB_STYLES} onChange={setStyle} />
        {style === "designed" && (
          <span className="text-sm text-ink-soft">Claude lays out the whole cover. New words keep the design; the first one takes a minute.</span>
        )}
      </div>
      <div className="grid gap-1">
        <label className="field-label flex justify-between" htmlFor="thumb-at">
          {image ? "Background" : "Frame"} <span className="font-normal text-ink-soft tabular-nums">{image ? "photo" : `${at.toFixed(1)} s`}</span>
        </label>
        {image ? (
          <Button size="sm" variant="ghost" className="justify-self-start" icon={<Film className="size-3.5" />} onClick={() => setImage("")}>
            Use a video frame instead
          </Button>
        ) : (
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
        )}
        <label className={`${buttonClass("ghost", "sm")} cursor-pointer justify-self-start ${uploading ? "opacity-60" : ""}`}>
          <ImageUp className="size-3.5" /> {uploading ? "Uploading…" : image ? "Upload another photo" : "Use my own photo"}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            disabled={uploading}
            onChange={(e) => {
              const f = e.target.files?.[0];
              e.target.value = "";
              if (f) void uploadPhoto(f);
            }}
          />
        </label>
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

/** The finished video's covers, post text, fact check and publishing (the editor's Export panel). */
export function ExportCards({ detail, onThumbnail, onDeleteVideo, onOpenSettings }: {
  detail: VideoDetail;
  onThumbnail: (summary: VideoSummary) => void;
  onDeleteVideo: (name: string) => void;
  onOpenSettings: () => void;
}) {
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-4">
      <ThumbnailCard key={`thumb-${detail.name}`} detail={detail} onChange={onThumbnail} />
      <PostCard key={`post-${detail.name}`} detail={detail} onDelete={onDeleteVideo} />
      <FactsCard key={`facts-${detail.name}`} detail={detail} />
      <PublishCard key={`publish-${detail.name}`} detail={detail} onOpenSettings={onOpenSettings} />
    </div>
  );
}

export function PreviewPane({
  live,
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
  onOpenSettings,
  variant = "full",
}: {
  variant?: "full" | "stage"; // stage: only the player, filling the space it gets (the editor's centre)
  live: { timeline: DraftTimeline; music: string; edit: FrameEdits; options: Options | null } | null; // the open draft
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
  onMakeMusicVideo: (name: string, settings: MusicVideoSettings) => void;
  onOpenTiming: (name: string) => void;
  onSelectVideo: (name: string) => void;
  onOpenSettings: () => void;
}) {
  const showProgress = rendering || job?.status === "error";
  const canToggle = !!scene && !!detail?.video && !showProgress;
  const showVideo = !showProgress && !!detail?.video && (view === "video" || !scene);
  const isSong = !showProgress && !scene && detail?.kind === "song" && detail.audio;
  const showSong = isSong && !showVideo;
  const landscape = !showProgress && !scene && detail?.aspect === "16:9";
  const title = showProgress
    ? job?.kind === "song" ? "Composing" : job?.kind === "lyrics_sync" ? "Syncing lyrics" : "Rendering"
    : showVideo ? (detail?.kind === "music_video" ? "Music video" : "Video") : showSong ? "Song" : "Preview";
  const toggle = canToggle && (
    <Segmented
      size="sm"
      name="preview-view"
      value={view}
      onChange={onView}
      options={[
        { value: "scene", label: "Edit" },
        { value: "video", label: "Rendered" },
      ]}
    />
  );
  const screen = showProgress ? (
    <Progress job={job} title={job?.kind === "excel" ? job.title : jobTitle} />
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
  ) : scene && live?.timeline.active ? (
    <LiveFrame timeline={live.timeline} lang={lang} edit={live.edit} />
  ) : scene ? (
    <ScenePreview scene={scene} index={sceneIndex} total={sceneCount} lang={lang} />
  ) : (
    <div className="grid h-full place-items-center p-7 text-center">
      <p className="m-0 font-display text-2xl leading-tight font-extrabold">
        <mark>Your video</mark> shows up here
      </p>
    </div>
  );

  if (variant === "stage") {
    return (
      <div className="flex h-full min-h-0 flex-col">
        <div className="flex h-11 shrink-0 items-center justify-between gap-2 px-4">
          <span className="text-sm font-semibold tracking-wide text-ink-soft uppercase">{title}</span>
          {toggle}
        </div>
        {/* a size container: the frame takes the most room its shape fits in */}
        <div className="min-h-0 flex-1 px-4 [container-type:size]">
          <div className="grid h-full place-items-center">
            <div style={{ width: landscape ? "min(100cqw, calc(100cqh * 16 / 9))" : "min(100cqw, calc(100cqh * 9 / 16))" }}>
              <Phone landscape={landscape} fit>
                {screen}
              </Phone>
            </div>
          </div>
        </div>
        <div className="mx-auto w-full max-w-[560px] shrink-0 px-4 pt-3 pb-3">
          {!showProgress && !showVideo && scene && live ? (
            <LiveControls timeline={live.timeline} music={live.music} />
          ) : (
            showVideo && <p className="m-0 text-center text-sm text-ink-soft">The rendered video. Switch to Edit to keep changing the draft, then render again.</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start">
      <div className="pane-header sticky top-0 z-10 px-5">
        <h2 className="pane-title m-0">{title}</h2>
        {toggle}
      </div>

      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-4 p-5">
        <Phone landscape={landscape}>{screen}</Phone>

        {!showProgress && !showVideo && scene && live && <LiveControls timeline={live.timeline} music={live.music} />}
        {!showProgress && !showVideo && scene && live?.options && (
          <CaptionPanel style={live.edit.captions} onChange={live.edit.setCaptions} options={live.options} lang={lang} />
        )}
        {!showProgress && !showVideo && scene && !live && (
          <p className="m-0 text-center text-sm text-ink-soft">Approximate look of the scene you&apos;re editing. Click a scene to preview it.</p>
        )}
        {showVideo && detail && <ThumbnailCard key={`thumb-${detail.name}`} detail={detail} onChange={onThumbnail} />}
        {showVideo && detail?.kind === "music_video" && (
          <section className="grid gap-1.5 card p-3.5">
            {detail.song_folder ? (
              <>
                <Button variant="secondary" icon={<ListMusic className="size-4" />} onClick={() => onOpenTiming(detail.song_folder)}>
                  Edit lyric timing
                </Button>
                {detail.idea && (
                  <p className="m-0 text-sm text-ink-soft">
                    Made with the idea: <span className="text-ink">{detail.idea}</span>
                  </p>
                )}
                <p className="m-0 text-sm text-ink-soft">This video stays as it is. Fix the timing, then make a new version from the song.</p>
              </>
            ) : (
              <p className="m-0 text-sm text-ink-soft">The song this video was made from has been deleted, so its timing can&apos;t be edited.</p>
            )}
          </section>
        )}
        {isSong && detail && (
          <SongCard key={`song-${detail.name}`} detail={detail} onDelete={onDeleteVideo} onMakeVideo={onMakeMusicVideo} onOpenTiming={onOpenTiming} onSelectVideo={onSelectVideo} />
        )}
        {showVideo && detail && <PostCard key={`post-${detail.name}`} detail={detail} onDelete={onDeleteVideo} />}
        {showVideo && detail && <FactsCard key={`facts-${detail.name}`} detail={detail} />}
        {showVideo && detail && <PublishCard key={`publish-${detail.name}`} detail={detail} onOpenSettings={onOpenSettings} />}
      </div>
    </div>
  );
}
