"use client";

import { Check, Copy, ExternalLink, Play, Scissors } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, outputUrl, type HighlightCandidate, type HighlightsReport, type Job, type VideoDetail } from "@/lib/api";
import { Button, useToast } from "./ui";

// the "[n/7]" steps of crcontent/highlights make_highlights
const STEPS = ["Reading the video", "Audio structure", "Lyrics", "Visuals", "Ranking", "AI judge", "Covers and clips"];
const ARTIST_KEY = "highlights.artist";

const clock = (t: number) => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, "0")}`;

function savedArtist(): string {
  try {
    return localStorage.getItem(ARTIST_KEY) ?? "";
  } catch {
    return "";
  }
}

/** Smart Highlights on a music video: the best 15–30 s for Shorts / Reels, ranked, with covers and rendered clips. */
export function HighlightsCard({ detail, onSelectVideo, onVideosChanged }: {
  detail: VideoDetail;
  onSelectVideo: (name: string) => void;
  onVideosChanged: () => void;
}) {
  const toast = useToast();
  const [report, setReport] = useState<HighlightsReport | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [judge, setJudge] = useState(false);
  const [artist, setArtist] = useState(savedArtist);
  const [starting, setStarting] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [v, setV] = useState(0); // cache buster: covers are redrawn by a new run

  const load = useCallback(
    () =>
      api
        .highlights(detail.name)
        .then((r) => {
          setReport(r.report);
          if (r.job) setJobId(r.job); // a run still going (started before this card was opened)
        })
        .catch(() => setReport(null)), // an older engine without highlights: the card offers to start one
    [detail.name],
  );

  useEffect(() => {
    api
      .highlights(detail.name)
      .then((r) => {
        setReport(r.report);
        if (r.job) setJobId(r.job);
      })
      .catch(() => setReport(null));
  }, [detail.name]);

  // follow the run until it finishes
  useEffect(() => {
    if (!jobId) return;
    let stop = false;
    const t = window.setInterval(async () => {
      let j: Job;
      try {
        j = await api.job(jobId);
      } catch {
        return; // the engine may be restarting; try again next tick
      }
      if (stop) return;
      setJob(j);
      if (j.status === "done" || j.status === "error") {
        window.clearInterval(t);
        setJobId(null);
        if (j.status === "done") {
          await load();
          setV(Date.now());
          onVideosChanged();
          toast("Highlights ready: 3 clips added to your videos", "success");
        } else {
          toast(j.error ?? "Smart Highlights failed", "error");
        }
      }
    }, 1500);
    return () => {
      stop = true;
      window.clearInterval(t);
    };
  }, [jobId, load, onVideosChanged, toast]);

  async function start() {
    setStarting(true);
    try {
      try {
        localStorage.setItem(ARTIST_KEY, artist.trim());
      } catch {
        // private window: the name just isn't remembered
      }
      const { id } = await api.findHighlights(detail.name, { ai_judge: judge, artist: artist.trim() });
      setJob({ id, kind: "highlights", status: "queued", step: 0, log: [], title: detail.title });
      setJobId(id);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setStarting(false);
    }
  }

  const running = !!jobId;
  const step = Math.max(job?.step ?? 0, 0);
  const lastLine = job?.log.filter((l) => !l.startsWith("[")).at(-1)?.trim() ?? "";
  const picks = report?.candidates ?? [];
  const shown = showAll ? picks : picks.slice(0, report?.chosen.length || 3);

  return (
    <section aria-label="Smart Highlights" className="mx-auto grid w-full max-w-[300px] gap-3 card p-3.5">
      <div className="grid gap-1">
        <h3 className="m-0 flex items-center gap-1.5 text-base font-bold">
          <Scissors className="size-4 text-cobalt" aria-hidden /> Smart Highlights
        </h3>
        <p className="m-0 text-sm text-ink-soft">
          Finds the best 15–30 s for Shorts and Reels (choruses, the lines people remember, cut on the beat), makes covers
          and renders the top 3 as vertical clips.
        </p>
      </div>

      {!running && (
        <div className="grid gap-2">
          <label className="grid gap-1">
            <span className="field-label">
              Artist on the covers <span className="font-normal">optional</span>
            </span>
            <input className="field-input h-9 py-0 text-base" value={artist} maxLength={80} onChange={(e) => setArtist(e.target.value)} placeholder="Your artist name" />
          </label>
          <label className="flex items-center gap-2 text-sm font-semibold">
            <input type="checkbox" className="size-4 accent-cobalt" checked={judge} onChange={(e) => setJudge(e.target.checked)} />
            Gemini picks the order and writes hooks and captions
          </label>
          <Button variant={report ? "secondary" : "primary"} icon={<Scissors className="size-4" />} loading={starting} onClick={start}>
            {report ? "Find highlights again" : "Find highlights"}
          </Button>
          {report && <p className="m-0 text-xs text-ink-soft">Each run adds 3 new clips to your videos; the ones you have stay.</p>}
        </div>
      )}

      {running && (
        <div className="grid gap-1.5" aria-live="polite">
          <div role="progressbar" aria-label="Finding highlights" aria-valuemin={0} aria-valuemax={STEPS.length} aria-valuenow={step} className="h-1.5 overflow-hidden rounded-full bg-ink/[0.08]">
            <div className="h-full rounded-full bg-cobalt transition-[width] duration-300 ease-linear" style={{ width: `${Math.max(4, (Math.max(step - 1, 0) / STEPS.length) * 100)}%` }} />
          </div>
          <span className="text-sm font-semibold">
            {job?.status === "queued" || step === 0 ? "Waiting for the renderer…" : `${step}/${STEPS.length} · ${STEPS[step - 1]}`}
          </span>
          {lastLine && <span className="truncate text-xs text-ink-soft" title={lastLine}>{lastLine}</span>}
          <span className="text-xs text-ink-soft">A few minutes for a full song. You can keep working.</span>
        </div>
      )}

      {report && picks.length > 0 && (
        <div className={`grid gap-3 ${running ? "opacity-50" : ""}`}>
          {shown.map((c) => (
            <Pick key={`${c.candidate}-${v}`} c={c} folder={detail.name} v={v} chosen={report.chosen.includes(c.candidate)} onOpen={onSelectVideo} />
          ))}
          {picks.length > shown.length && (
            <Button size="sm" variant="ghost" onClick={() => setShowAll(true)}>
              Show {picks.length - shown.length} more candidate{picks.length - shown.length === 1 ? "" : "s"}
            </Button>
          )}
          <a href={outputUrl(detail.name, report.page)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm font-semibold text-cobalt">
            Full report with score breakdown <ExternalLink className="size-3.5" aria-hidden />
          </a>
        </div>
      )}
    </section>
  );
}

function Pick({ c, folder, v, chosen, onOpen }: { c: HighlightCandidate; folder: string; v: number; chosen: boolean; onOpen: (name: string) => void }) {
  const toast = useToast();
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(c.caption);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      toast("Couldn't copy the caption", "error");
    }
  }

  const parts = [
    ["structure", c.parts.structure],
    ["lyrics", c.parts.lyrics],
    ["visual", c.parts.visual],
    ["hook", c.parts.hook],
  ].filter(([, x]) => x !== undefined) as [string, number][];

  return (
    <article className={`grid gap-2 rounded-lg border p-2.5 ${chosen ? "border-cobalt/50" : "border-line"}`}>
      <div className="flex items-baseline gap-2">
        <span className="font-display text-lg leading-none font-extrabold text-cobalt">#{c.final_rank}</span>
        <span className="text-sm font-semibold tabular-nums">
          {clock(c.start)}–{clock(c.end)}
        </span>
        <span className="truncate text-xs text-ink-soft">
          {c.length.toFixed(1)} s · {c.section || c.kind}
        </span>
      </div>
      {c.covers.length > 0 && (
        <div className="grid grid-cols-3 gap-1.5">
          {c.covers.map((cover) => (
            <a key={cover.file} href={outputUrl(folder, cover.file)} target="_blank" rel="noreferrer" title={`Cover from ${cover.at.toFixed(1)} s (score ${cover.score.toFixed(2)})`} className="block aspect-[9/16] overflow-hidden rounded-md bg-media outline outline-1 outline-line transition hover:brightness-110">
              {/* eslint-disable-next-line @next/next/no-img-element -- local engine file */}
              <img src={`${outputUrl(folder, cover.file)}?v=${v}`} alt={`Cover at ${cover.at.toFixed(1)} s`} loading="lazy" className="h-full w-full object-cover" />
            </a>
          ))}
        </div>
      )}
      {c.ai ? (
        <>
          <p className="m-0 text-base leading-snug font-bold">{c.hook_text}</p>
          {c.ai.title && (
            <p className="m-0 text-sm leading-snug">
              <span className="text-ink-soft">Title: </span>
              {c.ai.title}
            </p>
          )}
          <p className="m-0 line-clamp-3 text-sm text-ink-soft" title={c.ai.reason}>{c.ai.reason}</p>
        </>
      ) : (
        <p className="m-0 text-sm text-ink-soft">Opens on “{c.hook_line}”</p>
      )}
      {c.caption && (
        <div className="flex items-start gap-1.5 rounded-md bg-ink/[0.04] p-2">
          <p className="m-0 min-w-0 flex-1 text-sm leading-snug break-words">{c.caption}</p>
          <button type="button" onClick={copy} aria-label="Copy caption" title="Copy caption" className="shrink-0 cursor-pointer rounded p-1 text-ink-soft hover:bg-ink/[0.06] hover:text-ink">
            {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
          </button>
        </div>
      )}
      <p className="m-0 text-xs text-ink-soft tabular-nums">
        score {c.score.toFixed(2)} · {parts.map(([k, x]) => `${k} ${x.toFixed(2)}`).join(" · ")}
        {!!c.parts.repeat_penalty && ` · shares lyrics with another pick`}
      </p>
      {c.job ? (
        <Button size="sm" variant={chosen && c.final_rank === 1 ? "primary" : "secondary"} icon={<Play className="size-3.5" />} onClick={() => onOpen(c.job)}>
          Open clip
        </Button>
      ) : chosen ? (
        <p className="m-0 text-xs text-ink-soft">This clip was deleted.</p>
      ) : null}
    </article>
  );
}
