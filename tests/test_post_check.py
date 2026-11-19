from crcontent.post import check_post

GOOD_DESC = ("Nine hikers left a warm tent in -30°C, barefoot, in the dark.\n"
             "Searchers found the canvas slashed open from the inside.\n"
             "The answer took sixty years to settle.\n"
             "What would make you run into a blizzard?")
TAGS = ["history", "dyatlovpass", "mystery", "coldcase"]


def test_vidiq_ranking_holds():
    # vidIQ (2026-11-20): 98 vs 89; the local check must order them the same way
    best, _ = check_post("What Happened When 9 Hikers Fled Their Tent At Night 😳", GOOD_DESC, TAGS)
    worse, issues = check_post("What Made 9 Hikers Cut Their Way Out Of Their Tent 😱", GOOD_DESC, TAGS)
    assert best >= 90 > worse
    assert any("cause" in i for i in issues)


def test_description_rules():
    score, issues = check_post("What Happened When 9 Hikers Fled Their Tent At Night 😳",
                               "Short one. #fyp", ["fyp"])
    assert score < 90
    assert any("characters" in i for i in issues) and any("question" in i for i in issues)
    assert any("dead tags" in i for i in issues)
