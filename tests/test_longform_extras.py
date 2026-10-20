from crcontent.longform.extras import description, thumbnail_text
from crcontent.longform.parse import Scene, Script
from crcontent.longform.timing import Slot, Timeline
from crcontent.longform.video import cues, srt
from crcontent.tts import Word


def _setup():
    script = Script("Owls", "owls", "en", [Scene(1, 0, "v", "", "Owls hunt at night. They hear everything."),
                                           Scene(2, 30, "v", "#1 OWL", "Number one.", rank=1, name="OWL")],
                    description="All about owls.", title_options=["Owls, Ranked"],
                    thumbnail='an owl, big text "SILENT HUNTER"')
    tl = Timeline([Slot(1, 0.0, 5.0, 0, "a.mp3", 4.6), Slot(2, 5.0, 2.0, 30, "b.mp3", 1.6)],
                  [{"at": 0.0, "planned": 0, "title": "Intro", "scene": 1},
                   {"at": 5.0, "planned": 30, "title": "Owl", "scene": 2}], 32.0)
    words = {1: [Word("Owls", 0.1, 0.4), Word("hunt", 0.4, 0.7), Word("at", 0.7, 0.8), Word("night.", 0.8, 1.3),
                 Word("They", 1.6, 1.8), Word("hear", 1.8, 2.1), Word("everything.", 2.1, 2.9)],
             2: [Word("Number", 0.1, 0.5), Word("one.", 0.5, 0.9)]}
    return script, tl, words


def test_cues_split_at_sentences_and_sit_on_the_video_timeline():
    script, tl, words = _setup()
    got = cues(script, tl, words)
    assert [t for _, _, t in got] == ["Owls hunt at night.", "They hear everything.", "Number one."]
    assert got[2][0] == 5.1  # scene 2 starts at 5.0 s
    assert all(a[1] <= b[0] for a, b in zip(got, got[1:]))  # never overlapping


def test_srt_format():
    text = srt([(0.1, 1.6, "Owls hunt at night."), (61.25, 62.0, "Next.")])
    assert text.startswith("1\n00:00:00,100 --> 00:00:01,600\nOwls hunt at night.\n")
    assert "2\n00:01:01,250 --> 00:01:02,000\nNext.\n" in text


def test_description_uses_real_chapter_times():
    script, tl, _ = _setup()
    desc = description(script, tl, [], [])
    assert "Chapters:\n0:00 Intro\n0:05 Owl" in desc
    assert desc.startswith("All about owls.")


def test_thumbnail_text_from_the_note():
    script, _, _ = _setup()
    assert thumbnail_text(script) == "SILENT HUNTER"


def test_punctuation_comes_back_from_the_text():
    from crcontent.longform.voice import punctuated

    words = [Word(x, i, i + 0.5) for i, x in enumerate(["People", "say", "bird", "brain", "Multi", "part", "tools"])]
    got = punctuated('People say "bird brain". Multi-part tools!', words)
    assert [w.text for w in got] == ["People", "say", '"bird', 'brain".', "Multi-part", "tools!"]
    assert (got[4].start, got[4].end) == (4, 5.5)  # the two engine words of one token, merged
