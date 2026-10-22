import openpyxl

from crcontent.sheet import pick_episodes
from crcontent.shorts import plan


def _workbook(path, with_plan=True):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Scripts"
    ws.append(["Ep", "Time", "Visual", "On-screen Text", "Voiceover"])
    ws.append([1, "TITLE", "Cat Gifts Explained #cats", None, None])
    ws.append([1, "0–2s", "Cat drops a mouse", "Your cat brought you THIS? 🐭", "Your cat just brought you a mouse."])
    ws.append([1, "2–5s", "Owner shocked", "Don't yell ❌", "(Gasp sound) Before you scream, listen."])
    ws.append([1, "5–9s", "Cat close-up", "Stay calm", "So one day, your cat will bring you—  [loops to start]"])
    ws.append([2, "TITLE", "Bird Title", None, None])
    ws.append([2, "0–2s", "Bird hanging", "Is it dead?", "This bird almost dies [loops] every night."])
    ws.append([2, "later", "Bird flying", "", "It wakes up."])
    if with_plan:
        p = wb.create_sheet("Plan")
        p.append(["Ep", "Posting order", "Old title", "New title", "Hook (first 2s)", "Description + hashtags",
                  "Pinned comment"])
        p.append([1, "1st", "Old Cat Title #shorts", "New Cat Title 🐭 #catfacts", "Cat drops gift",
                  "Why cats bring mice.\n#catfacts #cats #shorts", "What did yours bring? 👇"])
        p.append(["Rules for every Short", None, None, None, None, None, None])
    wb.save(path)
    return path


def test_episodes_titles_and_hashtags(tmp_path):
    eps = plan.read(_workbook(tmp_path / "Jackdaw Plan.xlsx"))
    assert [e.ep for e in eps] == [1, 2]
    cat, bird = eps
    assert cat.title == "New Cat Title 🐭"                      # no hashtags in the title
    assert cat.hashtags == ["catfacts", "cats", "shorts"]        # the title's tag joins the description's, once
    assert cat.description == "Why cats bring mice."
    assert cat.pinned_comment == "What did yours bring? 👇"
    assert cat.hook_idea == "Cat drops gift"
    assert cat.old_title == "Old Cat Title"
    assert bird.title == "Bird Title"                            # no Plan row: the TITLE row
    assert cat.script.slug == "jackdaw-plan-ep01"


def test_beats_skip_title_rows_and_strip_cues_and_loop_marker(tmp_path):
    cat = plan.read(_workbook(tmp_path / "p.xlsx"))[0]
    s = cat.script.scenes
    assert len(s) == 3 and [x.n for x in s] == [1, 2, 3]
    assert s[0].text == "Your cat brought you THIS? 🐭"
    assert s[1].voiceover == "Before you scream, listen."
    assert s[2].voiceover == "So one day, your cat will bring you—"
    assert cat.loop_marked
    assert [x.planned for x in s] == [0, 2, 5] and cat.planned_ends == [2, 5, 9]


def test_misplaced_loop_marker_and_missing_time_are_noted(tmp_path):
    bird = plan.read(_workbook(tmp_path / "p.xlsx"))[1]
    assert not bird.loop_marked
    assert any("isn't the last beat" in n for n in bird.notes)
    assert any("no time span" in n for n in bird.notes)
    assert bird.planned_ends == [2, 5]


def test_without_a_plan_sheet(tmp_path):
    cat = plan.read(_workbook(tmp_path / "p.xlsx", with_plan=False))[0]
    assert cat.title == "Cat Gifts Explained" and cat.hashtags == ["cats"]


def test_round_trip_and_episode_picking(tmp_path):
    eps = plan.read(_workbook(tmp_path / "p.xlsx"))
    eps[0].save(tmp_path / "ep.json")
    back = plan.ShortPlan.load(tmp_path / "ep.json")
    assert back.title == eps[0].title and back.script.scenes == eps[0].script.scenes
    assert [e.ep for e in pick_episodes(eps, "2")] == [2]
    assert len(pick_episodes(eps)) == 2


def test_split_hashtags_keeps_text_and_order():
    assert plan.split_hashtags("Fact one #a #b\n#a #c") == ("Fact one", ["a", "b", "c"])
    assert plan.split_hashtags("No tags & #1 fan")[1] == ["1"]
