"""Without Gemini, a plain finished script (no "Voiceover:" labels) still imports: one scene per line, word for word."""
import pytest

from crcontent.importer import import_script, parse_basic

RAVEN = """Ravens Make Tools

This bird just solved a puzzle that stumps most animals.
In the wild, ravens bend twigs into hooks to pull food out of cracks.
They even remember which humans treated them well, and which did not.
"""


def test_plain_script_keeps_title_and_narration_word_for_word():
    script, lang, method = import_script(RAVEN, "auto", use_claude=False)
    assert (lang, method) == ("en", "basic")
    assert script.title == "Ravens Make Tools"
    assert [s.narration for s in script.scenes] == RAVEN.strip().splitlines()[2:]
    assert all(s.visual_query.startswith("ravens") for s in script.scenes)  # the subject from the title
    assert script.scenes[2].visual_query == "ravens remember humans"


def test_a_long_paragraph_splits_at_sentence_ends():
    para = " ".join(f"Sentence number {i} has a few more words in it to make it long enough." for i in range(6))
    script = parse_basic(para)
    assert script.title == "Imported script"  # a first line ending in a full stop is narration, not a title
    assert len(script.scenes) > 1
    assert " ".join(s.narration for s in script.scenes) == para
    assert all(len(s.narration.split()) <= 30 for s in script.scenes)


def test_labelled_scripts_parse_as_before():
    script = parse_basic("Title: Owls\nVoiceover: Owls fly silently.\nVisual: owl flying at night\n")
    assert script.title == "Owls" and script.scenes[0].narration == "Owls fly silently."
    assert script.scenes[0].visual_query == "owl flying night"


def test_nothing_to_say_still_fails():
    with pytest.raises(ValueError):
        parse_basic("---\n***\n")
