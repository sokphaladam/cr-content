import json
import shutil
import subprocess
from pathlib import Path

import pytest

import make_song
from neonmekong import lyricvideo as lv

FIX = Path(__file__).parent / "fixtures" / "songs" / "demo-song"
HAS_FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


def _song(tmp_path):
    dest = tmp_path / "demo-song"
    shutil.copytree(FIX, dest)
    assert make_song.main(["--dry-run", "analyze", str(dest)]) == 0
    return dest


def _probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def test_timing_helpers():
    beats = [1.0, 2.0]
    assert lv.pulse(0.5, beats) == 0.0 and lv.pulse(1.0, beats) == pytest.approx(1.0) and 0 < lv.pulse(1.2, beats) < 1
    assert lv.lyric_y(10, 200) == lv.LYRIC_Y and lv.lyric_y(190, 200) == pytest.approx(lv.END_LYRIC_Y)
    assert lv.card_alpha(0.0) == 0 and lv.card_alpha(3.0) == 1 and lv.card_alpha(6.0) == 0
    assert lv.TITLE_CARD[1] <= 6.0


def test_subscribe_pill_follows_first_chorus():
    assert lv.pill_state(10, 28.4, 200) == (0.0, 0.0)
    assert lv.pill_state(28.4 + 0.3 + 2.0, 28.4, 200)[0] == 1.0
    assert lv.pill_state(28.4 + 0.3 + lv.PILL_LEN + 0.1, 28.4, 200)[0] == 0.0
    assert lv.pill_state(190, 28.4, 200)[0] == 0.0       # never inside the end-screen zone
    assert lv.pill_state(30, None, 200)[0] == 0.0


def test_active_line_fades_and_never_overlaps():
    lines = [{"start": 5.0, "end": 8.0}, {"start": 8.2, "end": 11.0}]
    starts = [5.0, 8.2]
    assert lv.active_line(2.0, lines, starts) is None
    assert lv.active_line(6.5, lines, starts) == (0, 1.0)
    assert lv.active_line(8.05, lines, starts)[1] < 0.1   # previous line is almost gone before the next fades in
    assert lv.active_line(8.11, lines, starts)[0] == 1
    assert lv.active_line(8.15, lines, starts)[0] == 1 and lv.active_line(8.15, lines, starts)[1] < 0.3
    assert lv.active_line(9.5, lines, starts)[0] == 1


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_draft_video_dry_run(tmp_path):
    song = _song(tmp_path)
    assert make_song.main(["--dry-run", "video", str(song), "--hook", "full", "--seconds", "3"]) == 0
    out = song / "out" / "lyric_full.mp4"
    info = _probe(out)
    assert (info["streams"][0]["width"], info["streams"][0]["height"]) == (960, 540)
    assert float(info["format"]["duration"]) == pytest.approx(3.0, abs=0.2)
    assert out.stat().st_size > 5_000


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_auto_renders_both_hook_options_with_audio(tmp_path):
    song = _song(tmp_path)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=48",
                    str(song / "audio.wav")], check=True)
    assert make_song.main(["video", str(song), "--draft", "--seconds", "2"]) == 0   # vocal at 12s -> trim + preview
    for option in ("trim", "preview"):
        out = song / "out" / f"lyric_{option}.mp4"
        assert out.exists()
        streams = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                                  str(out)], capture_output=True, text=True).stdout.split()
        assert "audio" in streams and "video" in streams


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_frames_differ_over_time_and_chorus_lines_flagged(tmp_path):
    song = _song(tmp_path)
    from neonmekong import songjson
    from neonmekong.suno import parse
    data = songjson.load(song / "song.json")
    s = parse((song / "suno.txt").read_text(encoding="utf-8"))
    chorus = [ln for sec in s.sections if sec.kind == "chorus" for ln in sec.lines]
    scene = lv.Scene(data, lv.variant(song, data, "full"), chorus, lv.DRAFT, 15)
    assert scene.chorus == [False, False, True, True, False, True, True, False]
    a, b = scene.frame(1.0), scene.frame(22.0)
    assert a.shape == (540, 960, 3) and (a != b).mean() > 0.2
    assert scene.frame(22.0).tobytes() == b.tobytes()   # deterministic
