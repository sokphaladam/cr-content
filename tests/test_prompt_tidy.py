from crcontent.imagegen import _tidy, full_prompt

IDEA = ("the young man on a rooftop on the left, the young woman by a window on the right, and one big glowing moon in "
        "the center. Make it in 16:9 at high resolution, and keep a clean version with no title text, so you can add "
        "the text separately in editing.")


def test_delivery_instructions_are_dropped_and_the_two_people_counted():
    assert _tidy(IDEA) == ("1boy, 1girl, the young man on a rooftop on the left, the young woman by a window on the "
                           "right, one big glowing moon in the center")


def test_tag_prompts_are_left_alone():
    tags = "1girl, solo, long black hair, holding a radio, simple background, red background"
    assert _tidy(tags) == tags
    assert "plain background" in full_prompt(tags, "anime")


ROOFTOPS = ("Wide 16:9 shot of 1 young man and 1 young woman on different rooftops at night looking up to the full "
            "moon, calm empty dark space in the center for lyrics, soft lavender and peach palette, cinematic "
            "dreamy hopeful atmosphere.")


def test_a_frame_shape_inside_the_subject_does_not_remove_the_subject():
    # "16:9" sat in the same phrase as the two people: the whole phrase used to be dropped, so only a moon was drawn
    out = _tidy(ROOFTOPS)
    assert "young man" in out and "young woman" in out and "rooftops" in out and "16:9" not in out
    assert out.startswith("1boy, 1girl,")
    assert "no humans" not in full_prompt(ROOFTOPS, "anime")


def test_shape_words_come_out_of_a_part_and_empty_parts_go():
    assert _tidy("Cinematic still frame for a poster, 16:9: wide night sky") == (
        "Cinematic still frame for a poster, wide night sky")
    assert _tidy("A river at dusk, 4K, ultra high resolution, calm") == "A river at dusk, calm"


def test_empty_space_for_the_lyrics_does_not_ask_for_writing():
    # "...empty dark space in the center for lyrics" made the model write gibberish captions into the sky
    out = _tidy("1boy, 1girl, rooftop at night, calm empty dark space in the center for lyrics, no text")
    assert "lyrics" not in out and "calm empty dark space in the center" in out


def test_sentences_are_told_from_tags():
    from crcontent.imagegen import looks_like_prose

    assert looks_like_prose(ROOFTOPS)
    assert not looks_like_prose("1girl, solo, long black hair, holding a radio, simple background, red background")


def test_anime_tags_leaves_tags_alone_and_remembers_a_conversion(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from crcontent import imagegen, script

    monkeypatch.setattr(imagegen, "GEN_CACHE", tmp_path)
    tags = "1girl, solo, long black hair, holding a radio"
    assert imagegen.anime_tags(tags) == tags
    calls = []

    class Client:
        class beta:
            class messages:
                @staticmethod
                def create(**kw):
                    calls.append(kw)
                    block = SimpleNamespace(type="text", text='{"tags": "1boy, 1girl, rooftop, night, full moon, wide shot"}')
                    return SimpleNamespace(content=[block])

    monkeypatch.setattr(script, "make_client", lambda: Client)
    assert imagegen.anime_tags(ROOFTOPS) == "1boy, 1girl, rooftop, night, full moon, wide shot"
    assert imagegen.anime_tags(ROOFTOPS) == "1boy, 1girl, rooftop, night, full moon, wide shot" and len(calls) == 1
