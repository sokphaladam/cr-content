import json
import shutil
from pathlib import Path

import make_song
from neonmekong import config, songjson, suno

FIX = Path(__file__).parent / "fixtures" / "songs" / "demo-song"


def test_parse_fixture():
    s = suno.parse((FIX / "suno.txt").read_text(encoding="utf-8"))
    assert s.title == "Demo Song" and "nu-disco" in s.style
    assert [x.kind for x in s.sections] == ["intro", "verse", "chorus", "verse", "chorus", "bridge"]  # empty intro kept
    assert s.sections[2].lines[0] == "Replay, replay the night again"


def test_title_without_header():
    s = suno.parse("My Song\n\n[Chorus]\nla la\n")
    assert s.title == "My Song" and s.sections[0].kind == "chorus"


def test_prechorus_not_chorus():
    assert suno.kind_of("Pre-Chorus") == "pre-chorus"


def test_warnings_and_genre():
    data = songjson.from_suno(suno.parse((FIX / "suno.txt").read_text(encoding="utf-8")))
    assert data["genre"] == "nu-disco" and data["playlist"] == config.PLAYLISTS["nu-disco"]
    assert len(songjson.warnings(data)) == 2  # plan + generated_on
    data.update(plan="Pro", generated_on="2026-10-01")
    assert songjson.warnings(data) == []


def test_init_never_overwrites(tmp_path):
    song = tmp_path / "demo-song"
    shutil.copytree(FIX, song)
    assert make_song.main(["--dry-run", "init", str(song)]) == 0
    first = json.loads((song / "song.json").read_text(encoding="utf-8"))
    assert first["slug"] == "demo-song"
    (song / "song.json").write_text('{"title": "edited"}', encoding="utf-8")
    assert make_song.main(["init", str(song)]) == 1  # refuses
    assert json.loads((song / "song.json").read_text(encoding="utf-8"))["title"] == "edited"
    assert make_song.main(["init", str(song), "--force"]) == 0
    assert list(song.glob("song.json.bak-*"))  # old file kept


def test_sound_notes_never_take_lyrics_or_start_sections():
    text = ("Title: T\nStyle: Psychedelic synth-pop, 102 BPM\n\n[Intro]\n[Radio beeps, cosmic arpeggio]\n"
            "[Verse 2]\n[Drums get fuller]\nline a\n[Bridge]\n[Drums drop out, floating vocals]\nline b\n"
            "[Instrumental Break]\n[Soaring synth solo with phaser]\n[Final Chorus]\n[Layered harmonies, euphoric]\nline c\n"
            "[Outro]\nline d\n[Radio beeps fading into silence]\n")
    s = suno.parse(text)
    assert [(x.kind, x.lines) for x in s.sections] == [
        ("intro", []), ("verse", ["line a"]), ("bridge", ["line b"]), ("instrumental", []),
        ("chorus", ["line c"]), ("outro", ["line d"])]
    assert suno.kind_of("Drums drop out") == "note" and suno.kind_of("Pre Chorus") == "pre-chorus"
    assert songjson.genre_of(s.style) == "psych-pop"
