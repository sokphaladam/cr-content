"use client";

import { AlertTriangle, Wand2 } from "lucide-react";
import { useState } from "react";
import { api, type EditPlan, type VideoScript } from "@/lib/api";
import { clock } from "./Transcript";
import { Button, useToast } from "./ui";

const KIND = { calm: "Calm scene", graphic: "Graphic", sound: "Sound" } as const;

/** The Edit Director (M7): story-aware edits proposed from the beats, each with its reason, and the footage gaps it
 *  won't cover up. Ticked ones are applied as one undoable edit; running it again replaces only its own edits. */
export function EditDirectorPanel({
  script,
  lengths,
  draftId,
  hasDirectorEdits,
  onApply,
  onScene,
}: {
  script: VideoScript;
  lengths: number[];
  draftId: string;
  hasDirectorEdits: boolean; // clips or calm scenes it made earlier are in the draft
  onApply: (plan: EditPlan, picked: Set<string>) => number; // returns how many were skipped (a locked lane)
  onScene: (index: number) => void; // open a scene (by its place among the rendered scenes)
}) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [ai, setAi] = useState(false);
  const [plan, setPlan] = useState<EditPlan | null>(null);
  const [picked, setPicked] = useState<Set<string>>(new Set());

  async function run() {
    setBusy(true);
    try {
      const p = await api.editDirect({ script, lengths, draft: draftId, ai });
      setPlan(p);
      setPicked(new Set(p.decisions.map((d) => d.id)));
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  const apply = (which: Set<string>, done: string) => {
    const skipped = onApply(plan ?? { decisions: [], gaps: [], notes: [], sound_source: "" }, which);
    toast(skipped ? `${done} ${skipped} left out: its lane is locked.` : done, "success");
    setPlan(null);
  };

  return (
    <section aria-label="Edit Director" className="grid gap-2 border-t border-line p-3">
      <h3 className="m-0 text-md font-bold">Edit Director</h3>
      <p className="m-0 text-xs text-ink-soft">
        Turns the story beats into a few edits: calm explanations and a held payoff, graphics only where they clarify,
        sounds on the moments that matter. Your own clips and choices are never changed.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" variant="secondary" loading={busy} icon={<Wand2 className="size-3.5" />} onClick={() => void run()}>
          {hasDirectorEdits ? "Direct the edit again" : "Direct the edit"}
        </Button>
        <label className="flex items-center gap-1.5 text-xs text-ink-soft">
          <input type="checkbox" className="size-3.5 accent-cobalt" checked={ai} onChange={(e) => setAi(e.target.checked)} />
          Ask Gemini for the sounds
        </label>
        {hasDirectorEdits && !plan && (
          <Button size="sm" variant="ghost" onClick={() => apply(new Set(), "The Edit Director's edits were removed (Ctrl+Z brings them back).")}>
            Remove its edits
          </Button>
        )}
      </div>

      {plan && (
        <div className="grid gap-2">
          {plan.gaps.length > 0 && (
            <div role="alert" className="grid gap-1 rounded-lg border border-warn/60 bg-warn/[0.08] p-2 text-sm">
              <span className="flex items-center gap-1.5 font-semibold"><AlertTriangle className="size-4" /> Evidence gaps</span>
              {plan.gaps.map((g) => (
                <button key={g.shot} type="button" onClick={() => onScene(g.scene)} className="cursor-pointer bg-transparent p-0 text-left text-sm text-ink hover:underline">
                  {g.text}
                </button>
              ))}
            </div>
          )}
          {plan.notes.map((n, k) => <p key={k} className="m-0 text-xs text-ink-soft">{n}</p>)}
          {plan.decisions.length === 0 ? (
            <p className="m-0 text-sm text-ink-soft">No edits to propose: nothing in the story needs extra emphasis.</p>
          ) : (
            <ul className="m-0 grid list-none gap-1 p-0">
              {plan.decisions.map((d) => (
                <li key={d.id}>
                  <label className="flex cursor-pointer items-start gap-2 text-sm">
                    <input
                      type="checkbox"
                      className="mt-0.5 size-4 accent-cobalt"
                      checked={picked.has(d.id)}
                      onChange={() => setPicked((p) => (p.has(d.id) ? new Set([...p].filter((x) => x !== d.id)) : new Set([...p, d.id])))}
                    />
                    <span className="grid gap-0.5">
                      <span>
                        <b>{KIND[d.kind]}</b>
                        {d.clip?.start !== undefined && <span className="ml-1 font-mono text-xs text-ink-soft">{clock(d.clip.start)}</span>}
                        <span className="ml-1 text-xs text-ink-soft">
                          scene {d.scene + 1}
                          {d.clip?.template ? ` · ${d.clip.template}` : d.clip?.sound ? ` · ${d.clip.sound}` : ""}
                          {d.essential ? " · essential" : ""}
                        </span>
                      </span>
                      <span className="text-xs text-ink-soft">{d.reason}</span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          )}
          <div className="flex gap-1.5">
            <Button size="sm" variant="primary" onClick={() => apply(picked, `Applied ${picked.size} edit${picked.size === 1 ? "" : "s"}.`)}>
              Apply {picked.size} edit{picked.size === 1 ? "" : "s"}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setPlan(null)}>Close</Button>
          </div>
          <p className="m-0 text-2xs text-ink-soft">Applying replaces its earlier edits (not the ones you changed). Ctrl+Z undoes it.</p>
        </div>
      )}
    </section>
  );
}
