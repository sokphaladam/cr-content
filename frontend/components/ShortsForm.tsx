"use client";

import { ClipboardCheck, FileSpreadsheet } from "lucide-react";
import { useState } from "react";
import { api, type ShortsPlan } from "@/lib/api";
import { Button, Field, FileInput, Message } from "./ui";

/** Shorts Mode: upload a content plan, tick episodes, and build each one's pre-flight report to approve and render. */
export function ShortsForm({ onStarted }: { onStarted: (jobId: string, title: string) => void }) {
  const [plan, setPlan] = useState<ShortsPlan | null>(null);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState<"" | "read" | "make">("");
  const [msg, setMsg] = useState<{ text: string; error?: boolean }>({ text: "" });

  async function read(file: File | undefined) {
    if (!file) return;
    setBusy("read");
    setPlan(null);
    setMsg({ text: "Reading your plan…" });
    try {
      const p = await api.readShorts(file);
      setPlan(p);
      setPicked(new Set(p.episodes.filter((e) => !e.posted).map((e) => e.ep)));
      setMsg({ text: "" });
    } catch (err) {
      setMsg({ text: (err as Error).message, error: true });
    } finally {
      setBusy("");
    }
  }

  const eps = plan ? plan.episodes.filter((e) => picked.has(e.ep)).map((e) => e.ep) : [];

  async function make() {
    if (!plan) return;
    setBusy("make");
    try {
      const { id } = await api.makeShorts(plan.file, eps);
      setMsg({ text: "" });
      const one = plan.episodes.find((e) => e.ep === eps[0]);
      onStarted(id, eps.length === 1 && one ? one.title : `${eps.length} Shorts from ${plan.name}`);
    } catch (err) {
      setMsg({ text: (err as Error).message, error: true });
    } finally {
      setBusy("");
    }
  }

  function toggle(ep: number, on: boolean) {
    setPicked((s) => {
      const next = new Set(s);
      if (on) next.add(ep);
      else next.delete(ep);
      return next;
    });
  }

  return (
    <div className="grid gap-5 card p-5 sm:p-6">
      <Field label="Content plan (.xlsx)" hint="a Scripts sheet with Ep | Time | Visual | On-screen Text | Voiceover" htmlFor="shorts-file">
        <FileInput
          id="shorts-file"
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          file={plan?.name ?? ""}
          disabled={busy !== ""}
          onReject={(text) => setMsg({ text, error: true })}
          onFile={(file) => void read(file)}
        />
      </Field>

      {plan && (
        <fieldset className="m-0 grid gap-2 border-0 p-0">
          <legend className="mb-2 flex w-full items-center justify-between gap-3">
            <span className="field-label">
              {plan.episodes.length} episodes in {plan.name}
            </span>
            <span className="flex gap-3 text-base">
              <button type="button" className="font-semibold text-cobalt hover:underline" onClick={() => setPicked(new Set(plan.episodes.map((e) => e.ep)))}>
                All
              </button>
              <button type="button" className="font-semibold text-cobalt hover:underline" onClick={() => setPicked(new Set())}>
                None
              </button>
            </span>
          </legend>
          <ul className="m-0 grid list-none gap-1.5 p-0">
            {plan.episodes.map((e) => (
              <li key={e.ep}>
                <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-line px-3 py-2.5 hover:bg-ink/[0.03]">
                  <input type="checkbox" checked={picked.has(e.ep)} onChange={(ev) => toggle(e.ep, ev.target.checked)} className="size-4 shrink-0 accent-cobalt" />
                  <span className="w-11 shrink-0 text-base font-semibold text-ink-soft tabular-nums">Ep {e.ep}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{e.title}</span>
                    <span className="block text-sm text-ink-soft">
                      {e.beats} beats{e.loops ? " · loops" : " · no [loops] marker"}
                      {e.status ? ` · ${e.status}` : ""}
                    </span>
                  </span>
                </label>
              </li>
            ))}
          </ul>
        </fieldset>
      )}

      <div className="grid gap-1.5 text-base text-ink-soft">
        <p className="m-0">
          A <code>TITLE</code> row in the Time column holds each episode&apos;s title; an optional Plan sheet adds the new title, description with hashtags and the
          pinned comment.
        </p>
        <p className="m-0">
          Each Short is held to your rules: the animal moving in the first 2 seconds under a big hook, 22–30 seconds from the real voiceover, a last line that loops
          into the first, and no hashtags in the title. The app records the voiceover, picks the footage and stops at a{" "}
          <b className="font-semibold text-ink">pre-flight report</b> (the checks, Claude&apos;s hook score with stronger first lines, and a storyboard) for you to
          approve before it renders.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-line pt-5">
        <Button
          variant="primary"
          loading={busy === "make"}
          disabled={!plan || !eps.length || busy !== ""}
          onClick={make}
          icon={<ClipboardCheck className="size-4" />}
        >
          {eps.length > 1 ? `Build ${eps.length} pre-flight reports` : "Build the pre-flight report"}
        </Button>
        {!plan && busy === "" && (
          <span className="flex items-center gap-1.5 text-base text-ink-soft">
            <FileSpreadsheet className="size-4" /> Choose a file to see its episodes
          </span>
        )}
      </div>
      <Message {...msg} />
    </div>
  );
}
