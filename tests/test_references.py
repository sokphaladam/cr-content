from crcontent import references, shot_footage
from crcontent.director_plan import Scene, Shot

SCRIPT = """Octopus facts
Hook: Octopuses have three hearts.
Reference: BBC Earth octopus hunting
Body: They taste with their arms. https://example.com/arm.jpg
Ending: Follow for more.

References
https://youtube.com/watch?v=abc
"""


class Plan:
    def __init__(self):
        self.scenes = [Scene(id="s1", narration="Octopuses have three hearts."),
                       Scene(id="s2", narration="They taste with their arms."),
                       Scene(id="s3", narration="Follow for more.")]


def test_references_go_to_their_scene_and_the_block_to_all():
    plan = Plan()
    references.attach(plan, SCRIPT)
    yt = "https://youtube.com/watch?v=abc"
    assert plan.scenes[0].references == ["BBC Earth octopus hunting", yt]
    assert plan.scenes[1].references == ["https://example.com/arm.jpg", yt]
    assert plan.scenes[2].references == [yt]


def test_strip_keeps_only_the_voiceover():
    text = references.strip(SCRIPT)
    assert "Reference" not in text and "http" not in text and "youtube" not in text
    assert "They taste with their arms." in text and "Follow for more." in text


def test_a_matching_reference_beats_stock(monkeypatch, tmp_path):
    pic = tmp_path / "ref.jpg"
    pic.write_bytes(b"x")
    monkeypatch.setattr(references, "fetch", lambda ref, log=print: pic)
    monkeypatch.setattr(shot_footage, "look", lambda *a, **k: {"subject": 9, "action": 9, "quality": 8, "problem": ""})
    shot = Shot(id="s1-a", scene_id="s1", subject="octopus")
    got = shot_footage.from_references(shot, ["BBC Earth octopus"], True, None, False, [], print)
    assert got[0].source == "reference" and got[0].rights == "rights_unknown" and got[0].match in ("exact", "good")
