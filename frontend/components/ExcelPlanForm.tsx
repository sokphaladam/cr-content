"use client";

import { Clapperboard, FileSpreadsheet, FilePen } from "lucide-react";
import { useState } from "react";
import { api, type ExcelPlan } from "@/lib/api";
import { Button, Field, Message } from "./ui";

/** Content plan in Excel: upload it, tick episodes, then make drafts to check or render them all in one go. */
export function ExcelPlanForm({
  claude,
  onDrafts,
  onRender,
}: {
  claude: boolean;
  onDrafts: (drafts: { ep: number; id: string; title: string }[]) => void;
  onRender: (jobId: string, title: string) => void;
}) {
  const [plan, setPlan] = useState<ExcelPlan | null>(null);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState<"" | "read" | "drafts" | "render">("");
  const [msg, setMsg] = useState<{ text: string; error?: boolean }>({ text: "" });

  async function read(file: File | undefined) {
    if (!file) return;
    setBusy("read");
    setPlan(null);
    setMsg({ text: "Reading your plan…" });
    try {
      const p = await api.readExcel(file);
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

  async function makeDrafts() {
    if (!plan) return;
    setBusy("drafts");
    setMsg({ text: claude ? "Claude is picking footage searches for every scene…" : "Creating drafts…" });
    try {
      const { drafts } = await api.excelDrafts(plan.file, eps);
      setMsg({ text: "" });
      onDrafts(drafts);
    } catch (err) {
      setMsg({ text: (err as Error).message, error: true });
    } finally {
      setBusy("");
    }
  }

  async function renderAll() {
    if (!plan) return;
    setBusy("render");
    try {
      const { id } = await api.excelRender(plan.file, eps);
      setMsg({ text: "" });
      onRender(id, `${eps.length} episode${eps.length === 1 ? "" : "s"} from ${plan.name}`);
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
    <div className="grid gap-5 rounded-xl border border-line bg-panel p-5 sm:p-6">
      <Field label="Content plan (.xlsx)" hint="a Scripts sheet with Ep | Time | Visual | On-screen Text | Voiceover" htmlFor="excel-file">
        <input
          id="excel-file"
          type="file"
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          disabled={busy !== ""}
          onChange={(e) => {
            void read(e.target.files?.[0]);
            e.target.value = ""; // choosing the same file again (after editing it) reads it again
          }}
          className="field-input h-auto py-2 file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-ink/[0.06] file:px-3 file:py-1.5 file:font-semibold"
        />
      </Field>

      {plan && (
        <fieldset className="m-0 grid gap-2 border-0 p-0">
          <legend className="mb-2 flex w-full items-center justify-between gap-3">
            <span className="field-label">
              {plan.episodes.length} episodes in {plan.name}
            </span>
            <span className="flex gap-3 text-[13px]">
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
                  <span className="w-11 shrink-0 text-[13px] font-semibold text-ink-soft tabular-nums">Ep {e.ep}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{e.title}</span>
                    <span className="block text-[12.5px] text-ink-soft">
                      {e.scenes} scenes{e.status ? ` · ${e.status}` : ""}
                    </span>
                  </span>
                </label>
              </li>
            ))}
          </ul>
        </fieldset>
      )}

      <p className="m-0 text-[13px] text-ink-soft">
        Voiceover is spoken word for word and each Visual becomes a footage search. Sound cues in brackets aren&apos;t read out; a scene that is only a cue becomes a silent
        beat. <b className="font-semibold text-ink">Create drafts</b> to check the footage first, or <b className="font-semibold text-ink">Render</b> them all now (each
        still becomes a draft you can fix and render again). Rows marked Posted start unticked.
      </p>

      <div className="flex flex-wrap items-center gap-2 border-t border-line pt-5">
        <Button
          variant="primary"
          loading={busy === "render"}
          disabled={!plan || !eps.length || busy !== ""}
          onClick={renderAll}
          icon={<Clapperboard className="size-4" />}
        >
          {`Render ${eps.length || ""} video${eps.length === 1 ? "" : "s"}`.replace("  ", " ")}
        </Button>
        <Button loading={busy === "drafts"} disabled={!plan || !eps.length || busy !== ""} onClick={makeDrafts} icon={<FilePen className="size-4" />}>
          Create drafts
        </Button>
        {!plan && busy === "" && (
          <span className="flex items-center gap-1.5 text-[13px] text-ink-soft">
            <FileSpreadsheet className="size-4" /> Choose a file to see its episodes
          </span>
        )}
      </div>
      <Message {...msg} />
    </div>
  );
}
