"use client";

import { CalendarClock, ExternalLink, ImageUp, MessageSquare, Settings as SettingsIcon, Upload, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api, autostartLabel, isMac, outputUrl, type CommentState, type Job, type ThumbnailState, type Platform, type PublishAccounts, type Published, type ScheduledUpload, type TikTokCreator, type TikTokPost, type TikTokPrivacy, type VideoDetail, type YouTubeOptions } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import { PLATFORM_NAMES as NAMES, PLATFORMS } from "./Settings";
import { Button, IconButton, useToast } from "./ui";

/** Local "YYYY-MM-DDTHH:MM" for a datetime-local input: the next full hour. */
function nextHour(): string {
  const d = new Date(Date.now() + 60 * 60 * 1000);
  d.setMinutes(0, 0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:00`;
}

/** The next full hour at least 15 minutes away: Facebook schedules posts 10 minutes ahead or more. */
function fbNextHour(): string {
  const at = nextHour();
  if (new Date(at).getTime() - Date.now() >= 15 * 60_000) return at;
  const d = new Date(new Date(at).getTime() + 60 * 60_000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:00`;
}

const YT_VISIBILITY = [
  { value: "public", label: "Public" },
  { value: "unlisted", label: "Unlisted" },
  { value: "private", label: "Private" },
  { value: "schedule", label: "Schedule" },
];

const TT_VISIBILITY: { value: TikTokPrivacy | "DRAFT" | "SCHEDULE"; label: string }[] = [
  { value: "PUBLIC_TO_EVERYONE", label: "Everyone" },
  { value: "MUTUAL_FOLLOW_FRIENDS", label: "Friends" },
  { value: "FOLLOWER_OF_CREATOR", label: "Followers" },
  { value: "SELF_ONLY", label: "Only me" },
  { value: "DRAFT", label: "Drafts (finish in the TikTok app)" },
  { value: "SCHEDULE", label: "Schedule (goes public later)" },
];
type TikTokChoice = TikTokPrivacy | "DRAFT" | "SCHEDULE";

// TikTok's Direct Post guidelines: every interaction and disclosure starts off; the creator turns on what they want
const TT_POST_OFF: TikTokPost = { allow_comment: false, allow_duet: false, allow_stitch: false, brand_organic: false, brand_content: false };
const TT_MUSIC_URL = "https://www.tiktok.com/legal/page/global/music-usage-confirmation/en";
const TT_BRANDED_URL = "https://www.tiktok.com/legal/page/global/bc-policy/en";

const when = (at: string) =>
  new Date(at).toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

const TAGS_MAX = 500;
const tagCost = (tags: string[]) => tags.reduce((n, t, i) => n + t.length + (t.includes(" ") ? 2 : 0) + (i ? 1 : 0), 0);

const COMMENT_MAX = 9000;

/** The video's YouTube tags, thumbnail and comment, saved with the video so every upload of it (auto too) uses them. */
function YouTubeExtras({ detail }: { detail: VideoDetail }) {
  const toast = useToast();
  const [options, setOptions] = useState<YouTubeOptions | null>(detail.youtube ?? null);
  const [text, setText] = useState((detail.youtube?.tags ?? []).join(", "));
  const [comment, setComment] = useState(detail.youtube?.comment ?? "");
  if (!options) return null;
  const typed = text.split(",").map((t) => t.trim()).filter(Boolean);

  async function save(patch: Parameters<typeof api.saveYouTubeOptions>[1]) {
    try {
      const next = await api.saveYouTubeOptions(detail.name, patch);
      setOptions(next);
      setText(next.tags.join(", "));
      setComment(next.comment ?? "");
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  const coverShown = options.thumbnail === "cover" || (options.thumbnail === "auto" && !options.short);
  return (
    <div className="grid gap-1.5">
      <label className="grid gap-1 text-sm text-ink-soft">
        <span className="flex items-center justify-between">
          Tags
          <span className={`tabular-nums ${tagCost(typed) > TAGS_MAX ? "text-danger" : ""}`}>
            {tagCost(typed)}/{TAGS_MAX}
          </span>
        </span>
        <input
          className="field-input h-8 py-0 text-sm"
          value={text}
          placeholder="cat facts, cats, slow blink"
          onChange={(e) => setText(e.target.value)}
          onBlur={() => typed.join(",") !== options.tags.join(",") && save({ tags: typed })}
          onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
        />
      </label>
      <span className="text-xs leading-snug text-ink-soft">
        {options.custom_tags ? (
          <button type="button" className="cursor-pointer bg-transparent p-0 text-xs text-cobalt underline" onClick={() => save({ reset_tags: true })}>
            Use the hashtags instead
          </button>
        ) : (
          "From the hashtags; separate with commas to change them."
        )}
      </span>
      <div className="flex items-center gap-2">
        {detail.thumb && (
          // eslint-disable-next-line @next/next/no-img-element -- local engine file
          <img
            src={`${outputUrl(detail.name, "thumbnail.jpg")}?v=${detail.thumb_v}`}
            alt="Cover"
            className={`h-12 shrink-0 rounded border border-line object-cover ${coverShown ? "" : "opacity-40"}`}
            style={{ aspectRatio: detail.aspect === "16:9" ? "16/9" : "9/16" }}
          />
        )}
        <label className="grid min-w-0 flex-1 gap-1 text-sm text-ink-soft">
          Thumbnail
          <select className="field-input h-8 py-0 text-sm" value={options.thumbnail} onChange={(e) => save({ thumbnail: e.target.value as YouTubeOptions["thumbnail"] })}>
            <option value="auto">{options.short ? "Auto (YouTube picks for Shorts)" : "Auto (my cover)"}</option>
            <option value="cover">Use my cover</option>
            <option value="youtube">Let YouTube pick</option>
          </select>
        </label>
      </div>
      {options.short && options.thumbnail === "cover" && (
        <span className="text-xs leading-snug text-ink-soft">Shorts may still show a frame in the Shorts feed; your cover shows on your channel and in search.</span>
      )}
      {options.comment !== undefined && (
        <label className="grid gap-1 text-sm text-ink-soft">
          <span className="flex items-center justify-between">
            Comment to pin
            <span className={`tabular-nums ${comment.length > COMMENT_MAX ? "text-danger" : ""}`}>{comment.length > 200 ? `${comment.length}/${COMMENT_MAX}` : ""}</span>
          </span>
          <textarea
            rows={3}
            maxLength={COMMENT_MAX}
            className="field-input field-sizing-content min-h-[60px] resize-none text-sm leading-snug"
            value={comment}
            placeholder="e.g. Which line hit you the most? 🎧 Full lyrics in the description."
            onChange={(e) => setComment(e.target.value)}
            onBlur={() => comment.trim() !== (options.comment ?? "") && save({ comment })}
          />
        </label>
      )}
      {options.comment !== undefined && (
        <span className="text-xs leading-snug text-ink-soft">
          Posted from your channel right after the upload; pin it in YouTube Studio → Comments (YouTube doesn&apos;t let apps pin).
          {options.custom_comment && !detail.script?.pinned_comment ? null : options.custom_comment ? (
            <>
              {" "}
              <button type="button" className="cursor-pointer bg-transparent p-0 text-xs text-cobalt underline" onClick={() => save({ reset_comment: true })}>
                Use the fact-check comment instead
              </button>
            </>
          ) : comment ? (
            " Written by Claude from the video's sources; edit it to make it yours."
          ) : null}
        </span>
      )}
    </div>
  );
}

/** Post the comment under a video that is already on YouTube (uploaded without one, or posting failed). */
function PostCommentButton({ name, onPosted }: { name: string; onPosted: (s: CommentState) => void }) {
  const [busy, setBusy] = useState(false);
  return (
    <Button
      size="sm"
      variant="secondary"
      className="mt-1 justify-self-start"
      icon={<MessageSquare className="size-3.5" />}
      loading={busy}
      onClick={async () => {
        setBusy(true);
        try {
          onPosted(await api.postYouTubeComment(name));
        } catch (e) {
          onPosted({ status: "error", error: (e as Error).message });
        } finally {
          setBusy(false);
        }
      }}
    >
      Post comment now
    </Button>
  );
}

/** How the video's fact-check comment went on YouTube. */
function CommentLine({ state }: { state: CommentState }) {
  const text = {
    posted: "Comment posted: pin it in YouTube Studio > Comments.",
    pending: `Comment posts when it goes public${state.at ? ` (${when(state.at)})` : ""}.`,
    skipped: `No comment: ${state.error ?? "it's private"}`,
    error: `Comment not posted: ${state.error ?? "unknown error"}`,
  }[state.status];
  return <span className={`block ${state.status === "error" ? "text-danger" : ""}`}>{text}</span>;
}

/** Whether the cover became the YouTube thumbnail; when YouTube refused, why, and a way to try again. */
function ThumbnailLine({ name, state, onChange }: { name: string; state: ThumbnailState; onChange: (s: ThumbnailState) => void }) {
  const [busy, setBusy] = useState(false);
  if (state.status === "set") return <span className="block">Cover set as the thumbnail.</span>;
  return (
    <span role="alert" className="mt-1 grid gap-1 rounded-md bg-danger/[0.07] px-2 py-1.5 text-danger">
      <span>{state.error ?? "The cover wasn't set as the thumbnail."}</span>
      <Button
        size="sm"
        variant="secondary"
        className="justify-self-start"
        icon={<ImageUp className="size-3.5" />}
        loading={busy}
        onClick={async () => {
          setBusy(true);
          try {
            onChange(await api.setYouTubeThumbnail(name));
          } catch (e) {
            onChange({ status: "error", error: (e as Error).message });
          } finally {
            setBusy(false);
          }
        }}
      >
        Set cover again
      </Button>
    </span>
  );
}

/** TikTok's Direct Post choices: who may comment, Duet and Stitch, the commercial content disclosure and the
 * consent line. Interactions the creator turned off in TikTok can't be turned on here. */
function TikTokPostOptions({
  creator,
  post,
  setPost,
  disclose,
  setDisclose,
  privacy,
}: {
  creator: TikTokCreator | null;
  post: TikTokPost;
  setPost: (p: TikTokPost) => void;
  disclose: boolean;
  setDisclose: (on: boolean) => void;
  privacy: TikTokChoice;
}) {
  const interactions: { key: "allow_comment" | "allow_duet" | "allow_stitch"; label: string; off: boolean }[] = [
    { key: "allow_comment", label: "Comment", off: !!creator?.comment_disabled },
    { key: "allow_duet", label: "Duet", off: !!creator?.duet_disabled },
    { key: "allow_stitch", label: "Stitch", off: !!creator?.stitch_disabled },
  ];
  const selfOnly = privacy === "SELF_ONLY";
  return (
    <div className="grid gap-1.5 pt-1 text-sm">
      <fieldset className="m-0 grid gap-1 border-0 p-0">
        <legend className="p-0 text-xs font-semibold text-ink-soft">Allow users to</legend>
        <div className="flex flex-wrap gap-3">
          {interactions.map((i) => (
            <label
              key={i.key}
              className={`flex items-center gap-1.5 ${i.off ? "opacity-50" : ""}`}
              title={i.off ? `${i.label} is turned off in your TikTok settings` : undefined}
            >
              <input
                type="checkbox"
                className="size-4 accent-cobalt"
                disabled={i.off}
                checked={!i.off && post[i.key]}
                onChange={(e) => setPost({ ...post, [i.key]: e.target.checked })}
              />
              {i.label}
            </label>
          ))}
        </div>
      </fieldset>
      <label className="flex items-center gap-1.5 font-semibold">
        <input type="checkbox" className="size-4 accent-cobalt" checked={disclose} onChange={(e) => setDisclose(e.target.checked)} />
        Disclose video content
      </label>
      {disclose && (
        <div className="grid gap-1 pl-5">
          <p className="m-0 text-xs leading-snug text-ink-soft">Turn on if this video promotes goods or services in exchange for something of value.</p>
          <label className="flex items-start gap-1.5">
            <input
              type="checkbox"
              className="mt-0.5 size-4 accent-cobalt"
              checked={post.brand_organic}
              onChange={(e) => setPost({ ...post, brand_organic: e.target.checked })}
            />
            <span>
              <b>Your brand</b>
              <span className="block text-xs text-ink-soft">You&apos;re promoting yourself or your own business.</span>
            </span>
          </label>
          <label className={`flex items-start gap-1.5 ${selfOnly ? "opacity-50" : ""}`}>
            <input
              type="checkbox"
              className="mt-0.5 size-4 accent-cobalt"
              disabled={selfOnly}
              checked={!selfOnly && post.brand_content}
              onChange={(e) => setPost({ ...post, brand_content: e.target.checked })}
            />
            <span>
              <b>Branded content</b>
              <span className="block text-xs text-ink-soft">
                {selfOnly ? <>Branded content can&apos;t be posted as &quot;Only me&quot;.</> : <>You&apos;re promoting another brand or a third party.</>}
              </span>
            </span>
          </label>
          {post.brand_organic || (post.brand_content && !selfOnly) ? (
            <p className="m-0 text-xs leading-snug text-ink-soft">
              Your video will be labeled &quot;{post.brand_content && !selfOnly ? "Paid partnership" : "Promotional content"}&quot;.
            </p>
          ) : (
            <p className="m-0 text-xs leading-snug text-danger">Pick whether you&apos;re promoting your own brand, another brand, or both.</p>
          )}
        </div>
      )}
      <p className="m-0 text-xs leading-snug text-ink-soft">
        By posting, you agree to TikTok&apos;s{" "}
        {disclose && post.brand_content && !selfOnly && (
          <>
            <a href={TT_BRANDED_URL} target="_blank" rel="noreferrer" className="underline">
              Branded Content Policy
            </a>{" "}
            and{" "}
          </>
        )}
        <a href={TT_MUSIC_URL} target="_blank" rel="noreferrer" className="underline">
          Music Usage Confirmation
        </a>
        .
      </p>
    </div>
  );
}

/** Upload the rendered video (with its post text) to the connected channels. Connecting happens in Settings. */
export function PublishCard({ detail, onOpenSettings }: { detail: VideoDetail; onOpenSettings: () => void }) {
  const toast = useToast();
  const [accounts, setAccounts] = useState<PublishAccounts | null>(null);
  const [done, setDone] = useState<Partial<Record<Platform, Published>>>(detail.published ?? {});
  const [running, setRunning] = useState<Partial<Record<Platform, Job>>>({});

  const [queue, setQueue] = useState<ScheduledUpload[]>([]);
  const [planning, setPlanning] = useState(false); // the schedule form is open
  const [at, setAt] = useState(nextHour);
  const [targets, setTargets] = useState<Platform[]>([]);
  const [scheduling, setScheduling] = useState(false);

  // YouTube visibility for the next upload, like YouTube Studio's last step; "schedule" goes public at ytAt
  const [ytVisibility, setYtVisibility] = useState<string | null>(null); // null: the channel's default (Settings)
  const [ytAt, setYtAt] = useState(nextHour);
  const [ytCategory, setYtCategory] = useState(""); // "" = the default from Settings
  const [ytChannel, setYtChannel] = useState(""); // channel id; "" = the default channel from Settings
  // TikTok visibility for the next upload; null = Settings. TikTok says which levels the account may use.
  const [ttVisibility, setTtVisibility] = useState<TikTokChoice | null>(null);
  const [ttAt, setTtAt] = useState(nextHour); // when a scheduled TikTok post goes out
  const [ttCreator, setTtCreator] = useState<TikTokCreator | null>(null);
  const [ttPost, setTtPost] = useState<TikTokPost>(TT_POST_OFF); // interactions and disclosure for a direct post
  const [ttDisclose, setTtDisclose] = useState(false); // "Disclose video content" is on
  const [fbSchedule, setFbSchedule] = useState(false); // Facebook: upload now, Facebook publishes it at fbAt
  const [fbAt, setFbAt] = useState(fbNextHour);

  const tiktokConnected = !!accounts?.tiktok.connected;
  useEffect(() => {
    if (tiktokConnected) api.tiktokCreator().then(setTtCreator).catch(() => {});
  }, [tiktokConnected]);

  useEffect(() => {
    api.publishAccounts().then(setAccounts).catch(() => {});
    api
      .schedule(detail.name)
      .then((items) => setQueue(items.filter((i) => i.status === "scheduled" || i.status === "uploading")))
      .catch(() => {});
  }, [detail.name]);

  async function schedule(platforms: Platform[]) {
    setScheduling(true);
    try {
      const added = await api.scheduleVideo(detail.name, platforms, at, ytChannel);
      setQueue((q) => [...q, ...added].sort((a, b) => a.at.localeCompare(b.at)));
      setPlanning(false);
      toast(`Scheduled for ${when(at)}`, "success");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setScheduling(false);
    }
  }

  // follow running uploads until they finish
  const active = (Object.entries(running) as [Platform, Job | undefined][])
    .filter(([, j]) => j && j.status !== "error")
    .map(([p, j]) => `${p}:${j!.id}`)
    .join(",");
  useEffect(() => {
    if (!active) return;
    const t = window.setInterval(async () => {
      for (const pair of active.split(",")) {
        const [p, id] = pair.split(":") as [Platform, string];
        let job: Job;
        try {
          job = await api.job(id);
        } catch {
          continue; // the engine may be restarting; try again next tick
        }
        if (job.status === "done") {
          const publishAt = job.publish_at || undefined;
          setDone((d) => ({
            ...d,
            [p]: {
              id: "",
              url: job.url ?? "",
              at: new Date().toISOString(),
              draft: p === "tiktok" && !job.url,
              publish_at: publishAt,
              comment: job.comment ?? undefined,
              thumbnail: job.thumbnail ?? undefined,
              ...(p === "youtube" ? { channel_name: job.channel_name ?? undefined } : {}),
            },
          }));
          setRunning((r) => ({ ...r, [p]: undefined }));
          toast(publishAt ? `Uploaded to ${NAMES[p]}, goes public ${when(publishAt)}` : `Uploaded to ${NAMES[p]}`, "success");
        } else {
          if (job.status === "error") toast(job.error ?? `${NAMES[p]} upload failed`, "error");
          setRunning((r) => ({ ...r, [p]: job }));
        }
      }
    }, 2000);
    return () => window.clearInterval(t);
  }, [active, toast]);

  async function upload(platforms: Platform[]) {
    const visibility = ytVisibility ?? accounts?.youtube.privacy;
    // TikTok can't schedule a post itself: the app keeps it and posts it publicly at that time
    if (platforms.includes("tiktok") && ttChoice === "SCHEDULE") {
      platforms = platforms.filter((p) => p !== "tiktok");
      try {
        const added = await api.scheduleVideo(detail.name, ["tiktok"], ttAt, "", ttPublic);
        setQueue((q) => [...q, ...added].sort((a, b) => a.at.localeCompare(b.at)));
        toast(`TikTok post scheduled for ${when(ttAt)}`, "success");
      } catch (e) {
        toast((e as Error).message, "error");
      }
      if (!platforms.length) return;
    }
    try {
      const { jobs } = await api.publishVideo(
        detail.name,
        platforms,
        {
          ...(visibility === "schedule" ? { publish_at: ytAt } : visibility ? { privacy: visibility } : {}),
          ...(ytCategory ? { category: ytCategory } : {}),
          ...(ytChannel ? { channel: ytChannel } : {}),
          ...(platforms.includes("tiktok") && ttChoice && ttChoice !== "SCHEDULE" ? { tiktok_privacy: ttChoice } : {}),
          ...(platforms.includes("tiktok") && ttDirect
            ? { tiktok_post: { ...ttPost, brand_organic: ttDisclose && ttPost.brand_organic, brand_content: ttBranded } }
            : {}),
          ...(platforms.includes("facebook") && fbSchedule ? { facebook_publish_at: fbAt } : {}),
        },
      );
      for (const p of platforms) {
        const id = jobs[p];
        if (id) setRunning((r) => ({ ...r, [p]: { id, status: "queued", step: 0, log: [], title: "" } }));
      }
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  if (!detail.video || !accounts) return null;
  // the TikTok visibility shown: your pick, else Settings; only levels TikTok allows this account (and Drafts)
  const ttAllowed = TT_VISIBILITY.filter(
    (o) => o.value === "DRAFT" || o.value === "SCHEDULE" || !ttCreator || ttCreator.privacy_options.includes(o.value as TikTokPrivacy),
  );
  const ttDefault: TikTokChoice = accounts.tiktok.mode === "draft" ? "DRAFT" : (accounts.tiktok.privacy as TikTokPrivacy);
  // a scheduled post goes out public (Everyone), or as the most open level TikTok allows this account
  const ttPublic: TikTokPrivacy = (ttCreator?.privacy_options ?? ["PUBLIC_TO_EVERYONE"]).includes("PUBLIC_TO_EVERYONE")
    ? "PUBLIC_TO_EVERYONE"
    : (ttCreator?.privacy_options[0] ?? "SELF_ONLY");
  const ttChoice = ttVisibility ?? (ttAllowed.some((o) => o.value === ttDefault) ? ttDefault : ttAllowed[0].value);
  const ttDirect = ttChoice !== "DRAFT" && ttChoice !== "SCHEDULE"; // posts now, so the post settings apply
  const ttBranded = ttDisclose && ttPost.brand_content && ttChoice !== "SELF_ONLY"; // branded content can't be private
  // disclosure on but neither kind picked: TikTok asks the creator to pick one before posting
  const ttBlocked = ttDirect && ttDisclose && !ttPost.brand_organic && !ttBranded;
  const connected = PLATFORMS.filter((p) => accounts[p]?.connected);
  const busy = (p: Platform) => !!running[p] && running[p].status !== "error";
  const channels = accounts.youtube.channels ?? [];

  return (
    <section aria-labelledby={`publish-${detail.name}`} className="mx-auto w-full max-w-[300px] card [&_.grid]:grid-cols-[minmax(0,1fr)] [&_select]:max-w-full [&_select]:min-w-0">
      <header className="flex items-center justify-between gap-2 px-3.5 pt-3 pb-2">
        <h3 id={`publish-${detail.name}`} className="m-0 font-display text-md font-bold">
          Upload
        </h3>
        {connected.length > 1 && (
          <Button size="sm" variant="primary" icon={<Upload className="size-3.5" />} disabled={connected.some(busy) || (connected.includes("tiktok") && ttBlocked)} onClick={() => upload(connected)}>
            Upload to both
          </Button>
        )}
      </header>
      {connected.length === 0 ? (
        <div className="grid gap-2 px-3.5 pb-3.5">
          <p className="m-0 text-sm leading-snug text-ink-soft">Connect YouTube or TikTok to upload this video with its title and description.</p>
          <Button size="sm" variant="secondary" icon={<SettingsIcon className="size-3.5" />} onClick={onOpenSettings} className="justify-self-start">
            Set up channels
          </Button>
        </div>
      ) : (
        <>
          <ul className="m-0 grid list-none p-0">
            {connected.map((p) => {
              const job = running[p];
              const prev = done[p];
              return (
                <li key={p} className="grid gap-1 border-t border-line px-3.5 py-2.5">
                  <div className="flex items-center gap-2">
                    {p === "youtube" && channels.length > 1 ? (
                      <label className="flex min-w-0 flex-1 items-center gap-1.5 text-base">
                        <b>{NAMES[p]}</b>
                        <select
                          aria-label="YouTube channel"
                          className="field-input h-8 w-auto min-w-0 flex-1 py-0 text-sm"
                          value={ytChannel || accounts.youtube.channel || ""}
                          disabled={busy(p)}
                          onChange={(e) => setYtChannel(e.target.value === accounts.youtube.channel ? "" : e.target.value)}
                        >
                          {channels.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name || c.id}
                            </option>
                          ))}
                        </select>
                      </label>
                    ) : (
                      <span className="min-w-0 flex-1 truncate text-base">
                        <b>{NAMES[p]}</b> <span className="text-ink-soft">{accounts[p].account}</span>
                      </span>
                    )}
                    <Button size="sm" variant={prev ? "ghost" : "secondary"} icon={<Upload className="size-3.5" />} loading={busy(p)} disabled={p === "tiktok" && ttBlocked} onClick={() => upload([p])}>
                      {(p === "youtube" && (ytVisibility ?? accounts.youtube.privacy) === "schedule") ||
                      (p === "tiktok" && ttChoice === "SCHEDULE") ||
                      (p === "facebook" && fbSchedule)
                        ? "Schedule"
                        : prev
                          ? "Upload again"
                          : "Upload"}
                    </Button>
                  </div>
                  {p === "youtube" && !busy(p) && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      <label className="sr-only" htmlFor={`yt-visibility-${detail.name}`}>
                        YouTube visibility
                      </label>
                      <select
                        id={`yt-visibility-${detail.name}`}
                        className="field-input h-8 w-auto py-0 text-sm"
                        value={ytVisibility ?? accounts.youtube.privacy}
                        onChange={(e) => {
                          if (e.target.value === "schedule" && ytVisibility !== "schedule") setYtAt(nextHour());
                          setYtVisibility(e.target.value);
                        }}
                      >
                        {YT_VISIBILITY.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                      {(ytVisibility ?? accounts.youtube.privacy) === "schedule" && (
                        <input
                          type="datetime-local"
                          aria-label="Goes public at"
                          className="field-input h-8 min-w-0 flex-1 py-0 text-sm"
                          value={ytAt}
                          onChange={(e) => setYtAt(e.target.value)}
                        />
                      )}
                    </div>
                  )}
                  {p === "tiktok" && !busy(p) && (
                    <div className="grid gap-1">
                      <label className="sr-only" htmlFor={`tt-visibility-${detail.name}`}>
                        TikTok visibility
                      </label>
                      <select
                        id={`tt-visibility-${detail.name}`}
                        className="field-input h-8 w-auto justify-self-start py-0 text-sm"
                        value={ttChoice}
                        onChange={(e) => {
                          if (e.target.value === "SCHEDULE" && ttVisibility !== "SCHEDULE") setTtAt(nextHour());
                          setTtVisibility(e.target.value as TikTokChoice);
                        }}
                      >
                        {ttAllowed.map((o) => (
                          <option key={o.value} value={o.value} disabled={ttBranded && o.value === "SELF_ONLY"}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                      {ttCreator && ttCreator.privacy_options.length === 1 && ttCreator.privacy_options[0] === "SELF_ONLY" && (
                        <p className="m-0 text-xs leading-snug text-ink-soft">
                          Until TikTok audits this app it can only post as &quot;Only me&quot;, and only to a private TikTok account (TikTok → Settings and
                          privacy → Privacy → Private account). Choose Drafts to post publicly from the TikTok app instead.
                        </p>
                      )}
                      {ttChoice === "SCHEDULE" && (
                        <>
                          <input
                            type="datetime-local"
                            aria-label="TikTok post goes public at"
                            className="field-input h-8 min-w-0 py-0 text-sm"
                            value={ttAt}
                            onChange={(e) => setTtAt(e.target.value)}
                          />
                          <p className="m-0 text-xs leading-snug text-ink-soft">
                            Posts as {TT_VISIBILITY.find((o) => o.value === ttPublic)?.label} at this time. TikTok can&apos;t schedule posts from apps, so Shorts
                            Studio posts it then. It keeps running in the {isMac() ? "menu bar" : "tray"} when you close the window; turn on Settings →{" "}
                            {autostartLabel()} so it runs after a restart too.
                          </p>
                        </>
                      )}
                      {ttChoice === "DRAFT" && (
                        <p className="m-0 text-xs leading-snug text-ink-soft">Goes to your TikTok inbox; open TikTok to add sounds or edits and post it.</p>
                      )}
                      {ttDirect && (
                        <TikTokPostOptions creator={ttCreator} post={ttPost} setPost={setTtPost} disclose={ttDisclose} setDisclose={setTtDisclose} privacy={ttChoice} />
                      )}
                    </div>
                  )}
                  {p === "facebook" && !busy(p) && (
                    <div className="grid gap-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <label className="sr-only" htmlFor={`fb-when-${detail.name}`}>
                          When it goes public on Facebook
                        </label>
                        <select
                          id={`fb-when-${detail.name}`}
                          className="field-input h-8 w-auto py-0 text-sm"
                          value={fbSchedule ? "schedule" : "now"}
                          onChange={(e) => {
                            if (e.target.value === "schedule" && !fbSchedule) setFbAt(fbNextHour());
                            setFbSchedule(e.target.value === "schedule");
                          }}
                        >
                          <option value="now">Post now</option>
                          <option value="schedule">Schedule</option>
                        </select>
                        {fbSchedule && (
                          <input
                            type="datetime-local"
                            aria-label="Facebook post goes public at"
                            className="field-input h-8 min-w-0 flex-1 py-0 text-sm"
                            value={fbAt}
                            onChange={(e) => setFbAt(e.target.value)}
                          />
                        )}
                      </div>
                      {fbSchedule && (
                        <p className="m-0 text-xs leading-snug text-ink-soft">
                          Uploads now; Facebook publishes it at this time, even if the app is closed (10 minutes to 28 days ahead). You&apos;ll find it in
                          Meta Business Suite → Planner.
                        </p>
                      )}
                    </div>
                  )}
                  {p === "youtube" && !busy(p) && <YouTubeExtras key={detail.name} detail={detail} />}
                  {p === "youtube" && !busy(p) && accounts.youtube_categories && (
                    <label className="flex items-center gap-1.5 text-sm text-ink-soft">
                      Category
                      <select className="field-input h-8 w-auto min-w-0 flex-1 py-0 text-sm" value={ytCategory} onChange={(e) => setYtCategory(e.target.value)}>
                        <option value="">
                          Default (
                          {accounts.youtube_categories[accounts.youtube.category ?? ""] ??
                            accounts.youtube_categories[detail.kind === "music_video" ? "10" : "22"]}
                          )
                        </option>
                        {Object.entries(accounts.youtube_categories).map(([id, name]) => (
                          <option key={id} value={id}>
                            {name}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                  {p === "youtube" && !busy(p) && (ytVisibility ?? accounts.youtube.privacy) === "schedule" && (
                    <p className="m-0 text-xs leading-snug text-ink-soft">Uploads now as private; YouTube makes it public at this time, even if the app is closed.</p>
                  )}
                  {job ? (
                    <p className={`m-0 text-sm leading-snug ${job.status === "error" ? "text-danger" : "text-ink-soft"}`}>
                      {job.status === "error" ? job.error : (job.log.at(-1) ?? "Waiting to upload…")}
                    </p>
                  ) : prev ? (
                    <p className="m-0 text-sm leading-snug text-ink-soft">
                      {prev.draft ? "Sent to TikTok drafts" : "Uploaded"}
                      {p === "tiktok" && !prev.draft && prev.privacy && ` as ${TT_VISIBILITY.find((o) => o.value === prev.privacy)?.label ?? prev.privacy}`}
                      {p === "youtube" && channels.length > 1 && prev.channel_name ? ` to ${prev.channel_name}` : ""} {relativeTime(prev.at)}
                      {prev.publish_at && new Date(prev.publish_at) > new Date() && `, goes public ${when(prev.publish_at)}`}
                      {prev.url && (
                        <>
                          {", "}
                          <a href={prev.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-cobalt">
                            view <ExternalLink className="size-3" />
                          </a>
                        </>
                      )}
                      {prev.comment && <CommentLine state={prev.comment} />}
                      {p === "youtube" && !prev.draft && prev.comment?.status !== "posted" && prev.comment?.status !== "pending" && (
                        <PostCommentButton
                          name={detail.name}
                          onPosted={(comment) => setDone((d) => (d.youtube ? { ...d, youtube: { ...d.youtube, comment } } : d))}
                        />
                      )}
                      {p === "youtube" && prev.thumbnail && (
                        <ThumbnailLine
                          name={detail.name}
                          state={prev.thumbnail}
                          onChange={(thumbnail) => setDone((d) => (d.youtube ? { ...d, youtube: { ...d.youtube, thumbnail } } : d))}
                        />
                      )}
                    </p>
                  ) : accounts[p].auto ? (
                    <p className="m-0 text-sm leading-snug text-ink-soft">
                      {accounts[p].when === "slots"
                        ? `New renders upload at ${accounts[p].times.join(", ")}.`
                        : "New renders upload automatically."}
                    </p>
                  ) : null}
                </li>
              );
            })}
          </ul>
          {queue.length > 0 && (
            <ul aria-label="Scheduled uploads" className="m-0 grid list-none gap-1 border-t border-line px-3.5 py-2.5">
              {queue.map((q) => (
                <li key={q.id} className="flex items-center gap-2 text-sm">
                  <CalendarClock className="size-3.5 shrink-0 text-ink-soft" />
                  <span className="min-w-0 flex-1 truncate">
                    <b>{NAMES[q.platform]}</b>
                    {q.platform === "youtube" && channels.length > 1 && q.channel_name ? ` (${q.channel_name})` : ""}{" "}
                    {q.status === "uploading" ? "uploading now" : when(q.at)}
                    {q.platform === "tiktok" && q.privacy && <span className="text-ink-soft"> as {TT_VISIBILITY.find((o) => o.value === q.privacy)?.label ?? q.privacy}</span>}
                    {q.source === "auto" && <span className="text-ink-soft"> (auto)</span>}
                  </span>
                  {q.status === "scheduled" && (
                    <IconButton
                      label={`Cancel ${NAMES[q.platform]} upload`}
                      tone="danger"
                      onClick={async () => {
                        try {
                          await api.cancelScheduled(q.id);
                          setQueue((all) => all.filter((x) => x.id !== q.id));
                        } catch (e) {
                          toast((e as Error).message, "error");
                        }
                      }}
                    >
                      <X className="size-3.5" />
                    </IconButton>
                  )}
                </li>
              ))}
            </ul>
          )}
          <div className="border-t border-line px-3.5 py-2.5">
            {planning ? (
              <form
                className="grid gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  const chosen = targets.filter((p) => connected.includes(p));
                  if (chosen.length) void schedule(chosen);
                }}
              >
                <label className="grid gap-1">
                  <span className="field-label">Upload at</span>
                  <input type="datetime-local" required className="field-input h-9 py-0 text-base" value={at} onChange={(e) => setAt(e.target.value)} />
                </label>
                <div className="flex flex-wrap gap-3">
                  {connected.map((p) => (
                    <label key={p} className="flex items-center gap-1.5 text-sm font-semibold">
                      <input
                        type="checkbox"
                        className="size-4 accent-cobalt"
                        checked={targets.includes(p)}
                        onChange={(e) => setTargets((t) => (e.target.checked ? [...t, p] : t.filter((x) => x !== p)))}
                      />
                      {NAMES[p]}
                    </label>
                  ))}
                </div>
                <div className="flex gap-1">
                  <Button type="submit" size="sm" variant="primary" loading={scheduling} disabled={!targets.some((p) => connected.includes(p))}>
                    Schedule
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setPlanning(false)}>
                    Cancel
                  </Button>
                </div>
                <p className="m-0 text-xs leading-snug text-ink-soft">
                  Uploads while the app is open. If it&apos;s closed then, the upload goes out when you open it.
                  {targets.includes("facebook") && " Facebook gets it ahead of time and publishes it itself at that time (when it's 15 minutes to 28 days away)."}
                </p>
              </form>
            ) : (
              <Button
                size="sm"
                variant="ghost"
                className="-ml-2"
                icon={<CalendarClock className="size-3.5" />}
                onClick={() => {
                  setTargets(connected);
                  setAt(nextHour());
                  setPlanning(true);
                }}
              >
                Schedule for later
              </Button>
            )}
          </div>
        </>
      )}
    </section>
  );
}
