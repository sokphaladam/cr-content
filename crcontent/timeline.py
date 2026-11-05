"""The editor timeline's global clips at render time (attention roadmap M4): the same Clip times the preview plays.

- sound_events  the sfx track's clips as render.finalize effects, trimmed, faded and at their gain
- graphic_clips the graphics track's clips as shorts.motion.overlay clips (Remotion, transparent, laid over)
- mix           the voice / music lanes' mute and volume for the mix

Solo is monitoring only (the preview); a muted or hidden track, or a clip whose sound / template doesn't exist, is
left out with a note for the job log, never silently.
"""
from . import graphic_templates as gt
from . import sfx
from .script import Clip, VideoScript


def _gain(script: VideoScript, track: str) -> float:
    t = script.track(track)
    return 0.0 if t.mute else t.volume


def sound_events(script: VideoScript, length: float, log=print, left_out: dict | None = None) -> list[tuple]:
    """(sound file, start, volume, {in, dur, fade_in, fade_out}) for every sfx clip that plays before `length`."""
    out, vol = [], _gain(script, "sfx")
    for c in sorted((c for c in script.clips if c.track == "sfx"), key=lambda c: c.start):
        why = ("the sound isn't in the library" if not sfx.exists(c.sound) else "the sounds lane is muted" if not vol else
               "its gain is 0" if not c.gain else "it starts after the video ends" if c.start >= length else "")
        if why:  # a missing optional sound never stops the render
            if not sfx.exists(c.sound):
                log(f"      ! sound effect {c.id}: the sound '{c.sound or 'none'}' isn't in the library, left out")
            if left_out is not None:
                left_out[c.id] = why
            continue
        dur = min(c.duration, length - c.start)
        fade_in, fade_out = min(c.fade_in, dur / 2), min(c.fade_out, dur / 2)
        out.append((sfx.sound(c.sound), c.start, c.gain * vol,
                    {"in": c.source_in, "dur": dur, "fade_in": fade_in, "fade_out": fade_out, "duck": c.duck}))
    return out


def graphic_clips(script: VideoScript, length: float, font: str, log=print, frame_at=None,
                  left_out: dict | None = None) -> list[dict]:
    """The graphics track as shorts.motion.overlay clips ({id, at, props}), bottom layer first. Props are checked
    against their template (graphic_templates.validate): an invalid graphic is left out, with why.
    frame_at(seconds): the picture there as a data: URL, for a freeze-frame spotlight (None: it spotlights live)."""
    if script.track("graphics").hidden or script.track("graphics").mute:
        if any(c.track == "graphics" for c in script.clips):
            log("      graphics track hidden: its graphics are left out")
        if left_out is not None:
            left_out.update({c.id: "the graphics lane is hidden" for c in script.clips if c.track == "graphics"})
        return []
    out = []
    for c in sorted((c for c in script.clips if c.track == "graphics"), key=lambda c: (c.layer, c.start)):
        props, errors = gt.validate(c.template, c.props, c.template_version)
        if errors:
            log(f"      ! graphic {c.id} ({c.template or 'no template'}) left out: {' '.join(errors)}")
            if left_out is not None:
                left_out[c.id] = " ".join(errors)
            continue
        if c.start >= length:
            if left_out is not None:
                left_out[c.id] = "it starts after the video ends"
            continue
        if c.template == "Spotlight" and props.get("freeze") == "yes" and frame_at:
            props["photo"] = frame_at(c.start) or ""
        seconds = round(min(c.duration, length - c.start), 3)
        out.append({"id": c.template, "at": c.start, "clip": c.id, "props": {**props, "font": font, "seconds": seconds}})
    return out


def mix(script: VideoScript) -> dict:
    """The voice and music lanes for render.finalize: music None when muted, its level and the voice's gain."""
    return {"music_on": not script.track("music").mute, "music_volume": 0.25 * script.track("music").volume,
            "voice_gain": _gain(script, "voice"), "music_duck": script.track("music").duck}


def sounds_used(script: VideoScript, length: float) -> list[str]:
    """The sound names the render mixes in (for credits)."""
    return [c.sound for c in script.clips if c.track == "sfx" and c.start < length and sfx.exists(c.sound)]


def check(clips: list[Clip]) -> list[str]:
    """Problems that keep a clip from rendering (shown before render; the render skips them the same way)."""
    out = []
    for c in clips:
        if c.track == "sfx" and not sfx.exists(c.sound):
            out.append(f"Sound effect {c.id} has no sound picked." if not c.sound else
                       f"Sound effect {c.id}: '{c.sound}' isn't in the sound library any more.")
        if c.track == "graphics" and (errors := gt.validate(c.template, c.props, c.template_version)[1]):
            out.append(f"Graphic {c.id} ({c.template or 'no template'}): {' '.join(errors)}")
    return out
