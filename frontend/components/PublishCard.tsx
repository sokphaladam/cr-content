"use client";

import { CalendarClock, ExternalLink, ImageUp, MessageSquare, Settings as SettingsIcon, Upload, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api, outputUrl, type CommentState, type Job, type ThumbnailState, type Platform, type PublishAccounts, type Published, type ScheduledUpload, type TikTokCreator, type TikTokPrivacy, type VideoDetail, type YouTubeOptions } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import { PLATFORM_NAMES as NAMES } from "./Settings";
import { Button, IconButton, useToast } from "./ui";

/** Local "YYYY-MM-DDTHH:MM" for a datetime-local input: the next full hour. */
function nextHour(): string {
  const d = new Date(Date.now() + 60 * 60 * 1000);
  d.setMinutes(0, 0, 0);
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
      <label className="grid gap-1 text-[12px] text-ink-soft">
        <span className="flex items-center justify-between">
          Tags
          <span className={`tabular-nums ${tagCost(typed) > TAGS_MAX ? "text-danger" : ""}`}>
            {tagCost(typed)}/{TAGS_MAX}
          </span>
        </span>
        <input
          className="field-input h-8 py-0 text-[12.5px]"
          value={text}
          placeholder="cat facts, cats, slow blink"
          onChange={(e) => setText(e.target.value)}
          onBlur={() => typed.join(",") !== options.tags.join(",") && save({ tags: typed })}
          onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
        />
      </label>
      <span className="text-[11.5px] leading-snug text-ink-soft">
        {options.custom_tags ? (
          <button type="button" className="cursor-pointer bg-transparent p-0 text-[11.5px] text-cobalt underline" onClick={() => save({ reset_tags: true })}>
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
        <label className="grid min-w-0 flex-1 gap-1 text-[12px] text-ink-soft">
          Thumbnail
          <select className="field-input h-8 py-0 text-[12.5px]" value={options.thumbnail} onChange={(e) => save({ thumbnail: e.target.value as YouTubeOptions["thumbnail"] })}>
            <option value="auto">{options.short ? "Auto (YouTube picks for Shorts)" : "Auto (my cover)"}</option>
            <option value="cover">Use my cover</option>
            <option value="youtube">Let YouTube pick</option>
          </select>
        </label>
      </div>
      {options.short && options.thumbnail === "cover" && (
        <span className="text-[11.5px] leading-snug text-ink-soft">Shorts may still show a frame in the Shorts feed; your cover shows on your channel and in search.</span>
      )}
      {options.comment !== undefined && (
        <label className="grid gap-1 text-[12px] text-ink-soft">
          <span className="flex items-center justify-between">
            Comment to pin
            <span className={`tabular-nums ${comment.length > COMMENT_MAX ? "text-danger" : ""}`}>{comment.length > 200 ? `${comment.length}/${COMMENT_MAX}` : ""}</span>
          </span>
          <textarea
            rows={3}
            maxLength={COMMENT_MAX}
            className="field-input field-sizing-content min-h-[60px] resize-none text-[12.5px] leading-snug"
            value={comment}
            placeholder="e.g. Which line hit you the most? 🎧 Full lyrics in the description."
            onChange={(e) => setComment(e.target.value)}
            onBlur={() => comment.trim() !== (options.comment ?? "") && save({ comment })}
          />
        </label>
      )}
      {options.comment !== undefined && (
        <span className="text-[11.5px] leading-snug text-ink-soft">
          Posted from your channel right after the upload; pin it in YouTube Studio → Comments (YouTube doesn&apos;t let apps pin).
          {options.custom_comment && !detail.script?.pinned_comment ? null : options.custom_comment ? (
            <>
              {" "}
              <button type="button" className="cursor-pointer bg-transparent p-0 text-[11.5px] text-cobalt underline" onClick={() => save({ reset_comment: true })}>
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
  const connected = (["youtube", "tiktok"] as Platform[]).filter((p) => accounts[p].connected);
  const busy = (p: Platform) => !!running[p] && running[p].status !== "error";
  const channels = accounts.youtube.channels ?? [];

  return (
    <section aria-labelledby={`publish-${detail.name}`} className="mx-auto w-full max-w-[300px] rounded-xl border border-line bg-panel">
      <header className="flex items-center justify-between gap-2 px-3.5 pt-3 pb-2">
        <h3 id={`publish-${detail.name}`} className="m-0 font-display text-[14.5px] font-bold">
          Upload
        </h3>
        {connected.length > 1 && (
          <Button size="sm" variant="primary" icon={<Upload className="size-3.5" />} disabled={connected.some(busy)} onClick={() => upload(connected)}>
            Upload to both
          </Button>
        )}
      </header>
      {connected.length === 0 ? (
        <div className="grid gap-2 px-3.5 pb-3.5">
          <p className="m-0 text-[12.5px] leading-snug text-ink-soft">Connect YouTube or TikTok to upload this video with its title and description.</p>
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
                      <label className="flex min-w-0 flex-1 items-center gap-1.5 text-[13px]">
                        <b>{NAMES[p]}</b>
                        <select
                          aria-label="YouTube channel"
                          className="field-input h-8 w-auto min-w-0 flex-1 py-0 text-[12.5px]"
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
                      <span className="min-w-0 flex-1 truncate text-[13px]">
                        <b>{NAMES[p]}</b> <span className="text-ink-soft">{accounts[p].account}</span>
                      </span>
                    )}
                    <Button size="sm" variant={prev ? "ghost" : "secondary"} icon={<Upload className="size-3.5" />} loading={busy(p)} onClick={() => upload([p])}>
                      {(p === "youtube" && (ytVisibility ?? accounts.youtube.privacy) === "schedule") || (p === "tiktok" && ttChoice === "SCHEDULE")
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
                        className="field-input h-8 w-auto py-0 text-[12.5px]"
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
                          className="field-input h-8 min-w-0 flex-1 py-0 text-[12.5px]"
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
                        className="field-input h-8 w-auto justify-self-start py-0 text-[12.5px]"
                        value={ttChoice}
                        onChange={(e) => {
                          if (e.target.value === "SCHEDULE" && ttVisibility !== "SCHEDULE") setTtAt(nextHour());
                          setTtVisibility(e.target.value as TikTokChoice);
                        }}
                      >
                        {ttAllowed.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                      {ttCreator && ttCreator.privacy_options.length === 1 && ttCreator.privacy_options[0] === "SELF_ONLY" && (
                        <p className="m-0 text-[11.5px] leading-snug text-ink-soft">
                          TikTok lets this app post as &quot;Only me&quot; until TikTok audits it. Choose Drafts to post publicly from the TikTok app, or change it to
                          public there after posting.
                        </p>
                      )}
                      {ttChoice === "SCHEDULE" && (
                        <>
                          <input
                            type="datetime-local"
                            aria-label="TikTok post goes public at"
                            className="field-input h-8 min-w-0 py-0 text-[12.5px]"
                            value={ttAt}
                            onChange={(e) => setTtAt(e.target.value)}
                          />
                          <p className="m-0 text-[11.5px] leading-snug text-ink-soft">
                            Posts as {TT_VISIBILITY.find((o) => o.value === ttPublic)?.label} at this time. TikTok can&apos;t schedule posts from apps, so Shorts
                            Studio posts it then. It keeps running in the tray when you close the window; turn on Settings → Start with Windows so it runs after a
                            restart too.
                          </p>
                        </>
                      )}
                      {ttChoice === "DRAFT" && (
                        <p className="m-0 text-[11.5px] leading-snug text-ink-soft">Goes to your TikTok inbox; open TikTok to add sounds or edits and post it.</p>
                      )}
                    </div>
                  )}
                  {p === "youtube" && !busy(p) && <YouTubeExtras key={detail.name} detail={detail} />}
                  {p === "youtube" && !busy(p) && accounts.youtube_categories && (
                    <label className="flex items-center gap-1.5 text-[12px] text-ink-soft">
                      Category
                      <select className="field-input h-8 w-auto min-w-0 flex-1 py-0 text-[12.5px]" value={ytCategory} onChange={(e) => setYtCategory(e.target.value)}>
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
                    <p className="m-0 text-[11.5px] leading-snug text-ink-soft">Uploads now as private; YouTube makes it public at this time, even if the app is closed.</p>
                  )}
                  {job ? (
                    <p className={`m-0 text-[12px] leading-snug ${job.status === "error" ? "text-danger" : "text-ink-soft"}`}>
                      {job.status === "error" ? job.error : (job.log.at(-1) ?? "Waiting to upload…")}
                    </p>
                  ) : prev ? (
                    <p className="m-0 text-[12px] leading-snug text-ink-soft">
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
                    <p className="m-0 text-[12px] leading-snug text-ink-soft">
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
                <li key={q.id} className="flex items-center gap-2 text-[12.5px]">
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
                  <input type="datetime-local" required className="field-input h-9 py-0 text-[13px]" value={at} onChange={(e) => setAt(e.target.value)} />
                </label>
                <div className="flex flex-wrap gap-3">
                  {connected.map((p) => (
                    <label key={p} className="flex items-center gap-1.5 text-[12.5px] font-semibold">
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
                <p className="m-0 text-[11.5px] leading-snug text-ink-soft">Uploads while the app is open. If it&apos;s closed then, the upload goes out when you open it.</p>
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
