import json
import shutil
import subprocess
from pathlib import Path

import pytest

import make_song

FIX = Path(__file__).parent / "fixtures" / "songs" / "demo-song"
HAS_FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


def _copy(tmp_path):
    dest = tmp_path / "demo-song"
    shutil.copytree(FIX, dest)
    return dest


def test_all_pauses_after_analyze_then_continues(tmp_path, capsys):
    song = _copy(tmp_path)
    assert make_song.main(["--dry-run", str(song), "--no-video"]) == 0          # bare path == "all"
    out = capsys.readouterr().out
    assert "Review and edit" in out and not (song / "upload.txt").exists()
    data = json.loads((song / "song.json").read_text(encoding="utf-8"))
    data.update(plan="Pro", generated_on="2026-10-01")
    (song / "song.json").write_text(json.dumps(data), encoding="utf-8")
    assert make_song.main(["--dry-run", str(song), "--no-video"]) == 0
    assert (song / "upload.txt").exists() and (song / "checklist.md").exists()
    assert (song / "out" / "thumbnail.jpg").exists()
    assert json.loads((song / "song.json").read_text(encoding="utf-8"))["plan"] == "Pro"   # edits kept


def test_all_needs_suno_txt(tmp_path):
    (tmp_path / "empty").mkdir()
    assert make_song.main(["--dry-run", str(tmp_path / "empty")]) == 1


def test_instrumental_skips_without_stem(tmp_path, capsys):
    song = _copy(tmp_path)
    assert make_song.main(["--dry-run", "analyze", str(song)]) == 0
    assert make_song.main(["--dry-run", "instrumental", str(song)]) == 0
    assert "skipping" in capsys.readouterr().out and not (song / "out" / "instrumental.mp4").exists()


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_full_pipeline_with_instrumental(tmp_path):
    song = _copy(tmp_path)
    for name, hz in (("audio.wav", 440), ("instrumental.wav", 220)):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency={hz}:duration=48",
                        str(song / name)], check=True)
    assert make_song.main(["--dry-run", "analyze", str(song)]) == 0
    assert make_song.main([str(song), "--draft", "--seconds", "2"]) == 0
    out = song / "out"
    for f in ("thumbnail.jpg", "lyric_full.mp4", "short_chorus.mp4", "instrumental.mp4"):
        assert (out / f).exists(), f
    assert (song / "upload.txt").exists() and (song / "checklist.md").exists()
