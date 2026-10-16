// Typed client for the Python engine (crcontent/web.py). The browser calls it directly.

import type { MusicUse } from "./musicLicence";

declare global {
  interface Window {
    /** Set by the desktop app (src-tauri), which starts the engine on a free port. */
    __ENGINE_URL__?: string;
    /** Tauri's IPC bridge (desktop app only): src-tauri commands such as pick_folder. */
    __TAURI_INTERNALS__?: { invoke: <T>(cmd: string, args?: Record<string, unknown>) => Promise<T> };
  }
}

const desktopEngine = typeof window !== "undefined" ? window.__ENGINE_URL__ : undefined;

export const API_BASE = (desktopEngine ?? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export type Lang = "en" | "km";

export interface Scene {
  narration: string;
  visual_query: string;
  on_screen_text: string;
  media: string; // "" = automatic footage, otherwise a project-relative path
  seconds?: number; // length of a scene without narration (a sound-effect beat)
  keywords?: string[]; // transcript editor: words drawn in the keyword colour (see keyword())
  cuts?: [number, number][]; // transcript editor: seconds cut out of the voiceover cuts_key
  cuts_key?: string;
  media_start?: number; // timeline: seconds into the clip where the scene's footage starts
  layout?: Layout;
  media2?: string; // split layout: the clip below ("" = picked automatically)
  broll?: BRoll[];
  texts?: TextOverlay[];
  // AI scene art (the script has an art_style): the picture's prompt, its seed (another seed = another take),
  // the camera move over it and atmosphere effects
  art_prompt?: string;
  art_seed?: number;
  motion?: Motion | "";
  effects?: Effect[];
}

/** Looks the local AI scene art can draw in (crcontent/imagegen.py STYLES). */
export type ArtStyle = "anime" | "cinematic" | "flat";
export const ART_STYLES: { value: ArtStyle; label: string; hint: string }[] = [
  { value: "anime", label: "Anime", hint: "Anime illustration: skies, city lights, characters" },
  { value: "cinematic", label: "Cinematic", hint: "Photoreal film stills with dramatic light" },
  { value: "flat", label: "Flat 2D", hint: "Flat motion-graphics illustration, for explainers" },
];
/** Camera moves over a picture (crcontent/fx.py MOTIONS); the _3d ones split it into depth layers. */
export type Motion = "push_in" | "pull_out" | "pan_left" | "pan_right" | "tilt_up" | "tilt_down" | "orbit_3d" | "dolly_3d" | "rise_3d" | "still";
export type Effect = "glow" | "light_leak" | "dust" | "snow" | "embers" | "sparkles" | "petals" | "speed_lines" | "chromatic" | "grain" | "vignette" | "flash";
/** Effects you pick per scene; bloom, grain and vignette come with the art style. */
export const MOOD_EFFECTS: Effect[] = ["dust", "snow", "embers", "sparkles", "petals", "speed_lines", "light_leak", "flash"];

export interface ArtStatus {
  installed: boolean; // diffusers + torch are installed
  gpu: string; // "" = no usable GPU (NVIDIA with CUDA, or an Apple Silicon Mac)
  folder: string; // where models are kept
  styles: Record<
    ArtStyle,
    {
      label: string;
      downloaded: boolean;
      downloading: boolean;
      error: string;
      // bytes fetched / in total; speed (bytes/s) and eta (s) while this engine is downloading it; null = not started
      progress: { done: number; total: number; active: boolean; speed?: number; eta?: number | null } | null;
    }
  >;
  motions: Record<Motion, string>;
  effects: Record<Effect, string>;
  // the one-time AI add-on (torch, Stable Diffusion, Whisper), installed from Settings
  addon?: AddonStatus;
}

export interface AddonStatus {
  needed: boolean; // this engine lacks the AI libraries and the add-on can be installed here
  ready: boolean;
  scope: "all" | "music"; // an Intel Mac gets the music extras only (scene art needs NVIDIA or Apple Silicon)
  size: string; // "about 3 GB"
  installing: boolean;
  stage: string; // "Downloading torch", "Installing (a few minutes…)"…
  done: number; // bytes
  total: number;
  speed: number; // bytes/s
  error: string;
  folder: string;
}

/** How a scene's footage fills the frame: cropped / the whole clip over a blurred copy / two clips stacked. */
export type Layout = "fill" | "fit" | "split";

/** A cutaway over the footage for a while (seconds from the scene's start). */
export interface BRoll {
  media: string;
  at: number;
  duration: number;
}

/** Extra text on the frame for a while (seconds from the scene's start); x, y = its middle as fractions. */
export interface TextOverlay {
  text: string;
  at: number;
  duration: number;
  x: number;
  y: number;
  size: "s" | "m" | "l";
  color: string;
  box: boolean;
}

/** How a narrated video's captions and headlines look (crcontent/styles.py CaptionStyle). */
export interface CaptionStyle {
  preset: string;
  font: string; // "" = the language's caption font
  size: "s" | "m" | "l";
  y: number; // middle of the caption, fraction of the frame height
  headline_y: number; // top of the headline
  color: string;
  highlight: string; // the spoken word
  keyword: string; // keywords marked in the transcript
  outline: "outline" | "shadow" | "box" | "glow";
  case: "as_is" | "upper" | "lower";
  words: number; // shown together; 0 = the language's default
}

export const DEFAULT_CAPTIONS: CaptionStyle = {
  preset: "classic",
  font: "",
  size: "m",
  y: 0.62,
  headline_y: 0.12,
  color: "#FFFFFF",
  highlight: "#FFE500",
  keyword: "#4ADE80",
  outline: "outline",
  case: "as_is",
  words: 0,
};

/** A word in a scene's voiceover: times in seconds; `at` = its [start, end) in the narration text (null if not found). */
export interface VoiceWord {
  text: string;
  start: number;
  end: number;
  at: [number, number] | null;
  caption?: string; // the word as captions show it: with the narration's emoji that follow it
}

export interface SceneVoice {
  key: string; // the cached audio, at voiceoverUrl(key)
  duration: number;
  words: VoiceWord[];
}

/** A word as Scene.keywords stores it (same as crcontent/voiceover.py keyword()). */
export const keyword = (text: string) => text.replace(/^[\p{P}\p{S}\s]+|[\p{P}\p{S}\s]+$/gu, "").toLowerCase();

export interface VideoScript {
  title: string;
  scenes: Scene[];
  caption: string;
  hashtags: string[];
  // from a content plan's Music / Mood and Key Visual columns; key_scene is 1-based (0 = none)
  mood?: string;
  key_visual?: string;
  key_scene?: number;
  captions?: CaptionStyle;
  facts?: string[]; // content plan's Fact Check notes
  sources?: string; // added to the description as "Sources: …"
  pinned_comment?: string; // to paste under the video and pin
  art_style?: ArtStyle | ""; // "" = stock footage; else every scene without chosen media is drawn in this look
  art_bible?: string; // the director's notes (characters, world, palette) that keep the pictures consistent
  art_subject?: string; // the real subject every picture must get right ("name: visible features"), checked by Claude
  art_avoid?: string; // what the image model must not draw instead (look-alikes)
}

/** A video's real subject, for drawing its pictures (each one showing it is checked and redrawn when wrong). */
export interface ArtSubject {
  subject: string;
  avoid: string;
}

/** A comment to pin under the video from fact-check notes (same as crcontent/facts.py pinned_comment()). */
export const pinnedComment = (notes: string[]) => {
  const kept = notes.map((n) => n.trim()).filter(Boolean);
  return kept.length ? `📌 Fact check & sources:\n${kept.map((n) => `• ${n}`).join("\n")}` : "";
};

export interface SongSection {
  name: string; // "Verse 1", "Chorus"...
  lyrics: string[]; // sung lines; [] = instrumental
  styles: string[];
  seconds: number;
  visual_query: string;
}

export interface SongScript {
  title: string;
  genre: string;
  mood: string;
  bpm: number;
  vocal: string; // description of the singing voice
  styles: string[];
  avoid: string[];
  sections: SongSection[];
  caption: string;
  hashtags: string[];
}

export type Look = "natural" | "cinematic" | "film" | "moody" | "vibrant" | "dusk" | "mono";
export type LyricPreset = "classic" | "neon" | "bold_pop" | "cinematic" | "minimal" | "retro" | "boxed";
export type CutPace = "slow" | "normal" | "fast";
/** Old-tape treatments for a section (crcontent/fx.py TAPES / FRAMES). */
export type Tape = "" | "play" | "rewind" | "static_in" | "static";
export type TapeFrame = "full" | "4:3";

/** One section of a shot list: what it shows, how fast it cuts, and how it looks as an old tape. */
export interface DirectedSection {
  scene: string;
  pace: CutPace;
  tape?: Tape; // "" = a clean modern picture
  wear?: number; // 0..1: how worn the tape looks (each replay of a memory a little more)
  frame?: TapeFrame; // "4:3": a home video on a dark screen inside the frame
  stamp?: string; // the camcorder date, e.g. "MAY 31 1998"
  fade?: boolean; // the person in the memory fades away
}

/** Your music video idea as a shot list (crcontent/director.py direct_idea): a scene and cutting pace per section of
 *  the song, in order, plus the recurring characters and world. Followed by the pictures, the cuts and the footage. */
export interface SongDirection {
  idea: string; // the idea it was made from; ignored once the idea changes
  bible: string;
  sections: DirectedSection[];
  notes: string[]; // what can't be done literally, and what is done instead
  look?: Look | ""; // Claude's suggestions when it was made (applied to the settings then)
  lyric_preset?: LyricPreset | "";
  lyric_font?: string;
}

/** How a music video's lyrics are drawn (crcontent/styles.py LyricStyle). */
export interface LyricStyle {
  preset: LyricPreset;
  font: string; // "" = the preset's font for the song's language
  size: "s" | "m" | "l";
  position: "low" | "middle" | "high";
  color: string; // "#RRGGBB", words not sung yet
  highlight: string; // sung words
  effect: "karaoke" | "fill" | "pop" | "fade";
  outline: "outline" | "shadow" | "box" | "glow";
  case: "as_is" | "upper" | "lower";
}

export interface StyleCatalog {
  presets: Record<LyricPreset, LyricStyle & { label: string; font_km: string }>;
  looks: Record<Look, string>; // look -> label
  fonts: Record<Lang, string[]>; // installed font families per language
}

/** How many AI pictures a music video gets (crcontent/pipeline.py PICTURE_PACES): fewer = one per ~8 s, normal ~4.5 s, more ~3 s. */
export type PicturePace = "fewer" | "normal" | "more";

/** One planned picture of a music video (crcontent/pipeline.py song_slots + Claude's prompt). */
export interface SongArtSlot {
  section: string;
  lyrics: string; // what is sung while it's on screen
  start: number; // seconds into the song
  seconds: number; // on screen in all
  also: string[]; // repeated sections that show it again, e.g. "Chorus #2"
  prompt: string;
  motion: Motion;
  effects: Effect[];
  seed: number;
  frame?: "4:3"; // a home-video section: drawn landscape
  picture: MediaInfo | null; // already drawn (free to check before the render)
}

/** A song's picture plan; a music video with the same look, pace and idea uses it as it is. */
export interface SongArtPlan {
  style: ArtStyle;
  pictures: PicturePace;
  idea: string;
  aspect: Aspect;
  bible: string;
  slots: SongArtSlot[];
  direction_current?: boolean; // false: the shot list changed since these pictures were planned
}

/** Everything chosen for the next music video of a song. */
export interface MusicVideoSettings {
  idea: string;
  look: Look | "";
  lyric_style: LyricStyle | null; // null = the song's last style (or Classic)
  art_style?: ArtStyle | ""; // "" = stock footage; undefined = the song's last choice
  pictures?: PicturePace; // undefined = the song's last choice
  direction?: SongDirection | null; // the shot list for the idea; undefined = the song's
}

export interface VideoIdeaSuggestion {
  title: string;
  idea: string;
  look: Look;
  lyric_style: LyricPreset;
}

export interface Options {
  langs: Record<Lang, { name: string; voices: string[] }>;
  music: string[];
  music_use?: Record<string, MusicUse>; // each track's licence for monetized videos (missing on an older engine)
  keys: { anthropic: boolean; stock: "" | "pexels" | "pixabay"; elevenlabs: boolean; jamendo?: boolean };
  styles?: StyleCatalog; // missing on an older engine
  captions?: { presets: Record<string, Partial<CaptionStyle> & { label: string }> };
}

export type Aspect = "16:9" | "9:16";

export interface Job {
  id: string;
  kind?: "song" | "song_video" | "lyrics_sync" | "excel" | "publish" | "campaign_prepare" | "campaign_clips";
  status: "queued" | "running" | "done" | "error";
  step: number;
  log: string[];
  title: string;
  video?: string;
  error?: string;
  summary?: string; // excel: "5 of 6 videos made; failed: Ep 3"
  platform?: Platform; // publish
  url?: string; // publish: link to the uploaded video ("" for a TikTok draft)
  publish_at?: string; // publish: YouTube goes public at this time ("" when not scheduled)
  comment?: CommentState | null; // publish (youtube): how posting the video's comment went
  thumbnail?: ThumbnailState | null; // publish (youtube): how setting the cover as its thumbnail went
  channel_name?: string; // publish (youtube): the channel it went to
}

export type Platform = "youtube" | "tiktok" | "facebook" | "instagram";
export type TikTokPrivacy = "PUBLIC_TO_EVERYONE" | "MUTUAL_FOLLOW_FRIENDS" | "FOLLOWER_OF_CREATOR" | "SELF_ONLY";

/** The connected TikTok account and the visibilities TikTok lets it post with (publish.py tiktok_creator). */
export interface TikTokCreator {
  username: string;
  nickname: string;
  privacy_options: TikTokPrivacy[];
  max_seconds: number;
}

/** A connected channel/account and its upload settings (crcontent/publish.py status()). */
export interface PublishAccount {
  configured: boolean; // the developer app keys are saved
  client_id: string; // the saved client ID (TikTok: client key); the secret never comes back
  connected: boolean;
  account: string; // channel or display name
  connecting: boolean;
  auto: boolean; // upload every new render automatically
  privacy: string; // youtube: public | unlisted | private; tiktok: TikTokPrivacy
  mode?: "direct" | "draft"; // tiktok only
  when: "now" | "slots"; // auto-upload right after a render, or at the next free time in `times`
  times: string[]; // daily posting times, "HH:MM"
  comment?: boolean; // youtube: post the video's pinned comment (fact check) after upload
  can_comment?: boolean; // youtube: the connection allows posting comments (older ones need connecting again)
  category?: string; // youtube: default category id, or "auto" (Music for music videos, People & Blogs otherwise)
  channel?: string; // youtube: the default channel's id (the one `account` names)
  channels?: YouTubeChannel[]; // youtube: every connected channel (missing on an older engine)
  page?: string; // facebook: the default Page's id
  pages?: { id: string; name: string }[]; // facebook: every Page the Meta sign-in gave
  account_id?: string; // instagram: the default account's id
  accounts?: { id: string; name: string; page: string }[]; // instagram: the accounts linked to those Pages
  share_to_feed?: boolean; // instagram: Reels also show in the profile grid
  no_linked_account?: boolean; // instagram: signed in, but no Page has an Instagram professional account linked
}

/** A connected YouTube channel. */
export interface YouTubeChannel {
  id: string;
  name: string;
  can_comment: boolean;
}

/** A video's YouTube tags (its hashtags unless changed) and whether its cover becomes the thumbnail. */
export interface YouTubeOptions {
  tags: string[];
  custom_tags: boolean;
  thumbnail: "auto" | "cover" | "youtube"; // auto: the cover for videos, YouTube's frame for Shorts
  short: boolean;
  comment?: string; // posted under the video after upload ("" = none); missing on an older engine
  custom_comment?: boolean; // you wrote it (else: the automatic fact-check notes)
}

/** The video's YouTube comment: posted, waiting for a scheduled video to go public, skipped or failed. */
/** How setting the cover as the YouTube thumbnail went (publish.py youtube.thumbnail). */
export interface ThumbnailState {
  status: "set" | "error";
  at?: string;
  error?: string;
}

export interface CommentState {
  status: "posted" | "pending" | "skipped" | "error";
  at?: string;
  error?: string;
}

export type PublishAccounts = Record<Platform, PublishAccount> & {
  redirect_uri: Record<Platform, string>;
  youtube_categories?: Record<string, string>; // id -> name (missing on an older engine)
};

export type ServiceKey = "ANTHROPIC_API_KEY" | "ANTHROPIC_WORKSPACE_ID" | "PIXABAY_API_KEY" | "PEXELS_API_KEY" | "ELEVENLABS_API_KEY" | "JAMENDO_CLIENT_ID";

/** A free instrumental track on Jamendo (crcontent/music.py search()). */
export interface MusicResult {
  id: string;
  name: string;
  artist: string;
  duration: number;
  preview: string; // stream URL to listen before adding it
  image: string;
  license: string;
  commercial: boolean; // false: the licence is non-commercial only
  use?: MusicUse; // what the licence allows in a monetized video (missing on an older engine)
  tags: string[];
}
/** Whether each service key is set; `hint` shows only its last 4 characters. */
export type ServiceKeys = Record<ServiceKey, { set: boolean; hint: string }>;

/** An upload waiting in (or done from) the schedule (crcontent/schedule.py). Times are local, "2026-10-13T09:00". */
export interface ScheduledUpload {
  id: string;
  video: string;
  title: string;
  platform: Platform;
  at: string;
  privacy?: string; // tiktok: the visibility it posts with ("" = the setting at that time)
  status: "scheduled" | "uploading" | "done" | "error";
  source: "manual" | "auto";
  url: string;
  error: string;
  channel?: string; // youtube: the channel id ("" = the default channel)
  channel_name?: string; // youtube: that channel's name
}

/* ---------- Campaigns (Whop Content Rewards) ---------- */

export interface CampaignReference {
  id: string;
  title: string;
  url: string;
  file: string; // project path once downloaded or uploaded
  kind: "video" | "audio" | "image" | "document" | "link";
  status: "new" | "ready" | "manual" | "error"; // manual: download it yourself and add the file
  note: string;
  duration: number;
  transcribed: boolean;
}

export interface CampaignRequirements {
  min_seconds: number;
  max_seconds: number;
  hashtags: string[]; // without #
  mentions: string[]; // without @
  must_include: string[]; // phrases the caption must contain
  disclosure: string; // "#ad", "Paid partnership" or ""
  captions: boolean;
  rules: string[];
  avoid: string[];
}

export interface CampaignClip extends VideoSummary {
  post: string;
  duration: number;
  hook: string;
  why: string;
  reference: string;
  published: Partial<Record<Platform, Published>>;
  scheduled: ScheduledUpload[];
}

export interface Campaign {
  id: string;
  name: string;
  brand: string;
  url: string;
  kind: "clipping" | "ugc" | "other";
  platforms: string[];
  rate: string;
  budget: string;
  brief: string;
  lang: Lang;
  requirements: CampaignRequirements;
  references: CampaignReference[];
  created: string;
  updated: string;
  clips: CampaignClip[];
}

export interface CampaignSummary {
  id: string;
  name: string;
  brand: string;
  rate: string;
  platforms: string[];
  updated: string;
  references: number;
  clips: number;
  uploaded: number;
}

export interface Published {
  id: string;
  url: string;
  at: string;
  draft?: boolean;
  privacy?: string; // tiktok: the visibility it was posted with
  publish_at?: string; // youtube: scheduled to go public at this local time
  comment?: CommentState; // youtube: the video's fact-check comment
  thumbnail?: ThumbnailState; // youtube: the cover as its thumbnail
  channel?: string; // youtube: the channel it was uploaded to
  channel_name?: string;
}

export interface ExcelEpisode {
  ep: number;
  title: string;
  topic: string;
  status: string;
  scenes: number;
  posted: boolean;
}

export interface ExcelPlan {
  file: string; // uploaded copy on the engine, passed back to make drafts or videos
  name: string;
  episodes: ExcelEpisode[];
}

export interface VideoSummary {
  name: string;
  title: string;
  lang: Lang;
  created: string;
  kind: "video" | "song" | "music_video";
  source: "" | "upload"; // "upload" = your own song (mp3 + lyrics)
  aspect: Aspect;
  song_folder: string; // music video: the song it was made from ("" if that song was deleted)
  video: boolean;
  audio: boolean; // song.mp3 exists
  thumb: boolean;
  thumb_v: number; // changes when the thumbnail is redrawn (cache buster)
}

export interface VideoDetail extends VideoSummary {
  script: VideoScript | null;
  song: SongScript | null;
  stems: { vocals?: string; instrumental?: string }; // files inside the output folder
  versions: VideoSummary[]; // song: the music videos made from it, newest first
  idea: string; // song: the last video idea used; music video: the idea it was made with
  look?: Look | ""; // same, for the footage colour grade
  art_style?: ArtStyle | ""; // same, for the AI scene art ("" = stock footage)
  pictures?: PicturePace; // same, for how many AI pictures
  direction?: SongDirection | null; // songs: the shot list made from the idea
  lyric_style?: LyricStyle | null; // same, for the lyrics
  post: string;
  published?: Partial<Record<Platform, Published>>; // missing on an older engine
  youtube?: YouTubeOptions | null; // tags and thumbnail for YouTube uploads (null before rendering)
  duration: number; // seconds
  thumb_text: string; // headline last used for the thumbnail
  thumb_at: number; // seconds into the video of the thumbnail frame
  thumb_style: ThumbStyle;
  thumb_emphasis: string; // word(s) highlighted in the headline ("" = automatic)
  thumb_image?: string; // photo used instead of a video frame (project path), "" = a frame
  thumb_suggestions: ThumbSuggestions | null; // last "Suggest covers" result
}

/** One "Suggest titles" option: a ready-to-post title, description and hashtags (no # sign). */
export interface PostSuggestion {
  angle: string; // e.g. "Curiosity gap", "Emotional story"
  title: string;
  description: string;
  hashtags: string[];
}

export type ThumbStyle ="bold" | "box" | "stacked" | "designed"; // designed: a full layout Claude draws

export interface ThumbSuggestion {
  text: string;
  emphasis: string;
  style: ThumbStyle;
  at: number;
  image?: string; // stock photo used instead of a frame (project path), "" = the frame at `at`
  file: string; // preview image inside the video's output folder
  design?: string; // style "designed": its layout (svg in the output folder), used when you pick it
}

export interface ThumbSuggestions {
  items: ThumbSuggestion[];
  note: string; // set when Claude wasn't available and headlines came from the script
  idea?: string; // the cover idea they were made for
}

export interface StockResult {
  source: "pexels" | "pixabay";
  id: number;
  kind: "video" | "photo";
  thumb: string;
  duration?: number;
  author: string;
}

export interface MediaInfo {
  media: string;
  url: string;
  kind: "video" | "photo";
}

export interface DraftData {
  script: VideoScript;
  lang: Lang;
  topic: string;
  voice: string;
  rate: string;
  music: string;
}

export interface DraftSummary {
  kind: "script" | "song";
  id: string; // script: draft id; song: its output folder name
  title: string;
  lang: Lang;
  updated: string;
  scenes: number;
  cover: string; // first scene background (project path) or ""
  // songs only
  source?: "" | "upload";
  versions?: number; // music videos made from it
  thumb?: string; // output folder of the newest version with a thumbnail
  thumb_v?: number;
}

export interface TimedWord {
  text: string;
  start: number; // seconds into the song
  end: number;
}

export interface TimedLine {
  section: number; // index into song.sections
  text: string;
  words: TimedWord[];
  check?: boolean; // the automatic sync isn't sure about this line: worth checking by ear
}

export interface LyricsTiming {
  lines: TimedLine[] | null; // null = not timed yet
  timing: "" | "exact" | "whisper" | "even" | "edited"; // exact: from the song generator's own word timings
}

/** Where the library lives (crcontent/locations.py). */
export interface Locations {
  data: string;
  videos: string;
  videos_default: boolean; // videos go to <data>/output
  default_data: string;
  locked: boolean; // set by CRCONTENT_DATA_DIR, not changeable from the app
}

/** Running on a Mac: the desktop app starts "at login" from the menu bar instead of "with Windows" from the tray. */
export function isMac(): boolean {
  return typeof navigator !== "undefined" && /Mac/i.test(navigator.userAgent);
}

/** What the "start in the background" option is called on this OS. */
export function autostartLabel(): string {
  return isMac() ? "Open at Login" : "Start with Windows";
}

/** Desktop app only: does it start at sign-in (in the tray / menu bar)? undefined = not in the desktop app. */
export async function getAutostart(): Promise<boolean | undefined> {
  const tauri = typeof window !== "undefined" ? window.__TAURI_INTERNALS__ : undefined;
  return tauri ? tauri.invoke<boolean>("get_autostart") : undefined;
}

/** Desktop app only: start at sign-in (in the tray / menu bar) or not; returns the new state. */
export async function setAutostart(enabled: boolean): Promise<boolean | undefined> {
  const tauri = typeof window !== "undefined" ? window.__TAURI_INTERNALS__ : undefined;
  return tauri ? tauri.invoke<boolean>("set_autostart", { enabled }) : undefined;
}

/** A newer version of the desktop app on GitHub (src-tauri check_update). */
export interface AppUpdate {
  version: string;
  current: string;
  notes: string; // the release's description (Markdown)
  date: string;
}

function desktop() {
  return typeof window !== "undefined" ? window.__TAURI_INTERNALS__ : undefined;
}

/** Desktop app only: this app's version; undefined in the browser. */
export async function appVersion(): Promise<string | undefined> {
  return desktop()?.invoke<string>("app_version");
}

/** Desktop app only: the newer version on GitHub, null when this one is the latest, undefined in the browser. */
export async function checkUpdate(): Promise<AppUpdate | null | undefined> {
  return desktop()?.invoke<AppUpdate | null>("check_update");
}

/** Desktop app only: download and install the update found by checkUpdate, then restart (progress comes as
 *  `desktop-update` window events: { downloaded, total }). */
export async function installUpdate(): Promise<void> {
  await desktop()?.invoke("install_update");
}

/** Desktop app only: a native folder picker. null = cancelled, undefined = not in the desktop app. */
export async function pickFolder(title: string, start?: string): Promise<string | null | undefined> {
  const tauri = typeof window !== "undefined" ? window.__TAURI_INTERNALS__ : undefined;
  return tauri ? tauri.invoke<string | null>("pick_folder", { title, start: start ?? null }) : undefined;
}

export class ApiError extends Error {}

// Quick calls give up after this long, so a request lost while the engine restarts can't hang the UI.
// Claude, upload and render calls pass `timeout: 0` (no limit).
const TIMEOUT_MS = 15_000;

async function request<T>(path: string, init: RequestInit & { json?: unknown; timeout?: number } = {}): Promise<T> {
  const { json, timeout = TIMEOUT_MS, ...rest } = init;
  let res: Response;
  try {
    res = await fetch(API_BASE + path, {
      ...rest,
      headers: json !== undefined ? { "Content-Type": "application/json", ...rest.headers } : rest.headers,
      body: json !== undefined ? JSON.stringify(json) : rest.body,
      signal: timeout ? AbortSignal.timeout(timeout) : rest.signal,
    });
  } catch (e) {
    if ((e as Error).name === "TimeoutError") throw new ApiError("The video engine didn't answer in time. Try again.");
    throw new ApiError(desktopEngine
      ? "Can't reach the video engine. Restart the app; if it keeps happening, see engine.log in %APPDATA%\\com.crcontent.shorts-studio."
      : "Can't reach the video engine. Start it with: npm run dev (in frontend/), or python app.py");
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    // FastAPI validation errors (422) come as a list: name the wrong field instead of only the status
    const detail = Array.isArray(data.detail)
      ? data.detail.map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg}`).join("; ")
      : data.detail;
    throw new ApiError(typeof detail === "string" && detail ? detail : `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

/** URL for a project-relative file (uploads/..., cache/...) or an output folder file. */
export const fileUrl = (projectPath: string) =>
  `${API_BASE}/${projectPath.split("/").map(encodeURIComponent).join("/")}`;
export interface TopicIdea {
  format: string; // the hook style: "rank these", "myth vs fact", ...
  topic: string; // the angle, for the script writer
  hook: string; // the opening line, payoff first
}

export const outputUrl = (folder: string, file: string) =>
  `${API_BASE}/media/${encodeURIComponent(folder)}/${file}`;

export const api = {
  options: () => request<Options>("/api/options"),
  writeScript: (body: { topic: string; lang: Lang; scenes: number; seconds: number; style: string }) =>
    request<VideoScript>("/api/script", { method: "POST", json: body, timeout: 0 }),
  /** Ideas for the next Shorts in a mix of hook formats, none a near-repeat of the library's recent titles. */
  topicIdeas: (niche: string, lang: Lang) =>
    request<{ topics: TopicIdea[] }>("/api/topic-ideas", { method: "POST", json: { niche, lang }, timeout: 0 }),
  importScript: (text: string) =>
    request<{ script: VideoScript; lang: Lang; method: "claude" | "basic" }>("/api/import", { method: "POST", json: { text, lang: "auto" }, timeout: 0 }),
  translate: (script: VideoScript, target: Lang) =>
    request<VideoScript>("/api/translate", { method: "POST", json: { script, target }, timeout: 0 }),
  ideas: (narration: string, current: string) =>
    request<{ queries: string[] }>("/api/ideas", { method: "POST", json: { narration, current }, timeout: 0 }),
  footage: (q: string, kind: "video" | "photo") =>
    request<{ results: StockResult[] }>(`/api/footage?q=${encodeURIComponent(q)}&kind=${kind}`),
  designFootage: (prompt: string, narration: string, animate = false) =>
    request<MediaInfo>("/api/footage/design", { method: "POST", json: { prompt: prompt ?? "", narration: narration ?? "", animate: animate === true }, timeout: 0 }),
  pick: (r: StockResult) =>
    request<MediaInfo>("/api/footage/pick", { method: "POST", json: { source: r.source, kind: r.kind, id: r.id }, timeout: 0 }),
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<MediaInfo>("/api/upload", { method: "POST", body: form, timeout: 0 });
  },
  campaigns: () => request<CampaignSummary[]>("/api/campaigns"),
  campaign: (id: string) => request<Campaign>(`/api/campaigns/${id}`),
  readCampaign: (body: { text: string; url: string }) => request<Campaign>("/api/campaigns", { method: "POST", json: body, timeout: 0 }),
  editCampaign: (id: string, changes: Partial<Omit<Campaign, "id" | "clips" | "references">>) =>
    request<Campaign>(`/api/campaigns/${id}`, { method: "PUT", json: changes }),
  deleteCampaign: (id: string) => request<{ deleted: string }>(`/api/campaigns/${id}`, { method: "DELETE" }),
  addReference: (id: string, url: string, title = "") =>
    request<Campaign>(`/api/campaigns/${id}/references`, { method: "POST", json: { url, title } }),
  uploadReference: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Campaign>(`/api/campaigns/${id}/references/upload`, { method: "POST", body: form, timeout: 0 });
  },
  removeReference: (id: string, refId: string) => request<Campaign>(`/api/campaigns/${id}/references/${refId}`, { method: "DELETE" }),
  prepareCampaign: (id: string) => request<{ id: string }>(`/api/campaigns/${id}/prepare`, { method: "POST" }),
  makeClips: (id: string, body: { count: number; layout: "fill" | "crop"; idea: string }) =>
    request<{ id: string }>(`/api/campaigns/${id}/clips`, { method: "POST", json: body }),
  schedule: (video = "") => request<ScheduledUpload[]>(`/api/schedule${video ? `?video=${encodeURIComponent(video)}` : ""}`),
  /** `channel`: the YouTube channel id ("" = the default channel). */
  /** `tiktokPrivacy`: the visibility a TikTok upload posts with at that time ("" = the TikTok setting then). */
  scheduleVideo: (name: string, platforms: Platform[], at: string, channel = "", tiktokPrivacy: TikTokPrivacy | "" = "") =>
    request<ScheduledUpload[]>(`/api/videos/${encodeURIComponent(name)}/schedule`, {
      method: "POST",
      json: { platforms, at, channel, tiktok_privacy: tiktokPrivacy },
    }),
  scheduleCampaign: (id: string, platforms: Platform[]) =>
    request<{ scheduled: number; campaign: Campaign }>(`/api/campaigns/${id}/schedule`, { method: "POST", json: { platforms } }),
  cancelScheduled: (id: string) => request<{ cancelled: string }>(`/api/schedule/${id}`, { method: "DELETE" }),
  render: (body: { script: VideoScript; topic: string; lang: Lang; voice: string; rate: string; music: string; draft_id: string }) =>
    request<{ id: string }>("/api/render", { method: "POST", json: body, timeout: 0 }),
  writeSong: (body: { topic: string; lang: Lang; seconds: number; style: string; vocal: string }) =>
    request<SongScript>("/api/song/write", { method: "POST", json: body, timeout: 0 }),
  composeSong: (body: { song: SongScript; topic: string; lang: Lang; stems: boolean }) =>
    request<{ id: string }>("/api/song/compose", { method: "POST", json: body, timeout: 0 }),
  importSong: (body: { file: File; title: string; lyrics: string; lang: Lang; aspect: Aspect }) => {
    const form = new FormData();
    form.append("file", body.file);
    form.append("title", body.title);
    form.append("lyrics", body.lyrics);
    form.append("lang", body.lang);
    form.append("aspect", body.aspect);
    return request<{ id: string }>("/api/song/import", { method: "POST", body: form, timeout: 0 });
  },
  readExcel: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ExcelPlan>("/api/excel/read", { method: "POST", body: form, timeout: 0 });
  },
  excelDrafts: (file: string, eps: number[]) =>
    request<{ drafts: { ep: number; id: string; title: string }[] }>("/api/excel/drafts", { method: "POST", json: { file, eps }, timeout: 0 }),
  excelRender: (file: string, eps: number[]) =>
    request<{ id: string }>("/api/excel/render", { method: "POST", json: { file, eps }, timeout: 0 }),
  lyrics: (name: string) => request<LyricsTiming>(`/api/videos/${encodeURIComponent(name)}/lyrics`),
  saveLyrics: (name: string, lines: TimedLine[]) =>
    request<LyricsTiming>(`/api/videos/${encodeURIComponent(name)}/lyrics`, { method: "PUT", json: { lines } }),
  resyncLyrics: (name: string) =>
    request<{ id: string }>(`/api/videos/${encodeURIComponent(name)}/lyrics/sync`, { method: "POST", timeout: 0 }),
  musicVideo: (name: string, settings: MusicVideoSettings) =>
    request<{ id: string }>(`/api/videos/${encodeURIComponent(name)}/music-video`, { method: "POST", json: settings, timeout: 0 }),
  videoIdeas: (name: string) =>
    request<{ ideas: VideoIdeaSuggestion[] }>(`/api/videos/${encodeURIComponent(name)}/video-ideas`, { method: "POST", timeout: 0 }),
  drafts: () => request<DraftSummary[]>("/api/drafts"),
  draft: (id: string) => request<DraftData & { id: string }>(`/api/drafts/${encodeURIComponent(id)}`),
  createDraft: (d: DraftData) => request<{ id: string; updated: string }>("/api/drafts", { method: "POST", json: d }),
  saveDraft: (id: string, d: DraftData) =>
    request<{ id: string; updated: string }>(`/api/drafts/${encodeURIComponent(id)}`, { method: "PUT", json: d }),
  deleteDraft: (id: string) => request<unknown>(`/api/drafts/${encodeURIComponent(id)}`, { method: "DELETE" }),
  job: (id: string) => request<Job>(`/api/jobs/${id}`),
  videos: () => request<VideoSummary[]>("/api/videos"),
  video: (name: string) => request<VideoDetail>(`/api/videos/${encodeURIComponent(name)}`),
  makeThumbnail: (name: string, cover: { text: string; at: number; style: ThumbStyle; emphasis: string; image: string; design?: string }) =>
    // a designed cover may ask Claude for a new layout, which takes a minute or two
    request<VideoSummary>(`/api/videos/${encodeURIComponent(name)}/thumbnail`, { method: "POST", json: cover, timeout: cover.style === "designed" ? 0 : 60_000 }),
  suggestThumbnails: (name: string, idea = "") =>
    request<ThumbSuggestions>(`/api/videos/${encodeURIComponent(name)}/thumbnail/suggest`, { method: "POST", json: { idea }, timeout: 0 }),
  suggestPosts: (name: string, idea = "") =>
    request<{ items: PostSuggestion[] }>(`/api/videos/${encodeURIComponent(name)}/post/suggest`, { method: "POST", json: { idea }, timeout: 0 }),
  savePost: (name: string, post: Omit<PostSuggestion, "angle">) =>
    request<{ post: string }>(`/api/videos/${encodeURIComponent(name)}/post`, { method: "PUT", json: post }),
  serviceKeys: () => request<ServiceKeys>("/api/settings/keys"),
  locations: () => request<Locations>("/api/settings/locations"),
  // moving a big library to another drive takes a while: no time limit
  moveLocations: (data: string, videos: string) =>
    request<Locations & { left_behind: number; restarting: boolean }>("/api/settings/locations", { method: "PUT", json: { data, videos }, timeout: 0 }),
  openLocation: (which: "data" | "videos") => request<{ opened: string }>("/api/settings/locations/open", { method: "POST", json: { which } }),
  saveServiceKeys: (keys: Partial<Record<ServiceKey, string>>) => request<ServiceKeys>("/api/settings/keys", { method: "PUT", json: { keys } }),
  publishAccounts: () => request<PublishAccounts>("/api/publish/accounts"),
  connectPlatform: (platform: Platform) => request<{ url: string }>(`/api/publish/${platform}/connect`, { method: "POST" }),
  /** `channel`: disconnect only this YouTube channel (else every channel). */
  disconnectPlatform: (platform: Platform, channel = "") =>
    request<PublishAccounts>(`/api/publish/${platform}${channel ? `?channel=${encodeURIComponent(channel)}` : ""}`, { method: "DELETE" }),
  savePublishApp: (platform: Platform, keys: { client_id: string; client_secret: string }) =>
    request<PublishAccounts>(`/api/publish/${platform}/app`, { method: "PUT", json: keys }),
  publishSettings: (platform: Platform, settings: Partial<Pick<PublishAccount, "auto" | "privacy" | "mode" | "when" | "times" | "comment" | "category" | "channel" | "page" | "account_id" | "share_to_feed">>) =>
    request<PublishAccounts>(`/api/publish/${platform}/settings`, { method: "PUT", json: settings }),
  /** `youtube` overrides the channel's visibility for this upload; `publish_at` uploads it private and YouTube makes it public then.
   *  `facebook_publish_at`: the same for Facebook (a scheduled Reel or Page video). */
  publishVideo: (
    name: string,
    platforms: Platform[],
    options: {
      privacy?: string;
      publish_at?: string;
      category?: string;
      channel?: string;
      tiktok_privacy?: TikTokPrivacy | "DRAFT";
      facebook_publish_at?: string; // uploads now; Facebook publishes it at this local time (10 min to 28 days ahead)
    } = {},
  ) =>
    request<{ jobs: Partial<Record<Platform, string>> }>(`/api/videos/${encodeURIComponent(name)}/publish`, {
      method: "POST",
      json: { platforms, ...options },
    }),
  saveYouTubeOptions: (
    name: string,
    options: { tags?: string[]; reset_tags?: boolean; thumbnail?: YouTubeOptions["thumbnail"]; comment?: string; reset_comment?: boolean },
  ) =>
    request<YouTubeOptions>(`/api/videos/${encodeURIComponent(name)}/youtube`, { method: "PUT", json: options }),
  tiktokCreator: () => request<TikTokCreator>("/api/tiktok/creator"),
  /** Post the video's comment under its YouTube upload now. */
  postYouTubeComment: (name: string) => request<CommentState>(`/api/videos/${encodeURIComponent(name)}/youtube/comment`, { method: "POST", timeout: 60_000 }),
  /** Set the cover as the thumbnail of a video already on YouTube (after verifying the channel, say). */
  setYouTubeThumbnail: (name: string) => request<ThumbnailState>(`/api/videos/${encodeURIComponent(name)}/youtube/thumbnail`, { method: "POST", timeout: 90_000 }),
  artStatus: () => request<ArtStatus>("/api/art/status"),
  artProgressUrl: `${API_BASE}/api/art/progress`, // server-sent events: the status while a model downloads
  installAddon: () => request<AddonStatus>("/api/addon/install", { method: "POST" }),
  artDownload: (style: ArtStyle) => request<{ downloading: boolean }>(`/api/art/download/${style}`, { method: "POST" }),
  /** `score`: how well the picture shows the subject (0-10; null when it wasn't checked), `problem`: what's wrong. */
  artDraw: (body: { prompt: string; style: ArtStyle; seed?: number; aspect?: Aspect } & Partial<ArtSubject>) =>
    request<{ media: string; url: string; kind: "photo"; seed: number; score: number | null; problem: string }>("/api/art/draw", {
      method: "POST",
      json: body,
      timeout: 900_000, // up to 3 takes when the subject comes out wrong
    }),
  /** How well a drawn picture shows the video's real subject (null: it isn't meant to show it). */
  artCheck: (media: string, subject: string, prompt: string) =>
    request<{ score: number | null; problem: string }>("/api/art/check", { method: "POST", json: { media, subject, prompt }, timeout: 120_000 }),
  /** Real footage or a real photo of the subject (stock, else Wikimedia Commons), checked to really show it. */
  artReal: (subject: string, exclude: string[] = []) =>
    request<{ media: string; url: string; kind: "photo" | "video"; credit: string }>("/api/art/real", {
      method: "POST",
      json: { subject, exclude },
      timeout: 300_000,
    }),
  songArtPlan: (name: string) => request<{ plan: SongArtPlan | null }>(`/api/videos/${encodeURIComponent(name)}/art-plan`),
  directIdea: (name: string, idea: string) =>
    request<SongDirection>(`/api/videos/${encodeURIComponent(name)}/direct`, { method: "POST", json: { idea }, timeout: 180_000 }),
  saveDirection: (name: string, direction: SongDirection) =>
    request<SongDirection>(`/api/videos/${encodeURIComponent(name)}/direct`, { method: "PUT", json: direction }),
  planSongArt: (name: string, body: { style: ArtStyle; pictures: PicturePace; idea: string; bible?: string; direction?: SongDirection | null }) =>
    request<{ plan: SongArtPlan }>(`/api/videos/${encodeURIComponent(name)}/art-plan`, { method: "POST", json: body, timeout: 300_000 }),
  saveSongArtPlan: (name: string, body: { bible?: string; slots: Pick<SongArtSlot, "prompt" | "motion" | "effects" | "seed">[] }) =>
    request<{ plan: SongArtPlan }>(`/api/videos/${encodeURIComponent(name)}/art-plan`, { method: "PUT", json: body }),
  /** A few seconds of a drawn picture with its camera move and effects. */
  previewShot: (body: { media: string; style: ArtStyle; motion: Motion; effects: Effect[]; aspect: Aspect; look?: string }) =>
    request<MediaInfo>("/api/art/preview-shot", { method: "POST", json: body, timeout: 300_000 }),
  artPlan: (script: VideoScript, replace = false) => request<VideoScript>("/api/art/plan", { method: "POST", json: { script, replace }, timeout: 180_000 }),
  deleteVideo: (name: string) => request<unknown>(`/api/videos/${encodeURIComponent(name)}`, { method: "DELETE" }),
  /** Returns an mp3 blob for the voice preview. */
  /** Each scene's voiceover with word timings (null for silent scenes); `pad` = silence after each scene. */
  voiceover: (scenes: string[], voice: string, rate: string) =>
    request<{ pad: number; scenes: (SceneVoice | null)[] }>("/api/voiceover", { method: "POST", json: { scenes, voice, rate }, timeout: 120_000 }),
  voiceoverUrl: (key: string) => `${API_BASE}/api/voiceover/${key}.mp3`,
  /** The voiceover's loudness: `rate` values per second, 0-1. */
  voiceoverPeaks: (key: string) => request<{ rate: number; peaks: number[] }>(`/api/voiceover/${key}/peaks`),
  /** A strip of `frames` frames across a clip (project path of one image) and the clip's length (0 for a photo). */
  filmstrip: (path: string) => request<{ duration: number; frames: number; sprite: string }>(`/api/filmstrip?path=${encodeURIComponent(path)}`, { timeout: 60_000 }),
  /** The clips the render will pick for scenes with automatic footage (project paths; null = none found). */
  /** `hook`: the first query is the video's opening scene (the engine picks the brightest, liveliest clip for it). */
  autoFootage: (queries: string[], hook = false) =>
    request<{ media: (string | null)[] }>("/api/footage/auto", { method: "POST", json: { queries, hook }, timeout: 180_000 }),
  musicSearch: (q: string) => request<{ results: MusicResult[] }>(`/api/music/search?q=${encodeURIComponent(q)}`),
  /** Download a Jamendo track into the music library; returns its file name (as listed in options.music). */
  musicPick: (id: string) => request<{ file: string; credit: string }>("/api/music/pick", { method: "POST", json: { id }, timeout: 120_000 }),
  speak: async (text: string, voice: string, rate: string): Promise<Blob> => {
    let res: Response;
    try {
      res = await fetch(`${API_BASE}/api/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voice, rate }),
      });
    } catch {
      throw new ApiError("Can't reach the video engine.");
    }
    if (!res.ok) throw new ApiError((await res.json().catch(() => ({}))).detail ?? `Preview failed (${res.status})`);
    return res.blob();
  },
};
