from crcontent.longform.parse import Scene, Script
from crcontent.longform.voice import Voice
from crcontent.shorts import settings, timing
from crcontent.tts import Word


def _short(lengths, hook_end=1.7):
    scenes = [Scene(i + 1, i * 5.0, "v", f"TEXT {i + 1}", f"line {i + 1}") for i in range(len(lengths))]
    voices = [Voice(i + 1, f"s{i + 1}.mp3", sec + 0.35, [Word("w", 0.1, hook_end if i == 0 else sec)])
              for i, sec in enumerate(lengths)]
    return Script("T", "t", "en", scenes), voices


def test_voices_end_with_their_last_word():
    script, voices = _short([1.7, 4.0])
    tl = timing.timeline(script, voices, settings.DEFAULTS)
    assert [v.seconds for v in voices] == [1.78, 4.08]       # last word + 0.08, not the file's silent tail
    assert [s.length for s in tl.slots] == [2.03, 4.33]      # + 0.25 s between beats
    assert tl.notes == [] and tl.chapters == []              # no long-video notes


def test_hook_line_must_end_by_two_seconds():
    script, voices = _short([2.5, 6, 6, 6], hook_end=2.4)
    tl = timing.timeline(script, voices, settings.DEFAULTS)
    hook = timing.checks(script, tl, voices, settings.DEFAULTS)[0]
    assert not hook["ok"] and "2.40s" in hook["detail"]


def test_too_long_suggests_the_smallest_middle_beat_that_fixes_it():
    script, voices = _short([1.7, 9, 5, 4, 12, 3])              # ~36.6 s; hook and last beat are never cut
    tl = timing.timeline(script, voices, settings.DEFAULTS)
    length = timing.checks(script, tl, voices, settings.DEFAULTS)[1]
    assert not length["ok"]
    assert length["cut"]["beat"] == 2                          # 9.3 s is enough; beat 5 (12.3 s) would be too much
    assert length["cut"]["total_after"] <= 30


def test_when_no_single_beat_is_enough_the_longest_goes():
    script, voices = _short([1.7, 8, 10, 9, 8, 3])
    cut = timing.cut_suggestion(script, timing.timeline(script, voices, settings.DEFAULTS), 20)
    assert cut["beat"] == 3


def test_in_range_has_no_cut():
    script, voices = _short([1.7, 6, 6, 6, 4])
    tl = timing.timeline(script, voices, settings.DEFAULTS)
    assert all(c["ok"] for c in timing.checks(script, tl, voices, settings.DEFAULTS))
