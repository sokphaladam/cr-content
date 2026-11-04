"use client";

import { Clapperboard, Film, Lock, RefreshCw, Search, Sparkles, Square } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  API_BASE,
  api,
  type DirectorPlan,
  type FootageMatch,
  type PlanFootage,
  type PlanKind,
  type PlanShot,
} from "@/lib/api";
import { Button, Chip, Message } from "./ui";

const words = (v: string) => v.replace(/_/g, " ");
const EVIDENCE: Record<PlanShot["evidence"], string> = {
  exact_action: "must show the exact action",
  subject: "right subject",
  supporting: "supporting footage",
  illustrative: "illustrative",
};
const MATCH: Record<FootageMatch, { label: string; tone: "ink" | "caption" | "neutral" }> = {
  own: { label: "your file", tone: "ink" },
  drawn: { label: "drawn card", tone: "ink" },
  exact: { label: "exact action", tone: "ink" },
  good: { label: "right subject", tone: "ink" },
  subject_only: { label: "subject, not the action", tone: "caption" },
  weak: { label: "doubtful match", tone: "caption" },
  unchecked: { label: "not checked", tone: "neutral" },
};

/** The AI Director's plan for a Script-to-Video project: the story, then every scene's shots, editable and re-plannable. */
export function DirectorPlanPanel({
  kind,
  refId,
  onAssemble,
}: {
  kind: PlanKind;
  refId: string;
  onAssemble?: () => Promise<string[]>; // a Short: the editor loads the plan's footage into its scenes
}) {
  const assembleRef = useRef(onAssemble);
  useEffect(() => {
    assembleRef.current = onAssemble; // the latest one (it reads the editor's current scenes)
  });
  const [plan, setPlan] = useState<DirectorPlan | null>(null);
  const [msg, setMsg] = useState<{ text: string; error?: boolean }>({
    text: "",
  });
  const [busy, setBusy] = useState<string | null>(null); // "all" or the scene id being re-planned
  const [note, setNote] = useState("");
  const [jobId, setJobId] = useState<string | null>(null); // a footage search running for this plan
  const [jobDetail, setJobDetail] = useState("");
  const [mediaFolder, setMediaFolder] = useState("");

  useEffect(() => {
    let live = true;
    api.plan(kind, refId).then(
      (p) => {
        if (!live) return;
        setPlan(p);
        setJobId(p.footage_job ?? null);
        setMediaFolder(p.media_folder ?? "");
      },
      (e) => live && setMsg({ text: (e as Error).message, error: true }),
    );
    return () => {
      live = false;
    };
  }, [kind, refId]);

  const assemble = useCallback(async () => {
    setMsg({ text: "Putting the footage in the video…" });
    try {
      const notes = assembleRef.current ? await assembleRef.current() : (await api.assemblePlan(kind, refId)).notes;
      setMsg({ text: notes.join(" ") || "No shot has footage yet: find footage first." });
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    }
  }, [kind, refId]);

  // follow the footage search; the plan is reloaded when it ends (it saves each shot as it goes)
  useEffect(() => {
    if (!jobId) return;
    const timer = setInterval(async () => {
      try {
        const j = await api.job(jobId);
        setJobDetail(j.detail || (j.status === "queued" ? "waiting to start…" : "searching…"));
        if (j.status === "done" || j.status === "error") {
          setJobId(null);
          setJobDetail("");
          setPlan(await api.plan(kind, refId));
          if (j.status === "error") setMsg({ text: j.error ?? "The footage search failed.", error: true });
          else if (kind === "draft") await assemble(); // the footage goes straight into the video
          else if (kind === "short") setMsg({ text: "The pre-flight report was made again with these shots. Check it, then approve the render." });
          else setMsg({ text: "The storyboard now cuts through the planned shots. Check it, then approve the render." });
        }
      } catch {
        setJobId(null); // the engine restarted: the job is gone, but every shot it finished was saved
        setJobDetail("");
        api.plan(kind, refId).then(setPlan, () => {});
        setMsg({ text: "The footage search was interrupted (the engine restarted). Shots it finished kept their footage: find the missing ones to carry on.", error: true });
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [jobId, kind, refId, assemble]);

  async function findFootage(shots?: string[]) {
    try {
      setJobId((await api.planFootage(kind, refId, shots)).id);
      setJobDetail("starting…");
      setMsg({ text: "" });
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    }
  }

  async function pick(shot: string, index: number) {
    try {
      setPlan(await api.pickFootage(kind, refId, shot, index));
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    }
  }

  async function direct(scenes?: string[]) {
    setBusy(scenes ? scenes[0] : "all");
    setMsg({
      text: scenes
        ? "Re-planning this scene…"
        : "The AI Director is reading the whole script…",
    });
    try {
      const next = await api.directPlan(kind, refId, { scenes, note: note.trim() });
      setPlan(next);
      if (next.footage_job) setJobId(next.footage_job); // footage for the new shots
      setMsg({ text: "" });
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    } finally {
      setBusy(null);
    }
  }

  /** An edited shot is locked, so the AI Director never overwrites it. Saved right away. */
  async function editShot(id: string, patch: Partial<PlanShot>) {
    if (!plan) return;
    const next = {
      ...plan,
      shots: plan.shots.map((s) =>
        s.id === id ? { ...s, ...patch, locked: true } : s,
      ),
    };
    setPlan(next);
    try {
      setPlan(await api.savePlan(kind, refId, next));
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    }
  }

  async function unlock(id: string) {
    if (!plan) return;
    const next = {
      ...plan,
      shots: plan.shots.map((s) => (s.id === id ? { ...s, locked: false } : s)),
    };
    try {
      setPlan(await api.savePlan(kind, refId, next));
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    }
  }

  if (!plan)
    return (
      <div className="p-3">
        <Message text={msg.text || "Loading the plan…"} error={msg.error} />
      </div>
    );
  const { story, continuity } = plan;
  return (
    <div className="grid gap-4 p-3">
      <section className="grid gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Chip tone={plan.planned_by === "ai" ? "ink" : "caption"}>
            {plan.planned_by === "ai"
              ? "Planned by the AI Director"
              : "One shot per scene (not directed yet)"}
          </Chip>
          <Chip>{plan.project.aspect_ratio}</Chip>
          <Chip>{words(plan.project.visual_style)}</Chip>
        </div>
        <input
          className="field-input"
          aria-label="Direction for the AI Director"
          placeholder="Optional direction, e.g. slower, more close-ups"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <Button
          variant="primary"
          size="sm"
          loading={busy === "all"}
          disabled={!!busy || !!jobId}
          icon={<Sparkles className="size-4" />}
          onClick={() => void direct()}
        >
          {plan.planned_by === "ai"
            ? "Direct the whole video again"
            : "Direct with AI"}
        </Button>
        <div className="flex flex-wrap items-center gap-2">
          {jobId ? (
            <>
              <span className="text-sm text-ink-soft" role="status">
                Finding footage: {jobDetail}
              </span>
              <Button size="sm" variant="ghost" icon={<Square className="size-3.5" />} onClick={() => void api.stopPlanFootage(kind, refId)}>
                Stop
              </Button>
            </>
          ) : (
            <Button size="sm" disabled={!!busy} icon={<Film className="size-4" />} onClick={() => void findFootage()}
              title={kind === "short" ? "Search each beat's clip again with these shots and rebuild the pre-flight report (the voice is kept)" : undefined}>
              {kind === "short"
                ? "Find clips again with this plan"
                : plan.shots.some((s) => s.footage) ? "Find footage again" : "Find footage for every shot"}
            </Button>
          )}
          {!jobId && kind !== "short" && plan.shots.some((s) => s.footage) && plan.shots.some((s) => !s.footage && s.shot_type !== "graphic") && (
            <Button size="sm" disabled={!!busy} icon={<Film className="size-4" />} onClick={() => void findFootage(plan.shots.filter((s) => !s.footage).map((s) => s.id))}
              title="Search only the shots that have no footage yet (after a stop or a restart)">
              Find the missing footage
            </Button>
          )}
          {!jobId && kind !== "short" && plan.shots.some((s) => s.footage) && (
            <Button size="sm" variant="primary" disabled={!!busy} icon={<Clapperboard className="size-4" />} onClick={() => void assemble()}
              title="Cut each scene through its planned shots. Footage you chose yourself is kept.">
              Put footage in the video
            </Button>
          )}
        </div>
        {kind === "short" && (
          <p className="m-0 text-xs text-ink-soft">
            Shorts Mode uses one clip per beat, found for its first shot. Swap or trim a beat&apos;s clip on the Pre-flight page.
          </p>
        )}
        {mediaFolder && kind !== "short" && (
          <p className="m-0 text-xs text-ink-soft">
            Your own clips come first: put them in <code>{mediaFolder}</code> named like{" "}
            <code>shot-001-1.mp4</code>, then find footage again.
          </p>
        )}
        {plan.warnings.length > 0 && (
          <ul className="m-0 grid gap-0.5 pl-4 text-sm text-ink">
            {plan.warnings.map((w, i) => (
              <li key={i}>
                {/* a shot id in the warning jumps to that shot, ready to edit */}
                {w.split(/(shot-\d+-\d+)/).map((part, k) =>
                  k % 2 ? (
                    <button
                      key={k}
                      type="button"
                      onClick={() => goToShot(part)}
                      title="Go to this shot"
                      className="cursor-pointer border-0 bg-transparent p-0 font-semibold text-cobalt hover:underline"
                    >
                      {part}
                    </button>
                  ) : (
                    part
                  ),
                )}
              </li>
            ))}
          </ul>
        )}
        <Message {...msg} />
      </section>

      {plan.planned_by === "ai" && (
        <section className="grid gap-1 text-sm">
          {story.hook && (
            <p className="m-0">
              <b>Hook:</b> {story.hook}
            </p>
          )}
          {story.central_idea && (
            <p className="m-0">
              <b>Story:</b> {story.central_idea}
            </p>
          )}
          {story.emotional_arc.length > 0 && (
            <p className="m-0">
              <b>Arc:</b> {story.emotional_arc.join(" → ")}
            </p>
          )}
          {story.payoff && (
            <p className="m-0">
              <b>Payoff:</b> {story.payoff}
            </p>
          )}
          {continuity.subjects.length > 0 && (
            <p className="m-0">
              <b>Subjects:</b> {continuity.subjects.join(", ")}
            </p>
          )}
          {story.key_facts.length > 0 && (
            <p className="m-0">
              <b>Facts the footage must not misrepresent:</b>{" "}
              {story.key_facts.join("; ")}
            </p>
          )}
          {plan.suggestions.length > 0 && (
            <div className="mt-1 rounded-lg border border-line p-2">
              <b>Script suggestions</b> (optional; your narration isn&apos;t
              changed)
              <ul className="m-0 pl-4">
                {plan.suggestions.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      <ol className="m-0 grid list-none gap-3 p-0">
        {plan.scenes.map((scene, i) => {
          const shots = plan.shots.filter((s) => s.scene_id === scene.id);
          return (
            <li
              key={scene.id}
              className="grid gap-2 rounded-lg border border-line p-2.5"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="grid gap-0.5">
                  <span className="text-xs font-semibold text-ink-soft">
                    Scene {i + 1}
                    {scene.purpose && ` · ${scene.purpose}`}
                    {scene.emotion && ` · ${scene.emotion}`}
                  </span>
                  <span
                    lang={plan.project.language}
                    className="text-sm text-ink"
                  >
                    “{scene.narration}”
                  </span>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  loading={busy === scene.id}
                  disabled={!!busy || !!jobId}
                  icon={<RefreshCw className="size-3.5" />}
                  onClick={() => void direct([scene.id])}
                  title="Re-plan this scene's shots (edited shots are kept)"
                >
                  Re-plan
                </Button>
              </div>
              {shots.map((shot) => (
                <ShotRow
                  id={`plan-${shot.id}`}
                  // remount when the saved shot changes (a re-plan), so the inputs show it
                  key={`${shot.id}:${shot.visual_description}:${shot.duration_seconds}`}
                  shot={shot}
                  onEdit={(p) => void editShot(shot.id, p)}
                  onUnlock={() => void unlock(shot.id)}
                  onPick={(i) => void pick(shot.id, i)}
                  onSearch={jobId || kind === "short" ? undefined : () => void findFootage([shot.id])}
                />
              ))}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/** Scroll to a shot and put the cursor in what it shows, so it can be changed right away. */
function goToShot(id: string) {
  const row = document.getElementById(`plan-${id}`);
  if (!row) return;
  row.scrollIntoView({ behavior: "smooth", block: "center" });
  row.querySelector("textarea")?.focus({ preventScroll: true });
}

function ShotRow({
  id,
  shot,
  onEdit,
  onUnlock,
  onPick,
  onSearch,
}: {
  id: string;
  shot: PlanShot;
  onEdit: (p: Partial<PlanShot>) => void;
  onUnlock: () => void;
  onPick: (index: number) => void;
  onSearch?: () => void; // absent while a search runs
}) {
  const [desc, setDesc] = useState(shot.visual_description);
  const [secs, setSecs] = useState(String(shot.duration_seconds));
  return (
    <div id={id} className="grid scroll-mt-4 gap-1.5 rounded-md bg-ink/[0.03] p-2 text-sm">
      <div className="flex flex-wrap items-center gap-1.5">
        <Chip tone="ink">{words(shot.shot_type)}</Chip>
        <span className="text-xs text-ink-soft">
          {words(shot.camera.angle)} · {words(shot.camera.movement)} ·{" "}
          {shot.camera.framing}
        </span>
        <span
          className={`text-xs ${shot.evidence === "exact_action" ? "font-semibold text-ink" : "text-ink-soft"}`}
        >
          · {EVIDENCE[shot.evidence]}
        </span>
        {shot.locked && (
          <button
            type="button"
            onClick={onUnlock}
            title="Edited by you: the AI Director keeps it. Click to let it re-plan."
            className="ml-auto flex cursor-pointer items-center gap-1 border-0 bg-transparent text-xs text-ink-soft hover:text-ink"
          >
            <Lock className="size-3" /> kept
          </button>
        )}
      </div>
      {shot.purpose && (
        <span className="text-xs text-ink-soft">{shot.purpose}</span>
      )}
      <textarea
        aria-label={`What ${shot.id} shows`}
        rows={2}
        className="field-input resize-y text-sm"
        value={desc}
        onChange={(e) => setDesc(e.target.value)}
        onBlur={() =>
          desc !== shot.visual_description &&
          onEdit({ visual_description: desc })
        }
      />
      <div className="flex flex-wrap items-center gap-2 text-xs text-ink-soft">
        <label className="flex items-center gap-1">
          <input
            type="number"
            min={0}
            step={0.1}
            aria-label={`Length of ${shot.id} in seconds`}
            className="field-input h-7 w-16 px-1.5 py-0 text-xs"
            value={secs}
            onChange={(e) => setSecs(e.target.value)}
            onBlur={() => {
              const n = Number(secs);
              if (Number.isFinite(n) && n >= 0 && n !== shot.duration_seconds)
                onEdit({ duration_seconds: n });
              else setSecs(String(shot.duration_seconds));
            }}
          />
          s
        </label>
        {shot.footage_queries.length > 0 && (
          <span>Searches: {shot.footage_queries.join(" · ")}</span>
        )}
      </div>
      {shot.factual_requirements.length > 0 && (
        <span className="text-xs text-ink-soft">
          Must: {shot.factual_requirements.join("; ")}
        </span>
      )}
      <FootageView shot={shot} onPick={onPick} onSearch={onSearch} />
    </div>
  );
}

function Thumb({ f, className = "" }: { f: PlanFootage; className?: string }) {
  if (!f.thumb)
    return (
      <span className={`grid place-items-center rounded bg-ink/[0.08] text-2xs text-ink-soft ${className}`}>
        {f.source === "own" ? "your file" : f.kind}
      </span>
    );
  const src = f.thumb.startsWith("/media/") ? `${API_BASE}${f.thumb}` : f.thumb; // a Shorts Mode beat's own thumbnail
  // eslint-disable-next-line @next/next/no-img-element -- remote stock thumbnails from any library
  return <img src={src} alt="" loading="lazy" className={`rounded object-cover ${className}`} />;
}

/** The shot's footage: what was picked, how well it matches, where it's from, its problems, and the alternatives. */
function FootageView({ shot, onPick, onSearch }: { shot: PlanShot; onPick: (i: number) => void; onSearch?: () => void }) {
  const f = shot.footage;
  const scores = f
    ? [
        f.subject_score !== null && `subject ${f.subject_score}/10`,
        f.action_score !== null && `action ${f.action_score}/10`,
        f.quality_score !== null && `quality ${f.quality_score}/10`,
      ]
        .filter(Boolean)
        .join(" · ")
    : "";
  return (
    <div className="grid gap-1.5 border-t border-line pt-1.5">
      <div className="flex items-start gap-2">
        {f && <Thumb f={f} className="h-16 w-12 shrink-0" />}
        <div className="grid min-w-0 flex-1 gap-0.5 text-xs">
          {f ? (
            <>
              <span className="flex flex-wrap items-center gap-1">
                <Chip tone={MATCH[f.match].tone}>{MATCH[f.match].label}</Chip>
                <span className="text-ink-soft">
                  {f.kind} · {f.source}
                  {f.duration ? ` · ${f.duration.toFixed(0)} s` : ""}
                </span>
              </span>
              {scores && <span className="text-ink-soft">{scores}</span>}
              {f.problem && <span className="text-ink">Gemini: {f.problem}</span>}
              {f.source !== "own" && (
                <span className="truncate text-ink-soft">
                  {f.author && `${f.author} · `}
                  {f.licence_url ? (
                    <a href={f.licence_url} target="_blank" rel="noreferrer" className="underline">
                      {f.licence}
                    </a>
                  ) : (
                    f.licence
                  )}
                  {f.page && (
                    <>
                      {" · "}
                      <a href={f.page} target="_blank" rel="noreferrer" className="underline">
                        source
                      </a>
                    </>
                  )}
                </span>
              )}
            </>
          ) : (
            <span className="text-ink-soft">
              {shot.shot_type === "graphic" ? "A graphic: drawn by the app, no footage needed." : "No footage yet."}
            </span>
          )}
        </div>
        {onSearch && shot.shot_type !== "graphic" && (
          <Button size="sm" variant="ghost" icon={<Search className="size-3.5" />} onClick={onSearch} title="Search this shot's footage again">
            Search
          </Button>
        )}
      </div>
      {shot.warnings.length > 0 && (
        <ul className="m-0 grid gap-0.5 pl-4 text-xs text-ink">
          {shot.warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
      {shot.candidates.length > 0 && (
        <div className="flex flex-wrap gap-1.5" aria-label="Alternatives">
          {shot.candidates.map((c, i) => (
            <button
              key={i}
              type="button"
              onClick={() => onPick(i)}
              aria-label={`Use alternative ${i + 1}: ${c.kind} from ${c.source}`}
              title={`Use this instead: ${c.kind} from ${c.source}${c.subject_score !== null ? `, subject ${c.subject_score}/10` : ", not checked yet"}${c.problem ? ` (${c.problem})` : ""}`}
              className="cursor-pointer rounded border border-line bg-transparent p-0 hover:border-cobalt"
            >
              <Thumb f={c} className="h-12 w-9" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
