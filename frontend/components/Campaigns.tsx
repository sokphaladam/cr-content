"use client";

import { CalendarClock, Check, Copy, ExternalLink, FileText, Film, ImageIcon, Link2, Music, Plus, RefreshCw, Scissors, Trash2, Upload, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  outputUrl,
  type Campaign,
  type CampaignClip,
  type CampaignReference,
  type CampaignRequirements,
  type CampaignSummary,
  type Job,
  type Platform,
  type PublishAccounts,
} from "@/lib/api";
import { relativeTime } from "@/lib/format";
import { PLATFORM_NAMES, PLATFORMS } from "./Settings";
import { Button, DropZone, IconButton, Segmented, useToast } from "./ui";

const PLATFORM_LABEL: Record<string, string> = { tiktok: "TikTok", youtube: "YouTube Shorts", instagram: "Instagram Reels", x: "X" };

/** Poll a job until it finishes; returns the latest state. */
function useJob(id: string | null, onFinish: (job: Job) => void) {
  const [job, setJob] = useState<Job | null>(null);
  const finish = useRef(onFinish);
  useEffect(() => {
    finish.current = onFinish;
  }, [onFinish]);
  useEffect(() => {
    if (!id) return;
    let stop = false;
    const tick = async () => {
      try {
        const j = await api.job(id);
        if (stop) return;
        setJob(j);
        if (j.status === "done" || j.status === "error") {
          finish.current(j);
          return;
        }
      } catch {
        // the engine may be busy; try again
      }
      if (!stop) setTimeout(tick, 1500);
    };
    void tick();
    return () => {
      stop = true;
    };
  }, [id]);
  return id ? job : null;
}

/** "Tue 13 Oct, 18:00" from a local "2026-10-13T18:00". */
function when(at: string) {
  const d = new Date(at);
  return Number.isNaN(d.getTime()) ? at : d.toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

function Panel({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="card">
      <header className="flex min-h-12 items-center justify-between gap-3 border-b border-line px-4 py-2">
        <h2 className="card-title m-0">{title}</h2>
        {action}
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

/* ---------- New campaign ---------- */

function NewCampaign({ claudeReady, onCreated }: { claudeReady: boolean; onCreated: (c: Campaign) => void }) {
  const toast = useToast();
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [reading, setReading] = useState(false);

  async function read() {
    setReading(true);
    try {
      const c = await api.readCampaign({ text, url });
      toast(`Read “${c.name}”. Check the requirements, then prepare the reference videos.`, "success");
      onCreated(c);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setReading(false);
    }
  }

  return (
    <div className="mx-auto grid max-w-[720px] gap-6 py-4">
      <header>
        <h1 className="page-title m-0">Add a campaign</h1>
        <p className="page-intro m-0 mt-1">
          Open the campaign on Whop, select everything on the page (Select All), copy it and paste it here. Gemini pulls out the brief, the content
          requirements and the links to the reference materials.
        </p>
      </header>
      <div className="grid gap-4 card p-4">
        <label className="grid gap-1.5">
          <span className="field-label">
            Campaign link <span className="font-normal">optional</span>
          </span>
          <input className="field-input h-10 py-0" placeholder="https://whop.com/…" value={url} onChange={(e) => setUrl(e.target.value)} />
        </label>
        <label className="grid gap-1.5">
          <span className="field-label">Campaign page</span>
          <textarea
            rows={12}
            className="field-input resize-y text-base leading-relaxed"
            placeholder={"Paste the whole campaign: title, pay rate, budget, platforms, the brief, content requirements and the links to the content you may clip."}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </label>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-sm text-ink-soft">
            {claudeReady ? "Takes about 20 seconds." : "Gemini isn't set up. Add your Gemini key in Settings first."}
          </span>
          <Button variant="primary" loading={reading} disabled={!claudeReady || (!text.trim() && !url.trim())} onClick={read}>
            Read campaign
          </Button>
        </div>
      </div>
    </div>
  );
}

/* ---------- Requirements ---------- */

const listText = (items: string[]) => items.join("\n");
const fromLines = (text: string) => text.split("\n").map((l) => l.trim()).filter(Boolean);
const fromWords = (text: string, prefix: string) =>
  text
    .split(/[\s,]+/)
    .map((w) => w.replace(new RegExp(`^\\${prefix}+`), "").trim())
    .filter(Boolean);

function RequirementsEditor({ value, onSave }: { value: CampaignRequirements; onSave: (r: CampaignRequirements) => Promise<void> }) {
  const [draft, setDraft] = useState(() => ({
    ...value,
    hashtagsText: value.hashtags.map((h) => `#${h}`).join(" "),
    mentionsText: value.mentions.map((m) => `@${m}`).join(" "),
    mustText: listText(value.must_include),
    rulesText: listText(value.rules),
    avoidText: listText(value.avoid),
  }));
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const set = (changes: Partial<typeof draft>) => {
    setDraft((d) => ({ ...d, ...changes }));
    setDirty(true);
  };

  async function save() {
    setSaving(true);
    try {
      await onSave({
        min_seconds: Number(draft.min_seconds) || 15,
        max_seconds: Number(draft.max_seconds) || 60,
        hashtags: fromWords(draft.hashtagsText, "#"),
        mentions: fromWords(draft.mentionsText, "@"),
        must_include: fromLines(draft.mustText),
        disclosure: draft.disclosure.trim(),
        captions: draft.captions,
        rules: fromLines(draft.rulesText),
        avoid: fromLines(draft.avoidText),
      });
      setDirty(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 sm:grid-cols-[auto_minmax(0,1fr)_minmax(0,1fr)]">
        <div className="grid gap-1.5">
          <span className="field-label">Clip length</span>
          <span className="flex items-center gap-1.5 text-base text-ink-soft">
            <input aria-label="Shortest clip, seconds" type="number" min={3} max={600} className="field-input h-9 w-16 py-0" value={draft.min_seconds} onChange={(e) => set({ min_seconds: Number(e.target.value) })} />
            to
            <input aria-label="Longest clip, seconds" type="number" min={5} max={600} className="field-input h-9 w-16 py-0" value={draft.max_seconds} onChange={(e) => set({ max_seconds: Number(e.target.value) })} />
            s
          </span>
        </div>
        <label className="grid gap-1.5">
          <span className="field-label">Required hashtags</span>
          <input className="field-input h-9 py-0 text-base" value={draft.hashtagsText} onChange={(e) => set({ hashtagsText: e.target.value })} placeholder="#brand #topic" />
        </label>
        <label className="grid gap-1.5">
          <span className="field-label">Accounts to tag</span>
          <input className="field-input h-9 py-0 text-base" value={draft.mentionsText} onChange={(e) => set({ mentionsText: e.target.value })} placeholder="@brand" />
        </label>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-1.5">
          <span className="field-label">
            Caption must include <span className="font-normal">one per line</span>
          </span>
          <textarea rows={2} className="field-input resize-y text-base" value={draft.mustText} onChange={(e) => set({ mustText: e.target.value })} placeholder="link in bio" />
        </label>
        <div className="grid content-start gap-3">
          <label className="grid gap-1.5">
            <span className="field-label">Ad disclosure</span>
            <input className="field-input h-9 py-0 text-base" value={draft.disclosure} onChange={(e) => set({ disclosure: e.target.value })} placeholder="#ad" />
          </label>
          <label className="flex items-center gap-2 text-base font-semibold">
            <input type="checkbox" className="size-4 accent-cobalt" checked={draft.captions} onChange={(e) => set({ captions: e.target.checked })} />
            Burn in captions
          </label>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-1.5">
          <span className="field-label">
            Content rules <span className="font-normal">one per line</span>
          </span>
          <textarea rows={5} className="field-input resize-y text-base leading-relaxed" value={draft.rulesText} onChange={(e) => set({ rulesText: e.target.value })} />
        </label>
        <label className="grid gap-1.5">
          <span className="field-label">
            Not allowed <span className="font-normal">one per line</span>
          </span>
          <textarea rows={5} className="field-input resize-y text-base leading-relaxed" value={draft.avoidText} onChange={(e) => set({ avoidText: e.target.value })} />
        </label>
      </div>
      {dirty && (
        <div className="flex justify-end">
          <Button size="sm" variant="primary" icon={<Check className="size-3.5" />} loading={saving} onClick={save}>
            Save requirements
          </Button>
        </div>
      )}
    </div>
  );
}

/* ---------- Reference materials ---------- */

function RefIcon({ kind }: { kind: CampaignReference["kind"] }) {
  const cls = "size-4";
  if (kind === "video") return <Film className={cls} />;
  if (kind === "audio") return <Music className={cls} />;
  if (kind === "image") return <ImageIcon className={cls} />;
  if (kind === "document") return <FileText className={cls} />;
  return <Link2 className={cls} />;
}

function refState(r: CampaignReference): { text: string; tone: "ok" | "soft" | "warn" } {
  if (r.status === "new") return { text: "Not downloaded yet", tone: "soft" };
  if (r.status === "manual") return { text: "Add it yourself", tone: "warn" };
  if (r.status === "error") return { text: "Failed", tone: "warn" };
  if (r.kind === "video" || r.kind === "audio") {
    const mins = r.duration ? `${Math.max(1, Math.round(r.duration / 60))} min` : "";
    return r.transcribed ? { text: ["Ready to clip", mins].filter(Boolean).join(", "), tone: "ok" } : { text: "Needs transcribing", tone: "soft" };
  }
  return { text: "Saved", tone: "ok" };
}

function References({
  campaign,
  onChange,
  preparing,
  onPrepare,
}: {
  campaign: Campaign;
  onChange: (c: Campaign) => void;
  preparing: Job | null;
  onPrepare: () => void;
}) {
  const toast = useToast();
  const [link, setLink] = useState("");
  const [adding, setAdding] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const busy = !!preparing && (preparing.status === "queued" || preparing.status === "running");
  const todo = campaign.references.filter((r) => (r.status === "new" && r.url) || (r.status === "ready" && (r.kind === "video" || r.kind === "audio") && !r.transcribed));

  async function addLink() {
    setAdding(true);
    try {
      onChange(await api.addReference(campaign.id, link.trim()));
      setLink("");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setAdding(false);
    }
  }

  async function upload(files: FileList | File[] | null) {
    if (!files?.length) return;
    setUploading(true);
    try {
      let c = campaign;
      for (const f of Array.from(files)) c = await api.uploadReference(campaign.id, f);
      onChange(c);
      toast(files.length === 1 ? "File added" : `${files.length} files added`, "success");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  return (
    <Panel
      title="Reference materials"
      action={
        <Button size="sm" variant={todo.length ? "primary" : "ghost"} icon={<RefreshCw className="size-3.5" />} loading={busy} disabled={!todo.length} onClick={onPrepare}>
          {todo.length ? `Prepare ${todo.length}` : "All prepared"}
        </Button>
      }
    >
      <p className="m-0 mb-3 text-base text-ink-soft">
        Videos are downloaded and transcribed so Gemini can pick the moments. Folders (Google Drive, Dropbox) can&apos;t be downloaded automatically: download the
        files and add them here.
      </p>
      <DropZone accept="video/*,audio/*,image/*,.pdf,.txt" multiple label="Drop to add references" onFiles={(f) => void upload(f)} onReject={(m) => toast(m, "error")}>
      {busy && <p className="m-0 mb-3 rounded-lg bg-caption/25 px-3 py-2 text-base">{preparing?.log.at(-1) ?? "Waiting for the current render to finish…"}</p>}
      {preparing?.status === "error" && <p className="m-0 mb-3 text-base text-danger">{preparing.error}</p>}
      {campaign.references.length > 0 && (
        <ul className="m-0 mb-3 grid list-none divide-y divide-line rounded-lg border border-line p-0">
          {campaign.references.map((r) => {
            const st = refState(r);
            return (
              <li key={r.id} className="grid grid-cols-[28px_minmax(0,1fr)_auto] items-center gap-2 px-3 py-2">
                <span className="grid size-7 place-items-center rounded-md bg-ink/[0.06] text-ink-soft">
                  <RefIcon kind={r.kind} />
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-base font-semibold">{r.title || r.url || "Untitled"}</span>
                  <span className="flex min-w-0 items-center gap-2 text-sm">
                    <span className={`shrink-0 font-semibold ${st.tone === "ok" ? "text-ok" : st.tone === "warn" ? "text-warn" : "text-ink-soft"}`}>{st.text}</span>
                    {r.url && (
                      <a href={r.url} target="_blank" rel="noreferrer" className="inline-flex min-w-0 items-center gap-0.5 truncate text-cobalt">
                        <span className="truncate">{r.url.replace(/^https?:\/\/(www\.)?/, "")}</span>
                        <ExternalLink className="size-3 shrink-0" />
                      </a>
                    )}
                  </span>
                  {r.note && <span className="block text-sm text-ink-soft">{r.note}</span>}
                </span>
                <IconButton label={`Remove ${r.title || "reference"}`} tone="danger" onClick={async () => onChange(await api.removeReference(campaign.id, r.id))}>
                  <X className="size-4" />
                </IconButton>
              </li>
            );
          })}
        </ul>
      )}
      <form
        className="flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (link.trim()) void addLink();
        }}
      >
        <input
          aria-label="Reference link"
          className="field-input h-9 min-w-[200px] flex-1 py-0 text-base"
          placeholder="Paste a YouTube, Drive or video link"
          value={link}
          onChange={(e) => setLink(e.target.value)}
        />
        <Button type="submit" size="sm" variant="secondary" className="h-9" icon={<Plus className="size-3.5" />} loading={adding} disabled={!link.trim()}>
          Add link
        </Button>
        <input ref={fileInput} type="file" multiple hidden accept="video/*,audio/*,image/*,.pdf,.txt" onChange={(e) => upload(e.target.files)} />
        <Button size="sm" variant="secondary" className="h-9" icon={<Upload className="size-3.5" />} loading={uploading} onClick={() => fileInput.current?.click()}>
          Add files
        </Button>
      </form>
      </DropZone>
    </Panel>
  );
}

/* ---------- Clips ---------- */

function ClipCard({ clip, onOpen }: { clip: CampaignClip; onOpen: () => void }) {
  const toast = useToast();
  const uploads = Object.entries(clip.published) as [Platform, NonNullable<CampaignClip["published"][Platform]>][];
  return (
    <li className="grid grid-cols-[72px_minmax(0,1fr)] gap-3 card p-2.5">
      <button type="button" onClick={onOpen} aria-label={`Open ${clip.title}`} className="cursor-pointer overflow-hidden rounded-lg border-0 bg-ink/[0.08] p-0">
        {clip.thumb ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={`${outputUrl(clip.name, "thumbnail.jpg")}?v=${clip.thumb_v}`} alt="" className="block aspect-[9/16] w-full object-cover" />
        ) : (
          <span className="grid aspect-[9/16] place-items-center text-ink-soft">
            <Film className="size-5" />
          </span>
        )}
      </button>
      <div className="grid min-w-0 content-start gap-1.5">
        <p className="m-0 line-clamp-2 text-base leading-snug font-semibold">{clip.title}</p>
        <p className="m-0 text-sm text-ink-soft">
          {Math.round(clip.duration)}s, made {relativeTime(clip.created)}
        </p>
        {clip.hook && <p className="m-0 line-clamp-2 text-sm text-ink-soft">Hook: {clip.hook}</p>}
        <div className="flex flex-wrap gap-1">
          {uploads.map(([p, u]) => (
            <span key={p} className="inline-flex items-center gap-1 rounded-full bg-ok/10 px-2 py-0.5 text-xs font-semibold text-ok">
              <Check className="size-3" />
              {PLATFORM_NAMES[p]}
              {u.url && (
                <button
                  type="button"
                  title="Copy the post link to submit it on Whop"
                  aria-label={`Copy ${PLATFORM_NAMES[p]} link`}
                  className="ml-0.5 cursor-pointer border-0 bg-transparent p-0 text-ok"
                  onClick={async () => {
                    await navigator.clipboard.writeText(u.url);
                    toast("Post link copied. Submit it on the campaign page.", "success");
                  }}
                >
                  <Copy className="size-3" />
                </button>
              )}
            </span>
          ))}
          {clip.scheduled.map((s) => (
            <span key={s.id} className="inline-flex items-center gap-1 rounded-full bg-caption/30 px-2 py-0.5 text-xs font-semibold">
              <CalendarClock className="size-3" />
              {PLATFORM_NAMES[s.platform]} {s.status === "uploading" ? "uploading" : when(s.at)}
            </span>
          ))}
        </div>
        <div>
          <Button size="sm" variant="ghost" className="-ml-2" onClick={onOpen}>
            Open in studio
          </Button>
        </div>
      </div>
    </li>
  );
}

function MakeClips({
  campaign,
  making,
  onMake,
}: {
  campaign: Campaign;
  making: Job | null;
  onMake: (body: { count: number; layout: "fill" | "crop"; idea: string }) => void;
}) {
  const [count, setCount] = useState(3);
  const [layout, setLayout] = useState<"fill" | "crop">("fill");
  const [idea, setIdea] = useState("");
  const ready = campaign.references.some((r) => r.kind === "video" && r.transcribed);
  const busy = !!making && (making.status === "queued" || making.status === "running");
  const r = campaign.requirements;
  return (
    <Panel title="Make clips">
      <div className="grid gap-4">
        <div className="flex flex-wrap items-end gap-4">
          <label className="grid gap-1.5">
            <span className="field-label">How many</span>
            <select className="field-input h-9 w-20 py-0" value={count} onChange={(e) => setCount(Number(e.target.value))}>
              {[1, 2, 3, 4, 5, 6, 8, 10].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <div className="grid gap-1.5">
            <span className="field-label">Framing</span>
            <Segmented
              name="clip-layout"
              size="sm"
              value={layout}
              onChange={setLayout}
              options={[
                { value: "fill", label: "Whole picture" },
                { value: "crop", label: "Fill the screen" },
              ]}
            />
          </div>
          <p className="m-0 pb-1.5 text-sm text-ink-soft">
            9:16, {r.min_seconds}–{r.max_seconds}s{r.captions ? ", captions" : ""}, hook on screen
          </p>
        </div>
        <label className="grid gap-1.5">
          <span className="field-label">
            Direction <span className="font-normal">optional</span>
          </span>
          <input
            className="field-input h-9 py-0 text-base"
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="Funny moments first, or: only the part about pricing"
          />
        </label>
        {busy && <p className="m-0 rounded-lg bg-caption/25 px-3 py-2 text-base">{making?.log.at(-1) ?? "Waiting for the current render to finish…"}</p>}
        {making?.status === "error" && <p className="m-0 text-base text-danger">{making.error}</p>}
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm text-ink-soft">{ready ? "Gemini reads the transcripts and picks the strongest moments." : "Prepare at least one reference video first."}</span>
          <Button variant="primary" icon={<Scissors className="size-4" />} loading={busy} disabled={!ready} onClick={() => onMake({ count, layout, idea })}>
            Make {count} clip{count === 1 ? "" : "s"}
          </Button>
        </div>
      </div>
    </Panel>
  );
}

/* ---------- Campaign page ---------- */

function CampaignDetail({
  campaign,
  setCampaign,
  onDeleted,
  onOpenVideo,
  onVideosChanged,
  onOpenSettings,
}: {
  campaign: Campaign;
  setCampaign: (c: Campaign) => void;
  onDeleted: () => void;
  onOpenVideo: (name: string) => void;
  onVideosChanged: () => void;
  onOpenSettings: () => void;
}) {
  const toast = useToast();
  const [brief, setBrief] = useState(campaign.brief);
  const [prepareId, setPrepareId] = useState<string | null>(null);
  const [clipsId, setClipsId] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<PublishAccounts | null>(null);
  const [scheduling, setScheduling] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    api.publishAccounts().then(setAccounts).catch(() => {});
  }, []);

  const reload = useCallback(async () => setCampaign(await api.campaign(campaign.id)), [campaign.id, setCampaign]);
  const preparing = useJob(prepareId, (j) => {
    void reload();
    if (j.status === "done") toast("References prepared", "success");
  });
  const making = useJob(clipsId, (j) => {
    void reload();
    onVideosChanged();
    if (j.status === "done") toast(`${j.summary ?? "Clips ready"}. They're also in Videos.`, "success");
  });

  async function edit(changes: Parameters<typeof api.editCampaign>[1]) {
    try {
      setCampaign(await api.editCampaign(campaign.id, changes));
    } catch (e) {
      toast((e as Error).message, "error");
      throw e;
    }
  }

  const connected = PLATFORMS.filter((p) => accounts?.[p]?.connected);
  const unposted = campaign.clips.filter((c) => connected.some((p) => !c.published[p] && !c.scheduled.some((s) => s.platform === p)));

  return (
    <div className="mx-auto grid max-w-[980px] gap-5 py-2">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <input
            aria-label="Campaign name"
            className="-ml-1 w-full rounded-md border border-transparent bg-transparent px-1 page-title hover:border-line focus:border-cobalt focus:outline-none"
            defaultValue={campaign.name}
            key={campaign.id}
            onBlur={(e) => e.target.value.trim() && e.target.value !== campaign.name && edit({ name: e.target.value.trim() })}
          />
          <p className="m-0 mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-base text-ink-soft">
            {campaign.brand && <span className="font-semibold text-ink">{campaign.brand}</span>}
            {campaign.rate && <span className="rounded-md bg-caption px-1.5 py-0.5 font-semibold text-media">{campaign.rate}</span>}
            {campaign.budget && <span>Budget {campaign.budget}</span>}
            {campaign.platforms.length > 0 && <span>{campaign.platforms.map((p) => PLATFORM_LABEL[p] ?? p).join(", ")}</span>}
          </p>
        </div>
        <div className="flex items-center gap-1">
          {campaign.url && (
            <a href={campaign.url} target="_blank" rel="noreferrer" className="inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-base font-semibold text-ink-soft no-underline hover:bg-ink/[0.05] hover:text-ink">
              Open on Whop <ExternalLink className="size-3.5" />
            </a>
          )}
          {confirmDelete ? (
            <Button
              size="sm"
              variant="danger"
              icon={<Trash2 className="size-3.5" />}
              onClick={async () => {
                await api.deleteCampaign(campaign.id);
                toast("Campaign deleted. Its clips are still in Videos.");
                onDeleted();
              }}
            >
              Delete campaign
            </Button>
          ) : (
            <IconButton
              label="Delete campaign"
              tone="danger"
              onClick={() => {
                setConfirmDelete(true);
                setTimeout(() => setConfirmDelete(false), 3000);
              }}
            >
              <Trash2 className="size-4" />
            </IconButton>
          )}
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <Panel title="Brief">
          <textarea
            aria-label="Brief"
            rows={9}
            className="field-input resize-y text-base leading-relaxed"
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            onBlur={() => brief !== campaign.brief && edit({ brief })}
          />
          <p className="m-0 mt-2 text-sm text-ink-soft">Gemini picks moments that serve this brief. Edits save when you click away.</p>
        </Panel>
        <Panel title="Content requirements">
          <RequirementsEditor key={JSON.stringify(campaign.requirements)} value={campaign.requirements} onSave={(requirements) => edit({ requirements })} />
        </Panel>
      </div>

      <References campaign={campaign} onChange={setCampaign} preparing={preparing} onPrepare={async () => {
        try {
          setPrepareId((await api.prepareCampaign(campaign.id)).id);
        } catch (e) {
          toast((e as Error).message, "error");
        }
      }} />

      <MakeClips
        campaign={campaign}
        making={making}
        onMake={async (body) => {
          try {
            setClipsId((await api.makeClips(campaign.id, body)).id);
          } catch (e) {
            toast((e as Error).message, "error");
          }
        }}
      />

      <Panel
        title={`Clips${campaign.clips.length ? ` (${campaign.clips.length})` : ""}`}
        action={
          connected.length ? (
            <Button
              size="sm"
              variant={unposted.length ? "secondary" : "ghost"}
              icon={<CalendarClock className="size-3.5" />}
              loading={scheduling}
              disabled={!unposted.length}
              onClick={async () => {
                setScheduling(true);
                try {
                  const { scheduled, campaign: c } = await api.scheduleCampaign(campaign.id, connected);
                  setCampaign(c);
                  toast(scheduled ? `Scheduled ${scheduled} upload${scheduled === 1 ? "" : "s"} at your posting times` : "Nothing new to schedule", "success");
                } catch (e) {
                  toast((e as Error).message, "error");
                } finally {
                  setScheduling(false);
                }
              }}
            >
              {unposted.length ? `Schedule ${unposted.length} new` : "All scheduled"}
            </Button>
          ) : (
            <Button size="sm" variant="ghost" onClick={onOpenSettings}>
              Connect channels
            </Button>
          )
        }
      >
        {campaign.clips.length === 0 ? (
          <p className="m-0 text-base text-ink-soft">Clips you make appear here, with where they&apos;re uploaded or scheduled.</p>
        ) : (
          <>
            <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2 xl:grid-cols-3">
              {campaign.clips.map((c) => (
                <ClipCard key={c.name} clip={c} onOpen={() => onOpenVideo(c.name)} />
              ))}
            </ul>
            <p className="m-0 mt-3 text-sm text-ink-soft">
              After a clip is posted, copy its link (the icon next to the platform) and submit it on the campaign page to get paid for its views.
            </p>
          </>
        )}
      </Panel>
    </div>
  );
}

/** Content Rewards campaigns: a list on the left, the selected campaign (or a new one) on the right. */
export function Campaigns({
  claudeReady,
  onOpenVideo,
  onVideosChanged,
  onOpenSettings,
}: {
  claudeReady: boolean;
  onOpenVideo: (name: string) => void;
  onVideosChanged: () => void;
  onOpenSettings: () => void;
}) {
  const toast = useToast();
  const [list, setList] = useState<CampaignSummary[] | null>(null);
  const [selected, setSelected] = useState<string | "new" | null>(null);
  const [campaign, setCampaign] = useState<Campaign | null>(null);

  const loadList = useCallback(
    () =>
      api
        .campaigns()
        .then((l) => {
          setList(l);
          setSelected((s) => s ?? (l[0]?.id || "new"));
        })
        .catch((e) => {
          toast((e as Error).message, "error");
          setList([]);
        }),
    [toast],
  );

  useEffect(() => {
    void loadList();
  }, [loadList]);

  useEffect(() => {
    if (!selected || selected === "new") return;
    let stale = false;
    api
      .campaign(selected)
      .then((c) => !stale && setCampaign(c))
      .catch((e) => toast((e as Error).message, "error"));
    return () => {
      stale = true;
    };
  }, [selected, toast]);

  const update = useCallback(
    (c: Campaign) => {
      setCampaign(c);
      void loadList();
    },
    [loadList],
  );

  return (
    <div className="grid h-full min-h-0 grid-cols-1 md:grid-cols-[272px_minmax(0,1fr)]">
      <aside aria-label="Campaigns" className="flex min-h-0 flex-col border-b border-line bg-paper md:border-r md:border-b-0">
        <div className="pane-header">
          <h2 className="pane-title m-0">Campaigns</h2>
          <Button size="sm" variant="primary" icon={<Plus className="size-4" />} onClick={() => setSelected("new")}>
            Add
          </Button>
        </div>
        <ul className="m-0 grid max-h-[40vh] min-h-0 list-none content-start gap-0.5 overflow-y-auto p-2 md:max-h-none md:flex-1">
          {list === null && <li className="p-2 text-base text-ink-soft">Loading…</li>}
          {list?.length === 0 && <li className="p-2 text-base text-ink-soft">No campaigns yet. Add one from Whop to start clipping.</li>}
          {list?.map((c) => {
            const current = c.id === selected;
            return (
              <li key={c.id}>
                <button
                  type="button"
                  aria-current={current || undefined}
                  onClick={() => setSelected(c.id)}
                  className={`relative grid w-full cursor-pointer gap-0.5 rounded-lg border-0 px-3 py-2 text-left transition-colors ${
                    current ? "bg-panel shadow-(--shadow-card)" : "bg-transparent hover:bg-ink/[0.04]"
                  }`}
                >
                  {current && <span aria-hidden className="absolute top-2 bottom-2 left-0 w-[3px] rounded-r bg-caption" />}
                  <span className="truncate text-base font-semibold">{c.name}</span>
                  <span className="truncate text-sm text-ink-soft">
                    {[c.rate, `${c.clips} clip${c.clips === 1 ? "" : "s"}`, c.uploaded ? `${c.uploaded} posted` : ""].filter(Boolean).join(", ")}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </aside>
      <main className="min-h-0 overflow-y-auto bg-paper px-4 py-6 sm:px-8">
        {selected === "new" || (list?.length === 0 && !campaign) ? (
          <NewCampaign
            claudeReady={claudeReady}
            onCreated={(c) => {
              setCampaign(c);
              setSelected(c.id);
              void loadList();
            }}
          />
        ) : campaign && campaign.id === selected ? (
          <CampaignDetail
            key={campaign.id}
            campaign={campaign}
            setCampaign={update}
            onDeleted={() => {
              setCampaign(null);
              setSelected(null);
              void loadList();
            }}
            onOpenVideo={onOpenVideo}
            onVideosChanged={onVideosChanged}
            onOpenSettings={onOpenSettings}
          />
        ) : (
          <p className="m-0 text-base text-ink-soft">Loading…</p>
        )}
      </main>
    </div>
  );
}
