from crcontent.pacing import auto_keywords
from crcontent.script import Scene


def test_numbers_with_their_unit_come_first():
    assert auto_keywords("This lizard can live for 400 years in the desert.", "horned lizard desert") == ["400", "years"]


def test_names_mid_sentence_and_the_spoken_subject():
    assert auto_keywords("The Texas horned lizard squirts blood.", "horned lizard") == ["texas", "horned"]
    assert auto_keywords("Its eyes can squirt blood.", "lizard blood") == ["blood"]


def test_the_script_hit_words_beat_punchy_ones_and_filler_never_counts():
    assert auto_keywords("It smashes the shell and then it wins.", "", ["wins"]) == ["wins", "smashes"]
    assert auto_keywords("It is what it is.", "") == []


def test_a_new_scene_picks_them_but_a_cleared_list_stays_cleared():
    s = Scene(narration="A cheetah hits 100 km/h.", visual_query="cheetah running")
    assert s.keywords == ["100", "km/h"]
    assert Scene(narration="A cheetah hits 100 km/h.", visual_query="x", keywords=[]).keywords == []
    assert Scene(narration="x", visual_query="x", keywords=["Horned Lizard,"]).keywords == ["horned", "lizard"]


def test_the_transcript_auto_pick_endpoint():
    from fastapi.testclient import TestClient
    from crcontent.web import app

    r = TestClient(app).post("/api/keywords/auto", json={"scenes": [
        {"narration": "It lives 400 years.", "visual_query": "tortoise"}, {"narration": "", "visual_query": "x"}]})
    assert r.json() == {"keywords": [["400", "years"], []]}
