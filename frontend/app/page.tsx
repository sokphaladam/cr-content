"use client";

import { CircleAlert } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Aspect, type DraftSummary, type Job, type Lang, type Options, type SongScript, type VideoDetail, type VideoSummary } from "@/lib/api";
import { CreateForm } from "@/components/CreateForm";
import { Library, type LibraryTab } from "@/components/Library";
import { PreviewPane, type PreviewView } from "@/components/PreviewPane";
import { LyricsTiming } from "@/components/LyricsTiming";
import { SongEditor } from "@/components/SongEditor";
import { Storyboard, toDraft, toDraftData, type Draft, type SaveState } from "@/components/Storyboard";
import { TopBar } from "@/components/TopBar";
import { Drawer, ToastProvider, useToast } from "@/components/ui";

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
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  // Song being edited (not autosaved; composing writes song.json into its output folder)
  const [song, setSongState] = useState<{ song: SongScript; lang: Lang; topic: string } | null>(null);
  const setSong = useCallback(
    (update: (s: SongScript) => SongScript) => setSongState((cur) => (cur ? { ...cur, song: update(cur.song) } : cur)),
    [],
  );
  // Song whose lyric timing is open in the editor (its output folder); the version remounts it after a re-sync.
  // It keeps its own copy of the song's details so the preview can show a rendered version meanwhile.
  const [timing, setTiming] = useState<{ name: string; version: number; title: string; lang: Lang; aspect: Aspect; sections: string[]; idea: string } | null>(
    null,
  );
  const poll = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Autosave bookkeeping. Saves run one after another so a burst of edits can't create duplicate drafts.
  const draftId = useRef<string | null>(null);
  const lastSaved = useRef<string>(""); // serialized content last written to disk
  const saveQueue = useRef<Promise<void>>(Promise.resolve());
  const currentDraft = useRef<Draft | null>(null);
  useEffect(() => {
    currentDraft.current = draft;
  }, [draft]);

  const setDraft = useCallback((update: (d: Draft) => Draft) => setDraftState((d) => (d ? update(d) : d)), []);

  const loadVideos = useCallback(async () => {
    try {
      setVideos(await withRetry(api.videos));
    } catch {
      setVideos([]);
    }
  }, []);
  const loadDrafts = useCallback(async () => {
    try {
      setDrafts(await withRetry(api.drafts));
    } catch {
      setDrafts([]);
    }
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

  // Desktop app: the native "Save as" dialog reports how each download went.
  useEffect(() => {
    const onDownload = (e: Event) => {
      const { success, name } = (e as CustomEvent<{ success: boolean; name: string | null }>).detail;
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
      setDraftState(d);
      setLibraryOpen(false);
    },
    [flush],
  );

  const closeDraft = useCallback(async () => {
    await flush();
    draftId.current = null;
    setDraftState(null);
    setActiveUid(null);
  }, [flush]);

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
      idea: d.idea ?? "",
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
      await openDraft(toDraft(d.script, d.lang, d.topic, { id, voice: d.voice, rate: d.rate, music: d.music }), true);
      setSelectedVideo(null);
      setDetail(null);
      setPreviewView("scene");
    } catch (e) {
      toast((e as Error).message, "error");
      void loadDrafts();
    }
  }

  async function deleteDraft() {
    const id = draftId.current;
    if (!id) return;
    await saveQueue.current; // let any in-flight save finish first
    try {
      await api.deleteDraft(id);
      toast("Draft deleted");
    } catch (e) {
      toast((e as Error).message, "error");
    }
    draftId.current = null;
    lastSaved.current = "";
    setDraftState(null);
    void loadDrafts();
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
                : j.kind === "lyrics_sync"
                  ? "Lyrics synced. Play the song to check the timing, then make the music video."
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
        setJob((j) => (j ? { ...j, status: "error", error: (e as Error).message } : j));
        return;
      }
      poll.current = setTimeout(tick, 1000);
    };
    void tick();
  }

  const rendering = job !== null && (job.status === "queued" || job.status === "running");
  const activeIndex = draft ? Math.max(0, draft.scenes.findIndex((s) => s.uid === activeUid)) : 0;
  const activeScene = draft ? (draft.scenes[activeIndex] ?? null) : null;
  const hasPreview = !!draft || !!song || !!timing || rendering || job?.status === "error" || !!detail?.video || !!detail?.audio;

  const library = (
    <Library
      tab={libraryTab}
      onTab={setLibraryTab}
      drafts={drafts}
      videos={videos}
      selectedDraft={draft?.id ?? timing?.name ?? (detail?.kind === "song" ? detail.name : null)}
      selectedVideo={selectedVideo}
      onSelectDraft={selectDraft}
      onSelectSong={(name) => {
        setLibraryOpen(false);
        void selectVideo(name, true);
      }}
      onSelectVideo={(name) => selectVideo(name, true)}
      onNew={async () => {
        await closeDraft();
        setSongState(null);
        setTiming(null);
        void selectVideo(null, false);
        setLibraryOpen(false);
      }}
    />
  );

  const preview = (
    <PreviewPane
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
        setDetail((d) => (d && d.name === summary.name ? { ...d, ...summary } : d));
        setVideos((vs) => vs?.map((v) => (v.name === summary.name ? summary : v)) ?? vs);
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
      onMakeMusicVideo={async (name, idea) => {
        try {
          const { id } = await api.musicVideo(name, idea);
          setJobTitle(detail?.title ?? name);
          setJob({ id, kind: "song_video", status: "queued", step: 0, log: [], title: detail?.title ?? name });
          setPreviewOpen(true);
          watch(id);
        } catch (e) {
          toast((e as Error).message, "error");
        }
      }}
      onDeleteVideo={async (name) => {
        await api.deleteVideo(name);
        toast(detail?.kind === "song" ? "Song deleted. Its music videos are still in Videos." : "Video deleted");
        if (timing?.name === name) setTiming(null);
        await selectVideo(null, false);
        await Promise.all([loadVideos(), loadDrafts()]);
      }}
    />
  );

  return (
    <div className="flex h-dvh flex-col">
      <TopBar options={options} onOpenLibrary={() => setLibraryOpen(true)} onOpenPreview={() => setPreviewOpen(true)} showPreviewButton={hasPreview} />

      {engineError && (
        <div role="alert" className="flex items-center gap-2 border-b border-danger/30 bg-danger/[0.07] px-4 py-2.5 text-[13.5px] text-danger">
          <CircleAlert className="size-4 shrink-0" />
          {engineError}
        </div>
      )}

      <div className={`grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[264px_minmax(0,1fr)] ${hasPreview ? "wide:grid-cols-[264px_minmax(0,1fr)_340px]" : ""}`}>
        <aside aria-label="Library" className="hidden min-h-0 border-r border-line bg-panel/60 lg:block">
          {library}
        </aside>

        <main className="min-h-0 min-w-0">
          {!draft && !song && timing && (
            <LyricsTiming
              key={`${timing.name}-${timing.version}`}
              name={timing.name}
              title={timing.title}
              lang={timing.lang}
              aspect={timing.aspect}
              sections={timing.sections}
              idea={timing.idea}
              busy={rendering}
              onBack={() => setTiming(null)}
              onResync={async () => {
                try {
                  const { id } = await api.resyncLyrics(timing.name);
                  setJobTitle(timing.title);
                  setJob({ id, kind: "lyrics_sync", status: "queued", step: 0, log: [], title: timing.title });
                  setPreviewOpen(true);
                  watch(id);
                  return null;
                } catch (e) {
                  return (e as Error).message;
                }
              }}
              onMakeVideo={async (idea) => {
                try {
                  const { id } = await api.musicVideo(timing.name, idea);
                  setTiming((t) => (t ? { ...t, idea } : t));
                  setJobTitle(timing.title);
                  setJob({ id, kind: "song_video", status: "queued", step: 0, log: [], title: timing.title });
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
              onCompose={async (stems) => {
                try {
                  const { id } = await api.composeSong({ song: song.song, topic: song.topic, lang: song.lang, stems });
                  setSelectedVideo(null);
                  setJobTitle(song.song.title);
                  setJob({ id, kind: "song", status: "queued", step: 0, log: [], title: song.song.title });
                  setPreviewOpen(true);
                  watch(id);
                  return null;
                } catch (e) {
                  return (e as Error).message;
                }
              }}
            />
          )}
          {!draft && !song && !timing && (
            <CreateForm
              options={options}
              onImportSong={(id, title) => {
                setSelectedVideo(null);
                setDetail(null);
                setJobTitle(title);
                setJob({ id, kind: "lyrics_sync", status: "queued", step: 0, log: [], title });
                setPreviewOpen(true);
                watch(id);
              }}
              onSong={(s, lang, topic) => {
                setSongState({ song: s, lang, topic });
                setSelectedVideo(null);
                setDetail(null);
                toast("Lyrics written. Check them, then compose the song.", "success");
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
              onActive={(uid) => {
                setActiveUid(uid);
                setPreviewView("scene");
              }}
              onBack={closeDraft}
              onNewDraft={async (d, notice) => {
                await openDraft(d, false);
                toast(notice, "success");
              }}
              onDeleteDraft={deleteDraft}
              onRender={async (script, settings) => {
                try {
                  const { id } = await api.render({ script, topic: draft.topic, lang: draft.lang, ...settings, draft_id: draftId.current ?? "" });
                  setSelectedVideo(null);
                  setJobTitle(script.title);
                  setJob({ id, status: "queued", step: 0, log: [], title: script.title });
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

        {hasPreview && (
          <aside aria-label="Preview" className="hidden min-h-0 overflow-y-auto border-l border-line bg-panel/60 wide:block">
            {preview}
          </aside>
        )}
      </div>

      <div className="lg:hidden">
        <Drawer open={libraryOpen} side="left" onClose={() => setLibraryOpen(false)} label="Library">
          {library}
        </Drawer>
      </div>
      <div className="wide:hidden">
        <Drawer open={previewOpen && hasPreview} side="right" onClose={() => setPreviewOpen(false)} label="Preview">
          {preview}
        </Drawer>
      </div>
    </div>
  );
}
