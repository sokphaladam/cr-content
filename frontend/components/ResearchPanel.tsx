"use client";

import { ExternalLink, Plus, Search, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, type ClaimStatus, type HistoricalClaim, type ResearchBrief, type ResearchKind } from "@/lib/api";
import { Button, Chip, IconButton, Message } from "./ui";

const STATUS: Record<ClaimStatus, { label: string; tone: string }> = {
  supported: { label: "Supported", tone: "text-ok" },
  disputed: { label: "Disputed", tone: "text-warn" },
  uncertain: { label: "Uncertain", tone: "text-warn" },
  unsupported: { label: "No source", tone: "text-danger" },
};
const ROLE: Record<string, string> = {
  primary: "Primary source", scholarly_secondary: "Scholarly", museum_or_archive: "Museum / archive", reference: "Reference",
};
const STATE = { draft: "Not reviewed", needs_review: "Needs your review", approved: "Approved" };

/** Research brief for a history project (or a topic): claims, their sources and the evidence that backs them. A claim
 * is "Supported" only when a stored source's passage is attached; the engine decides that, not the AI. */
export function ResearchPanel({ kind, refId }: { kind: ResearchKind; refId: string }) {
  const [brief, setBrief] = useState<ResearchBrief | null>(null);
  const [blockers, setBlockers] = useState<string[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [detail, setDetail] = useState("");
  const [msg, setMsg] = useState<{ text: string; error?: boolean }>({ text: "" });
  const [newClaim, setNewClaim] = useState("");
  const [src, setSrc] = useState({ url: "", note: "", excerpt: "" });
  const [adding, setAdding] = useState(false);

  const reload = useCallback(async () => {
    try {
      const r = await api.research(kind, refId);
      setBrief(r.brief);
      setBlockers(r.blockers);
      setJobId(r.job);
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    } finally {
      setLoaded(true);
    }
  }, [kind, refId]);

  useEffect(() => {
    api.research(kind, refId).then(
      (r) => {
        setBrief(r.brief);
        setBlockers(r.blockers);
        setJobId(r.job);
        setLoaded(true);
      },
      (e) => {
        setMsg({ text: (e as Error).message, error: true });
        setLoaded(true);
      },
    );
  }, [kind, refId]);

  useEffect(() => {
    if (!jobId) return;
    const timer = setInterval(async () => {
      try {
        const j = await api.job(jobId);
        setDetail(j.log[j.log.length - 1] ?? (j.status === "queued" ? "waiting to start…" : "researching…"));
        if (j.status === "done" || j.status === "error") {
          setJobId(null);
          setDetail("");
          if (j.status === "error") setMsg({ text: j.error ?? "The research failed.", error: true });
          await reload();
        }
      } catch {
        setJobId(null);
        setMsg({ text: "The research was interrupted (the engine restarted). Run it again.", error: true });
      }
    }, 1500);
    return () => clearInterval(timer);
  }, [jobId, reload]);

  async function run() {
    setMsg({ text: "" });
    try {
      setJobId((await api.runResearch(kind, refId)).id);
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    }
  }

  async function save(next: ResearchBrief) {
    setBrief(next); // shown at once; the engine's settled version replaces it
    try {
      setBrief(await api.saveResearch(kind, refId, next));
      setBlockers((await api.research(kind, refId)).blockers);
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    }
  }

  const editClaim = (id: string, patch: Partial<HistoricalClaim>) =>
    brief && save({ ...brief, claims: brief.claims.map((c) => (c.id === id ? { ...c, ...patch } : c)) });

  async function addSource(e: React.FormEvent) {
    e.preventDefault();
    setAdding(true);
    try {
      setBrief(await api.addResearchSource(kind, refId, src));
      setSrc({ url: "", note: "", excerpt: "" });
      setMsg({ text: "" });
    } catch (err) {
      setMsg({ text: (err as Error).message, error: true });
    } finally {
      setAdding(false);
    }
  }

  async function approve() {
    try {
      setBrief(await api.approveResearch(kind, refId));
      setMsg({ text: "Research approved. Edits after this need approving again." });
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    }
  }

  if (!loaded) return <div className="p-3"><Message text="Loading the research…" /></div>;
  const sources = Object.fromEntries((brief?.sources ?? []).map((s) => [s.id, s]));
  const excerpts = (brief?.sources ?? []).flatMap((s) => s.excerpts.map((x, i) => ({ key: `${s.id}#${i}`, source: s, text: x })));

  return (
    <div className="grid gap-4 p-3">
      <section className="grid gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Chip tone={brief?.research_status === "approved" ? "ink" : "caption"}>
            {brief ? STATE[brief.research_status] : "Not yet researched"}
          </Chip>
          {brief && brief.revision > 0 && <Chip>Revision {brief.revision}{brief.approved_revision ? ` · approved r${brief.approved_revision}` : ""}</Chip>}
        </div>
        {brief?.topic && <p className="m-0 text-sm font-semibold text-ink">{brief.topic}</p>}
        <Button variant="primary" size="sm" loading={!!jobId} onClick={run} icon={<Search className="size-3.5" />}>
          {jobId ? "Researching…" : brief?.claims.length ? "Re-check claims and sources" : "Research"}
        </Button>
        {jobId && <p className="m-0 text-xs text-ink-soft" role="status">{detail}</p>}
        {!brief && !jobId && (
          <p className="m-0 text-sm text-ink-soft">
            Splits the narration into factual claims, searches Google (through Gemini) and Wikipedia, and attaches the passages
            that back or dispute each claim. Nothing counts as supported without a source.
          </p>
        )}
        {brief?.provider_notes.map((n) => <p key={n} className="m-0 text-xs text-warn">{n}</p>)}
        <Message {...msg} />
      </section>

      {brief && (brief.summary || brief.period) && (
        <section className="grid gap-1 text-sm">
          {brief.period && <p className="m-0"><span className="font-semibold">Period:</span> {brief.period}</p>}
          {brief.summary && <p className="m-0 text-ink-soft">{brief.summary}</p>}
        </section>
      )}

      {brief && (
        <section className="grid gap-2" aria-label="Claims">
          <h3 className="m-0 text-sm font-bold">Claims ({brief.claims.length})</h3>
          {brief.claims.map((c) => (
            <div key={c.id} className="grid gap-1.5 rounded-md border border-line p-2">
              <div className="flex items-center gap-2">
                <span className={`text-xs font-bold ${STATUS[c.status].tone}`}>{STATUS[c.status].label}</span>
                <select aria-label="Importance" className="field-input h-7 py-0 text-xs" value={c.importance}
                  onChange={(e) => editClaim(c.id, { importance: e.target.value as HistoricalClaim["importance"] })}>
                  <option value="central">Central</option>
                  <option value="supporting">Supporting</option>
                  <option value="optional">Optional</option>
                </select>
                <select aria-label="Mark as" className="field-input h-7 py-0 text-xs" value={c.status}
                  title="You can mark a claim less sure than its sources; only sources can make it supported"
                  onChange={(e) => editClaim(c.id, { status: e.target.value as ClaimStatus })}>
                  {Object.entries(STATUS).map(([v, s]) => <option key={v} value={v}>{s.label}</option>)}
                </select>
                <IconButton label="Remove claim" onClick={() => save({ ...brief, claims: brief.claims.filter((x) => x.id !== c.id) })}>
                  <Trash2 className="size-3.5" />
                </IconButton>
              </div>
              <textarea aria-label="Claim" rows={2} className="field-input resize-y text-sm" defaultValue={c.claim_text}
                onBlur={(e) => e.target.value.trim() !== c.claim_text && editClaim(c.id, { claim_text: e.target.value.trim() })} />
              {c.notes && <p className="m-0 text-xs text-warn">{c.notes}</p>}
              <ul className="m-0 grid list-none gap-1 p-0">
                {c.evidence.map((ev, i) => (
                  <li key={i} className="grid gap-0.5 rounded bg-ink/[0.04] p-1.5 text-xs">
                    <span className="flex items-center gap-1.5">
                      <span className={ev.stance === "disputes" ? "font-bold text-warn" : "font-bold text-ok"}>{ev.stance === "disputes" ? "Disputes" : "Backs"}</span>
                      <a href={sources[ev.source_id]?.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 underline">
                        {sources[ev.source_id]?.publisher || sources[ev.source_id]?.title}
                        <ExternalLink className="size-3" />
                      </a>
                      <button type="button" className="ml-auto text-ink-soft hover:text-danger" aria-label="Detach this evidence"
                        onClick={() => editClaim(c.id, { evidence: c.evidence.filter((_, j) => j !== i) })}>
                        <Trash2 className="size-3" />
                      </button>
                    </span>
                    <span className="text-ink-soft">“{ev.excerpt}”</span>
                  </li>
                ))}
              </ul>
              {excerpts.length > 0 && (
                <select aria-label="Attach evidence" className="field-input h-7 py-0 text-xs" value=""
                  onChange={(e) => {
                    const [key, stance] = e.target.value.split("|");
                    const x = excerpts.find((p) => p.key === key);
                    if (x) editClaim(c.id, { evidence: [...c.evidence, { source_id: x.source.id, excerpt: x.text, stance: stance as "supports" | "disputes" }] });
                  }}>
                  <option value="">Attach a passage…</option>
                  {excerpts.map((x) => (
                    <optgroup key={x.key} label={x.source.publisher || x.source.title}>
                      <option value={`${x.key}|supports`}>Backs: {x.text.slice(0, 90)}</option>
                      <option value={`${x.key}|disputes`}>Disputes: {x.text.slice(0, 90)}</option>
                    </optgroup>
                  ))}
                </select>
              )}
            </div>
          ))}
          <form className="flex gap-1.5" onSubmit={(e) => {
            e.preventDefault();
            if (!newClaim.trim()) return;
            save({ ...brief, claims: [...brief.claims, { id: `claim-${Date.now().toString(36)}`, claim_text: newClaim.trim(), claim_type: "event",
              status: "unsupported", importance: "central", evidence: [], source_ids: [], notes: "", script_scene_ids: [], locked: true }] });
            setNewClaim("");
          }}>
            <input aria-label="New claim" className="field-input flex-1 text-sm" placeholder="Add a claim" value={newClaim} onChange={(e) => setNewClaim(e.target.value)} />
            <IconButton label="Add claim" type="submit"><Plus className="size-4" /></IconButton>
          </form>
        </section>
      )}

      {brief && brief.contradictions.length + brief.open_questions.length > 0 && (
        <section className="grid gap-1 text-sm">
          <h3 className="m-0 text-sm font-bold">Disagreements and open questions</h3>
          {brief.contradictions.map((x, i) => (
            <p key={i} className="m-0 text-warn">{brief.claims.find((c) => c.id === x.claim_id)?.claim_text ?? "General"}: {x.note}</p>
          ))}
          {brief.open_questions.map((q) => <p key={q} className="m-0 text-ink-soft">? {q}</p>)}
        </section>
      )}

      <section className="grid gap-2" aria-label="Sources">
        <h3 className="m-0 text-sm font-bold">Sources ({brief?.sources.length ?? 0})</h3>
        {brief?.sources.map((s) => (
          <details key={s.id} className="rounded-md border border-line p-2 text-sm">
            <summary className="cursor-pointer">
              <span className="font-semibold">{s.title || s.publisher}</span>{" "}
              <span className="text-xs text-ink-soft">{s.publisher} · {ROLE[s.source_role]} · {s.provider === "google_search" ? "Google Search" : s.provider === "wikipedia" ? "Wikipedia" : "Added by you"}</span>
              {s.retrieval_error && <span className="block text-xs text-danger">The page {s.retrieval_error}: add the passage yourself to use it.</span>}
            </summary>
            <div className="mt-1 grid gap-1 text-xs">
              <a href={s.url} target="_blank" rel="noreferrer" className="break-all underline">{s.url}</a>
              {s.note && <p className="m-0">Note: {s.note}</p>}
              {s.excerpts.map((x, i) => <p key={i} className="m-0 text-ink-soft">“{x}”</p>)}
              <select aria-label="Source type" className="field-input h-7 py-0 text-xs" value={s.source_role}
                onChange={(e) => save({ ...brief, sources: brief.sources.map((x) => (x.id === s.id ? { ...x, source_role: e.target.value as typeof s.source_role } : x)) })}>
                {Object.entries(ROLE).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
          </details>
        ))}
        <form onSubmit={addSource} className="grid gap-1.5">
          <input aria-label="Source link" required type="url" className="field-input text-sm" placeholder="https://… source link" value={src.url}
            onChange={(e) => setSrc({ ...src, url: e.target.value })} />
          <input aria-label="Source note" className="field-input text-sm" placeholder="Note (optional)" value={src.note} onChange={(e) => setSrc({ ...src, note: e.target.value })} />
          <textarea aria-label="Passage from the source" rows={2} className="field-input text-sm" placeholder="The passage that backs a claim (optional)"
            value={src.excerpt} onChange={(e) => setSrc({ ...src, excerpt: e.target.value })} />
          <Button size="sm" type="submit" loading={adding} icon={<Plus className="size-3.5" />}>Add source</Button>
        </form>
      </section>

      {brief && brief.claims.length > 0 && (
        <section className="grid gap-1.5 border-t border-line pt-3">
          {blockers.length > 0 && <p className="m-0 text-xs text-danger">Central claims without a source: {blockers.join(" · ")}</p>}
          <Button variant="primary" size="sm" disabled={blockers.length > 0 || brief.research_status === "approved"} onClick={approve}>
            {brief.research_status === "approved" ? "Approved" : "Approve research"}
          </Button>
        </section>
      )}
    </div>
  );
}
