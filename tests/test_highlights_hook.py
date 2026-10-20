from types import SimpleNamespace

from crcontent.config import HEIGHT, LANGS, WIDTH
from crcontent.highlights.clip import GAP, HOOK_BORDER, SAFE_BOTTOM, SAFE_TOP, _add_hook, _wrap, lyric_box, place_hook
from crcontent.styles import LyricStyle

EN = LANGS["en"]
HOOK = "POV: she won't decide but keeps driving"


def line(text):
    return SimpleNamespace(words=[SimpleNamespace(text=w) for w in text.split()])


def hook_height(rows, size):
    return (rows * size * 1.1 + 2 * HOOK_BORDER) / HEIGHT


def overlaps(top, rows, size, box):
    bottom = top + hook_height(rows, size)
    return not (bottom <= box[0] - GAP + 1e-6 or top >= box[1] + GAP - 1e-6)


def test_screenshot_case_hook_clear_of_two_line_lyrics():
    # the broken clip: lyrics in the middle wrapping to 2 lines, a face near the top, a hook on 2 lines
    style = LyricStyle(position="middle", size="l").clean("en")
    box = lyric_box([line("She test drive my heart tonight and she never wants to stop")], style, EN)
    size = round(EN.font_size * 0.8)
    rows = _wrap(HOOK, EN.font_name, size, "en", WIDTH - 180)
    assert len(rows) == 2
    top = place_hook(len(rows), size, subject_y=0.3, lyrics=box)
    assert not overlaps(top, len(rows), size, box)
    assert SAFE_TOP <= top and top + hook_height(len(rows), size) <= SAFE_BOTTOM


def test_every_layout_keeps_the_hook_off_the_lyrics():
    size = round(EN.font_size * 0.8)
    for position in ("low", "middle", "high"):
        for lyric_size in ("s", "m", "l"):
            style = LyricStyle(position=position, size=lyric_size).clean("en")
            for lyrics in ([], [line("short")], [line("a much longer lyric line that has to wrap across the frame twice over")]):
                box = lyric_box(lyrics, style, EN)
                for rows in (1, 2, 3):
                    for subject in (None, 0.2, 0.7):
                        top = place_hook(rows, size, subject, box)
                        assert not overlaps(top, rows, size, box), (position, lyric_size, rows, subject)
                        assert top + hook_height(rows, size) <= SAFE_BOTTOM + 1e-6


def test_hook_goes_to_the_top_unless_a_face_is_there():
    style = LyricStyle(position="low").clean("en")
    box = lyric_box([line("one line")], style, EN)
    assert place_hook(1, 74, None, box) < 0.15
    assert place_hook(1, 74, 0.25, box) > 0.4  # just above the lyrics instead


def test_hook_lines_are_written_as_given():
    ass = "[V4+ Styles]\nStyle: Lyric,Arial,80\n[Events]\n"
    out = _add_hook(ass, ["POV: she won't decide", "but keeps driving"], "Arial", 74, 0.4)
    assert r"POV: she won't decide\Nbut keeps driving" in out and r"\q2" in out
    assert _add_hook(ass, [], "Arial", 74, 0.4) == ass
