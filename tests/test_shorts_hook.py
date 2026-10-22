import subprocess

import pytest

from crcontent.shorts import hook


def _clip(path, vf, still=False):
    src = ["-loop", "1", "-framerate", "30", "-t", "4", "-i", str(path.with_suffix(".png"))] if still else \
          ["-f", "lavfi", "-i", "testsrc2=s=640x360:d=4"]
    if still:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=640x360:d=1", "-frames:v", "1",
                        str(path.with_suffix(".png"))], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", *src, "-vf", f"{vf},format=yuv420p", str(path)], check=True)
    return path


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("hook")
    return {
        "static": _clip(d / "static.mp4", "null", still=True),
        # zoompan crops on whole pixels: at a small size that jitters (real motion); at 1080p it's a smooth zoom
        "zoom": _clip(d / "zoom.mp4", "scale=3840:-2,zoompan=z='1+0.0015*on':x='iw/2-(iw/zoom/2)':"
                                      "y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=30", still=True),
        "dark": _clip(d / "dark.mp4", "eq=brightness=-0.7"),
        "moving": _clip(d / "moving.mp4", "null"),
    }


def test_static_and_slow_zoom_and_dark_are_rejected(clips):
    assert hook.scan(clips["static"], 2.0).reject == "static: nothing moves"
    assert hook.scan(clips["zoom"], 2.0).reject.startswith("slow zoom or pan")
    assert hook.scan(clips["dark"], 2.0).reject.startswith("too dark")


def test_a_moving_clip_passes_and_skips_the_fade_in(clips):
    s = hook.scan(clips["moving"], 2.0)
    assert s.reject == "" and s.own >= hook.OWN_MOTION_MIN
    assert s.start >= hook.SKIP_START - 0.5 / hook.SAMPLE_FPS and s.start + 2.0 <= s.seconds


def test_claude_rejects_the_wrong_animal_no_motion_logos_and_intros():
    seen = {"animal": True, "in_motion": True, "logo_or_text": False, "intro_or_title": False, "seen": "cat"}
    assert hook.judged(hook.Scan("a.mp4", 10, score=0.8), dict(seen)).reject == ""
    assert "right animal" in hook.judged(hook.Scan("b", 10), {**seen, "animal": False, "seen": "a leopard"}).reject
    assert "logo" in hook.judged(hook.Scan("c", 10), {**seen, "logo_or_text": True}).reject
    assert "intro" in hook.judged(hook.Scan("d", 10), {**seen, "intro_or_title": True}).reject
    assert "doesn't move" in hook.judged(hook.Scan("f", 10), {**seen, "in_motion": False}).reject
    # a clip the motion checks rejected keeps that reason
    assert hook.judged(hook.Scan("e", 10, reject="static: nothing moves"), dict(seen)).reject ==         "static: nothing moves"
