"use client";

import { Copy, Cpu, Film, ImageIcon, Sparkles, Trash2, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { CoverLoop, CoverMode, GpuLoopJob, LivingRegion, LoopMotion } from "@/lib/api";
import { LivingRegions } from "./LivingRegions";
import { Button, Spinner, buttonClass, useToast } from "./ui";

/** Picture or Animated: which cover a song's video holds and its thumbnail is made from. Same in both editors. */
export function CoverSwitch({ mode, onChange, disabled }: { mode: CoverMode; onChange: (m: CoverMode) => void; disabled?: boolean }) {
  const options = [
    ["picture", "Picture", <ImageIcon key="i" className="size-3.5" aria-hidden />],
    ["animated", "Animated", <Film key="f" className="size-3.5" aria-hidden />],
  ] as const;
  return (
    <div role="radiogroup" aria-label="Cover type" className="inline-flex rounded-lg border border-line p-0.5">
      {options.map(([m, label, icon]) => (
        <button key={m} type="button" role="radio" aria-checked={mode === m} disabled={disabled}
          className={`inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-sm font-semibold transition-colors ${mode === m ? "bg-cobalt text-white" : "text-ink-soft hover:text-ink"}`}
          onClick={() => m !== mode && onChange(m)}>{icon}{label}</button>
      ))}
    </div>
  );
}

/** The calls behind one editor's animated cover; each returns that editor's fresh state. */
export type CoverLoopCalls<T> = {
  savePrompt: (prompt: string) => Promise<T>;
  saveMovement: (movement: string) => Promise<T>; // what a character loop is told moves
  saveRegions?: (regions: LivingRegion[]) => Promise<T>; // a living loop's regions (editors without it: no Living mode)
  preview?: (regions: LivingRegion[]) => Promise<readonly [T, string]>; // a quick living preview: state, preview file
  gpu: (effects: string[], useCover: boolean, again: boolean, motion: LoopMotion, intensity: number) => Promise<T>; // starts a GPU job
  status: () => Promise<GpuLoopJob>; // that job, as it goes
  refresh: () => Promise<T>; // the editor's state again, once the job is done
  draw: (again: boolean) => Promise<T>; // Gemini's animated drawing (one request)
  upload: (file: File) => Promise<T>;
  reuse: (from: string) => Promise<T>;
  remove: () => Promise<T>;
};

/**
 * The animated cover: a seamless loop that plays instead of the still cover picture. Drawn on this computer's GPU and
 * brought to life (free), drawn by Gemini as moving artwork (one request), your own clip, or reused from another song
 * (both editors' songs). Laid out like a picture's card.
 */
export function AnimatedCover<T>({ state, src, calls, onSaved, videoPrompt, disabled, hasPicture = false, picture = "", previewUrl }: {
  state: CoverLoop;
  src: string; // the loop's url ("" = none yet)
  calls: CoverLoopCalls<T>;
  onSaved: (next: T) => void;
  videoPrompt?: string; // a prompt for other text-to-video tools
  disabled?: boolean; // something else on the page is busy
  hasPicture?: boolean; // the song has a cover picture that can be brought to life
  picture?: string; // the cover picture's url (the living editor draws on it)
  previewUrl?: (file: string) => string; // a file in the song folder as a url
}) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [prompt, setPrompt] = useState<string | null>(null); // null = the saved one
  const text = prompt ?? state.loop_prompt;
  const [effects, setEffects] = useState<string[] | null>(null); // null = the saved choice
  const moving = effects ?? state.loop_effects;
  const [useCover, setUseCover] = useState<boolean | null>(null); // null = parallax animates the cover, the others draw
  const [working, setWorking] = useState("");
  const [motion, setMotion] = useState<LoopMotion | null>(null); // null = the last one used
  const how = motion ?? state.loop_motion;
  const [intensity, setIntensity] = useState<number | null>(null); // null = the last one used
  const strength = intensity ?? state.loop_intensity;
  const [movement, setMovement] = useState<string | null>(null); // null = the saved one
  const moves = movement ?? state.loop_movement;
  const movedEdit = movement !== null && movement !== state.loop_movement;
  const living = !!(calls.preview && calls.saveRegions && picture && previewUrl);
  const cover = hasPicture && (how === "living" || (useCover ?? how === "parallax")); // living marks the cover itself
  const [regions, setRegions] = useState<LivingRegion[] | null>(null); // null = the saved ones
  const marked = regions ?? state.loop_regions;
  const [preview, setPreview] = useState("");
  const unmarked = how === "living" && !marked.length; // Living has nothing to move until a box is drawn
  const [job, setJob] = useState<GpuLoopJob | null>(state.job.state === "running" ? state.job : null);
  /** Follow the GPU job until it's done, then show the new loop. */
  const follow = useCallback(async () => {
    for (;;) {
      const st = await calls.status();
      setJob(st);
      if (st.state === "done") return void onSaved(await calls.refresh());
      if (st.state === "error") throw new Error(st.error || "The animated cover could not be made.");
      if (st.state === "idle") return;
      await new Promise((r) => setTimeout(r, 1500));
    }
  }, [calls, onSaved]);
  const resumed = useRef(false);
  useEffect(() => {
    // a GPU loop may still be running from before this page was opened: follow it (in a timer callback, so the
    // first setState isn't in the effect body)
    if (resumed.current || state.job.state !== "running") return;
    const t = setTimeout(() => {
      resumed.current = true;
      setBusy(true);
      follow().catch((e: Error) => toast(e.message, "error")).finally(() => { setBusy(false); setJob(null); });
    }, 0);
    return () => clearTimeout(t);
  }, [state.job.state, follow, toast]);
  const copy = (t: string) => { void navigator.clipboard.writeText(t); toast("Prompt copied", "success"); };
  async function run(work: () => Promise<T>, what = "") {
    setBusy(true);
    setWorking(what);
    try {
      onSaved(await work());
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }
  const edited = prompt !== null && prompt !== state.loop_prompt;
  const off = busy || !!disabled;
  const pct = job && job.total > 0 ? Math.round((job.done / job.total) * 100) : null;

  return (
    <div className="well grid gap-3 p-3 sm:grid-cols-[minmax(0,13rem)_1fr]">
      <div className="grid content-start gap-2">
        <div className="grid aspect-video w-full place-items-center overflow-hidden rounded-lg bg-black">
          {src ? (
            <video key={src} src={src} className="size-full object-cover" autoPlay loop muted playsInline aria-label="Animated cover" />
          ) : busy ? <Spinner className="size-5" /> : <Film className="size-6 text-ink-soft" aria-hidden />}
        </div>
        <div className="text-sm font-semibold">Animated <span className="font-normal text-ink-soft">loops every {state.loop_seconds}s</span></div>
        {src && state.loop_seam && (
          <div className={`text-xs ${state.loop_seam.ok ? "text-ink-soft" : "text-amber-600"}`}
            title={`End-to-start change ${state.loop_seam.jump} vs typical step ${state.loop_seam.step}`}>
            {state.loop_seam.ok ? "Loop seam: smooth" : "Loop seam: visible jump where it repeats. Make it again."}
          </div>
        )}
        {src && state.loop_motion === "character" && state.loop_changed != null && state.loop_changed > state.loop_change_max && (
          <div className="text-xs text-amber-600">
            The video model redrew {Math.round(state.loop_changed * 100)}% of the picture instead of animating it (the best of 3 takes). Make it again, or keep the Movement text to small motions.
          </div>
        )}
      </div>
      <div className="grid min-w-0 content-start gap-2">
        <textarea className="field-input min-h-24 text-sm" disabled={busy} aria-label="Animated cover prompt" value={text}
          onChange={(e) => setPrompt(e.target.value)}
          onBlur={() => edited && void run(async () => { const next = await calls.savePrompt(text); setPrompt(null); return next; })} />
        <p className="m-0 text-sm text-ink-soft">
          {busy && working ? working : how === "living"
            ? "Living moves the parts you mark on your cover picture (this description isn't used): nothing is redrawn, so faces and the art stay exactly as drawn."
            : how === "parallax"
            ? hasPicture
              ? cover
                ? "Parallax animates your cover picture (this description isn't used): depth and a slow camera, no new drawing and no Gemini. Untick the box below to draw this description first."
                : "Your GPU draws this description, then Parallax animates it with depth and a slow camera."
              : "Parallax animates the cover picture. There's none yet, so your GPU draws one from this description first (or draw or upload one under Picture)."
            : how === "character"
            ? "Describe the place and how it moves, in plain sentences (she nods slowly while writing, steam curls up from the mug, rain runs down the window). Your GPU draws it, then a video model moves the picture itself, free."
            : "Describe the place. Your GPU draws it and brings it to life with the moving light and particles you tick below, free. Gemini instead draws moving artwork from the words, one request per draw."}
        </p>
        {job && job.state === "running" && (
          <div role="progressbar" aria-label="Making the animated cover" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct ?? undefined} className="grid gap-1">
            <div className="h-2 overflow-hidden rounded-full bg-line">
              <div className={`h-full rounded-full bg-cobalt transition-[width] duration-300 ${pct === null ? "w-1/3 animate-pulse" : ""}`} style={pct === null ? undefined : { width: `${pct}%` }} />
            </div>
            <div className="text-xs text-ink-soft tabular-nums">{job.text || "Working…"}{pct === null ? "" : ` · ${pct}%`}</div>
          </div>
        )}
        <fieldset className="m-0 grid gap-1.5 border-0 p-0">
          <legend className="mb-1 p-0 text-sm font-semibold">Moves <span className="font-normal text-ink-soft">(GPU)</span></legend>
          <div role="radiogroup" aria-label="What the GPU moves" className="inline-flex w-fit rounded-lg border border-line p-0.5">
            {([...(living ? [["living", "Living (mark what moves)"]] as const : []), ["parallax", "Parallax"], ["light", "Light & particles"], ["character", "Character"]] as const).map(([m, label]) => (
              <button key={m} type="button" role="radio" aria-checked={how === m} disabled={off}
                className={`h-8 rounded-md px-3 text-sm font-semibold transition-colors ${how === m ? "bg-cobalt text-white" : "text-ink-soft hover:text-ink"}`}
                onClick={() => setMotion(m)}>{label}</button>
            ))}
          </div>
          <p className="m-0 text-sm text-ink-soft">
            {how === "living"
              ? "Hair sways, a body breathes, eyes blink, lights flicker, rain or leaves fall only where you mark. Every motion repeats exactly, so the loop has no seam. Made on this computer in under a minute; no GPU needed."
              : how === "parallax"
              ? `Near parts of the picture slide further than far ones, on a slow camera path that repeats with no seam. It moves the depth, not the people in it (no nods or blinks). Under a minute, on the CPU if need be.${state.loop && state.loop_motion === "parallax" && !state.loop_depth ? " The last one had no depth model, so it was a flat 2D drift." : ""}`
              : how === "character"
              ? `The picture itself moves as the prompt says (a nod, a writing hand, steam): about 5 minutes on your GPU, the same 4-second motion played three times.${state.video_model_ready ? "" : " The first time downloads the video model (about 24 GB)."} Faces and hands can warp: make it again for another take.`
              : "A slow breathing camera with the light and particles you pick; the picture stays still. About a minute."}
          </p>
          {how === "living" && living && (
            <LivingRegions picture={picture} regions={marked} kinds={state.region_kinds} onChange={setRegions} disabled={off}
              preview={preview}
              onPreview={() => void run(async () => {
                const [next, file] = await calls.preview!(marked);
                setRegions(null);
                setPreview(previewUrl!(file)); // once: a fresh url per preview, not per render
                return next;
              }, "Making the preview…")} />
          )}
          {how === "character" && (
            <label className="grid gap-1 text-sm">
              <span className="font-semibold">Movement <span className="font-normal text-ink-soft">(only how things move: describing the picture makes the model redraw it)</span></span>
              <textarea className="field-input min-h-20 text-sm" disabled={busy} value={moves}
                onChange={(e) => setMovement(e.target.value)}
                onBlur={() => movedEdit && void run(async () => { const next = await calls.saveMovement(moves); setMovement(null); return next; })} />
            </label>
          )}
          {how === "parallax" && <>
            <label className="flex items-center gap-2 text-sm">
              Intensity
              <input type="range" min={0} max={100} step={1} value={strength} disabled={off} className="w-40 accent-cobalt"
                onChange={(e) => setIntensity(Number(e.target.value))} />
              <span className="tabular-nums text-ink-soft">{strength}</span>
            </label>
            <p className="m-0 text-sm text-ink-soft">Beat-reactive effects use Style and mood → Beat effect in the final music-video render.</p>
          </>}
          {how === "light" && <div className="flex flex-wrap gap-1.5">
            {Object.entries(state.effect_choices).map(([k, label]) => {
              const on = moving.includes(k);
              return (
                <button key={k} type="button" aria-pressed={on} disabled={off}
                  className={`h-8 rounded-full border px-3 text-sm transition-colors ${on ? "border-cobalt bg-cobalt/15 font-semibold text-ink" : "border-line text-ink-soft hover:text-ink"}`}
                  onClick={() => setEffects(on ? moving.filter((e) => e !== k) : [...moving, k])}>{label}</button>
              );
            })}
          </div>}
          {hasPicture && how !== "living" && (
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="size-4 accent-cobalt" checked={cover} disabled={off} onChange={(e) => setUseCover(e.target.checked)} />
              Bring my cover picture to life (instead of drawing a new one)
            </label>
          )}
        </fieldset>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="primary" icon={<Cpu className="size-3.5" />} loading={busy && working.startsWith("Your GPU")} disabled={off || unmarked}
            title={unmarked ? "Drag a box over a part of the picture first" : "Drawn and animated on this computer: free, no Gemini request"}
            onClick={() => void run(async () => {
              if (edited) await calls.savePrompt(text);
              setPrompt(null);
              if (movedEdit) await calls.saveMovement(moves);
              setMovement(null);
              if (regions && calls.saveRegions) await calls.saveRegions(regions);
              setRegions(null);
              await calls.gpu(moving, cover, !!state.loop, how, strength);
              setJob({ state: "running", text: "Starting…", done: 0, total: 0, error: "" });
              try {
                await follow();
              } finally {
                setJob(null);
              }
              return calls.refresh();
            }, `Your GPU is ${cover ? "bringing the cover to life" : "drawing the cover, then bringing it to life"}.`)}>
            {how === "living" ? "Make the living loop" : state.loop ? "Make again on GPU" : "Make on GPU (free)"}</Button>
          {unmarked && <span className="text-sm text-ink-soft">Drag a box over a part of the picture to make it move.</span>}
          <Button size="sm" variant="secondary" icon={<Sparkles className="size-3.5" />} loading={busy && working.startsWith("Gemini")} disabled={off}
            title="Gemini draws moving artwork from the prompt: one request of your daily quota"
            onClick={() => void run(async () => {
              if (edited) await calls.savePrompt(text);
              setPrompt(null);
              return calls.draw(!!state.loop);
            }, "Gemini is drawing the moving artwork: a minute or two.")}>Gemini (1 request)</Button>
          <label className={`${buttonClass("secondary", "sm")} cursor-pointer`}>
            <Upload className="size-3.5" aria-hidden /> Upload clip
            <input type="file" hidden accept=".mp4,.webm,.mov,video/*" disabled={off}
              onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) void run(() => calls.upload(f)); }} />
          </label>
          <Button size="sm" variant="ghost" icon={<Copy className="size-3.5" />} onClick={() => copy(text)}>Copy prompt</Button>
          {state.loop && <Button size="sm" variant="ghost" icon={<Trash2 className="size-3.5" />} disabled={off}
            onClick={() => void run(() => calls.remove())}>Remove</Button>}
          {state.other_loops.length > 0 && (
            <select className="field-input h-9 w-auto py-0 text-sm" aria-label="Use the animated cover of another song" value="" disabled={off}
              onChange={(e) => { const from = e.target.value; if (from) void run(() => calls.reuse(from)); }}>
              <option value="">Use one from another song…</option>
              {state.other_loops.map((o) => <option key={o.slug} value={o.slug}>{o.title}</option>)}
            </select>
          )}
        </div>
        {videoPrompt && (
          <details className="text-sm">
            <summary className="cursor-pointer font-semibold text-ink-soft">Make it in another video tool</summary>
            <div className="mt-2 grid gap-2">
              <code className="well block p-3 text-sm break-words whitespace-pre-wrap">{videoPrompt}</code>
              <div className="flex flex-wrap items-center gap-2">
                <Button size="sm" variant="ghost" icon={<Copy className="size-3.5" />} onClick={() => copy(videoPrompt)}>Copy prompt</Button>
                <span className="text-ink-soft">Written from the song&apos;s mood, genre and lyrics. Make a looping clip with it, then Upload clip.</span>
              </div>
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
