from crcontent.longform import cards, footage
from crcontent.longform.extras import _attributions, credits
from crcontent.longform.parse import Scene, Script


def _item(source, kind="photo", n=0, **kw):
    return {"source": source, "kind": kind, "id": n, "width": 1920, **kw}


def test_graphic_and_montage_scenes_are_told_apart_without_claude():
    assert footage.local_kind(Scene(1, 0, "Channel logo sting", "", "")) == "graphic"
    assert footage.local_kind(Scene(2, 0, "Split screen: Monet painting vs Picasso painting", "", "")) == "graphic"
    assert footage.local_kind(Scene(3, 0, "Recap montage of all 10 birds", "", "")) == "montage"
    assert footage.local_kind(Scene(4, 0, "Green heron standing at pond edge", "", "")) == "footage"
    assert footage.local_card(Scene(5, 0, "End screen with two video slots", "", ""))["style"] == "end"


def test_checks_are_spread_across_libraries():
    got = footage.spread([_item("pixabay", n=1), _item("pixabay", n=2), _item("inaturalist", n=3),
                          _item("commons", n=4)])
    assert [(m["source"], m["id"]) for m in got] == [("pixabay", 1), ("inaturalist", 3), ("commons", 4),
                                                     ("pixabay", 2)]


def test_rank_puts_long_enough_video_first_and_archive_clips_count_as_long_enough():
    sources = ["archive", "nasa", "commons"]
    short = _item("nasa", "video", duration=3)
    archive = _item("archive", "video")  # cut to the scene's length: no duration
    photo = _item("commons")
    got = sorted([photo, short, archive], key=lambda m: footage.rank(m, sources, 1920, 8.0))
    assert got == [archive, short, photo]


def test_a_card_for_a_graphic_scene_is_not_flagged_but_a_fallback_card_is():
    entry = {"subject": "", "query": "crowds watching tv", "kind": "graphic",
             "chosen": {"source": "card", "kind": "photo"}}
    assert footage.flags(entry, 5.0, (1920, 1080)) == []
    entry["kind"] = "archival"
    assert "nothing found really shows crowds watching tv" in footage.flags(entry, 5.0, (1920, 1080))[0]


def test_title_card_scenes_get_an_empty_card():
    scene = Scene(1, 0, "Kea in the mountains", "#5 KEA", "", rank=5, name="KEA")
    assert footage.plan_card({"card": {"style": "headline", "title": "Kea", "items": []}}, scene)["title"] == ""


def test_cards_draw_every_style(tmp_path):
    for style in cards.STYLES:
        out = cards.draw({"style": style, "title": "Brain power", "items": ["Parrot", "Monkey", "Crow"]},
                         tmp_path / f"{style}.png", (640, 360))
        assert out.exists() and out.stat().st_size > 0


def test_credits_name_the_new_libraries():
    script = Script("Moon", "moon", "en", [Scene(1, 0, "v", "", "")])
    entries = [{"scene": 1, "chosen": {"source": "inaturalist", "kind": "photo", "author": "A. Birder",
                                       "licence": "CC BY 4.0", "page": "https://www.inaturalist.org/observations/1",
                                       "licence_url": "", "file": "x.jpg"}},
               {"scene": 2, "chosen": {"source": "archive", "kind": "video", "author": "Internet Archive",
                                       "licence": "Public domain (Internet Archive)", "page": "p", "licence_url": "",
                                       "file": "y.mp4"}},
               {"scene": 3, "chosen": {"source": "card", "kind": "photo", "file": "card-03.png"}}]
    text = credits(script, entries, [])
    assert "on iNaturalist, CC BY 4.0" in text and "graphic card (made by the app)" in text
    lines = _attributions(entries)
    assert lines[0].startswith("Photo: A. Birder, CC BY 4.0, via iNaturalist")
    assert "Internet Archive" in lines[1]
