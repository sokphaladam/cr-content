from crcontent.captions import build_ass
from crcontent.config import LANGS
from crcontent.tts import Word


def test_first_scene_voiceover_is_captioned_under_the_hook():
    ass = build_ass([(0.0, 2.0, [Word("hello", 0.1, 0.5)], "Big hook")], LANGS["en"])
    assert ",Caption,," in ass and "hello" in ass.lower()
