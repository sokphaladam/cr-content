from crcontent import packaging
from crcontent.packaging import _seconds, find_outliers, fluff_opening


def test_fluff_found():
    assert fluff_opening("Hey guys, welcome back to my channel! In this video we rank owls.") == [
        "a greeting", "\"welcome back\"", "\"in this video\""]
    assert fluff_opening("So today we're going to talk about birds") == ["\"today we're going to...\""]
    assert fluff_opening("Don't forget to subscribe before we start") == ["\"before we start\"", "a subscribe request"]
    assert fluff_opening("សួស្តី ថ្ងៃនេះ យើង នឹង និយាយ") == ["a greeting", "\"today we're going to...\""]


def test_payoff_first_is_clean():
    assert fluff_opening("If your cat sleeps like THIS, it trusts you completely.") == []
    assert fluff_opening("Crows remember your face for years. Here's how.") == []


def test_fluff_only_in_the_opening():
    late = " ".join(["word"] * 40) + " don't forget to subscribe"
    assert fluff_opening(late) == []


def test_iso_duration():
    assert _seconds("PT1H2M3S") == 3723
    assert _seconds("PT45S") == 45
    assert _seconds("P1DT1S") == 86401
    assert _seconds("") == 0


def test_outliers_keep_high_ratio(monkeypatch):
    def fake(path, params):
        if path == "search":
            return {"items": [{"id": {"videoId": v}} for v in ("a", "b", "c", "d")]}
        if path == "videos":
            def item(v, ch, views):
                return {"id": v, "snippet": {"channelId": ch, "title": v.upper(), "channelTitle": ch,
                                             "publishedAt": "2026-05-01T00:00:00Z", "thumbnails": {}},
                        "statistics": {"viewCount": str(views)}, "contentDetails": {"duration": "PT50S"}}
            return {"items": [item("a", "small", 200_000), item("b", "big", 200_000), item("c", "hidden", 900_000),
                              item("d", "small", 5_000)]}
        return {"items": [{"id": "small", "statistics": {"subscriberCount": "10000"}},
                          {"id": "big", "statistics": {"subscriberCount": "1000000"}},
                          {"id": "hidden", "statistics": {"hiddenSubscriberCount": True}}]}

    monkeypatch.setattr(packaging, "_youtube_get", fake)
    found = find_outliers("owls")
    assert [o["id"] for o in found] == ["a"]  # b: 0.2 views/sub, c: subs hidden, d: too few views
    assert found[0]["ratio"] == 20.0 and found[0]["seconds"] == 50
