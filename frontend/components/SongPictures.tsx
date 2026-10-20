"use client";

import { ChevronDown, Clapperboard, Dices, GalleryHorizontal, ImageIcon, Paintbrush, RefreshCw, Square, Wand2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, fileUrl, type ArtStatus, type ArtStyle, type Aspect, type Motion, type PictureFit, type PicturePace, type SongArtPlan, type SongDirection, type SongArtSlot } from "@/lib/api";
import { PictureReview } from "./PictureReview";
import { Button, Message, Spinner } from "./ui";

const MOTION_ORDER: Motion[] = ["dolly_3d", "orbit_3d", "rise_3d", "push_in", "pull_out", "pan_left", "pan_right", "tilt_up", "tilt_down", "still", "breathe"];
const newSeed = () => Math.floor(Math.random() * 2 ** 31) + 1;
const clock = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const without = <T,>(o: Record<number, T>, k: number) => Object.fromEntries(Object.entries(o).filter(([i]) => Number(i) !== k)) as Record<number, T>;
/** The shape a picture is drawn in: a cover character portrait, unless it fills the screen or is a whole scene. */
const drawAspect = (slot: SongArtSlot, fit: PictureFit, aspect: Aspect): Aspect =>
  slot.frame === "4:3" ? "16:9" : slot.frame === "cover" && fit === "fit" && /simple background/i.test(slot.prompt) ? "9:16" : aspect;
const edits = (slots: SongArtSlot[]) => slots.map(({ prompt, motion, effects, seed }) => ({ prompt, motion, effects, seed }));

/**
 * A music video's pictures, planned and checked before the render: Claude plans them once (the only step that uses
 * credits), then each one can be drawn, redrawn, rewritten and previewed moving, all on this computer for free.
 * The render then uses exactly these pictures.
 */
export function SongPictures({
  name,
  direction,
  style,
  pace,
  fit,
  idea,
  look,
  aspect,
  status,
  blocker,
}: {
  name: string; // the song's folder
  direction: SongDirection | null; // the shot list the pictures follow (when made from this idea)
  style: ArtStyle;
  pace: PicturePace;
  fit: PictureFit;
  idea: string;
  look: string;
  aspect: Aspect;
  status: ArtStatus | null;
  blocker: string; // why pictures can't be drawn yet ("" = ready)
}) {
  const [plan, setPlanState] = useState<SongArtPlan | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [open, setOpen] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [drawingAll, setDrawingAll] = useState(false);
  const [busy, setBusy] = useState<Record<number, "draw" | "preview">>({});
  const [previews, setPreviews] = useState<Record<number, string>>({});
  const [message, setMessage] = useState<{ text: string; error?: boolean }>({ text: "" });
  const [reviewing, setReviewing] = useState<number | null>(null); // the one-by-one view, from this picture
  const stop = useRef(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const planRef = useRef<SongArtPlan | null>(null); // the latest plan, for edits made while drawing
  const setPlan = useCallback((next: SongArtPlan | null) => {
    planRef.current = next;
    setPlanState(next);
  }, []);

  useEffect(() => {
    let alive = true;
    api
      .songArtPlan(name)
      .then((r) => alive && setPlan(r.plan))
      .catch(() => {})
      .finally(() => alive && setLoaded(true));
    return () => {
      alive = false;
      stop.current = true;
    };
  }, [name, setPlan]);

  // the shot list changed (it saves itself a moment later): check again whether the plan still follows it
  const directionKey = JSON.stringify(direction ?? null);
  useEffect(() => {
    const t = setTimeout(() => {
      api
        .songArtPlan(name)
        .then((r) => r.plan && planRef.current && setPlan({ ...planRef.current, direction_current: r.plan.direction_current }))
        .catch(() => {});
    }, 1500);
    return () => clearTimeout(t);
  }, [directionKey, name, setPlan]);

  // edits are saved shortly after you stop typing; the render reads the saved plan
  const save = useCallback(
    (next: SongArtPlan, now = false) => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
      const run = () => api.saveSongArtPlan(name, { bible: next.bible, fit, slots: edits(next.slots) }).catch((e) => setMessage({ text: (e as Error).message, error: true }));
      if (now) void run();
      else saveTimer.current = setTimeout(run, 700);
    },
    [name, fit],
  );

  // Fit or Fill changed: the plan remembers it, and shows the pictures already drawn in the new shape
  useEffect(() => {
    if (!loaded || !planRef.current) return;
    const cur = planRef.current;
    api
      .saveSongArtPlan(name, { bible: cur.bible, fit, slots: edits(cur.slots) })
      .then((r) => setPlan(r.plan))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only when the choice changes
  }, [fit]);

  const update = (k: number, patch: Partial<SongArtSlot>, now = false) => {
    const cur = planRef.current;
    if (!cur) return;
    // a new prompt or take is a different picture: the drawn one no longer belongs to it
    const changesPicture = ("prompt" in patch && patch.prompt !== cur.slots[k].prompt) || ("seed" in patch && patch.seed !== cur.slots[k].seed);
    const next = { ...cur, slots: cur.slots.map((s, i) => (i === k ? { ...s, ...(changesPicture ? { picture: null } : {}), ...patch } : s)) };
    setPlan(next);
    if (changesPicture || "motion" in patch || "effects" in patch) setPreviews((p) => without(p, k));
    save(next, now);
  };

  async function planPictures() {
    setPlanning(true);
    setMessage({ text: "Claude is planning the pictures from your lyrics… about 30 seconds." });
    try {
      // keep your edited bible (the characters and world) when planning again in the same look
      const bible = plan && plan.style === style ? plan.bible : "";
      const fits = direction && direction.idea === idea.trim();
      const r = await api.planSongArt(name, { style, pictures: pace, idea, bible: bible || (fits ? direction.bible : ""), direction: fits ? direction : null });
      setPlan(r.plan);
      setPreviews({});
      setOpen(true);
      setMessage({ text: "" });
    } catch (e) {
      setMessage({ text: (e as Error).message, error: true });
    } finally {
      setPlanning(false);
    }
  }

  async function draw(k: number, newTake = false) {
    const slot = planRef.current?.slots[k];
    if (!slot?.prompt.trim()) return;
    const seed = newTake ? newSeed() : slot.seed;
    setBusy((b) => ({ ...b, [k]: "draw" }));
    try {
      const m = await api.artDraw({ prompt: slot.prompt, style, seed, aspect: drawAspect(slot, fit, aspect) });
      update(k, { seed, picture: { media: m.media, url: m.url, kind: "photo" } }, newTake);
      return true;
    } catch (e) {
      setMessage({ text: (e as Error).message, error: true });
      return false;
    } finally {
      setBusy((b) => without(b, k));
    }
  }

  async function drawAll() {
    stop.current = false;
    setDrawingAll(true);
    setMessage({ text: "" });
    for (let k = 0; k < (planRef.current?.slots.length ?? 0); k++) {
      if (stop.current) break;
      if (planRef.current?.slots[k].picture) continue;
      if (!(await draw(k))) break;
    }
    setDrawingAll(false);
  }

  async function preview(k: number) {
    const slot = planRef.current?.slots[k];
    if (!slot?.picture) return;
    setBusy((b) => ({ ...b, [k]: "preview" }));
    try {
      const m = await api.previewShot({ media: slot.picture.media, style, motion: slot.motion, effects: slot.effects, aspect, look });
      setPreviews((p) => ({ ...p, [k]: m.media }));
    } catch (e) {
      setMessage({ text: (e as Error).message, error: true });
    } finally {
      setBusy((b) => without(b, k));
    }
  }

  if (!loaded) return null;
  const drawn = plan?.slots.filter((s) => s.picture).length ?? 0;
  const stale = !!plan && (plan.style !== style || plan.pictures !== pace || plan.idea !== idea.trim() || plan.direction_current === false);
  const left = (plan?.slots.length ?? 0) - drawn;

  return (
    <div className="grid gap-2 rounded-lg border border-line p-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="grid">
          <span className="text-base font-semibold text-ink">Check the pictures first</span>
          <span className="text-sm text-ink-soft tabular-nums">
            {plan ? `${plan.slots.length} pictures · ${drawn} drawn` : "See every picture before you render"}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          {plan && (
            <Button size="sm" variant="ghost" icon={<RefreshCw className="size-3.5" />} loading={planning} disabled={drawingAll} onClick={planPictures} title="Claude plans new pictures (uses credits once)">
              Plan again
            </Button>
          )}
          {!plan && (
            <Button size="sm" variant="primary" icon={<Wand2 className="size-3.5" />} loading={planning} disabled={!!blocker} onClick={planPictures}>
              Plan pictures
            </Button>
          )}
        </div>
      </div>

      {!plan && (
        <p className="m-0 text-sm text-ink-soft">
          Planning asks Claude once, for a few cents. Drawing, redrawing and motion previews then run on your GPU for free, and Make video uses exactly the pictures
          you approved, with no new Claude call.
        </p>
      )}
      {stale && (
        <p className="m-0 rounded-md bg-amber-500/10 px-2 py-1.5 text-sm text-ink">
          You changed the look, the number of pictures, the idea or its shot list since these were planned. Plan again to see the new pictures, otherwise Make video will plan
          them itself (one Claude call) without you checking them.
        </p>
      )}

      {plan && (
        <>
          <div className="flex flex-wrap items-center gap-1.5">
            {drawingAll ? (
              <Button size="sm" icon={<Square className="size-3.5" />} onClick={() => (stop.current = true)}>
                Stop drawing
              </Button>
            ) : (
              left > 0 && (
                <Button size="sm" icon={<Paintbrush className="size-3.5" />} disabled={!!blocker || stale} onClick={drawAll}>
                  Draw {left === plan.slots.length ? "all" : `the other ${left}`} (~{Math.max(1, Math.round((left * 40) / 60))} min)
                </Button>
              )
            )}
            {!drawingAll && (
              <Button
                size="sm"
                variant="ghost"
                icon={<GalleryHorizontal className="size-3.5" />}
                disabled={!!blocker || stale}
                title="Draw and check each picture in turn: keep it, or ask for another take"
                onClick={() => {
                  const first = plan.slots.findIndex((sl) => !sl.picture);
                  setReviewing(first < 0 ? 0 : first);
                }}
              >
                One by one
              </Button>
            )}
            <button
              type="button"
              aria-expanded={open}
              onClick={() => setOpen((o) => !o)}
              className="flex cursor-pointer items-center gap-1 border-0 bg-transparent p-0 text-sm font-semibold text-cobalt"
            >
              <ChevronDown className={`size-3.5 transition-transform ${open ? "rotate-180" : ""}`} /> {open ? "Hide pictures" : "Show pictures"}
            </button>
          </div>
          {drawingAll && (
            <div role="progressbar" aria-label="Drawing the pictures" aria-valuemin={0} aria-valuemax={plan.slots.length} aria-valuenow={drawn} className="h-1.5 overflow-hidden rounded-full bg-ink/[0.08]">
              <div className="h-full rounded-full bg-cobalt transition-[width] duration-300" style={{ width: `${(drawn / plan.slots.length) * 100}%` }} />
            </div>
          )}
        </>
      )}

      <Message text={message.text || (plan ? blocker : "")} error={message.error} />

      {plan && reviewing !== null && (
        <PictureReview
          items={plan.slots.map((sl) => ({
            label: `${sl.section} · ${clock(sl.start)}${sl.also.length ? ` (also ${sl.also.join(", ")})` : ""}`,
            text: sl.lyrics,
            prompt: sl.prompt,
            media: sl.picture?.media ?? null,
          }))}
          start={reviewing}
          aspect={aspect}
          blocker={blocker}
          onDraw={async (k, newTake) => !!(await draw(k, newTake))}
          onPrompt={(k, prompt) => update(k, { prompt })}
          onClose={() => setReviewing(null)}
        />
      )}

      {plan && open && (
        <>
          <label className="grid gap-1">
            <span className="field-label">Visual bible</span>
            <textarea
              rows={2}
              value={plan.bible}
              onChange={(e) => {
                const next = { ...plan, bible: e.target.value };
                setPlan(next);
                save(next);
              }}
              className="field-input field-sizing-content min-h-[52px] resize-none text-sm leading-snug"
            />
            <span className="text-xs text-ink-soft">The characters, world and colours every picture shares. Edit it, then Plan again to apply it to all prompts.</span>
          </label>
          <ol className={`m-0 grid list-none gap-2 p-0 ${aspect === "16:9" ? "grid-cols-1" : "grid-cols-2"}`}>
            {plan.slots.map((slot, k) => (
              <li key={k} className="grid content-start gap-1.5 rounded-lg border border-line/70 bg-sunken p-1.5">
                <div className={`relative grid place-items-center overflow-hidden rounded-md bg-ink/[0.06] ${slot.frame === "4:3" ? "aspect-[4/3] self-center" : drawAspect(slot, fit, aspect) === "9:16" && aspect === "16:9" ? "aspect-[9/16] max-h-64 self-center" : aspect === "16:9" ? "aspect-video" : "aspect-[9/16]"}`}>
                  {previews[k] ? (
                    <video src={fileUrl(previews[k])} autoPlay loop muted playsInline className="size-full object-cover" />
                  ) : slot.picture ? (
                    // eslint-disable-next-line @next/next/no-img-element -- a local file from the engine
                    <img src={fileUrl(slot.picture.media)} alt={`Picture ${k + 1}: ${slot.prompt}`} className="size-full object-cover" />
                  ) : busy[k] === "draw" ? (
                    <span className="grid justify-items-center gap-1 text-xs text-ink-soft">
                      <Spinner /> Drawing…
                    </span>
                  ) : (
                    <ImageIcon className="size-6 text-ink-soft/60" aria-hidden />
                  )}
                  {busy[k] === "preview" && (
                    <span className="absolute inset-0 grid place-items-center bg-black/40 text-white">
                      <Spinner className="size-5" />
                    </span>
                  )}
                  <span className="absolute top-1 left-1 rounded bg-black/55 px-1.5 py-0.5 text-2xs font-semibold text-white tabular-nums">
                    {k + 1} · {clock(slot.start)}
                  </span>
                </div>
                <div className="grid gap-0.5 px-0.5">
                  <span className="text-sm font-semibold text-ink">
                    {slot.section} <span className="font-normal text-ink-soft">· {slot.seconds.toFixed(1)} s</span>
                  </span>
                  {slot.also.length > 0 && <span className="text-xs text-cobalt">Shown again in {slot.also.join(", ")}</span>}
                  {slot.lyrics && <span className="line-clamp-2 text-xs text-ink-soft italic">“{slot.lyrics}”</span>}
                </div>
                <textarea
                  aria-label={`Picture ${k + 1} prompt`}
                  rows={3}
                  value={slot.prompt}
                  onChange={(e) => update(k, { prompt: e.target.value })}
                  className="field-input min-h-[64px] resize-y text-xs leading-snug"
                />
                <select
                  aria-label={`Picture ${k + 1} camera move`}
                  className="field-input h-7 py-0 text-xs"
                  value={slot.motion}
                  onChange={(e) => update(k, { motion: e.target.value as Motion })}
                >
                  {MOTION_ORDER.map((m) => (
                    <option key={m} value={m}>
                      {status?.motions[m] ?? m}
                    </option>
                  ))}
                </select>
                <div className="flex flex-wrap gap-0.5">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 px-1.5 text-sm"
                    icon={slot.picture ? <Dices className="size-3.5" /> : <Paintbrush className="size-3.5" />}
                    loading={busy[k] === "draw"}
                    disabled={!!blocker || !!busy[k]}
                    onClick={() => draw(k, !!slot.picture)}
                    title={slot.picture ? "The same prompt, a different picture" : "Draw this picture"}
                  >
                    {slot.picture ? "Retake" : "Draw"}
                  </Button>
                  {slot.picture && (
                    <Button size="sm" variant="ghost" className="h-7 px-1.5 text-sm" icon={<Clapperboard className="size-3.5" />} disabled={!!busy[k]} onClick={() => (previews[k] ? setPreviews((p) => without(p, k)) : preview(k))}>
                      {previews[k] ? "Still" : "Preview"}
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
