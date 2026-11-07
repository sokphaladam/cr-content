"use client";

import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, type HistoryGate, type HistoryGateItem, type HistoryTrace } from "@/lib/api";
import { Button, Message } from "./ui";

const STATUS: Record<HistoryGate["status"], { label: string; tone: string }> = {
  ready: { label: "Ready to render", tone: "text-ok" },
  review_required: { label: "Needs your review", tone: "text-warn" },
  blocked: { label: "Blocked", tone: "text-danger" },
  not_history: { label: "", tone: "" },
};

/** The history gate (H7): what stops this history video from rendering and publishing, and the creator's decisions.
 * Blockers must be fixed; most review items can be approved with a reason; unknown rights need confirming. */
export function HistoryGatePanel({ draftId, refreshKey = "" }: { draftId: string; refreshKey?: string }) {
  const [gate, setGate] = useState<HistoryGate | null>(null);
  const [msg, setMsg] = useState<{ text: string; error?: boolean }>({ text: "" });
  const [notes, setNotes] = useState<Record<string, string>>({});

  const load = useCallback(() => {
    api.historyGate(draftId).then(setGate, (e) => setMsg({ text: (e as Error).message, error: true }));
  }, [draftId]);
  useEffect(() => {
    api.historyGate(draftId).then(setGate, (e) => setMsg({ text: (e as Error).message, error: true }));
  }, [draftId, refreshKey]);

  async function decide(it: HistoryGateItem) {
    const note = notes[it.key] ?? "";
    try {
      const shot = it.key.split(":")[1];
      setGate(it.key.startsWith("rights:") ? await api.confirmRights(draftId, shot, note) : await api.approveGateItem(draftId, it.key, note));
      setMsg({ text: "" });
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    }
  }

  if (!gate || gate.status === "not_history") return null;
  const open = gate.items.filter((i) => !i.approved);
  return (
    <section className="mb-4 grid gap-2 rounded-lg border border-line p-3" aria-label="History check">
      <div className="flex items-center gap-2">
        <h3 className="m-0 text-sm font-bold">History check</h3>
        <span className={`text-sm font-bold ${STATUS[gate.status].tone}`}>{STATUS[gate.status].label}</span>
        <Button size="sm" variant="ghost" className="ml-auto" icon={<RefreshCw className="size-3.5" />} onClick={load}>
          Check again
        </Button>
      </div>
      <p className="m-0 text-xs text-ink-soft">
        Rendering and publishing wait until this is ready. Sources, rights and misleading pictures are checked by rules, not by an AI score.
      </p>
      {open.map((it) => (
        <div key={it.key} className="grid gap-1 rounded-md bg-ink/[0.04] p-2 text-sm">
          <span className={it.level === "blocked" ? "font-semibold text-danger" : "font-semibold text-warn"}>
            {it.level === "blocked" ? "Blocked: " : ""}{it.title}
          </span>
          {it.detail && <span className="break-all text-xs text-ink-soft">{it.detail}</span>}
          {it.fix && <span className="text-xs">{it.fix}</span>}
          {(it.overridable || it.key.startsWith("rights:")) && it.level === "review" && (
            <div className="flex gap-1.5">
              <input aria-label={it.key.startsWith("rights:") ? "What you checked" : "Why it's fine"} className="field-input flex-1 text-xs"
                placeholder={it.key.startsWith("rights:") ? "What you checked, e.g. Item page: Public Domain Mark" : "Why it's fine (kept as your record)"}
                value={notes[it.key] ?? ""} onChange={(e) => setNotes({ ...notes, [it.key]: e.target.value })} />
              <Button size="sm" disabled={(notes[it.key] ?? "").trim().length < 10} onClick={() => void decide(it)}>
                {it.key.startsWith("rights:") ? "Confirm rights" : "Approve"}
              </Button>
            </div>
          )}
        </div>
      ))}
      {gate.approved.length > 0 && (
        <details className="text-xs text-ink-soft">
          <summary className="cursor-pointer">Approved by you ({gate.approved.length})</summary>
          {gate.approved.map((a) => <p key={a.key} className="m-0 mt-1">{a.title}: “{a.note}” ({new Date(a.at).toLocaleString()})</p>)}
        </details>
      )}
      {gate.trace && <HistoryTraceView trace={gate.trace} />}
      <Message {...msg} />
    </section>
  );
}

const CLAIM_TONE: Record<string, string> = { supported: "text-ok", disputed: "text-warn", uncertain: "text-warn", unsupported: "text-danger" };

/** Which source each claim rests on, and what kind of material each shot is (archival, modern stock, AI reconstruction). */
export function HistoryTraceView({ trace }: { trace: HistoryTrace }) {
  return (
    <details className="text-xs">
      <summary className="cursor-pointer font-semibold">Claims and sources ({trace.claims.length}) · shots ({trace.shots.length})</summary>
      <ul className="m-0 mt-1 grid gap-1 pl-4">
        {trace.claims.map((c) => (
          <li key={c.id}>
            <span className={`font-semibold ${CLAIM_TONE[c.status] ?? ""}`}>{c.status}</span> · scene {c.scenes.join(", ")} · {c.text}{" "}
            {c.sources.length ? (
              c.sources.map((s, i) => (
                <a key={i} href={s.url} target="_blank" rel="noreferrer" className="mr-1 underline">{s.title || "source"}</a>
              ))
            ) : (
              <span className="text-danger">no source</span>
            )}
          </li>
        ))}
      </ul>
      <ul className="m-0 mt-1 grid gap-0.5 pl-4 text-ink-soft">
        {trace.shots.map((s) => (
          <li key={s.id}>
            {s.id}: <span className={s.material === "AI reconstruction" || s.material === "modern stock" ? "font-semibold text-ink" : ""}>{s.material}</span>
            {s.origin && ` (planned as ${s.origin})`}
            {s.rights === "rights_unknown" && <span className="text-warn"> · rights {s.rights_note ? `confirmed: ${s.rights_note}` : "unknown"}</span>}
            {s.licence && ` · ${s.licence}`}
          </li>
        ))}
      </ul>
    </details>
  );
}
