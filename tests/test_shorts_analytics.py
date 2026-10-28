import pytest

from crcontent.longform.parse import Scene, Script
from crcontent.shorts import analytics, judge, plan

STUDIO_CSV = """﻿Content,Video title,Video publish time,Duration,Views,Average percentage viewed (%),Stayed to watch (%)
Total,,,,,,
abc1,Your Cat Brought You a Dead Mouse. Here's Why 🐭,"Oct 1, 2026",42,12000,71.5,58.2
abc2,Why Your Cat Slow Blinks at You 😻 #catfacts,"Oct 3, 2026",28,9000,88.0,61.0
abc3,How Hummingbirds Survive the Night: Torpor Explained,"Oct 5, 2026",58,3000,41.0,33.5
abc4,Why Wombats Poop Cubes (The Science),"Oct 7, 2026",55,2500,44.0,35.0
abc5,This Shrimp Punches So Hard the Water BOILS 🥊,"Oct 9, 2026",24,6000,79.0,47.0
"""


def _ep(n, title, old="", first="", animal=""):
    return plan.ShortPlan(n, title, Script(title, "s", "en", [Scene(1, 0, "v", "", first)]), old_title=old,
                          animal=animal)


@pytest.fixture
def csv_file(tmp_path):
    p = tmp_path / "Table data.csv"
    p.write_text(STUDIO_CSV, encoding="utf-8")
    return p


@pytest.fixture
def offline(monkeypatch, tmp_path):
    """No Claude (tags come from the keyword rules) and the summary saved in a scratch file."""
    monkeypatch.setattr("crcontent.script.make_client", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    monkeypatch.setattr(analytics, "PATH", tmp_path / "shorts-analytics.json")


def test_reads_the_studio_export(csv_file):
    videos = analytics.read_csv(csv_file)
    assert len(videos) == 5                                   # the Total row is skipped
    v = videos[0]
    assert (v.seconds, v.views, v.viewed, v.stayed) == (42, 12000, 71.5, 58.2)


def test_matches_episodes_by_new_or_old_title(csv_file):
    videos = analytics.read_csv(csv_file)
    eps = [_ep(1, "Your Cat Brought You a Dead Mouse? DON'T Yell 🐭", "Your Cat Brought You a Dead Mouse. Here's Why 🐭",
               "Your cat just brought you a dead mouse.", "cat"),
           _ep(3, "This Shrimp Punches So Hard the Water BOILS 🥊", animal="mantis shrimp")]
    analytics.match(videos, eps)
    assert [v.ep for v in videos] == [1, None, None, None, 3]
    assert videos[0].first_line.startswith("Your cat") and videos[4].animal == "mantis shrimp"


def test_your_cat_hooks_rank_above_science_explainers(csv_file, offline):
    data = analytics.import_csv(csv_file, [])
    styles = [r["tag"] for r in data["summary"]["hook_style"]]
    assert styles.index("your cat + hidden meaning") < styles.index("science explainer")
    cat = data["summary"]["hook_style"][0]
    assert cat["tag"] == "your cat + hidden meaning" and cat["videos"] == 2
    assert cat["stayed"] == round((58.2 * 12000 + 61.0 * 9000) / 21000, 1)   # weighted by views
    assert analytics.PATH.exists()
    assert "your cat + hidden meaning" in analytics.report(data)


def test_length_buckets():
    assert [analytics.length_bucket(s) for s in (15, 24, 42, 58, 90)] == \
        ["under 20s", "20-30s", "30-45s", "45-60s", "over 60s"]


def test_judge_suggestions_follow_the_channel_numbers():
    stats = {"your cat + hidden meaning": {"stayed": 59.4, "viewed": 78.4, "videos": 2},
             "science explainer": {"stayed": 34.2, "viewed": 42.4, "videos": 2}}
    items = [{"text": "How cats hunt, explained", "style": "science explainer"},
             {"text": "A brand new style", "style": "pov / situation"},
             {"text": "That mouse means you're family", "style": "your cat + hidden meaning"}]
    ranked = judge.rank_suggestions(items, stats)
    assert [r["style"] for r in ranked] == ["your cat + hidden meaning", "science explainer", "pov / situation"]
    assert ranked[0]["stayed"] == 59.4 and ranked[0]["claude_rank"] == 3 and ranked[2]["stayed"] is None
