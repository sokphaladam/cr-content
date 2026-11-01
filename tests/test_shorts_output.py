import re

from crcontent.highlights import covers
from crcontent.longform.parse import Scene, Script
from crcontent.longform.timing import Slot, Timeline
from crcontent.shorts import captions, extras, plan, render
from crcontent.tts import Word


def _short(lang="en"):
    if lang == "km":
        scenes = [Scene(1, 0, "v", "ឆ្មារបស់អ្នក?", "ឆ្មា នាំ កណ្ដុរ មក"), Scene(2, 2, "v", "កុំស្រែក", "កុំ ស្រែក ដាក់ វា")]
    else:
        scenes = [Scene(1, 0, "v", "Your cat brought you THIS? 🐭", "Your cat just brought you a dead mouse."),
                  Scene(2, 2, "v", "Don't yell at it ❌", "Before you scream, this is a big deal.")]
    slots = [Slot(1, 0.0, 2.07, 0, "a.mp3", 1.8), Slot(2, 2.07, 2.9, 2, "b.mp3", 2.6)]
    words = {n: [Word(w, 0.1 + 0.2 * k, 0.28 + 0.2 * k) for k, w in enumerate(s.voiceover.split())]
             for n, s in enumerate(scenes, 1)}
    return Script("T", "t", lang, scenes), Timeline(slots, [], 5.0), words


def _positions(ass: str) -> list[tuple[int, int]]:
    return [(int(x), int(y)) for x, y in re.findall(r"\\pos\((\d+),(\d+)\)", ass)]


def test_every_text_sits_inside_the_safe_zone():
    for lang in ("en", "km"):
        ass = captions.build(*_short(lang))
        assert "Style: Hook" in ass and "Caption" in ass and "Label" in ass
        for x, y in _positions(ass):
            assert captions.LEFT < x < captions.RIGHT and captions.TOP < y < captions.BOTTOM


def test_text_is_centred_on_screen_and_clear_of_the_right_buttons():
    assert captions.CX == 1080 // 2
    assert captions.RIGHT <= round(1080 * covers.SAFE["right"]) and captions.LEFT >= round(1080 * covers.SAFE["left"])
    assert captions.CX - captions.LEFT == captions.RIGHT - captions.CX
    for x, _ in _positions(captions.build(*_short())):
        assert x == captions.CX


def test_caption_widths_fit_between_the_safe_edges():
    for text in ["SHORT", "EVEN WELL-FED HOUSE CATS STILL", "HARD-WIRED — NOT HUNGER. EXTRAORDINARILY"]:
        rows, size = captions._fit(text, "Segoe UI Black", captions.CAPTION_PX, "en",
                                   captions.RIGHT - captions.LEFT)
        assert len(rows) <= 2
        assert max(captions._text_width(r, "Segoe UI Black", size, "en") for r in rows) <= \
            captions.RIGHT - captions.LEFT + 1


def test_hook_is_on_the_first_frame_and_the_spoken_word_is_yellow():
    ass = captions.build(*_short())
    hook = [l for l in ass.splitlines() if l.startswith("Dialogue") and ",Hook," in l]
    assert hook and all(",0:00:00.00," in l for l in hook)
    assert "YOUR CAT BROUGHT YOU THIS?" in hook[-1].replace(r"\N", " ")
    assert captions.YELLOW in ass


def test_caption_groups_break_at_sentence_ends():
    words = [Word(w, k, k + 0.5) for k, w in enumerate("It's hard-wired — not hunger. Cats carry prey".split())]
    assert [[w.text for w in g] for g in captions.groups(words, 3)] == \
        [["It's", "hard-wired", "—"], ["not", "hunger."], ["Cats", "carry", "prey"]]


def test_beats_cut_on_whole_frames_without_drift():
    lengths = render.frame_lengths([2.068, 4.91, 10.2, 23.372])
    assert all(abs(l * 30 - round(l * 30)) < 1e-9 for l in lengths)
    assert abs(sum(lengths) - 23.372) < 1 / 30


def test_loop_tail_ends_on_the_opening_frame():
    assert render.loop_tail({"file": "x.mp4", "start": 17.875}, 0.5) == 17.375
    assert render.loop_tail({"file": "x.mp4", "start": 0.2}, 0.5) == 0.2  # nothing before it: from the start


def test_long_cover_titles_get_a_third_line_only_when_needed():
    width = lambda t, px: {"w": len(t) * px * 0.6}
    assert covers._lines("REPLAY", width, 100, 860) == ["REPLAY"]
    assert len(covers._lines("SAME MOON SOMEHOW", width, 100, 860)) == 2
    rows = covers._lines("YOUR CAT BROUGHT YOU A DEAD MOUSE? DON'T YELL", width, 100, 860)
    assert len(rows) == 3 and " ".join(rows) == "YOUR CAT BROUGHT YOU A DEAD MOUSE? DON'T YELL"


def test_metadata_has_every_part_and_no_hashtags_in_the_title():
    ep = plan.ShortPlan(1, "Cat Title 🐭", Script("Cat Title", "s", "en", []), description="Why cats do it.",
                        hashtags=["catfacts", "shorts"], pinned_comment="What did yours bring? 👇")
    text = extras.metadata(ep)
    assert text.startswith("TITLE\nCat Title 🐭\n")
    assert "#catfacts #shorts" in text and "PINNED COMMENT\nWhat did yours bring? 👇" in text


def test_the_rules_endpoint_serves_the_numbers_the_checks_use():
    from fastapi.testclient import TestClient

    from crcontent import web
    from crcontent.shorts import match, preflight, registry, settings

    r = TestClient(web.app).get("/api/shorts/rules").json()
    rules = settings.load()["rules"]
    assert (r["hook_max"], r["length_min"], r["length_max"], r["loop_tail"]) == (
        rules["hook_max"], rules["length"]["min"], rules["length"]["max"], rules["loop_tail"])
    assert (r["match_pass"], r["fresh_days"], r["judge_ready"]) == (match.PASS, registry.RECENT_DAYS, preflight.JUDGE_READY)
