"use client";

import { ClipboardCheck, FileSpreadsheet } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type ShortsPlan, type ShortsRules } from "@/lib/api";
import { Button, Field, FileInput, Message } from "./ui";

/** Shorts Mode: upload a content plan, tick episodes, and build each one's pre-flight report to approve and render. */
export function ShortsForm({ onStarted }: { onStarted: (jobId: string, title: string) => void }) {
  const [plan, setPlan] = useState<ShortsPlan | null>(null);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState<"" | "read" | "make">("");
  const [msg, setMsg] = useState<{ text: string; error?: boolean }>({ text: "" });
  const [rules, setRules] = useState<ShortsRules | null>(null);
  useEffect(() => {
    api.shortsRules().then(setRules).catch(() => {}); // without them the checklist just isn't shown
  }, []);

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
      {rules && <Checklist rules={rules} open={!plan} />}
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
          Each Short is held to the checklist above. The app records the voiceover, picks the footage and stops at a{" "}
          <b className="font-semibold text-ink">pre-flight report</b> (the checks, Gemini&apos;s hook score with stronger first lines, and a storyboard) for you to
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

/** Every pre-flight check and what passes it, so a plan can be written to pass before it's uploaded. */
function Checklist({ rules: r, open }: { rules: ShortsRules; open: boolean }) {
  const items: [string, string, React.ReactNode][] = [
    ["script", "hook beat", <>The first voiceover line is <b>spoken by {r.hook_max}s</b>: a few words.</>],
    ["script", "length", <>The whole voiceover runs <b>{r.length_min}–{r.length_max}s</b> as recorded (about {Math.round(r.length_min * 2.6)}–{Math.round(r.length_max * 2.6)} words).</>],
    ["script", "loop line", <>The last line <b>doesn&apos;t end a sentence</b> (end it with “—”, not . ! ?) and runs into the first line as one natural sentence. Put a <code>[loops]</code> marker on it.</>],
    ["script", "title", <><b>No #hashtags</b> in the title (they go in the description).</>],
    ["clips", "hook shot", <>Beat 1&apos;s clip, for its whole stretch: <b>one continuous shot</b> (no cut), the <b>animal itself moving</b> (a pan or zoom alone fails), bright and sharp, no logo, text or intro, and it shows the planned shot ({r.match_pass}/10).</>],
    ["clips", "loop shot", <>Beat 1 is <b>real footage</b>, so the last {r.loop_tail}s can cut back to it.</>],
    ["clips", "shot match", <>Every beat&apos;s clip shows <b>its planned shot</b>: {r.match_pass}/10 or more. A clip without the shot&apos;s key objects scores at most {r.generic_max}, so write a Visual you can find.</>],
    ["clips", "placeholders", <>Every beat finds footage: <b>no placeholder cards</b>. Your own clips (<code>&lt;plan&gt;-epNN/scene-XX.mp4</code>) come first.</>],
    ["clips", "fresh clips", <>No clip <b>another Short used in the last {r.fresh_days} days</b>, and a hook no other Short has used.</>],
    ["ready", "hook judge", <>Gemini scores the hook <b>{r.judge_ready}/10 or more</b> (needs GEMINI_API_KEY in Settings).</>],
  ];
  const groups = [["script", "In the script"], ["clips", "In the footage"], ["ready", "To be ready"]] as const;
  return (
    <details open={open} className="well p-4">
      <summary className="cursor-pointer text-base font-semibold">What each Short must pass</summary>
      <div className="mt-3 grid gap-3">
        {groups.map(([g, label]) => (
          <div key={g} className="grid gap-1.5">
            <div className="field-label">{label}</div>
            <ul className="m-0 grid list-none gap-1.5 p-0">
              {items.filter(([k]) => k === g).map(([, name, text]) => (
                <li key={name} className="grid gap-x-3 text-base sm:grid-cols-[8rem_1fr]">
                  <span className="font-semibold">{name}</span>
                  <span className="text-ink-soft">{text}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
        <p className="m-0 text-sm text-ink-soft">The pre-flight report checks each of these on the real voiceover and footage; change the script and make it again to fix one.</p>
      </div>
    </details>
  );
}
