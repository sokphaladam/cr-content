import json
import os
from datetime import datetime, timedelta

from crcontent.shorts import footage, judge, match, preflight, queries
from crcontent.shorts.registry import Registry


# ---------- the match score ----------

def test_a_clip_without_the_key_objects_scores_at_most_five():
    dry = {"score": 9, "objects_seen": ["sofa"], "animal": True}
    assert match.capped(dry, ["water"])["score"] == match.GENERIC_MAX
    assert match.capped(dry, ["water"])["missing"] == ["water"]
    wet = {"score": 8, "objects_seen": ["running water", "tap"], "animal": True}
    assert match.capped(wet, ["water", "tap"])["score"] == 8
    assert match.capped({"score": 9, "objects_seen": [], "animal": True}, [])["score"] == 9  # the animal is the shot
    assert match.capped({"score": 9, "objects_seen": ["water"], "animal": False}, ["water"])["score"] == 0


# ---------- the searches ----------

def test_queries_are_short_and_always_name_the_animal():
    p = queries._clean({"beat": 3, "shot": "soaked cat", "queries": ["Wet cat", "bath time", "wet cat",
                                                                       "soaked fur dripping water close"],
                        "key_objects": [" Water ", ""], "reuse_opening": False}, "cat")
    assert p["queries"] == ["wet cat", "cat bath time", "cat soaked fur dripping water"]
    assert p["key_objects"] == ["water"]


# ---------- the registry ----------

def _short(root, name, slug, ep, picks, rendered_days_ago=None, created_days_ago=1):
    job = root / name
    (job / "storyboard").mkdir(parents=True)
    when = datetime.now() - timedelta(days=created_days_ago)
    (job / "meta.json").write_text(json.dumps({"kind": "short", "ep": ep, "created": when.isoformat()}))
    (job / "episode.json").write_text(json.dumps({"script": {"slug": slug}}))
    (job / "footage.json").write_text(json.dumps([
        {"scene": n, "chosen": {"source": "pixabay", "kind": "video", "id": i}} for n, i in enumerate(picks, 1)]))
    if rendered_days_ago is not None:
        video = job / "video.mp4"
        video.write_bytes(b"x")
        t = (datetime.now() - timedelta(days=rendered_days_ago)).timestamp()
        os.utime(video, (t, t))


def test_registry_rules(tmp_path):
    _short(tmp_path, "a", "plan-ep01", 1, [161726, 65438], rendered_days_ago=30)   # an old Short
    _short(tmp_path, "b", "plan-ep02", 2, [11, 22], created_days_ago=2)             # pending, recent
    _short(tmp_path, "c", "plan-ep07", 7, [33, 44], created_days_ago=1)             # an earlier version of Ep 7
    reg = Registry(tmp_path, "plan-ep07")
    clip = lambda i: {"source": "pixabay", "kind": "video", "id": i}
    assert "Ep 1 hook" in reg.hook_block(clip(161726))       # never a hook again, however old
    assert reg.hook_block(clip(22))                           # used anywhere: not a hook
    assert reg.hook_block(clip(33)) == ""                     # the same episode's other version doesn't count
    assert reg.recent(clip(65438)) == []                      # 30 days ago: free for other beats
    assert [u.ep for u in reg.recent(clip(22))] == [2]        # 2 days ago: kept for last


# ---------- the picker ----------

class FakePicker(footage.Picker):
    """A Picker with canned search results and match scores (no network, no Claude)."""

    def __init__(self, results, scores, sources=("pixabay", "pexels")):
        self.results, self.scores = results, scores
        self.sources, self.skipped_sources = list(sources), []
        self.width = 1080
        self.reg = type("R", (), {"hook_block": lambda s, m: "", "recent": lambda s, m: []})()
        self.lock = __import__("threading").Lock()
        self.taken = set()
        self.animal_words, self.filtered = {"cat", "cats"}, 0
        self.log = lambda m: None
        self.tried = []

    def try_clip(self, item, plan, length, is_hook, query, source):
        self.tried.append((query, source, item["id"]))
        score = self.scores.get(item["id"], 3)
        return {"query": query, "source": source, "key": f"{source}-video-{item['id']}", "page": "", "score": score,
                "seen": "", "missing": [], "reject": "", "_pick": {**item, "file": f"{item['id']}.mp4"}}


def _results(monkeypatch, table, tags=None):
    monkeypatch.setattr(footage.lf, "search",
                        lambda q, sources, *a, **k: [{"source": sources[0], "kind": "video", "id": i,
                                                      "tags": (tags or {}).get(i, "cat, pet")}
                                                     for i in table.get((q, sources[0]), [])])


def test_searches_go_in_order_and_stop_at_the_first_match(monkeypatch):
    _results(monkeypatch, {("cat bath", "pixabay"): [1, 2], ("cat bath", "pexels"): [3],
                           ("wet cat", "pixabay"): [4, 5], ("cat faucet", "pixabay"): [6]})
    p = FakePicker({}, {1: 4, 2: 5, 3: 6, 4: 8, 5: 9, 6: 10})
    log = {"attempts": [], "skipped": [], "deferred": []}
    best = p.search({"queries": ["cat bath", "wet cat", "cat faucet"], "shot": "wet cat", "key_objects": ["water"]},
                    3.0, False, footage.CHECKS, log)
    assert best["score"] == 8 and best["query"] == "wet cat"
    assert p.tried == [("cat bath", "pixabay", 1), ("cat bath", "pixabay", 2), ("cat bath", "pexels", 3),
                       ("wet cat", "pixabay", 4)]                       # Pixabay before Pexels, stops at 8/10
    assert len(log["attempts"]) == 4
    assert p.taken == {"pixabay-video-4"}                               # the others are free for other beats


def test_the_check_budget_caps_a_beat(monkeypatch):
    _results(monkeypatch, {(f"cat q{k}", "pixabay"): [10 * k + 1, 10 * k + 2, 10 * k + 3] for k in range(6)})
    p = FakePicker({}, {})
    log = {"attempts": [], "skipped": [], "deferred": []}
    best = p.search({"queries": [f"cat q{k}" for k in range(6)], "shot": "x", "key_objects": []}, 3.0, False, 5, log)
    assert len(p.tried) == 5 and best["score"] == 3


# ---------- the loop and the status ----------

def test_a_loop_that_repeats_itself_fails():
    assert judge.echoes("because one day, your cat will bring you—", "Your cat just brought you a dead mouse.") == \
        ["cat"]
    assert judge.echoes("the scariest thing in your house is…", "Water. Most cats hate it, but why?") == []


def _report(checks_ok=True, score=7):
    return {"checks": [{"check": "length", "ok": True, "detail": ""},
                       {"check": "shot match", "ok": checks_ok, "detail": "beat 3 5/10"}],
            "judge": {"score": score} if score is not None else None}


def test_ready_only_when_everything_passes():
    assert preflight.status(_report())["state"] == "ready"
    low = preflight.status(_report(score=5))
    assert low["state"] == "needs work" and "hook judge 5/10" in low["reasons"][0]
    assert preflight.status(_report(checks_ok=False))["state"] == "needs work"
    assert preflight.status(_report(score=None))["state"] == "not judged"


def test_weak_beats_are_the_ones_under_seven():
    entries = [{"scene": 1, "match": 8, "chosen": {"source": "pixabay"}},
               {"scene": 2, "match": 5, "chosen": {"source": "pixabay"}},
               {"scene": 3, "match": None, "chosen": {"source": "own"}},
               {"scene": 4, "match": 0, "chosen": {"source": "card"}}]
    assert footage.weak(entries) == [2, 4]


def test_results_not_tagged_with_the_animal_are_never_downloaded(monkeypatch):
    _results(monkeypatch, {("wet cat", "pixabay"): [1, 2, 3]}, tags={1: "rain, water, drops", 2: "waterfall, jungle"})
    p = FakePicker({}, {3: 8})
    log = {"attempts": [], "skipped": [], "deferred": []}
    best = p.search({"queries": ["wet cat"], "shot": "wet cat", "key_objects": ["water"]}, 3.0, False, 12, log)
    assert [t[2] for t in p.tried] == [3] and best["score"] == 8 and p.filtered == 2


def test_tags_match_any_word_the_animal_goes_by():
    assert footage.tagged({"tags": "kittens, milk, glass"}, {"cat", "cats", "kitten", "kittens"})
    assert not footage.tagged({"tags": "rooster, hen, farm"}, {"cat", "cats"})
    assert footage.tagged({"source": "commons"}, {"cat"})  # no tags at all: can't tell, so it's checked
