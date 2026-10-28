import shutil
from pathlib import Path

from PIL import Image

import make_song
from neonmekong import thumbnail

FIX = Path(__file__).parent / "fixtures" / "songs" / "demo-song"


def _song(tmp_path):
    dest = tmp_path / "demo-song"
    shutil.copytree(FIX, dest)
    assert make_song.main(["--dry-run", "analyze", str(dest)]) == 0
    return dest


def test_thumbnail_size_and_repeatable(tmp_path):
    song = _song(tmp_path)
    assert make_song.main(["--dry-run", "thumbnail", str(song)]) == 0
    out = song / "out" / "thumbnail.jpg"
    with Image.open(out) as im:
        assert im.size == (1280, 720)
    assert 20_000 < out.stat().st_size < thumbnail.MAX_BYTES
    first = out.read_bytes()
    assert make_song.main(["thumbnail", str(song)]) == 0
    assert out.read_bytes() == first  # same song, same picture
    assert list((song / "out").glob("thumbnail.jpg.bak-*"))  # old one kept


def test_fit_shrinks_long_text():
    lines, f = thumbnail.fit("A VERY LONG MOOD PHRASE THAT NEEDS WRAPPING", 800, 360, 170, 3)
    assert 1 < len(lines) <= 3 and f.size < 170


def test_bad_palette_falls_back():
    assert thumbnail.palette_of({"palette": ["nope"]}) == thumbnail.palette_of({})
