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

VERSION = 1
ASPECTS = {"short": "9:16", "long": "16:9"}
STYLES = ("cinematic_documentary", "cinematic_wildlife", "educational", "storytelling")
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


class Camera(BaseModel):
    angle: str = "eye_level"
    movement: str = "static"
    framing: str = "medium"


MATCHES = ("own", "drawn", "exact", "good", "subject_only", "weak", "unchecked")


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


class Project(BaseModel):
    title: str = ""
    format: Literal["short", "long"]
    aspect_ratio: str = ""
    language: str = "en"
    visual_style: str = STYLES[0]

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
    """Bring a stored plan up to VERSION. Version 1 is the first, so there is nothing to convert yet."""
    version = int(data.get("version", VERSION))
    if version > VERSION:
        raise ValueError(f"This plan was made by a newer version of the app (plan v{version}). Update the app to open it.")
    return {**data, "version": VERSION}


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
