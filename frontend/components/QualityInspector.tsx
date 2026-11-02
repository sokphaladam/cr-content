"use client";

import { AlertTriangle, CheckCircle2, CircleDashed, ShieldCheck, XCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE, api, type InspectTarget, type Job, type QualityCheck, type QualityReport } from "@/lib/api";
import { Button, useToast } from "./ui";

const clock = (t: number) => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, "0")}`;
const STATUS = {
  fail: { label: "Fail", icon: XCircle, tone: "text-danger" },
  warning: { label: "Warning", icon: AlertTriangle, tone: "text-warn" },
  pass: { label: "Pass", icon: CheckCircle2, tone: "text-ok" },
  not_checked: { label: "Not checked", icon: CircleDashed, tone: "text-ink-soft" },
} as const;
const ORDER = { fail: 0, warning: 1, not_checked: 2, pass: 3 };
const VERDICT = {
  fail: "Blocking problems found: fix and render again before uploading.",
  warning: "No blocking problems. Review the warnings below.",
  pass: "Every check that ran passed. Items marked Not checked still need your own review.",
  incomplete: "Cancelled: a partial report. Run it again for the remaining checks.",
};

/** Final Render Inspector: checks the exported file itself and lists timestamped issues; clicking one seeks the
 *  player. With `onSeek` it drives the page's own player, otherwise it shows its own. */
export function QualityInspector({ target, src, vertical, onSeek }: {
  target: InspectTarget;
  src: string;
  vertical?: boolean;
  onSeek?: (t: number) => void;
}) {
  const toast = useToast();
  const [report, setReport] = useState<QualityReport | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const player = useRef<HTMLVideoElement>(null);
  const key = JSON.stringify(target);

  const load = useCallback(async () => {
    try {
      const r = await api.inspection(JSON.parse(key));
      setReport(r.report);
      if (r.job) setJobId(r.job);
    } catch {
      setReport(null); // an older engine without the inspector: the button still shows
    }
  }, [key]);

  useEffect(() => {
    api
      .inspection(JSON.parse(key))
      .then((r) => {
        setReport(r.report);
        if (r.job) setJobId(r.job); // a run started before this card was opened
      })
      .catch(() => setReport(null));
  }, [key]);

  useEffect(() => {
    if (!jobId) return;
    const t = window.setInterval(async () => {
      let j: Job;
      try {
        j = await api.job(jobId);
      } catch {
        return; // engine restarting: try again next tick
      }
      setJob(j);
      if (j.status === "done" || j.status === "error") {
        window.clearInterval(t);
        setJobId(null);
        if (j.status === "error") toast(j.error ?? "The quality check failed", "error");
        await load();
      }
    }, 1000);
    return () => window.clearInterval(t);
  }, [jobId, load, toast]);

  async function start() {
    try {
      const { id } = await api.inspect(target);
      setJob(null);
      setJobId(id);
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  function seek(c: QualityCheck) {
    setSelected(c.id);
    if (c.start === undefined) return;
    if (onSeek) onSeek(c.start);
    else if (player.current) {
      player.current.currentTime = c.start;
      void player.current.play().catch(() => {});
    }
  }

  const running = !!jobId;
  const checks = [...(report?.checks ?? [])].sort((a, b) => ORDER[a.status] - ORDER[b.status] || (a.start ?? 0) - (b.start ?? 0));
  const shown = showAll ? checks : checks.filter((c) => c.status === "fail" || c.status === "warning");
  const timed = checks.filter((c) => c.start !== undefined && (c.status === "fail" || c.status === "warning"));
  const total = report?.media?.duration || 0;
  const pick = checks.find((c) => c.id === selected);
  const categories = [...new Set(checks.map((c) => c.category))];

  return (
    <section aria-label="Quality check" className="grid gap-3 card p-3.5">
      <div className="grid gap-1">
        <h3 className="m-0 flex items-center gap-1.5 text-base font-bold">
          <ShieldCheck className="size-4 text-cobalt" aria-hidden /> Quality check
          <span className="rounded bg-sunken px-1.5 text-2xs font-semibold tracking-wide text-ink-soft uppercase">Rendered file</span>
        </h3>
        <p className="m-0 text-sm text-ink-soft">
          Checks the exported video itself: streams, size, length, decode errors, black or frozen picture, silence and
          loudness. Runs locally; the file is never changed.
        </p>
      </div>

      {running ? (
        <div className="grid gap-1.5" role="status">
          <div className="h-1.5 overflow-hidden rounded bg-sunken">
            <div className="h-full bg-cobalt transition-[width]" style={{ width: `${Math.round((job?.progress ?? 0) * 100)}%` }} />
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-sm text-ink-soft">{job?.detail || "Waiting to start…"}</span>
            <Button size="sm" variant="ghost" onClick={() => jobId && api.cancelInspection(jobId).catch(() => {})}>Cancel</Button>
          </div>
        </div>
      ) : (
        <Button variant={report && !report.outdated ? "secondary" : "primary"} icon={<ShieldCheck className="size-4" />} onClick={start}>
          {report ? "Check again" : "Check the rendered video"}
        </Button>
      )}

      {report && (
        <>
          {report.outdated && (
            <p className="m-0 rounded-md bg-warn/10 p-2 text-sm font-semibold text-warn">
              Outdated: the video changed since this report. Check it again.
            </p>
          )}
          <div className={`grid gap-1 ${report.outdated ? "opacity-60" : ""}`}>
            <p className={`m-0 text-sm font-bold ${report.verdict === "fail" ? "text-danger" : report.verdict === "pass" ? "text-ok" : "text-warn"}`}>
              {VERDICT[report.verdict]}
            </p>
            <p className="m-0 text-2xs text-ink-soft">
              {report.profile_label} profile · {report.file} · {new Date(report.created).toLocaleString()} ·{" "}
              {report.counts.fail} fail, {report.counts.warning} warning, {report.counts.pass} pass, {report.counts.not_checked} not checked
            </p>
            <ul className="m-0 flex list-none flex-wrap gap-1 p-0">
              {categories.map((cat) => {
                const items = checks.filter((c) => c.category === cat);
                const worst = items.reduce((w, c) => (ORDER[c.status] < ORDER[w] ? c.status : w), "pass" as QualityCheck["status"]);
                const S = STATUS[worst];
                return (
                  <li key={cat} className="flex items-center gap-1 rounded bg-sunken px-1.5 py-0.5 text-2xs font-semibold capitalize">
                    <S.icon className={`size-3 ${S.tone}`} aria-hidden /> {cat}
                    <span className="sr-only">: {S.label}</span>
                  </li>
                );
              })}
            </ul>
          </div>

          {!onSeek && (
            <video
              ref={player}
              src={`${src}${src.includes("?") ? "&" : "?"}r=${encodeURIComponent(report.created)}`}
              controls
              playsInline
              preload="metadata"
              className={`w-full rounded-lg bg-media ${vertical ? "max-h-[28rem] object-contain" : ""}`}
            />
          )}

          {total > 0 && timed.length > 0 && (
            <div className="relative h-4 rounded bg-sunken" aria-label="Issues on the timeline">
              {timed.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  title={`${clock(c.start!)} ${c.title}`}
                  aria-label={`Go to ${clock(c.start!)}: ${c.title}`}
                  onClick={() => seek(c)}
                  className={`absolute top-0 h-full min-w-1.5 cursor-pointer rounded-sm ${c.status === "fail" ? "bg-danger" : "bg-warn"} ${
                    selected === c.id ? "outline-2 outline-offset-1 outline-ink" : "opacity-80"
                  }`}
                  style={{ left: `${(c.start! / total) * 100}%`, width: `${(((c.end ?? c.start!) - c.start!) / total) * 100}%` }}
                />
              ))}
            </div>
          )}

          {pick && (
            <div className="grid gap-1.5 rounded-md border border-line p-2.5">
              <p className="m-0 text-sm font-bold">
                {pick.start !== undefined && <span className="mr-1 font-mono text-ink-soft">{clock(pick.start)}</span>}
                {pick.title}
              </p>
              {pick.evidence && (
                // eslint-disable-next-line @next/next/no-img-element -- local engine file
                <img src={`${API_BASE}${report.base}/${pick.evidence}?r=${encodeURIComponent(report.created)}`} alt={`Frame at ${clock(pick.start ?? 0)}`} className="max-h-48 w-fit rounded bg-media" />
              )}
              {pick.description && <p className="m-0 text-sm whitespace-pre-wrap text-ink-soft">{pick.description}</p>}
              {pick.recommendation && <p className="m-0 text-sm"><span className="font-semibold">Suggested: </span>{pick.recommendation}</p>}
            </div>
          )}

          <div className="flex items-center justify-between">
            <span className="field-label">{showAll ? "All checks" : "Issues"}</span>
            <Button size="sm" variant="ghost" onClick={() => setShowAll(!showAll)}>{showAll ? "Issues only" : `All ${checks.length} checks`}</Button>
          </div>
          {shown.length === 0 ? (
            <p className="m-0 text-sm text-ink-soft">No failures or warnings.</p>
          ) : (
            <ul className="m-0 grid max-h-80 list-none gap-0.5 overflow-auto p-0">
              {shown.map((c) => {
                const S = STATUS[c.status];
                return (
                  <li key={c.id}>
                    <button
                      type="button"
                      onClick={() => seek(c)}
                      className={`flex w-full cursor-pointer items-start gap-1.5 rounded-md px-1.5 py-1 text-left text-sm hover:bg-ink/[0.05] ${selected === c.id ? "bg-cobalt-soft" : ""}`}
                    >
                      <S.icon className={`mt-0.5 size-3.5 shrink-0 ${S.tone}`} aria-label={S.label} />
                      <span className="min-w-0 flex-1">{c.title}</span>
                      {c.start !== undefined && <span className="font-mono text-2xs text-ink-soft">{clock(c.start)}</span>}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
          <p className="m-0 text-2xs text-ink-soft">
            Scope: {report.sampled}. This doesn&apos;t replace YouTube Studio&apos;s copyright (Content ID) and ad-suitability
            checks: upload privately or unlisted first and let those finish.
          </p>
        </>
      )}
    </section>
  );
}
