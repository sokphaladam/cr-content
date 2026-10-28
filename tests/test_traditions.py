from neonmekong import traditions


def test_a_tradition_puts_its_traits_first_and_plain_anime_changes_nothing():
    assert traditions.apply("1boy, rooftop", "") == "1boy, rooftop"
    out = traditions.apply("1boy, rooftop", "ghibli")
    assert out.startswith("hand-painted background") and out.endswith("1boy, rooftop")
    assert traditions.pick("bogus") == "" and traditions.avoid("bogus") == ""
    assert "neon" in traditions.avoid("ghibli")


def test_suggestion_follows_the_mood():
    assert traditions.suggest({"mood_phrase": "Chill lofi study beats"}) == "lofi"
    assert traditions.suggest({"genre": "synthwave", "mood_phrase": "neon night drive"}) == "citypop"
    assert traditions.suggest({"mood_phrase": "Dreamy Psych Pop"}) == "ghibli"
    assert traditions.suggest({"mood_phrase": "heavy metal"}) == ""


def test_the_plan_carries_the_traditions_for_the_page(tmp_path, monkeypatch):
    from crcontent import lyricvideo as web
    (tmp_path / "song.json").write_text('{"title": "T", "mood_phrase": "lofi chill"}', encoding="utf-8")
    (tmp_path / "pictures.json").write_text('{"slots": [{"id": "s1", "start": 0, "end": 5, "kind": "verse"}], '
                                            '"tradition": "citypop"}', encoding="utf-8")
    out = web._pictures(tmp_path)
    assert out["tradition"] == "citypop" and out["tradition_suggested"] == "lofi" and "ghibli" in out["traditions"]


def test_the_users_own_style_goes_first_and_is_kept_short():
    out = traditions.apply("1girl, rooftop", "custom", "oil painting,\n thick brush strokes ")
    assert out == "oil painting, thick brush strokes, 1girl, rooftop"
    assert traditions.avoid("custom", "neon, 3d") == "neon, 3d" and traditions.avoid("ghibli", "x") != "x"
    assert len(traditions.clean("a" * 500)) == traditions.MAX_CUSTOM
    assert traditions.apply("p", "custom", "") == "p" and traditions.pick("custom") == "custom"
    assert "custom" in traditions.catalog() and traditions.suggest({"mood_phrase": "oil"}) != "custom"
