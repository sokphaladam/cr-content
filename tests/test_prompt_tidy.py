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
