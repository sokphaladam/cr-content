import json
import shutil
import subprocess
from pathlib import Path

import pytest

import make_song
from neonmekong import analyze, lyricvideo, short, songjson

FIX = Path(__file__).parent / "fixtures" / "songs" / "demo-song"
HAS_FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


def _song(tmp_path):
    dest = tmp_path / "demo-song"
    shutil.copytree(FIX, dest)
    assert make_song.main(["--dry-run", "analyze", str(dest)]) == 0
    return dest


def _plan(song):
    return short.plan(songjson.load(song / "song.json"),
                      analyze.parse_lrc((song / "lyrics.lrc").read_text(encoding="utf-8")))


def test_plan_cuts_the_chorus(tmp_path):
    p = _plan(_song(tmp_path))
    assert 20.0 <= p["cut"] <= 20.5                     # on a beat just before the first chorus line
    assert short.MIN_LEN <= p["length"] <= short.MAX_LEN
    assert p["lyrics"][0]["text"] == "Replay, replay the night again" and p["lyrics"][0]["start"] < 0.7
    assert all(0 <= ln["start"] < p["length"] for ln in p["lyrics"])
    assert p["beats"][0] >= 0


def test_plan_needs_a_chorus(tmp_path):
    song = _song(tmp_path)
    d = songjson.load(song / "song.json")
    d["chorus"] = {"start": None, "end": None}
    with pytest.raises(ValueError):
        short.plan(d, [])


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_short_video_vertical_with_lyric_in_first_frame(tmp_path):
    song = _song(tmp_path)
    assert make_song.main(["--dry-run", "short", str(song), "--seconds", "2"]) == 0
    out = song / "out" / "short_chorus.mp4"
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "json", str(out)], capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    assert (s["width"], s["height"]) == (540, 960)      # draft size; the real one is 1080x1920
    assert short.SIZE == (1080, 1920)

    data = songjson.load(song / "song.json")
    p = _plan(song)
    v = lyricvideo.Variant("short", None, p["lyrics"], p["beats"], None, p["length"])
    chorus = [ln["text"] for ln in p["lyrics"]]
    kw = dict(text_scale=2.0, title_card=False, pill=False, end_screen=False, lyric_frac=0.5, max_lines=3,
              wrap_frac=0.88)
    on = lyricvideo.Scene(data, v, chorus, short.DRAFT, 15, instant_first=True, **kw).frame(0.0)
    off = lyricvideo.Scene(data, v, chorus, short.DRAFT, 15, instant_first=False, **kw).frame(0.0)
    band = slice(380, 580)                               # where the centred lyric sits
    assert (on[band] != off[band]).mean() > 0.01         # frame 0 already carries the lyric
    assert lyricvideo.Scene(data, v, chorus, short.DRAFT, 15, instant_first=True, **kw).frame(0.0).tobytes() == on.tobytes()


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_short_audio_length_and_stream(tmp_path):
    song = _song(tmp_path)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=48",
                    str(song / "audio.wav")], check=True)
    assert make_song.main(["short", str(song), "--draft"]) == 0
    p = json.loads((song / "out" / "short.json").read_text())
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json",
                        str(song / "out" / "short_chorus.mp4")], capture_output=True, text=True, check=True)
    info = json.loads(r.stdout)
    assert float(info["format"]["duration"]) == pytest.approx(p["length"], abs=0.3)
    assert {s["codec_type"] for s in info["streams"]} == {"video", "audio"}
