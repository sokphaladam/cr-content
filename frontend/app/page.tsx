"use client";

import { CircleAlert } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, type DraftSummary, type Job, type Options, type VideoDetail, type VideoSummary } from "@/lib/api";
import { CreateForm } from "@/components/CreateForm";
import { Library, type LibraryTab } from "@/components/Library";
import { PreviewPane, type PreviewView } from "@/components/PreviewPane";
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
      await new Promise((r) => setTimeout(r, 1000 * i));
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
    api
      .options()
      .then(setOptions)
      .catch((e: Error) => setEngineError(e.message));
    void loadVideos();
    void loadDrafts();
    return () => {
      if (poll.current) clearTimeout(poll.current);
    };
  }, [loadVideos, loadDrafts]);

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
      if (openScript && d.script) await openDraft(toDraft(d.script, d.lang, ""), true);
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  async function selectDraft(id: string) {
    try {
      const d = await api.draft(id);
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
          toast("Video ready. Your draft is still saved, so you can render another version.", "success");
          await loadVideos();
          await selectVideo(j.video ?? null, false);
          return;
        }
        if (j.status === "error") {
          toast(`Rendering failed: ${j.error ?? "unknown error"}`, "error");
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
  const hasPreview = !!draft || rendering || job?.status === "error" || !!detail?.video;

  const library = (
    <Library
      tab={libraryTab}
      onTab={setLibraryTab}
      drafts={drafts}
      videos={videos}
      selectedDraft={draft?.id ?? null}
      selectedVideo={selectedVideo}
      onSelectDraft={selectDraft}
      onSelectVideo={(name) => selectVideo(name, true)}
      onNew={async () => {
        await closeDraft();
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
      onDeleteVideo={async (name) => {
        await api.deleteVideo(name);
        toast("Video deleted");
        await selectVideo(null, false);
        await loadVideos();
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
          {!draft && (
            <CreateForm
              options={options}
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
