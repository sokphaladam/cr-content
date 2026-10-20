"""The real timeline: each scene lasts as long as its voiceover plus a short pause, and every timestamp (scene starts,
chapters) is recomputed from that, whatever the script's Time column planned.

A scene with no voiceover keeps the length its Time column gave it (up to the next scene's time), or 3 s.
Chapters are tied to the scene their planned time points at, so they move with it; without a Chapters line, each
"#N NAME" title card starts one.
"""
from dataclasses import dataclass, field

from .parse import Script, stamp
from .voice import Voice

SILENT_SEC = 3.0
LONG_MIN, LONG_MAX = 8 * 60, 15 * 60   # what the video is meant to be
YT_CHAPTER_MIN = 10.0                  # YouTube ignores chapter lists with one shorter than this


@dataclass
class Slot:
    scene: int
    start: float
    length: float
    planned: float
    voice: str
    voice_seconds: float

    @property
    def end(self) -> float:
        return self.start + self.length


@dataclass
class Timeline:
    slots: list[Slot]
    chapters: list[dict]                # {at, planned, title, scene}
    planned_total: float
    notes: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return self.slots[-1].end if self.slots else 0.0

    def to_json(self) -> dict:
        return {"total": round(self.total, 3), "planned_total": self.planned_total,
                "slots": [{**s.__dict__, "end": round(s.end, 3)} for s in self.slots],
                "chapters": self.chapters, "notes": self.notes}

    @classmethod
    def from_json(cls, data: dict) -> "Timeline":
        slots = [Slot(**{k: v for k, v in s.items() if k != "end"}) for s in data["slots"]]
        return cls(slots, data["chapters"], data["planned_total"], data.get("notes", []))


def _scene_for(script: Script, planned: float) -> int:
    """Index of the scene a planned chapter time points at: the one timed exactly there, else the first after it."""
    for i, s in enumerate(script.scenes):
        if abs(s.planned - planned) < 0.5:
            return i
    later = [i for i, s in enumerate(script.scenes) if s.planned >= planned]
    return later[0] if later else len(script.scenes) - 1


def build(script: Script, voices: list[Voice], cfg: dict) -> Timeline:
    pad = float(cfg["timing"]["pad_seconds"])
    by_scene = {v.scene: v for v in voices}
    slots, t = [], 0.0
    for i, scene in enumerate(script.scenes):
        v = by_scene.get(scene.n)
        if v and v.audio:
            length = v.seconds + pad
        else:  # no voiceover: as long as the plan gave it
            nxt = script.scenes[i + 1].planned if i + 1 < len(script.scenes) else None
            length = nxt - scene.planned if nxt and nxt > scene.planned else SILENT_SEC
        slots.append(Slot(scene.n, round(t, 3), round(length, 3), scene.planned,
                          v.audio if v else "", v.seconds if v else 0.0))
        t += length

    notes = []
    if script.chapters:
        marks = [(c.planned, c.title, _scene_for(script, c.planned)) for c in script.chapters]
    else:
        marks = [(0.0, "Intro", 0)] + [(s.planned, s.name.title(), i) for i, s in enumerate(script.scenes) if s.rank]
        notes.append("the script has no Chapters line; chapters start at each title card")
    chapters = []
    for planned, title, i in marks:
        at = 0.0 if not chapters else slots[i].start  # YouTube needs the first chapter at 0:00
        if chapters and at <= chapters[-1]["at"]:
            notes.append(f"chapter \"{title}\" ({stamp(planned)}) lands on the one before it; dropped")
            continue
        chapters.append({"at": round(at, 3), "planned": planned, "title": title, "scene": script.scenes[i].n})
    ends = [c["at"] for c in chapters[1:]] + [t]
    short = [c["title"] for c, end in zip(chapters, ends) if end - c["at"] < YT_CHAPTER_MIN]
    if short:
        notes.append(f"chapter(s) under {YT_CHAPTER_MIN:.0f} s ({', '.join(short)}): YouTube won't show chapters")
    if len(chapters) < 3:
        notes.append("fewer than 3 chapters: YouTube won't show chapters")

    planned_total = script.scenes[-1].planned + slots[-1].length  # the plan's end: its last scene, as long as it is
    if t < LONG_MIN or t > LONG_MAX:
        notes.append(f"the video is {stamp(t)} long, outside the {LONG_MIN // 60} to {LONG_MAX // 60} min it's meant "
                     f"to be (the voiceover is {sum(len(s.voiceover.split()) for s in script.scenes)} words)")
    return Timeline(slots, chapters, round(planned_total, 3), notes)
