"use client";

import { Clapperboard, Copy, ImageIcon, Paintbrush, RefreshCw, Trash2, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, songFileUrl, type ArtStyle, type LyricDrawStatus, type LyricPicture, type LyricPictures } from "@/lib/api";
import { ArtStylePicker, artBlocker, useArtStatus } from "./ArtControls";
import { Button, Spinner, buttonClass, useToast } from "./ui";

const withoutKey = (o: Record<string, string>, k: string) => Object.fromEntries(Object.entries(o).filter(([key]) => key !== k));
const clock = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

type Row = { id: string; title: string; when: string; lyrics: string; prompt: string; url: string };

/**
 * A lyric video's pictures: the cover (the background) and one picture per sung section, each with a suggested
 * prompt that can be edited, drawn on this computer for free, or replaced by your own file. "Test" jumps the preview
 * above to that section, so the picture is seen behind its lyrics before the render.
 */
/** How far the picture is: loading the model (no count), the drawing's steps, then the detail pass. */
function DrawProgress({ st }: { st: LyricDrawStatus }) {
  const known = (st.phase === "drawing" || st.phase === "detail") && st.total > 0;
  const pct = !known ? 0 : st.phase === "drawing" ? (st.done / st.total) * 65 : 65 + (st.done / st.total) * 35;
  return (
    <div role="progressbar" aria-label="Drawing" aria-valuemin={0} aria-valuemax={100} aria-valuenow={known ? Math.round(pct) : undefined} className="grid gap-1">
      <div className="h-2 overflow-hidden rounded-full bg-line">
        <div className={`h-full rounded-full bg-cobalt transition-[width] duration-300 ${known ? "" : "w-1/3 animate-pulse"}`} style={known ? { width: `${pct}%` } : undefined} />
      </div>
      <div className="text-xs text-ink-soft tabular-nums">{st.text || "Working…"}{known ? ` · ${Math.round(pct)}%` : ""}</div>
    </div>
  );
}

export function LyricPicturesCard({ slug, onTest, onChanged }: { slug: string; onTest: (t: number) => void; onChanged: () => void }) {
  const toast = useToast();
  const art = useArtStatus();
  const [plan, setPlan] = useState<LyricPictures | null>(null);
  const [style, setStyle] = useState<ArtStyle | "">("cinematic");
  const [prompts, setPrompts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [bust, setBust] = useState("");
  const stop = useRef(false);
  const [drawing, setDrawing] = useState<LyricDrawStatus | null>(null); // the picture being drawn, as it goes
  const [asks, setAsks] = useState<Record<string, string>>({}); // "change it like this" per picture
  const [rewriting, setRewriting] = useState<string | null>(null);
  const [tradition, setTradition] = useState<string | null>(null); // null = the song's saved one
  const [custom, setCustom] = useState<{ look: string; avoid: string } | null>(null); // null = the song's saved words
  const [clips, setClips] = useState<Record<string, string>>({}); // slot id -> its camera-move clip's file

  const take = useCallback((p: LyricPictures) => {
    setPlan(p);
    setPrompts({ cover: p.cover_prompt, ...Object.fromEntries(p.slots.map((s) => [s.id, s.prompt])) });
    setBust(String(Date.now()));
  }, []);
  useEffect(() => {
    let live = true;
    api.lyricPictures(slug).then((p) => live && take(p)).catch((e: Error) => toast(e.message, "error"));
    return () => {
      live = false;
    };
  }, [slug, take, toast]);

  const blocker = style ? artBlocker(art.status, style) : "Pick a look to draw, or upload your own pictures.";

  async function run<T>(id: string, work: () => Promise<T>): Promise<T | undefined> {
    setBusy(id);
    try {
      return await work();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(null);
    }
  }
  const saved = (p: LyricPictures) => {
    take(p);
    onChanged();
  };
  /** Follow the picture being drawn until it is done; then show it. */
  const follow = useCallback(async () => {
    for (;;) {
      const st = await api.lyricDrawStatus(slug);
      setDrawing(st);
      if (st.state === "done") return take(await api.lyricPictures(slug)), onChanged();
      if (st.state === "error") throw new Error(st.error || "The picture could not be drawn.");
      if (st.state === "idle") return;
      await new Promise((r) => setTimeout(r, 500));
    }
  }, [slug, take, onChanged]);
  useEffect(() => {
    // a picture may still be drawing from before this page was opened: pick it up
    let live = true;
    api.lyricDrawStatus(slug).then((st) => {
      if (live && st.state === "running") {
        setBusy(st.pid);
        follow().catch((e: Error) => toast(e.message, "error")).finally(() => { setBusy(null); setDrawing(null); });
      }
    }).catch(() => {});
    return () => { live = false; };
  }, [slug, follow, toast]);
  const draw = (id: string, again = false) =>
    run(id, async () => {
      if (!style) return;
      const seed = again ? Math.floor(Math.random() * 2 ** 31) + 1 : undefined;
      setDrawing({ state: "running", pid: id, phase: "queued", text: "Starting…", done: 0, total: 0, error: "" });
      try {
        await api.drawLyricPicture(slug, id, { prompt: prompts[id], style, seed, tradition: tradition ?? plan?.tradition ?? "",
          custom_look: custom?.look ?? plan?.custom_look ?? "", custom_avoid: custom?.avoid ?? plan?.custom_avoid ?? "" });
        await follow();
      } finally {
        setDrawing(null);
      }
    });
  async function rewrite(id: string) {
    const ask = (asks[id] ?? "").trim();
    if (!ask) return;
    setRewriting(id);
    try {
      const r = await api.rewriteLyricPrompt(slug, id, prompts[id], ask);
      setPrompts((p) => ({ ...p, [id]: r.prompt }));
      setAsks((a) => ({ ...a, [id]: "" }));
      await api.editLyricPictures(slug, { [id]: r.prompt }).then(setPlan).catch(() => {});
      toast(r.by === "Gemini" ? "Prompt changed. Draw again to see it." : "Added to the end of the prompt. Draw again to see it.", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    }
    setRewriting(null);
  }
  async function playMove(id: string) {
    await run(`move-${id}`, async () => {
      const r = await api.lyricMotionClip(slug, id);
      setClips((c) => ({ ...c, [id]: `${r.file}?v=${Date.now()}` }));
    });
  }
  async function drawMissing() {
    if (!plan || !style) return;
    stop.current = false;
    for (const s of plan.slots.filter((x) => !x.file)) {
      if (stop.current) break;
      await draw(s.id);
    }
  }

  if (!plan) return <div className="card grid place-items-center p-6"><Spinner className="size-5" /></div>;
  const rows: Row[] = [
    { id: "cover", title: "Cover", when: "background and thumbnail", lyrics: "", prompt: prompts.cover ?? "", url: plan.cover ? songFileUrl(slug, plan.cover, bust) : "" },
    ...plan.slots.map((s: LyricPicture) => ({
      id: s.id, title: s.tag, when: `${clock(s.start)}–${clock(s.end)}`, lyrics: s.lyrics, prompt: prompts[s.id] ?? s.prompt,
      url: s.file ? songFileUrl(slug, `pictures/${s.file}`, bust) : "",
    })),
  ];
  const missing = plan.slots.filter((s) => !s.file).length;
  const hasTraditions = style === "anime" || style === "flat"; // the looks the traditions are written for

  const card = (r: Row) => (
    <div key={r.id} className="well grid gap-3 p-3 sm:grid-cols-[minmax(0,13rem)_1fr]">
      <div className="grid content-start gap-2">
        <div className="grid aspect-video w-full place-items-center overflow-hidden rounded-lg bg-black">
          {r.url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={r.url} alt={`${r.title} picture`} className="size-full object-cover" />
          ) : busy === r.id && !drawing ? <Spinner className="size-5" /> : <ImageIcon className="size-6 text-ink-soft" aria-hidden />}
        </div>
        {drawing && drawing.pid === r.id && <DrawProgress st={drawing} />}
        <div className="text-sm font-semibold">{r.title} <span className="font-normal text-ink-soft">{r.when}</span></div>
      </div>
      <div className="grid min-w-0 gap-2">
        {r.lyrics && <p className="m-0 line-clamp-2 text-sm text-ink-soft">{r.lyrics}</p>}
        <textarea className="field-input min-h-20 text-sm" disabled={busy === r.id} aria-label={`${r.title} picture prompt`} value={r.prompt}
          onChange={(e) => setPrompts({ ...prompts, [r.id]: e.target.value })}
          onBlur={() => prompts[r.id] !== (r.id === "cover" ? plan.cover_prompt : plan.slots.find((s) => s.id === r.id)?.prompt) && void api.editLyricPictures(slug, { [r.id]: prompts[r.id] }).then(setPlan).catch(() => {})} />
        <div className="flex gap-2">
          <input className="field-input h-9 min-w-0 flex-1 py-0 text-sm" aria-label={`Change the ${r.title} prompt`}
            placeholder="Change it: make it night, add a lantern, no people…" value={asks[r.id] ?? ""} disabled={!!busy || rewriting === r.id}
            onChange={(e) => setAsks({ ...asks, [r.id]: e.target.value })}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); void rewrite(r.id); } }} />
          <Button size="sm" variant="secondary" className="h-9" loading={rewriting === r.id} disabled={!!busy || !(asks[r.id] ?? "").trim()}
            onClick={() => void rewrite(r.id)}>Change prompt</Button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="primary" icon={<Paintbrush className="size-3.5" />} loading={busy === r.id}
            disabled={(!!busy && busy !== r.id) || !style || !!blocker} title={blocker || undefined}
            onClick={() => void draw(r.id, !!r.url)}>{r.url ? "Draw again" : "Draw"}</Button>
          <label className={`${buttonClass("secondary", "sm")} cursor-pointer`}>
            <Upload className="size-3.5" aria-hidden /> Upload
            <input type="file" hidden accept=".png,.jpg,.jpeg,.webp,image/*" disabled={!!busy}
              onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) void run(r.id, async () => saved(await api.uploadLyricPicture(slug, r.id, f))); }} />
          </label>
          <Button size="sm" variant="ghost" icon={<Copy className="size-3.5" />}
            onClick={() => { void navigator.clipboard.writeText(r.prompt); toast("Prompt copied", "success"); }}>Copy prompt</Button>
          {r.url && <Button size="sm" variant="ghost" icon={<Trash2 className="size-3.5" />} disabled={!!busy}
            onClick={() => void run(r.id, async () => saved(await api.removeLyricPicture(slug, r.id)))}>Remove</Button>}
          {r.id !== "cover" && (() => {
            const s = plan.slots.find((x) => x.id === r.id)!;
            return (
              <>
                <Button size="sm" variant="ghost" onClick={() => onTest(Math.min(s.start + 3, (s.start + s.end) / 2))}>Test in preview</Button>
              </>
            );
          })()}
        </div>
      </div>
    </div>
  );

  return (
    <section className="card grid gap-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="card-title">Cover picture</h2>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="ghost" icon={<RefreshCw className="size-3.5" />} disabled={!!busy}
            onClick={() => void run("reset", async () => saved(await api.resetLyricPictures(slug)))}>New suggestions</Button>
        </div>
      </div>
      <p className="m-0 text-sm text-ink-soft">
        Prompts are written by Gemini from what the lyrics mean (and your scene theme). Draw one cover and it is used behind every lyric, the title card and the thumbnail (slowly panned and zoomed). Edit a prompt, then draw (free, on this computer) or upload your own. Want it to change with the song? Give sections their own pictures below; the rest keep the cover.
      </p>
      {plan.meaning && <p className="well m-0 p-3 text-sm"><b>What the song is about:</b> {plan.meaning}</p>}
      <ArtStylePicker value={style} onChange={setStyle} status={art.status} reload={art.reload} stockLabel="Upload only" />
      {(
        <label className="grid gap-1 text-sm">
          <span className="font-semibold">Art tradition <span className="font-normal text-ink-soft">(all of this song&apos;s pictures follow it, so they look like one film)</span></span>
          <select className="field-input h-9 py-0 text-sm" aria-label="Art tradition" value={tradition ?? plan.tradition}
            disabled={!hasTraditions} onChange={(e) => setTradition(e.target.value)}>
            {Object.entries(plan.traditions).map(([k, t]) => (
              <option key={k} value={k}>{t.label}{k === plan.tradition_suggested && k !== "" ? " (suggested)" : ""}</option>
            ))}
          </select>
          {!hasTraditions ? (
            <span className="flex flex-wrap items-center gap-2 text-ink-soft">
              Art traditions (Ghibli-like, lofi room, your own…) work with the Anime and Flat 2D looks.
              <Button size="sm" variant="secondary" type="button" onClick={() => setStyle("anime")}>Switch to Anime</Button>
            </span>
          ) : (
            <span className="text-ink-soft">{plan.traditions[tradition ?? plan.tradition]?.hint}.{style === "flat" ? " On Flat 2D it is blended with the flat vector look." : ""} Draw again to see it in the pictures you already made.</span>
          )}
          {hasTraditions && (tradition ?? plan.tradition) === "custom" && (
            <>
              <input className="field-input h-9 py-0 text-sm" aria-label="Your own style" maxLength={240}
                placeholder="Your style: oil painting, thick brush strokes, moody blue light"
                value={custom?.look ?? plan.custom_look} onChange={(e) => setCustom({ look: e.target.value, avoid: custom?.avoid ?? plan.custom_avoid })} />
              <input className="field-input h-9 py-0 text-sm" aria-label="What to avoid in your style" maxLength={240}
                placeholder="Avoid (optional): neon, 3d, sharp lines"
                value={custom?.avoid ?? plan.custom_avoid} onChange={(e) => setCustom({ look: custom?.look ?? plan.custom_look, avoid: e.target.value })} />
            </>
          )}
        </label>
      )}
      {card(rows[0])}
      <section className="grid gap-2" aria-label="Camera motion">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="m-0 text-base font-semibold">Camera motion <span className="font-normal text-ink-soft">(how each picture moves behind the lyrics)</span></h3>
          <Button size="sm" variant="ghost" icon={<RefreshCw className="size-3.5" />} disabled={!!busy}
            title="Set every move to what suits it (verses push in, choruses pull out, bridges pan)"
            onClick={() => void run("motion", async () => saved(await api.suggestLyricMotions(slug)))}>Suggest camera moves</Button>
        </div>
        <ul className="m-0 grid list-none gap-2 p-0">
          {[{ id: "cover", title: "Cover", when: "whole song", move: plan.cover_motion, edited: true, has: true },
            ...plan.slots.map((x) => ({ id: x.id, title: x.tag, when: `${clock(x.start)}–${clock(x.end)}`, move: x.motion, edited: !!x.motion_edited, has: !!x.file }))].map((m) => (
            <li key={m.id} className="well grid items-center gap-2 p-2 sm:grid-cols-[minmax(0,12rem)_minmax(0,12rem)_auto_1fr]">
              <span className="text-sm font-semibold">{m.title} <span className="font-normal text-ink-soft">{m.when}</span></span>
              <select className="field-input h-9 py-0 text-sm" aria-label={`${m.title} camera move`} value={m.move} disabled={!!busy}
                onChange={(e) => { setClips((c) => withoutKey(c, m.id)); void api.editLyricPictures(slug, {}, { [m.id]: e.target.value }).then(saved).catch((er: Error) => toast(er.message, "error")); }}>
                {Object.entries(plan.motions).map(([k, label]) => (
                  <option key={k} value={k}>{label}{m.id !== "cover" && !m.edited && k === m.move ? " (suggested)" : ""}</option>
                ))}
              </select>
              <Button size="sm" variant="ghost" icon={<Clapperboard className="size-3.5" />} loading={busy === `move-${m.id}`}
                disabled={(!!busy && busy !== `move-${m.id}`) || (!m.has && m.id !== "cover")}
                title={m.has || m.id === "cover" ? "A few seconds of this picture going through its camera move" : "Draw or upload this picture first"}
                onClick={() => (clips[m.id] ? setClips((c) => withoutKey(c, m.id)) : void playMove(m.id))}>{clips[m.id] ? "Hide" : "Preview move"}</Button>
              {clips[m.id] && <video src={songFileUrl(slug, clips[m.id])} className="aspect-video w-48 rounded-lg bg-black object-cover" autoPlay loop muted playsInline aria-label={`${m.title} camera move preview`} />}
            </li>
          ))}
        </ul>
      </section>
      <details className="grid gap-3" open={plan.slots.some((x) => x.file)}>
        <summary className="cursor-pointer text-base font-semibold text-ink-soft">
          A different picture for each section (optional, {plan.slots.length} sections, {missing} without one)
        </summary>
        <div className="mt-3 grid gap-3">
          <div className="flex justify-end">
            <Button size="sm" variant="secondary" icon={<Paintbrush className="size-3.5" />} disabled={!!busy || !style || !!blocker || missing === 0}
              onClick={() => void drawMissing()}>Draw the {missing} missing</Button>
          </div>
          {rows.slice(1).map(card)}
        </div>
      </details>
    </section>
  );
}
