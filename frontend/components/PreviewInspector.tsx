"use client";

import { ClipboardCheck, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Lang, type QualityCheck, type QualityReport, type VideoScript } from "@/lib/api";
import { QualityReportView } from "./QualityInspector";
import { Button, useToast } from "./ui";

const QUICK_DELAY_MS = 1200; // quick checks re-run this long after the last edit

function Header({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid gap-1">
      <h3 className="m-0 flex items-center gap-1.5 text-base font-bold">
        <ClipboardCheck className="size-4 text-cobalt" aria-hidden /> Pre-render check
        <span className="rounded bg-sunken px-1.5 text-2xs font-semibold tracking-wide text-ink-soft uppercase">Project</span>
      </h3>
      <p className="m-0 text-sm text-ink-soft">{children}</p>
    </div>
  );
}

/** Preview Inspector for a Shorts draft: quick checks follow your edits; the full check also probes every media file.
 *  A full report isn't replaced by quick ones: it's marked outdated when the project changes. */
export function ShortsPreviewCheck({ script, lang, music, lengths, total, onIssue }: {
  script: VideoScript;
  lang: Lang;
  music: string;
  lengths: number[];
  total: number;
  onIssue: (c: QualityCheck) => void;
}) {
  const toast = useToast();
  const [report, setReport] = useState<QualityReport | null>(null);
  const [madeFrom, setMadeFrom] = useState("");
  const [busy, setBusy] = useState(false);
  const key = JSON.stringify({ script, lang, music, lengths });

  async function run(full: boolean, from: string) {
    if (full) setBusy(true);
    try {
      const r = await api.previewShort({ ...JSON.parse(from), full });
      setReport(r);
      setMadeFrom(from);
    } catch (e) {
      if (full) toast((e as Error).message, "error");
    } finally {
      if (full) setBusy(false);
    }
  }

  const fullShown = report?.mode === "full";
  useEffect(() => {
    if (fullShown) return; // keep the full report; it shows as outdated instead
    const t = window.setTimeout(() => void run(false, key), QUICK_DELAY_MS);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `key` carries everything run() reads
  }, [key, fullShown]);

  return (
    <section aria-label="Pre-render check" className="grid gap-3 card p-3.5">
      <Header>
        Checks this draft before rendering: media files, timing, text placement, captions, audio and structure. Quick
        checks update as you edit.
      </Header>
      <div className="flex gap-2">
        <Button size="sm" variant="primary" loading={busy} onClick={() => run(true, key)}>Full check</Button>
        {fullShown && <Button size="sm" variant="ghost" onClick={() => run(false, key)}>Back to quick checks</Button>}
      </div>
      {report ? (
        <QualityReportView key={report.created} report={{ ...report, outdated: madeFrom !== key }} total={total} onSelect={onIssue} />
      ) : (
        <p className="m-0 text-sm text-ink-soft">Checking…</p>
      )}
      <StoryReview script={script} lang={lang} total={total} onIssue={onIssue} />
      <FootageReview script={script} lengths={lengths} total={total} onIssue={onIssue} />
    </section>
  );
}

/** Preview Inspector for a Lyric Studio song folder (the saved song: save your edits first). */
export function SongPreviewCheck({ slug, stamp, duration, onSeek }: {
  slug: string;
  stamp: string; // changes when the song is saved or its pictures change, so the outdated flag is re-read
  duration: number;
  onSeek: (t: number) => void;
}) {
  const toast = useToast();
  const [report, setReport] = useState<QualityReport | null>(null);
  const [busy, setBusy] = useState<"" | "quick" | "full">("");

  useEffect(() => {
    api.previewSong(slug).then((r) => setReport(r.report)).catch(() => setReport(null));
  }, [slug, stamp]);

  async function run(full: boolean) {
    setBusy(full ? "full" : "quick");
    try {
      setReport(await api.checkSong(slug, full));
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy("");
    }
  }

  return (
    <section aria-label="Pre-render check" className="card grid gap-3 p-4">
      <Header>
        Checks the saved song before rendering: the song file, lyric timing (order, quick flashes, gaps, duplicates,
        long lines), pictures and upload details. The full check also measures every line with the video&apos;s font.
      </Header>
      <div className="flex gap-2">
        <Button size="sm" variant="secondary" loading={busy === "quick"} disabled={!!busy} onClick={() => run(false)}>Quick check</Button>
        <Button size="sm" variant="primary" loading={busy === "full"} disabled={!!busy} onClick={() => run(true)}>Full check</Button>
      </div>
      {report && <QualityReportView key={report.created} report={report} total={duration} onSelect={(c) => c.start !== undefined && onSeek(c.start)} />}
    </section>
  );
}

/** Optional, AI-assisted editorial review of the script. Sends text only, and only when you ask. */
function StoryReview({ script, lang, total, onIssue }: { script: VideoScript; lang: Lang; total: number; onIssue: (c: QualityCheck) => void }) {
  const toast = useToast();
  const [report, setReport] = useState<QualityReport | null>(null);
  const [madeFrom, setMadeFrom] = useState("");
  const [busy, setBusy] = useState(false);
  const key = JSON.stringify(script);

  async function run() {
    setBusy(true);
    try {
      setReport(await api.storyReview({ script, lang }));
      setMadeFrom(key);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-2 border-t border-line pt-3">
      <div className="flex items-center justify-between gap-2">
        <span className="field-label">Story review <span className="font-normal">optional, AI</span></span>
        <Button size="sm" variant="secondary" icon={<Sparkles className="size-3.5" />} loading={busy} onClick={run}>
          {report ? "Review again" : "Send to Gemini"}
        </Button>
      </div>
      <p className="m-0 text-2xs text-ink-soft">
        Sends the script text (title, narration, footage searches, headlines) to Gemini with your API key. No video, pictures
        or audio. You get advice on the hook, payoff, structure and ending, not a prediction of views.
      </p>
      {report && <QualityReportView key={report.created} report={{ ...report, outdated: madeFrom !== key }} total={total} onSelect={onIssue} />}
    </div>
  );
}

/** Optional, AI-assisted check that each scene's footage shows what its narration says. Sends frames, only when you ask. */
function FootageReview({ script, lengths, total, onIssue }: { script: VideoScript; lengths: number[]; total: number; onIssue: (c: QualityCheck) => void }) {
  const toast = useToast();
  const [report, setReport] = useState<QualityReport | null>(null);
  const [madeFrom, setMadeFrom] = useState("");
  const [busy, setBusy] = useState(false);
  const key = JSON.stringify({ script, lengths });

  async function run() {
    setBusy(true);
    try {
      setReport(await api.footageReview({ script, lengths }));
      setMadeFrom(key);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-2 border-t border-line pt-3">
      <div className="flex items-center justify-between gap-2">
        <span className="field-label">Footage vs narration <span className="font-normal">optional, AI</span></span>
        <Button size="sm" variant="secondary" icon={<Sparkles className="size-3.5" />} loading={busy} onClick={run}>
          {report ? "Check again" : "Check footage with Gemini"}
        </Button>
      </div>
      <p className="m-0 text-2xs text-ink-soft">
        Sends three frames of each scene&apos;s footage (the part shown) and its voiceover text to Gemini with your API key.
        Cutaways and footage picked at render aren&apos;t checked. Answers are kept, so checking again only asks about changed scenes.
      </p>
      {report && <QualityReportView key={report.created} report={{ ...report, outdated: madeFrom !== key }} total={total} onSelect={onIssue} />}
    </div>
  );
}
