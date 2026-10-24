import json
import shutil
from pathlib import Path

import make_song
from neonmekong import analyze

FIX = Path(__file__).parent / "fixtures" / "songs" / "demo-song"


def _run(tmp_path, *extra):
    song = tmp_path / "demo-song"
    if not song.exists():
        shutil.copytree(FIX, song)
    assert make_song.main(["--dry-run", "analyze", str(song), *extra]) == 0
    return song, json.loads((song / "song.json").read_text(encoding="utf-8"))


def test_analyze_dry_run(tmp_path, capsys):
    song, d = _run(tmp_path)
    assert d["bpm"] == 118 and d["vocal_start"] == 12.0
    assert d["chorus"] == {"start": 20.5, "end": 28.4}
    kinds = {r["kind"]: r.get("level") for r in d["sections"] if "start" in r}
    assert kinds["chorus"] == "high" and kinds["verse"] == "mid"
    assert d["mood_phrase"] == "Nostalgic Disco Love" and d["subscribe_line"]
    lrc = (song / "lyrics.lrc").read_text(encoding="utf-8")
    assert lrc.startswith("[00:12.00]Streetlights hum along the river")
    out = capsys.readouterr().out
    assert "vocals start at 12.0s" in out and "plan is missing" in out


def test_user_edits_survive_and_backup_kept(tmp_path):
    song, d = _run(tmp_path)
    d.update(mood_phrase="My Own Phrase", plan="Pro", generated_on="2026-10-01")
    (song / "song.json").write_text(json.dumps(d), encoding="utf-8")
    song, d2 = _run(tmp_path)
    assert d2["mood_phrase"] == "My Own Phrase" and d2["plan"] == "Pro"
    assert list(song.glob("song.json.bak-*"))


def test_quiet_chorus_warns():
    from neonmekong import songjson, suno
    s = suno.parse((FIX / "suno.txt").read_text(encoding="utf-8"))
    m = analyze.mock(FIX)
    m["rms"] = [0.5] * len(m["rms"])
    _, notes = analyze.fill(songjson.from_suno(s), s, m)
    assert any("not louder" in n for n in notes)
