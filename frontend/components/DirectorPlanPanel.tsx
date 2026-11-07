"use client";

import { Clapperboard, Film, Lock, RefreshCw, Search, Sparkles, Square } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  API_BASE,
  api,
  type ChannelAnalytics,
  type DirectorPlan,
  type FootageMatch,
  type PlanFootage,
  type PlanKind,
  type PlanShot,
  type ReconstructionBrief,
  type ResearchBrief,
} from "@/lib/api";
import { Button, Chip, FileInput, Message } from "./ui";

const words = (v: string) => v.replace(/_/g, " ");
const EVIDENCE: Record<PlanShot["evidence"], string> = {
  exact_action: "must show the exact action",
  subject: "right subject",
  supporting: "supporting footage",
  illustrative: "illustrative",
};
// what a history shot is (director_plan.VISUAL_ORIGINS): real material, or something that must not pass for it
const ORIGIN: Record<string, string> = {
  archive: "archive", evidence: "evidence", context: "context only", graphic: "graphic", reconstruction: "reconstruction",
};
const CLAIM_TONE: Record<string, string> = { supported: "text-ok", disputed: "text-warn", uncertain: "text-warn", unsupported: "text-danger" };

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
  onPlan,
}: {
  kind: PlanKind;
  refId: string;
  onAssemble?: () => Promise<string[]>; // a Short: the editor loads the plan's footage into its scenes
  onPlan?: (plan: DirectorPlan) => void; // every plan it loads or saves (the pre-render check follows it)
}) {
  const assembleRef = useRef(onAssemble);
  useEffect(() => {
    assembleRef.current = onAssemble; // the latest one (it reads the editor's current scenes)
  });
  const [plan, setPlan] = useState<DirectorPlan | null>(null);
  const onPlanRef = useRef(onPlan);
  useEffect(() => {
    onPlanRef.current = onPlan;
  });
  useEffect(() => {
    if (plan) onPlanRef.current?.(plan);
  }, [plan]);
  const [msg, setMsg] = useState<{ text: string; error?: boolean }>({
    text: "",
  });
  // a history project's research: each scene shows the claims it states and their sources
  const [research, setResearch] = useState<ResearchBrief | null>(null);
  const researchRev = plan?.story.research_revision ?? 0;
  useEffect(() => {
    if (kind !== "draft" && kind !== "long") return;
    api.research(kind, refId).then((r) => setResearch(r.brief), () => setResearch(null));
  }, [kind, refId, researchRev]);
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
  const history = plan.project.channel_profile_id === "hidden_history_files" || plan.project.visual_style === "cinematic_history";
  const claims = Object.fromEntries((research?.claims ?? []).map((c) => [c.id, c]));
  const sources = Object.fromEntries((research?.sources ?? []).map((x) => [x.id, x]));
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
          {plan.project.channel_profile_id && <Chip tone="ink">Channel: {words(plan.project.channel_profile_id)}</Chip>}
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
          {(story.loops ?? []).length > 0 && (
            <p className="m-0">
              <b>Open questions:</b>{" "}
              {(story.loops ?? []).map((l) => `${l.question}${l.left_open ? " (left open)" : ""}`).join("; ")}
            </p>
          )}
          {(plan.story_warnings ?? []).length > 0 && (
            <div className="mt-1 rounded-lg border border-line p-2">
              <b>Story checks</b> (rule-based; your narration isn&apos;t changed)
              <ul className="m-0 pl-4">
                {(plan.story_warnings ?? []).map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
          {plan.evidence && <p className="m-0 text-xs text-ink-soft">{plan.evidence}</p>}
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

      {!history && <ChannelNumbers /> /* the wildlife channel's numbers: history direction never uses them */}
      {history && research?.research_status !== "approved" && (
        <p className="m-0 text-xs text-warn">
          The research isn&apos;t approved yet, so the Director plans without checked facts. Approve it in the Research tab, then direct again.
        </p>
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
                  {scene.phase && (
                    <span className="text-xs text-ink-soft">
                      <b className="capitalize">{scene.phase}</b>
                      {scene.beat_role && ` · ${scene.beat_role.replace(/_/g, " ")}`}
                      {scene.tension != null && ` · tension ${scene.tension}`}
                      {scene.viewer_question && ` · “${scene.viewer_question}”`}
                    </span>
                  )}
                  <span
                    lang={plan.project.language}
                    className="text-sm text-ink"
                  >
                    “{scene.narration}”
                  </span>
                  {history && (scene.claim_ids ?? []).map((cid) => {
                    const c = claims[cid];
                    if (!c) return null;
                    return (
                      <span key={cid} className="text-xs">
                        <b className={CLAIM_TONE[c.status]}>{c.status}</b> {c.claim_text}
                        {c.source_ids.map((sid) => sources[sid] && (
                          <a key={sid} href={sources[sid].url} target="_blank" rel="noreferrer" className="ml-1 text-ink-soft underline">
                            {sources[sid].publisher || sources[sid].title}
                          </a>
                        ))}
                      </span>
                    );
                  })}
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
                  rebuild={shot.visual_origin === "reconstruction" && kind !== "short" ? { kind, refId, onPlan: setPlan } : undefined}
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
  rebuild,
}: {
  id: string;
  shot: PlanShot;
  rebuild?: { kind: PlanKind; refId: string; onPlan: (p: DirectorPlan) => void }; // a history reconstruction shot
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
        {shot.visual_origin && (
          <Chip tone={shot.visual_origin === "reconstruction" || shot.visual_origin === "context" ? "caption" : "neutral"}>
            {ORIGIN[shot.visual_origin]}
          </Chip>
        )}
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
      {rebuild && <ReconstructionBox shot={shot} {...rebuild} />}
      <FootageView shot={shot} onPick={onPick} onSearch={onSearch} />
    </div>
  );
}

/** A reconstruction shot (H6): what the research lets it show, the prompt (editable), and draw / redraw / reject.
 *  Drawn pictures carry an "AI RECONSTRUCTION" label; earlier drawings stay as alternatives. */
function ReconstructionBox({ shot, kind, refId, onPlan }: { shot: PlanShot; kind: PlanKind; refId: string; onPlan: (p: DirectorPlan) => void }) {
  const [open, setOpen] = useState(false);
  const [info, setInfo] = useState<{ brief: ReconstructionBrief; installed: boolean } | null>(null);
  const [prompt, setPrompt] = useState("");
  const [job, setJob] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ text: string; error?: boolean }>({ text: "" });
  const drawn = shot.footage?.asset_type === "reconstruction";

  async function show() {
    setOpen(true);
    try {
      const r = await api.reconstruction(kind, refId, shot.id);
      setInfo(r);
      setPrompt(r.brief.prompt);
      setMsg({ text: "" });
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    }
  }

  async function draw() {
    try {
      setJob((await api.drawReconstruction(kind, refId, shot.id, prompt)).id);
      setMsg({ text: "Drawing on this computer… (the first time downloads the model)" });
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    }
  }

  async function reject() {
    try {
      onPlan(await api.rejectReconstruction(kind, refId, shot.id));
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    }
  }

  useEffect(() => {
    if (!job) return;
    const timer = setInterval(async () => {
      try {
        const j = await api.job(job);
        if (j.status !== "done" && j.status !== "error") return;
        setJob(null);
        setMsg(j.status === "error" ? { text: j.error ?? "Drawing failed.", error: true } : { text: "" });
        onPlan(await api.plan(kind, refId));
      } catch {
        setJob(null);
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [job, kind, refId, onPlan]);

  const b = info?.brief;
  return (
    <div className="grid gap-1.5 rounded border border-line p-2 text-xs">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="font-semibold">AI reconstruction</span>
        <span className="text-ink-soft">labelled on screen · drawn only from approved research</span>
        {!open && (
          <Button size="sm" variant="ghost" className="ml-auto" onClick={() => void show()}>
            {drawn ? "Redraw / review" : "Plan the reconstruction"}
          </Button>
        )}
      </div>
      {open && b && (
        <>
          <span className="text-ink-soft">
            {b.kind} · {[b.period, b.location, b.framing, b.aspect].filter(Boolean).join(" · ")}
          </span>
          {b.verified.length > 0 && <span>Verified: {b.verified.join("; ")}</span>}
          {b.uncertain.length > 0 && <span className="text-warn">Not shown as certain: {b.uncertain.join("; ")}</span>}
          <span className="text-ink-soft">Never invented: {b.must_not_invent.join(", ")}</span>
          <label className="grid gap-0.5">
            <span className="text-ink-soft">What to draw (edit freely; keep to the verified facts)</span>
            <textarea rows={2} className="field-input resize-y text-xs" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          </label>
          <div className="flex flex-wrap items-center gap-1.5">
            <Button size="sm" loading={!!job} disabled={!info?.installed || !!job || !prompt.trim()} onClick={() => void draw()}
              title={info?.installed ? "Draw with the free local generator (SDXL)" : "The local image generator isn't installed"}>
              {drawn ? "Draw again" : "Draw"}
            </Button>
            {drawn && (
              <Button size="sm" variant="ghost" disabled={!!job} onClick={() => void reject()} title="Take it out of the video (kept as an alternative)">
                Reject
              </Button>
            )}
            {!info?.installed && (
              <span className="text-ink-soft">No local generator: add your own picture named {shot.id}.jpg to the media folder, then search the shot.</span>
            )}
          </div>
        </>
      )}
      <Message text={msg.text} error={msg.error} />
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
  // a Shorts Mode beat's own thumbnail, or a drawn card
  const src = /^\/(media|cache)\//.test(f.thumb) ? `${API_BASE}${f.thumb}` : f.thumb;
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
                {f.rights === "rights_unknown" && <Chip tone="caption">rights unknown</Chip>}
                {f.depicts === "actual" && <Chip tone="ink">the real subject</Chip>}
                {f.asset_type === "reconstruction" ? <Chip tone="caption">AI reconstruction</Chip> : f.depicts === "illustrative" && <Chip>illustrative</Chip>}
                <span className="text-ink-soft">
                  {f.kind} · {f.asset_type ? `${f.asset_type} · ` : ""}{f.source}
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

const DIMS: { key: "hook_style" | "length" | "animal"; label: string }[] = [
  { key: "hook_style", label: "Hook style" },
  { key: "length", label: "Length" },
  { key: "animal", label: "Subject" },
];

/** The YouTube Studio numbers the AI Director is given, and where to import them. */
function ChannelNumbers() {
  const [data, setData] = useState<ChannelAnalytics | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ text: string; error?: boolean }>({ text: "" });

  useEffect(() => {
    api.analytics().then(setData, () => setData({ imported: null }));
  }, []);

  async function upload(file: File) {
    setBusy(true);
    setMsg({ text: "" });
    try {
      const d = await api.importAnalytics(file);
      setData(d);
      setMsg({ text: d.evidence ? "Imported. The next time you direct a video, the AI Director gets these numbers." : `Imported, but no tag has ${d.min_videos} videos yet, so the AI Director isn't given them.` });
    } catch (e) {
      setMsg({ text: (e as Error).message, error: true });
    } finally {
      setBusy(false);
    }
  }

  const pct = (x: number | null) => (x === null ? "–" : `${x.toFixed(0)}%`);
  return (
    <details className="grid gap-2 rounded-lg border border-line p-2 text-sm">
      <summary className="cursor-pointer font-semibold">
        Your channel&apos;s numbers{" "}
        <span className="font-normal text-ink-soft">
          {data?.imported ? `${data.videos} videos, imported ${data.imported.slice(0, 10)}` : "not imported"}
        </span>
      </summary>
      <p className="m-0 text-xs text-ink-soft">
        From YouTube Studio: Analytics → Advanced mode → Content → Export (the .zip or its .csv). The AI Director reads them
        as evidence about your channel, not as rules, and only tags with {data?.min_videos ?? 3}+ videos. It never uses them
        to suggest a misleading hook.
      </p>
      {data?.summary &&
        DIMS.map(({ key, label }) =>
          data.summary![key].length ? (
            <table key={key} className="w-full text-xs tabular-nums">
              <thead>
                <tr className="text-left text-ink-soft">
                  <th className="font-semibold">{label}</th>
                  <th className="text-right font-normal">videos</th>
                  <th className="text-right font-normal">stayed</th>
                  <th className="text-right font-normal">viewed</th>
                </tr>
              </thead>
              <tbody>
                {data.summary![key].map((r) => (
                  <tr key={r.tag} className={r.videos < (data.min_videos ?? 3) ? "text-ink-soft" : ""}>
                    <td>{r.tag}</td>
                    <td className="text-right">{r.videos}</td>
                    <td className="text-right">{pct(r.stayed)}</td>
                    <td className="text-right">{pct(r.viewed)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null,
        )}
      <FileInput id="analytics-csv" accept=".csv,.zip" file="" disabled={busy} onFile={(f) => void upload(f)} onReject={(t) => setMsg({ text: t, error: true })} />
      <Message {...msg} />
    </details>
  );
}
