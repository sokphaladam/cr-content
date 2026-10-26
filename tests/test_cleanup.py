import os
import time
from pathlib import Path

from crcontent import cleanup

OLD = time.time() - 3 * 86_400


def _file(path: Path, size: int = 10, age: float = OLD) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    os.utime(path, (age, age))
    return path


def _library(tmp_path: Path):
    root, out = tmp_path, tmp_path / "output"
    job = out / "20261001-000000-en-a"
    _file(job / "work" / "scene_00.mp4", 100)
    _file(job / "video.mp4", 500)
    _file(job / "video.mp4.bak-20261001-000000", 300)
    (job / "script.json").write_text('{"media": "cache/stock/pixabay-1.mp4", "art": "cache\\gen\\anime-aa.png"}')
    _file(root / "cache" / "stock" / "pixabay-1.mp4", 200)            # used
    _file(root / "cache" / "stock" / "pixabay-2.mp4", 400)            # unused
    _file(root / "cache" / "stock" / "pixabay-3.mp4", 400, age=time.time())   # unused but just downloaded
    _file(root / "cache" / "gen" / "anime-aa.png", 50)                 # used
    _file(root / "cache" / "gen" / "anime-bb.png", 60)                 # unused
    _file(root / "cache" / "voiceover" / "keep.mp3", 70)               # never touched
    _file(root / "cache" / "preview" / "p.mp4", 80)
    _file(root / "media" / "plan-x-ep01" / "removed" / "mine.mp4", 90)
    return root, out


def test_scan_finds_only_what_nothing_uses(tmp_path):
    root, out = _library(tmp_path)
    by = {g["id"]: g for g in cleanup.scan(root, out)}
    assert by["work"]["bytes"] == 100 and by["old"]["bytes"] == 300
    assert by["footage"]["bytes"] == 400 and by["footage"]["examples"] == ["pixabay-2.mp4"]
    assert by["pictures"]["bytes"] == 60 and by["temp"]["bytes"] == 80 and by["removed"]["bytes"] == 90
    assert "voiceover" not in str(by)


def test_run_deletes_only_the_chosen_groups(tmp_path):
    root, out = _library(tmp_path)
    result = cleanup.run(root, out, ["work", "footage", "nonsense"])
    assert result == {"freed": 500, "files": 2, "failed": 0}
    assert not (out / "20261001-000000-en-a" / "work").exists()          # the emptied folder goes too
    assert (out / "20261001-000000-en-a" / "video.mp4").exists()
    assert (root / "cache" / "stock" / "pixabay-1.mp4").exists() and (root / "cache" / "stock" / "pixabay-3.mp4").exists()
    assert not (root / "cache" / "stock" / "pixabay-2.mp4").exists()
    assert (root / "cache" / "gen" / "anime-bb.png").exists() and (root / "cache" / "voiceover" / "keep.mp3").exists()
    assert {g["id"] for g in cleanup.scan(root, out)} == {"old", "pictures", "temp", "removed"}
