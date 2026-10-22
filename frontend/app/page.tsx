"use client";

import { CircleAlert } from "lucide-react";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type CSSProperties,
} from "react";
import {
  API_BASE,
  api,
  outputUrl,
  type Aspect,
  type DraftSummary,
  type Job,
  type Lang,
  type MusicVideoSettings,
  type Options,
  type SongScript,
  type VideoDetail,
  type VideoSummary,
} from "@/lib/api";
import { CreateForm } from "@/components/CreateForm";
import { Library, type LibraryTab } from "@/components/Library";
import {
  ExportCards,
  PreviewPane,
  settingsOf,
  type PreviewView,
} from "@/components/PreviewPane";
import { LyricsTiming } from "@/components/LyricsTiming";
import { NavRail, type AppView } from "@/components/NavRail";
import { Settings } from "@/components/Settings";
import { Campaigns } from "@/components/Campaigns";
import { SongEditor } from "@/components/SongEditor";
import {
  Storyboard,
  draftVoice,
  toDraft,
  toDraftData,
  type Draft,
  type SaveState,
} from "@/components/Storyboard";
import { TopBar } from "@/components/TopBar";
import { UpdateNotice } from "@/components/UpdateNotice";
import { Button, Drawer, ResizeHandle, ToastProvider, useToast } from "@/components/ui";
import { usePaneWidth } from "@/lib/appearance";
import { DraftHistory } from "@/lib/draftHistory";
import { useDraftTimeline } from "@/lib/useDraftTimeline";

const AUTOSAVE_MS = 800;

/** Retry a few times: the engine may be (re)starting when the page loads. */
async function withRetry<T>(fn: () => Promise<T>, tries = 4): Promise<T> {
  for (let i = 1; ; i++) {
    try {
      return await fn();
    } catch (e) {
      if (i >= tries) throw e;
      await new Promise((r) => setTimeout(r, 1000 * Math.min(i, 3)));
    }
  }
}

export default function Page() {
  return (
    <ToastProvider>
      <Studio />
    </ToastProvider>
  );
}

function Studio() {
  const toast = useToast();
  const [options, setOptions] = useState<Options | null>(null);
  const [engineError, setEngineError] = useState("");
  const [videos, setVideos] = useState<VideoSummary[] | null>(null);
  const [drafts, setDrafts] = useState<DraftSummary[] | null>(null);
  const [libraryTab, setLibraryTab] = useState<LibraryTab>("drafts");
  const [draft, setDraftState] = useState<Draft | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [activeUid, setActiveUid] = useState<string | null>(null);
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null);
  const [detail, setDetail] = useState<VideoDetail | null>(null);
  const [previewView, setPreviewView] = useState<PreviewView>("scene");
  const [job, setJob] = useState<Job | null>(null);
  const [jobTitle, setJobTitle] = useState("");
  const [libraryOpen, setLibraryOpen] = useState(false); // slide-over below laptop width
  const [libraryHidden, setLibraryHidden] = useState(false); // collapsed from the rail at laptop width and up
  // the draft editor uses the whole width: its library column only shows when opened from the rail
  const [libraryInEditor, setLibraryInEditor] = useState(false);
  // the library and preview panes can be dragged wider or narrower; the widths are remembered
  const libraryPane = usePaneWidth("library", 288, 240, 440);
  const previewPane = usePaneWidth("preview", 340, 300, 560);
  const [view, setView] = useState<AppView>("studio");
  const [previewOpen, setPreviewOpen] = useState(false);
  // Song being edited (not autosaved; composing writes song.json into its output folder)
  const [song, setSongState] = useState<{
    song: SongScript;
    lang: Lang;
    topic: string;
  } | null>(null);
  const setSong = useCallback(
    (update: (s: SongScript) => SongScript) =>
      setSongState((cur) => (cur ? { ...cur, song: update(cur.song) } : cur)),
    [],
  );
  // Song whose lyric timing is open in the editor (its output folder); the version remounts it after a re-sync.
  // It keeps its own copy of the song's details so the preview can show a rendered version meanwhile.
  const [timing, setTiming] = useState<{
    name: string;
    version: number;
    title: string;
    lang: Lang;
    aspect: Aspect;
    sections: string[];
    settings: MusicVideoSettings;
  } | null>(null);
  const poll = useRef<ReturnType<typeof setTimeout> | null>(null);

  // the open draft as a playable timeline, shared by the transcript editor and the live preview
  const { voice: draftVoiceName, rate: draftRate } =
    draft && options ? draftVoice(draft, options) : { voice: "", rate: "" };
  const timeline = useDraftTimeline(
    draft?.scenes ?? null,
    draftVoiceName,
    draftRate,
  );
  // while it plays, the scene being played is the one highlighted in the storyboard
  const playheadUid = timeline.playing
    ? (draft?.scenes[timeline.pos.i]?.uid ?? null)
    : null;
  useEffect(() => {
    if (playheadUid) setActiveUid(playheadUid);
  }, [playheadUid]);

  // Autosave bookkeeping. Saves run one after another so a burst of edits can't create duplicate drafts.
  const draftId = useRef<string | null>(null);
  const lastSaved = useRef<string>(""); // serialized content last written to disk
  const saveQueue = useRef<Promise<void>>(Promise.resolve());
  const currentDraft = useRef<Draft | null>(null);
  useEffect(() => {
    currentDraft.current = draft;
  }, [draft]);

  // undo/redo of draft edits (saving the new id after a first save isn't an edit, so it goes around this)
  const [history] = useState(() => new DraftHistory<Draft>());
  const historyFlags = useSyncExternalStore(
    history.subscribe,
    history.flags,
    () => "00",
  );
  const setDraft = useCallback(
    (update: (d: Draft) => Draft) =>
      setDraftState((d) => {
        if (!d) return d;
        const next = update(d);
        if (next !== d) history.record(d);
        return next;
      }),
    [history],
  );
  const step = useCallback(
    (dir: "undo" | "redo") => {
      const cur = currentDraft.current;
      const to =
        cur && (dir === "undo" ? history.undo(cur) : history.redo(cur));
      if (cur && to) setDraftState({ ...to, id: cur.id });
    },
    [history],
  );
  // Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y, except in text fields, which undo their own typing
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey) || !currentDraft.current) return;
      const el = e.target as HTMLElement | null;
      if (
        el &&
        (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName))
      )
        return;
      const key = e.key.toLowerCase();
      if (key === "z" || key === "y") {
        e.preventDefault();
        step(key === "y" || e.shiftKey ? "redo" : "undo");
      }
    };
    window.addEventListener("keydown", onKey);
    // a drag (caption, text, timeline) is one step however many edits it made
    const seal = () => history.seal();
    window.addEventListener("pointerup", seal);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerup", seal);
    };
  }, [step, history]);

  const loadVideos = useCallback(async () => {
    try {
      setVideos(await withRetry(api.videos));
    } catch {
      setVideos([]);
    }
  }, []);
  const loadDrafts = useCallback(async () => {
    try {
      const apiDrafts = await withRetry(api.drafts);
      setDrafts(apiDrafts);
    } catch {
      setDrafts([]);
    }
  }, []);

  // after keys change in Settings: the "connected" checks in the editors read these
  const reloadOptions = useCallback(() => {
    api
      .options()
      .then(setOptions)
      .catch(() => {});
  }, []);

  useEffect(() => {
    // The engine may still be starting (the desktop app launches it alongside the window), so wait for it first.
    withRetry(api.options, 12)
      .then((o) => {
        setOptions(o);
        void loadVideos();
        void loadDrafts();
      })
      .catch((e: Error) => {
        setEngineError(e.message);
        setVideos([]);
        setDrafts([]);
      });
    return () => {
      if (poll.current) clearTimeout(poll.current);
    };
  }, [loadVideos, loadDrafts]);

  // The storyboard page (an iframe from the engine) started its render: show its progress here too.
  // No deps: re-subscribed each render so it always calls the current watch().
  useEffect(() => {
    const onMessage = (e: MessageEvent) => {
      if (e.origin !== new URL(API_BASE).origin || e.data?.type !== "storyboard-render") return;
      const { id, job: name, kind } = e.data as { id: string; job: string; kind?: "short" };
      const title = videos?.find((v) => v.name === name)?.title ?? name;
      setJobTitle(title);
      setJob({ id, kind: kind ?? "long_video", status: "queued", step: 5, log: [], title });
      setPreviewOpen(true);
      watch(id);
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  });

  // Desktop app: the native "Save as" dialog reports how each download went.
  useEffect(() => {
    const onDownload = (e: Event) => {
      const { success, name } = (
        e as CustomEvent<{ success: boolean; name: string | null }>
      ).detail;
      if (success) toast(name ? `Saved ${name}` : "Download saved", "success");
      else toast("Download failed. Try again.", "error");
    };
    window.addEventListener("desktop-download", onDownload);
    return () => window.removeEventListener("desktop-download", onDownload);
  }, [toast]);

  /** Queue a save of `body`. Runs after earlier saves so ids are never created twice. */
  const enqueueSave = useCallback(
    (body: string) => {
      const forId = draftId.current;
      saveQueue.current = saveQueue.current.then(async () => {
        if (body === lastSaved.current || draftId.current !== forId) return; // unchanged, or user switched drafts
        setSaveState("saving");
        try {
          const data = JSON.parse(body);
          if (forId) {
            await api.saveDraft(forId, data);
          } else {
            const { id } = await api.createDraft(data);
            draftId.current = id;
            setDraftState((d) => (d && d.id === null ? { ...d, id } : d));
          }
          lastSaved.current = body;
          setSaveState("saved");
          void loadDrafts();
        } catch {
          setSaveState("error");
        }
      });
      return saveQueue.current;
    },
    [loadDrafts],
  );

  /** Save pending edits right away (before leaving the current draft). */
  const flush = useCallback(() => {
    const d = currentDraft.current;
    if (!d) return Promise.resolve();
    const body = JSON.stringify(toDraftData(d));
    return body === lastSaved.current ? saveQueue.current : enqueueSave(body);
  }, [enqueueSave]);

  // Autosave: write the draft to drafts/<id>/draft.json shortly after each change.
  useEffect(() => {
    if (!draft) return;
    const body = JSON.stringify(toDraftData(draft));
    if (body === lastSaved.current) return;
    const timer = setTimeout(() => enqueueSave(body), AUTOSAVE_MS);
    return () => clearTimeout(timer);
  }, [draft, enqueueSave]);

  /** Put a draft in the editor (saving the previous one first). `persisted` = this content is already on disk. */
  const openDraft = useCallback(
    async (d: Draft, persisted: boolean) => {
      await flush();
      draftId.current = d.id;
      lastSaved.current = persisted ? JSON.stringify(toDraftData(d)) : "";
      setSaveState("idle");
      setActiveUid(d.scenes[0]?.uid ?? null);
      history.reset();
      setDraftState(d);
      setLibraryOpen(false);
    },
    [flush, history],
  );

  const closeDraft = useCallback(async () => {
    await flush();
    draftId.current = null;
    history.reset();
    setDraftState(null);
    setActiveUid(null);
  }, [flush, history]);

  /** Open a song's lyric timing editor; `reload` remounts it with fresh timing (after a sync). */
  async function openTiming(name: string, reload = false) {
    const d = await api.video(name);
    await closeDraft();
    setSongState(null);
    setTiming((t) => ({
      name,
      version: t?.name === name ? t.version + (reload ? 1 : 0) : 0,
      title: d.title,
      lang: d.lang,
      aspect: d.aspect,
      sections: d.song?.sections.map((s) => s.name) ?? [],
      settings: settingsOf(d),
    }));
    return d;
  }

  async function selectVideo(name: string | null, openScript: boolean) {
    setSelectedVideo(name);
    if (!name) {
      setDetail(null);
      return;
    }
    try {
      const d = await api.video(name);
      setDetail(d);
      setPreviewView("video");
      // Editing a rendered video's script starts a new draft on the first change; the video stays as it is.
      if (openScript && d.script) {
        setSongState(null);
        await openDraft(toDraft(d.script, d.lang, ""), true);
      }
      // Your own song opens in the lyric timing editor; a composed song in the song editor (composing again
      // makes a new output folder). A music video keeps whatever is open: its song is one click away.
      const isSong = d.kind === "song" && !!d.song;
      if (openScript && isSong && d.source === "upload") {
        await openTiming(d.name);
      } else if (openScript && d.kind !== "music_video") {
        setTiming(null);
      }
      // a long video's storyboard opens in the middle, in place of whatever was being edited
      if (openScript && (d.kind === "long_video" || d.kind === "short")) {
        setSongState(null);
        await closeDraft();
      }
      if (openScript && d.song && d.kind === "song" && d.source !== "upload") {
        await closeDraft();
        setSongState({ song: d.song, lang: d.lang, topic: "" });
      }
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  async function selectDraft(id: string) {
    try {
      const d = await api.draft(id);
      setSongState(null);
      setTiming(null);
      await openDraft(
        toDraft(d.script, d.lang, d.topic, {
          id,
          voice: d.voice,
          rate: d.rate,
          music: d.music,
        }),
        true,
      );
      setSelectedVideo(null);
      setDetail(null);
      setPreviewView("scene");
    } catch (e) {
      toast((e as Error).message, "error");
      void loadDrafts();
    }
  }

  /** Deletes a script draft: the open one by default, or any draft from the library. */
  async function deleteDraft(id = draftId.current) {
    if (!id) return;
    const open = id === draftId.current;
    if (open) await saveQueue.current; // let any in-flight save finish first
    try {
      await api.deleteDraft(id);
      toast("Draft deleted");
    } catch (e) {
      toast((e as Error).message, "error");
      if (!open) return;
    }
    if (open) {
      draftId.current = null;
      lastSaved.current = "";
      setDraftState(null);
    }
    void loadDrafts();
  }

  /** Copies a script draft (with its latest edits, if it's open) and opens the copy. */
  async function duplicateDraft(id: string) {
    try {
      if (id === draftId.current) await flush();
      const d = await api.draft(id);
      const { id: copy } = await api.createDraft({
        script: {
          ...d.script,
          title: `${d.script.title || "Untitled draft"} (copy)`,
        },
        lang: d.lang,
        topic: d.topic,
        voice: d.voice,
        rate: d.rate,
        music: d.music,
      });
      await loadDrafts();
      setView("studio");
      await selectDraft(copy);
      toast("Draft duplicated", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  /** Deletes a rendered video or a song (a song's music videos stay in Videos). */
  async function deleteVideo(name: string, isSong = detail?.kind === "song") {
    try {
      await api.deleteVideo(name);
    } catch (e) {
      toast((e as Error).message, "error");
      return;
    }
    toast(
      isSong
        ? "Song deleted. Its music videos are still in Videos."
        : "Video deleted",
    );
    if (timing?.name === name) setTiming(null);
    if (isSong && detail?.name === name) setSongState(null);
    if (selectedVideo === name || detail?.name === name)
      await selectVideo(null, false);
    await Promise.all([loadVideos(), loadDrafts()]);
  }

  function watch(id: string) {
    const tick = async () => {
      try {
        const j = await api.job(id);
        setJob(j);
        if (j.status === "done") {
          toast(
            j.kind === "song"
              ? "Song ready. Make a music video from it, or edit the lyrics and compose again."
              : j.kind === "song_video"
                ? "Music video ready."
                : j.kind === "excel"
                  ? `${j.summary ?? "Videos ready"}. They're in Videos; each episode is also a draft.`
                  : j.kind === "lyrics_sync"
                    ? "Lyrics synced. Play the song to check the timing, then make the music video."
                    : j.kind === "long_video" && j.step < 7 // steps 1-5 make the storyboard, 6-7 render it
                      ? "Storyboard ready. Check every scene, swap what's wrong, then approve it to render."
                      : j.kind === "long_video"
                        ? "Long video ready. The chapters, captions and credits are in its folder."
                      : j.kind === "short" && j.step < 7 // steps 1-5 make the pre-flight report, 6-7 render it
                        ? `${j.summary ?? "Pre-flight report ready"}. Check the hook score and the storyboard, then approve it to render.`
                      : j.kind === "short"
                        ? "Short ready. Its cover, metadata and pinned comment are in its folder."
                      : "Video ready. Your draft is still saved, so you can render another version.",
            "success",
          );
          await Promise.all([loadVideos(), loadDrafts()]);
          await selectVideo(j.video ?? null, false);
          if (j.kind === "lyrics_sync" && j.video) {
            await openTiming(j.video, true);
            setLibraryTab("drafts");
            setJob(null);
          }
          return;
        }
        if (j.status === "error") {
          toast(
            `${j.kind === "song" ? "Composing" : j.kind === "lyrics_sync" ? "Lyric sync" : "Rendering"} failed: ${j.error ?? "unknown error"}`,
            "error",
          );
          if (j.kind === "lyrics_sync" && j.video) {
            // the song was saved; open it so the timing can be fixed by hand or synced again
            await Promise.all([loadVideos(), loadDrafts()]);
            await selectVideo(j.video, false);
            await openTiming(j.video, true);
          }
          // keep the song editor/preview usable after a failed music-video render
          if (j.kind === "song_video") setJob(null);
          return;
        }
      } catch (e) {
        setJob((j) =>
          j ? { ...j, status: "error", error: (e as Error).message } : j,
        );
        return;
      }
      poll.current = setTimeout(tick, 1000);
    };
    void tick();
  }

  async function startNew() {
    setView("studio");
    await closeDraft();
    setSongState(null);
    setTiming(null);
    void selectVideo(null, false);
    setLibraryOpen(false);
  }

  const rendering =
    job !== null && (job.status === "queued" || job.status === "running");
  const activeIndex = draft
    ? Math.max(
        0,
        draft.scenes.findIndex((s) => s.uid === activeUid),
      )
    : 0;
  const activeScene = draft ? (draft.scenes[activeIndex] ?? null) : null;
  // The lyric timing editor has its own player, monitor and music video options: the preview pane would only repeat
  // them (and play the song a second time), so it shows only while a job is running or has failed.
  const timingOpen = !draft && !song && !!timing;
  const hasPreview = timingOpen
    ? rendering || job?.status === "error"
    : !!draft ||
      !!song ||
      rendering ||
      job?.status === "error" ||
      !!detail?.video ||
      !!detail?.audio;
  // Script to Video: its storyboard (the engine's page, where footage is swapped and the render approved) fills the middle
  // Shorts Mode: its pre-flight report (the engine's page, where the render is approved) fills the middle the same way
  const storyboard =
    !draft && !song && !timing && (detail?.kind === "long_video" || detail?.kind === "short") ? detail : null;

  const library = (
    <Library
      tab={libraryTab}
      onTab={setLibraryTab}
      drafts={drafts}
      videos={videos}
      selectedDraft={
        draft?.id ??
        timing?.name ??
        (detail?.kind === "song" ? detail.name : null)
      }
      selectedVideo={selectedVideo}
      onSelectDraft={(id) => {
        setView("studio");
        void selectDraft(id);
      }}
      onSelectSong={(name) => {
        setView("studio");
        setLibraryOpen(false);
        void selectVideo(name, true);
      }}
      onSelectVideo={(name) => {
        setView("studio");
        setLibraryOpen(false);
        void selectVideo(name, true);
      }}
      onDuplicateDraft={(id) => void duplicateDraft(id)}
      onDeleteDraft={(id) => void deleteDraft(id)}
      onDeleteVideo={(name, isSong) => void deleteVideo(name, isSong)}
      onNew={startNew}
    />
  );

  const editing = !!draft && !!options && view === "studio";
  const sidePreview = hasPreview && !editing; // the draft editor has its own player in the middle
  const showLibrary = editing ? libraryInEditor : !libraryHidden;
  const renderPreview = (variant: "full" | "stage") => (
    <PreviewPane
      variant={variant}
      live={
        draft
          ? {
              timeline,
              music: draft.music || (options?.music.length ? "" : "none"),
              options,
              edit: {
                captions: draft.captions,
                setCaptions: (patch) =>
                  setDraft((d) => ({
                    ...d,
                    captions: { ...d.captions, ...patch },
                  })),
                patchScene: (uid, patch) =>
                  setDraft((d) => ({
                    ...d,
                    scenes: d.scenes.map((s) =>
                      s.uid === uid ? { ...s, ...patch(s) } : s,
                    ),
                  })),
              },
            }
          : null
      }
      scene={activeScene}
      sceneIndex={activeIndex}
      sceneCount={draft?.scenes.length ?? 0}
      lang={draft?.lang ?? "en"}
      rendering={rendering}
      job={job}
      jobTitle={jobTitle}
      detail={detail}
      view={previewView}
      onView={setPreviewView}
      onThumbnail={(summary) => {
        setDetail((d) =>
          d && d.name === summary.name ? { ...d, ...summary } : d,
        );
        setVideos(
          (vs) => vs?.map((v) => (v.name === summary.name ? summary : v)) ?? vs,
        );
      }}
      onOpenTiming={async (name) => {
        try {
          await openTiming(name);
          setPreviewOpen(false);
        } catch (e) {
          toast((e as Error).message, "error");
        }
      }}
      onSelectVideo={(name) => void selectVideo(name, false)}
      onVideosChanged={loadVideos}
      onOpenSettings={() => {
        setPreviewOpen(false);
        setView("settings");
      }}
      onMakeMusicVideo={async (name, settings) => {
        try {
          const { id } = await api.musicVideo(name, settings);
          setJobTitle(detail?.title ?? name);
          setJob({
            id,
            kind: "song_video",
            status: "queued",
            step: 0,
            log: [],
            title: detail?.title ?? name,
          });
          setPreviewOpen(true);
          watch(id);
        } catch (e) {
          toast((e as Error).message, "error");
        }
      }}
      onDeleteVideo={deleteVideo}
    />
  );
  const preview = renderPreview("full");
  // the rendered video's export cards, in the draft editor's inspector
  const exportDetail =
    detail?.video && detail.kind !== "song" && detail.kind !== "music_video"
      ? detail
      : null;

  return (
    <div className="flex h-dvh overflow-hidden">
      <UpdateNotice />
      <div className="hidden shrink-0 lg:block">
        <NavRail
          view={view}
          libraryOpen={showLibrary}
          options={options}
          onNew={startNew}
          onLibrary={() => {
            if (view === "settings") {
              setView("studio");
              setLibraryHidden(false);
            } else if (editing) setLibraryInEditor((open) => !open);
            else setLibraryHidden((h) => !h);
          }}
          onSettings={() =>
            setView((v) => (v === "settings" ? "studio" : "settings"))
          }
          onCampaigns={() =>
            setView((v) => (v === "campaigns" ? "studio" : "campaigns"))
          }
          onPreview={
            view === "studio" && sidePreview
              ? () => setPreviewOpen(true)
              : undefined
          }
        />
      </div>
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          onOpenLibrary={() => setLibraryOpen(true)}
          onOpenSettings={() =>
            setView((v) => (v === "settings" ? "studio" : "settings"))
          }
          onOpenCampaigns={() =>
            setView((v) => (v === "campaigns" ? "studio" : "campaigns"))
          }
          onOpenPreview={() => setPreviewOpen(true)}
          showPreviewButton={view === "studio" && sidePreview}
          setupNeeded={
            !!options && (!options.keys.anthropic || !options.keys.stock)
          }
        />

        {engineError && (
          <div
            role="alert"
            className="flex items-center gap-2 border-b border-danger/30 bg-danger/[0.07] px-4 py-2.5 text-base text-danger"
          >
            <CircleAlert className="size-4 shrink-0" />
            {engineError}
          </div>
        )}

        {view === "campaigns" && (
          <div className="min-h-0 flex-1">
            <Campaigns
              claudeReady={!!options?.keys.anthropic}
              onVideosChanged={() => void loadVideos()}
              onOpenSettings={() => setView("settings")}
              onOpenVideo={(name) => {
                setView("studio");
                setLibraryTab("videos");
                setLibraryHidden(false);
                void selectVideo(name, true);
              }}
            />
          </div>
        )}
        {view === "settings" && (
          <main className="min-h-0 flex-1 bg-paper">
            <Settings onKeysChanged={reloadOptions} />
          </main>
        )}
        <div
          hidden={view !== "studio"}
          style={
            {
              "--lib-w": `${libraryPane.width}px`,
              "--prev-w": `${previewPane.width}px`,
            } as CSSProperties
          }
          className={`grid min-h-0 flex-1 grid-cols-1 ${
            !showLibrary
              ? sidePreview
                ? "wide:grid-cols-[minmax(0,1fr)_var(--prev-w)]"
                : ""
              : `lg:grid-cols-[var(--lib-w)_minmax(0,1fr)] ${sidePreview ? "wide:grid-cols-[var(--lib-w)_minmax(0,1fr)_var(--prev-w)]" : ""}`
          }`}
        >
          {showLibrary && (
            <aside
              aria-label="Library"
              className="relative hidden min-h-0 border-r border-line bg-paper lg:block"
            >
              {library}
              <ResizeHandle
                edge="right"
                label="Resize library"
                width={libraryPane.width}
                min={240}
                max={440}
                onResize={libraryPane.setWidth}
                onReset={libraryPane.reset}
              />
            </aside>
          )}

          <main className="min-h-0 min-w-0">
            {!draft && !song && timing && (
              <LyricsTiming
                key={`${timing.name}-${timing.version}`}
                name={timing.name}
                title={timing.title}
                lang={timing.lang}
                aspect={timing.aspect}
                sections={timing.sections}
                settings={timing.settings}
                busy={rendering}
                onBack={() => setTiming(null)}
                onDelete={() => void deleteVideo(timing.name, true)}
                onResync={async () => {
                  try {
                    const { id } = await api.resyncLyrics(timing.name);
                    setJobTitle(timing.title);
                    setJob({
                      id,
                      kind: "lyrics_sync",
                      status: "queued",
                      step: 0,
                      log: [],
                      title: timing.title,
                    });
                    setPreviewOpen(true);
                    watch(id);
                    return null;
                  } catch (e) {
                    return (e as Error).message;
                  }
                }}
                onMakeVideo={async (settings) => {
                  try {
                    const { id } = await api.musicVideo(timing.name, settings);
                    setTiming((t) => (t ? { ...t, settings } : t));
                    setJobTitle(timing.title);
                    setJob({
                      id,
                      kind: "song_video",
                      status: "queued",
                      step: 0,
                      log: [],
                      title: timing.title,
                    });
                    setPreviewOpen(true);
                    watch(id);
                    return null;
                  } catch (e) {
                    return (e as Error).message;
                  }
                }}
              />
            )}
            {!draft && song && options && (
              <SongEditor
                song={song.song}
                setSong={setSong}
                lang={song.lang}
                options={options}
                composing={rendering && job?.kind === "song"}
                onBack={() => setSongState(null)}
                onDelete={
                  detail?.kind === "song"
                    ? () => void deleteVideo(detail.name, true)
                    : null
                }
                onCompose={async (stems) => {
                  try {
                    const { id } = await api.composeSong({
                      song: song.song,
                      topic: song.topic,
                      lang: song.lang,
                      stems,
                    });
                    setSelectedVideo(null);
                    setJobTitle(song.song.title);
                    setJob({
                      id,
                      kind: "song",
                      status: "queued",
                      step: 0,
                      log: [],
                      title: song.song.title,
                    });
                    setPreviewOpen(true);
                    watch(id);
                    return null;
                  } catch (e) {
                    return (e as Error).message;
                  }
                }}
              />
            )}
            {storyboard && (
              <div className="flex h-full min-h-0 flex-col">
                <div className="pane-header px-5">
                  <h2 className="pane-title m-0 truncate">{storyboard.title}</h2>
                  <Button variant="ghost" size="sm" onClick={() => void selectVideo(null, false)}>
                    Close
                  </Button>
                </div>
                <iframe
                  key={`${storyboard.name}-${storyboard.video}`}
                  title={`${storyboard.kind === "short" ? "Pre-flight" : "Storyboard"}: ${storyboard.title}`}
                  src={outputUrl(storyboard.name, storyboard.kind === "short" ? "preflight.html" : "storyboard.html")}
                  className="min-h-0 w-full flex-1 border-0 bg-paper"
                />
              </div>
            )}
            {!draft && !song && !timing && !storyboard && (
              <CreateForm
                options={options}
                onImportSong={(id, title) => {
                  setSelectedVideo(null);
                  setDetail(null);
                  setJobTitle(title);
                  setJob({
                    id,
                    kind: "lyrics_sync",
                    status: "queued",
                    step: 0,
                    log: [],
                    title,
                  });
                  setPreviewOpen(true);
                  watch(id);
                }}
                onExcelDrafts={async (made) => {
                  await loadDrafts();
                  setLibraryTab("drafts");
                  toast(
                    `Created ${made.length} draft${made.length === 1 ? "" : "s"}. Check each one's footage, then render.`,
                    "success",
                  );
                  if (made[0]) await selectDraft(made[0].id);
                }}
                onLongVideo={(id, title) => {
                  setSelectedVideo(null);
                  setDetail(null);
                  setJobTitle(title);
                  setJob({
                    id,
                    kind: "long_video",
                    status: "queued",
                    step: 0,
                    log: [],
                    title,
                  });
                  setLibraryTab("videos");
                  setPreviewOpen(true);
                  watch(id);
                }}
                onShorts={(id, title) => {
                  setSelectedVideo(null);
                  setDetail(null);
                  setJobTitle(title);
                  setJob({
                    id,
                    kind: "short",
                    status: "queued",
                    step: 0,
                    log: [],
                    title,
                  });
                  setLibraryTab("videos");
                  setPreviewOpen(true);
                  watch(id);
                }}
                onExcelRender={(id, title) => {
                  setSelectedVideo(null);
                  setDetail(null);
                  setJobTitle(title);
                  setJob({
                    id,
                    kind: "excel",
                    status: "queued",
                    step: 0,
                    log: [],
                    title,
                  });
                  setLibraryTab("videos");
                  setPreviewOpen(true);
                  watch(id);
                }}
                onSong={(s, lang, topic) => {
                  setSongState({ song: s, lang, topic });
                  setSelectedVideo(null);
                  setDetail(null);
                  toast(
                    "Lyrics written. Check them, then compose the song.",
                    "success",
                  );
                }}
                onScript={async (script, lang, topic, notice) => {
                  await openDraft(toDraft(script, lang, topic), false);
                  setSelectedVideo(null);
                  setDetail(null);
                  setLibraryTab("drafts");
                  if (notice) toast(notice, "success");
                }}
              />
            )}
            {draft && options && (
              <Storyboard
                draft={draft}
                setDraft={setDraft}
                options={options}
                rendering={rendering}
                saveState={saveState}
                activeUid={activeUid}
                timeline={timeline}
                onMusicAdded={reloadOptions}
                stage={renderPreview("stage")}
                exportKey={exportDetail?.name ?? null}
                exportPanel={
                  exportDetail && (
                    <ExportCards
                      detail={exportDetail}
                      onThumbnail={(summary) => {
                        setDetail((d) =>
                          d && d.name === summary.name
                            ? { ...d, ...summary }
                            : d,
                        );
                        setVideos(
                          (vs) =>
                            vs?.map((v) =>
                              v.name === summary.name ? summary : v,
                            ) ?? vs,
                        );
                      }}
                      onDeleteVideo={deleteVideo}
                      onOpenSettings={() => setView("settings")}
                    />
                  )
                }
                history={{
                  canUndo: historyFlags[0] === "1",
                  canRedo: historyFlags[1] === "1",
                  undo: () => step("undo"),
                  redo: () => step("redo"),
                }}
                onActive={(uid, seek = true) => {
                  setActiveUid(uid);
                  setPreviewView("scene");
                  if (seek) timeline.seekScene(uid);
                }}
                onBack={closeDraft}
                onNewDraft={async (d, notice) => {
                  await openDraft(d, false);
                  toast(notice, "success");
                }}
                onDeleteDraft={() => void deleteDraft()}
                onRender={async (script, settings) => {
                  try {
                    const { id } = await api.render({
                      script,
                      topic: draft.topic,
                      lang: draft.lang,
                      ...settings,
                      draft_id: draftId.current ?? "",
                    });
                    setSelectedVideo(null);
                    setJobTitle(script.title);
                    setJob({
                      id,
                      status: "queued",
                      step: 0,
                      log: [],
                      title: script.title,
                    });
                    setPreviewOpen(true);
                    watch(id);
                    return null;
                  } catch (e) {
                    return (e as Error).message;
                  }
                }}
              />
            )}
          </main>

          {sidePreview && (
            <aside
              aria-label="Preview"
              className="relative hidden min-h-0 border-l border-line bg-paper wide:block"
            >
              <div className="relative h-full overflow-y-auto">{preview}</div>
              <ResizeHandle
                edge="left"
                label="Resize preview"
                width={previewPane.width}
                min={300}
                max={560}
                onResize={previewPane.setWidth}
                onReset={previewPane.reset}
              />
            </aside>
          )}
        </div>

        <div className="lg:hidden">
          <Drawer
            open={libraryOpen}
            side="left"
            onClose={() => setLibraryOpen(false)}
            label="Library"
          >
            {library}
          </Drawer>
        </div>
        <div className="wide:hidden">
          <Drawer
            open={previewOpen && sidePreview && view === "studio"}
            side="right"
            onClose={() => setPreviewOpen(false)}
            label="Preview"
          >
            {preview}
          </Drawer>
        </div>
      </div>
    </div>
  );
}
