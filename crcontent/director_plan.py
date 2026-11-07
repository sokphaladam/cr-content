"""Director Plan: the versioned production plan saved with every Script-to-Video project (AI-DIRECTOR.md section 7).

A Short keeps it inside its draft (drafts/<id>/draft.json, "plan"); a Long Video writes <job>/plan.json.
It is seeded straight from the script: one scene per narration block, one shot per scene, the user's voiceover kept
word for word, durations estimated from the word count (planned_by="script"). The AI Director (ai_director.py) then
fills story, continuity and multi-shot scenes on top of this same schema (planned_by="ai"), shot_footage.py finds
footage per shot, and plan_render.py puts it into the existing Shorts and Long Video renders.
"""
import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator

VERSION = 2  # 2: story phases, beat roles and open loops (attention roadmap M1); v1 plans load with them empty
ASPECTS = {"short": "9:16", "long": "16:9"}
STYLES = ("cinematic_documentary", "cinematic_wildlife", "educational", "storytelling", "cinematic_history")
KHMER = re.compile(r"[ក-៿]")
SHOT_TYPES = ("extreme_wide", "wide", "medium", "close_up", "extreme_close_up", "tracking", "establishing",
              "reaction", "cutaway", "montage", "graphic")
ANGLES = ("eye_level", "low", "high", "overhead", "ground_level", "aerial")
MOVEMENTS = ("static", "slow_push_in", "pull_out", "pan_left", "pan_right", "tilt_up", "tilt_down", "tracking",
             "aerial", "handheld", "slow_motion")
FRAMINGS = ("tight", "medium", "loose")
TRANSITIONS = ("hard_cut", "match_cut", "cross_dissolve", "dip_to_black", "whip", "j_cut", "l_cut")
# how closely footage must match the narration (milestone 3 searches and scores by it)
EVIDENCE = ("exact_action", "subject", "supporting", "illustrative")
# what a history shot is (Hidden History Files spec 6.2, H3): real archive material, place/period context, the
# evidence itself (artifact, document, site), an explanatory graphic or map, or an AI reconstruction; "" = not set
VISUAL_ORIGINS = ("archive", "context", "evidence", "graphic", "reconstruction")
# Setup -> Tension -> Payoff, and what a beat does inside its phase (roadmap section 4); "" = not planned yet
PHASES = ("setup", "tension", "payoff")
BEAT_ROLES = ("pattern_interrupt", "curiosity_gap", "context", "stakes", "evidence", "escalation", "complication",
              "contrast", "relief", "mini_payoff", "delayed_reveal", "final_payoff", "explanation", "callback")


class Camera(BaseModel):
    angle: str = "eye_level"
    movement: str = "static"
    framing: str = "medium"


MATCHES = ("own", "drawn", "exact", "good", "subject_only", "weak", "unchecked")
ASSET_TYPES = ("own", "graphic", "archival", "museum", "photograph", "stock", "reconstruction")


class Footage(BaseModel):
    """A clip or photo for a shot, with where it came from and how well it matches (shot_footage.py)."""
    source: str                 # "own", "pexels", "pixabay", "commons", "inaturalist", "archive", ...
    kind: Literal["video", "photo"]
    file: str = ""              # downloaded file ("" for an alternative not downloaded yet)
    thumb: str = ""
    page: str = ""
    author: str = ""
    licence: str = ""
    licence_url: str = ""
    query: str = ""             # the search that found it
    width: int = 0
    height: int = 0
    duration: float = 0
    subject_score: int | None = None  # Gemini's 0-10 look at it (None: not checked)
    action_score: int | None = None   # only for shots that must show an exact action
    quality_score: int | None = None
    problem: str = ""
    match: Literal["own", "drawn", "exact", "good", "subject_only", "weak", "unchecked"] = "unchecked"
    raw: dict = {}              # the search result, to download it later
    # provenance (Hidden History Files spec 7.3, H4); "" on footage found before H4
    asset_type: str = ""        # ASSET_TYPES: what kind of material it is, from its source
    depicts: Literal["", "actual", "illustrative", "unknown"] = ""  # the real subject, or a stand-in for it
    rights: Literal["", "licensed", "rights_unknown"] = ""          # a licence is stated, or it must be checked
    period_score: int | None = None  # history: Gemini's 0-10 on the period (modern objects in an 802 AD shot: low)
    rights_note: str = ""       # the creator confirmed rights_unknown material: what they checked (H7)


class Shot(BaseModel):
    id: str
    scene_id: str
    purpose: str = ""
    shot_type: str = "medium"
    subject: str = ""
    action: str = ""
    visual_description: str = ""
    camera: Camera = Field(default_factory=Camera)
    lighting: str = ""
    duration_seconds: float = Field(default=0, ge=0)
    narration_reference: str = ""
    footage_queries: list[str] = []
    sound_design: list[str] = []
    transition_out: str = "hard_cut"
    visual_priority: Literal["low", "normal", "high"] = "normal"
    factual_requirements: list[str] = []
    alternatives: list[str] = []
    evidence: str = "subject"
    visual_origin: str = ""  # one of VISUAL_ORIGINS (history projects); "" = not set
    locked: bool = False  # the user edited it or picked its footage: the AI Director and footage search leave it alone
    footage: Footage | None = None
    candidates: list[Footage] = []  # alternatives to swap to, best first
    warnings: list[str] = []        # what's wrong with its footage, in plain words


class Scene(BaseModel):
    id: str
    narration: str = ""  # the user's voiceover, never rewritten
    on_screen_text: str = ""
    visual_notes: str = ""
    purpose: str = ""
    viewer_objective: str = ""
    emotion: str = ""
    transition_out: str = "hard_cut"
    phase: Literal["", "setup", "tension", "payoff"] = ""
    beat_role: str = ""          # one of BEAT_ROLES ("" = none)
    viewer_question: str = ""    # the question in the viewer's mind during this beat
    opens: list[str] = []        # loop ids (Story.loops) this beat raises
    resolves: list[str] = []     # loop ids this beat answers
    tension: int | None = Field(default=None, ge=0, le=100)  # relative anticipation; editorial guidance, not a measurement
    claim_ids: list[str] = []    # research claims (history/models.py) this scene's narration states


class Loop(BaseModel):
    """A question or promise the video raises and must answer (or deliberately leave open)."""
    id: str
    question: str = ""
    left_open: bool = False      # intentionally unresolved (a natural loop or cliffhanger the creator wants)


class Project(BaseModel):
    title: str = ""
    format: Literal["short", "long"]
    aspect_ratio: str = ""
    language: str = "en"
    visual_style: str = STYLES[0]
    target_seconds: float = 0  # the length the creator aims for (0 = none); the narration is never cut to fit
    channel_profile_id: str = ""     # profiles.PROFILES key; "" = the general defaults (every pre-profile project)
    channel_profile_version: int = 0

    @model_validator(mode="after")
    def _aspect(self):
        self.aspect_ratio = ASPECTS[self.format]  # the format decides it; a stale value can't disagree
        return self


class Story(BaseModel):
    hook: str = ""
    central_idea: str = ""
    emotional_arc: list[str] = []
    payoff: str = ""
    audience: str = ""
    key_facts: list[str] = []  # claims in the narration the footage must not misrepresent
    loops: list[Loop] = []     # open loops, opened and resolved by Scene.opens / Scene.resolves
    research_revision: int = 0  # the approved research brief revision linked into the plan (0 = none)


class Continuity(BaseModel):
    subjects: list[str] = []
    locations: list[str] = []
    lighting: list[str] = []
    visual_style: str = ""


class EditPlan(BaseModel):
    music_mood: str = ""
    sound_effects: list[str] = []
    colour_grade: str = ""
    pacing: Literal["slow", "normal", "fast"] = "normal"


class DirectorPlan(BaseModel):
    version: int = VERSION
    planned_by: Literal["script", "ai"] = "script"
    project: Project
    story: Story = Field(default_factory=Story)
    continuity: Continuity = Field(default_factory=Continuity)
    scenes: list[Scene] = []
    shots: list[Shot] = []
    edit_plan: EditPlan = Field(default_factory=EditPlan)
    suggestions: list[str] = []  # optional script improvements; the narration itself is never changed
    warnings: list[str] = []     # whole-video footage problems (repeated shot sizes, too many photos)
    story_warnings: list[str] = []  # story-structure problems (story_check), recomputed on every direct/save
    evidence: str = ""           # the channel analytics the AI Director was given ("" = none)

    @model_validator(mode="before")
    @classmethod
    def _migrate(cls, data):
        return migrate(data) if isinstance(data, dict) else data  # every load (draft.json, plan.json) upgrades old plans

    @model_validator(mode="after")
    def _ids(self):
        scene_ids = [s.id for s in self.scenes]
        if len(set(scene_ids)) != len(scene_ids):
            raise ValueError("scene ids must be unique")
        shot_ids = [s.id for s in self.shots]
        if len(set(shot_ids)) != len(shot_ids):
            raise ValueError("shot ids must be unique")
        unknown = {s.scene_id for s in self.shots} - set(scene_ids)
        if unknown:
            raise ValueError(f"shots point at unknown scenes: {', '.join(sorted(unknown))}")
        return self


def migrate(data: dict) -> dict:
    """Bring a stored plan up to VERSION. v1 -> v2 only adds story fields, which default to empty."""
    version = int(data.get("version", VERSION))
    if version > VERSION:
        raise ValueError(f"This plan was made by a newer version of the app (plan v{version}). Update the app to open it.")
    return {**data, "version": VERSION}


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w{4,}", text.lower()))


def story_findings(plan: DirectorPlan) -> list[dict]:
    """Deterministic Setup/Tension/Payoff checks on an AI-directed plan (roadmap 5.2, M1-M2). Each finding:
    {key, scene (plan scene id or ""), title (with its evidence), fix}. Nothing is changed. A script-seeded plan has
    no beats to check yet."""
    if plan.planned_by != "ai" or not plan.scenes:
        return []
    out, scenes = [], plan.scenes

    def add(key, scene, title, fix):
        out.append({"key": key, "scene": scene, "title": title, "fix": fix})

    unplanned = [s.id for s in scenes if not s.phase]
    if len(unplanned) == len(scenes):
        add("unplanned", "", "No story phases planned yet: re-plan the whole video to get Setup / Tension / Payoff beats.",
            "Run the AI Director on the whole video.")
        return out
    if unplanned:
        add("unplanned", unplanned[0], f"{len(unplanned)} scene(s) have no story phase (first: {unplanned[0]}).",
            "Re-plan those scenes so every beat has a job.")
    first = scenes[0]
    if first.phase and first.phase != "setup":
        add("opening", first.id, f"The video opens in its {first.phase} ({first.id}): the viewer gets no reason to watch first.",
            "Open on the most surprising image or claim, and raise the question the video answers.")
    elif first.phase == "setup" and not first.viewer_question and not first.opens:
        add("opening", first.id, f"The opening ({first.id}) raises no question or promise: give the viewer a reason to stay.",
            "Start with a specific question or promise the video pays off, e.g. the result before the how.")
    order = {p: i for i, p in enumerate(PHASES)}
    for a, b in zip(scenes, scenes[1:]):
        if a.phase and b.phase and order[b.phase] < order[a.phase] and not (a.phase == "payoff" and b.beat_role == "callback"):
            add("order", b.id, f"{b.id} goes back to {b.phase} after the {a.phase} ({a.id}): check the story order.",
                f"Move this beat before {a.id}, or make it a callback that closes the story.")
    if not any(s.phase == "payoff" for s in scenes):
        add("payoff", scenes[-1].id, "No payoff beat: the video never delivers what its opening promises.",
            "End on the answer or result the opening set up.")
    loops = {l.id: l for l in plan.story.loops}
    opened, resolved = {}, {}
    for s in scenes:
        for lid in s.opens:
            if lid not in loops:
                add("loop", s.id, f"{s.id} opens an unknown question '{lid}'.", "Re-plan this scene.")
            opened.setdefault(lid, s.id)
        for lid in s.resolves:
            if lid not in loops:
                add("loop", s.id, f"{s.id} answers an unknown question '{lid}'.", "Re-plan this scene.")
            elif lid not in opened:
                add("loop", s.id, f"{s.id} answers '{loops[lid].question or lid}' before any scene asks it.",
                    "Raise the question earlier, or move this answer later.")
            resolved.setdefault(lid, s.id)
    for lid, loop in loops.items():
        if lid not in opened:
            add("loop", "", f"The question '{loop.question or lid}' is never raised by a scene.",
                "Re-plan the whole video so the question is asked where it belongs.")
        elif lid not in resolved and not loop.left_open:
            add("unresolved", opened[lid], f"The question '{loop.question or lid}' ({opened[lid]}) is never answered.",
                "Answer it before the end, or cut the line that raises it, so the viewer isn't left hanging.")
    payoff = [s for s in scenes if s.phase == "payoff"]
    if loops and payoff and not any(s.resolves for s in payoff):
        add("payoff_mismatch", payoff[0].id,
            f"The payoff ({payoff[0].id}) answers none of the video's questions: it may feel unearned.",
            "Make the ending answer the opening question directly.")
    tension = [s for s in scenes if s.phase == "tension"]
    if tension and not any(s.beat_role in ("stakes", "escalation", "complication", "evidence") for s in tension):
        add("stakes", tension[0].id, "The tension beats add no stakes, evidence or escalation: say why the question matters.",
            "Add what's at stake or a new piece of evidence before the payoff.")
    for a, b in zip(scenes, scenes[1:]):  # shortcut: word overlap, not meaning; the AI story review catches paraphrases
        wa, wb = _words(a.narration), _words(b.narration)
        if len(wa) >= 4 and len(wb) >= 4 and len(wa & wb) / len(wa | wb) > 0.6:
            add("repeat", b.id, f"{b.id} repeats what {a.id} already said: cut it or add something new.",
                "Cut the repeat, or use the line for a new detail that moves the story on.")
    return out


def story_check(plan: DirectorPlan) -> list[str]:
    """The story findings as plain-words warnings (plan.story_warnings)."""
    return [f["title"] for f in story_findings(plan)]


def load(data: dict) -> DirectorPlan:
    return DirectorPlan.model_validate(data)


def spoken_seconds(text: str) -> float:
    """Rough voiceover length. Khmer has no spaces between words, so count its letters instead."""
    if KHMER.search(text):
        return round(len(KHMER.findall(text)) / 12, 1)
    return round(len(text.split()) / 2.6, 1)


def from_scenes(title: str, fmt: str, lang: str, style: str, scenes: list[dict]) -> DirectorPlan:
    """Seed a plan from script scenes ({"narration", "visual_query", "on_screen_text"}, as script.Scene dumps)."""
    plan_scenes, shots = [], []
    for i, s in enumerate(scenes, 1):
        sid = f"scene-{i:03d}"
        narration = s.get("narration", "")
        visual = s.get("visual_query", "")
        plan_scenes.append(Scene(id=sid, narration=narration, on_screen_text=s.get("on_screen_text", ""), visual_notes=visual))
        shots.append(Shot(id=f"shot-{i:03d}-1", scene_id=sid, visual_description=visual, narration_reference=narration,
                          duration_seconds=spoken_seconds(narration) or float(s.get("seconds") or 0),
                          footage_queries=[visual] if visual else []))
    return DirectorPlan(project=Project(title=title, format=fmt, language=lang, visual_style=style),
                        continuity=Continuity(visual_style=style), scenes=plan_scenes, shots=shots)


def _cell(text: str) -> str:
    return " ".join(text.replace("|", "/").split())


def longform_markdown(plan: DirectorPlan) -> str:
    """The plan as the long-video script table longform/parse.py reads (Time | Visual | On-screen Text | Voiceover)."""
    rows, at = [], 0.0
    by_scene = {s.scene_id: s for s in plan.shots}
    for scene in plan.scenes:
        m, sec = divmod(int(at), 60)
        rows.append(f"| {m}:{sec:02d} | {_cell(scene.visual_notes)} | {_cell(scene.on_screen_text)} | {_cell(scene.narration)} |")
        shot = by_scene.get(scene.id)
        at += shot.duration_seconds if shot else 0
    return "\n".join([f"# {plan.project.title or 'Untitled'}", "",
                      "| Time | Visual | On-screen Text | Voiceover |", "| --- | --- | --- | --- |", *rows, ""])
