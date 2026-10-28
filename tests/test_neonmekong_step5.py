import json
import shutil
import subprocess
from pathlib import Path

import pytest

import make_song
from neonmekong import analyze, hook, songjson

FIX = Path(__file__).parent / "fixtures" / "songs" / "demo-song"
HAS_FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


def _song(tmp_path):
    dest = tmp_path / "demo-song"
    shutil.copytree(FIX, dest)
    assert make_song.main(["--dry-run", "analyze", str(dest)]) == 0
    return dest


def _plan(song):
    return hook.plan(songjson.load(song / "song.json"), analyze.parse_lrc((song / "lyrics.lrc").read_text(encoding="utf-8")))


def test_plan_trim_and_preview(tmp_path):
    p = _plan(_song(tmp_path))
    assert p["needs_edit"]
    t = p["trim"]
    assert 10.0 <= t["audio_start"] <= 10.5 and t["lyrics"][0]["start"] == pytest.approx(12.0 - t["audio_start"], abs=0.01)
    pv = p["preview"]
    assert pv["length"] == 8.0 and pv["song_offset"] == pytest.approx(7.2)
    assert 20.0 <= pv["src_start"] <= 20.5
    starts = [ln["start"] for ln in pv["lyrics"]]
    assert starts[0] < 1.0 and starts == sorted(starts)             # the chorus preview opens on a lyric
    assert pv["lyrics"][-1]["text"] == "Hold on, hold on"           # full song follows, shifted by the offset
    # the song part skips the same long intro as the trim: it starts at the trim's cut, not at 0
    assert pv["song_start"] == t["audio_start"]
    assert pv["lyrics"][-1]["start"] == pytest.approx(40.5 + 7.2 - t["audio_start"], abs=0.01)
    assert pv["duration"] == pytest.approx(7.2 + 48.0 - t["audio_start"], abs=0.01)


def test_early_vocal_needs_no_edit(tmp_path):
    song = _song(tmp_path)
    d = songjson.load(song / "song.json")
    d["vocal_start"] = 4.0
    assert hook.plan(d, [])["needs_edit"] is False
    assert hook.plan(d, [], force=True)["needs_edit"] is True


def test_dry_run_writes_plan_and_lyrics_only(tmp_path):
    song = _song(tmp_path)
    assert make_song.main(["--dry-run", "hook", str(song)]) == 0
    out = song / "out" / "hook"
    assert (out / "lyrics_trim.lrc").exists() and (out / "lyrics_preview.lrc").exists()
    assert json.loads((out / "hook.json").read_text())["needs_edit"] is True
    assert not list(out.glob("*.wav"))


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_renders_audio_with_expected_lengths(tmp_path):
    song = _song(tmp_path)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=48",
                    str(song / "audio.wav")], check=True)
    assert make_song.main(["hook", str(song)]) == 0

    def length(name):
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            str(song / "out" / "hook" / name)], capture_output=True, text=True, check=True)
        return float(r.stdout)
    p = json.loads((song / "out" / "hook" / "hook.json").read_text())
    assert length("audio_trim.wav") == pytest.approx(48 - p["trim"]["audio_start"], abs=0.1)
    assert length("audio_preview.wav") == pytest.approx(p["preview"]["duration"], abs=0.1)


def test_preview_timeline_maps_back_to_the_song(tmp_path):
    from neonmekong import lyricvideo as lv
    song = _song(tmp_path)
    assert make_song.main(["--dry-run", "hook", str(song)]) == 0
    data = songjson.load(song / "song.json")
    v = lv.variant(song, data, "preview")
    length, p0, off = v.preview
    assert v.song_time(1.0) == pytest.approx(p0 + 1.0)                       # the chorus preview
    assert v.song_time(off + 5.0) == pytest.approx(v.skip + 5.0)             # the song, from the trim's cut
