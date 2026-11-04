"use client";

import { AlertTriangle, CheckCircle2, CircleDashed, ShieldCheck, XCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE, api, type Disposition, type InspectTarget, type Job, type QualityCheck, type QualityReport } from "@/lib/api";
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
  render: {
    fail: "Blocking problems found: fix and render again before uploading.",
    warning: "No blocking problems. Review the warnings below.",
    pass: "Every check that ran passed. Items marked Not checked still need your own review.",
    incomplete: "Cancelled: a partial report. Run it again for the remaining checks.",
  },
  preview: {
    fail: "Fix these before rendering.",
    warning: "Nothing blocking. Review the warnings before rendering.",
    pass: "The project looks ready to render. Check the rendered file afterwards.",
    incomplete: "Incomplete: run it again.",
  },
};

/** The body of a quality report (render or preview): verdict, categories, issue markers, the selected issue and the
 *  issue list. `total` > 0 draws the markers along a bar of that many seconds. */
const MARKS: { value: Disposition; label: string }[] = [
  { value: "reviewed", label: "Reviewed" },
  { value: "dismissed", label: "Dismiss" },
  { value: "fixed", label: "Fixed" },
];

export function QualityReportView({ report, total, onSelect, onReview, onApply, marks = MARKS }: {
  report: QualityReport;
  total: number;
  onSelect: (c: QualityCheck) => void;
  onReview?: (c: QualityCheck, d: Disposition) => void; // mark an issue
  onApply?: (c: QualityCheck) => void; // preview reports: apply the issue's safe fix (the editor's undo reverts it)
  marks?: typeof MARKS;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const checks = [...report.checks].sort((a, b) => ORDER[a.status] - ORDER[b.status] || (a.start ?? 0) - (b.start ?? 0));
  const shown = showAll ? checks : checks.filter((c) => c.status === "fail" || c.status === "warning");
  const timed = checks.filter((c) => c.start !== undefined && (c.status === "fail" || c.status === "warning"));
  const pick = checks.find((c) => c.id === selected);
  const categories = [...new Set(checks.map((c) => c.category))];
  const select = (c: QualityCheck) => {
    setSelected(c.id);
    onSelect(c);
  };

  return (
    <>
      {report.outdated && !report.archived && (
        <p className="m-0 rounded-md bg-warn/10 p-2 text-sm font-semibold text-warn">
          Outdated: the {report.stage === "render" ? "video" : "project"} changed since this report. Check it again.
        </p>
      )}
      <div className={`grid gap-1 ${report.outdated ? "opacity-60" : ""}`}>
        <p className={`m-0 text-sm font-bold ${report.verdict === "fail" ? "text-danger" : report.verdict === "pass" ? "text-ok" : "text-warn"}`}>
          {VERDICT[report.stage][report.verdict]}
        </p>
        <p className="m-0 text-2xs text-ink-soft">
          {report.profile_label} profile{report.file ? ` · ${report.file}` : ""}{report.mode ? ` · ${report.mode} check` : ""} ·{" "}
          {new Date(report.created).toLocaleString()} · {report.counts.fail} fail, {report.counts.warning} warning, {report.counts.pass} pass,{" "}
          {report.counts.not_checked} not checked
        </p>
        <ul className="m-0 flex list-none flex-wrap gap-1 p-0">
          {categories.map((cat) => {
            const worst = checks.filter((c) => c.category === cat).reduce((w, c) => (ORDER[c.status] < ORDER[w] ? c.status : w), "pass" as QualityCheck["status"]);
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

      {total > 0 && timed.length > 0 && (
        <div className="relative h-4 rounded bg-sunken" aria-label="Issues on the timeline">
          {timed.map((c) => (
            <button
              key={c.id}
              type="button"
              title={`${clock(c.start!)} ${c.title}`}
              aria-label={`Go to ${clock(c.start!)}: ${c.title}`}
              onClick={() => select(c)}
              className={`absolute top-0 h-full min-w-1.5 cursor-pointer rounded-sm ${c.status === "fail" ? "bg-danger" : "bg-warn"} ${
                selected === c.id ? "outline-2 outline-offset-1 outline-ink" : "opacity-80"
              }`}
              style={{ left: `${Math.min(c.start! / total, 1) * 100}%`, width: `${(Math.max((c.end ?? c.start!) - c.start!, 0) / total) * 100}%` }}
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
          {pick.evidence && report.base && (
            // eslint-disable-next-line @next/next/no-img-element -- local engine file
            <img src={`${API_BASE}${report.base}/${pick.evidence}?r=${encodeURIComponent(report.created)}`} alt={`Frame at ${clock(pick.start ?? 0)}`} className="max-h-48 w-fit rounded bg-media" />
          )}
          {pick.description && <p className="m-0 text-sm whitespace-pre-wrap text-ink-soft">{pick.description}</p>}
          {pick.reopened && <p className="m-0 text-sm font-semibold text-warn">You marked this fixed, but the latest check still finds it.</p>}
          {onReview && !report.archived && (pick.status === "warning" || pick.status === "fail") && (
            <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Mark this issue">
              {marks.map((m) => (
                <Button key={m.value} size="sm" variant={pick.disposition === m.value ? "primary" : "ghost"}
                  onClick={() => onReview(pick, pick.disposition === m.value ? "unreviewed" : m.value)}>
                  {m.label}
                </Button>
              ))}
              {pick.disposition === "fixed" && <span className="text-2xs text-ink-soft">Confirmed only when the next check no longer finds it.</span>}
            </div>
          )}
          {pick.recommendation && (
            <p className="m-0 text-sm">
              <span className="font-semibold">Suggested: </span>
              {pick.recommendation}
            </p>
          )}
          {/* an outdated report's fix may no longer fit the project: check again first */}
          {onApply && pick.fix && !report.outdated && pick.disposition !== "dismissed" && (
            <div className="flex flex-wrap items-center gap-1.5">
              <Button size="sm" variant="secondary" onClick={() => onApply(pick)}>Apply: {pick.fix.label}</Button>
              <span className="text-2xs text-ink-soft">Undo (Ctrl+Z) reverts it.</span>
            </div>
          )}
        </div>
      )}

      {!!report.resolved?.length && (
        <p className="m-0 text-sm text-ok">
          Confirmed fixed by this check: {report.resolved.map((r) => r.title).join(", ")}
        </p>
      )}
      {report.error && <p className="m-0 text-sm text-warn">The analysis stopped part way: {report.error}</p>}
      <div className="flex items-center justify-between">
        <span className="field-label">{showAll ? "All checks" : "Issues"}</span>
        <Button size="sm" variant="ghost" onClick={() => setShowAll(!showAll)}>
          {showAll ? "Issues only" : `All ${checks.length} checks`}
        </Button>
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
                  onClick={() => select(c)}
                  className={`flex w-full cursor-pointer items-start gap-1.5 rounded-md px-1.5 py-1 text-left text-sm hover:bg-ink/[0.05] ${selected === c.id ? "bg-cobalt-soft" : ""}`}
                >
                  <S.icon className={`mt-0.5 size-3.5 shrink-0 ${S.tone}`} aria-label={S.label} />
                  <span className={`min-w-0 flex-1 ${c.disposition === "dismissed" ? "text-ink-soft line-through" : ""}`}>{c.title}</span>
                  {c.disposition && c.disposition !== "unreviewed" && <span className="text-2xs text-ink-soft capitalize">{c.disposition}</span>}
                  {c.reopened && <span className="text-2xs font-semibold text-warn">Still found</span>}
                  {c.start !== undefined && <span className="font-mono text-2xs text-ink-soft">{clock(c.start)}</span>}
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <p className="m-0 text-2xs text-ink-soft">
        Scope: {report.sampled}.{" "}
        {report.stage === "preview"
          ? "This checks the project, not a rendered file: after rendering, run the Quality check on the video."
          : "This doesn't replace YouTube Studio's copyright (Content ID) and ad-suitability checks: upload privately or unlisted first and let those finish."}
      </p>
    </>
  );
}

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
    if (c.start === undefined) return;
    if (onSeek) onSeek(c.start);
    else if (player.current) {
      player.current.currentTime = c.start;
      void player.current.play().catch(() => {});
    }
  }

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

      {jobId ? (
        <div className="grid gap-1.5" role="status">
          <div className="h-1.5 overflow-hidden rounded bg-sunken">
            <div className="h-full bg-cobalt transition-[width]" style={{ width: `${Math.round((job?.progress ?? 0) * 100)}%` }} />
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-sm text-ink-soft">{job?.detail || "Waiting to start…"}</span>
            <Button size="sm" variant="ghost" onClick={() => api.cancelInspection(jobId).catch(() => {})}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <Button variant={report && !report.outdated ? "secondary" : "primary"} icon={<ShieldCheck className="size-4" />} onClick={start}>
          {report ? "Check again" : "Check the rendered video"}
        </Button>
      )}

      {report && !onSeek && (
        <video
          ref={player}
          src={`${src}${src.includes("?") ? "&" : "?"}r=${encodeURIComponent(report.created)}`}
          controls
          playsInline
          preload="metadata"
          className={`w-full rounded-lg bg-media ${vertical ? "max-h-[28rem] object-contain" : ""}`}
        />
      )}
      {report && (
        <QualityReportView
          key={report.created}
          report={report}
          total={report.media?.duration || 0}
          onSelect={seek}
          onReview={async (c, d) => {
            try {
              const r = await api.reviewIssue(target, c.id, d);
              if (r.report) setReport(r.report);
            } catch (e) {
              toast((e as Error).message, "error");
            }
          }}
        />
      )}
      {report && <History target={target} current={report.created} />}
    </section>
  );
}

/** Earlier checks of this video (kept 10 deep), opened read-only. */
function History({ target, current }: { target: InspectTarget; current: string }) {
  const [list, setList] = useState<{ id: string; created: string; verdict: QualityReport["verdict"]; counts: QualityReport["counts"] }[] | null>(null);
  const [open, setOpen] = useState<QualityReport | null>(null);

  async function toggle() {
    if (list) return setList(null);
    try {
      setList((await api.inspectionHistory(target)).history);
    } catch {
      setList([]);
    }
  }

  return (
    <div className="grid gap-1.5 border-t border-line pt-2">
      <Button size="sm" variant="ghost" className="justify-self-start" onClick={toggle} aria-expanded={!!list}>
        {list ? "Hide earlier checks" : "Earlier checks"}
      </Button>
      {list && list.length === 0 && <p className="m-0 text-sm text-ink-soft">No earlier checks.</p>}
      {list && list.length > 0 && (
        <ul className="m-0 grid list-none gap-0.5 p-0">
          {list.map((h) => (
            <li key={h.id}>
              <button type="button" className="flex w-full cursor-pointer justify-between gap-2 rounded px-1.5 py-1 text-left text-sm hover:bg-ink/[0.05]"
                onClick={async () => setOpen(open?.created === h.created ? null : (await api.inspectionHistoryEntry(target, h.id)).report)}>
                <span>{new Date(h.created).toLocaleString()}</span>
                <span className="text-ink-soft">{h.verdict} · {h.counts?.fail ?? 0} fail, {h.counts?.warning ?? 0} warning</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && open.created !== current && (
        <div className="grid gap-2 rounded-md bg-sunken p-2">
          <p className="m-0 text-2xs font-semibold tracking-wide text-ink-soft uppercase">Earlier report (read-only)</p>
          <QualityReportView key={open.created} report={open} total={open.media?.duration || 0} onSelect={() => {}} />
        </div>
      )}
    </div>
  );
}
