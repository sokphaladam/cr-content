"use client";

import { CalendarClock, Copy, Download, ExternalLink, FolderOpen, KeyRound, LogOut, Monitor, Moon, Plus, Sun, Trash2, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useAppearance } from "@/lib/appearance";
import { checkNow, install, setAutoCheck, startUpdates, useAutoCheck, useUpdates } from "@/lib/updates";
import { AddonProgress, DownloadProgress, useArtStatus } from "./ArtControls";
import { api, ART_STYLES, getAutostart, isMac, pickFolder, setAutostart, type CleanupGroup, type Locations, type Platform, type PublishAccount, type PublishAccounts, type ScheduledUpload, type ServiceKey, type ServiceKeys } from "@/lib/api";
import { Button, IconButton, Segmented, useToast } from "./ui";

export const PLATFORM_NAMES: Record<Platform, string> = { youtube: "YouTube", tiktok: "TikTok", facebook: "Facebook", instagram: "Instagram" };
export const PLATFORMS: Platform[] = ["youtube", "tiktok", "facebook", "instagram"];
/** Facebook and Instagram share one Meta developer app and one sign-in. */
const META: Platform[] = ["facebook", "instagram"];

const SERVICES: { key: ServiceKey; name: string; does: string; url: string; optional?: boolean }[] = [
  { key: "GEMINI_API_KEY", name: "Gemini", does: "Writes scripts, lyrics, titles, descriptions and cover ideas. Has a free tier.", url: "https://aistudio.google.com/apikey" },
  { key: "PIXABAY_API_KEY", name: "Pixabay", does: "Free stock footage and photos for your scenes.", url: "https://pixabay.com/api/docs/" },
  { key: "PEXELS_API_KEY", name: "Pexels", does: "A second stock footage library, used when Pixabay isn't set.", url: "https://www.pexels.com/api/", optional: true },
  { key: "ELEVENLABS_API_KEY", name: "ElevenLabs", does: "Composes AI songs. Needs Music API access.", url: "https://elevenlabs.io/app/settings/api-keys" },
  {
    key: "JAMENDO_CLIENT_ID",
    name: "Jamendo",
    does: "Free background music: search it from the Music picker; plan episodes fetch a track for their Music / Mood.",
    url: "https://devportal.jamendo.com/",
    optional: true,
  },
  {
    key: "YOUTUBE_API_KEY",
    name: "YouTube Data API",
    does: "Searches YouTube for outlier videos to remake. Not needed when a YouTube channel is connected below.",
    url: "https://console.cloud.google.com/apis/credentials",
    optional: true,
  },
];

const ID_LABEL: Record<Platform, string> = { youtube: "Client ID", tiktok: "Client key", facebook: "App ID", instagram: "App ID" };
const HOW_TO: Record<Platform, { url: string; steps: string }> = {
  youtube: {
    url: "https://console.cloud.google.com/apis/credentials",
    steps: "In Google Cloud, enable YouTube Data API v3, set up the OAuth consent screen with yourself as a test user, then create an OAuth client ID of type Desktop app.",
  },
  tiktok: {
    url: "https://developers.tiktok.com/apps",
    steps: "In TikTok for Developers, create a Desktop app, add Login Kit and the Content Posting API, and register the redirect URI below.",
  },
  facebook: {
    url: "https://developers.facebook.com/apps",
    steps:
      "In Meta for Developers, create an app with the use cases for managing a Page and the Instagram API (with Facebook Login), and keep it in Development mode: as its admin you can grant every permission without App Review. Instagram must be a professional (Business or Creator) account linked to your Page. Copy the App ID and secret from App settings → Basic. If Facebook asks for the redirect URI, add the one below.",
  },
  instagram: { url: "https://developers.facebook.com/apps", steps: "" }, // keys are set on the Facebook row
};
const YT_PRIVACY = [
  { value: "public", label: "Public" },
  { value: "unlisted", label: "Unlisted" },
  { value: "private", label: "Private" },
];
const TT_PRIVACY = [
  { value: "PUBLIC_TO_EVERYONE", label: "Everyone" },
  { value: "MUTUAL_FOLLOW_FRIENDS", label: "Friends" },
  { value: "FOLLOWER_OF_CREATOR", label: "Followers" },
  { value: "SELF_ONLY", label: "Only me" },
];

function StatusDot({ on, children }: { on: boolean; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm font-semibold ${on ? "text-ok" : "text-ink-soft"}`}>
      <span className={`size-1.5 rounded-full ${on ? "bg-ok" : "bg-ink-soft/40"}`} />
      {children}
    </span>
  );
}

function Section({ id, title, intro, children }: { id: string; title: string; intro: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="scroll-mt-6">
      <h2 id={`${id}-title`} className="section-title m-0">
        {title}
      </h2>
      <p className="page-intro mt-1 mb-4">{intro}</p>
      <div className="divide-y divide-line overflow-hidden card">{children}</div>
    </section>
  );
}

/* ---------- Running in the background (desktop app) ---------- */

/** Start at sign-in in the tray (menu bar on macOS), so scheduled uploads go out on time even when you never open the app. */
function BackgroundRow() {
  const toast = useToast();
  const [on, setOn] = useState<boolean | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    getAutostart().then(setOn).catch(() => setOn(undefined));
  }, []);
  if (on === undefined) return null; // the browser version: nothing to start
  return (
    <div className="grid gap-1.5 px-4 py-3">
      <label className="flex cursor-pointer items-center gap-2 text-base font-semibold">
        <input
          type="checkbox"
          checked={on}
          disabled={busy}
          className="size-4 accent-cobalt"
          onChange={async (e) => {
            setBusy(true);
            try {
              setOn((await setAutostart(e.target.checked)) ?? e.target.checked);
            } catch (err) {
              toast(String(err), "error");
            } finally {
              setBusy(false);
            }
          }}
        />
        {isMac() ? "Open at login and run in the background" : "Start with Windows and run in the background"}
      </label>
      <p className="m-0 text-sm leading-snug text-ink-soft">
        {isMac()
          ? "Shorts Studio starts in the menu bar when you log in, so scheduled uploads (TikTok included) go out on time without opening it. Closing the window keeps it running in the menu bar; to stop it completely, click the menu bar icon → Quit (or press ⌘Q)."
          : "Shorts Studio starts in the system tray when you sign in, so scheduled uploads (TikTok included) go out on time without opening it. Closing the window keeps it running in the tray; to stop it completely, right-click the tray icon → Quit."}
      </p>
    </div>
  );
}

/* ---------- Services (API keys) ---------- */

function ServiceRow({ service, state, onSaved }: { service: (typeof SERVICES)[number]; state?: ServiceKeys[ServiceKey]; onSaved: (keys: ServiceKeys) => void }) {
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);
  const isSet = !!state?.set;

  async function save(v: string) {
    setSaving(true);
    try {
      onSaved(await api.saveServiceKeys({ [service.key]: v }));
      toast(v ? `${service.name} saved` : `${service.name} removed`, "success");
      setEditing(false);
      setValue("");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="text-md font-semibold">{service.name}</span>
          {state && <StatusDot on={isSet}>{isSet ? `Saved ${state.hint}` : service.optional ? "Optional" : "Not set"}</StatusDot>}
        </div>
        <p className="m-0 mt-0.5 text-base text-ink-soft">
          {service.does}{" "}
          <a href={service.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-cobalt">
            Get a key <ExternalLink className="size-3" />
          </a>
        </p>
      </div>
      {!editing && (
        <div className="flex gap-1">
          <Button size="sm" variant={isSet ? "ghost" : "secondary"} onClick={() => setEditing(true)}>
            {isSet ? "Replace" : "Add key"}
          </Button>
          {isSet && (
            <Button size="sm" variant="danger" loading={saving} onClick={() => save("")}>
              Remove
            </Button>
          )}
        </div>
      )}
      {editing && (
        <form
          className="flex gap-2 sm:col-span-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (value.trim()) void save(value);
          }}
        >
          <input
            aria-label={`${service.name} key`}
            type="password"
            autoFocus
            autoComplete="off"
            spellCheck={false}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={`Paste your ${service.name} key`}
            className="field-input h-9 min-w-0 flex-1 py-0 text-base"
          />
          <Button type="submit" size="sm" variant="primary" className="h-9" loading={saving} disabled={!value.trim()}>
            Save
          </Button>
          <Button size="sm" variant="ghost" className="h-9" onClick={() => setEditing(false)}>
            Cancel
          </Button>
        </form>
      )}
    </div>
  );
}

/* ---------- Section menu (follows the scroll) ---------- */

const SECTIONS = [
  { id: "services", label: "Services" },
  { id: "channels", label: "Channels" },
  { id: "journey", label: "Your journey" },
  { id: "queue", label: "Upload queue" },
  { id: "scene-art", label: "AI features" },
  { id: "appearance", label: "Appearance" },
  { id: "storage", label: "Storage" },
  { id: "cleanup", label: "Clean up" },
  { id: "about", label: "About & updates" },
];

function SectionNav() {
  const [current, setCurrent] = useState(SECTIONS[0].id);
  useEffect(() => {
    const els = SECTIONS.map((s) => document.getElementById(s.id)).filter((el): el is HTMLElement => !!el);
    const scroller = els[0]?.closest(".overflow-y-auto");
    if (!scroller) return;
    // the section whose top passed a line a third of the way down is the one being read
    const onScroll = () => {
      const line = scroller.getBoundingClientRect().top + scroller.clientHeight / 3;
      const atEnd = scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 4;
      const passed = els.filter((el) => el.getBoundingClientRect().top <= line);
      setCurrent((atEnd ? els[els.length - 1] : (passed[passed.length - 1] ?? els[0])).id);
    };
    onScroll();
    scroller.addEventListener("scroll", onScroll, { passive: true });
    return () => scroller.removeEventListener("scroll", onScroll);
  }, []);
  return (
    <nav aria-label="Settings sections" className="sticky top-8 grid gap-0.5 text-base">
      {SECTIONS.map((s) => {
        const on = s.id === current;
        return (
          <a
            key={s.id}
            href={`#${s.id}`}
            aria-current={on ? "true" : undefined}
            className={`rounded-md px-3 py-1.5 font-semibold no-underline transition-colors ${
              on ? "bg-cobalt-soft text-cobalt" : "text-ink-soft hover:bg-ink/[0.05] hover:text-ink"
            }`}
          >
            {s.label}
          </a>
        );
      })}
    </nav>
  );
}

/* ---------- Appearance (theme, interface size) ---------- */

function AppearanceRows() {
  const { theme, setTheme, size, setSize } = useAppearance();
  return (
    <>
      <SettingRow title="Theme" hint="System follows your computer's light or dark mode.">
        <Segmented
          name="theme"
          size="sm"
          value={theme}
          onChange={setTheme}
          options={[
            { value: "system", label: <IconLabel icon={<Monitor className="size-3.5" />}>System</IconLabel> },
            { value: "light", label: <IconLabel icon={<Sun className="size-3.5" />}>Light</IconLabel> },
            { value: "dark", label: <IconLabel icon={<Moon className="size-3.5" />}>Dark</IconLabel> },
          ]}
        />
      </SettingRow>
      <SettingRow title="Interface size" hint="Scales text and spacing everywhere. Compact fits more on a laptop screen.">
        <Segmented
          name="ui-size"
          size="sm"
          value={size}
          onChange={setSize}
          options={[
            { value: "compact", label: "Compact" },
            { value: "default", label: "Default" },
            { value: "large", label: "Large" },
          ]}
        />
      </SettingRow>
    </>
  );
}

function IconLabel({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      {icon}
      {children}
    </span>
  );
}

/** One setting: title and hint on the left, its control on the right (stacked on narrow screens). */
function SettingRow({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3.5">
      <div className="grid min-w-[200px] flex-1 gap-0.5">
        <span className="text-md font-semibold">{title}</span>
        {hint && <span className="text-sm text-ink-soft">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

/* ---------- Your journey (a progress line in descriptions) ---------- */

function JourneyRow() {
  const toast = useToast();
  const [saved, setSaved] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.journey().then((r) => {
      setSaved(r.journey);
      setText(r.journey);
    }).catch(() => setSaved(""));
  }, []);

  async function save() {
    setBusy(true);
    try {
      const r = await api.saveJourney(text);
      setSaved(r.journey);
      setText(r.journey);
      toast(r.journey ? "Journey saved" : "Journey line turned off", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-2 px-4 py-3.5">
      <label htmlFor="journey" className="text-md font-semibold">
        Where you are now <span className="text-sm font-normal text-ink-soft">optional</span>
      </label>
      <textarea
        id="journey"
        rows={2}
        maxLength={400}
        value={text}
        disabled={saved === null}
        onChange={(e) => setText(e.target.value)}
        placeholder="Week 6 of posting a Short every day. 312 subscribers, aiming for 1,000 by March."
        className="field-input resize-y py-1.5 text-base leading-snug"
      />
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm text-ink-soft">Update it as you grow. Leave it empty to turn the line off.</span>
        <Button size="sm" variant="primary" loading={busy} disabled={saved === null || text.trim() === saved} onClick={save}>
          Save
        </Button>
      </div>
    </div>
  );
}

/* ---------- About & updates (desktop app) ---------- */

function AboutRows() {
  const u = useUpdates();
  const auto = useAutoCheck();
  useEffect(startUpdates, []);
  if (!u.desktop) {
    return <p className="m-0 p-4 text-base text-ink-soft">This is the browser version: update it with git pull in the project folder. The desktop app updates itself.</p>;
  }
  const busy = u.status === "downloading" || u.status === "installing";
  const checked = u.checkedAt ? new Date(u.checkedAt).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "";
  const pct = u.progress?.total ? Math.round((u.progress.downloaded / u.progress.total) * 100) : null;
  return (
    <>
      <SettingRow
        title={`Shorts Studio ${u.version}`}
        hint={
          u.status === "checking"
            ? "Checking for updates…"
            : u.status === "latest"
              ? `You have the latest version. Checked ${checked}.`
              : u.status === "available" && u.update
                ? `Version ${u.update.version} is available.`
                : u.status === "downloading"
                  ? `Downloading the update${pct !== null ? ` (${pct}%)` : ""}…`
                  : u.status === "installing"
                    ? "Installing… the app restarts in a moment."
                    : u.status === "error"
                      ? u.error
                      : "Not checked yet."
        }
      >
        {u.status === "available" || (u.installFailed && u.update) ? (
          <Button size="sm" variant="primary" icon={<Download className="size-3.5" />} onClick={() => void install()}>
            {u.installFailed ? "Try again" : "Install and restart"}
          </Button>
        ) : (
          <Button size="sm" loading={u.status === "checking"} disabled={busy} onClick={() => void checkNow()}>
            Check now
          </Button>
        )}
      </SettingRow>
      {u.update && (u.status === "available" || busy) && u.update.notes && (
        <div className="grid gap-1.5 px-4 py-3.5">
          <span className="text-sm font-semibold text-ink-soft">What&apos;s new in {u.update.version}</span>
          <p className="well m-0 max-h-56 overflow-y-auto p-3 text-sm whitespace-pre-line">{u.update.notes}</p>
        </div>
      )}
      <SettingRow title="Check automatically" hint="When the app starts and every few hours. You choose when to install.">
        <input type="checkbox" aria-label="Check for updates automatically" checked={auto} onChange={(e) => setAutoCheck(e.target.checked)} className="size-4 accent-cobalt" />
      </SettingRow>
    </>
  );
}

/* ---------- AI features (local models) ---------- */

function SceneArt() {
  const { status, reload } = useArtStatus();
  const [error, setError] = useState("");
  if (!status) return <p className="m-0 p-4 text-base text-ink-soft">Checking the graphics card…</p>;
  const addon = status.addon;
  const music = addon?.scope === "music";
  const install =
    addon && (addon.needed || addon.installing) ? (
      <div className="grid gap-2 px-4 py-4">
        <span className="text-md font-semibold">{music ? "Music extras" : "AI add-on"}</span>
        <span className="max-w-[62ch] text-base text-ink-soft">
          {music
            ? "Accurate lyric timing (Whisper), beat-cut music videos and vocal separation, with a one-time install"
            : "Scene art, accurate lyric timing (Whisper) and beat-cut music videos run on your graphics card with a one-time add-on"}
          : {addon.size} to download, into {addon.folder}. No restart needed.
        </span>
        {addon.installing ? (
          <AddonProgress addon={addon} />
        ) : (
          <Button
            size="sm"
            variant="primary"
            className="justify-self-start"
            icon={<Download className="size-3.5" />}
            onClick={async () => {
              setError("");
              try {
                await api.installAddon();
                reload();
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            {addon.error ? "Try again" : `${music ? "Install music extras" : "Install AI add-on"} (${addon.size.replace("about ", "~")})`}
          </Button>
        )}
        {(error || addon.error) && <p className="m-0 max-w-[62ch] text-sm break-words whitespace-pre-wrap text-danger">{error || addon.error}</p>}
      </div>
    ) : null;
  if (music) {
    return (
      <>
        {install ?? (
          <div className="px-4 py-3 text-base">
            <StatusDot on>Music extras installed: Whisper lyric timing, beat detection, vocal separation</StatusDot>
          </div>
        )}
        <p className="m-0 px-4 py-3 text-base text-ink-soft">AI scene art needs an Apple Silicon Mac (M1 or newer), so videos use stock footage.</p>
      </>
    );
  }
  if (!status.installed && install) return install;
  if (!status.installed || !status.gpu) {
    return (
      <p className="m-0 p-4 text-base text-ink-soft">
        {!status.installed ? "AI scene art isn't installed on this computer." : "No NVIDIA graphics card or Apple Silicon GPU was found, so videos use stock footage."}
      </p>
    );
  }
  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-base">
        <StatusDot on>{status.gpu}</StatusDot>
        <span className="text-sm text-ink-soft">Models are kept in {status.folder}</span>
      </div>
      {ART_STYLES.map((a) => {
        const st = status.styles[a.value];
        return (
          <div key={a.value} className="flex flex-wrap items-center gap-3 px-4 py-3">
            <div className="grid min-w-0 flex-1 gap-0.5">
              <span className="text-md font-semibold">{st.label}</span>
              <span className="text-sm text-ink-soft">{a.hint}</span>
              {st.error && <span className="text-sm text-danger">{st.error}</span>}
              {!st.downloaded && <DownloadProgress progress={st.progress} label={st.label} />}
            </div>
            {st.downloaded ? (
              <StatusDot on>Ready</StatusDot>
            ) : (
              <Button
                size="sm"
                icon={<Download className="size-3.5" />}
                loading={st.downloading}
                onClick={async () => {
                  setError("");
                  try {
                    await api.artDownload(a.value);
                    reload();
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                {st.downloading ? "Downloading…" : st.progress ? "Resume download" : "Download (~7 GB)"}
              </Button>
            )}
          </div>
        );
      })}
      {error && <p className="m-0 px-4 py-3 text-base text-danger">{error}</p>}
    </>
  );
}

/* ---------- Storage (where the library is kept) ---------- */

/** After the folders change the engine restarts on them: wait until it answers again. */
async function waitForEngine() {
  await new Promise((r) => window.setTimeout(r, 1500));
  for (let i = 0; i < 60; i++) {
    try {
      await api.locations();
      return;
    } catch {
      await new Promise((r) => window.setTimeout(r, 1000));
    }
  }
}

type FolderKey = "data" | "videos";
const FOLDERS: Record<FolderKey, { name: string; does: string; pick: string }> = {
  data: {
    name: "Data folder",
    does: "Drafts, uploads, downloaded footage and music, fonts, campaigns and your keys.",
    pick: "Choose the data folder",
  },
  videos: { name: "Finished videos", does: "Every rendered video, with its thumbnail and post text.", pick: "Choose the folder for finished videos" },
};

const size = (b: number) => (b >= 1e9 ? `${(b / 1e9).toFixed(1)} GB` : `${Math.max(Math.round(b / 1e6), b ? 1 : 0)} MB`);
/** Groups that can't be undone start unticked; the rest only cost a download or a redraw. */
const KEEP_BY_DEFAULT = new Set(["old", "removed"]);

function CleanUp() {
  const toast = useToast();
  const [groups, setGroups] = useState<CleanupGroup[] | null>(null);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");
  const [sure, setSure] = useState(false);
  const [busy, setBusy] = useState(false);

  const scan = () => {
    setGroups(null);
    setError("");
    api
      .cleanupScan()
      .then((r) => {
        setGroups(r.groups);
        setPicked(new Set(r.groups.filter((g) => !KEEP_BY_DEFAULT.has(g.id)).map((g) => g.id)));
      })
      .catch((e) => setError((e as Error).message));
  };
  useEffect(() => {
    const t = setTimeout(scan, 0); // a timer callback, so the first scan isn't a setState in the effect body
    return () => clearTimeout(t);
  }, []);

  if (!groups) return <p className={`m-0 p-4 text-base ${error ? "text-danger" : "text-ink-soft"}`}>{error || "Looking for files nothing uses…"}</p>;
  if (groups.length === 0) return <p className="m-0 p-4 text-base text-ink-soft">Nothing to clean up: every file is in use.</p>;
  const total = groups.filter((g) => picked.has(g.id)).reduce((n, g) => n + g.bytes, 0);

  async function run() {
    setBusy(true);
    try {
      const r = await api.cleanupRun([...picked]);
      toast(`Freed ${size(r.freed)} (${r.files} files)${r.failed ? `. ${r.failed} are open in another program and stayed.` : ""}`, "success");
      scan();
    } catch (e) {
      toast((e as Error).message, "error");
    }
    setSure(false);
    setBusy(false);
  }

  return (
    <>
      {groups.map((g) => (
        <label key={g.id} className="grid cursor-pointer gap-1 p-4 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:gap-x-3">
          <input
            type="checkbox"
            className="mt-1 size-4 accent-cobalt"
            checked={picked.has(g.id)}
            disabled={busy}
            onChange={(e) => {
              setSure(false);
              setPicked((p) => {
                const next = new Set(p);
                if (e.target.checked) next.add(g.id);
                else next.delete(g.id);
                return next;
              });
            }}
          />
          <span className="min-w-0">
            <span className="block text-md font-semibold">{g.label}</span>
            <span className="block text-base text-ink-soft">{g.hint}</span>
            <span className="block text-sm text-ink-soft">If deleted: {g.cost}</span>
            <span className="block truncate text-sm text-ink-soft">
              {g.files} files, e.g. {g.examples.join(", ")}
            </span>
          </span>
          <span className="text-md font-semibold tabular-nums sm:text-right">{size(g.bytes)}</span>
        </label>
      ))}
      <div className="flex flex-wrap items-center gap-2 p-4">
        <Button
          size="sm"
          variant={sure ? "primary" : "secondary"}
          icon={<Trash2 className="size-3.5" />}
          loading={busy}
          disabled={busy || total === 0}
          onClick={() => (sure ? void run() : setSure(true))}
        >
          {sure ? `Click again to delete ${size(total)}` : total ? `Free ${size(total)}` : "Pick something to free"}
        </Button>
        <Button size="sm" variant="ghost" disabled={busy} onClick={scan}>
          Check again
        </Button>
        <span className="text-sm text-ink-soft">Deleted files don&apos;t go to the recycle bin. Videos you have finished are never touched.</span>
      </div>
    </>
  );
}

function Storage() {
  const toast = useToast();
  const [loc, setLoc] = useState<Locations | null>(null);
  const [error, setError] = useState("");
  const [typing, setTyping] = useState<{ which: FolderKey; value: string } | null>(null); // browser: no folder picker
  const [pending, setPending] = useState<{ data: string; videos: string } | null>(null); // a move waiting for "Move"
  const [moving, setMoving] = useState(false);

  useEffect(() => {
    api.locations().then(setLoc).catch((e) => setError((e as Error).message));
  }, []);

  if (!loc) return <p className={`m-0 p-4 text-base ${error ? "text-danger" : "text-ink-soft"}`}>{error || "Checking folders…"}</p>;

  const current = { data: loc.data, videos: loc.videos_default ? "" : loc.videos };
  const propose = (which: FolderKey, path: string) => {
    setTyping(null);
    const next = { ...current, [which]: path.trim() };
    if (next.data !== current.data || next.videos !== current.videos) setPending(next);
  };

  async function choose(which: FolderKey) {
    const start = which === "data" ? loc!.data : loc!.videos;
    try {
      const picked = await pickFolder(FOLDERS[which].pick, start);
      if (picked === undefined) setTyping({ which, value: start });
      else if (picked) propose(which, picked);
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  async function open(which: FolderKey) {
    try {
      await api.openLocation(which);
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  async function move() {
    if (!pending) return;
    setMoving(true);
    try {
      const r = await api.moveLocations(pending.data, pending.videos);
      await waitForEngine();
      toast(r.left_behind ? `Moved. ${r.left_behind} older duplicate files stayed in the old folder.` : "Moved. Your library is in its new folder.", "success");
      window.location.reload(); // every list on the page came from the old folders
    } catch (e) {
      toast((e as Error).message, "error");
      setMoving(false);
    }
  }

  const videosNote = pending && !pending.videos ? `${pending.data}\\output` : pending?.videos;
  return (
    <>
      {(Object.keys(FOLDERS) as FolderKey[]).map((which) => {
        const path = which === "data" ? loc.data : loc.videos;
        return (
          <div key={which} className="grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="text-md font-semibold">{FOLDERS[which].name}</span>
                {which === "videos" && loc.videos_default && <StatusDot on={false}>Inside the data folder</StatusDot>}
              </div>
              <p className="m-0 mt-0.5 text-base text-ink-soft">{FOLDERS[which].does}</p>
              <code className="mt-1.5 block truncate text-sm text-ink" title={path}>
                {path}
              </code>
            </div>
            <div className="flex flex-wrap gap-1">
              <Button size="sm" variant="ghost" icon={<FolderOpen className="size-3.5" />} onClick={() => open(which)}>
                Open
              </Button>
              {!loc.locked && (
                <Button size="sm" variant="secondary" disabled={moving} onClick={() => choose(which)}>
                  Change…
                </Button>
              )}
              {which === "videos" && !loc.videos_default && !loc.locked && (
                <Button size="sm" variant="ghost" disabled={moving} onClick={() => propose("videos", "")}>
                  Use default
                </Button>
              )}
            </div>
            {typing?.which === which && (
              <form
                className="flex gap-2 sm:col-span-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (typing.value.trim()) propose(which, typing.value);
                }}
              >
                <input
                  aria-label={`${FOLDERS[which].name} path`}
                  autoFocus
                  spellCheck={false}
                  value={typing.value}
                  onChange={(e) => setTyping({ which, value: e.target.value })}
                  placeholder="Full folder path, e.g. D:\Shorts Studio"
                  className="field-input h-9 min-w-0 flex-1 py-0 text-base"
                />
                <Button type="submit" size="sm" variant="primary" className="h-9" disabled={!typing.value.trim()}>
                  Next
                </Button>
                <Button size="sm" variant="ghost" className="h-9" onClick={() => setTyping(null)}>
                  Cancel
                </Button>
              </form>
            )}
          </div>
        );
      })}
      {loc.locked && <p className="m-0 p-4 text-base text-ink-soft">The data folder is set by CRCONTENT_DATA_DIR, so it can&apos;t be changed here.</p>}
      {pending && (
        <div className="grid gap-3 bg-caption/15 p-4">
          <div className="text-base">
            <p className="m-0 font-semibold">Move your files?</p>
            <ul className="m-0 mt-1 grid gap-0.5 pl-4 text-ink-soft">
              {pending.data !== current.data && (
                <li>
                  Data → <code className="text-ink">{pending.data}</code>
                </li>
              )}
              {(pending.videos !== current.videos || (!pending.videos && pending.data !== current.data)) && (
                <li>
                  Finished videos → <code className="text-ink">{videosNote}</code>
                </li>
              )}
            </ul>
            <p className="m-0 mt-1.5 text-ink-soft">
              Files are moved, not copied. Anything already in the new folder is kept. Moving to another drive can take a few minutes; the engine restarts when
              it&apos;s done.
            </p>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="primary" loading={moving} onClick={move}>
              {moving ? "Moving…" : "Move files"}
            </Button>
            <Button size="sm" variant="ghost" disabled={moving} onClick={() => setPending(null)}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </>
  );
}

/* ---------- Channels (YouTube / TikTok) ---------- */

/** The developer app keys a platform needs before "Connect" (the secret never comes back from the engine). */
function AppKeysForm({
  platform,
  account,
  redirectUri,
  onSaved,
  onCancel,
}: {
  platform: Platform;
  account: PublishAccount;
  redirectUri: string;
  onSaved: (accounts: PublishAccounts) => void;
  onCancel?: () => void;
}) {
  const toast = useToast();
  const [clientId, setClientId] = useState(account.client_id);
  const [secret, setSecret] = useState("");
  const [saving, setSaving] = useState(false);
  const changesApp = account.configured && clientId.trim() !== account.client_id;

  async function save(keys: { client_id: string; client_secret: string }) {
    setSaving(true);
    try {
      onSaved(await api.savePublishApp(platform, keys));
      toast(keys.client_id ? `${PLATFORM_NAMES[platform]} app keys saved` : `${PLATFORM_NAMES[platform]} app keys removed`, "success");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      className="grid gap-3 rounded-lg bg-sunken p-3.5"
      onSubmit={(e) => {
        e.preventDefault();
        void save({ client_id: clientId, client_secret: secret });
      }}
    >
      <p className="m-0 max-w-[62ch] text-base text-ink-soft">
        {HOW_TO[platform].steps}{" "}
        <a href={HOW_TO[platform].url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-cobalt">
          Open developer console <ExternalLink className="size-3" />
        </a>
      </p>
      <div className="grid gap-1.5">
        <span className="field-label">Redirect URI</span>
        <div className="flex items-center gap-1 rounded-md border border-line bg-panel py-0.5 pr-0.5 pl-3">
          <code className="min-w-0 flex-1 truncate text-sm">{redirectUri}</code>
          <IconButton
            label="Copy redirect URI"
            onClick={async () => {
              await navigator.clipboard.writeText(redirectUri);
              toast("Redirect URI copied", "success");
            }}
          >
            <Copy className="size-4" />
          </IconButton>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1.5">
          <span className="field-label">{ID_LABEL[platform]}</span>
          <input className="field-input h-9 py-0 text-base" autoComplete="off" spellCheck={false} value={clientId} onChange={(e) => setClientId(e.target.value)} />
        </label>
        <label className="grid gap-1.5">
          <span className="field-label">Client secret</span>
          <input
            type="password"
            className="field-input h-9 py-0 text-base"
            placeholder={account.configured && !changesApp ? "Saved. Leave empty to keep it." : ""}
            autoComplete="off"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
          />
        </label>
      </div>
      {changesApp && account.connected && (
        <p className="m-0 text-sm text-warn">Saving a different app disconnects {account.account}. Connect again afterwards.</p>
      )}
      <div className="flex items-center gap-1">
        <Button type="submit" size="sm" variant="primary" loading={saving} disabled={!clientId.trim() || (!secret.trim() && (!account.configured || changesApp))}>
          Save app keys
        </Button>
        {onCancel && (
          <Button size="sm" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        )}
        {account.configured && (
          <Button size="sm" variant="danger" className="ml-auto" disabled={saving} onClick={() => save({ client_id: "", client_secret: "" })}>
            Remove app keys
          </Button>
        )}
      </div>
    </form>
  );
}

/** When auto-upload posts: right after each render, or at the next free time of day from a list. */
function PostingTimes({
  platform,
  account,
  onChange,
}: {
  platform: Platform;
  account: PublishAccount;
  onChange: (s: { when?: "now" | "slots"; times?: string[] }) => void;
}) {
  const [adding, setAdding] = useState("12:00");
  const add = () => adding && !account.times.includes(adding) && onChange({ times: [...account.times, adding] });
  return (
    <div className="grid gap-2.5 rounded-lg bg-sunken p-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className="field-label">New renders upload</span>
        <Segmented
          name={`when-${platform}`}
          size="sm"
          value={account.when}
          onChange={(when) => onChange({ when })}
          options={[
            { value: "now", label: "Right away" },
            { value: "slots", label: "At set times" },
          ]}
        />
      </div>
      {account.when === "slots" && (
        <>
          <div className="flex flex-wrap items-center gap-1.5">
            {account.times.map((t) => (
              <span key={t} className="inline-flex h-7 items-center gap-1 rounded-full border border-line bg-panel pr-1 pl-2.5 text-sm font-semibold tabular-nums">
                {t}
                <button
                  type="button"
                  aria-label={`Remove ${t}`}
                  disabled={account.times.length === 1}
                  onClick={() => onChange({ times: account.times.filter((x) => x !== t) })}
                  className="grid size-5 cursor-pointer place-items-center rounded-full border-0 bg-transparent text-ink-soft hover:bg-ink/[0.06] hover:text-danger disabled:cursor-not-allowed disabled:opacity-30"
                >
                  <X className="size-3" />
                </button>
              </span>
            ))}
            <span className="flex items-center gap-1">
              <input
                aria-label="Posting time to add"
                type="time"
                className="field-input h-7 w-[110px] py-0 text-sm"
                value={adding}
                onChange={(e) => setAdding(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && add()}
              />
              <IconButton label="Add posting time" onClick={add}>
                <Plus className="size-4" />
              </IconButton>
            </span>
          </div>
          <p className="m-0 text-sm text-ink-soft">Each new video takes the next free time, one per slot, so a batch of clips spreads over the days.</p>
        </>
      )}
    </div>
  );
}

/** The connected YouTube channels: which one is the default, and disconnecting one. */
function YouTubeChannels({ accounts, setAccounts }: { accounts: PublishAccounts; setAccounts: (a: PublishAccounts) => void }) {
  const toast = useToast();
  const a = accounts.youtube;
  const channels = a.channels ?? [];
  if (channels.length === 0) return null;

  async function run(call: Promise<PublishAccounts>) {
    try {
      setAccounts(await call);
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  return (
    <div className="grid gap-1.5">
      <ul className="m-0 grid list-none gap-1 p-0">
        {channels.map((c) => {
          const isDefault = c.id === a.channel;
          return (
            <li key={c.id} className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg bg-sunken py-1.5 pr-1.5 pl-3">
              <span className="min-w-0 truncate text-base font-semibold">{c.name || c.id}</span>
              {isDefault && channels.length > 1 && (
                <span className="rounded-full bg-cobalt/10 px-2 py-0.5 text-xs font-semibold text-cobalt">Default</span>
              )}
              {!c.can_comment && (a.comment ?? true) && <span className="text-sm text-warn">Connect again to allow comments</span>}
              <span className="ml-auto flex items-center gap-1">
                {!isDefault && (
                  <Button size="sm" variant="ghost" onClick={() => run(api.publishSettings("youtube", { channel: c.id }))}>
                    Make default
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="ghost"
                  icon={<LogOut className="size-3.5" />}
                  aria-label={`Disconnect ${c.name || c.id}`}
                  onClick={() => run(api.disconnectPlatform("youtube", c.id))}
                >
                  Disconnect
                </Button>
              </span>
            </li>
          );
        })}
      </ul>
      {channels.length > 1 && (
        <p className="m-0 text-sm text-ink-soft">
          Uploads go to the default channel unless you pick another on the video&apos;s Upload card. Auto-uploads and set-time uploads always use the default.
        </p>
      )}
    </div>
  );
}

function ChannelRow({ platform, accounts, setAccounts }: { platform: Platform; accounts: PublishAccounts; setAccounts: (a: PublishAccounts) => void }) {
  const toast = useToast();
  const a = accounts[platform];
  const youtube = platform === "youtube" && !!a.channels; // an older engine has no channel list: one account only
  const multi = youtube && (a.channels?.length ?? 0) > 1;
  const meta = META.includes(platform);
  const sharesKeys = platform === "instagram"; // its app keys are the Meta app's, edited on the Facebook row
  const [editingKeys, setEditingKeys] = useState(false);
  const [signInUrl, setSignInUrl] = useState("");

  async function connect() {
    try {
      const { url } = await api.connectPlatform(platform);
      setSignInUrl(url);
      setAccounts(await api.publishAccounts());
      toast(`Finish signing in to ${PLATFORM_NAMES[platform]} in your browser`, "success");
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  async function change(settings: Parameters<typeof api.publishSettings>[1]) {
    try {
      setAccounts(await api.publishSettings(platform, settings));
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  return (
    <div className="grid gap-4 p-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="text-md font-semibold">{PLATFORM_NAMES[platform]}</span>
        <StatusDot on={a.connected}>
          {!a.connected
            ? a.no_linked_account
              ? "No Instagram account linked"
              : a.configured
                ? "Not connected"
                : sharesKeys
                  ? "Needs the Meta app keys"
                  : "Needs app keys"
            : multi
              ? `${a.channels?.length} channels`
              : a.account}
        </StatusDot>
        <span className="ml-auto flex items-center gap-1">
          {a.configured && !a.connected && (
            <Button size="sm" variant="primary" loading={a.connecting} onClick={connect}>
              {a.no_linked_account ? "Connect again" : "Connect"}
            </Button>
          )}
          {a.configured && a.connected && youtube && (
            <Button size="sm" variant="ghost" icon={<Plus className="size-3.5" />} loading={a.connecting} onClick={connect}>
              Add channel
            </Button>
          )}
          {(a.connected || (meta && accounts.facebook.connected)) && !youtube && (
            <Button
              size="sm"
              variant="ghost"
              icon={<LogOut className="size-3.5" />}
              title={meta ? "Facebook and Instagram share one sign-in: this disconnects both" : undefined}
              onClick={async () => setAccounts(await api.disconnectPlatform(platform))}
            >
              Disconnect
            </Button>
          )}
          {a.configured && !sharesKeys && (
            <Button size="sm" variant="ghost" icon={<KeyRound className="size-3.5" />} aria-expanded={editingKeys} onClick={() => setEditingKeys((v) => !v)}>
              App keys
            </Button>
          )}
        </span>
      </div>
      {a.connecting && signInUrl && (
        <p className="m-0 text-sm break-all text-ink-soft">
          Waiting for the sign-in in your browser. If no browser opened,{" "}
          <a href={signInUrl} target="_blank" rel="noreferrer" className="text-cobalt">
            open the sign-in page
          </a>
          .
        </p>
      )}
      {youtube && a.connecting && a.connected && (
        <p className="m-0 text-sm text-ink-soft">
          On Google&apos;s sign-in, pick the account (or brand account) that owns the channel to add. Signing in to a channel that&apos;s already here renews it.
        </p>
      )}
      {youtube && a.connected && <YouTubeChannels accounts={accounts} setAccounts={setAccounts} />}
      {sharesKeys && !a.configured && (
        <p className="m-0 text-sm text-ink-soft">Instagram uses the same Meta app as Facebook: add its App ID and secret on the Facebook row above.</p>
      )}
      {meta && a.no_linked_account && (
        <p className="m-0 text-sm text-warn">
          None of your Pages has an Instagram account linked. Switch Instagram to a professional (Business or Creator) account, link it to your Page in the
          Instagram app (Settings → Account Center or Edit profile → Page), then press Connect again and allow Instagram.
        </p>
      )}
      {meta && !a.connected && a.configured && !a.no_linked_account && (
        <p className="m-0 text-sm text-ink-soft">
          One sign-in connects both Facebook and Instagram. When Facebook asks, choose your Page and its Instagram account and allow every permission.
        </p>
      )}
      {(!a.configured || editingKeys) && !sharesKeys && (
        <AppKeysForm
          key={`${platform}-${a.client_id}`}
          platform={platform}
          account={a}
          redirectUri={accounts.redirect_uri[platform]}
          onSaved={(next) => {
            setAccounts(next);
            setEditingKeys(false);
          }}
          onCancel={a.configured ? () => setEditingKeys(false) : undefined}
        />
      )}
      {a.connected && (
        <div className="grid gap-3 sm:grid-cols-[repeat(3,minmax(0,1fr))]">
          {platform === "tiktok" && (
            <label className="grid gap-1.5">
              <span className="field-label">Upload as</span>
              <select className="field-input h-9 py-0 text-base" value={a.mode} onChange={(e) => change({ mode: e.target.value as "direct" | "draft" })}>
                <option value="direct">Post directly</option>
                <option value="draft">TikTok draft</option>
              </select>
            </label>
          )}
          {platform === "facebook" && (a.pages?.length ?? 0) > 1 && (
            <label className="grid gap-1.5">
              <span className="field-label">Post to Page</span>
              <select className="field-input h-9 py-0 text-base" value={a.page} onChange={(e) => change({ page: e.target.value })}>
                {a.pages?.map((pg) => (
                  <option key={pg.id} value={pg.id}>
                    {pg.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {platform === "instagram" && (a.accounts?.length ?? 0) > 1 && (
            <label className="grid gap-1.5">
              <span className="field-label">Post to account</span>
              <select className="field-input h-9 py-0 text-base" value={a.account_id} onChange={(e) => change({ account_id: e.target.value })}>
                {a.accounts?.map((ac) => (
                  <option key={ac.id} value={ac.id}>
                    {ac.name} ({ac.page})
                  </option>
                ))}
              </select>
            </label>
          )}
          {(platform === "youtube" || (platform === "tiktok" && a.mode !== "draft")) && (
            <label className="grid gap-1.5">
              <span className="field-label">Who can watch</span>
              <select className="field-input h-9 py-0 text-base" value={a.privacy} onChange={(e) => change({ privacy: e.target.value })}>
                {(platform === "youtube" ? YT_PRIVACY : TT_PRIVACY).map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="flex items-center gap-2 self-end pb-2 text-base font-semibold">
            <input type="checkbox" checked={a.auto} onChange={(e) => change({ auto: e.target.checked })} className="size-4 accent-cobalt" />
            Upload new renders automatically
          </label>
          {platform === "youtube" && accounts.youtube_categories && (
            <label className="grid gap-1.5">
              <span className="field-label">Category</span>
              <select className="field-input h-9 py-0 text-base" value={a.category ?? "auto"} onChange={(e) => change({ category: e.target.value })}>
                <option value="auto">Auto (Music for music videos, else People &amp; Blogs)</option>
                {Object.entries(accounts.youtube_categories).map(([id, name]) => (
                  <option key={id} value={id}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {platform === "instagram" && (
            <label className="flex items-center gap-2 text-base font-semibold sm:col-span-3">
              <input type="checkbox" checked={a.share_to_feed ?? true} onChange={(e) => change({ share_to_feed: e.target.checked })} className="size-4 accent-cobalt" />
              Also show Reels in the profile grid
            </label>
          )}
          {meta && (
            <p className="m-0 text-sm text-ink-soft sm:col-span-3">
              {platform === "facebook"
                ? "Vertical videos up to 90 seconds post as public Reels; longer or landscape videos as regular Page videos."
                : "Videos post as public Reels, with your thumbnail's frame as the cover."}
            </p>
          )}
          {platform === "youtube" && (
            <label className="flex items-center gap-2 text-base font-semibold sm:col-span-3">
              <input type="checkbox" checked={a.comment ?? true} onChange={(e) => change({ comment: e.target.checked })} className="size-4 accent-cobalt" />
              Post Gemini&apos;s fact-check comment after upload (a comment you write is always posted)
            </label>
          )}
        </div>
      )}
      {platform === "youtube" && !youtube && a.connected && (a.comment ?? true) && a.can_comment === false && (
        <p className="m-0 text-sm text-warn">
          To post comments, YouTube needs one more permission: press Disconnect, then Connect, and allow it. Until then the comment is only shown for you to copy.
        </p>
      )}
      {a.connected && a.auto && <PostingTimes platform={platform} account={a} onChange={change} />}
      {platform === "tiktok" && a.connected && a.mode === "direct" && a.privacy !== "SELF_ONLY" && (
        <p className="m-0 text-sm text-ink-soft">
          Until TikTok audits your developer app, direct posts can only be &ldquo;Only me&rdquo;. Choose TikTok draft to post publicly from the app.
        </p>
      )}
    </div>
  );
}

const STATUS_TEXT: Record<ScheduledUpload["status"], string> = { scheduled: "Scheduled", uploading: "Uploading", done: "Uploaded", error: "Failed" };

/** Every scheduled upload (and the latest finished ones), with a way to cancel what hasn't started. */
function UploadQueue() {
  const toast = useToast();
  const [items, setItems] = useState<ScheduledUpload[] | null>(null);
  useEffect(() => {
    const load = () => api.schedule().then(setItems).catch(() => setItems([]));
    void load();
    const t = window.setInterval(load, 15000);
    return () => window.clearInterval(t);
  }, []);
  if (items === null) return <p className="m-0 p-4 text-base text-ink-soft">Loading…</p>;
  if (items.length === 0) {
    return <p className="m-0 p-4 text-base text-ink-soft">Nothing scheduled. Schedule a video from its Upload card, or turn on auto-upload at set times.</p>;
  }
  return (
    <ul className="m-0 list-none divide-y divide-line p-0">
      {items.slice(0, 30).map((i) => (
        <li key={i.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 py-2.5">
          <span className="min-w-0">
            <span className="block truncate text-base font-semibold">{i.title}</span>
            <span className="flex flex-wrap items-center gap-x-2 text-sm text-ink-soft">
              <CalendarClock className="size-3.5" />
              {PLATFORM_NAMES[i.platform]}
              {i.channel_name ? ` (${i.channel_name})` : ""},{" "}
              {new Date(i.at).toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
              <span className={`font-semibold ${i.status === "done" ? "text-ok" : i.status === "error" ? "text-danger" : "text-ink"}`}>{STATUS_TEXT[i.status]}</span>
              {i.source === "auto" && <span>auto</span>}
              {i.url && (
                <a href={i.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-cobalt">
                  view <ExternalLink className="size-3" />
                </a>
              )}
            </span>
            {i.error && <span className="block text-sm text-danger">{i.error}</span>}
          </span>
          {i.status === "scheduled" && (
            <Button
              size="sm"
              variant="ghost"
              onClick={async () => {
                try {
                  await api.cancelScheduled(i.id);
                  setItems((all) => all?.filter((x) => x.id !== i.id) ?? all);
                } catch (e) {
                  toast((e as Error).message, "error");
                }
              }}
            >
              Cancel
            </Button>
          )}
        </li>
      ))}
    </ul>
  );
}

/** Settings: the keys for Gemini and the media services, the channels videos upload to, and where files are kept. */
export function Settings({ onKeysChanged }: { onKeysChanged: () => void }) {
  const [keys, setKeys] = useState<ServiceKeys | null>(null);
  const [accounts, setAccounts] = useState<PublishAccounts | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.serviceKeys().then(setKeys).catch((e) => setError((e as Error).message));
    api.publishAccounts().then(setAccounts).catch((e) => setError((e as Error).message));
  }, []);

  // while a sign-in is open in the browser, check every few seconds whether it finished
  const connecting = !!accounts && PLATFORMS.some((p) => accounts[p]?.connecting);
  useEffect(() => {
    if (!connecting) return;
    const t = window.setInterval(() => api.publishAccounts().then(setAccounts).catch(() => {}), 2500);
    return () => window.clearInterval(t);
  }, [connecting]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto grid max-w-[880px] gap-10 px-4 py-8 sm:px-8 lg:grid-cols-[160px_minmax(0,1fr)]">
        <aside className="hidden lg:block">
          <SectionNav />
        </aside>
        <div className="grid min-w-0 gap-10">
          <header>
            <h1 className="page-title m-0">Settings</h1>
            <p className="page-intro m-0 mt-1">Keys and accounts are saved on this computer only.</p>
            {error && <p className="m-0 mt-3 text-base text-danger">{error}</p>}
          </header>
          <Section id="services" title="Services" intro="The AI and media services the studio uses. Changes apply right away, no restart needed.">
            {SERVICES.map((s) => (
              <ServiceRow
                key={s.key}
                service={s}
                state={keys?.[s.key]}
                onSaved={(k) => {
                  setKeys(k);
                  onKeysChanged();
                }}
              />
            ))}
          </Section>
          <Section
            id="channels"
            title="Channels"
            intro="Connect the accounts your videos upload to. Each one uses your own developer app, then you sign in once."
          >
            {accounts ? (
              PLATFORMS.filter((p) => accounts[p]).map((p) => <ChannelRow key={p} platform={p} accounts={accounts} setAccounts={setAccounts} />)
            ) : (
              <p className="m-0 p-4 text-base text-ink-soft">Checking accounts…</p>
            )}
          </Section>
          <Section
            id="journey"
            title="Your journey"
            intro="Viewers stick with a channel they feel they're growing with. Say where you are, and Gemini works one honest line about it into each description it writes, never into the video itself."
          >
            <JourneyRow />
          </Section>
          <Section
            id="queue"
            title="Upload queue"
            intro="Scheduled uploads go out while the app runs (also in the background, from the tray or menu bar). Anything that came due while it wasn't running goes out when it starts."
          >
            <BackgroundRow />
            <UploadQueue />
          </Section>
          <Section
            id="scene-art"
            title="AI features"
            intro="Accurate lyric timing, beat-cut music videos and AI scene art (anime, cinematic or flat 2D pictures), running on this computer for free after a one-time download."
          >
            <SceneArt />
          </Section>
          <Section id="appearance" title="Appearance" intro="How the studio looks on this computer.">
            <AppearanceRows />
          </Section>
          <Section id="storage" title="Storage" intro="Where your library is kept. Changing a folder moves the files there.">
            <Storage />
          </Section>
          <Section id="cleanup" title="Clean up" intro="Remove files nothing uses any more to save space. Each group says what deleting it costs; nothing is deleted until you press the button.">
            <CleanUp />
          </Section>
          <Section id="about" title="About & updates" intro="New versions come from the project's releases on GitHub and install with one click.">
            <AboutRows />
          </Section>
        </div>
      </div>
    </div>
  );
}
