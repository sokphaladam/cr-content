from crcontent.longform import settings
from crcontent.longform.parse import Chapter, Scene, Script
from crcontent.longform.timing import build
from crcontent.longform.voice import Voice


def _script(chapters=()):
    scenes = [Scene(1, 0, "v", "HELLO", "Hi there."), Scene(2, 20, "v", "#2 OWL", "Number two: the owl.", rank=2,
                                                                name="OWL"),
              Scene(3, 40, "v", "", ""), Scene(4, 50, "v", "#1 CROW", "Number one: the crow.", rank=1, name="CROW")]
    return Script("T", "t", "en", scenes, chapters=list(chapters))


def _voices():
    return [Voice(1, "a.mp3", 5.0), Voice(2, "b.mp3", 12.0), Voice(3, "", 0.0), Voice(4, "d.mp3", 11.6)]


def test_scene_lengths_follow_the_voice():
    tl = build(_script(), _voices(), settings.DEFAULTS)
    assert [s.length for s in tl.slots] == [5.4, 12.4, 10.0, 12.0]  # silent scene keeps its planned 10 s
    assert [s.start for s in tl.slots] == [0, 5.4, 17.8, 27.8]
    assert round(tl.total, 3) == 39.8


def test_chapters_move_with_their_scene():
    tl = build(_script([Chapter(0, "Intro"), Chapter(20, "Owl"), Chapter(50, "Crow")]), _voices(), settings.DEFAULTS)
    assert [(c["at"], c["title"], c["scene"]) for c in tl.chapters] == [(0, "Intro", 1), (5.4, "Owl", 2),
                                                                          (27.8, "Crow", 4)]
    assert any("under 10 s" in n for n in tl.notes)  # Intro is 5.4 s


def test_chapters_from_title_cards_without_a_chapters_line():
    tl = build(_script(), _voices(), settings.DEFAULTS)
    assert [c["title"] for c in tl.chapters] == ["Intro", "Owl", "Crow"]
