(globalThis["TURBOPACK"] || (globalThis["TURBOPACK"] = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/app/page.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>Page
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$circle$2d$alert$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__CircleAlert$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/circle-alert.mjs [app-client] (ecmascript) <export default as CircleAlert>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$CreateForm$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/CreateForm.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$Library$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/Library.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$PreviewPane$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/PreviewPane.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$LyricsTiming$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/LyricsTiming.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$SongEditor$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/SongEditor.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$Storyboard$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/Storyboard.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$TopBar$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/TopBar.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/ui.tsx [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
"use client";
;
;
;
;
;
;
;
;
;
;
;
const AUTOSAVE_MS = 800;
/** Retry a few times: the engine may be (re)starting when the page loads. */ async function withRetry(fn, tries = 4) {
    for(let i = 1;; i++){
        try {
            return await fn();
        } catch (e) {
            if (i >= tries) throw e;
            await new Promise((r)=>setTimeout(r, 1000 * Math.min(i, 3)));
        }
    }
}
function Page() {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["ToastProvider"], {
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Studio, {}, void 0, false, {
            fileName: "[project]/app/page.tsx",
            lineNumber: 32,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/app/page.tsx",
        lineNumber: 31,
        columnNumber: 5
    }, this);
}
_c = Page;
function Studio() {
    _s();
    const toast = (0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useToast"])();
    const [options, setOptions] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [engineError, setEngineError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [videos, setVideos] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [drafts, setDrafts] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [libraryTab, setLibraryTab] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("drafts");
    const [draft, setDraftState] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [saveState, setSaveState] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("idle");
    const [activeUid, setActiveUid] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [selectedVideo, setSelectedVideo] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [detail, setDetail] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [previewView, setPreviewView] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("scene");
    const [job, setJob] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [jobTitle, setJobTitle] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [libraryOpen, setLibraryOpen] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [previewOpen, setPreviewOpen] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    // Song being edited (not autosaved; composing writes song.json into its output folder)
    const [song, setSongState] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const setSong = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "Studio.useCallback[setSong]": (update)=>setSongState({
                "Studio.useCallback[setSong]": (cur)=>cur ? {
                        ...cur,
                        song: update(cur.song)
                    } : cur
            }["Studio.useCallback[setSong]"])
    }["Studio.useCallback[setSong]"], []);
    // Song whose lyric timing is open in the editor (its output folder); the version remounts it after a re-sync.
    // It keeps its own copy of the song's details so the preview can show a rendered version meanwhile.
    const [timing, setTiming] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const poll = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    // Autosave bookkeeping. Saves run one after another so a burst of edits can't create duplicate drafts.
    const draftId = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    const lastSaved = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(""); // serialized content last written to disk
    const saveQueue = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(Promise.resolve());
    const currentDraft = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "Studio.useEffect": ()=>{
            currentDraft.current = draft;
        }
    }["Studio.useEffect"], [
        draft
    ]);
    const setDraft = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "Studio.useCallback[setDraft]": (update)=>setDraftState({
                "Studio.useCallback[setDraft]": (d)=>d ? update(d) : d
            }["Studio.useCallback[setDraft]"])
    }["Studio.useCallback[setDraft]"], []);
    const loadVideos = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "Studio.useCallback[loadVideos]": async ()=>{
            try {
                setVideos(await withRetry(__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].videos));
            } catch  {
                setVideos([]);
            }
        }
    }["Studio.useCallback[loadVideos]"], []);
    const loadDrafts = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "Studio.useCallback[loadDrafts]": async ()=>{
            try {
                setDrafts(await withRetry(__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].drafts));
            } catch  {
                setDrafts([]);
            }
        }
    }["Studio.useCallback[loadDrafts]"], []);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "Studio.useEffect": ()=>{
            // The engine may still be starting (the desktop app launches it alongside the window), so wait for it first.
            withRetry(__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].options, 12).then({
                "Studio.useEffect": (o)=>{
                    setOptions(o);
                    void loadVideos();
                    void loadDrafts();
                }
            }["Studio.useEffect"]).catch({
                "Studio.useEffect": (e)=>{
                    setEngineError(e.message);
                    setVideos([]);
                    setDrafts([]);
                }
            }["Studio.useEffect"]);
            return ({
                "Studio.useEffect": ()=>{
                    if (poll.current) clearTimeout(poll.current);
                }
            })["Studio.useEffect"];
        }
    }["Studio.useEffect"], [
        loadVideos,
        loadDrafts
    ]);
    // Desktop app: the native "Save as" dialog reports how each download went.
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "Studio.useEffect": ()=>{
            const onDownload = {
                "Studio.useEffect.onDownload": (e)=>{
                    const { success, name } = e.detail;
                    if (success) toast(name ? `Saved ${name}` : "Download saved", "success");
                    else toast("Download failed. Try again.", "error");
                }
            }["Studio.useEffect.onDownload"];
            window.addEventListener("desktop-download", onDownload);
            return ({
                "Studio.useEffect": ()=>window.removeEventListener("desktop-download", onDownload)
            })["Studio.useEffect"];
        }
    }["Studio.useEffect"], [
        toast
    ]);
    /** Queue a save of `body`. Runs after earlier saves so ids are never created twice. */ const enqueueSave = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "Studio.useCallback[enqueueSave]": (body)=>{
            const forId = draftId.current;
            saveQueue.current = saveQueue.current.then({
                "Studio.useCallback[enqueueSave]": async ()=>{
                    if (body === lastSaved.current || draftId.current !== forId) return; // unchanged, or user switched drafts
                    setSaveState("saving");
                    try {
                        const data = JSON.parse(body);
                        if (forId) {
                            await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].saveDraft(forId, data);
                        } else {
                            const { id } = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].createDraft(data);
                            draftId.current = id;
                            setDraftState({
                                "Studio.useCallback[enqueueSave]": (d)=>d && d.id === null ? {
                                        ...d,
                                        id
                                    } : d
                            }["Studio.useCallback[enqueueSave]"]);
                        }
                        lastSaved.current = body;
                        setSaveState("saved");
                        void loadDrafts();
                    } catch  {
                        setSaveState("error");
                    }
                }
            }["Studio.useCallback[enqueueSave]"]);
            return saveQueue.current;
        }
    }["Studio.useCallback[enqueueSave]"], [
        loadDrafts
    ]);
    /** Save pending edits right away (before leaving the current draft). */ const flush = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "Studio.useCallback[flush]": ()=>{
            const d = currentDraft.current;
            if (!d) return Promise.resolve();
            const body = JSON.stringify((0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$Storyboard$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["toDraftData"])(d));
            return body === lastSaved.current ? saveQueue.current : enqueueSave(body);
        }
    }["Studio.useCallback[flush]"], [
        enqueueSave
    ]);
    // Autosave: write the draft to drafts/<id>/draft.json shortly after each change.
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "Studio.useEffect": ()=>{
            if (!draft) return;
            const body = JSON.stringify((0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$Storyboard$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["toDraftData"])(draft));
            if (body === lastSaved.current) return;
            const timer = setTimeout({
                "Studio.useEffect.timer": ()=>enqueueSave(body)
            }["Studio.useEffect.timer"], AUTOSAVE_MS);
            return ({
                "Studio.useEffect": ()=>clearTimeout(timer)
            })["Studio.useEffect"];
        }
    }["Studio.useEffect"], [
        draft,
        enqueueSave
    ]);
    /** Put a draft in the editor (saving the previous one first). `persisted` = this content is already on disk. */ const openDraft = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "Studio.useCallback[openDraft]": async (d, persisted)=>{
            await flush();
            draftId.current = d.id;
            lastSaved.current = persisted ? JSON.stringify((0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$Storyboard$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["toDraftData"])(d)) : "";
            setSaveState("idle");
            setActiveUid(d.scenes[0]?.uid ?? null);
            setDraftState(d);
            setLibraryOpen(false);
        }
    }["Studio.useCallback[openDraft]"], [
        flush
    ]);
    const closeDraft = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "Studio.useCallback[closeDraft]": async ()=>{
            await flush();
            draftId.current = null;
            setDraftState(null);
            setActiveUid(null);
        }
    }["Studio.useCallback[closeDraft]"], [
        flush
    ]);
    /** Open a song's lyric timing editor; `reload` remounts it with fresh timing (after a sync). */ async function openTiming(name, reload = false) {
        const d = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].video(name);
        await closeDraft();
        setSongState(null);
        setTiming((t)=>({
                name,
                version: t?.name === name ? t.version + (reload ? 1 : 0) : 0,
                title: d.title,
                lang: d.lang,
                aspect: d.aspect,
                sections: d.song?.sections.map((s)=>s.name) ?? [],
                settings: (0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$PreviewPane$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["settingsOf"])(d)
            }));
        return d;
    }
    async function selectVideo(name, openScript) {
        setSelectedVideo(name);
        if (!name) {
            setDetail(null);
            return;
        }
        try {
            const d = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].video(name);
            setDetail(d);
            setPreviewView("video");
            // Editing a rendered video's script starts a new draft on the first change; the video stays as it is.
            if (openScript && d.script) {
                setSongState(null);
                await openDraft((0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$Storyboard$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["toDraft"])(d.script, d.lang, ""), true);
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
                setSongState({
                    song: d.song,
                    lang: d.lang,
                    topic: ""
                });
            }
        } catch (e) {
            toast(e.message, "error");
        }
    }
    async function selectDraft(id) {
        try {
            const d = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].draft(id);
            setSongState(null);
            setTiming(null);
            await openDraft((0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$Storyboard$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["toDraft"])(d.script, d.lang, d.topic, {
                id,
                voice: d.voice,
                rate: d.rate,
                music: d.music
            }), true);
            setSelectedVideo(null);
            setDetail(null);
            setPreviewView("scene");
        } catch (e) {
            toast(e.message, "error");
            void loadDrafts();
        }
    }
    async function deleteDraft() {
        const id = draftId.current;
        if (!id) return;
        await saveQueue.current; // let any in-flight save finish first
        try {
            await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].deleteDraft(id);
            toast("Draft deleted");
        } catch (e) {
            toast(e.message, "error");
        }
        draftId.current = null;
        lastSaved.current = "";
        setDraftState(null);
        void loadDrafts();
    }
    function watch(id) {
        const tick = async ()=>{
            try {
                const j = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].job(id);
                setJob(j);
                if (j.status === "done") {
                    toast(j.kind === "song" ? "Song ready. Make a music video from it, or edit the lyrics and compose again." : j.kind === "song_video" ? "Music video ready." : j.kind === "lyrics_sync" ? "Lyrics synced. Play the song to check the timing, then make the music video." : "Video ready. Your draft is still saved, so you can render another version.", "success");
                    await Promise.all([
                        loadVideos(),
                        loadDrafts()
                    ]);
                    await selectVideo(j.video ?? null, false);
                    if (j.kind === "lyrics_sync" && j.video) {
                        await openTiming(j.video, true);
                        setLibraryTab("drafts");
                        setJob(null);
                    }
                    return;
                }
                if (j.status === "error") {
                    toast(`${j.kind === "song" ? "Composing" : j.kind === "lyrics_sync" ? "Lyric sync" : "Rendering"} failed: ${j.error ?? "unknown error"}`, "error");
                    if (j.kind === "lyrics_sync" && j.video) {
                        // the song was saved; open it so the timing can be fixed by hand or synced again
                        await Promise.all([
                            loadVideos(),
                            loadDrafts()
                        ]);
                        await selectVideo(j.video, false);
                        await openTiming(j.video, true);
                    }
                    // keep the song editor/preview usable after a failed music-video render
                    if (j.kind === "song_video") setJob(null);
                    return;
                }
            } catch (e) {
                setJob((j)=>j ? {
                        ...j,
                        status: "error",
                        error: e.message
                    } : j);
                return;
            }
            poll.current = setTimeout(tick, 1000);
        };
        void tick();
    }
    const rendering = job !== null && (job.status === "queued" || job.status === "running");
    const activeIndex = draft ? Math.max(0, draft.scenes.findIndex((s)=>s.uid === activeUid)) : 0;
    const activeScene = draft ? draft.scenes[activeIndex] ?? null : null;
    const hasPreview = !!draft || !!song || !!timing || rendering || job?.status === "error" || !!detail?.video || !!detail?.audio;
    const library = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$Library$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Library"], {
        tab: libraryTab,
        onTab: setLibraryTab,
        drafts: drafts,
        videos: videos,
        selectedDraft: draft?.id ?? timing?.name ?? (detail?.kind === "song" ? detail.name : null),
        selectedVideo: selectedVideo,
        onSelectDraft: selectDraft,
        onSelectSong: (name)=>{
            setLibraryOpen(false);
            void selectVideo(name, true);
        },
        onSelectVideo: (name)=>selectVideo(name, true),
        onNew: async ()=>{
            await closeDraft();
            setSongState(null);
            setTiming(null);
            void selectVideo(null, false);
            setLibraryOpen(false);
        }
    }, void 0, false, {
        fileName: "[project]/app/page.tsx",
        lineNumber: 323,
        columnNumber: 5
    }, this);
    const preview = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$PreviewPane$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["PreviewPane"], {
        scene: activeScene,
        sceneIndex: activeIndex,
        sceneCount: draft?.scenes.length ?? 0,
        lang: draft?.lang ?? "en",
        rendering: rendering,
        job: job,
        jobTitle: jobTitle,
        detail: detail,
        view: previewView,
        onView: setPreviewView,
        onThumbnail: (summary)=>{
            setDetail((d)=>d && d.name === summary.name ? {
                    ...d,
                    ...summary
                } : d);
            setVideos((vs)=>vs?.map((v)=>v.name === summary.name ? summary : v) ?? vs);
        },
        onOpenTiming: async (name)=>{
            try {
                await openTiming(name);
                setPreviewOpen(false);
            } catch (e) {
                toast(e.message, "error");
            }
        },
        onSelectVideo: (name)=>void selectVideo(name, false),
        onMakeMusicVideo: async (name, settings)=>{
            try {
                const { id } = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].musicVideo(name, settings);
                setJobTitle(detail?.title ?? name);
                setJob({
                    id,
                    kind: "song_video",
                    status: "queued",
                    step: 0,
                    log: [],
                    title: detail?.title ?? name
                });
                setPreviewOpen(true);
                watch(id);
            } catch (e) {
                toast(e.message, "error");
            }
        },
        onDeleteVideo: async (name)=>{
            await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].deleteVideo(name);
            toast(detail?.kind === "song" ? "Song deleted. Its music videos are still in Videos." : "Video deleted");
            if (timing?.name === name) setTiming(null);
            await selectVideo(null, false);
            await Promise.all([
                loadVideos(),
                loadDrafts()
            ]);
        }
    }, void 0, false, {
        fileName: "[project]/app/page.tsx",
        lineNumber: 347,
        columnNumber: 5
    }, this);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "flex h-dvh flex-col",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$TopBar$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["TopBar"], {
                options: options,
                onOpenLibrary: ()=>setLibraryOpen(true),
                onOpenPreview: ()=>setPreviewOpen(true),
                showPreviewButton: hasPreview
            }, void 0, false, {
                fileName: "[project]/app/page.tsx",
                lineNumber: 394,
                columnNumber: 7
            }, this),
            engineError && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                role: "alert",
                className: "flex items-center gap-2 border-b border-danger/30 bg-danger/[0.07] px-4 py-2.5 text-[13.5px] text-danger",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$circle$2d$alert$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__CircleAlert$3e$__["CircleAlert"], {
                        className: "size-4 shrink-0"
                    }, void 0, false, {
                        fileName: "[project]/app/page.tsx",
                        lineNumber: 398,
                        columnNumber: 11
                    }, this),
                    engineError
                ]
            }, void 0, true, {
                fileName: "[project]/app/page.tsx",
                lineNumber: 397,
                columnNumber: 9
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: `grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[264px_minmax(0,1fr)] ${hasPreview ? "wide:grid-cols-[264px_minmax(0,1fr)_340px]" : ""}`,
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("aside", {
                        "aria-label": "Library",
                        className: "hidden min-h-0 border-r border-line bg-panel/60 lg:block",
                        children: library
                    }, void 0, false, {
                        fileName: "[project]/app/page.tsx",
                        lineNumber: 404,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("main", {
                        className: "min-h-0 min-w-0",
                        children: [
                            !draft && !song && timing && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$LyricsTiming$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["LyricsTiming"], {
                                name: timing.name,
                                title: timing.title,
                                lang: timing.lang,
                                aspect: timing.aspect,
                                sections: timing.sections,
                                settings: timing.settings,
                                busy: rendering,
                                onBack: ()=>setTiming(null),
                                onResync: async ()=>{
                                    try {
                                        const { id } = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].resyncLyrics(timing.name);
                                        setJobTitle(timing.title);
                                        setJob({
                                            id,
                                            kind: "lyrics_sync",
                                            status: "queued",
                                            step: 0,
                                            log: [],
                                            title: timing.title
                                        });
                                        setPreviewOpen(true);
                                        watch(id);
                                        return null;
                                    } catch (e) {
                                        return e.message;
                                    }
                                },
                                onMakeVideo: async (settings)=>{
                                    try {
                                        const { id } = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].musicVideo(timing.name, settings);
                                        setTiming((t)=>t ? {
                                                ...t,
                                                settings
                                            } : t);
                                        setJobTitle(timing.title);
                                        setJob({
                                            id,
                                            kind: "song_video",
                                            status: "queued",
                                            step: 0,
                                            log: [],
                                            title: timing.title
                                        });
                                        setPreviewOpen(true);
                                        watch(id);
                                        return null;
                                    } catch (e) {
                                        return e.message;
                                    }
                                }
                            }, `${timing.name}-${timing.version}`, false, {
                                fileName: "[project]/app/page.tsx",
                                lineNumber: 410,
                                columnNumber: 13
                            }, this),
                            !draft && song && options && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$SongEditor$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["SongEditor"], {
                                song: song.song,
                                setSong: setSong,
                                lang: song.lang,
                                options: options,
                                composing: rendering && job?.kind === "song",
                                onBack: ()=>setSongState(null),
                                onCompose: async (stems)=>{
                                    try {
                                        const { id } = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].composeSong({
                                            song: song.song,
                                            topic: song.topic,
                                            lang: song.lang,
                                            stems
                                        });
                                        setSelectedVideo(null);
                                        setJobTitle(song.song.title);
                                        setJob({
                                            id,
                                            kind: "song",
                                            status: "queued",
                                            step: 0,
                                            log: [],
                                            title: song.song.title
                                        });
                                        setPreviewOpen(true);
                                        watch(id);
                                        return null;
                                    } catch (e) {
                                        return e.message;
                                    }
                                }
                            }, void 0, false, {
                                fileName: "[project]/app/page.tsx",
                                lineNumber: 448,
                                columnNumber: 13
                            }, this),
                            !draft && !song && !timing && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$CreateForm$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["CreateForm"], {
                                options: options,
                                onImportSong: (id, title)=>{
                                    setSelectedVideo(null);
                                    setDetail(null);
                                    setJobTitle(title);
                                    setJob({
                                        id,
                                        kind: "lyrics_sync",
                                        status: "queued",
                                        step: 0,
                                        log: [],
                                        title
                                    });
                                    setPreviewOpen(true);
                                    watch(id);
                                },
                                onSong: (s, lang, topic)=>{
                                    setSongState({
                                        song: s,
                                        lang,
                                        topic
                                    });
                                    setSelectedVideo(null);
                                    setDetail(null);
                                    toast("Lyrics written. Check them, then compose the song.", "success");
                                },
                                onScript: async (script, lang, topic, notice)=>{
                                    await openDraft((0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$Storyboard$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["toDraft"])(script, lang, topic), false);
                                    setSelectedVideo(null);
                                    setDetail(null);
                                    setLibraryTab("drafts");
                                    if (notice) toast(notice, "success");
                                }
                            }, void 0, false, {
                                fileName: "[project]/app/page.tsx",
                                lineNumber: 471,
                                columnNumber: 13
                            }, this),
                            draft && options && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$Storyboard$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Storyboard"], {
                                draft: draft,
                                setDraft: setDraft,
                                options: options,
                                rendering: rendering,
                                saveState: saveState,
                                activeUid: activeUid,
                                onActive: (uid)=>{
                                    setActiveUid(uid);
                                    setPreviewView("scene");
                                },
                                onBack: closeDraft,
                                onNewDraft: async (d, notice)=>{
                                    await openDraft(d, false);
                                    toast(notice, "success");
                                },
                                onDeleteDraft: deleteDraft,
                                onRender: async (script, settings)=>{
                                    try {
                                        const { id } = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].render({
                                            script,
                                            topic: draft.topic,
                                            lang: draft.lang,
                                            ...settings,
                                            draft_id: draftId.current ?? ""
                                        });
                                        setSelectedVideo(null);
                                        setJobTitle(script.title);
                                        setJob({
                                            id,
                                            status: "queued",
                                            step: 0,
                                            log: [],
                                            title: script.title
                                        });
                                        setPreviewOpen(true);
                                        watch(id);
                                        return null;
                                    } catch (e) {
                                        return e.message;
                                    }
                                }
                            }, void 0, false, {
                                fileName: "[project]/app/page.tsx",
                                lineNumber: 497,
                                columnNumber: 13
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/app/page.tsx",
                        lineNumber: 408,
                        columnNumber: 9
                    }, this),
                    hasPreview && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("aside", {
                        "aria-label": "Preview",
                        className: "hidden min-h-0 overflow-y-auto border-l border-line bg-panel/60 wide:block",
                        children: preview
                    }, void 0, false, {
                        fileName: "[project]/app/page.tsx",
                        lineNumber: 532,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/app/page.tsx",
                lineNumber: 403,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "lg:hidden",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Drawer"], {
                    open: libraryOpen,
                    side: "left",
                    onClose: ()=>setLibraryOpen(false),
                    label: "Library",
                    children: library
                }, void 0, false, {
                    fileName: "[project]/app/page.tsx",
                    lineNumber: 539,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/app/page.tsx",
                lineNumber: 538,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "wide:hidden",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Drawer"], {
                    open: previewOpen && hasPreview,
                    side: "right",
                    onClose: ()=>setPreviewOpen(false),
                    label: "Preview",
                    children: preview
                }, void 0, false, {
                    fileName: "[project]/app/page.tsx",
                    lineNumber: 544,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/app/page.tsx",
                lineNumber: 543,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/app/page.tsx",
        lineNumber: 393,
        columnNumber: 5
    }, this);
}
_s(Studio, "cj3pWCVhYDPPn7BxttywjuyWhRs=", false, function() {
    return [
        __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useToast"]
    ];
});
_c1 = Studio;
var _c, _c1;
__turbopack_context__.k.register(_c, "Page");
__turbopack_context__.k.register(_c1, "Studio");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/CreateForm.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "CreateForm",
    ()=>CreateForm
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$clipboard$2d$paste$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ClipboardPaste$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/clipboard-paste.mjs [app-client] (ecmascript) <export default as ClipboardPaste>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$music$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Music$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/music.mjs [app-client] (ecmascript) <export default as Music>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$pen$2d$line$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__PenLine$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/pen-line.mjs [app-client] (ecmascript) <export default as PenLine>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$sparkles$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Sparkles$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/sparkles.mjs [app-client] (ecmascript) <export default as Sparkles>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$upload$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Upload$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/upload.mjs [app-client] (ecmascript) <export default as Upload>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/ui.tsx [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature(), _s1 = __turbopack_context__.k.signature();
"use client";
;
;
;
;
const PLACEHOLDER = {
    en: "3 weird facts about octopuses",
    km: "ប្រវត្តិប្រាសាទអង្គរវត្ត"
};
const PASTE_EXAMPLE = [
    "Title: 3 Octopus Facts That Sound Fake",
    "",
    "[0–3s] Hook",
    "Visual: Close-up of an octopus eye",
    "On-screen text: This animal is basically an alien",
    "Voiceover: This animal is so weird, scientists still can't explain it.",
    "",
    "[3–10s] Fact 1",
    "…"
].join("\n");
const LYRICS_EXAMPLE = [
    "[Verse 1]",
    "I walked along the river in the rain",
    "The city lights were calling out your name",
    "",
    "[Chorus]",
    "Stay with me tonight",
    "…"
].join("\n");
/** Your own finished song: audio + lyrics in, then lyric timing runs as a job. */ function OwnSongForm({ onImported }) {
    _s();
    const [file, setFile] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [title, setTitle] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [lyrics, setLyrics] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [lang, setLang] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("en");
    const [aspect, setAspect] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("16:9");
    const [busy, setBusy] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [msg, setMsg] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])({
        text: ""
    });
    async function submit(e) {
        e.preventDefault();
        if (!file) return;
        setBusy(true);
        setMsg({
            text: "Uploading your song…"
        });
        try {
            const name = title.trim() || file.name.replace(/\.[^.]+$/, "");
            const { id } = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].importSong({
                file,
                title: name,
                lyrics,
                lang,
                aspect
            });
            setMsg({
                text: ""
            });
            onImported(id, name);
        } catch (err) {
            setMsg({
                text: err.message,
                error: true
            });
        } finally{
            setBusy(false);
        }
    }
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("form", {
        onSubmit: submit,
        className: "grid gap-5 rounded-xl border border-line bg-panel p-5 sm:p-6",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                label: "Song file",
                hint: "mp3, wav, m4a, flac",
                htmlFor: "own-file",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                    id: "own-file",
                    type: "file",
                    required: true,
                    accept: ".mp3,.wav,.m4a,.aac,.flac,.ogg,.opus,audio/*",
                    onChange: (e)=>{
                        const f = e.target.files?.[0] ?? null;
                        setFile(f);
                        if (f && !title) setTitle(f.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " "));
                    },
                    className: "field-input h-auto py-2 file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-ink/[0.06] file:px-3 file:py-1.5 file:font-semibold"
                }, void 0, false, {
                    fileName: "[project]/components/CreateForm.tsx",
                    lineNumber: 59,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/CreateForm.tsx",
                lineNumber: 58,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid items-end gap-5 sm:grid-cols-[minmax(0,1fr)_auto_auto]",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                        label: "Title",
                        htmlFor: "own-title",
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                            id: "own-title",
                            lang: lang,
                            className: "field-input",
                            value: title,
                            onChange: (e)=>setTitle(e.target.value),
                            placeholder: "Song title"
                        }, void 0, false, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 75,
                            columnNumber: 11
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/components/CreateForm.tsx",
                        lineNumber: 74,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "grid gap-1.5",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "field-label",
                                children: "Language"
                            }, void 0, false, {
                                fileName: "[project]/components/CreateForm.tsx",
                                lineNumber: 78,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Segmented"], {
                                name: "own-lang",
                                value: lang,
                                onChange: setLang,
                                options: [
                                    {
                                        value: "en",
                                        label: "English"
                                    },
                                    {
                                        value: "km",
                                        label: "ខ្មែរ",
                                        lang: "km"
                                    }
                                ]
                            }, void 0, false, {
                                fileName: "[project]/components/CreateForm.tsx",
                                lineNumber: 79,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/CreateForm.tsx",
                        lineNumber: 77,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "grid gap-1.5",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "field-label",
                                children: "Video shape"
                            }, void 0, false, {
                                fileName: "[project]/components/CreateForm.tsx",
                                lineNumber: 90,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Segmented"], {
                                name: "own-aspect",
                                value: aspect,
                                onChange: setAspect,
                                options: [
                                    {
                                        value: "16:9",
                                        label: "16:9 YouTube"
                                    },
                                    {
                                        value: "9:16",
                                        label: "9:16 vertical"
                                    }
                                ]
                            }, void 0, false, {
                                fileName: "[project]/components/CreateForm.tsx",
                                lineNumber: 91,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/CreateForm.tsx",
                        lineNumber: 89,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/CreateForm.tsx",
                lineNumber: 73,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                label: "Lyrics",
                hint: "one sung line per row; [Verse] / [Chorus] headings optional",
                htmlFor: "own-lyrics",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("textarea", {
                    id: "own-lyrics",
                    rows: 12,
                    required: true,
                    lang: lang,
                    value: lyrics,
                    onChange: (e)=>setLyrics(e.target.value),
                    placeholder: LYRICS_EXAMPLE,
                    className: "field-input resize-y py-2.5 leading-relaxed"
                }, void 0, false, {
                    fileName: "[project]/components/CreateForm.tsx",
                    lineNumber: 104,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/CreateForm.tsx",
                lineNumber: 103,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                className: "m-0 text-[13px] text-ink-soft",
                children: "The app listens to your song and lines each lyric up with the singing, then shows you the timing to check before it makes the video. Footage is picked for each part of the song and cut on the beat."
            }, void 0, false, {
                fileName: "[project]/components/CreateForm.tsx",
                lineNumber: 115,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "flex flex-wrap items-center gap-2 border-t border-line pt-5",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                    type: "submit",
                    variant: "primary",
                    loading: busy,
                    disabled: !file || !lyrics.trim(),
                    icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$upload$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Upload$3e$__["Upload"], {
                        className: "size-4"
                    }, void 0, false, {
                        fileName: "[project]/components/CreateForm.tsx",
                        lineNumber: 121,
                        columnNumber: 105
                    }, this),
                    children: busy ? "Uploading…" : "Upload and sync lyrics"
                }, void 0, false, {
                    fileName: "[project]/components/CreateForm.tsx",
                    lineNumber: 121,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/CreateForm.tsx",
                lineNumber: 120,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Message"], {
                ...msg
            }, void 0, false, {
                fileName: "[project]/components/CreateForm.tsx",
                lineNumber: 125,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/CreateForm.tsx",
        lineNumber: 57,
        columnNumber: 5
    }, this);
}
_s(OwnSongForm, "P/dKdreQTDd4fUFYX+dqXuCJihA=");
_c = OwnSongForm;
function CreateForm({ options, onScript, onSong, onImportSong }) {
    _s1();
    const [mode, setMode] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("topic");
    const [songSource, setSongSource] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("own");
    const [topic, setTopic] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [lang, setLang] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("en");
    const [seconds, setSeconds] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(45);
    const [scenes, setScenes] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(6);
    const [style, setStyle] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [busy, setBusy] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [msg, setMsg] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])({
        text: ""
    });
    const [pasted, setPasted] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [importing, setImporting] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [importMsg, setImportMsg] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])({
        text: ""
    });
    const [vocal, setVocal] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const claudeMissing = options !== null && !options.keys.anthropic;
    async function writeSong(e) {
        e.preventDefault();
        setBusy(true);
        setMsg({
            text: "Claude is writing your song. This usually takes 15–40 seconds."
        });
        try {
            const song = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].writeSong({
                topic: topic.trim(),
                lang,
                seconds,
                style,
                vocal
            });
            onSong(song, lang, topic.trim());
        } catch (err) {
            setMsg({
                text: err.message,
                error: true
            });
        } finally{
            setBusy(false);
        }
    }
    async function write(e) {
        e.preventDefault();
        setBusy(true);
        setMsg({
            text: "Claude is writing your script. This usually takes 15–40 seconds."
        });
        try {
            const script = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].writeScript({
                topic: topic.trim(),
                lang,
                scenes,
                seconds,
                style
            });
            onScript(script, lang, topic.trim(), "Script written and saved as a draft. Check each scene, then render.");
        } catch (err) {
            setMsg({
                text: err.message,
                error: true
            });
        } finally{
            setBusy(false);
        }
    }
    async function importPasted(e) {
        e.preventDefault();
        setImporting(true);
        setImportMsg({
            text: options?.keys.anthropic ? "Claude is reading your script…" : "Reading your script…"
        });
        try {
            const res = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].importScript(pasted);
            const n = res.script.scenes.length;
            onScript(res.script, res.lang, res.script.title, res.method === "claude" ? `Imported ${n} scenes. Voiceover kept word for word; footage searches come from your visual notes.` : `Imported ${n} scenes with the basic reader (Claude wasn't available). Check the footage searches.`);
        } catch (err) {
            setImportMsg({
                text: err.message,
                error: true
            });
        } finally{
            setImporting(false);
        }
    }
    function blank() {
        onScript({
            title: topic.trim(),
            scenes: Array.from({
                length: scenes
            }, ()=>({
                    narration: "",
                    visual_query: "",
                    on_screen_text: "",
                    media: ""
                })),
            caption: "",
            hashtags: []
        }, lang, topic.trim());
    }
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "h-full overflow-y-auto",
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "mx-auto grid max-w-[720px] gap-6 px-4 py-8 sm:px-8 sm:py-14",
            children: [
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "grid gap-2",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                            className: "m-0 font-display text-[clamp(30px,3.6vw,44px)] leading-[1.05] font-extrabold tracking-[-0.025em]",
                            children: "Make a new video"
                        }, void 0, false, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 225,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "m-0 max-w-[56ch] text-[15px] text-ink-soft",
                            children: "Start from an idea and let Claude write the script, or paste a script you already have. Either way it becomes a draft you can edit."
                        }, void 0, false, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 226,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/components/CreateForm.tsx",
                    lineNumber: 224,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Tabs"], {
                    label: "How to start",
                    value: mode,
                    onChange: (m)=>{
                        setMode(m);
                        setMsg({
                            text: ""
                        });
                    },
                    items: [
                        {
                            value: "topic",
                            label: "Start from a topic"
                        },
                        {
                            value: "paste",
                            label: "Paste a script"
                        },
                        {
                            value: "song",
                            label: "Music video"
                        }
                    ]
                }, void 0, false, {
                    fileName: "[project]/components/CreateForm.tsx",
                    lineNumber: 231,
                    columnNumber: 9
                }, this),
                mode === "song" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Segmented"], {
                    name: "song-source",
                    value: songSource,
                    onChange: setSongSource,
                    options: [
                        {
                            value: "own",
                            label: "Use my song (mp3 + lyrics)"
                        },
                        {
                            value: "ai",
                            label: "Compose with AI"
                        }
                    ]
                }, void 0, false, {
                    fileName: "[project]/components/CreateForm.tsx",
                    lineNumber: 246,
                    columnNumber: 11
                }, this),
                mode === "song" && songSource === "own" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(OwnSongForm, {
                    onImported: onImportSong
                }, void 0, false, {
                    fileName: "[project]/components/CreateForm.tsx",
                    lineNumber: 257,
                    columnNumber: 53
                }, this),
                mode === "song" && songSource === "ai" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("form", {
                    onSubmit: writeSong,
                    className: "grid gap-5 rounded-xl border border-line bg-panel p-5 sm:p-6",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                            label: "What the song is about",
                            htmlFor: "song-topic",
                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("textarea", {
                                id: "song-topic",
                                rows: 2,
                                required: true,
                                lang: lang,
                                value: topic,
                                onChange: (e)=>setTopic(e.target.value),
                                placeholder: "Summer love on the Phnom Penh riverside",
                                className: "field-input resize-y py-3 text-lg leading-snug font-medium"
                            }, void 0, false, {
                                fileName: "[project]/components/CreateForm.tsx",
                                lineNumber: 262,
                                columnNumber: 15
                            }, this)
                        }, void 0, false, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 261,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "grid items-end gap-5 sm:grid-cols-[auto_1fr]",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "grid gap-1.5",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: "field-label",
                                            children: "Language"
                                        }, void 0, false, {
                                            fileName: "[project]/components/CreateForm.tsx",
                                            lineNumber: 276,
                                            columnNumber: 17
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Segmented"], {
                                            name: "song-lang",
                                            value: lang,
                                            onChange: setLang,
                                            options: [
                                                {
                                                    value: "en",
                                                    label: "English"
                                                },
                                                {
                                                    value: "km",
                                                    label: "ខ្មែរ",
                                                    lang: "km"
                                                }
                                            ]
                                        }, void 0, false, {
                                            fileName: "[project]/components/CreateForm.tsx",
                                            lineNumber: 277,
                                            columnNumber: 17
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/CreateForm.tsx",
                                    lineNumber: 275,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                                    label: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                                        children: [
                                            "Length ",
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("output", {
                                                className: "ml-1 font-semibold text-ink",
                                                children: [
                                                    seconds,
                                                    " s"
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/components/CreateForm.tsx",
                                                lineNumber: 287,
                                                columnNumber: 38
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/components/CreateForm.tsx",
                                        lineNumber: 287,
                                        columnNumber: 29
                                    }, this),
                                    htmlFor: "song-seconds",
                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        id: "song-seconds",
                                        type: "range",
                                        min: 15,
                                        max: 120,
                                        step: 5,
                                        value: seconds,
                                        onChange: (e)=>setSeconds(+e.target.value),
                                        className: "h-10 w-full accent-cobalt"
                                    }, void 0, false, {
                                        fileName: "[project]/components/CreateForm.tsx",
                                        lineNumber: 288,
                                        columnNumber: 17
                                    }, this)
                                }, void 0, false, {
                                    fileName: "[project]/components/CreateForm.tsx",
                                    lineNumber: 287,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 274,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "grid gap-5 sm:grid-cols-2",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                                    label: "Genre and sound",
                                    hint: "optional",
                                    htmlFor: "song-style",
                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        id: "song-style",
                                        className: "field-input",
                                        value: style,
                                        onChange: (e)=>setStyle(e.target.value),
                                        placeholder: "Dreamy synth-pop, 80s drums"
                                    }, void 0, false, {
                                        fileName: "[project]/components/CreateForm.tsx",
                                        lineNumber: 294,
                                        columnNumber: 17
                                    }, this)
                                }, void 0, false, {
                                    fileName: "[project]/components/CreateForm.tsx",
                                    lineNumber: 293,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                                    label: "Singer voice",
                                    hint: "optional",
                                    htmlFor: "song-vocal",
                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        id: "song-vocal",
                                        className: "field-input",
                                        value: vocal,
                                        onChange: (e)=>setVocal(e.target.value),
                                        placeholder: "Breathy female pop vocal"
                                    }, void 0, false, {
                                        fileName: "[project]/components/CreateForm.tsx",
                                        lineNumber: 297,
                                        columnNumber: 17
                                    }, this)
                                }, void 0, false, {
                                    fileName: "[project]/components/CreateForm.tsx",
                                    lineNumber: 296,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 292,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "m-0 text-[13px] text-ink-soft",
                            children: "Describe a sound, not a real singer. Names of real artists get turned into a description of their style, because ElevenLabs won't imitate real voices."
                        }, void 0, false, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 300,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "flex flex-wrap items-center gap-2 border-t border-line pt-5",
                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                type: "submit",
                                variant: "primary",
                                loading: busy,
                                disabled: claudeMissing,
                                icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$music$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Music$3e$__["Music"], {
                                    className: "size-4"
                                }, void 0, false, {
                                    fileName: "[project]/components/CreateForm.tsx",
                                    lineNumber: 305,
                                    columnNumber: 101
                                }, this),
                                children: busy ? "Writing…" : "Write lyrics with Claude"
                            }, void 0, false, {
                                fileName: "[project]/components/CreateForm.tsx",
                                lineNumber: 305,
                                columnNumber: 15
                            }, this)
                        }, void 0, false, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 304,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Message"], {
                            text: msg.text || (claudeMissing ? "Claude isn't connected, so it can't write lyrics yet. Add your key to .env and restart the engine." : ""),
                            error: msg.error
                        }, void 0, false, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 309,
                            columnNumber: 13
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/components/CreateForm.tsx",
                    lineNumber: 260,
                    columnNumber: 11
                }, this),
                mode === "topic" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("form", {
                    onSubmit: write,
                    className: "grid gap-5 rounded-xl border border-line bg-panel p-5 sm:p-6",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                            label: "Topic",
                            htmlFor: "topic",
                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("textarea", {
                                id: "topic",
                                rows: 2,
                                required: true,
                                lang: lang,
                                value: topic,
                                onChange: (e)=>setTopic(e.target.value),
                                placeholder: PLACEHOLDER[lang],
                                className: "field-input resize-y py-3 text-lg leading-snug font-medium"
                            }, void 0, false, {
                                fileName: "[project]/components/CreateForm.tsx",
                                lineNumber: 319,
                                columnNumber: 15
                            }, this)
                        }, void 0, false, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 318,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "grid items-end gap-5 sm:grid-cols-[auto_1fr_1fr]",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "grid gap-1.5",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: "field-label",
                                            children: "Language"
                                        }, void 0, false, {
                                            fileName: "[project]/components/CreateForm.tsx",
                                            lineNumber: 333,
                                            columnNumber: 17
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Segmented"], {
                                            name: "lang",
                                            value: lang,
                                            onChange: setLang,
                                            options: [
                                                {
                                                    value: "en",
                                                    label: "English"
                                                },
                                                {
                                                    value: "km",
                                                    label: "ខ្មែរ",
                                                    lang: "km"
                                                }
                                            ]
                                        }, void 0, false, {
                                            fileName: "[project]/components/CreateForm.tsx",
                                            lineNumber: 334,
                                            columnNumber: 17
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/CreateForm.tsx",
                                    lineNumber: 332,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                                    label: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                                        children: [
                                            "Length ",
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("output", {
                                                className: "ml-1 font-semibold text-ink",
                                                children: [
                                                    seconds,
                                                    " s"
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/components/CreateForm.tsx",
                                                lineNumber: 344,
                                                columnNumber: 38
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/components/CreateForm.tsx",
                                        lineNumber: 344,
                                        columnNumber: 29
                                    }, this),
                                    htmlFor: "seconds",
                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        id: "seconds",
                                        type: "range",
                                        min: 15,
                                        max: 90,
                                        step: 5,
                                        value: seconds,
                                        onChange: (e)=>setSeconds(+e.target.value),
                                        className: "h-10 w-full accent-cobalt"
                                    }, void 0, false, {
                                        fileName: "[project]/components/CreateForm.tsx",
                                        lineNumber: 345,
                                        columnNumber: 17
                                    }, this)
                                }, void 0, false, {
                                    fileName: "[project]/components/CreateForm.tsx",
                                    lineNumber: 344,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                                    label: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                                        children: [
                                            "Scenes ",
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("output", {
                                                className: "ml-1 font-semibold text-ink",
                                                children: scenes
                                            }, void 0, false, {
                                                fileName: "[project]/components/CreateForm.tsx",
                                                lineNumber: 347,
                                                columnNumber: 38
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/components/CreateForm.tsx",
                                        lineNumber: 347,
                                        columnNumber: 29
                                    }, this),
                                    htmlFor: "scenes",
                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        id: "scenes",
                                        type: "range",
                                        min: 3,
                                        max: 10,
                                        value: scenes,
                                        onChange: (e)=>setScenes(+e.target.value),
                                        className: "h-10 w-full accent-cobalt"
                                    }, void 0, false, {
                                        fileName: "[project]/components/CreateForm.tsx",
                                        lineNumber: 348,
                                        columnNumber: 17
                                    }, this)
                                }, void 0, false, {
                                    fileName: "[project]/components/CreateForm.tsx",
                                    lineNumber: 347,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 331,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                            label: "Tone or audience",
                            hint: "optional",
                            htmlFor: "style",
                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                id: "style",
                                className: "field-input",
                                value: style,
                                onChange: (e)=>setStyle(e.target.value),
                                placeholder: "Funny, for teenagers. Mention a local example."
                            }, void 0, false, {
                                fileName: "[project]/components/CreateForm.tsx",
                                lineNumber: 353,
                                columnNumber: 15
                            }, this)
                        }, void 0, false, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 352,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "flex flex-wrap items-center gap-2 border-t border-line pt-5",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                    type: "submit",
                                    variant: "primary",
                                    loading: busy,
                                    disabled: claudeMissing,
                                    icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$sparkles$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Sparkles$3e$__["Sparkles"], {
                                        className: "size-4"
                                    }, void 0, false, {
                                        fileName: "[project]/components/CreateForm.tsx",
                                        lineNumber: 357,
                                        columnNumber: 101
                                    }, this),
                                    children: busy ? "Writing…" : "Write script with Claude"
                                }, void 0, false, {
                                    fileName: "[project]/components/CreateForm.tsx",
                                    lineNumber: 357,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                    variant: "ghost",
                                    onClick: blank,
                                    icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$pen$2d$line$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__PenLine$3e$__["PenLine"], {
                                        className: "size-4"
                                    }, void 0, false, {
                                        fileName: "[project]/components/CreateForm.tsx",
                                        lineNumber: 360,
                                        columnNumber: 61
                                    }, this),
                                    children: "Write it myself"
                                }, void 0, false, {
                                    fileName: "[project]/components/CreateForm.tsx",
                                    lineNumber: 360,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 356,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Message"], {
                            text: msg.text || (claudeMissing ? "Claude isn't connected, so it can't write scripts yet. Use “Write it myself”, or add your key to .env and restart the engine." : ""),
                            error: msg.error
                        }, void 0, false, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 364,
                            columnNumber: 13
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/components/CreateForm.tsx",
                    lineNumber: 317,
                    columnNumber: 11
                }, this),
                mode === "paste" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("form", {
                    onSubmit: importPasted,
                    className: "grid gap-4 rounded-xl border border-line bg-panel p-5 sm:p-6",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                            label: "Script",
                            htmlFor: "pasted",
                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("textarea", {
                                id: "pasted",
                                rows: 14,
                                required: true,
                                value: pasted,
                                onChange: (e)=>setPasted(e.target.value),
                                placeholder: PASTE_EXAMPLE,
                                className: "field-input resize-y font-mono text-[13px] leading-relaxed"
                            }, void 0, false, {
                                fileName: "[project]/components/CreateForm.tsx",
                                lineNumber: 377,
                                columnNumber: 15
                            }, this)
                        }, void 0, false, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 376,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "m-0 text-[13px] text-ink-soft",
                            children: "English or ខ្មែរ, any layout. Voiceover is kept word for word, visual notes become footage searches, and extra notes like production tips are ignored. Emojis are removed from on-screen text."
                        }, void 0, false, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 387,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "flex flex-wrap items-center gap-2 border-t border-line pt-5",
                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                type: "submit",
                                variant: "primary",
                                loading: importing,
                                icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$clipboard$2d$paste$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ClipboardPaste$3e$__["ClipboardPaste"], {
                                    className: "size-4"
                                }, void 0, false, {
                                    fileName: "[project]/components/CreateForm.tsx",
                                    lineNumber: 392,
                                    columnNumber: 81
                                }, this),
                                children: importing ? "Importing…" : "Import script"
                            }, void 0, false, {
                                fileName: "[project]/components/CreateForm.tsx",
                                lineNumber: 392,
                                columnNumber: 15
                            }, this)
                        }, void 0, false, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 391,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Message"], {
                            ...importMsg
                        }, void 0, false, {
                            fileName: "[project]/components/CreateForm.tsx",
                            lineNumber: 396,
                            columnNumber: 13
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/components/CreateForm.tsx",
                    lineNumber: 375,
                    columnNumber: 11
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/components/CreateForm.tsx",
            lineNumber: 223,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/components/CreateForm.tsx",
        lineNumber: 222,
        columnNumber: 5
    }, this);
}
_s1(CreateForm, "Wqs90MP9tTpVlXqewob7lDbU/k4=");
_c1 = CreateForm;
var _c, _c1;
__turbopack_context__.k.register(_c, "OwnSongForm");
__turbopack_context__.k.register(_c1, "CreateForm");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/Library.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "Library",
    ()=>Library
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$file$2d$text$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__FileText$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/file-text.mjs [app-client] (ecmascript) <export default as FileText>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$film$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Film$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/film.mjs [app-client] (ecmascript) <export default as Film>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$music$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Music$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/music.mjs [app-client] (ecmascript) <export default as Music>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$plus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Plus$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/plus.mjs [app-client] (ecmascript) <export default as Plus>");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$format$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/format.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/ui.tsx [app-client] (ecmascript)");
"use client";
;
;
;
;
;
function Row({ current, onClick, thumb, title, lang, meta }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
            type: "button",
            "aria-current": current || undefined,
            onClick: onClick,
            className: `grid w-full cursor-pointer grid-cols-[36px_minmax(0,1fr)] items-center gap-3 rounded-lg border-0 p-2 text-left transition-colors ${current ? "bg-panel shadow-[inset_3px_0_0_var(--color-cobalt),0_1px_2px_rgb(24_32_46/0.06)]" : "bg-transparent hover:bg-ink/[0.04]"}`,
            children: [
                thumb,
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                    className: "min-w-0",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                            lang: lang,
                            className: "line-clamp-2 text-[13.5px] leading-snug font-semibold text-ink",
                            children: title
                        }, void 0, false, {
                            fileName: "[project]/components/Library.tsx",
                            lineNumber: 37,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                            className: "mt-0.5 flex items-center gap-1.5 text-xs text-ink-soft",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    lang: lang === "km" ? "km" : undefined,
                                    className: "rounded bg-ink/[0.06] px-1 leading-4 font-semibold",
                                    children: (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$format$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["langCode"])(lang)
                                }, void 0, false, {
                                    fileName: "[project]/components/Library.tsx",
                                    lineNumber: 41,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    className: "truncate",
                                    children: meta
                                }, void 0, false, {
                                    fileName: "[project]/components/Library.tsx",
                                    lineNumber: 44,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/Library.tsx",
                            lineNumber: 40,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/components/Library.tsx",
                    lineNumber: 36,
                    columnNumber: 9
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/components/Library.tsx",
            lineNumber: 27,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/components/Library.tsx",
        lineNumber: 26,
        columnNumber: 5
    }, this);
}
_c = Row;
function Thumb({ src, fallback }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
        className: "grid aspect-[9/16] w-9 place-items-center overflow-hidden rounded-md bg-ink/[0.08] bg-cover bg-center text-ink-soft",
        style: src ? {
            backgroundImage: `url('${src}')`
        } : undefined,
        children: !src && fallback
    }, void 0, false, {
        fileName: "[project]/components/Library.tsx",
        lineNumber: 54,
        columnNumber: 5
    }, this);
}
_c1 = Thumb;
function Empty({ icon, text }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
        className: "grid justify-items-center gap-2 px-4 py-10 text-center text-[13px] text-ink-soft",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                className: "grid size-10 place-items-center rounded-full bg-ink/[0.06]",
                children: icon
            }, void 0, false, {
                fileName: "[project]/components/Library.tsx",
                lineNumber: 66,
                columnNumber: 7
            }, this),
            text
        ]
    }, void 0, true, {
        fileName: "[project]/components/Library.tsx",
        lineNumber: 65,
        columnNumber: 5
    }, this);
}
_c2 = Empty;
function Library({ tab, onTab, drafts, videos, selectedDraft, selectedVideo, onSelectDraft, onSelectSong, onSelectVideo, onNew }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "flex h-full min-h-0 flex-col",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid gap-3 px-4 pt-4",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                        variant: "primary",
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$plus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Plus$3e$__["Plus"], {
                            className: "size-4"
                        }, void 0, false, {
                            fileName: "[project]/components/Library.tsx",
                            lineNumber: 98,
                            columnNumber: 41
                        }, this),
                        onClick: onNew,
                        className: "w-full",
                        children: "New video"
                    }, void 0, false, {
                        fileName: "[project]/components/Library.tsx",
                        lineNumber: 98,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Tabs"], {
                        label: "Library",
                        value: tab,
                        onChange: onTab,
                        items: [
                            {
                                value: "drafts",
                                label: "Drafts",
                                count: drafts?.length
                            },
                            {
                                value: "videos",
                                label: "Videos",
                                count: videos?.length
                            }
                        ]
                    }, void 0, false, {
                        fileName: "[project]/components/Library.tsx",
                        lineNumber: 101,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/Library.tsx",
                lineNumber: 97,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                className: "m-0 grid min-h-0 flex-1 list-none content-start gap-0.5 overflow-y-auto p-2",
                children: [
                    tab === "drafts" && (drafts === null ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                        className: "p-4 text-[13px] text-ink-soft",
                        children: "Loading…"
                    }, void 0, false, {
                        fileName: "[project]/components/Library.tsx",
                        lineNumber: 115,
                        columnNumber: 13
                    }, this) : drafts.length === 0 ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Empty, {
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$file$2d$text$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__FileText$3e$__["FileText"], {
                            className: "size-5"
                        }, void 0, false, {
                            fileName: "[project]/components/Library.tsx",
                            lineNumber: 117,
                            columnNumber: 26
                        }, this),
                        text: "Scripts you write or paste, and songs you add, are saved here automatically."
                    }, void 0, false, {
                        fileName: "[project]/components/Library.tsx",
                        lineNumber: 117,
                        columnNumber: 13
                    }, this) : drafts.map((d)=>d.kind === "song" ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Row, {
                            current: d.id === selectedDraft,
                            onClick: ()=>onSelectSong(d.id),
                            title: d.title,
                            lang: d.lang,
                            meta: `song, ${d.versions ? `${d.versions} video${d.versions === 1 ? "" : "s"}` : "no video yet"}, ${(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$format$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["relativeTime"])(d.updated)}`,
                            thumb: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Thumb, {
                                src: d.thumb ? `${(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["outputUrl"])(d.thumb, "thumbnail.jpg")}?v=${d.thumb_v ?? 0}` : undefined,
                                fallback: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$music$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Music$3e$__["Music"], {
                                    className: "size-4"
                                }, void 0, false, {
                                    fileName: "[project]/components/Library.tsx",
                                    lineNumber: 128,
                                    columnNumber: 132
                                }, this)
                            }, void 0, false, {
                                fileName: "[project]/components/Library.tsx",
                                lineNumber: 128,
                                columnNumber: 26
                            }, this)
                        }, d.id, false, {
                            fileName: "[project]/components/Library.tsx",
                            lineNumber: 121,
                            columnNumber: 17
                        }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Row, {
                            current: d.id === selectedDraft,
                            onClick: ()=>onSelectDraft(d.id),
                            title: d.title,
                            lang: d.lang,
                            meta: `${d.scenes} scene${d.scenes === 1 ? "" : "s"}, ${(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$format$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["relativeTime"])(d.updated)}`,
                            thumb: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Thumb, {
                                src: d.cover && (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$format$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["isImagePath"])(d.cover) ? (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fileUrl"])(d.cover) : undefined,
                                fallback: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$file$2d$text$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__FileText$3e$__["FileText"], {
                                    className: "size-4"
                                }, void 0, false, {
                                    fileName: "[project]/components/Library.tsx",
                                    lineNumber: 138,
                                    columnNumber: 112
                                }, this)
                            }, void 0, false, {
                                fileName: "[project]/components/Library.tsx",
                                lineNumber: 138,
                                columnNumber: 26
                            }, this)
                        }, d.id, false, {
                            fileName: "[project]/components/Library.tsx",
                            lineNumber: 131,
                            columnNumber: 17
                        }, this))),
                    tab === "videos" && (videos === null ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                        className: "p-4 text-[13px] text-ink-soft",
                        children: "Loading…"
                    }, void 0, false, {
                        fileName: "[project]/components/Library.tsx",
                        lineNumber: 145,
                        columnNumber: 13
                    }, this) : videos.length === 0 ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Empty, {
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$film$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Film$3e$__["Film"], {
                            className: "size-5"
                        }, void 0, false, {
                            fileName: "[project]/components/Library.tsx",
                            lineNumber: 147,
                            columnNumber: 26
                        }, this),
                        text: "Videos you render appear here."
                    }, void 0, false, {
                        fileName: "[project]/components/Library.tsx",
                        lineNumber: 147,
                        columnNumber: 13
                    }, this) : videos.map((v)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Row, {
                            current: v.name === selectedVideo,
                            onClick: ()=>onSelectVideo(v.name),
                            title: v.title,
                            lang: v.lang,
                            meta: v.video || v.audio ? `${v.kind === "music_video" ? "music video, " : v.kind === "song" ? "song, " : ""}${(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$format$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["relativeTime"])(v.created)}` : "script only",
                            thumb: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Thumb, {
                                src: v.thumb ? `${(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["outputUrl"])(v.name, "thumbnail.jpg")}?v=${v.thumb_v}` : undefined,
                                fallback: v.kind !== "video" ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$music$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Music$3e$__["Music"], {
                                    className: "size-4"
                                }, void 0, false, {
                                    fileName: "[project]/components/Library.tsx",
                                    lineNumber: 160,
                                    columnNumber: 52
                                }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$film$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Film$3e$__["Film"], {
                                    className: "size-4"
                                }, void 0, false, {
                                    fileName: "[project]/components/Library.tsx",
                                    lineNumber: 160,
                                    columnNumber: 83
                                }, this)
                            }, void 0, false, {
                                fileName: "[project]/components/Library.tsx",
                                lineNumber: 158,
                                columnNumber: 19
                            }, this)
                        }, v.name, false, {
                            fileName: "[project]/components/Library.tsx",
                            lineNumber: 150,
                            columnNumber: 15
                        }, this)))
                ]
            }, void 0, true, {
                fileName: "[project]/components/Library.tsx",
                lineNumber: 112,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/Library.tsx",
        lineNumber: 96,
        columnNumber: 5
    }, this);
}
_c3 = Library;
var _c, _c1, _c2, _c3;
__turbopack_context__.k.register(_c, "Row");
__turbopack_context__.k.register(_c1, "Thumb");
__turbopack_context__.k.register(_c2, "Empty");
__turbopack_context__.k.register(_c3, "Library");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/LyricsTiming.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "LyricsTiming",
    ()=>LyricsTiming
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$check$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Check$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/check.mjs [app-client] (ecmascript) <export default as Check>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$chevron$2d$down$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ChevronDown$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/chevron-down.mjs [app-client] (ecmascript) <export default as ChevronDown>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$chevron$2d$left$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ChevronLeft$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/chevron-left.mjs [app-client] (ecmascript) <export default as ChevronLeft>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$circle$2d$alert$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__CircleAlert$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/circle-alert.mjs [app-client] (ecmascript) <export default as CircleAlert>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$crosshair$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Crosshair$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/crosshair.mjs [app-client] (ecmascript) <export default as Crosshair>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$film$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Film$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/film.mjs [app-client] (ecmascript) <export default as Film>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$list$2d$plus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ListPlus$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/list-plus.mjs [app-client] (ecmascript) <export default as ListPlus>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$minus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Minus$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/minus.mjs [app-client] (ecmascript) <export default as Minus>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$pause$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Pause$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/pause.mjs [app-client] (ecmascript) <export default as Pause>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$play$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Play$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/play.mjs [app-client] (ecmascript) <export default as Play>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$plus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Plus$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/plus.mjs [app-client] (ecmascript) <export default as Plus>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$refresh$2d$cw$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__RefreshCw$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/refresh-cw.mjs [app-client] (ecmascript) <export default as RefreshCw>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$trash$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Trash2$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/trash.mjs [app-client] (ecmascript) <export default as Trash2>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$undo$2d$2$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Undo2$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/undo-2.mjs [app-client] (ecmascript) <export default as Undo2>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/ui.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$MusicVideoOptions$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/MusicVideoOptions.tsx [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature(), _s1 = __turbopack_context__.k.signature();
"use client";
;
;
;
;
;
const fmt = (t, digits = 1)=>{
    const m = Math.floor(Math.max(0, t) / 60);
    const s = Math.max(0, t) - m * 60;
    return `${m}:${s.toFixed(digits).padStart(digits + 3, "0")}`;
};
/** "1:23.45", "83.45" or "1:23" -> seconds; null when it isn't a time. */ function parseTime(text) {
    const m = text.trim().match(/^(?:(\d+):)?(\d+(?:[.,]\d*)?)$/);
    if (!m) return null;
    return (m[1] ? Number(m[1]) * 60 : 0) + Number(m[2].replace(",", "."));
}
const lineStart = (l)=>l.words[0]?.start ?? 0;
const lineEnd = (l)=>l.words[l.words.length - 1]?.end ?? 0;
const round = (t)=>Math.round(t * 100) / 100;
const byStart = (a, b)=>lineStart(a) - lineStart(b);
const GAP = 0.05; // smallest pause kept between two lines
let uidCounter = 0;
const newUid = ()=>`l${++uidCounter}`;
function shift(line, by) {
    const by2 = Math.max(by, -lineStart(line)); // never before 0:00
    return {
        ...line,
        words: line.words.map((w)=>({
                ...w,
                start: round(w.start + by2),
                end: round(w.end + by2)
            }))
    };
}
/** Stretch the line's words to fit [start, end], keeping their relative timing. */ function respan(line, start, end) {
    const s0 = lineStart(line);
    const k = (end - start) / Math.max(lineEnd(line) - s0, 0.01);
    return {
        ...line,
        words: line.words.map((w)=>({
                ...w,
                start: round(start + (w.start - s0) * k),
                end: round(start + (w.end - s0) * k)
            }))
    };
}
/** Keep lines in order and never overlapping after line `uid` changed: the line before it is cut short where it
 * now starts, and lines after it that it now runs into are pushed later (each just enough to clear the one before). */ function settle(ls, uid) {
    const out = [
        ...ls
    ].sort(byStart);
    const i = out.findIndex((l)=>l.uid === uid);
    if (i < 0) return out;
    const prev = out[i - 1];
    if (prev && lineEnd(prev) > lineStart(out[i]) - GAP) {
        const end = Math.max(lineStart(out[i]) - GAP, lineStart(prev) + 0.3);
        out[i - 1] = respan(prev, lineStart(prev), end);
        if (lineEnd(out[i - 1]) > lineStart(out[i]) - GAP) out[i] = shift(out[i], lineEnd(out[i - 1]) + GAP - lineStart(out[i]));
    }
    for(let j = i + 1; j < out.length; j++){
        const need = round(lineEnd(out[j - 1]) + GAP - lineStart(out[j]));
        if (need <= 0) break; // from here on the lines were already in order
        out[j] = shift(out[j], need);
    }
    return out;
}
/** Spread `text`'s words over [start, end], longer words getting more time. */ function spread(text, start, end) {
    const tokens = text.trim().split(/\s+/).filter(Boolean);
    const span = Math.max(end - start, 0.2);
    const total = tokens.reduce((n, t)=>n + t.length + 1, 0);
    let t = start;
    return tokens.map((tok)=>{
        const len = span * (tok.length + 1) / total;
        const w = {
            text: tok,
            start: round(t),
            end: round(t + len)
        };
        t += len;
        return w;
    });
}
/** New text: spread its words over the line's current span. */ function retext(line, text) {
    const words = spread(text, lineStart(line), lineEnd(line));
    return words.length ? {
        ...line,
        text,
        words
    } : {
        ...line,
        text
    };
}
/** Word `i` starts at `t`: the word before it ends there, so the highlight moves on without a gap. */ function setWordStart(line, i, t) {
    const words = line.words.map((w)=>({
            ...w
        }));
    const lo = i > 0 ? words[i - 1].start + 0.02 : 0;
    const hi = words[i].end - 0.02;
    const at = round(Math.min(Math.max(t, lo), hi));
    words[i].start = at;
    if (i > 0) words[i - 1].end = at;
    return {
        ...line,
        words,
        check: false
    };
}
function setLastWordEnd(line, t) {
    const words = line.words.map((w)=>({
            ...w
        }));
    const last = words[words.length - 1];
    last.end = round(Math.max(t, last.start + 0.05));
    return {
        ...line,
        words,
        check: false
    };
}
/** A time you can type ("1:23.45" or seconds). Commits on Enter or when it loses focus; Escape cancels. */ function TimeInput({ value, onCommit, label, className = "" }) {
    _s();
    const [text, setText] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null); // null = not being edited, show the value
    const [bad, setBad] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const commit = ()=>{
        if (text === null) return;
        const t = parseTime(text);
        if (t === null) {
            setBad(true);
            return;
        }
        setText(null);
        setBad(false);
        if (Math.abs(t - value) >= 0.005) onCommit(t);
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
        "aria-label": label,
        title: `${label}: type a time like 1:23.45`,
        inputMode: "decimal",
        value: text ?? fmt(value, 2),
        onFocus: (e)=>{
            setText(fmt(value, 2));
            e.currentTarget.select();
        },
        onChange: (e)=>{
            setText(e.target.value);
            setBad(false);
        },
        onBlur: ()=>{
            commit();
            setText(null);
            setBad(false);
        },
        onKeyDown: (e)=>{
            if (e.key === "Enter") commit();
            if (e.key === "Escape") {
                setText(null);
                setBad(false);
                e.currentTarget.blur();
            }
        },
        className: `h-7 w-[4.6rem] rounded-md border bg-panel px-1.5 text-center font-mono text-[12.5px] tabular-nums text-ink focus:border-cobalt focus:outline-none ${bad ? "border-danger" : "border-line"} ${className}`
    }, void 0, false, {
        fileName: "[project]/components/LyricsTiming.tsx",
        lineNumber: 117,
        columnNumber: 5
    }, this);
}
_s(TimeInput, "jYcTQ905G04XUkxxs4G70N7leaA=");
_c = TimeInput;
function LyricsTiming({ name, title, lang, aspect, sections, settings: initialSettings, busy, onBack, onResync, onMakeVideo }) {
    _s1();
    const [settings, setSettings] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(initialSettings);
    const [making, setMaking] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false); // the "make music video" panel is open
    const [lines, setLines] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [method, setMethod] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [loadError, setLoadError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [save, setSave] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("idle");
    const [error, setError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [now, setNow] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(0);
    const [playing, setPlaying] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [follow, setFollow] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(true);
    const [ripple, setRipple] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(true); // retiming a line moves every line after it by the same amount
    const [confirmResync, setConfirmResync] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [open, setOpen] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(new Set()); // lines showing their words
    const [fresh, setFresh] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null); // just-added line: focus its text
    const [deleted, setDeleted] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const audio = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    const list = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    const dirty = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(false);
    const pending = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(Promise.resolve());
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "LyricsTiming.useEffect": ()=>{
            let cancelled = false;
            __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].lyrics(name).then({
                "LyricsTiming.useEffect": (d)=>{
                    if (cancelled) return;
                    setLines((d.lines ?? []).map({
                        "LyricsTiming.useEffect": (l)=>({
                                ...l,
                                uid: newUid()
                            })
                    }["LyricsTiming.useEffect"]));
                    setMethod(d.timing);
                }
            }["LyricsTiming.useEffect"]).catch({
                "LyricsTiming.useEffect": (e)=>!cancelled && setLoadError(e.message)
            }["LyricsTiming.useEffect"]);
            return ({
                "LyricsTiming.useEffect": ()=>{
                    cancelled = true;
                }
            })["LyricsTiming.useEffect"];
        }
    }["LyricsTiming.useEffect"], [
        name
    ]);
    const toSave = (ls)=>ls.map((l)=>({
                section: l.section,
                text: l.text,
                words: l.words,
                check: !!l.check
            }));
    // Autosave shortly after each change; the music video always uses the latest saved timing.
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "LyricsTiming.useEffect": ()=>{
            if (!lines || !dirty.current) return;
            const timer = setTimeout({
                "LyricsTiming.useEffect.timer": ()=>{
                    setSave("saving");
                    pending.current = __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].saveLyrics(name, toSave(lines)).then({
                        "LyricsTiming.useEffect.timer": ()=>{
                            dirty.current = false;
                            setSave("saved");
                            setMethod("edited");
                        }
                    }["LyricsTiming.useEffect.timer"]).catch({
                        "LyricsTiming.useEffect.timer": ()=>setSave("error")
                    }["LyricsTiming.useEffect.timer"]);
                }
            }["LyricsTiming.useEffect.timer"], 700);
            return ({
                "LyricsTiming.useEffect": ()=>clearTimeout(timer)
            })["LyricsTiming.useEffect"];
        }
    }["LyricsTiming.useEffect"], [
        lines,
        name
    ]);
    const edit = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "LyricsTiming.useCallback[edit]": (update)=>{
            dirty.current = true;
            setSave("idle");
            setLines({
                "LyricsTiming.useCallback[edit]": (ls)=>ls ? update(ls) : ls
            }["LyricsTiming.useCallback[edit]"]);
        }
    }["LyricsTiming.useCallback[edit]"], []);
    /** Change a line's timing. With `ripple` on, every line after it moves by as much as its start (or end) moved. */ const retime = (uid, update, edge)=>edit((ls)=>{
            const i = ls.findIndex((l)=>l.uid === uid);
            if (i < 0) return ls;
            const next = {
                ...update(ls[i]),
                check: false
            }; // retimed by hand = checked
            let by = round(edge === "start" ? lineStart(next) - lineStart(ls[i]) : lineEnd(next) - lineEnd(ls[i]));
            // moving earlier: the lines after keep their spacing, so they stop when the first of them reaches 0:00
            if (ls[i + 1]) by = Math.max(by, -lineStart(ls[i + 1]));
            return settle(ls.map((l, j)=>j === i ? next : ripple && j > i && by ? shift(l, by) : l), uid);
        });
    /** Line starts at `t`: with ripple the whole line moves there (keeping its length), else it stretches to its end. */ const startAt = (uid, t)=>retime(uid, (l)=>ripple ? shift(l, t - lineStart(l)) : respan(l, t, Math.max(lineEnd(l), t + 0.3)), "start");
    const endAt = (uid, t)=>retime(uid, (l)=>respan(l, lineStart(l), Math.max(t, lineStart(l) + 0.3)), "end");
    const editLine = (uid, update)=>edit((ls)=>settle(ls.map((l)=>l.uid === uid ? update(l) : l), uid));
    /** Insert a line with placeholder text sung over [start, end], in the section of the line before it. */ const addLine = (start, end)=>{
        const uid = newUid();
        edit((ls)=>{
            const before = ls.filter((l)=>lineStart(l) <= start).at(-1) ?? ls[0];
            const text = "New line";
            // fit into the pause before the next line when there is room for it
            const nextStart = ls.find((l)=>lineStart(l) > start)?.words[0].start ?? Infinity;
            const fit = Math.min(end, nextStart - GAP);
            const row = {
                uid,
                section: before?.section ?? 0,
                text,
                words: spread(text, round(start), round(fit - start >= 0.6 ? fit : end))
            };
            return settle([
                ...ls,
                row
            ], uid);
        });
        setFresh(uid);
        setDeleted(null);
    };
    const addAfter = (i)=>{
        if (!lines) return;
        const start = lineEnd(lines[i]) + 0.2;
        const next = lines[i + 1] ? lineStart(lines[i + 1]) - 0.1 : start + 2;
        addLine(start, Math.max(start + 0.6, Math.min(start + 2, next)));
    };
    const removeLine = (i)=>{
        if (!lines) return;
        setDeleted({
            row: lines[i],
            index: i
        });
        edit((ls)=>ls.filter((_, j)=>j !== i));
    };
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "LyricsTiming.useEffect": ()=>{
            if (!fresh) return;
            const input = list.current?.querySelector(`[data-line-text="${fresh}"]`);
            if (input) {
                input.scrollIntoView({
                    block: "center",
                    behavior: "smooth"
                });
                input.focus();
                input.select();
                setFresh(null);
            }
        }
    }["LyricsTiming.useEffect"], [
        fresh,
        lines
    ]);
    // Playhead: smooth while playing (the timeupdate event only fires ~4 times a second).
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "LyricsTiming.useEffect": ()=>{
            if (!playing) return;
            let raf = 0;
            const tick = {
                "LyricsTiming.useEffect.tick": ()=>{
                    if (audio.current) setNow(audio.current.currentTime);
                    raf = requestAnimationFrame(tick);
                }
            }["LyricsTiming.useEffect.tick"];
            raf = requestAnimationFrame(tick);
            return ({
                "LyricsTiming.useEffect": ()=>cancelAnimationFrame(raf)
            })["LyricsTiming.useEffect"];
        }
    }["LyricsTiming.useEffect"], [
        playing
    ]);
    const active = lines ? lines.findLastIndex((l)=>lineStart(l) - 0.3 <= now && now <= lineEnd(l) + 0.6) : -1;
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "LyricsTiming.useEffect": ()=>{
            if (!follow || !playing || active < 0) return;
            list.current?.querySelector(`[data-line="${active}"]`)?.scrollIntoView({
                block: "center",
                behavior: "smooth"
            });
        }
    }["LyricsTiming.useEffect"], [
        active,
        follow,
        playing
    ]);
    const seek = (t, play = true)=>{
        const a = audio.current;
        if (!a) return;
        a.currentTime = Math.max(0, t);
        setNow(a.currentTime);
        if (play) void a.play();
    };
    const nowLine = active >= 0 && lines ? lines[active] : null;
    const toCheck = lines?.filter((l)=>l.check) ?? [];
    /** Play the next line the sync wasn't sure about (after the playhead, else from the top). */ const playNextToCheck = ()=>{
        const next = toCheck.find((l)=>lineStart(l) > now + 0.5) ?? toCheck[0];
        if (!next) return;
        list.current?.querySelector(`[data-line-text="${next.uid}"]`)?.scrollIntoView({
            block: "center",
            behavior: "smooth"
        });
        seek(lineStart(next) - 1.5);
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "flex h-full min-h-0 flex-col",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("header", {
                className: "flex h-14 shrink-0 items-center gap-2 border-b border-line bg-panel px-3 sm:px-5",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                        label: "Back to start",
                        onClick: onBack,
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$chevron$2d$left$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ChevronLeft$3e$__["ChevronLeft"], {
                            className: "size-5"
                        }, void 0, false, {
                            fileName: "[project]/components/LyricsTiming.tsx",
                            lineNumber: 332,
                            columnNumber: 11
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/components/LyricsTiming.tsx",
                        lineNumber: 331,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "min-w-0 flex-1 truncate text-sm font-semibold",
                        lang: lang,
                        children: title
                    }, void 0, false, {
                        fileName: "[project]/components/LyricsTiming.tsx",
                        lineNumber: 334,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "hidden text-[13px] text-ink-soft sm:inline",
                        "aria-live": "polite",
                        children: save === "saving" ? "Saving…" : save === "saved" ? "Timing saved" : save === "error" ? "Couldn't save" : ""
                    }, void 0, false, {
                        fileName: "[project]/components/LyricsTiming.tsx",
                        lineNumber: 337,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                        variant: "primary",
                        size: "sm",
                        loading: busy,
                        disabled: !lines?.length,
                        "aria-expanded": making,
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$film$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Film$3e$__["Film"], {
                            className: "size-3.5"
                        }, void 0, false, {
                            fileName: "[project]/components/LyricsTiming.tsx",
                            lineNumber: 346,
                            columnNumber: 17
                        }, this),
                        onClick: ()=>setMaking((m)=>!m),
                        children: [
                            "Make ",
                            aspect === "16:9" ? "16:9" : "9:16",
                            " music video"
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/LyricsTiming.tsx",
                        lineNumber: 340,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/LyricsTiming.tsx",
                lineNumber: 330,
                columnNumber: 7
            }, this),
            making && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "max-h-[62vh] shrink-0 overflow-y-auto border-b border-line bg-panel px-4 py-3 sm:px-8",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "mx-auto grid max-w-[760px] gap-2",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$MusicVideoOptions$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["MusicVideoOptions"], {
                            name: name,
                            lang: lang,
                            aspect: aspect,
                            sample: lines?.find((l)=>l.text.trim())?.text ?? title,
                            value: settings,
                            onChange: setSettings
                        }, void 0, false, {
                            fileName: "[project]/components/LyricsTiming.tsx",
                            lineNumber: 356,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "flex justify-end gap-2",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                    size: "sm",
                                    variant: "ghost",
                                    onClick: ()=>setMaking(false),
                                    children: "Cancel"
                                }, void 0, false, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 365,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                    size: "sm",
                                    variant: "primary",
                                    loading: busy,
                                    icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$film$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Film$3e$__["Film"], {
                                        className: "size-3.5"
                                    }, void 0, false, {
                                        fileName: "[project]/components/LyricsTiming.tsx",
                                        lineNumber: 372,
                                        columnNumber: 23
                                    }, this),
                                    onClick: async ()=>{
                                        setError("");
                                        await pending.current;
                                        if (dirty.current && lines) await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].saveLyrics(name, toSave(lines)).catch(()=>undefined);
                                        const err = await onMakeVideo(settings);
                                        if (err) setError(err);
                                        else setMaking(false);
                                    },
                                    children: "Make video"
                                }, void 0, false, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 368,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/LyricsTiming.tsx",
                            lineNumber: 364,
                            columnNumber: 13
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/components/LyricsTiming.tsx",
                    lineNumber: 355,
                    columnNumber: 11
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/LyricsTiming.tsx",
                lineNumber: 354,
                columnNumber: 9
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "shrink-0 border-b border-line bg-[#141a26] px-4 py-4 text-white sm:px-8",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "mx-auto grid max-w-[760px] gap-3",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            lang: lang,
                            className: "m-0 min-h-[2.6em] text-center font-display text-[clamp(18px,2.4vw,26px)] leading-snug font-bold",
                            children: nowLine ? nowLine.words.map((w, i)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    className: w.start <= now ? "text-caption" : "text-white",
                                    children: [
                                        w.text,
                                        " "
                                    ]
                                }, i, true, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 395,
                                    columnNumber: 17
                                }, this)) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "text-white/40",
                                children: playing ? "♪" : "Play the song to check the timing"
                            }, void 0, false, {
                                fileName: "[project]/components/LyricsTiming.tsx",
                                lineNumber: 400,
                                columnNumber: 15
                            }, this)
                        }, void 0, false, {
                            fileName: "[project]/components/LyricsTiming.tsx",
                            lineNumber: 392,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "flex items-center gap-3",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                                    label: playing ? "Pause" : "Play",
                                    className: "size-10 bg-white/10 text-white hover:bg-white/20 hover:text-white",
                                    onClick: ()=>audio.current?.paused ? void audio.current.play() : audio.current?.pause(),
                                    children: playing ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$pause$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Pause$3e$__["Pause"], {
                                        className: "size-5"
                                    }, void 0, false, {
                                        fileName: "[project]/components/LyricsTiming.tsx",
                                        lineNumber: 409,
                                        columnNumber: 26
                                    }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$play$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Play$3e$__["Play"], {
                                        className: "size-5"
                                    }, void 0, false, {
                                        fileName: "[project]/components/LyricsTiming.tsx",
                                        lineNumber: 409,
                                        columnNumber: 57
                                    }, this)
                                }, void 0, false, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 404,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("audio", {
                                    ref: audio,
                                    src: (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["outputUrl"])(name, "song.mp3"),
                                    controls: true,
                                    className: "h-10 min-w-0 flex-1",
                                    onPlay: ()=>setPlaying(true),
                                    onPause: ()=>setPlaying(false),
                                    onSeeked: (e)=>setNow(e.currentTarget.currentTime),
                                    onTimeUpdate: (e)=>!playing && setNow(e.currentTarget.currentTime)
                                }, void 0, false, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 411,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    className: "w-14 text-right font-mono text-sm tabular-nums text-white/70",
                                    children: fmt(now)
                                }, void 0, false, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 421,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/LyricsTiming.tsx",
                            lineNumber: 403,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/components/LyricsTiming.tsx",
                    lineNumber: 391,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/LyricsTiming.tsx",
                lineNumber: 390,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "min-h-0 flex-1 overflow-y-auto",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "mx-auto grid max-w-[760px] gap-4 px-4 py-5 sm:px-8",
                    children: [
                        loadError && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Message"], {
                            text: loadError,
                            error: true
                        }, void 0, false, {
                            fileName: "[project]/components/LyricsTiming.tsx",
                            lineNumber: 428,
                            columnNumber: 25
                        }, this),
                        !lines && !loadError && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "m-0 flex items-center gap-2 text-sm text-ink-soft",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Spinner"], {}, void 0, false, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 431,
                                    columnNumber: 15
                                }, this),
                                " Loading the lyrics…"
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/LyricsTiming.tsx",
                            lineNumber: 430,
                            columnNumber: 13
                        }, this),
                        lines && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "flex flex-wrap items-center gap-x-4 gap-y-2 text-[13px] text-ink-soft",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    children: [
                                        lines.length,
                                        " lines ·",
                                        " ",
                                        method === "edited" ? "timing edited" : method === "exact" ? "timed from the song's own word timings" : method === "even" ? "spaced evenly (auto-sync unavailable)" : lines.length ? "timed automatically" : "not timed yet"
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 437,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    className: "flex items-center gap-1",
                                    children: [
                                        "All lines",
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                                            label: "All lines 0.1 s earlier",
                                            onClick: ()=>edit((ls)=>ls.map((l)=>shift(l, -0.1))),
                                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$minus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Minus$3e$__["Minus"], {
                                                className: "size-3.5"
                                            }, void 0, false, {
                                                fileName: "[project]/components/LyricsTiming.tsx",
                                                lineNumber: 452,
                                                columnNumber: 19
                                            }, this)
                                        }, void 0, false, {
                                            fileName: "[project]/components/LyricsTiming.tsx",
                                            lineNumber: 451,
                                            columnNumber: 17
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                                            label: "All lines 0.1 s later",
                                            onClick: ()=>edit((ls)=>ls.map((l)=>shift(l, 0.1))),
                                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$plus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Plus$3e$__["Plus"], {
                                                className: "size-3.5"
                                            }, void 0, false, {
                                                fileName: "[project]/components/LyricsTiming.tsx",
                                                lineNumber: 455,
                                                columnNumber: 19
                                            }, this)
                                        }, void 0, false, {
                                            fileName: "[project]/components/LyricsTiming.tsx",
                                            lineNumber: 454,
                                            columnNumber: 17
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 449,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                    className: "flex items-center gap-1.5",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                            type: "checkbox",
                                            checked: follow,
                                            onChange: (e)=>setFollow(e.target.checked),
                                            className: "size-4 accent-cobalt"
                                        }, void 0, false, {
                                            fileName: "[project]/components/LyricsTiming.tsx",
                                            lineNumber: 459,
                                            columnNumber: 17
                                        }, this),
                                        "Follow the song"
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 458,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                    className: "flex items-center gap-1.5",
                                    title: "When you change a line's time, every line after it moves by the same amount",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                            type: "checkbox",
                                            checked: ripple,
                                            onChange: (e)=>setRipple(e.target.checked),
                                            className: "size-4 accent-cobalt"
                                        }, void 0, false, {
                                            fileName: "[project]/components/LyricsTiming.tsx",
                                            lineNumber: 463,
                                            columnNumber: 17
                                        }, this),
                                        "Move later lines too"
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 462,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    className: "ml-auto flex flex-wrap items-center gap-1",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                            size: "sm",
                                            variant: "ghost",
                                            icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$list$2d$plus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ListPlus$3e$__["ListPlus"], {
                                                className: "size-3.5"
                                            }, void 0, false, {
                                                fileName: "[project]/components/LyricsTiming.tsx",
                                                lineNumber: 467,
                                                columnNumber: 57
                                            }, this),
                                            onClick: ()=>addLine(now, now + 2),
                                            children: [
                                                "Add line at ",
                                                fmt(now)
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/components/LyricsTiming.tsx",
                                            lineNumber: 467,
                                            columnNumber: 17
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                            size: "sm",
                                            variant: "ghost",
                                            disabled: busy,
                                            icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$refresh$2d$cw$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__RefreshCw$3e$__["RefreshCw"], {
                                                className: "size-3.5"
                                            }, void 0, false, {
                                                fileName: "[project]/components/LyricsTiming.tsx",
                                                lineNumber: 474,
                                                columnNumber: 25
                                            }, this),
                                            onClick: async ()=>{
                                                if (method === "edited" && !confirmResync) {
                                                    setConfirmResync(true);
                                                    return;
                                                }
                                                setConfirmResync(false);
                                                setError("");
                                                const err = await onResync();
                                                if (err) setError(err);
                                            },
                                            children: confirmResync ? "Replace my edits? Click again" : lines.length ? "Sync again" : "Sync lyrics"
                                        }, void 0, false, {
                                            fileName: "[project]/components/LyricsTiming.tsx",
                                            lineNumber: 470,
                                            columnNumber: 17
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 466,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/LyricsTiming.tsx",
                            lineNumber: 436,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Message"], {
                            text: error,
                            error: true
                        }, void 0, false, {
                            fileName: "[project]/components/LyricsTiming.tsx",
                            lineNumber: 491,
                            columnNumber: 11
                        }, this),
                        toCheck.length > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "m-0 flex flex-wrap items-center gap-2 rounded-lg border border-warn/40 bg-warn/[0.08] px-3 py-2 text-[13px] text-ink",
                            role: "status",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$circle$2d$alert$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__CircleAlert$3e$__["CircleAlert"], {
                                    className: "size-4 shrink-0 text-warn"
                                }, void 0, false, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 494,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    className: "min-w-0 flex-1",
                                    children: [
                                        "The sync isn't sure about ",
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                            children: toCheck.length
                                        }, void 0, false, {
                                            fileName: "[project]/components/LyricsTiming.tsx",
                                            lineNumber: 496,
                                            columnNumber: 48
                                        }, this),
                                        " line",
                                        toCheck.length === 1 ? "" : "s",
                                        ". Listen to ",
                                        toCheck.length === 1 ? "it" : "them",
                                        "; fix the timing or press ",
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                            children: "Looks right"
                                        }, void 0, false, {
                                            fileName: "[project]/components/LyricsTiming.tsx",
                                            lineNumber: 497,
                                            columnNumber: 37
                                        }, this),
                                        "."
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 495,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                    size: "sm",
                                    variant: "secondary",
                                    icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$play$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Play$3e$__["Play"], {
                                        className: "size-3.5"
                                    }, void 0, false, {
                                        fileName: "[project]/components/LyricsTiming.tsx",
                                        lineNumber: 499,
                                        columnNumber: 59
                                    }, this),
                                    onClick: playNextToCheck,
                                    children: "Play next to check"
                                }, void 0, false, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 499,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/LyricsTiming.tsx",
                            lineNumber: 493,
                            columnNumber: 13
                        }, this),
                        deleted && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "m-0 flex items-center gap-2 rounded-lg bg-ink/[0.05] px-3 py-1.5 text-[13px] text-ink-soft",
                            role: "status",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    className: "min-w-0 flex-1 truncate",
                                    children: [
                                        "Deleted “",
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            lang: lang,
                                            children: deleted.row.text
                                        }, void 0, false, {
                                            fileName: "[project]/components/LyricsTiming.tsx",
                                            lineNumber: 507,
                                            columnNumber: 26
                                        }, this),
                                        "”"
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 506,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                    size: "sm",
                                    variant: "ghost",
                                    icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$undo$2d$2$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Undo2$3e$__["Undo2"], {
                                        className: "size-3.5"
                                    }, void 0, false, {
                                        fileName: "[project]/components/LyricsTiming.tsx",
                                        lineNumber: 512,
                                        columnNumber: 23
                                    }, this),
                                    onClick: ()=>{
                                        const { row, index } = deleted;
                                        edit((ls)=>[
                                                ...ls.slice(0, index),
                                                row,
                                                ...ls.slice(index)
                                            ]);
                                        setDeleted(null);
                                    },
                                    children: "Undo"
                                }, void 0, false, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 509,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/LyricsTiming.tsx",
                            lineNumber: 505,
                            columnNumber: 13
                        }, this),
                        lines && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ol", {
                            ref: list,
                            className: "@container m-0 grid list-none gap-1.5 p-0",
                            children: lines.map((line, i)=>{
                                const start = lineStart(line);
                                const end = lineEnd(line);
                                const newSection = i === 0 || lines[i - 1].section !== line.section;
                                const isActive = i === active;
                                const expanded = open.has(line.uid);
                                return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                    "data-line": i,
                                    className: "grid gap-1.5",
                                    children: [
                                        newSection && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                            className: "m-0 mt-3 text-xs font-semibold tracking-wide text-ink-soft uppercase",
                                            children: sections[line.section] ?? ""
                                        }, void 0, false, {
                                            fileName: "[project]/components/LyricsTiming.tsx",
                                            lineNumber: 534,
                                            columnNumber: 36
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                            className: `grid gap-1.5 rounded-lg border px-2 py-1.5 ${isActive ? "border-cobalt bg-cobalt/[0.06]" : line.check ? "border-warn/60 bg-warn/[0.06]" : "border-line bg-panel"}`,
                                            children: [
                                                line.check && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                    className: "flex items-center gap-2 text-xs text-ink-soft",
                                                    children: [
                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$circle$2d$alert$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__CircleAlert$3e$__["CircleAlert"], {
                                                            className: "size-3.5 shrink-0 text-warn"
                                                        }, void 0, false, {
                                                            fileName: "[project]/components/LyricsTiming.tsx",
                                                            lineNumber: 542,
                                                            columnNumber: 27
                                                        }, this),
                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                            className: "flex-1",
                                                            children: "Not sure about this line's timing. Play it to check."
                                                        }, void 0, false, {
                                                            fileName: "[project]/components/LyricsTiming.tsx",
                                                            lineNumber: 543,
                                                            columnNumber: 27
                                                        }, this),
                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                                            size: "sm",
                                                            variant: "ghost",
                                                            icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$check$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Check$3e$__["Check"], {
                                                                className: "size-3.5"
                                                            }, void 0, false, {
                                                                fileName: "[project]/components/LyricsTiming.tsx",
                                                                lineNumber: 544,
                                                                columnNumber: 67
                                                            }, this),
                                                            onClick: ()=>editLine(line.uid, (l)=>({
                                                                        ...l,
                                                                        check: false
                                                                    })),
                                                            children: "Looks right"
                                                        }, void 0, false, {
                                                            fileName: "[project]/components/LyricsTiming.tsx",
                                                            lineNumber: 544,
                                                            columnNumber: 27
                                                        }, this)
                                                    ]
                                                }, void 0, true, {
                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                    lineNumber: 541,
                                                    columnNumber: 25
                                                }, this),
                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                    className: "grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-2 gap-y-1 @3xl:grid-cols-[auto_minmax(0,1fr)_auto]",
                                                    children: [
                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                            className: "flex items-center gap-1",
                                                            children: [
                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                                                                    label: "Play from this line",
                                                                    onClick: ()=>seek(start - 0.6),
                                                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$play$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Play$3e$__["Play"], {
                                                                        className: "size-3.5"
                                                                    }, void 0, false, {
                                                                        fileName: "[project]/components/LyricsTiming.tsx",
                                                                        lineNumber: 552,
                                                                        columnNumber: 29
                                                                    }, this)
                                                                }, void 0, false, {
                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                    lineNumber: 551,
                                                                    columnNumber: 27
                                                                }, this),
                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(TimeInput, {
                                                                    label: `Line ${i + 1} start`,
                                                                    value: start,
                                                                    onCommit: (t)=>startAt(line.uid, t)
                                                                }, void 0, false, {
                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                    lineNumber: 554,
                                                                    columnNumber: 27
                                                                }, this),
                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                                    className: "text-ink-soft/60",
                                                                    children: "–"
                                                                }, void 0, false, {
                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                    lineNumber: 555,
                                                                    columnNumber: 27
                                                                }, this),
                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(TimeInput, {
                                                                    label: `Line ${i + 1} end`,
                                                                    value: end,
                                                                    onCommit: (t)=>endAt(line.uid, t)
                                                                }, void 0, false, {
                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                    lineNumber: 556,
                                                                    columnNumber: 27
                                                                }, this)
                                                            ]
                                                        }, void 0, true, {
                                                            fileName: "[project]/components/LyricsTiming.tsx",
                                                            lineNumber: 550,
                                                            columnNumber: 25
                                                        }, this),
                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                            lang: lang,
                                                            "aria-label": `Line ${i + 1} text`,
                                                            "data-line-text": line.uid,
                                                            className: "field-input h-9 min-w-0",
                                                            value: line.text,
                                                            onChange: (e)=>editLine(line.uid, (l)=>retext(l, e.target.value))
                                                        }, void 0, false, {
                                                            fileName: "[project]/components/LyricsTiming.tsx",
                                                            lineNumber: 558,
                                                            columnNumber: 25
                                                        }, this),
                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                            className: "col-span-2 flex flex-wrap items-center justify-end gap-0.5 @3xl:col-span-1",
                                                            children: [
                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                                                                    label: "0.1 s earlier",
                                                                    onClick: ()=>retime(line.uid, (l)=>shift(l, -0.1), "start"),
                                                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$minus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Minus$3e$__["Minus"], {
                                                                        className: "size-3.5"
                                                                    }, void 0, false, {
                                                                        fileName: "[project]/components/LyricsTiming.tsx",
                                                                        lineNumber: 568,
                                                                        columnNumber: 29
                                                                    }, this)
                                                                }, void 0, false, {
                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                    lineNumber: 567,
                                                                    columnNumber: 27
                                                                }, this),
                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                                                                    label: "0.1 s later",
                                                                    onClick: ()=>retime(line.uid, (l)=>shift(l, 0.1), "start"),
                                                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$plus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Plus$3e$__["Plus"], {
                                                                        className: "size-3.5"
                                                                    }, void 0, false, {
                                                                        fileName: "[project]/components/LyricsTiming.tsx",
                                                                        lineNumber: 571,
                                                                        columnNumber: 29
                                                                    }, this)
                                                                }, void 0, false, {
                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                    lineNumber: 570,
                                                                    columnNumber: 27
                                                                }, this),
                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                                                    size: "sm",
                                                                    variant: "ghost",
                                                                    title: "This line starts at the playhead",
                                                                    disabled: now >= end,
                                                                    onClick: ()=>startAt(line.uid, now),
                                                                    children: "Start here"
                                                                }, void 0, false, {
                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                    lineNumber: 573,
                                                                    columnNumber: 27
                                                                }, this),
                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                                                    size: "sm",
                                                                    variant: "ghost",
                                                                    title: "This line ends at the playhead",
                                                                    disabled: now <= start,
                                                                    onClick: ()=>endAt(line.uid, now),
                                                                    children: "End here"
                                                                }, void 0, false, {
                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                    lineNumber: 576,
                                                                    columnNumber: 27
                                                                }, this),
                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                                                                    label: expanded ? "Hide word timing" : "Word timing",
                                                                    "aria-expanded": expanded,
                                                                    onClick: ()=>setOpen((s)=>{
                                                                            const next = new Set(s);
                                                                            if (next.has(line.uid)) next.delete(line.uid);
                                                                            else next.add(line.uid);
                                                                            return next;
                                                                        }),
                                                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$chevron$2d$down$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ChevronDown$3e$__["ChevronDown"], {
                                                                        className: `size-4 transition-transform ${expanded ? "rotate-180" : ""}`
                                                                    }, void 0, false, {
                                                                        fileName: "[project]/components/LyricsTiming.tsx",
                                                                        lineNumber: 591,
                                                                        columnNumber: 29
                                                                    }, this)
                                                                }, void 0, false, {
                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                    lineNumber: 579,
                                                                    columnNumber: 27
                                                                }, this),
                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                                                                    label: "Add a line after this one",
                                                                    onClick: ()=>addAfter(i),
                                                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$list$2d$plus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ListPlus$3e$__["ListPlus"], {
                                                                        className: "size-3.5"
                                                                    }, void 0, false, {
                                                                        fileName: "[project]/components/LyricsTiming.tsx",
                                                                        lineNumber: 594,
                                                                        columnNumber: 29
                                                                    }, this)
                                                                }, void 0, false, {
                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                    lineNumber: 593,
                                                                    columnNumber: 27
                                                                }, this),
                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                                                                    label: "Delete this line",
                                                                    tone: "danger",
                                                                    onClick: ()=>removeLine(i),
                                                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$trash$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Trash2$3e$__["Trash2"], {
                                                                        className: "size-3.5"
                                                                    }, void 0, false, {
                                                                        fileName: "[project]/components/LyricsTiming.tsx",
                                                                        lineNumber: 597,
                                                                        columnNumber: 29
                                                                    }, this)
                                                                }, void 0, false, {
                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                    lineNumber: 596,
                                                                    columnNumber: 27
                                                                }, this)
                                                            ]
                                                        }, void 0, true, {
                                                            fileName: "[project]/components/LyricsTiming.tsx",
                                                            lineNumber: 566,
                                                            columnNumber: 25
                                                        }, this)
                                                    ]
                                                }, void 0, true, {
                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                    lineNumber: 549,
                                                    columnNumber: 23
                                                }, this),
                                                expanded && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                    className: "grid gap-1.5 border-t border-line pt-2",
                                                    children: [
                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                                                            className: "m-0 flex list-none flex-wrap gap-1.5 p-0",
                                                            children: [
                                                                line.words.map((w, k)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                                                        className: `grid justify-items-center gap-1 rounded-md border px-1.5 py-1 ${w.start <= now && now < w.end ? "border-cobalt bg-cobalt/[0.08]" : "border-line"}`,
                                                                        children: [
                                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                                                                type: "button",
                                                                                lang: lang,
                                                                                title: "Play from this word",
                                                                                onClick: ()=>seek(w.start - 0.3),
                                                                                className: "cursor-pointer rounded border-0 bg-transparent px-1 text-[13.5px] font-semibold text-ink hover:bg-ink/[0.06]",
                                                                                children: w.text
                                                                            }, void 0, false, {
                                                                                fileName: "[project]/components/LyricsTiming.tsx",
                                                                                lineNumber: 612,
                                                                                columnNumber: 33
                                                                            }, this),
                                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                                                className: "flex items-center gap-0.5",
                                                                                children: [
                                                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(TimeInput, {
                                                                                        label: `“${w.text}” starts`,
                                                                                        value: w.start,
                                                                                        onCommit: (t)=>editLine(line.uid, (l)=>setWordStart(l, k, t))
                                                                                    }, void 0, false, {
                                                                                        fileName: "[project]/components/LyricsTiming.tsx",
                                                                                        lineNumber: 622,
                                                                                        columnNumber: 35
                                                                                    }, this),
                                                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                                                                                        label: `“${w.text}” starts at the playhead`,
                                                                                        className: "size-6",
                                                                                        onClick: ()=>editLine(line.uid, (l)=>setWordStart(l, k, now)),
                                                                                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$crosshair$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Crosshair$3e$__["Crosshair"], {
                                                                                            className: "size-3"
                                                                                        }, void 0, false, {
                                                                                            fileName: "[project]/components/LyricsTiming.tsx",
                                                                                            lineNumber: 624,
                                                                                            columnNumber: 37
                                                                                        }, this)
                                                                                    }, void 0, false, {
                                                                                        fileName: "[project]/components/LyricsTiming.tsx",
                                                                                        lineNumber: 623,
                                                                                        columnNumber: 35
                                                                                    }, this)
                                                                                ]
                                                                            }, void 0, true, {
                                                                                fileName: "[project]/components/LyricsTiming.tsx",
                                                                                lineNumber: 621,
                                                                                columnNumber: 33
                                                                            }, this)
                                                                        ]
                                                                    }, k, true, {
                                                                        fileName: "[project]/components/LyricsTiming.tsx",
                                                                        lineNumber: 606,
                                                                        columnNumber: 31
                                                                    }, this)),
                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                                                    className: "grid content-end justify-items-center gap-1 px-1 py-1",
                                                                    children: [
                                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                                            className: "text-xs text-ink-soft",
                                                                            children: "line ends"
                                                                        }, void 0, false, {
                                                                            fileName: "[project]/components/LyricsTiming.tsx",
                                                                            lineNumber: 630,
                                                                            columnNumber: 31
                                                                        }, this),
                                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                                            className: "flex items-center gap-0.5",
                                                                            children: [
                                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(TimeInput, {
                                                                                    label: "Last word ends",
                                                                                    value: end,
                                                                                    onCommit: (t)=>retime(line.uid, (l)=>setLastWordEnd(l, t), "end")
                                                                                }, void 0, false, {
                                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                                    lineNumber: 632,
                                                                                    columnNumber: 33
                                                                                }, this),
                                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                                                                                    label: "Line ends at the playhead",
                                                                                    className: "size-6",
                                                                                    onClick: ()=>retime(line.uid, (l)=>setLastWordEnd(l, now), "end"),
                                                                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$crosshair$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Crosshair$3e$__["Crosshair"], {
                                                                                        className: "size-3"
                                                                                    }, void 0, false, {
                                                                                        fileName: "[project]/components/LyricsTiming.tsx",
                                                                                        lineNumber: 634,
                                                                                        columnNumber: 35
                                                                                    }, this)
                                                                                }, void 0, false, {
                                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                                    lineNumber: 633,
                                                                                    columnNumber: 33
                                                                                }, this)
                                                                            ]
                                                                        }, void 0, true, {
                                                                            fileName: "[project]/components/LyricsTiming.tsx",
                                                                            lineNumber: 631,
                                                                            columnNumber: 31
                                                                        }, this)
                                                                    ]
                                                                }, void 0, true, {
                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                    lineNumber: 629,
                                                                    columnNumber: 29
                                                                }, this)
                                                            ]
                                                        }, void 0, true, {
                                                            fileName: "[project]/components/LyricsTiming.tsx",
                                                            lineNumber: 604,
                                                            columnNumber: 27
                                                        }, this),
                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                                            className: "m-0 text-xs text-ink-soft",
                                                            children: [
                                                                "Each word lights up at its start time. Play the song and click ",
                                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$crosshair$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Crosshair$3e$__["Crosshair"], {
                                                                    className: "inline size-3"
                                                                }, void 0, false, {
                                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                                    lineNumber: 640,
                                                                    columnNumber: 92
                                                                }, this),
                                                                " the moment a word is sung, or type a time."
                                                            ]
                                                        }, void 0, true, {
                                                            fileName: "[project]/components/LyricsTiming.tsx",
                                                            lineNumber: 639,
                                                            columnNumber: 27
                                                        }, this)
                                                    ]
                                                }, void 0, true, {
                                                    fileName: "[project]/components/LyricsTiming.tsx",
                                                    lineNumber: 603,
                                                    columnNumber: 25
                                                }, this)
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/components/LyricsTiming.tsx",
                                            lineNumber: 535,
                                            columnNumber: 21
                                        }, this)
                                    ]
                                }, line.uid, true, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 533,
                                    columnNumber: 19
                                }, this);
                            })
                        }, void 0, false, {
                            fileName: "[project]/components/LyricsTiming.tsx",
                            lineNumber: 525,
                            columnNumber: 13
                        }, this),
                        lines && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "m-0 text-[13px] text-ink-soft",
                            children: [
                                "Play the song and watch the line above the player. If a line is early or late, nudge it with − / +, type its start and end, or pause where it really starts and press ",
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                    children: "Start here"
                                }, void 0, false, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 653,
                                    columnNumber: 39
                                }, this),
                                ". With ",
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                    children: "Move later lines too"
                                }, void 0, false, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 653,
                                    columnNumber: 73
                                }, this),
                                " on, every line after it moves by the same amount, so fixing the first line that's off usually fixes the rest. Open a line's word timing to time each word. Missing a line? Pause where it's sung and press ",
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                    children: "Add line"
                                }, void 0, false, {
                                    fileName: "[project]/components/LyricsTiming.tsx",
                                    lineNumber: 655,
                                    columnNumber: 21
                                }, this),
                                ". Changes save automatically and the next music video uses them."
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/LyricsTiming.tsx",
                            lineNumber: 651,
                            columnNumber: 13
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/components/LyricsTiming.tsx",
                    lineNumber: 427,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/LyricsTiming.tsx",
                lineNumber: 426,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/LyricsTiming.tsx",
        lineNumber: 329,
        columnNumber: 5
    }, this);
}
_s1(LyricsTiming, "CwMOEc9i2HDeVM46xMS/agtyM8w=");
_c1 = LyricsTiming;
var _c, _c1;
__turbopack_context__.k.register(_c, "TimeInput");
__turbopack_context__.k.register(_c1, "LyricsTiming");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/MusicVideoOptions.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "MusicVideoOptions",
    ()=>MusicVideoOptions
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$chevron$2d$down$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ChevronDown$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/chevron-down.mjs [app-client] (ecmascript) <export default as ChevronDown>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$sparkles$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Sparkles$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/sparkles.mjs [app-client] (ecmascript) <export default as Sparkles>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/ui.tsx [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature(), _s1 = __turbopack_context__.k.signature(), _s2 = __turbopack_context__.k.signature();
"use client";
;
;
;
;
// The catalog (presets, looks, installed fonts) is the same for every song: fetch it once per page load.
let catalogPromise = null;
function useStyleCatalog() {
    _s();
    const [catalog, setCatalog] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "useStyleCatalog.useEffect": ()=>{
            catalogPromise ??= __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].options().then({
                "useStyleCatalog.useEffect": (o)=>o.styles ?? null
            }["useStyleCatalog.useEffect"]).catch({
                "useStyleCatalog.useEffect": ()=>{
                    catalogPromise = null; // try again next time
                    return null;
                }
            }["useStyleCatalog.useEffect"]);
            let alive = true;
            void catalogPromise.then({
                "useStyleCatalog.useEffect": (c)=>alive && setCatalog(c)
            }["useStyleCatalog.useEffect"]);
            return ({
                "useStyleCatalog.useEffect": ()=>{
                    alive = false;
                }
            })["useStyleCatalog.useEffect"];
        }
    }["useStyleCatalog.useEffect"], []);
    return catalog;
}
_s(useStyleCatalog, "BMUqhm1FSNVQElX8g869hgoM/nk=");
/** A preset as a full style: the font is left to the engine, which picks the preset's font for the language. */ function fromPreset(catalog, key) {
    const { preset, size, position, color, highlight, effect, outline, case: textCase } = catalog.presets[key];
    return {
        preset: preset ?? key,
        font: "",
        size,
        position,
        color,
        highlight,
        effect,
        outline,
        case: textCase
    };
}
/** The font the engine will use for this style and language. */ function fontFor(catalog, style, lang) {
    const p = catalog.presets[style.preset] ?? catalog.presets.classic;
    return style.font || (lang === "km" ? p.font_km : p.font);
}
// CSS stand-ins for the colour grades in crcontent/styles.py LOOKS, applied to the swatches and the preview
const LOOK_CSS = {
    natural: "brightness(0.96) saturate(1.08)",
    cinematic: "contrast(1.1) saturate(1.05) brightness(0.92) hue-rotate(-8deg)",
    film: "sepia(0.25) contrast(1.05) saturate(0.9)",
    moody: "contrast(1.12) saturate(0.7) brightness(0.82)",
    vibrant: "contrast(1.06) saturate(1.4)",
    mono: "grayscale(1) contrast(1.15)"
};
const SCENE_BG = "linear-gradient(180deg,#f2a65a 0%,#c9576b 38%,#3b4a8c 70%,#0f1a33 100%)";
const SIZE_PX = {
    s: 0.8,
    m: 1,
    l: 1.25
};
function textCss(style, font, sung) {
    const color = sung ? style.highlight : style.color;
    const css = {
        fontFamily: `"${font}", Arial, sans-serif`,
        color,
        fontWeight: 700
    };
    if (style.outline === "outline") css.textShadow = "0 0 2px #000, 0 0 2px #000, 0 0 3px #000, 1px 2px 2px rgb(0 0 0 / 0.6)";
    if (style.outline === "shadow") css.textShadow = "0 2px 6px rgb(0 0 0 / 0.75)";
    if (style.outline === "glow") css.textShadow = `0 0 6px ${style.highlight}, 0 0 14px ${style.highlight}aa`;
    return css;
}
/** A sample line of lyrics drawn roughly the way the video will draw it, with the words being "sung" in a loop. */ function LyricPreview({ style, font, lang, aspect, look, sample }) {
    _s1();
    const words = sample.split(/\s+/).filter(Boolean).slice(0, lang === "km" ? 4 : 7);
    const [sung, setSung] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(0);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "LyricPreview.useEffect": ()=>{
            const t = setInterval({
                "LyricPreview.useEffect.t": ()=>setSung({
                        "LyricPreview.useEffect.t": (n)=>n >= words.length + 2 ? 0 : n + 1
                    }["LyricPreview.useEffect.t"])
            }["LyricPreview.useEffect.t"], 420);
            return ({
                "LyricPreview.useEffect": ()=>clearInterval(t)
            })["LyricPreview.useEffect"];
        }
    }["LyricPreview.useEffect"], [
        words.length
    ]);
    const top = {
        low: aspect === "16:9" ? "80%" : "64%",
        middle: "50%",
        high: aspect === "16:9" ? "20%" : "24%"
    }[style.position];
    const display = (w)=>lang === "km" ? w : style.case === "upper" ? w.toUpperCase() : style.case === "lower" ? w.toLowerCase() : w;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: `@container relative mx-auto w-full overflow-hidden rounded-lg ${aspect === "16:9" ? "aspect-video" : "aspect-[9/16] max-w-[150px]"}`,
        "aria-hidden": true,
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "absolute inset-0",
                style: {
                    background: SCENE_BG,
                    filter: LOOK_CSS[look]
                }
            }, void 0, false, {
                fileName: "[project]/components/MusicVideoOptions.tsx",
                lineNumber: 88,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                lang: lang,
                className: "absolute inset-x-[6%] m-0 -translate-y-1/2 text-center leading-tight",
                style: {
                    top,
                    fontSize: `${(aspect === "16:9" ? 4.6 : 7.4) * SIZE_PX[style.size]}cqw`
                },
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                    className: style.outline === "box" ? "rounded-[0.15em] bg-black/40 box-decoration-clone px-[0.25em] py-[0.05em]" : "",
                    style: {
                        opacity: style.effect === "fade" ? sung === 0 || sung > words.length ? 0.15 : 1 : 1,
                        transition: "opacity 0.3s"
                    },
                    children: words.map((w, i)=>{
                        const isSung = style.effect !== "fade" && i < sung;
                        const hidden = style.effect === "pop" && i >= sung;
                        return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                            style: {
                                ...textCss(style, font, isSung),
                                opacity: hidden ? 0 : 1,
                                transition: style.effect === "fill" ? "color 0.35s" : undefined
                            },
                            children: [
                                display(w),
                                i < words.length - 1 ? " " : ""
                            ]
                        }, i, true, {
                            fileName: "[project]/components/MusicVideoOptions.tsx",
                            lineNumber: 102,
                            columnNumber: 15
                        }, this);
                    })
                }, void 0, false, {
                    fileName: "[project]/components/MusicVideoOptions.tsx",
                    lineNumber: 94,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/MusicVideoOptions.tsx",
                lineNumber: 89,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/MusicVideoOptions.tsx",
        lineNumber: 84,
        columnNumber: 5
    }, this);
}
_s1(LyricPreview, "O272JfdnC1eekbwp9pKhYIoCCdk=");
_c = LyricPreview;
function Pick({ label, value, options, onChange }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "grid justify-items-start gap-1",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                className: "field-label",
                children: label
            }, void 0, false, {
                fileName: "[project]/components/MusicVideoOptions.tsx",
                lineNumber: 117,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Segmented"], {
                name: label,
                size: "sm",
                value: value,
                options: options,
                onChange: onChange
            }, void 0, false, {
                fileName: "[project]/components/MusicVideoOptions.tsx",
                lineNumber: 118,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/MusicVideoOptions.tsx",
        lineNumber: 116,
        columnNumber: 5
    }, this);
}
_c1 = Pick;
function MusicVideoOptions({ name, lang, aspect, sample, value, onChange }) {
    _s2();
    const catalog = useStyleCatalog();
    const [ideas, setIdeas] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [ideasBusy, setIdeasBusy] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [ideasError, setIdeasError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [custom, setCustom] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const look = value.look || "natural";
    const style = catalog ? value.lyric_style ?? fromPreset(catalog, "classic") : null;
    const setStyle = (patch)=>style && onChange({
            ...value,
            lyric_style: {
                ...style,
                ...patch
            }
        });
    async function suggest() {
        setIdeasBusy(true);
        setIdeasError("");
        try {
            setIdeas((await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].videoIdeas(name)).ideas);
        } catch (e) {
            setIdeasError(e.message);
        } finally{
            setIdeasBusy(false);
        }
    }
    const ideaId = `mv-idea-${name}`;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "grid gap-3",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid gap-1",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "flex items-center justify-between gap-2",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                htmlFor: ideaId,
                                className: "field-label",
                                children: [
                                    "Video idea ",
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "font-normal",
                                        children: "optional"
                                    }, void 0, false, {
                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                        lineNumber: 167,
                                        columnNumber: 24
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                lineNumber: 166,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                size: "sm",
                                variant: "ghost",
                                icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$sparkles$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Sparkles$3e$__["Sparkles"], {
                                    className: "size-3.5"
                                }, void 0, false, {
                                    fileName: "[project]/components/MusicVideoOptions.tsx",
                                    lineNumber: 169,
                                    columnNumber: 51
                                }, this),
                                loading: ideasBusy,
                                onClick: suggest,
                                children: ideas ? "More ideas" : "Suggest ideas"
                            }, void 0, false, {
                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                lineNumber: 169,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/MusicVideoOptions.tsx",
                        lineNumber: 165,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("textarea", {
                        id: ideaId,
                        rows: 2,
                        maxLength: 1000,
                        value: value.idea,
                        onChange: (e)=>onChange({
                                ...value,
                                idea: e.target.value
                            }),
                        placeholder: "Empty city streets at blue hour, rain on neon signs, a lone figure under an umbrella",
                        className: "field-input min-h-[3.5rem] resize-y text-[13.5px]"
                    }, void 0, false, {
                        fileName: "[project]/components/MusicVideoOptions.tsx",
                        lineNumber: 173,
                        columnNumber: 9
                    }, this),
                    ideasError && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "m-0 text-xs text-danger",
                        children: ideasError
                    }, void 0, false, {
                        fileName: "[project]/components/MusicVideoOptions.tsx",
                        lineNumber: 182,
                        columnNumber: 24
                    }, this),
                    ideas && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                        className: "m-0 grid list-none gap-1.5 p-0",
                        children: ideas.map((idea, i)=>{
                            const chosen = value.idea === idea.idea;
                            return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                    type: "button",
                                    "aria-pressed": chosen,
                                    onClick: ()=>onChange({
                                            idea: idea.idea,
                                            look: idea.look,
                                            lyric_style: catalog ? fromPreset(catalog, idea.lyric_style) : value.lyric_style
                                        }),
                                    className: `grid w-full cursor-pointer gap-0.5 rounded-lg border p-2 text-left text-[12.5px] transition-colors hover:bg-ink/[0.04] ${chosen ? "border-cobalt bg-cobalt/[0.06]" : "border-line bg-transparent"}`,
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: "font-semibold text-ink",
                                            children: idea.title
                                        }, void 0, false, {
                                            fileName: "[project]/components/MusicVideoOptions.tsx",
                                            lineNumber: 199,
                                            columnNumber: 21
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: "text-ink-soft",
                                            children: idea.idea
                                        }, void 0, false, {
                                            fileName: "[project]/components/MusicVideoOptions.tsx",
                                            lineNumber: 200,
                                            columnNumber: 21
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: "text-[11.5px] text-ink-soft",
                                            children: [
                                                catalog?.looks[idea.look] ?? idea.look,
                                                " look · ",
                                                catalog?.presets[idea.lyric_style]?.label ?? idea.lyric_style,
                                                " lyrics"
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/components/MusicVideoOptions.tsx",
                                            lineNumber: 201,
                                            columnNumber: 21
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/MusicVideoOptions.tsx",
                                    lineNumber: 189,
                                    columnNumber: 19
                                }, this)
                            }, i, false, {
                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                lineNumber: 188,
                                columnNumber: 17
                            }, this);
                        })
                    }, void 0, false, {
                        fileName: "[project]/components/MusicVideoOptions.tsx",
                        lineNumber: 184,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "m-0 text-xs text-ink-soft",
                        children: "The footage follows your idea, matched to each part of the song. Leave empty to let the lyrics decide."
                    }, void 0, false, {
                        fileName: "[project]/components/MusicVideoOptions.tsx",
                        lineNumber: 210,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/MusicVideoOptions.tsx",
                lineNumber: 164,
                columnNumber: 7
            }, this),
            catalog && style && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "grid gap-1",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "field-label",
                                children: "Footage look"
                            }, void 0, false, {
                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                lineNumber: 216,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                role: "radiogroup",
                                "aria-label": "Footage look",
                                className: "grid grid-cols-3 gap-1.5",
                                children: Object.keys(catalog.looks).map((k)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                        type: "button",
                                        role: "radio",
                                        "aria-checked": look === k,
                                        onClick: ()=>onChange({
                                                ...value,
                                                look: k
                                            }),
                                        className: `grid cursor-pointer gap-1 rounded-lg border bg-transparent p-1 text-[11.5px] font-semibold ${look === k ? "border-cobalt text-ink" : "border-line text-ink-soft"}`,
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                className: "block h-7 rounded",
                                                style: {
                                                    background: SCENE_BG,
                                                    filter: LOOK_CSS[k]
                                                }
                                            }, void 0, false, {
                                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                                lineNumber: 227,
                                                columnNumber: 19
                                            }, this),
                                            catalog.looks[k]
                                        ]
                                    }, k, true, {
                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                        lineNumber: 219,
                                        columnNumber: 17
                                    }, this))
                            }, void 0, false, {
                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                lineNumber: 217,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                className: "m-0 text-xs text-ink-soft",
                                children: "One colour grade over every clip, with a slow camera drift, so the footage looks like one film."
                            }, void 0, false, {
                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                lineNumber: 232,
                                columnNumber: 13
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/MusicVideoOptions.tsx",
                        lineNumber: 215,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "grid gap-1.5",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "field-label",
                                children: "Lyrics style"
                            }, void 0, false, {
                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                lineNumber: 236,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                role: "radiogroup",
                                "aria-label": "Lyrics style",
                                className: "grid grid-cols-3 gap-1.5",
                                children: Object.keys(catalog.presets).map((k)=>{
                                    const p = fromPreset(catalog, k);
                                    const active = style.preset === k;
                                    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                        type: "button",
                                        role: "radio",
                                        "aria-checked": active,
                                        onClick: ()=>onChange({
                                                ...value,
                                                lyric_style: p
                                            }),
                                        className: `grid cursor-pointer place-items-center gap-0.5 rounded-lg border bg-[#141a26] px-1 py-1.5 ${active ? "border-cobalt outline-2 outline-cobalt" : "border-line"}`,
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                lang: lang,
                                                className: "text-[15px] leading-none",
                                                style: textCss(p, fontFor(catalog, p, lang), true),
                                                children: lang === "km" ? "ចម្រៀង" : p.case === "upper" ? "AA" : p.case === "lower" ? "aa" : "Aa"
                                            }, void 0, false, {
                                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                                lineNumber: 250,
                                                columnNumber: 21
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                className: "text-[11px] font-semibold text-white/70",
                                                children: catalog.presets[k].label
                                            }, void 0, false, {
                                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                                lineNumber: 253,
                                                columnNumber: 21
                                            }, this)
                                        ]
                                    }, k, true, {
                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                        lineNumber: 242,
                                        columnNumber: 19
                                    }, this);
                                })
                            }, void 0, false, {
                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                lineNumber: 237,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(LyricPreview, {
                                style: style,
                                font: fontFor(catalog, style, lang),
                                lang: lang,
                                aspect: aspect,
                                look: look,
                                sample: sample
                            }, void 0, false, {
                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                lineNumber: 258,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                type: "button",
                                "aria-expanded": custom,
                                onClick: ()=>setCustom((c)=>!c),
                                className: "flex cursor-pointer items-center gap-1 justify-self-start border-0 bg-transparent p-0 text-[12.5px] font-semibold text-cobalt",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$chevron$2d$down$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ChevronDown$3e$__["ChevronDown"], {
                                        className: `size-3.5 transition-transform ${custom ? "rotate-180" : ""}`
                                    }, void 0, false, {
                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                        lineNumber: 265,
                                        columnNumber: 15
                                    }, this),
                                    " Customize font, colours and effect"
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                lineNumber: 259,
                                columnNumber: 13
                            }, this),
                            custom && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "grid gap-2.5 rounded-lg border border-line p-2.5",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "grid gap-1",
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                                className: "field-label",
                                                htmlFor: `${ideaId}-font`,
                                                children: "Font"
                                            }, void 0, false, {
                                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                                lineNumber: 270,
                                                columnNumber: 19
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("select", {
                                                id: `${ideaId}-font`,
                                                value: fontFor(catalog, style, lang),
                                                onChange: (e)=>setStyle({
                                                        font: e.target.value
                                                    }),
                                                className: "field-input h-9 py-0 text-[13px]",
                                                children: (catalog.fonts[lang] ?? []).map((f)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
                                                        value: f,
                                                        style: {
                                                            fontFamily: `"${f}"`
                                                        },
                                                        children: f
                                                    }, f, false, {
                                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                                        lineNumber: 280,
                                                        columnNumber: 23
                                                    }, this))
                                            }, void 0, false, {
                                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                                lineNumber: 273,
                                                columnNumber: 19
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                        lineNumber: 269,
                                        columnNumber: 17
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "flex flex-wrap gap-3",
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                                className: "grid gap-1 text-[12.5px]",
                                                children: [
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                        className: "field-label",
                                                        children: "Text"
                                                    }, void 0, false, {
                                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                                        lineNumber: 288,
                                                        columnNumber: 21
                                                    }, this),
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                        type: "color",
                                                        value: style.color,
                                                        onChange: (e)=>setStyle({
                                                                color: e.target.value.toUpperCase()
                                                            }),
                                                        className: "h-8 w-12 cursor-pointer rounded border border-line bg-panel p-0.5"
                                                    }, void 0, false, {
                                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                                        lineNumber: 289,
                                                        columnNumber: 21
                                                    }, this)
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                                lineNumber: 287,
                                                columnNumber: 19
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                                className: "grid gap-1 text-[12.5px]",
                                                children: [
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                        className: "field-label",
                                                        children: "Sung words"
                                                    }, void 0, false, {
                                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                                        lineNumber: 292,
                                                        columnNumber: 21
                                                    }, this),
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                        type: "color",
                                                        value: style.highlight,
                                                        onChange: (e)=>setStyle({
                                                                highlight: e.target.value.toUpperCase()
                                                            }),
                                                        className: "h-8 w-12 cursor-pointer rounded border border-line bg-panel p-0.5"
                                                    }, void 0, false, {
                                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                                        lineNumber: 293,
                                                        columnNumber: 21
                                                    }, this)
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                                lineNumber: 291,
                                                columnNumber: 19
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                        lineNumber: 286,
                                        columnNumber: 17
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Pick, {
                                        label: "Effect",
                                        value: style.effect,
                                        onChange: (effect)=>setStyle({
                                                effect
                                            }),
                                        options: [
                                            {
                                                value: "karaoke",
                                                label: "Karaoke"
                                            },
                                            {
                                                value: "fill",
                                                label: "Fill"
                                            },
                                            {
                                                value: "pop",
                                                label: "Pop"
                                            },
                                            {
                                                value: "fade",
                                                label: "Fade"
                                            }
                                        ]
                                    }, void 0, false, {
                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                        lineNumber: 296,
                                        columnNumber: 17
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Pick, {
                                        label: "Edge",
                                        value: style.outline,
                                        onChange: (outline)=>setStyle({
                                                outline
                                            }),
                                        options: [
                                            {
                                                value: "outline",
                                                label: "Outline"
                                            },
                                            {
                                                value: "shadow",
                                                label: "Shadow"
                                            },
                                            {
                                                value: "box",
                                                label: "Box"
                                            },
                                            {
                                                value: "glow",
                                                label: "Glow"
                                            }
                                        ]
                                    }, void 0, false, {
                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                        lineNumber: 307,
                                        columnNumber: 17
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "flex flex-wrap gap-3",
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Pick, {
                                                label: "Size",
                                                value: style.size,
                                                onChange: (size)=>setStyle({
                                                        size
                                                    }),
                                                options: [
                                                    {
                                                        value: "s",
                                                        label: "S"
                                                    },
                                                    {
                                                        value: "m",
                                                        label: "M"
                                                    },
                                                    {
                                                        value: "l",
                                                        label: "L"
                                                    }
                                                ]
                                            }, void 0, false, {
                                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                                lineNumber: 319,
                                                columnNumber: 19
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Pick, {
                                                label: "Position",
                                                value: style.position,
                                                onChange: (position)=>setStyle({
                                                        position
                                                    }),
                                                options: [
                                                    {
                                                        value: "high",
                                                        label: "High"
                                                    },
                                                    {
                                                        value: "middle",
                                                        label: "Middle"
                                                    },
                                                    {
                                                        value: "low",
                                                        label: "Low"
                                                    }
                                                ]
                                            }, void 0, false, {
                                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                                lineNumber: 329,
                                                columnNumber: 19
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                        lineNumber: 318,
                                        columnNumber: 17
                                    }, this),
                                    lang !== "km" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Pick, {
                                        label: "Letters",
                                        value: style.case,
                                        onChange: (c)=>setStyle({
                                                case: c
                                            }),
                                        options: [
                                            {
                                                value: "as_is",
                                                label: "As written"
                                            },
                                            {
                                                value: "upper",
                                                label: "CAPS"
                                            },
                                            {
                                                value: "lower",
                                                label: "lower"
                                            }
                                        ]
                                    }, void 0, false, {
                                        fileName: "[project]/components/MusicVideoOptions.tsx",
                                        lineNumber: 341,
                                        columnNumber: 19
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/MusicVideoOptions.tsx",
                                lineNumber: 268,
                                columnNumber: 15
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/MusicVideoOptions.tsx",
                        lineNumber: 235,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/MusicVideoOptions.tsx",
                lineNumber: 214,
                columnNumber: 9
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/MusicVideoOptions.tsx",
        lineNumber: 163,
        columnNumber: 5
    }, this);
}
_s2(MusicVideoOptions, "rsBk4EuoR4o8z5Bk4/18y2gKbuM=", false, function() {
    return [
        useStyleCatalog
    ];
});
_c2 = MusicVideoOptions;
var _c, _c1, _c2;
__turbopack_context__.k.register(_c, "LyricPreview");
__turbopack_context__.k.register(_c1, "Pick");
__turbopack_context__.k.register(_c2, "MusicVideoOptions");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/PreviewPane.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "PreviewPane",
    ()=>PreviewPane,
    "settingsOf",
    ()=>settingsOf
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$check$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Check$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/check.mjs [app-client] (ecmascript) <export default as Check>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$copy$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Copy$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/copy.mjs [app-client] (ecmascript) <export default as Copy>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$download$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Download$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/download.mjs [app-client] (ecmascript) <export default as Download>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$film$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Film$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/film.mjs [app-client] (ecmascript) <export default as Film>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$image$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ImageIcon$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/image.mjs [app-client] (ecmascript) <export default as ImageIcon>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$image$2d$up$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ImageUp$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/image-up.mjs [app-client] (ecmascript) <export default as ImageUp>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$list$2d$music$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ListMusic$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/list-music.mjs [app-client] (ecmascript) <export default as ListMusic>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$music$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Music$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/music.mjs [app-client] (ecmascript) <export default as Music>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$sparkles$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Sparkles$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/sparkles.mjs [app-client] (ecmascript) <export default as Sparkles>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$trash$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Trash2$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/trash.mjs [app-client] (ecmascript) <export default as Trash2>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$format$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/format.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/ui.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$MusicVideoOptions$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/MusicVideoOptions.tsx [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature(), _s1 = __turbopack_context__.k.signature(), _s2 = __turbopack_context__.k.signature(), _s3 = __turbopack_context__.k.signature();
"use client";
;
;
;
;
;
;
const STEPS = [
    "Script",
    "Voiceover",
    "Footage",
    "Captions",
    "Final render"
];
const SONG_STEPS = [
    "Lyrics",
    "Compose",
    "Lyric timing"
];
const MUSIC_VIDEO_STEPS = [
    "Lyric timing",
    "Beats and footage",
    "Captions",
    "Final render"
];
const SYNC_STEPS = [
    "Read lyrics",
    "Lyric timing"
];
const stepsFor = (job)=>job?.kind === "song" ? SONG_STEPS : job?.kind === "song_video" ? MUSIC_VIDEO_STEPS : job?.kind === "lyrics_sync" ? SYNC_STEPS : STEPS;
function SongPlayer({ detail }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "flex h-full flex-col justify-end gap-4 bg-gradient-to-b from-[#2a1b4a] via-[#1b2a4a] to-black p-5",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$music$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Music$3e$__["Music"], {
                className: "size-10 text-white/40"
            }, void 0, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 20,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid gap-1",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        lang: detail.lang,
                        className: "m-0 font-display text-2xl leading-tight font-extrabold",
                        children: detail.title
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 22,
                        columnNumber: 9
                    }, this),
                    detail.song && (detail.song.genre || detail.song.bpm > 0) && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "m-0 text-[13px] text-white/60",
                        children: [
                            detail.song.genre,
                            detail.song.bpm > 0 ? `${detail.song.bpm} bpm` : ""
                        ].filter(Boolean).join(", ")
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 24,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 21,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("audio", {
                src: (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["outputUrl"])(detail.name, "song.mp3"),
                controls: true,
                className: "w-full"
            }, detail.name, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 27,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/PreviewPane.tsx",
        lineNumber: 19,
        columnNumber: 5
    }, this);
}
_c = SongPlayer;
function settingsOf(detail) {
    return {
        idea: detail.idea ?? "",
        look: detail.look ?? "",
        lyric_style: detail.lyric_style ?? null
    };
}
function SongCard({ detail, onDelete, onMakeVideo, onOpenTiming, onSelectVideo }) {
    _s();
    const own = detail.source === "upload";
    const versions = detail.versions ?? [];
    const [settings, setSettings] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])({
        "SongCard.useState": ()=>settingsOf(detail)
    }["SongCard.useState"]);
    const sample = detail.song?.sections.flatMap((s)=>s.lyrics).find((l)=>l.trim()) ?? detail.title;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
        className: "grid gap-3 rounded-xl border border-line bg-panel p-3.5",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid gap-1.5",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                        variant: "secondary",
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$list$2d$music$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ListMusic$3e$__["ListMusic"], {
                            className: "size-4"
                        }, void 0, false, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 57,
                            columnNumber: 43
                        }, this),
                        onClick: ()=>onOpenTiming(detail.name),
                        children: "Edit lyric timing"
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 57,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$MusicVideoOptions$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["MusicVideoOptions"], {
                        name: detail.name,
                        lang: detail.lang,
                        aspect: detail.aspect,
                        sample: sample,
                        value: settings,
                        onChange: setSettings
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 60,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                        variant: versions.length ? "secondary" : "primary",
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$film$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Film$3e$__["Film"], {
                            className: "size-4"
                        }, void 0, false, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 61,
                            columnNumber: 75
                        }, this),
                        onClick: ()=>onMakeVideo(detail.name, settings),
                        children: versions.length ? "Make a new version" : "Make music video"
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 61,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "m-0 text-xs text-ink-soft",
                        children: [
                            detail.aspect === "16:9" ? "16:9 landscape" : "9:16 vertical",
                            ". Footage cut on the beat with karaoke lyrics, using the timing as it is now. Takes a few minutes",
                            own ? ", longer for a full song" : "",
                            ". Earlier versions are kept."
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 64,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 56,
                columnNumber: 7
            }, this),
            versions.length > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid gap-1",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                        className: "m-0 text-sm font-semibold",
                        children: [
                            "Music videos (",
                            versions.length,
                            ")"
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 71,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                        className: "m-0 grid list-none gap-0.5 p-0",
                        children: versions.map((v, i)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                    type: "button",
                                    onClick: ()=>onSelectVideo(v.name),
                                    className: "flex w-full cursor-pointer items-center gap-2.5 rounded-lg border-0 bg-transparent p-1.5 text-left hover:bg-ink/[0.04]",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: `grid h-9 shrink-0 place-items-center overflow-hidden rounded bg-ink/[0.08] bg-cover bg-center text-ink-soft ${v.aspect === "16:9" ? "aspect-video" : "aspect-[9/16]"}`,
                                            style: v.thumb ? {
                                                backgroundImage: `url('${(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["outputUrl"])(v.name, "thumbnail.jpg")}?v=${v.thumb_v}')`
                                            } : undefined,
                                            children: !v.thumb && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$film$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Film$3e$__["Film"], {
                                                className: "size-3.5"
                                            }, void 0, false, {
                                                fileName: "[project]/components/PreviewPane.tsx",
                                                lineNumber: 84,
                                                columnNumber: 34
                                            }, this)
                                        }, void 0, false, {
                                            fileName: "[project]/components/PreviewPane.tsx",
                                            lineNumber: 80,
                                            columnNumber: 19
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: "min-w-0 text-[13px]",
                                            children: [
                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                    className: "block font-semibold text-ink",
                                                    children: [
                                                        "Version ",
                                                        versions.length - i
                                                    ]
                                                }, void 0, true, {
                                                    fileName: "[project]/components/PreviewPane.tsx",
                                                    lineNumber: 87,
                                                    columnNumber: 21
                                                }, this),
                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                    className: "block text-xs text-ink-soft",
                                                    children: (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$format$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["relativeTime"])(v.created)
                                                }, void 0, false, {
                                                    fileName: "[project]/components/PreviewPane.tsx",
                                                    lineNumber: 88,
                                                    columnNumber: 21
                                                }, this)
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/components/PreviewPane.tsx",
                                            lineNumber: 86,
                                            columnNumber: 19
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/PreviewPane.tsx",
                                    lineNumber: 75,
                                    columnNumber: 17
                                }, this)
                            }, v.name, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 74,
                                columnNumber: 15
                            }, this))
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 72,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 70,
                columnNumber: 9
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                className: "m-0 text-sm font-semibold",
                children: "Lyrics"
            }, void 0, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 96,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                lang: detail.lang,
                className: "grid max-h-[260px] gap-3 overflow-auto text-[13px] leading-relaxed",
                children: detail.song?.sections.map((s, i)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                className: "m-0 text-xs font-semibold text-ink-soft",
                                children: [
                                    s.name,
                                    s.seconds > 0 ? ` · ${s.seconds}s` : ""
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 100,
                                columnNumber: 13
                            }, this),
                            s.lyrics.filter((l)=>l.trim()).length ? s.lyrics.filter((l)=>l.trim()).map((l, j)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                    className: "m-0",
                                    children: l
                                }, j, false, {
                                    fileName: "[project]/components/PreviewPane.tsx",
                                    lineNumber: 105,
                                    columnNumber: 62
                                }, this)) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                className: "m-0 text-ink-soft italic",
                                children: "instrumental"
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 107,
                                columnNumber: 15
                            }, this)
                        ]
                    }, i, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 99,
                        columnNumber: 11
                    }, this))
            }, void 0, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 97,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "flex flex-wrap items-center gap-1",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("a", {
                        className: (0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["buttonClass"])("ghost", "sm"),
                        href: `${__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["API_BASE"]}/api/videos/${encodeURIComponent(detail.name)}/song`,
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$download$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Download$3e$__["Download"], {
                                className: "size-3.5"
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 114,
                                columnNumber: 11
                            }, this),
                            " Song"
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 113,
                        columnNumber: 9
                    }, this),
                    detail.stems.vocals && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("a", {
                        className: (0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["buttonClass"])("ghost", "sm"),
                        href: `${__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["API_BASE"]}/api/videos/${encodeURIComponent(detail.name)}/stem/vocals`,
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$download$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Download$3e$__["Download"], {
                                className: "size-3.5"
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 118,
                                columnNumber: 13
                            }, this),
                            " Vocals"
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 117,
                        columnNumber: 11
                    }, this),
                    detail.stems.instrumental && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("a", {
                        className: (0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["buttonClass"])("ghost", "sm"),
                        href: `${__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["API_BASE"]}/api/videos/${encodeURIComponent(detail.name)}/stem/instrumental`,
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$download$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Download$3e$__["Download"], {
                                className: "size-3.5"
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 123,
                                columnNumber: 13
                            }, this),
                            " Instrumental"
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 122,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                        size: "sm",
                        variant: "danger",
                        className: "ml-auto",
                        title: versions.length ? "Deletes the song and its timing. Its music videos stay in Videos." : undefined,
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$trash$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Trash2$3e$__["Trash2"], {
                            className: "size-3.5"
                        }, void 0, false, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 131,
                            columnNumber: 17
                        }, this),
                        onClick: ()=>onDelete(detail.name),
                        children: "Delete song"
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 126,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 112,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/PreviewPane.tsx",
        lineNumber: 55,
        columnNumber: 5
    }, this);
}
_s(SongCard, "Ve1jTsrhhez1O44MOAFsKTgMHb8=");
_c1 = SongCard;
/** 9:16 phone frame (or a 16:9 screen for landscape music videos); children are positioned inside the screen.
 * Uses container units so overlays scale with it. */ function Phone({ children, landscape = false }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: `mx-auto w-full shrink-0 bg-ink shadow-[0_24px_48px_-24px_rgb(24_32_46/0.55)] ${landscape ? "aspect-video rounded-xl p-1.5" : "aspect-[9/16] max-w-[300px] rounded-[32px] p-2"}`,
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: `@container relative h-full w-full overflow-hidden bg-[#222b3b] text-white ${landscape ? "rounded-lg" : "rounded-[25px]"}`,
            children: children
        }, void 0, false, {
            fileName: "[project]/components/PreviewPane.tsx",
            lineNumber: 150,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/components/PreviewPane.tsx",
        lineNumber: 145,
        columnNumber: 5
    }, this);
}
_c2 = Phone;
/** Approximation of the rendered frame: background, headline box, caption with one highlighted word. */ function ScenePreview({ scene, index, total, lang }) {
    const words = scene.narration.trim().split(/\s+/).filter(Boolean);
    const group = lang === "km" ? words.slice(0, 1) : words.slice(0, 3);
    const font = lang === "km" ? "var(--font-khmer)" : "Arial, Helvetica, sans-serif";
    const media = scene.media;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
        children: [
            media ? (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$format$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["isImagePath"])(media) ? // eslint-disable-next-line @next/next/no-img-element -- local engine file
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                src: (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fileUrl"])(media),
                alt: "",
                className: "absolute inset-0 h-full w-full object-cover brightness-90"
            }, void 0, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 166,
                columnNumber: 11
            }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("video", {
                src: (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fileUrl"])(media),
                muted: true,
                loop: true,
                autoPlay: true,
                playsInline: true,
                className: "absolute inset-0 h-full w-full object-cover brightness-90"
            }, media, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 168,
                columnNumber: 11
            }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "absolute inset-0 bg-[linear-gradient(160deg,#1e3c72,#2a5298_45%,#6a11cb)]",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                    className: "absolute inset-x-0 bottom-[14%] px-[8cqw] text-center text-[3.6cqw] leading-snug text-white/70",
                    children: [
                        "Auto footage",
                        scene.visual_query ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                            children: [
                                ": “",
                                scene.visual_query,
                                "”"
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 173,
                            columnNumber: 47
                        }, this) : " from the search words"
                    ]
                }, void 0, true, {
                    fileName: "[project]/components/PreviewPane.tsx",
                    lineNumber: 172,
                    columnNumber: 11
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 171,
                columnNumber: 9
            }, this),
            scene.on_screen_text && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "absolute inset-x-0 top-[12%] flex justify-center px-[7cqw]",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                    lang: lang,
                    style: {
                        fontFamily: font
                    },
                    className: "bg-black/90 px-[2.4cqw] py-[1.2cqw] text-center text-[6.8cqw] leading-tight font-bold uppercase",
                    children: scene.on_screen_text
                }, void 0, false, {
                    fileName: "[project]/components/PreviewPane.tsx",
                    lineNumber: 179,
                    columnNumber: 11
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 178,
                columnNumber: 9
            }, this),
            group.length > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                lang: lang,
                style: {
                    fontFamily: font,
                    WebkitTextStroke: "0.55cqw #000",
                    paintOrder: "stroke fill"
                },
                className: "absolute inset-x-0 top-[57%] px-[8cqw] text-center text-[8.5cqw] leading-tight font-bold",
                children: group.map((w, i)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: i === 0 ? "text-caption" : "",
                        children: [
                            w,
                            i < group.length - 1 ? " " : ""
                        ]
                    }, i, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 195,
                        columnNumber: 13
                    }, this))
            }, void 0, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 189,
                columnNumber: 9
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                className: "absolute top-[3.5cqw] right-[4cqw] rounded-full bg-black/55 px-[2.2cqw] py-[0.8cqw] text-[3.4cqw] font-semibold",
                children: [
                    index + 1,
                    " / ",
                    total
                ]
            }, void 0, true, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 202,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/PreviewPane.tsx",
        lineNumber: 162,
        columnNumber: 5
    }, this);
}
_c3 = ScenePreview;
function Progress({ job, title }) {
    _s1();
    const log = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "Progress.useEffect": ()=>{
            if (log.current) log.current.scrollTop = log.current.scrollHeight;
        }
    }["Progress.useEffect"], [
        job?.log.length
    ]);
    const step = job?.step ?? 0;
    const finished = job?.status === "done";
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "flex h-full flex-col gap-3.5 px-5 pt-7 pb-4",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                className: "m-0 font-display text-[17px] leading-tight font-bold",
                children: title
            }, void 0, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 218,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ol", {
                className: "m-0 grid list-none gap-2 p-0",
                children: stepsFor(job).map((label, i)=>{
                    const n = i + 1;
                    const done = finished || n < step;
                    const active = !finished && n === step;
                    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                        className: `flex items-center gap-2.5 text-sm ${done ? "text-white/85" : active ? "font-semibold text-white" : "text-white/45"}`,
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: `grid size-[22px] place-items-center rounded-full text-xs font-semibold ${done ? "bg-white/15" : active ? "animate-pulse bg-caption text-ink" : "border border-white/30"}`,
                                children: done ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$check$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Check$3e$__["Check"], {
                                    className: "size-3.5"
                                }, void 0, false, {
                                    fileName: "[project]/components/PreviewPane.tsx",
                                    lineNumber: 231,
                                    columnNumber: 25
                                }, this) : n
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 226,
                                columnNumber: 15
                            }, this),
                            label
                        ]
                    }, label, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 225,
                        columnNumber: 13
                    }, this);
                })
            }, void 0, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 219,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("pre", {
                ref: log,
                "aria-live": "polite",
                className: "m-0 flex-1 overflow-auto font-mono text-[11px] leading-normal break-words whitespace-pre-wrap text-white/55",
                children: [
                    job?.log.length ? job.log.join("\n") : job?.status === "queued" ? "Waiting for the previous render to finish…" : "Starting…",
                    job?.status === "error" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "mt-2 block text-[#ff9a8f]",
                        children: job.error
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 240,
                        columnNumber: 37
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 238,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/PreviewPane.tsx",
        lineNumber: 217,
        columnNumber: 5
    }, this);
}
_s1(Progress, "VgqI98z6jW2AgerEqquueufBytM=");
_c4 = Progress;
function PostCard({ detail, onDelete }) {
    _s2();
    const toast = (0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useToast"])();
    const [confirmDelete, setConfirmDelete] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
        "aria-label": "Post text",
        className: "mx-auto w-full max-w-[300px] rounded-xl border border-line bg-panel",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("pre", {
                lang: detail.lang,
                className: "m-0 max-h-[160px] overflow-auto p-3.5 font-sans text-[13px] leading-relaxed whitespace-pre-wrap",
                children: detail.post || "No caption saved for this video."
            }, void 0, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 251,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "flex items-center gap-0.5 border-t border-line p-1.5",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                        size: "sm",
                        variant: "ghost",
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$copy$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Copy$3e$__["Copy"], {
                            className: "size-3.5"
                        }, void 0, false, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 258,
                            columnNumber: 17
                        }, this),
                        onClick: async ()=>{
                            await navigator.clipboard.writeText(detail.post);
                            toast("Caption and hashtags copied", "success");
                        },
                        children: "Copy"
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 255,
                        columnNumber: 9
                    }, this),
                    detail.video && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("a", {
                        className: (0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["buttonClass"])("ghost", "sm"),
                        href: `${__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["API_BASE"]}/api/videos/${encodeURIComponent(detail.name)}/download`,
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$download$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Download$3e$__["Download"], {
                                className: "size-3.5"
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 268,
                                columnNumber: 13
                            }, this),
                            "Download"
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 267,
                        columnNumber: 11
                    }, this),
                    confirmDelete ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                        size: "sm",
                        variant: "danger",
                        className: "ml-auto",
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$trash$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Trash2$3e$__["Trash2"], {
                            className: "size-3.5"
                        }, void 0, false, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 273,
                            columnNumber: 72
                        }, this),
                        onClick: ()=>onDelete(detail.name),
                        children: "Confirm"
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 273,
                        columnNumber: 11
                    }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                        label: "Delete video",
                        tone: "danger",
                        className: "ml-auto",
                        onClick: ()=>{
                            setConfirmDelete(true);
                            setTimeout(()=>setConfirmDelete(false), 3000);
                        },
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$trash$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Trash2$3e$__["Trash2"], {
                            className: "size-4"
                        }, void 0, false, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 286,
                            columnNumber: 13
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 277,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 254,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/PreviewPane.tsx",
        lineNumber: 250,
        columnNumber: 5
    }, this);
}
_s2(PostCard, "nW8S+HgHoHSCGUdY82D07YIC1pw=", false, function() {
    return [
        __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useToast"]
    ];
});
_c5 = PostCard;
const THUMB_STYLES = [
    {
        value: "bold",
        label: "Bold"
    },
    {
        value: "box",
        label: "Box"
    },
    {
        value: "stacked",
        label: "Stacked"
    },
    {
        value: "designed",
        label: "Designed"
    }
];
/** Cover image: get ideas (Claude headline x best frame x style) or pick a frame and headline, then redraw thumbnail.jpg. */ function ThumbnailCard({ detail, onChange }) {
    _s3();
    const toast = (0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useToast"])();
    // an older engine doesn't send the thumbnail fields: fall back to sensible defaults
    const duration = detail.duration ?? 0;
    const initial = {
        text: detail.thumb_text ?? detail.title,
        at: detail.thumb_at ?? Math.min(1, duration / 2),
        style: detail.thumb_style ?? "bold",
        emphasis: detail.thumb_emphasis ?? "",
        image: detail.thumb_image ?? "",
        v: detail.thumb_v ?? 0
    };
    const [text, setText] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(initial.text);
    const [at, setAt] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(initial.at);
    const [style, setStyle] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(initial.style);
    const [emphasis, setEmphasis] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(initial.emphasis);
    const [image, setImage] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(initial.image); // photo instead of a video frame ("" = the frame at `at`)
    const [coverIdea, setCoverIdea] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(detail.thumb_suggestions?.idea ?? "");
    const [uploading, setUploading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [saved, setSaved] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(initial);
    const [busy, setBusy] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [ideas, setIdeas] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(detail.thumb_suggestions ?? null);
    const [ideasV, setIdeasV] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(0); // cache buster for re-rendered preview images
    const [suggesting, setSuggesting] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const frame = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    const changed = text !== saved.text || at !== saved.at || style !== saved.style || emphasis !== saved.emphasis || image !== saved.image;
    const pickingFrame = !image && (at !== saved.at || !!saved.image);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "ThumbnailCard.useEffect": ()=>{
            if (frame.current) frame.current.currentTime = at;
        }
    }["ThumbnailCard.useEffect"], [
        at,
        pickingFrame
    ]);
    async function generate(cover = {
        text,
        at,
        style,
        emphasis,
        image
    }) {
        setBusy(true);
        try {
            const summary = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].makeThumbnail(detail.name, cover);
            setText(cover.text);
            setAt(cover.at);
            setStyle(cover.style);
            setEmphasis(cover.emphasis);
            setImage(cover.image);
            setSaved({
                text: cover.text,
                at: cover.at,
                style: cover.style,
                emphasis: cover.emphasis,
                image: cover.image,
                v: summary.thumb_v
            });
            onChange(summary);
            toast("Thumbnail updated", "success");
        } catch (e) {
            toast(e.message, "error");
        } finally{
            setBusy(false);
        }
    }
    async function suggest() {
        setSuggesting(true);
        try {
            setIdeas(await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].suggestThumbnails(detail.name, coverIdea));
            setIdeasV(Date.now());
        } catch (e) {
            toast(e.message, "error");
        } finally{
            setSuggesting(false);
        }
    }
    async function uploadPhoto(file) {
        setUploading(true);
        try {
            const media = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].upload(file);
            if (media.kind !== "photo") throw new Error("Use a photo (jpg, png or webp) for the thumbnail.");
            setImage(media.media);
        } catch (e) {
            toast(e.message, "error");
        } finally{
            setUploading(false);
        }
    }
    const isCurrent = (i)=>i.text === saved.text && i.at === saved.at && i.style === saved.style && i.emphasis === saved.emphasis && (i.image ?? "") === saved.image;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
        "aria-label": "Thumbnail",
        className: "mx-auto grid w-full max-w-[300px] gap-3 rounded-xl border border-line bg-panel p-3.5",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid gap-2",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                        className: "field-label",
                        htmlFor: `cover-idea-${detail.name}`,
                        children: [
                            "Cover idea ",
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "font-normal",
                                children: "optional"
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 386,
                                columnNumber: 22
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 385,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("textarea", {
                        id: `cover-idea-${detail.name}`,
                        lang: detail.lang,
                        rows: 2,
                        maxLength: 600,
                        value: coverIdea,
                        onChange: (e)=>setCoverIdea(e.target.value),
                        placeholder: "A silhouette against a neon city at night, the headline asks a question",
                        className: "field-input resize-y py-1.5 text-[13px] leading-snug"
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 388,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "flex items-center justify-between gap-2",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "text-[12px] text-ink-soft",
                                children: "Describe the picture, words or mood you want."
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 399,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                size: "sm",
                                variant: ideas && !coverIdea ? "ghost" : "primary",
                                icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$sparkles$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Sparkles$3e$__["Sparkles"], {
                                    className: "size-3.5"
                                }, void 0, false, {
                                    fileName: "[project]/components/PreviewPane.tsx",
                                    lineNumber: 400,
                                    columnNumber: 87
                                }, this),
                                loading: suggesting,
                                onClick: suggest,
                                children: ideas ? "New ideas" : "Suggest covers"
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 400,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 398,
                        columnNumber: 9
                    }, this),
                    suggesting && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "m-0 text-[12.5px] text-ink-soft",
                        children: "Claude is picking frames, writing headlines and designing each cover… about a minute."
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 404,
                        columnNumber: 24
                    }, this),
                    ideas && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: `grid grid-cols-4 gap-1.5 ${suggesting ? "opacity-50" : ""}`,
                                children: ideas.items.map((idea)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                        type: "button",
                                        disabled: busy || suggesting,
                                        onClick: ()=>generate({
                                                text: idea.text,
                                                at: idea.at,
                                                style: idea.style,
                                                emphasis: idea.emphasis,
                                                image: idea.image ?? "",
                                                design: idea.design
                                            }),
                                        title: `Use “${idea.text}” (${idea.style}, ${idea.image ? "stock photo" : `${idea.at.toFixed(1)} s`})`,
                                        "aria-label": `Use cover: ${idea.text}`,
                                        className: `relative ${detail.aspect === "16:9" ? "aspect-video" : "aspect-[9/16]"} cursor-pointer overflow-hidden rounded-md bg-ink outline outline-offset-1 transition hover:brightness-110 disabled:cursor-wait ${isCurrent(idea) ? "outline-2 outline-cobalt" : "outline-1 outline-line"}`,
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                                                src: `${(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["outputUrl"])(detail.name, idea.file)}?v=${ideasV}`,
                                                alt: "",
                                                className: "h-full w-full object-cover"
                                            }, void 0, false, {
                                                fileName: "[project]/components/PreviewPane.tsx",
                                                lineNumber: 421,
                                                columnNumber: 19
                                            }, this),
                                            idea.image && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                className: "absolute inset-x-0 bottom-0 bg-black/60 py-px text-center text-[9px] font-semibold text-white",
                                                children: "Photo"
                                            }, void 0, false, {
                                                fileName: "[project]/components/PreviewPane.tsx",
                                                lineNumber: 423,
                                                columnNumber: 21
                                            }, this),
                                            isCurrent(idea) && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                className: "absolute top-1 right-1 grid size-4 place-items-center rounded-full bg-cobalt text-white",
                                                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$check$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Check$3e$__["Check"], {
                                                    className: "size-3"
                                                }, void 0, false, {
                                                    fileName: "[project]/components/PreviewPane.tsx",
                                                    lineNumber: 427,
                                                    columnNumber: 23
                                                }, this)
                                            }, void 0, false, {
                                                fileName: "[project]/components/PreviewPane.tsx",
                                                lineNumber: 426,
                                                columnNumber: 21
                                            }, this)
                                        ]
                                    }, idea.file, true, {
                                        fileName: "[project]/components/PreviewPane.tsx",
                                        lineNumber: 409,
                                        columnNumber: 17
                                    }, this))
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 407,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                className: "m-0 text-[12px] text-ink-soft",
                                children: ideas.note || "Click one to use it, then fine-tune below."
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 433,
                                columnNumber: 13
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 406,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 384,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "flex gap-3",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: `relative shrink-0 overflow-hidden rounded-md bg-ink ${detail.aspect === "16:9" ? "aspect-video w-[132px]" : "aspect-[9/16] w-[84px]"}`,
                        children: image && image !== saved.image ? // eslint-disable-next-line @next/next/no-img-element -- local engine file
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                            src: (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fileUrl"])(image),
                            alt: "Chosen background photo",
                            className: "h-full w-full object-cover"
                        }, void 0, false, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 441,
                            columnNumber: 13
                        }, this) : pickingFrame ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("video", {
                            ref: frame,
                            src: `${(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["outputUrl"])(detail.name, "video.mp4")}?v=${encodeURIComponent(detail.created)}`,
                            muted: true,
                            playsInline: true,
                            preload: "auto",
                            onLoadedMetadata: (e)=>e.currentTarget.currentTime = at,
                            className: "h-full w-full object-cover"
                        }, void 0, false, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 443,
                            columnNumber: 13
                        }, this) : detail.thumb ? // eslint-disable-next-line @next/next/no-img-element -- local engine file
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                            src: `${(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["outputUrl"])(detail.name, "thumbnail.jpg")}?v=${saved.v}`,
                            alt: "Current thumbnail",
                            className: "h-full w-full object-cover"
                        }, void 0, false, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 454,
                            columnNumber: 13
                        }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                            className: "grid h-full place-items-center text-white/60",
                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$image$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ImageIcon$3e$__["ImageIcon"], {
                                className: "size-5"
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 457,
                                columnNumber: 15
                            }, this)
                        }, void 0, false, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 456,
                            columnNumber: 13
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 438,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "grid min-w-0 flex-1 content-start gap-2",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                className: "field-label",
                                htmlFor: "thumb-text",
                                children: "Thumbnail headline"
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 462,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("textarea", {
                                id: "thumb-text",
                                lang: detail.lang,
                                rows: 3,
                                maxLength: 120,
                                value: text,
                                onChange: (e)=>setText(e.target.value),
                                placeholder: "No headline: just the frame",
                                className: "field-input resize-none py-1.5 text-[13px] leading-snug"
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 465,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 461,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 437,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid gap-1",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                        className: "field-label",
                        htmlFor: "thumb-emphasis",
                        children: "Highlight"
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 478,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                        id: "thumb-emphasis",
                        lang: detail.lang,
                        maxLength: 60,
                        value: emphasis,
                        onChange: (e)=>setEmphasis(e.target.value),
                        placeholder: "Auto: a number or the key word",
                        className: "field-input h-8 text-[13px]"
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 481,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 477,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid justify-items-start gap-1",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "field-label",
                        children: "Style"
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 492,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Segmented"], {
                        name: "thumb-style",
                        size: "sm",
                        value: style,
                        options: THUMB_STYLES,
                        onChange: setStyle
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 493,
                        columnNumber: 9
                    }, this),
                    style === "designed" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "text-[12px] text-ink-soft",
                        children: "Claude lays out the whole cover. New words keep the design; the first one takes a minute."
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 495,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 491,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid gap-1",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                        className: "field-label flex justify-between",
                        htmlFor: "thumb-at",
                        children: [
                            image ? "Background" : "Frame",
                            " ",
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "font-normal text-ink-soft tabular-nums",
                                children: image ? "photo" : `${at.toFixed(1)} s`
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 500,
                                columnNumber: 44
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 499,
                        columnNumber: 9
                    }, this),
                    image ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                        size: "sm",
                        variant: "ghost",
                        className: "justify-self-start",
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$film$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Film$3e$__["Film"], {
                            className: "size-3.5"
                        }, void 0, false, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 503,
                            columnNumber: 82
                        }, this),
                        onClick: ()=>setImage(""),
                        children: "Use a video frame instead"
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 503,
                        columnNumber: 11
                    }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                        id: "thumb-at",
                        type: "range",
                        min: 0,
                        max: Math.max(0.1, duration - 0.1),
                        step: 0.1,
                        value: at,
                        onChange: (e)=>setAt(+e.target.value),
                        className: "h-6 w-full accent-cobalt"
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 507,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                        className: `${(0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["buttonClass"])("ghost", "sm")} cursor-pointer justify-self-start ${uploading ? "opacity-60" : ""}`,
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$image$2d$up$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ImageUp$3e$__["ImageUp"], {
                                className: "size-3.5"
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 519,
                                columnNumber: 11
                            }, this),
                            " ",
                            uploading ? "Uploading…" : image ? "Upload another photo" : "Use my own photo",
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                type: "file",
                                accept: "image/jpeg,image/png,image/webp",
                                className: "sr-only",
                                disabled: uploading,
                                onChange: (e)=>{
                                    const f = e.target.files?.[0];
                                    e.target.value = "";
                                    if (f) void uploadPhoto(f);
                                }
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 520,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 518,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 498,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "flex items-center gap-1.5",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                        size: "sm",
                        variant: changed ? "primary" : "secondary",
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$image$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ImageIcon$3e$__["ImageIcon"], {
                            className: "size-3.5"
                        }, void 0, false, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 534,
                            columnNumber: 77
                        }, this),
                        loading: busy,
                        onClick: ()=>generate(),
                        children: detail.thumb ? "Regenerate" : "Generate"
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 534,
                        columnNumber: 9
                    }, this),
                    detail.thumb && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("a", {
                        className: (0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["buttonClass"])("ghost", "sm"),
                        href: `${__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["API_BASE"]}/api/videos/${encodeURIComponent(detail.name)}/thumbnail.jpg`,
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$download$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Download$3e$__["Download"], {
                                className: "size-3.5"
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 539,
                                columnNumber: 13
                            }, this),
                            "Download"
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 538,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 533,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/PreviewPane.tsx",
        lineNumber: 383,
        columnNumber: 5
    }, this);
}
_s3(ThumbnailCard, "cOXSCveSvLvCAPfmYaOCfTvVGvI=", false, function() {
    return [
        __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useToast"]
    ];
});
_c6 = ThumbnailCard;
function PreviewPane({ scene, sceneIndex, sceneCount, lang, rendering, job, jobTitle, detail, view, onView, onDeleteVideo, onThumbnail, onMakeMusicVideo, onOpenTiming, onSelectVideo }) {
    const showProgress = rendering || job?.status === "error";
    const canToggle = !!scene && !!detail?.video && !showProgress;
    const showVideo = !showProgress && !!detail?.video && (view === "video" || !scene);
    const isSong = !showProgress && !scene && detail?.kind === "song" && detail.audio;
    const showSong = isSong && !showVideo;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "grid content-start gap-4 p-5",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "flex h-8 items-center justify-between",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                        className: "m-0 font-display text-base font-bold",
                        children: showProgress ? job?.kind === "song" ? "Composing" : job?.kind === "lyrics_sync" ? "Syncing lyrics" : "Rendering" : showVideo ? detail?.kind === "music_video" ? "Music video" : "Video" : showSong ? "Song" : "Preview"
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 592,
                        columnNumber: 9
                    }, this),
                    canToggle && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Segmented"], {
                        size: "sm",
                        name: "preview-view",
                        value: view,
                        onChange: onView,
                        options: [
                            {
                                value: "scene",
                                label: "Scene"
                            },
                            {
                                value: "video",
                                label: "Video"
                            }
                        ]
                    }, void 0, false, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 596,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 591,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Phone, {
                landscape: !showProgress && !scene && detail?.aspect === "16:9",
                children: showProgress ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Progress, {
                    job: job,
                    title: jobTitle
                }, void 0, false, {
                    fileName: "[project]/components/PreviewPane.tsx",
                    lineNumber: 611,
                    columnNumber: 11
                }, this) : showVideo && detail ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("video", {
                    src: `${(0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["outputUrl"])(detail.name, "video.mp4")}?v=${encodeURIComponent(detail.created)}`,
                    controls: true,
                    playsInline: true,
                    className: "block h-full w-full bg-black object-cover"
                }, detail.name, false, {
                    fileName: "[project]/components/PreviewPane.tsx",
                    lineNumber: 613,
                    columnNumber: 11
                }, this) : showSong && detail ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(SongPlayer, {
                    detail: detail
                }, void 0, false, {
                    fileName: "[project]/components/PreviewPane.tsx",
                    lineNumber: 621,
                    columnNumber: 11
                }, this) : scene ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(ScenePreview, {
                    scene: scene,
                    index: sceneIndex,
                    total: sceneCount,
                    lang: lang
                }, void 0, false, {
                    fileName: "[project]/components/PreviewPane.tsx",
                    lineNumber: 623,
                    columnNumber: 11
                }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "grid h-full place-items-center p-7 text-center",
                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "m-0 font-display text-2xl leading-tight font-extrabold",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("mark", {
                                children: "Your video"
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 627,
                                columnNumber: 15
                            }, this),
                            " shows up here"
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/PreviewPane.tsx",
                        lineNumber: 626,
                        columnNumber: 13
                    }, this)
                }, void 0, false, {
                    fileName: "[project]/components/PreviewPane.tsx",
                    lineNumber: 625,
                    columnNumber: 11
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 609,
                columnNumber: 7
            }, this),
            !showProgress && !showVideo && scene && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                className: "m-0 text-center text-xs text-ink-soft",
                children: "Approximate look of the scene you're editing. Click a scene to preview it."
            }, void 0, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 634,
                columnNumber: 9
            }, this),
            showVideo && detail && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(ThumbnailCard, {
                detail: detail,
                onChange: onThumbnail
            }, `thumb-${detail.name}`, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 636,
                columnNumber: 31
            }, this),
            showVideo && detail?.kind === "music_video" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                className: "grid gap-1.5 rounded-xl border border-line bg-panel p-3.5",
                children: detail.song_folder ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                            variant: "secondary",
                            icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$list$2d$music$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ListMusic$3e$__["ListMusic"], {
                                className: "size-4"
                            }, void 0, false, {
                                fileName: "[project]/components/PreviewPane.tsx",
                                lineNumber: 641,
                                columnNumber: 49
                            }, this),
                            onClick: ()=>onOpenTiming(detail.song_folder),
                            children: "Edit lyric timing"
                        }, void 0, false, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 641,
                            columnNumber: 15
                        }, this),
                        detail.idea && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "m-0 text-xs text-ink-soft",
                            children: [
                                "Made with the idea: ",
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    className: "text-ink",
                                    children: detail.idea
                                }, void 0, false, {
                                    fileName: "[project]/components/PreviewPane.tsx",
                                    lineNumber: 646,
                                    columnNumber: 39
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 645,
                            columnNumber: 17
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "m-0 text-xs text-ink-soft",
                            children: "This video stays as it is. Fix the timing, then make a new version from the song."
                        }, void 0, false, {
                            fileName: "[project]/components/PreviewPane.tsx",
                            lineNumber: 649,
                            columnNumber: 15
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/components/PreviewPane.tsx",
                    lineNumber: 640,
                    columnNumber: 13
                }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                    className: "m-0 text-xs text-ink-soft",
                    children: "The song this video was made from has been deleted, so its timing can't be edited."
                }, void 0, false, {
                    fileName: "[project]/components/PreviewPane.tsx",
                    lineNumber: 652,
                    columnNumber: 13
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 638,
                columnNumber: 9
            }, this),
            isSong && detail && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(SongCard, {
                detail: detail,
                onDelete: onDeleteVideo,
                onMakeVideo: onMakeMusicVideo,
                onOpenTiming: onOpenTiming,
                onSelectVideo: onSelectVideo
            }, `song-${detail.name}`, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 657,
                columnNumber: 9
            }, this),
            showVideo && detail && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(PostCard, {
                detail: detail,
                onDelete: onDeleteVideo
            }, `post-${detail.name}`, false, {
                fileName: "[project]/components/PreviewPane.tsx",
                lineNumber: 659,
                columnNumber: 31
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/PreviewPane.tsx",
        lineNumber: 590,
        columnNumber: 5
    }, this);
}
_c7 = PreviewPane;
var _c, _c1, _c2, _c3, _c4, _c5, _c6, _c7;
__turbopack_context__.k.register(_c, "SongPlayer");
__turbopack_context__.k.register(_c1, "SongCard");
__turbopack_context__.k.register(_c2, "Phone");
__turbopack_context__.k.register(_c3, "ScenePreview");
__turbopack_context__.k.register(_c4, "Progress");
__turbopack_context__.k.register(_c5, "PostCard");
__turbopack_context__.k.register(_c6, "ThumbnailCard");
__turbopack_context__.k.register(_c7, "PreviewPane");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/SceneCard.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "SceneCard",
    ()=>SceneCard
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$arrow$2d$down$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ArrowDown$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/arrow-down.mjs [app-client] (ecmascript) <export default as ArrowDown>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$arrow$2d$up$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ArrowUp$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/arrow-up.mjs [app-client] (ecmascript) <export default as ArrowUp>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$image$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ImageIcon$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/image.mjs [app-client] (ecmascript) <export default as ImageIcon>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$palette$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Palette$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/palette.mjs [app-client] (ecmascript) <export default as Palette>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$pause$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Pause$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/pause.mjs [app-client] (ecmascript) <export default as Pause>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$play$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Play$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/play.mjs [app-client] (ecmascript) <export default as Play>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$search$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Search$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/search.mjs [app-client] (ecmascript) <export default as Search>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$sparkles$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Sparkles$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/sparkles.mjs [app-client] (ecmascript) <export default as Sparkles>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$trash$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Trash2$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/trash.mjs [app-client] (ecmascript) <export default as Trash2>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$upload$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Upload$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/upload.mjs [app-client] (ecmascript) <export default as Upload>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$x$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__X$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/x.mjs [app-client] (ecmascript) <export default as X>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$format$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/format.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/ui.tsx [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature(), _s1 = __turbopack_context__.k.signature(), _s2 = __turbopack_context__.k.signature(), _s3 = __turbopack_context__.k.signature();
"use client";
;
;
;
;
;
function MediaSlot({ media, onClick }) {
    _s();
    const video = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    if (!media) {
        return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
            type: "button",
            onClick: onClick,
            title: "Footage is picked automatically from the search words",
            "aria-label": "Choose background for this scene",
            className: "grid aspect-[9/16] w-full cursor-pointer place-items-center rounded-lg border border-dashed border-ink-soft/50 bg-paper p-0 text-ink-soft transition-colors hover:border-cobalt hover:text-cobalt",
            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                className: "grid justify-items-center gap-1 text-[11px] font-semibold",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$image$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ImageIcon$3e$__["ImageIcon"], {
                        className: "size-4",
                        "aria-hidden": true
                    }, void 0, false, {
                        fileName: "[project]/components/SceneCard.tsx",
                        lineNumber: 23,
                        columnNumber: 11
                    }, this),
                    "Auto"
                ]
            }, void 0, true, {
                fileName: "[project]/components/SceneCard.tsx",
                lineNumber: 22,
                columnNumber: 9
            }, this)
        }, void 0, false, {
            fileName: "[project]/components/SceneCard.tsx",
            lineNumber: 15,
            columnNumber: 7
        }, this);
    }
    const url = (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fileUrl"])(media);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
        type: "button",
        onClick: onClick,
        title: "Change background",
        "aria-label": "Change background for this scene",
        onMouseEnter: ()=>video.current?.play().catch(()=>{}),
        onMouseLeave: ()=>video.current?.pause(),
        className: "relative aspect-[9/16] w-full cursor-pointer overflow-hidden rounded-lg border-0 bg-ink p-0 ring-cobalt hover:ring-2",
        children: [
            (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$format$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["isImagePath"])(media) ? // eslint-disable-next-line @next/next/no-img-element -- local engine file, not a Next-optimizable asset
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                src: url,
                alt: "",
                className: "block h-full w-full object-cover"
            }, void 0, false, {
                fileName: "[project]/components/SceneCard.tsx",
                lineNumber: 42,
                columnNumber: 9
            }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("video", {
                ref: video,
                src: `${url}#t=0.5`,
                muted: true,
                playsInline: true,
                preload: "metadata",
                className: "block h-full w-full object-cover"
            }, void 0, false, {
                fileName: "[project]/components/SceneCard.tsx",
                lineNumber: 44,
                columnNumber: 9
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                className: "absolute bottom-1 left-1",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Chip"], {
                    tone: "caption",
                    children: (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$format$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["isImagePath"])(media) ? "Photo" : "Video"
                }, void 0, false, {
                    fileName: "[project]/components/SceneCard.tsx",
                    lineNumber: 47,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/SceneCard.tsx",
                lineNumber: 46,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/SceneCard.tsx",
        lineNumber: 31,
        columnNumber: 5
    }, this);
}
_s(MediaSlot, "xBF5W4IXnKdZ7ux1jd/Ct6M1VVU=");
_c = MediaSlot;
/** Stock search state for one scene. */ function useFinder(setStatus) {
    _s1();
    const [q, setQ] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [kind, setKind] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("video");
    const [results, setResults] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    async function search(query = q, k = kind) {
        if (!query.trim()) return;
        setResults(null);
        setStatus("Searching…");
        try {
            const data = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].footage(query.trim(), k);
            setResults(data.results);
            setStatus(data.results.length ? "" : "Nothing found. Try simpler words, or ask Claude for ideas.");
        } catch (err) {
            setResults([]);
            setStatus(err.message, true);
        }
    }
    return {
        q,
        setQ,
        kind,
        setKind,
        results,
        search
    };
}
_s1(useFinder, "ZKKqK4gKGN1yw5kmBCLsEOWGGOw=");
function Picker({ finder, narration, onPicked, onClose, setStatus }) {
    _s2();
    const { q, setQ, kind, setKind, results, search } = finder;
    const [ideas, setIdeas] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])([]);
    const [ideasBusy, setIdeasBusy] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [picking, setPicking] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [designing, setDesigning] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const radioName = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useId"])();
    async function pick(r) {
        setPicking(r.id);
        setStatus("Downloading…");
        try {
            const m = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].pick(r);
            onPicked(m.media, q.trim());
            setStatus(`${m.kind === "photo" ? "Photo" : "Video"} set for this scene.`);
        } catch (err) {
            setStatus(err.message, true);
        } finally{
            setPicking(null);
        }
    }
    async function design() {
        setDesigning(true);
        setStatus("Claude is drawing this background… about a minute.");
        try {
            const m = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].designFootage(q.trim(), narration);
            onPicked(m.media, q.trim());
            setStatus("Claude's artwork set for this scene.");
        } catch (err) {
            setStatus(err.message, true);
        } finally{
            setDesigning(false);
        }
    }
    async function askIdeas() {
        setIdeasBusy(true);
        try {
            setIdeas((await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].ideas(narration, q)).queries);
        } catch (err) {
            setStatus(err.message, true);
        } finally{
            setIdeasBusy(false);
        }
    }
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "grid gap-3 rounded-xl border border-line bg-paper/70 p-3",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "flex flex-wrap items-center gap-2",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Segmented"], {
                        size: "sm",
                        name: radioName,
                        value: kind,
                        onChange: (k)=>{
                            setKind(k);
                            void search(q, k);
                        },
                        options: [
                            {
                                value: "video",
                                label: "Videos"
                            },
                            {
                                value: "photo",
                                label: "Photos"
                            }
                        ]
                    }, void 0, false, {
                        fileName: "[project]/components/SceneCard.tsx",
                        lineNumber: 147,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("form", {
                        className: "flex min-w-[200px] flex-1 items-center gap-2",
                        onSubmit: (e)=>{
                            e.preventDefault();
                            void search();
                        },
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "relative flex-1",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$search$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Search$3e$__["Search"], {
                                        "aria-hidden": true,
                                        className: "pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-ink-soft"
                                    }, void 0, false, {
                                        fileName: "[project]/components/SceneCard.tsx",
                                        lineNumber: 168,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        "aria-label": "Search footage",
                                        className: "field-input h-8 py-0 pl-8 text-[13px]",
                                        value: q,
                                        onChange: (e)=>setQ(e.target.value)
                                    }, void 0, false, {
                                        fileName: "[project]/components/SceneCard.tsx",
                                        lineNumber: 169,
                                        columnNumber: 13
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/SceneCard.tsx",
                                lineNumber: 167,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                size: "sm",
                                type: "submit",
                                children: "Search"
                            }, void 0, false, {
                                fileName: "[project]/components/SceneCard.tsx",
                                lineNumber: 171,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/SceneCard.tsx",
                        lineNumber: 160,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                        size: "sm",
                        variant: "ghost",
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$sparkles$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Sparkles$3e$__["Sparkles"], {
                            className: "size-3.5"
                        }, void 0, false, {
                            fileName: "[project]/components/SceneCard.tsx",
                            lineNumber: 175,
                            columnNumber: 49
                        }, this),
                        onClick: askIdeas,
                        loading: ideasBusy,
                        children: "Ideas"
                    }, void 0, false, {
                        fileName: "[project]/components/SceneCard.tsx",
                        lineNumber: 175,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                        size: "sm",
                        variant: "ghost",
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$palette$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Palette$3e$__["Palette"], {
                            className: "size-3.5"
                        }, void 0, false, {
                            fileName: "[project]/components/SceneCard.tsx",
                            lineNumber: 181,
                            columnNumber: 17
                        }, this),
                        onClick: design,
                        loading: designing,
                        disabled: picking !== null || !q.trim() && !narration.trim(),
                        title: "Claude draws an original background from the search words and the narration",
                        children: "Design with Claude"
                    }, void 0, false, {
                        fileName: "[project]/components/SceneCard.tsx",
                        lineNumber: 178,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                        label: "Close footage search",
                        onClick: onClose,
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$x$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__X$3e$__["X"], {
                            className: "size-4"
                        }, void 0, false, {
                            fileName: "[project]/components/SceneCard.tsx",
                            lineNumber: 190,
                            columnNumber: 11
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/components/SceneCard.tsx",
                        lineNumber: 189,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/SceneCard.tsx",
                lineNumber: 146,
                columnNumber: 7
            }, this),
            ideas.length > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "flex flex-wrap gap-1.5",
                children: ideas.map((idea)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                        type: "button",
                        onClick: ()=>{
                            setQ(idea);
                            void search(idea);
                        },
                        className: "h-7 cursor-pointer rounded-full border border-line bg-panel px-3 text-[12.5px] font-medium text-ink hover:border-cobalt hover:text-cobalt",
                        children: idea
                    }, idea, false, {
                        fileName: "[project]/components/SceneCard.tsx",
                        lineNumber: 197,
                        columnNumber: 13
                    }, this))
            }, void 0, false, {
                fileName: "[project]/components/SceneCard.tsx",
                lineNumber: 195,
                columnNumber: 9
            }, this),
            results === null && q && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid h-24 place-items-center text-ink-soft",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Spinner"], {}, void 0, false, {
                    fileName: "[project]/components/SceneCard.tsx",
                    lineNumber: 214,
                    columnNumber: 11
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/SceneCard.tsx",
                lineNumber: 213,
                columnNumber: 9
            }, this),
            results && results.length > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                className: "m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(76px,1fr))] gap-1.5 p-0",
                children: results.map((r)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                            type: "button",
                            onClick: ()=>pick(r),
                            disabled: picking !== null,
                            "aria-label": `Use this ${r.kind}${r.author ? ` by ${r.author}` : ""}`,
                            style: {
                                backgroundImage: `url('${r.thumb}')`
                            },
                            className: "relative grid aspect-[9/16] w-full cursor-pointer place-items-center overflow-hidden rounded-lg border-2 border-transparent bg-ink bg-cover bg-center p-0 transition hover:border-cobalt focus-visible:border-cobalt disabled:cursor-progress",
                            children: [
                                picking === r.id && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    className: "grid size-8 place-items-center rounded-full bg-black/60 text-white",
                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Spinner"], {}, void 0, false, {
                                        fileName: "[project]/components/SceneCard.tsx",
                                        lineNumber: 231,
                                        columnNumber: 21
                                    }, this)
                                }, void 0, false, {
                                    fileName: "[project]/components/SceneCard.tsx",
                                    lineNumber: 230,
                                    columnNumber: 19
                                }, this),
                                r.kind === "video" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    className: "absolute right-1 bottom-1 rounded bg-black/65 px-1 py-0.5 text-[10.5px] leading-none text-white",
                                    children: [
                                        r.duration,
                                        "s"
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/SceneCard.tsx",
                                    lineNumber: 235,
                                    columnNumber: 19
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/SceneCard.tsx",
                            lineNumber: 221,
                            columnNumber: 15
                        }, this)
                    }, `${r.source}-${r.id}`, false, {
                        fileName: "[project]/components/SceneCard.tsx",
                        lineNumber: 220,
                        columnNumber: 13
                    }, this))
            }, void 0, false, {
                fileName: "[project]/components/SceneCard.tsx",
                lineNumber: 218,
                columnNumber: 9
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                className: "m-0 text-xs text-ink-soft",
                children: "Free stock media: click one to use it for this scene. Or let Claude draw an original background."
            }, void 0, false, {
                fileName: "[project]/components/SceneCard.tsx",
                lineNumber: 242,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/SceneCard.tsx",
        lineNumber: 145,
        columnNumber: 5
    }, this);
}
_s2(Picker, "BjD050+7WLT2xz4ReKG/3FG97gk=", false, function() {
    return [
        __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useId"]
    ];
});
_c1 = Picker;
function SceneCard({ scene, index, total, lang, active, listenState, onActivate, onChange, onMove, onRemove, onListen }) {
    _s3();
    const [pickerOpen, setPickerOpen] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [status, setStatusState] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])({
        text: ""
    });
    const setStatus = (text, error = false)=>setStatusState({
            text,
            error
        });
    const finder = useFinder(setStatus);
    const hook = index === 0;
    function togglePicker() {
        if (pickerOpen) return setPickerOpen(false);
        setPickerOpen(true);
        if (finder.results === null && scene.visual_query.trim()) {
            finder.setQ(scene.visual_query);
            void finder.search(scene.visual_query, finder.kind);
        } else if (!finder.q) {
            finder.setQ(scene.visual_query);
        }
    }
    async function upload(file) {
        setStatus(`Uploading ${file.name}…`);
        try {
            const m = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].upload(file);
            onChange({
                media: m.media
            });
            setStatus(`${m.kind === "photo" ? "Photo" : "Video"} uploaded.`);
        } catch (err) {
            setStatus(err.message, true);
        }
    }
    const ListenIcon = listenState === "loading" ? __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Spinner"] : listenState === "playing" ? __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$pause$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Pause$3e$__["Pause"] : __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$play$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Play$3e$__["Play"];
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
        onFocusCapture: onActivate,
        onPointerDown: onActivate,
        className: `group grid grid-cols-[64px_minmax(0,1fr)] gap-x-4 gap-y-3 rounded-xl border bg-panel p-4 transition-shadow sm:grid-cols-[76px_minmax(0,1fr)] ${active ? "border-cobalt/60 shadow-[0_0_0_3px_rgb(47_79_216/0.12)]" : "border-line hover:border-ink-soft/40"}`,
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid content-start gap-2",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(MediaSlot, {
                    media: scene.media,
                    onClick: togglePicker
                }, void 0, false, {
                    fileName: "[project]/components/SceneCard.tsx",
                    lineNumber: 311,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/SceneCard.tsx",
                lineNumber: 310,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid min-w-0 content-start gap-3",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "flex items-center justify-between gap-2",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "flex items-center gap-2",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "font-display text-[15px] font-extrabold text-ink",
                                        children: [
                                            "Scene ",
                                            index + 1
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/components/SceneCard.tsx",
                                        lineNumber: 317,
                                        columnNumber: 13
                                    }, this),
                                    hook && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Chip"], {
                                        tone: "caption",
                                        children: "Hook"
                                    }, void 0, false, {
                                        fileName: "[project]/components/SceneCard.tsx",
                                        lineNumber: 318,
                                        columnNumber: 22
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/SceneCard.tsx",
                                lineNumber: 316,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "flex items-center gap-0.5 opacity-70 transition-opacity group-hover:opacity-100 focus-within:opacity-100",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                                        label: "Move scene up",
                                        onClick: ()=>onMove(-1),
                                        disabled: index === 0,
                                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$arrow$2d$up$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ArrowUp$3e$__["ArrowUp"], {
                                            className: "size-4"
                                        }, void 0, false, {
                                            fileName: "[project]/components/SceneCard.tsx",
                                            lineNumber: 322,
                                            columnNumber: 15
                                        }, this)
                                    }, void 0, false, {
                                        fileName: "[project]/components/SceneCard.tsx",
                                        lineNumber: 321,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                                        label: "Move scene down",
                                        onClick: ()=>onMove(1),
                                        disabled: index === total - 1,
                                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$arrow$2d$down$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ArrowDown$3e$__["ArrowDown"], {
                                            className: "size-4"
                                        }, void 0, false, {
                                            fileName: "[project]/components/SceneCard.tsx",
                                            lineNumber: 325,
                                            columnNumber: 15
                                        }, this)
                                    }, void 0, false, {
                                        fileName: "[project]/components/SceneCard.tsx",
                                        lineNumber: 324,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                                        label: "Remove scene",
                                        tone: "danger",
                                        onClick: onRemove,
                                        disabled: total === 1,
                                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$trash$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Trash2$3e$__["Trash2"], {
                                            className: "size-4"
                                        }, void 0, false, {
                                            fileName: "[project]/components/SceneCard.tsx",
                                            lineNumber: 328,
                                            columnNumber: 15
                                        }, this)
                                    }, void 0, false, {
                                        fileName: "[project]/components/SceneCard.tsx",
                                        lineNumber: 327,
                                        columnNumber: 13
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/SceneCard.tsx",
                                lineNumber: 320,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/SceneCard.tsx",
                        lineNumber: 315,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "grid gap-1.5",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                className: "field-label",
                                htmlFor: `narration-${scene.uid}`,
                                children: "Voiceover"
                            }, void 0, false, {
                                fileName: "[project]/components/SceneCard.tsx",
                                lineNumber: 334,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("textarea", {
                                id: `narration-${scene.uid}`,
                                lang: lang,
                                rows: 2,
                                value: scene.narration,
                                onChange: (e)=>onChange({
                                        narration: e.target.value
                                    }),
                                placeholder: "What the voice says in this scene",
                                className: "field-input field-sizing-content min-h-[68px] resize-none text-[15px] leading-relaxed"
                            }, void 0, false, {
                                fileName: "[project]/components/SceneCard.tsx",
                                lineNumber: 337,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/SceneCard.tsx",
                        lineNumber: 333,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "grid gap-3 sm:grid-cols-2",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "grid gap-1.5",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                        className: "field-label",
                                        htmlFor: `headline-${scene.uid}`,
                                        children: [
                                            "Headline ",
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                className: "font-normal text-ink-soft/80",
                                                children: "optional"
                                            }, void 0, false, {
                                                fileName: "[project]/components/SceneCard.tsx",
                                                lineNumber: 351,
                                                columnNumber: 24
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/components/SceneCard.tsx",
                                        lineNumber: 350,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        id: `headline-${scene.uid}`,
                                        lang: lang,
                                        className: "field-input h-9 py-0 text-[13.5px]",
                                        value: scene.on_screen_text,
                                        onChange: (e)=>onChange({
                                                on_screen_text: e.target.value
                                            }),
                                        placeholder: "Text at the top"
                                    }, void 0, false, {
                                        fileName: "[project]/components/SceneCard.tsx",
                                        lineNumber: 353,
                                        columnNumber: 13
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/SceneCard.tsx",
                                lineNumber: 349,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "grid gap-1.5",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                        className: "field-label",
                                        htmlFor: `visual-${scene.uid}`,
                                        children: "Footage search"
                                    }, void 0, false, {
                                        fileName: "[project]/components/SceneCard.tsx",
                                        lineNumber: 356,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        id: `visual-${scene.uid}`,
                                        className: "field-input h-9 py-0 text-[13.5px]",
                                        value: scene.visual_query,
                                        onChange: (e)=>onChange({
                                                visual_query: e.target.value
                                            }),
                                        placeholder: "e.g. octopus underwater"
                                    }, void 0, false, {
                                        fileName: "[project]/components/SceneCard.tsx",
                                        lineNumber: 359,
                                        columnNumber: 13
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/SceneCard.tsx",
                                lineNumber: 355,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/SceneCard.tsx",
                        lineNumber: 348,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "-ml-2.5 flex flex-wrap items-center gap-1",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                size: "sm",
                                variant: "ghost",
                                onClick: onListen,
                                "aria-label": `Listen to scene ${index + 1}`,
                                icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(ListenIcon, {
                                    className: listenState === "loading" ? "size-3.5" : "size-3.5 fill-current"
                                }, void 0, false, {
                                    fileName: "[project]/components/SceneCard.tsx",
                                    lineNumber: 364,
                                    columnNumber: 114
                                }, this),
                                children: listenState === "playing" ? "Stop" : "Listen"
                            }, void 0, false, {
                                fileName: "[project]/components/SceneCard.tsx",
                                lineNumber: 364,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                size: "sm",
                                variant: "ghost",
                                onClick: togglePicker,
                                icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$search$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Search$3e$__["Search"], {
                                    className: "size-3.5"
                                }, void 0, false, {
                                    fileName: "[project]/components/SceneCard.tsx",
                                    lineNumber: 367,
                                    columnNumber: 74
                                }, this),
                                "aria-expanded": pickerOpen,
                                children: "Find footage"
                            }, void 0, false, {
                                fileName: "[project]/components/SceneCard.tsx",
                                lineNumber: 367,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                className: `relative cursor-pointer`,
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-[13px] font-semibold text-ink-soft transition-colors hover:bg-ink/[0.05] hover:text-ink",
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$upload$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Upload$3e$__["Upload"], {
                                                className: "size-3.5",
                                                "aria-hidden": true
                                            }, void 0, false, {
                                                fileName: "[project]/components/SceneCard.tsx",
                                                lineNumber: 372,
                                                columnNumber: 15
                                            }, this),
                                            "Upload"
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/components/SceneCard.tsx",
                                        lineNumber: 371,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        type: "file",
                                        className: "sr-only",
                                        accept: "video/mp4,video/quicktime,video/webm,image/jpeg,image/png,image/webp",
                                        onChange: (e)=>{
                                            const f = e.target.files?.[0];
                                            e.target.value = "";
                                            if (f) void upload(f);
                                        }
                                    }, void 0, false, {
                                        fileName: "[project]/components/SceneCard.tsx",
                                        lineNumber: 375,
                                        columnNumber: 13
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/components/SceneCard.tsx",
                                lineNumber: 370,
                                columnNumber: 11
                            }, this),
                            scene.media && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                size: "sm",
                                variant: "ghost",
                                onClick: ()=>{
                                    onChange({
                                        media: ""
                                    });
                                    setStatus("");
                                },
                                children: "Use auto footage"
                            }, void 0, false, {
                                fileName: "[project]/components/SceneCard.tsx",
                                lineNumber: 387,
                                columnNumber: 13
                            }, this),
                            status.text && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                role: "status",
                                className: `ml-1 text-[12.5px] ${status.error ? "text-danger" : "text-ink-soft"}`,
                                children: status.text
                            }, void 0, false, {
                                fileName: "[project]/components/SceneCard.tsx",
                                lineNumber: 399,
                                columnNumber: 13
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/SceneCard.tsx",
                        lineNumber: 363,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/SceneCard.tsx",
                lineNumber: 314,
                columnNumber: 7
            }, this),
            pickerOpen && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "col-span-2",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Picker, {
                    finder: finder,
                    narration: scene.narration,
                    setStatus: setStatus,
                    onClose: ()=>setPickerOpen(false),
                    onPicked: (media, query)=>{
                        onChange({
                            media,
                            visual_query: query || scene.visual_query
                        });
                        setPickerOpen(false);
                    }
                }, void 0, false, {
                    fileName: "[project]/components/SceneCard.tsx",
                    lineNumber: 408,
                    columnNumber: 11
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/SceneCard.tsx",
                lineNumber: 407,
                columnNumber: 9
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/SceneCard.tsx",
        lineNumber: 303,
        columnNumber: 5
    }, this);
}
_s3(SceneCard, "/qEB5LPm6oDhobv9NeO3tfoH3uQ=", false, function() {
    return [
        useFinder
    ];
});
_c2 = SceneCard;
var _c, _c1, _c2;
__turbopack_context__.k.register(_c, "MediaSlot");
__turbopack_context__.k.register(_c1, "Picker");
__turbopack_context__.k.register(_c2, "SceneCard");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/SongEditor.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "SongEditor",
    ()=>SongEditor
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$chevron$2d$left$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ChevronLeft$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/chevron-left.mjs [app-client] (ecmascript) <export default as ChevronLeft>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$music$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Music$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/music.mjs [app-client] (ecmascript) <export default as Music>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$plus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Plus$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/plus.mjs [app-client] (ecmascript) <export default as Plus>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$trash$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Trash2$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/trash.mjs [app-client] (ecmascript) <export default as Trash2>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/ui.tsx [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature(), _s1 = __turbopack_context__.k.signature();
"use client";
;
;
;
/** Comma-separated tags, edited as free text so typing isn't reformatted under the cursor. */ function TagsInput({ id, value, onChange, placeholder }) {
    _s();
    const [text, setText] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(value.join(", "));
    const parse = (t)=>t.split(",").map((x)=>x.trim()).filter(Boolean);
    // Resync when the value changes from outside (e.g. a section above was removed).
    if (parse(text).join("\n") !== value.join("\n")) setText(value.join(", "));
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
        id: id,
        className: "field-input",
        value: text,
        placeholder: placeholder,
        onChange: (e)=>{
            setText(e.target.value);
            onChange(parse(e.target.value));
        }
    }, void 0, false, {
        fileName: "[project]/components/SongEditor.tsx",
        lineNumber: 15,
        columnNumber: 5
    }, this);
}
_s(TagsInput, "Y3rgeaWdE9qI2VoCik4UH9xbDd4=");
_c = TagsInput;
function SectionCard({ index, section, lang, onChange, onRemove }) {
    const id = `section-${index}`;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
        className: "grid gap-4 rounded-xl border border-line bg-panel p-4 sm:p-5",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid items-end gap-4 sm:grid-cols-[minmax(0,1fr)_110px_auto]",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                        label: "Section",
                        htmlFor: `${id}-name`,
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                            id: `${id}-name`,
                            className: "field-input font-semibold",
                            value: section.name,
                            onChange: (e)=>onChange({
                                    ...section,
                                    name: e.target.value
                                })
                        }, void 0, false, {
                            fileName: "[project]/components/SongEditor.tsx",
                            lineNumber: 46,
                            columnNumber: 11
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/components/SongEditor.tsx",
                        lineNumber: 45,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                        label: "Seconds",
                        htmlFor: `${id}-sec`,
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                            id: `${id}-sec`,
                            type: "number",
                            min: 3,
                            max: 120,
                            className: "field-input",
                            value: section.seconds,
                            onChange: (e)=>onChange({
                                    ...section,
                                    seconds: Math.max(3, Math.min(120, Math.round(+e.target.value || 3)))
                                })
                        }, void 0, false, {
                            fileName: "[project]/components/SongEditor.tsx",
                            lineNumber: 49,
                            columnNumber: 11
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/components/SongEditor.tsx",
                        lineNumber: 48,
                        columnNumber: 9
                    }, this),
                    onRemove && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                        label: "Remove section",
                        tone: "danger",
                        onClick: onRemove,
                        className: "mb-1",
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$trash$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Trash2$3e$__["Trash2"], {
                            className: "size-4"
                        }, void 0, false, {
                            fileName: "[project]/components/SongEditor.tsx",
                            lineNumber: 61,
                            columnNumber: 13
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/components/SongEditor.tsx",
                        lineNumber: 60,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/SongEditor.tsx",
                lineNumber: 44,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                label: "Lyrics",
                hint: "one sung line per row; empty = instrumental",
                htmlFor: `${id}-lyrics`,
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("textarea", {
                    id: `${id}-lyrics`,
                    lang: lang,
                    rows: Math.max(3, section.lyrics.length + 1),
                    className: "field-input resize-y py-2.5 leading-relaxed",
                    value: section.lyrics.join("\n"),
                    onChange: (e)=>onChange({
                            ...section,
                            lyrics: e.target.value.split("\n")
                        })
                }, void 0, false, {
                    fileName: "[project]/components/SongEditor.tsx",
                    lineNumber: 66,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/SongEditor.tsx",
                lineNumber: 65,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "grid gap-4 sm:grid-cols-2",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                        label: "Sound for this part",
                        hint: "comma separated",
                        htmlFor: `${id}-styles`,
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(TagsInput, {
                            id: `${id}-styles`,
                            value: section.styles,
                            onChange: (styles)=>onChange({
                                    ...section,
                                    styles
                                }),
                            placeholder: "stripped back, soft piano"
                        }, void 0, false, {
                            fileName: "[project]/components/SongEditor.tsx",
                            lineNumber: 77,
                            columnNumber: 11
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/components/SongEditor.tsx",
                        lineNumber: 76,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                        label: "Footage search",
                        htmlFor: `${id}-visual`,
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                            id: `${id}-visual`,
                            className: "field-input",
                            value: section.visual_query,
                            onChange: (e)=>onChange({
                                    ...section,
                                    visual_query: e.target.value
                                })
                        }, void 0, false, {
                            fileName: "[project]/components/SongEditor.tsx",
                            lineNumber: 80,
                            columnNumber: 11
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/components/SongEditor.tsx",
                        lineNumber: 79,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/SongEditor.tsx",
                lineNumber: 75,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/SongEditor.tsx",
        lineNumber: 43,
        columnNumber: 5
    }, this);
}
_c1 = SectionCard;
function SongEditor({ song, setSong, lang, options, composing, onBack, onCompose }) {
    _s1();
    const [stems, setStems] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(true);
    const [error, setError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const total = song.sections.reduce((n, s)=>n + s.seconds, 0);
    const keyMissing = !options.keys.elevenlabs;
    const set = (patch)=>setSong((s)=>({
                ...s,
                ...patch
            }));
    const setSection = (i, section)=>setSong((s)=>({
                ...s,
                sections: s.sections.map((x, j)=>j === i ? section : x)
            }));
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "flex h-full min-h-0 flex-col",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("header", {
                className: "flex h-14 shrink-0 items-center gap-2 border-b border-line bg-panel px-3 sm:px-5",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                        label: "Back to start",
                        onClick: onBack,
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$chevron$2d$left$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ChevronLeft$3e$__["ChevronLeft"], {
                            className: "size-5"
                        }, void 0, false, {
                            fileName: "[project]/components/SongEditor.tsx",
                            lineNumber: 116,
                            columnNumber: 11
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/components/SongEditor.tsx",
                        lineNumber: 115,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "min-w-0 flex-1 truncate text-sm font-semibold",
                        lang: lang,
                        children: song.title || "Untitled song"
                    }, void 0, false, {
                        fileName: "[project]/components/SongEditor.tsx",
                        lineNumber: 118,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "text-[13px] text-ink-soft",
                        children: [
                            song.sections.length,
                            " sections, ",
                            total,
                            " s"
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/SongEditor.tsx",
                        lineNumber: 121,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/SongEditor.tsx",
                lineNumber: 114,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "min-h-0 flex-1 overflow-y-auto",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "mx-auto grid max-w-[760px] gap-5 px-4 py-6 sm:px-8",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                            className: "grid gap-4 rounded-xl border border-line bg-panel p-4 sm:p-5",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                                    label: "Title",
                                    htmlFor: "song-title",
                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        id: "song-title",
                                        lang: lang,
                                        className: "field-input text-lg font-semibold",
                                        value: song.title,
                                        onChange: (e)=>set({
                                                title: e.target.value
                                            })
                                    }, void 0, false, {
                                        fileName: "[project]/components/SongEditor.tsx",
                                        lineNumber: 130,
                                        columnNumber: 15
                                    }, this)
                                }, void 0, false, {
                                    fileName: "[project]/components/SongEditor.tsx",
                                    lineNumber: 129,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "grid gap-4 sm:grid-cols-[1fr_1fr_100px]",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                                            label: "Genre",
                                            htmlFor: "song-genre",
                                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                id: "song-genre",
                                                className: "field-input",
                                                value: song.genre,
                                                onChange: (e)=>set({
                                                        genre: e.target.value
                                                    })
                                            }, void 0, false, {
                                                fileName: "[project]/components/SongEditor.tsx",
                                                lineNumber: 134,
                                                columnNumber: 17
                                            }, this)
                                        }, void 0, false, {
                                            fileName: "[project]/components/SongEditor.tsx",
                                            lineNumber: 133,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                                            label: "Mood",
                                            htmlFor: "song-mood",
                                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                id: "song-mood",
                                                className: "field-input",
                                                value: song.mood,
                                                onChange: (e)=>set({
                                                        mood: e.target.value
                                                    })
                                            }, void 0, false, {
                                                fileName: "[project]/components/SongEditor.tsx",
                                                lineNumber: 137,
                                                columnNumber: 17
                                            }, this)
                                        }, void 0, false, {
                                            fileName: "[project]/components/SongEditor.tsx",
                                            lineNumber: 136,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                                            label: "BPM",
                                            htmlFor: "song-bpm",
                                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                id: "song-bpm",
                                                type: "number",
                                                min: 40,
                                                max: 220,
                                                className: "field-input",
                                                value: song.bpm,
                                                onChange: (e)=>set({
                                                        bpm: Math.round(+e.target.value || 100)
                                                    })
                                            }, void 0, false, {
                                                fileName: "[project]/components/SongEditor.tsx",
                                                lineNumber: 140,
                                                columnNumber: 17
                                            }, this)
                                        }, void 0, false, {
                                            fileName: "[project]/components/SongEditor.tsx",
                                            lineNumber: 139,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/SongEditor.tsx",
                                    lineNumber: 132,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                                    label: "Singer voice",
                                    htmlFor: "song-vocal-edit",
                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        id: "song-vocal-edit",
                                        className: "field-input",
                                        value: song.vocal,
                                        onChange: (e)=>set({
                                                vocal: e.target.value
                                            })
                                    }, void 0, false, {
                                        fileName: "[project]/components/SongEditor.tsx",
                                        lineNumber: 144,
                                        columnNumber: 15
                                    }, this)
                                }, void 0, false, {
                                    fileName: "[project]/components/SongEditor.tsx",
                                    lineNumber: 143,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "grid gap-4 sm:grid-cols-2",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                                            label: "Overall sound",
                                            hint: "comma separated",
                                            htmlFor: "song-styles",
                                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(TagsInput, {
                                                id: "song-styles",
                                                value: song.styles,
                                                onChange: (styles)=>set({
                                                        styles
                                                    })
                                            }, void 0, false, {
                                                fileName: "[project]/components/SongEditor.tsx",
                                                lineNumber: 148,
                                                columnNumber: 17
                                            }, this)
                                        }, void 0, false, {
                                            fileName: "[project]/components/SongEditor.tsx",
                                            lineNumber: 147,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                                            label: "Avoid",
                                            hint: "comma separated",
                                            htmlFor: "song-avoid",
                                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(TagsInput, {
                                                id: "song-avoid",
                                                value: song.avoid,
                                                onChange: (avoid)=>set({
                                                        avoid
                                                    })
                                            }, void 0, false, {
                                                fileName: "[project]/components/SongEditor.tsx",
                                                lineNumber: 151,
                                                columnNumber: 17
                                            }, this)
                                        }, void 0, false, {
                                            fileName: "[project]/components/SongEditor.tsx",
                                            lineNumber: 150,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/SongEditor.tsx",
                                    lineNumber: 146,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/SongEditor.tsx",
                            lineNumber: 128,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ol", {
                            className: "m-0 grid list-none gap-4 p-0",
                            children: song.sections.map((s, i)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(SectionCard, {
                                    index: i,
                                    section: s,
                                    lang: lang,
                                    onChange: (x)=>setSection(i, x),
                                    onRemove: song.sections.length > 1 ? ()=>setSong((so)=>({
                                                ...so,
                                                sections: so.sections.filter((_, j)=>j !== i)
                                            })) : null
                                }, i, false, {
                                    fileName: "[project]/components/SongEditor.tsx",
                                    lineNumber: 158,
                                    columnNumber: 15
                                }, this))
                        }, void 0, false, {
                            fileName: "[project]/components/SongEditor.tsx",
                            lineNumber: 156,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                            variant: "ghost",
                            icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$plus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Plus$3e$__["Plus"], {
                                className: "size-4"
                            }, void 0, false, {
                                fileName: "[project]/components/SongEditor.tsx",
                                lineNumber: 170,
                                columnNumber: 19
                            }, this),
                            className: "justify-self-start",
                            onClick: ()=>setSong((s)=>({
                                        ...s,
                                        sections: [
                                            ...s.sections,
                                            {
                                                name: "Chorus",
                                                lyrics: [],
                                                styles: [],
                                                seconds: 10,
                                                visual_query: ""
                                            }
                                        ]
                                    })),
                            children: "Add section"
                        }, void 0, false, {
                            fileName: "[project]/components/SongEditor.tsx",
                            lineNumber: 168,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                            className: "grid gap-3 rounded-xl border border-line bg-panel p-4 sm:p-5",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                    className: "flex items-center gap-2 text-sm",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                            type: "checkbox",
                                            checked: stems,
                                            onChange: (e)=>setStems(e.target.checked),
                                            className: "size-4 accent-cobalt"
                                        }, void 0, false, {
                                            fileName: "[project]/components/SongEditor.tsx",
                                            lineNumber: 181,
                                            columnNumber: 15
                                        }, this),
                                        "Also split vocals and instrumental (uses extra ElevenLabs credits)"
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/SongEditor.tsx",
                                    lineNumber: 180,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "flex flex-wrap items-center gap-2",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                            variant: "primary",
                                            loading: composing,
                                            disabled: keyMissing,
                                            icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$music$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Music$3e$__["Music"], {
                                                className: "size-4"
                                            }, void 0, false, {
                                                fileName: "[project]/components/SongEditor.tsx",
                                                lineNumber: 189,
                                                columnNumber: 23
                                            }, this),
                                            onClick: async ()=>{
                                                setError("");
                                                const err = await onCompose(stems);
                                                if (err) setError(err);
                                            },
                                            children: composing ? "Composing…" : "Compose song"
                                        }, void 0, false, {
                                            fileName: "[project]/components/SongEditor.tsx",
                                            lineNumber: 185,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: "text-[13px] text-ink-soft",
                                            children: "Takes about 30 seconds to 2 minutes."
                                        }, void 0, false, {
                                            fileName: "[project]/components/SongEditor.tsx",
                                            lineNumber: 198,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/SongEditor.tsx",
                                    lineNumber: 184,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Message"], {
                                    text: error || (keyMissing ? "ElevenLabs isn't connected. Add ELEVENLABS_API_KEY to .env and restart the engine." : ""),
                                    error: !!error || keyMissing
                                }, void 0, false, {
                                    fileName: "[project]/components/SongEditor.tsx",
                                    lineNumber: 200,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/SongEditor.tsx",
                            lineNumber: 179,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/components/SongEditor.tsx",
                    lineNumber: 127,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/SongEditor.tsx",
                lineNumber: 126,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/SongEditor.tsx",
        lineNumber: 113,
        columnNumber: 5
    }, this);
}
_s1(SongEditor, "kbYw7aUDCzdij8miRcmBYADE11c=");
_c2 = SongEditor;
var _c, _c1, _c2;
__turbopack_context__.k.register(_c, "TagsInput");
__turbopack_context__.k.register(_c1, "SectionCard");
__turbopack_context__.k.register(_c2, "SongEditor");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/Storyboard.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "Storyboard",
    ()=>Storyboard,
    "toDraft",
    ()=>toDraft,
    "toDraftData",
    ()=>toDraftData
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$check$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Check$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/check.mjs [app-client] (ecmascript) <export default as Check>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$chevron$2d$left$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ChevronLeft$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/chevron-left.mjs [app-client] (ecmascript) <export default as ChevronLeft>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$circle$2d$alert$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__CircleAlert$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/circle-alert.mjs [app-client] (ecmascript) <export default as CircleAlert>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$clapperboard$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Clapperboard$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/clapperboard.mjs [app-client] (ecmascript) <export default as Clapperboard>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$languages$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Languages$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/languages.mjs [app-client] (ecmascript) <export default as Languages>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$pause$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Pause$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/pause.mjs [app-client] (ecmascript) <export default as Pause>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$play$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Play$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/play.mjs [app-client] (ecmascript) <export default as Play>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$plus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Plus$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/plus.mjs [app-client] (ecmascript) <export default as Plus>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$trash$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Trash2$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/trash.mjs [app-client] (ecmascript) <export default as Trash2>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$useVoicePreview$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/useVoicePreview.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$SceneCard$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/SceneCard.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/ui.tsx [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
"use client";
;
;
;
;
;
;
let uidCounter = 0;
const uid = ()=>`s${++uidCounter}`;
const emptyScene = ()=>({
        narration: "",
        visual_query: "",
        on_screen_text: "",
        media: "",
        uid: uid()
    });
function toDraft(script, lang, topic, extra = {}) {
    const scenes = script.scenes.length ? script.scenes : [
        {
            narration: "",
            visual_query: "",
            on_screen_text: "",
            media: ""
        }
    ];
    return {
        id: extra.id ?? null,
        voice: extra.voice ?? "",
        rate: extra.rate ?? "+5%",
        music: extra.music ?? "",
        title: script.title,
        scenes: scenes.map((s)=>({
                ...s,
                media: s.media ?? "",
                uid: uid()
            })),
        caption: script.caption,
        hashtags: script.hashtags.map((h)=>`#${h}`).join(" "),
        lang,
        topic
    };
}
function toDraftData(d) {
    return {
        script: {
            title: d.title,
            scenes: d.scenes.map(({ narration, visual_query, on_screen_text, media })=>({
                    narration,
                    visual_query,
                    on_screen_text,
                    media
                })),
            caption: d.caption,
            hashtags: d.hashtags.split(/[\s,]+/).map((h)=>h.replace(/^#/, "")).filter(Boolean)
        },
        lang: d.lang,
        topic: d.topic,
        voice: d.voice,
        rate: d.rate,
        music: d.music
    };
}
/** What gets rendered: only scenes with narration, trimmed. */ function toScript(d) {
    return {
        title: d.title.trim() || "Untitled video",
        scenes: d.scenes.filter((s)=>s.narration.trim()).map((s)=>({
                narration: s.narration.trim(),
                visual_query: s.visual_query.trim() || "abstract background",
                on_screen_text: s.on_screen_text.trim(),
                media: s.media
            })),
        caption: d.caption.trim(),
        hashtags: d.hashtags.split(/[\s,]+/).map((h)=>h.replace(/^#/, "")).filter(Boolean)
    };
}
const SAMPLE = {
    en: "Did you know octopuses have three hearts? Follow for more.",
    km: "តើអ្នកដឹងទេ ថាមឹកដៃប្រាំបី មានបេះដូងបី? តាមដានយើង ដើម្បីដឹងបន្ថែម។"
};
const RATES = [
    {
        value: "-10%",
        label: "Slower"
    },
    {
        value: "+0%",
        label: "Normal"
    },
    {
        value: "+5%",
        label: "Slightly fast"
    },
    {
        value: "+15%",
        label: "Fast"
    }
];
const REGION = {
    "en-US": "English (US)",
    "en-GB": "English (UK)",
    "en-AU": "English (Australia)",
    "km-KH": "Khmer"
};
/** "en-US-AndrewMultilingualNeural" -> "Andrew Multilingual" */ function voiceName(v) {
    return v.split("-").slice(2).join(" ").replace(/Neural$/, "").replace(/([a-z])([A-Z])/g, "$1 $2");
}
/** Voices grouped by region, keeping the engine's order (recommended voices first). */ function groupVoices(voices) {
    const groups = new Map();
    for (const v of voices){
        const region = v.split("-").slice(0, 2).join("-");
        groups.set(region, [
            ...groups.get(region) ?? [],
            v
        ]);
    }
    return [
        ...groups.entries()
    ];
}
function SaveStatus({ state, saved }) {
    if (state === "saving") return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
        role: "status",
        className: "flex shrink-0 items-center gap-1.5 text-[12.5px] text-ink-soft",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Spinner"], {
                className: "size-3.5"
            }, void 0, false, {
                fileName: "[project]/components/Storyboard.tsx",
                lineNumber: 116,
                columnNumber: 9
            }, this),
            " Saving"
        ]
    }, void 0, true, {
        fileName: "[project]/components/Storyboard.tsx",
        lineNumber: 115,
        columnNumber: 7
    }, this);
    if (state === "error") return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
        role: "alert",
        className: "flex shrink-0 items-center gap-1.5 text-[12.5px] font-semibold text-danger",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$circle$2d$alert$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__CircleAlert$3e$__["CircleAlert"], {
                className: "size-3.5"
            }, void 0, false, {
                fileName: "[project]/components/Storyboard.tsx",
                lineNumber: 122,
                columnNumber: 9
            }, this),
            " Not saved. Is the engine running?"
        ]
    }, void 0, true, {
        fileName: "[project]/components/Storyboard.tsx",
        lineNumber: 121,
        columnNumber: 7
    }, this);
    if (!saved) return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
        className: "hidden shrink-0 text-[12.5px] text-ink-soft md:inline",
        children: "Your edits will be saved as a new draft"
    }, void 0, false, {
        fileName: "[project]/components/Storyboard.tsx",
        lineNumber: 126,
        columnNumber: 12
    }, this);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
        role: "status",
        className: "flex shrink-0 items-center gap-1 text-[12.5px] text-ink-soft",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$check$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Check$3e$__["Check"], {
                className: "size-3.5 text-ok"
            }, void 0, false, {
                fileName: "[project]/components/Storyboard.tsx",
                lineNumber: 129,
                columnNumber: 7
            }, this),
            " Saved"
        ]
    }, void 0, true, {
        fileName: "[project]/components/Storyboard.tsx",
        lineNumber: 128,
        columnNumber: 5
    }, this);
}
_c = SaveStatus;
function Storyboard({ draft, setDraft, options, rendering, saveState, activeUid, onActive, onBack, onNewDraft, onDeleteDraft, onRender }) {
    _s();
    const toast = (0, __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useToast"])();
    const voices = options.langs[draft.lang].voices;
    const voice = voices.includes(draft.voice) ? draft.voice : voices[0] ?? "";
    const rate = draft.rate || "+5%";
    const music = draft.music || (options.music.length ? "" : "none");
    const [confirmDelete, setConfirmDelete] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [translating, setTranslating] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const onPreviewError = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "Storyboard.useCallback[onPreviewError]": (m)=>toast(m, "error")
    }["Storyboard.useCallback[onPreviewError]"], [
        toast
    ]);
    const preview = (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$useVoicePreview$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useVoicePreview"])(onPreviewError);
    const listenState = (id)=>preview.active === id ? preview.loading ? "loading" : "playing" : "idle";
    const other = draft.lang === "km" ? "en" : "km";
    const otherLabel = other === "km" ? "ខ្មែរ" : "English";
    const updateScene = (i, patch)=>setDraft((d)=>({
                ...d,
                scenes: d.scenes.map((s, j)=>j === i ? {
                        ...s,
                        ...patch
                    } : s)
            }));
    const moveScene = (i, dir)=>setDraft((d)=>{
            const scenes = [
                ...d.scenes
            ];
            const j = i + dir;
            if (j < 0 || j >= scenes.length) return d;
            [scenes[i], scenes[j]] = [
                scenes[j],
                scenes[i]
            ];
            return {
                ...d,
                scenes
            };
        });
    const removeScene = (i)=>setDraft((d)=>d.scenes.length > 1 ? {
                ...d,
                scenes: d.scenes.filter((_, j)=>j !== i)
            } : d);
    const addScene = ()=>{
        const s = emptyScene();
        setDraft((d)=>({
                ...d,
                scenes: [
                    ...d.scenes,
                    s
                ]
            }));
        onActive(s.uid);
        setTimeout(()=>document.getElementById(`narration-${s.uid}`)?.focus(), 0);
    };
    async function translate() {
        const script = toScript(draft);
        if (!script.scenes.length) return toast("Write the voiceover for at least one scene first.", "error");
        preview.stop();
        setTranslating(true);
        try {
            const translated = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].translate(script, other);
            // a translation is a new draft, so the original-language draft is kept
            onNewDraft(toDraft(translated, other, draft.topic, {
                rate: draft.rate,
                music: draft.music
            }), `Translated to ${options.langs[other].name} and saved as a new draft. The original is still in Drafts.`);
        } catch (err) {
            toast(err.message, "error");
        } finally{
            setTranslating(false);
        }
    }
    async function render() {
        const script = toScript(draft);
        if (!script.scenes.length) return toast("Write the voiceover for at least one scene first.", "error");
        preview.stop();
        const error = await onRender(script, {
            voice,
            rate,
            music
        });
        if (error) toast(error, "error");
    }
    const filled = draft.scenes.filter((s)=>s.narration.trim()).length;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "flex h-full min-h-0 flex-col",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("header", {
                className: "flex h-14 shrink-0 items-center gap-2 border-b border-line bg-panel px-3 sm:px-5",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                        label: "Back to start",
                        onClick: onBack,
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$chevron$2d$left$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__ChevronLeft$3e$__["ChevronLeft"], {
                            className: "size-5"
                        }, void 0, false, {
                            fileName: "[project]/components/Storyboard.tsx",
                            lineNumber: 226,
                            columnNumber: 11
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/components/Storyboard.tsx",
                        lineNumber: 225,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "flex min-w-0 flex-1 items-center gap-3",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "truncate text-sm font-semibold",
                                lang: draft.lang,
                                children: draft.title || "Untitled draft"
                            }, void 0, false, {
                                fileName: "[project]/components/Storyboard.tsx",
                                lineNumber: 229,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(SaveStatus, {
                                state: saveState,
                                saved: draft.id !== null
                            }, void 0, false, {
                                fileName: "[project]/components/Storyboard.tsx",
                                lineNumber: 232,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/Storyboard.tsx",
                        lineNumber: 228,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                        size: "sm",
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$languages$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Languages$3e$__["Languages"], {
                            className: "size-3.5"
                        }, void 0, false, {
                            fileName: "[project]/components/Storyboard.tsx",
                            lineNumber: 234,
                            columnNumber: 33
                        }, this),
                        onClick: translate,
                        loading: translating,
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "hidden sm:inline",
                                children: "Translate to "
                            }, void 0, false, {
                                fileName: "[project]/components/Storyboard.tsx",
                                lineNumber: 235,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                lang: other,
                                children: otherLabel
                            }, void 0, false, {
                                fileName: "[project]/components/Storyboard.tsx",
                                lineNumber: 236,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/Storyboard.tsx",
                        lineNumber: 234,
                        columnNumber: 9
                    }, this),
                    draft.id && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                        size: "sm",
                        variant: "danger",
                        "aria-label": confirmDelete ? "Confirm delete draft" : "Delete draft",
                        icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$trash$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Trash2$3e$__["Trash2"], {
                            className: "size-3.5"
                        }, void 0, false, {
                            fileName: "[project]/components/Storyboard.tsx",
                            lineNumber: 243,
                            columnNumber: 19
                        }, this),
                        onClick: ()=>{
                            if (!confirmDelete) {
                                setConfirmDelete(true);
                                setTimeout(()=>setConfirmDelete(false), 3000);
                                return;
                            }
                            preview.stop();
                            onDeleteDraft();
                        },
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                            className: confirmDelete ? "" : "hidden md:inline",
                            children: confirmDelete ? "Confirm delete" : "Delete"
                        }, void 0, false, {
                            fileName: "[project]/components/Storyboard.tsx",
                            lineNumber: 254,
                            columnNumber: 13
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/components/Storyboard.tsx",
                        lineNumber: 239,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/Storyboard.tsx",
                lineNumber: 224,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "min-h-0 flex-1 overflow-y-auto",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "mx-auto grid max-w-[880px] gap-6 px-4 py-6 sm:px-8 sm:py-8",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "grid gap-1.5",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                    htmlFor: "title",
                                    className: "field-label",
                                    children: "Title"
                                }, void 0, false, {
                                    fileName: "[project]/components/Storyboard.tsx",
                                    lineNumber: 263,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("textarea", {
                                    id: "title",
                                    lang: draft.lang,
                                    rows: 1,
                                    value: draft.title,
                                    onChange: (e)=>setDraft((d)=>({
                                                ...d,
                                                title: e.target.value.replace(/\n/g, " ")
                                            })),
                                    placeholder: "Video title",
                                    className: "field-sizing-content w-full resize-none rounded-lg border border-transparent bg-transparent px-0 py-1 font-display text-[clamp(24px,2.6vw,32px)] leading-tight font-extrabold tracking-[-0.02em] hover:border-line hover:px-3 focus:border-cobalt focus:bg-panel focus:px-3 focus:outline-none"
                                }, void 0, false, {
                                    fileName: "[project]/components/Storyboard.tsx",
                                    lineNumber: 266,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                    className: "m-0 text-[13px] text-ink-soft",
                                    children: [
                                        options.langs[draft.lang].name,
                                        ", ",
                                        draft.scenes.length,
                                        " scene",
                                        draft.scenes.length === 1 ? "" : "s",
                                        filled < draft.scenes.length && `, ${draft.scenes.length - filled} without voiceover (skipped when rendering)`
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/Storyboard.tsx",
                                    lineNumber: 275,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/Storyboard.tsx",
                            lineNumber: 262,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ol", {
                            className: "m-0 grid list-none gap-3 p-0",
                            children: draft.scenes.map((s, i)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$SceneCard$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["SceneCard"], {
                                    scene: s,
                                    index: i,
                                    total: draft.scenes.length,
                                    lang: draft.lang,
                                    active: s.uid === activeUid,
                                    listenState: listenState(s.uid),
                                    onActivate: ()=>onActive(s.uid),
                                    onChange: (patch)=>updateScene(i, patch),
                                    onMove: (dir)=>moveScene(i, dir),
                                    onRemove: ()=>removeScene(i),
                                    onListen: ()=>preview.toggle(s.uid, s.narration, voice, rate)
                                }, s.uid, false, {
                                    fileName: "[project]/components/Storyboard.tsx",
                                    lineNumber: 283,
                                    columnNumber: 15
                                }, this))
                        }, void 0, false, {
                            fileName: "[project]/components/Storyboard.tsx",
                            lineNumber: 281,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                            variant: "secondary",
                            icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$plus$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Plus$3e$__["Plus"], {
                                className: "size-4"
                            }, void 0, false, {
                                fileName: "[project]/components/Storyboard.tsx",
                                lineNumber: 299,
                                columnNumber: 45
                            }, this),
                            onClick: addScene,
                            className: "justify-self-start border-dashed",
                            children: "Add scene"
                        }, void 0, false, {
                            fileName: "[project]/components/Storyboard.tsx",
                            lineNumber: 299,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                            className: "grid gap-4 rounded-xl border border-line bg-panel p-4 sm:p-5",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                                    className: "m-0 font-display text-base font-bold",
                                    children: "Post details"
                                }, void 0, false, {
                                    fileName: "[project]/components/Storyboard.tsx",
                                    lineNumber: 304,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                                    label: "Caption",
                                    htmlFor: "caption",
                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("textarea", {
                                        id: "caption",
                                        lang: draft.lang,
                                        rows: 2,
                                        className: "field-input resize-y",
                                        value: draft.caption,
                                        onChange: (e)=>setDraft((d)=>({
                                                    ...d,
                                                    caption: e.target.value
                                                }))
                                    }, void 0, false, {
                                        fileName: "[project]/components/Storyboard.tsx",
                                        lineNumber: 306,
                                        columnNumber: 15
                                    }, this)
                                }, void 0, false, {
                                    fileName: "[project]/components/Storyboard.tsx",
                                    lineNumber: 305,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Field"], {
                                    label: "Hashtags",
                                    hint: "separate with spaces",
                                    htmlFor: "hashtags",
                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        id: "hashtags",
                                        className: "field-input",
                                        value: draft.hashtags,
                                        onChange: (e)=>setDraft((d)=>({
                                                    ...d,
                                                    hashtags: e.target.value
                                                }))
                                    }, void 0, false, {
                                        fileName: "[project]/components/Storyboard.tsx",
                                        lineNumber: 309,
                                        columnNumber: 15
                                    }, this)
                                }, void 0, false, {
                                    fileName: "[project]/components/Storyboard.tsx",
                                    lineNumber: 308,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/Storyboard.tsx",
                            lineNumber: 303,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/components/Storyboard.tsx",
                    lineNumber: 261,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/Storyboard.tsx",
                lineNumber: 260,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("footer", {
                className: "shrink-0 border-t border-line bg-panel px-3 py-3 sm:px-5",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "mx-auto flex max-w-[880px] flex-wrap items-end gap-3",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "grid min-w-[150px] flex-[2] gap-1",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                    className: "field-label",
                                    htmlFor: "voice",
                                    children: "Voice"
                                }, void 0, false, {
                                    fileName: "[project]/components/Storyboard.tsx",
                                    lineNumber: 319,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "flex gap-1.5",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("select", {
                                            id: "voice",
                                            className: "field-input h-10 py-0",
                                            value: voice,
                                            onChange: (e)=>{
                                                preview.stop();
                                                setDraft((d)=>({
                                                        ...d,
                                                        voice: e.target.value
                                                    }));
                                            },
                                            children: groupVoices(voices).map(([region, list])=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("optgroup", {
                                                    label: REGION[region] ?? region,
                                                    children: list.map((v)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
                                                            value: v,
                                                            children: voiceName(v)
                                                        }, v, false, {
                                                            fileName: "[project]/components/Storyboard.tsx",
                                                            lineNumber: 335,
                                                            columnNumber: 23
                                                        }, this))
                                                }, region, false, {
                                                    fileName: "[project]/components/Storyboard.tsx",
                                                    lineNumber: 333,
                                                    columnNumber: 19
                                                }, this))
                                        }, void 0, false, {
                                            fileName: "[project]/components/Storyboard.tsx",
                                            lineNumber: 323,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                                            "aria-label": listenState("voice") === "playing" ? "Stop voice preview" : "Listen to this voice",
                                            title: "Listen to this voice",
                                            className: "w-10 px-0!",
                                            icon: listenState("voice") === "loading" ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Spinner"], {}, void 0, false, {
                                                fileName: "[project]/components/Storyboard.tsx",
                                                lineNumber: 346,
                                                columnNumber: 60
                                            }, this) : listenState("voice") === "playing" ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$pause$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Pause$3e$__["Pause"], {
                                                className: "size-4 fill-current"
                                            }, void 0, false, {
                                                fileName: "[project]/components/Storyboard.tsx",
                                                lineNumber: 346,
                                                columnNumber: 111
                                            }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$play$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Play$3e$__["Play"], {
                                                className: "size-4 fill-current"
                                            }, void 0, false, {
                                                fileName: "[project]/components/Storyboard.tsx",
                                                lineNumber: 346,
                                                columnNumber: 155
                                            }, this),
                                            onClick: ()=>preview.toggle("voice", draft.scenes.find((s)=>s.narration.trim())?.narration || SAMPLE[draft.lang], voice, rate)
                                        }, void 0, false, {
                                            fileName: "[project]/components/Storyboard.tsx",
                                            lineNumber: 342,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/Storyboard.tsx",
                                    lineNumber: 322,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/Storyboard.tsx",
                            lineNumber: 318,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "grid min-w-[145px] flex-1 gap-1",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                    className: "field-label",
                                    htmlFor: "rate",
                                    children: "Speed"
                                }, void 0, false, {
                                    fileName: "[project]/components/Storyboard.tsx",
                                    lineNumber: 352,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("select", {
                                    id: "rate",
                                    className: "field-input h-10 py-0",
                                    value: rate,
                                    onChange: (e)=>{
                                        preview.stop();
                                        setDraft((d)=>({
                                                ...d,
                                                rate: e.target.value
                                            }));
                                    },
                                    children: RATES.map((r)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
                                            value: r.value,
                                            children: r.label
                                        }, r.value, false, {
                                            fileName: "[project]/components/Storyboard.tsx",
                                            lineNumber: 365,
                                            columnNumber: 17
                                        }, this))
                                }, void 0, false, {
                                    fileName: "[project]/components/Storyboard.tsx",
                                    lineNumber: 355,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/Storyboard.tsx",
                            lineNumber: 351,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "grid min-w-[125px] flex-1 gap-1",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                    className: "field-label",
                                    htmlFor: "music",
                                    children: "Music"
                                }, void 0, false, {
                                    fileName: "[project]/components/Storyboard.tsx",
                                    lineNumber: 372,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("select", {
                                    id: "music",
                                    className: "field-input h-10 py-0",
                                    value: music,
                                    onChange: (e)=>setDraft((d)=>({
                                                ...d,
                                                music: e.target.value
                                            })),
                                    children: [
                                        options.music.length > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
                                            value: "",
                                            children: "Random track"
                                        }, void 0, false, {
                                            fileName: "[project]/components/Storyboard.tsx",
                                            lineNumber: 376,
                                            columnNumber: 44
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
                                            value: "none",
                                            children: "No music"
                                        }, void 0, false, {
                                            fileName: "[project]/components/Storyboard.tsx",
                                            lineNumber: 377,
                                            columnNumber: 15
                                        }, this),
                                        options.music.map((m)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
                                                value: m,
                                                children: m.replace(/\.mp3$/i, "")
                                            }, m, false, {
                                                fileName: "[project]/components/Storyboard.tsx",
                                                lineNumber: 379,
                                                columnNumber: 17
                                            }, this))
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/components/Storyboard.tsx",
                                    lineNumber: 375,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/components/Storyboard.tsx",
                            lineNumber: 371,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Button"], {
                            variant: "primary",
                            onClick: render,
                            loading: rendering,
                            icon: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$clapperboard$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Clapperboard$3e$__["Clapperboard"], {
                                className: "size-4"
                            }, void 0, false, {
                                fileName: "[project]/components/Storyboard.tsx",
                                lineNumber: 385,
                                columnNumber: 80
                            }, this),
                            className: "w-full sm:w-auto",
                            children: rendering ? "Rendering…" : "Render video"
                        }, void 0, false, {
                            fileName: "[project]/components/Storyboard.tsx",
                            lineNumber: 385,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/components/Storyboard.tsx",
                    lineNumber: 317,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/Storyboard.tsx",
                lineNumber: 316,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/Storyboard.tsx",
        lineNumber: 222,
        columnNumber: 5
    }, this);
}
_s(Storyboard, "vzkL8Zc/j8FCnojV6WGP7FkLk9U=", false, function() {
    return [
        __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useToast"],
        __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$useVoicePreview$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useVoicePreview"]
    ];
});
_c1 = Storyboard;
var _c, _c1;
__turbopack_context__.k.register(_c, "SaveStatus");
__turbopack_context__.k.register(_c1, "Storyboard");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/TopBar.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "TopBar",
    ()=>TopBar
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$panel$2d$left$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__PanelLeft$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/panel-left.mjs [app-client] (ecmascript) <export default as PanelLeft>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$smartphone$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Smartphone$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/smartphone.mjs [app-client] (ecmascript) <export default as Smartphone>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/client/app-dir/link.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/components/ui.tsx [app-client] (ecmascript)");
;
;
;
;
function Status({ ok, warn, children, title }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
        title: title,
        className: "hidden items-center gap-1.5 text-[12.5px] text-ink-soft md:inline-flex",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                className: `size-1.5 rounded-full ${ok ? "bg-ok" : warn ? "bg-warn" : "bg-danger"}`
            }, void 0, false, {
                fileName: "[project]/components/TopBar.tsx",
                lineNumber: 9,
                columnNumber: 7
            }, this),
            children
        ]
    }, void 0, true, {
        fileName: "[project]/components/TopBar.tsx",
        lineNumber: 8,
        columnNumber: 5
    }, this);
}
_c = Status;
function TopBar({ options, onOpenLibrary, onOpenPreview, showPreviewButton }) {
    const keys = options?.keys;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("header", {
        className: "flex h-14 shrink-0 items-center gap-3 border-b border-line bg-panel px-3 sm:px-4",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                label: "Open library",
                onClick: onOpenLibrary,
                className: "lg:hidden",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$panel$2d$left$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__PanelLeft$3e$__["PanelLeft"], {
                    className: "size-5"
                }, void 0, false, {
                    fileName: "[project]/components/TopBar.tsx",
                    lineNumber: 30,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/components/TopBar.tsx",
                lineNumber: 29,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"], {
                href: "/",
                className: "inline-flex items-center font-display text-lg leading-none font-extrabold tracking-tight text-ink no-underline",
                "aria-label": "Shorts Studio home",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        "aria-hidden": "true",
                        className: "mr-2 h-[22px] w-3 rounded-[3px] bg-ink shadow-[inset_0_-6px_0_var(--color-caption)]"
                    }, void 0, false, {
                        fileName: "[project]/components/TopBar.tsx",
                        lineNumber: 33,
                        columnNumber: 9
                    }, this),
                    "Shorts",
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "ml-1 rounded-[2px] bg-caption px-1 py-0.5",
                        children: "Studio"
                    }, void 0, false, {
                        fileName: "[project]/components/TopBar.tsx",
                        lineNumber: 35,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/TopBar.tsx",
                lineNumber: 32,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "ml-auto flex items-center gap-4",
                children: [
                    keys && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Status, {
                                ok: keys.anthropic,
                                title: keys.anthropic ? "Claude writes, translates and imports scripts" : "Add ANTHROPIC_API_KEY to .env and restart the engine",
                                children: keys.anthropic ? "Claude connected" : "Claude not connected"
                            }, void 0, false, {
                                fileName: "[project]/components/TopBar.tsx",
                                lineNumber: 40,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Status, {
                                ok: !!keys.stock,
                                warn: true,
                                title: keys.stock ? "Stock footage search is on" : "Add a free PIXABAY_API_KEY to .env for real footage",
                                children: keys.stock ? `Footage: ${keys.stock === "pixabay" ? "Pixabay" : "Pexels"}` : "Footage: gradients only"
                            }, void 0, false, {
                                fileName: "[project]/components/TopBar.tsx",
                                lineNumber: 43,
                                columnNumber: 13
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/TopBar.tsx",
                        lineNumber: 39,
                        columnNumber: 11
                    }, this),
                    showPreviewButton && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$components$2f$ui$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["IconButton"], {
                        label: "Open preview",
                        onClick: onOpenPreview,
                        className: "wide:hidden",
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$smartphone$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Smartphone$3e$__["Smartphone"], {
                            className: "size-5"
                        }, void 0, false, {
                            fileName: "[project]/components/TopBar.tsx",
                            lineNumber: 50,
                            columnNumber: 13
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/components/TopBar.tsx",
                        lineNumber: 49,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/TopBar.tsx",
                lineNumber: 37,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/TopBar.tsx",
        lineNumber: 28,
        columnNumber: 5
    }, this);
}
_c1 = TopBar;
var _c, _c1;
__turbopack_context__.k.register(_c, "Status");
__turbopack_context__.k.register(_c1, "TopBar");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/components/ui.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "Button",
    ()=>Button,
    "Chip",
    ()=>Chip,
    "Drawer",
    ()=>Drawer,
    "Field",
    ()=>Field,
    "IconButton",
    ()=>IconButton,
    "Message",
    ()=>Message,
    "Segmented",
    ()=>Segmented,
    "Spinner",
    ()=>Spinner,
    "Tabs",
    ()=>Tabs,
    "ToastProvider",
    ()=>ToastProvider,
    "buttonClass",
    ()=>buttonClass,
    "useToast",
    ()=>useToast
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$loader$2d$circle$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Loader2$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/loader-circle.mjs [app-client] (ecmascript) <export default as Loader2>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$x$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__X$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/x.mjs [app-client] (ecmascript) <export default as X>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature(), _s1 = __turbopack_context__.k.signature(), _s2 = __turbopack_context__.k.signature();
"use client";
;
;
const VARIANTS = {
    primary: "bg-cobalt text-white border-cobalt hover:bg-cobalt-deep hover:border-cobalt-deep",
    secondary: "bg-panel text-ink border-line hover:border-ink-soft/60 hover:bg-paper/60",
    ghost: "bg-transparent text-ink-soft border-transparent hover:bg-ink/[0.05] hover:text-ink",
    danger: "bg-transparent text-danger border-transparent hover:bg-danger/[0.07]"
};
const SIZES = {
    sm: "h-8 gap-1.5 px-2.5 text-[13px]",
    md: "h-10 gap-2 px-4 text-sm"
};
function buttonClass(variant = "secondary", size = "md", extra = "") {
    return `inline-flex shrink-0 cursor-pointer items-center justify-center rounded-lg border font-semibold whitespace-nowrap no-underline transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${SIZES[size]} ${extra}`;
}
function Button({ variant = "secondary", size = "md", loading = false, icon, className = "", children, disabled, ...rest }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
        type: "button",
        ...rest,
        disabled: disabled || loading,
        className: buttonClass(variant, size, className),
        children: [
            loading ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$loader$2d$circle$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Loader2$3e$__["Loader2"], {
                className: size === "sm" ? "size-3.5 animate-spin" : "size-4 animate-spin",
                "aria-hidden": true
            }, void 0, false, {
                fileName: "[project]/components/ui.tsx",
                lineNumber: 52,
                columnNumber: 18
            }, this) : icon,
            children
        ]
    }, void 0, true, {
        fileName: "[project]/components/ui.tsx",
        lineNumber: 51,
        columnNumber: 5
    }, this);
}
_c = Button;
function IconButton({ label, children, className = "", tone = "default", ...rest }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
        type: "button",
        "aria-label": label,
        title: label,
        ...rest,
        className: `grid size-8 shrink-0 cursor-pointer place-items-center rounded-lg text-ink-soft transition-colors hover:bg-ink/[0.06] disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent ${tone === "danger" ? "hover:text-danger" : "hover:text-ink"} ${className}`,
        children: children
    }, void 0, false, {
        fileName: "[project]/components/ui.tsx",
        lineNumber: 67,
        columnNumber: 5
    }, this);
}
_c1 = IconButton;
function Spinner({ className = "size-4" }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$loader$2d$circle$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Loader2$3e$__["Loader2"], {
        className: `animate-spin ${className}`,
        "aria-hidden": true
    }, void 0, false, {
        fileName: "[project]/components/ui.tsx",
        lineNumber: 82,
        columnNumber: 10
    }, this);
}
_c2 = Spinner;
function Field({ label, htmlFor, hint, children }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "grid min-w-0 gap-1.5",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                className: "field-label",
                htmlFor: htmlFor,
                children: [
                    label,
                    " ",
                    hint && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "font-normal text-ink-soft/80",
                        children: hint
                    }, void 0, false, {
                        fileName: "[project]/components/ui.tsx",
                        lineNumber: 91,
                        columnNumber: 26
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/ui.tsx",
                lineNumber: 90,
                columnNumber: 7
            }, this),
            children
        ]
    }, void 0, true, {
        fileName: "[project]/components/ui.tsx",
        lineNumber: 89,
        columnNumber: 5
    }, this);
}
_c3 = Field;
function Message({ text, error }) {
    if (!text) return null;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
        role: error ? "alert" : "status",
        className: `m-0 text-[13.5px] ${error ? "text-danger" : "text-ink-soft"}`,
        children: text
    }, void 0, false, {
        fileName: "[project]/components/ui.tsx",
        lineNumber: 101,
        columnNumber: 5
    }, this);
}
_c4 = Message;
function Segmented({ name, value, options, onChange, size = "md" }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        role: "radiogroup",
        className: `inline-flex rounded-lg bg-ink/[0.06] p-0.5 ${size === "sm" ? "h-8" : "h-10"}`,
        children: options.map((o)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                className: "relative cursor-pointer",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                        type: "radio",
                        name: name,
                        value: o.value,
                        checked: value === o.value,
                        onChange: ()=>onChange(o.value),
                        className: "peer sr-only"
                    }, void 0, false, {
                        fileName: "[project]/components/ui.tsx",
                        lineNumber: 125,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        lang: o.lang,
                        className: `flex h-full items-center rounded-md px-3 font-semibold text-ink-soft transition-colors peer-checked:bg-panel peer-checked:text-ink peer-checked:shadow-sm peer-focus-visible:outline-2 peer-focus-visible:outline-cobalt ${size === "sm" ? "text-[12.5px]" : "text-[13.5px]"}`,
                        children: o.label
                    }, void 0, false, {
                        fileName: "[project]/components/ui.tsx",
                        lineNumber: 126,
                        columnNumber: 11
                    }, this)
                ]
            }, o.value, true, {
                fileName: "[project]/components/ui.tsx",
                lineNumber: 124,
                columnNumber: 9
            }, this))
    }, void 0, false, {
        fileName: "[project]/components/ui.tsx",
        lineNumber: 122,
        columnNumber: 5
    }, this);
}
_c5 = Segmented;
function Tabs({ value, onChange, items, label }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        role: "tablist",
        "aria-label": label,
        className: "flex gap-5 border-b border-line",
        children: items.map((it)=>{
            const active = it.value === value;
            return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                type: "button",
                role: "tab",
                "aria-selected": active,
                onClick: ()=>onChange(it.value),
                className: `-mb-px flex cursor-pointer items-center gap-1.5 border-b-2 bg-transparent px-0.5 pt-1 pb-2.5 text-sm font-semibold transition-colors ${active ? "border-ink text-ink" : "border-transparent text-ink-soft hover:text-ink"}`,
                children: [
                    it.label,
                    it.count !== undefined && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: `rounded-full px-1.5 py-px text-[11px] leading-4 ${active ? "bg-ink text-white" : "bg-ink/[0.07] text-ink-soft"}`,
                        children: it.count
                    }, void 0, false, {
                        fileName: "[project]/components/ui.tsx",
                        lineNumber: 169,
                        columnNumber: 15
                    }, this)
                ]
            }, it.value, true, {
                fileName: "[project]/components/ui.tsx",
                lineNumber: 157,
                columnNumber: 11
            }, this);
        })
    }, void 0, false, {
        fileName: "[project]/components/ui.tsx",
        lineNumber: 153,
        columnNumber: 5
    }, this);
}
_c6 = Tabs;
function Chip({ children, tone = "neutral" }) {
    const t = {
        neutral: "bg-ink/[0.06] text-ink-soft",
        caption: "bg-caption text-ink",
        ink: "bg-ink text-white"
    }[tone];
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
        className: `inline-flex items-center rounded px-1.5 py-0.5 text-[11px] leading-none font-semibold ${t}`,
        children: children
    }, void 0, false, {
        fileName: "[project]/components/ui.tsx",
        lineNumber: 182,
        columnNumber: 10
    }, this);
}
_c7 = Chip;
const ToastContext = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["createContext"])(_c8 = ()=>{});
_c9 = ToastContext;
const useToast = ()=>{
    _s();
    return (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useContext"])(ToastContext);
};
_s(useToast, "gDsCjeeItUuvgOWf1v4qoK9RF6k=");
function ToastProvider({ children }) {
    _s1();
    const [toasts, setToasts] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])([]);
    const nextId = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(0);
    const push = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "ToastProvider.useCallback[push]": (text, tone = "info")=>{
            const id = ++nextId.current;
            setToasts({
                "ToastProvider.useCallback[push]": (t)=>[
                        ...t.slice(-2),
                        {
                            id,
                            text,
                            tone
                        }
                    ]
            }["ToastProvider.useCallback[push]"]);
            setTimeout({
                "ToastProvider.useCallback[push]": ()=>setToasts({
                        "ToastProvider.useCallback[push]": (t)=>t.filter({
                                "ToastProvider.useCallback[push]": (x)=>x.id !== id
                            }["ToastProvider.useCallback[push]"])
                    }["ToastProvider.useCallback[push]"])
            }["ToastProvider.useCallback[push]"], tone === "error" ? 7000 : 3500);
        }
    }["ToastProvider.useCallback[push]"], []);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(ToastContext.Provider, {
        value: push,
        children: [
            children,
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                "aria-live": "polite",
                className: "pointer-events-none fixed right-4 bottom-4 z-50 grid w-[min(380px,calc(100vw-32px))] gap-2",
                children: toasts.map((t)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        role: t.tone === "error" ? "alert" : "status",
                        className: `pointer-events-auto flex items-start gap-3 rounded-xl px-4 py-3 text-[13.5px] shadow-[0_12px_32px_-12px_rgb(24_32_46/0.45)] ${t.tone === "error" ? "bg-danger text-white" : "bg-ink text-white"}`,
                        children: [
                            t.tone === "success" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                "aria-hidden": true,
                                className: "mt-1 size-2 shrink-0 rounded-full bg-caption"
                            }, void 0, false, {
                                fileName: "[project]/components/ui.tsx",
                                lineNumber: 211,
                                columnNumber: 38
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "flex-1",
                                children: t.text
                            }, void 0, false, {
                                fileName: "[project]/components/ui.tsx",
                                lineNumber: 212,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                type: "button",
                                "aria-label": "Dismiss",
                                onClick: ()=>setToasts((all)=>all.filter((x)=>x.id !== t.id)),
                                className: "-mr-1 cursor-pointer rounded bg-transparent text-white/70 hover:text-white",
                                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$x$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__X$3e$__["X"], {
                                    className: "size-4"
                                }, void 0, false, {
                                    fileName: "[project]/components/ui.tsx",
                                    lineNumber: 219,
                                    columnNumber: 15
                                }, this)
                            }, void 0, false, {
                                fileName: "[project]/components/ui.tsx",
                                lineNumber: 213,
                                columnNumber: 13
                            }, this)
                        ]
                    }, t.id, true, {
                        fileName: "[project]/components/ui.tsx",
                        lineNumber: 204,
                        columnNumber: 11
                    }, this))
            }, void 0, false, {
                fileName: "[project]/components/ui.tsx",
                lineNumber: 202,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/ui.tsx",
        lineNumber: 200,
        columnNumber: 5
    }, this);
}
_s1(ToastProvider, "Gvd7s/KuV/FmsyUKKsKzNZMDINU=");
_c10 = ToastProvider;
function Drawer({ open, side, onClose, label, children }) {
    _s2();
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "Drawer.useEffect": ()=>{
            if (!open) return;
            const onKey = {
                "Drawer.useEffect.onKey": (e)=>e.key === "Escape" && onClose()
            }["Drawer.useEffect.onKey"];
            window.addEventListener("keydown", onKey);
            return ({
                "Drawer.useEffect": ()=>window.removeEventListener("keydown", onKey)
            })["Drawer.useEffect"];
        }
    }["Drawer.useEffect"], [
        open,
        onClose
    ]);
    if (!open) return null;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "fixed inset-0 z-40",
        role: "dialog",
        "aria-modal": "true",
        "aria-label": label,
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "absolute inset-0 bg-ink/40",
                onClick: onClose
            }, void 0, false, {
                fileName: "[project]/components/ui.tsx",
                lineNumber: 252,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: `absolute top-0 bottom-0 flex w-[min(360px,90vw)] flex-col bg-paper shadow-2xl ${side === "left" ? "left-0" : "right-0"}`,
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "flex h-14 shrink-0 items-center justify-between border-b border-line bg-panel px-4",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "font-display text-base font-bold",
                                children: label
                            }, void 0, false, {
                                fileName: "[project]/components/ui.tsx",
                                lineNumber: 257,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(IconButton, {
                                label: "Close",
                                onClick: onClose,
                                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$x$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__X$3e$__["X"], {
                                    className: "size-5"
                                }, void 0, false, {
                                    fileName: "[project]/components/ui.tsx",
                                    lineNumber: 259,
                                    columnNumber: 13
                                }, this)
                            }, void 0, false, {
                                fileName: "[project]/components/ui.tsx",
                                lineNumber: 258,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/components/ui.tsx",
                        lineNumber: 256,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "min-h-0 flex-1 overflow-y-auto",
                        children: children
                    }, void 0, false, {
                        fileName: "[project]/components/ui.tsx",
                        lineNumber: 262,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/components/ui.tsx",
                lineNumber: 253,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/components/ui.tsx",
        lineNumber: 251,
        columnNumber: 5
    }, this);
}
_s2(Drawer, "OD7bBpZva5O2jO+Puf00hKivP7c=");
_c11 = Drawer;
var _c, _c1, _c2, _c3, _c4, _c5, _c6, _c7, _c8, _c9, _c10, _c11;
__turbopack_context__.k.register(_c, "Button");
__turbopack_context__.k.register(_c1, "IconButton");
__turbopack_context__.k.register(_c2, "Spinner");
__turbopack_context__.k.register(_c3, "Field");
__turbopack_context__.k.register(_c4, "Message");
__turbopack_context__.k.register(_c5, "Segmented");
__turbopack_context__.k.register(_c6, "Tabs");
__turbopack_context__.k.register(_c7, "Chip");
__turbopack_context__.k.register(_c8, "ToastContext$createContext");
__turbopack_context__.k.register(_c9, "ToastContext");
__turbopack_context__.k.register(_c10, "ToastProvider");
__turbopack_context__.k.register(_c11, "Drawer");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/lib/api.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

// Typed client for the Python engine (crcontent/web.py). The browser calls it directly.
__turbopack_context__.s([
    "API_BASE",
    ()=>API_BASE,
    "ApiError",
    ()=>ApiError,
    "api",
    ()=>api,
    "fileUrl",
    ()=>fileUrl,
    "outputUrl",
    ()=>outputUrl
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = /*#__PURE__*/ __turbopack_context__.i("[project]/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
const desktopEngine = ("TURBOPACK compile-time truthy", 1) ? window.__ENGINE_URL__ : "TURBOPACK unreachable";
const API_BASE = (desktopEngine ?? __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
class ApiError extends Error {
}
// Quick calls give up after this long, so a request lost while the engine restarts can't hang the UI.
// Claude, upload and render calls pass `timeout: 0` (no limit).
const TIMEOUT_MS = 15_000;
async function request(path, init = {}) {
    const { json, timeout = TIMEOUT_MS, ...rest } = init;
    let res;
    try {
        res = await fetch(API_BASE + path, {
            ...rest,
            headers: json !== undefined ? {
                "Content-Type": "application/json",
                ...rest.headers
            } : rest.headers,
            body: json !== undefined ? JSON.stringify(json) : rest.body,
            signal: timeout ? AbortSignal.timeout(timeout) : rest.signal
        });
    } catch (e) {
        if (e.name === "TimeoutError") throw new ApiError("The video engine didn't answer in time. Try again.");
        throw new ApiError(desktopEngine ? "Can't reach the video engine. Restart the app; if it keeps happening, see engine.log in the app's data folder." : "Can't reach the video engine. Start it with: npm run dev (in frontend/), or python app.py");
    }
    if (!res.ok) {
        const data = await res.json().catch(()=>({}));
        throw new ApiError(typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`);
    }
    return res.json();
}
const fileUrl = (projectPath)=>`${API_BASE}/${projectPath.split("/").map(encodeURIComponent).join("/")}`;
const outputUrl = (folder, file)=>`${API_BASE}/media/${encodeURIComponent(folder)}/${file}`;
const api = {
    options: ()=>request("/api/options"),
    writeScript: (body)=>request("/api/script", {
            method: "POST",
            json: body,
            timeout: 0
        }),
    importScript: (text)=>request("/api/import", {
            method: "POST",
            json: {
                text,
                lang: "auto"
            },
            timeout: 0
        }),
    translate: (script, target)=>request("/api/translate", {
            method: "POST",
            json: {
                script,
                target
            },
            timeout: 0
        }),
    ideas: (narration, current)=>request("/api/ideas", {
            method: "POST",
            json: {
                narration,
                current
            },
            timeout: 0
        }),
    footage: (q, kind)=>request(`/api/footage?q=${encodeURIComponent(q)}&kind=${kind}`),
    designFootage: (prompt, narration)=>request("/api/footage/design", {
            method: "POST",
            json: {
                prompt,
                narration
            },
            timeout: 0
        }),
    pick: (r)=>request("/api/footage/pick", {
            method: "POST",
            json: {
                source: r.source,
                kind: r.kind,
                id: r.id
            },
            timeout: 0
        }),
    upload: (file)=>{
        const form = new FormData();
        form.append("file", file);
        return request("/api/upload", {
            method: "POST",
            body: form,
            timeout: 0
        });
    },
    render: (body)=>request("/api/render", {
            method: "POST",
            json: body,
            timeout: 0
        }),
    writeSong: (body)=>request("/api/song/write", {
            method: "POST",
            json: body,
            timeout: 0
        }),
    composeSong: (body)=>request("/api/song/compose", {
            method: "POST",
            json: body,
            timeout: 0
        }),
    importSong: (body)=>{
        const form = new FormData();
        form.append("file", body.file);
        form.append("title", body.title);
        form.append("lyrics", body.lyrics);
        form.append("lang", body.lang);
        form.append("aspect", body.aspect);
        return request("/api/song/import", {
            method: "POST",
            body: form,
            timeout: 0
        });
    },
    lyrics: (name)=>request(`/api/videos/${encodeURIComponent(name)}/lyrics`),
    saveLyrics: (name, lines)=>request(`/api/videos/${encodeURIComponent(name)}/lyrics`, {
            method: "PUT",
            json: {
                lines
            }
        }),
    resyncLyrics: (name)=>request(`/api/videos/${encodeURIComponent(name)}/lyrics/sync`, {
            method: "POST",
            timeout: 0
        }),
    musicVideo: (name, settings)=>request(`/api/videos/${encodeURIComponent(name)}/music-video`, {
            method: "POST",
            json: settings,
            timeout: 0
        }),
    videoIdeas: (name)=>request(`/api/videos/${encodeURIComponent(name)}/video-ideas`, {
            method: "POST",
            timeout: 0
        }),
    drafts: ()=>request("/api/drafts"),
    draft: (id)=>request(`/api/drafts/${encodeURIComponent(id)}`),
    createDraft: (d)=>request("/api/drafts", {
            method: "POST",
            json: d
        }),
    saveDraft: (id, d)=>request(`/api/drafts/${encodeURIComponent(id)}`, {
            method: "PUT",
            json: d
        }),
    deleteDraft: (id)=>request(`/api/drafts/${encodeURIComponent(id)}`, {
            method: "DELETE"
        }),
    job: (id)=>request(`/api/jobs/${id}`),
    videos: ()=>request("/api/videos"),
    video: (name)=>request(`/api/videos/${encodeURIComponent(name)}`),
    makeThumbnail: (name, cover)=>// a designed cover may ask Claude for a new layout, which takes a minute or two
        request(`/api/videos/${encodeURIComponent(name)}/thumbnail`, {
            method: "POST",
            json: cover,
            timeout: cover.style === "designed" ? 0 : 60_000
        }),
    suggestThumbnails: (name, idea = "")=>request(`/api/videos/${encodeURIComponent(name)}/thumbnail/suggest`, {
            method: "POST",
            json: {
                idea
            },
            timeout: 0
        }),
    deleteVideo: (name)=>request(`/api/videos/${encodeURIComponent(name)}`, {
            method: "DELETE"
        }),
    /** Returns an mp3 blob for the voice preview. */ speak: async (text, voice, rate)=>{
        let res;
        try {
            res = await fetch(`${API_BASE}/api/speak`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    text,
                    voice,
                    rate
                })
            });
        } catch  {
            throw new ApiError("Can't reach the video engine.");
        }
        if (!res.ok) throw new ApiError((await res.json().catch(()=>({}))).detail ?? `Preview failed (${res.status})`);
        return res.blob();
    }
};
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/lib/format.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

/** "just now", "5 min ago", "3 h ago", "yesterday", "Oct 6" */ __turbopack_context__.s([
    "isImagePath",
    ()=>isImagePath,
    "langCode",
    ()=>langCode,
    "relativeTime",
    ()=>relativeTime
]);
function relativeTime(iso, now = Date.now()) {
    if (!iso) return "";
    const t = new Date(iso).getTime();
    if (Number.isNaN(t)) return "";
    const s = Math.max(0, Math.round((now - t) / 1000));
    if (s < 60) return "just now";
    const m = Math.round(s / 60);
    if (m < 60) return `${m} min ago`;
    const h = Math.round(m / 60);
    if (h < 24) return `${h} h ago`;
    if (h < 48) return "yesterday";
    return new Date(t).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric"
    });
}
const langCode = (lang)=>lang === "km" ? "ខ្មែរ" : "EN";
const isImagePath = (p)=>/\.(jpe?g|png|webp)$/i.test(p);
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/lib/useVoicePreview.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "useVoicePreview",
    ()=>useVoicePreview
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api.ts [app-client] (ecmascript)");
var _s = __turbopack_context__.k.signature();
"use client";
;
;
function useVoicePreview(onError) {
    _s();
    const audio = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    const urlRef = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    const activeRef = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    const [active, setActive] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [loading, setLoading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const stop = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "useVoicePreview.useCallback[stop]": ()=>{
            audio.current?.pause();
            activeRef.current = null;
            setActive(null);
            setLoading(false);
        }
    }["useVoicePreview.useCallback[stop]"], []);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "useVoicePreview.useEffect": ()=>{
            const a = new Audio();
            a.onended = ({
                "useVoicePreview.useEffect": ()=>{
                    activeRef.current = null;
                    setActive(null);
                }
            })["useVoicePreview.useEffect"];
            audio.current = a;
            return ({
                "useVoicePreview.useEffect": ()=>{
                    a.pause();
                    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
                }
            })["useVoicePreview.useEffect"];
        }
    }["useVoicePreview.useEffect"], []);
    const toggle = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "useVoicePreview.useCallback[toggle]": async (id, text, voice, rate)=>{
            if (activeRef.current === id) return stop();
            stop();
            if (!text.trim()) return onError("Write some narration first, then listen.");
            activeRef.current = id;
            setActive(id);
            setLoading(true);
            try {
                const blob = await __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["api"].speak(text, voice, rate);
                if (activeRef.current !== id || !audio.current) return; // another button was clicked meanwhile
                if (urlRef.current) URL.revokeObjectURL(urlRef.current);
                urlRef.current = URL.createObjectURL(blob);
                audio.current.src = urlRef.current;
                setLoading(false);
                await audio.current.play();
            } catch (err) {
                stop();
                onError(err.message);
            }
        }
    }["useVoicePreview.useCallback[toggle]"], [
        onError,
        stop
    ]);
    return {
        active,
        loading,
        toggle,
        stop
    };
}
_s(useVoicePreview, "LDQdIoeZz5JA1f+ugmMO1BpfJRA=");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
]);

//# sourceMappingURL=_1miy4q5._.js.map