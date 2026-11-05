"""Mixkit (read from its tag pages) and Unsplash beside Pexels/Pixabay; offline: requests is faked."""
from crcontent import visuals

CARD = ('<div data-item-grid--video-player-item-id-value="{id}" x>'
        '<img src="t.jpg" alt="White cat &amp; dog." width="460" height="{h}" loading="lazy">'
        '<span class="item-grid-video-player__overlay-video-title">\n Cat on grass\n</span>'
        '<a href="/free-stock-video/white-cat-{id}/" class="x">')


class Resp:
    def __init__(self, text="", status=200):
        self.text, self.status_code = text, status

    def raise_for_status(self):
        pass


def test_mixkit_drops_words_until_a_tag_page_has_clips(monkeypatch):
    asked = []

    def get(url, **_):
        asked.append(url.split("/")[-2])
        return Resp(CARD.format(id=7, h=259) + CARD.format(id=8, h=818) if url.endswith("/cat/") else "No results")

    monkeypatch.setattr(visuals.requests, "get", get)
    monkeypatch.setattr(visuals.requests, "head", lambda url, **_: Resp(status=403 if "2160" in url else 200))
    got = visuals.mixkit_search("Cat drinking water", 1080, portrait=True)
    assert asked == ["cat-drinking-water", "cat-drinking", "cat"]
    landscape, tall = got
    # a landscape clip can't fill a 9:16 frame at 1080 and 2160 is missing: the biggest it has
    assert (landscape["id"], landscape["width"], landscape["height"]) == (7, 1918, 1080)
    assert landscape["url"].endswith("/7-1080.mp4") and landscape["page"].endswith("/white-cat-7/")
    assert (tall["width"], tall["height"]) == (1080, 1921) and tall["url"].endswith("/8-1080.mp4")  # 720 is too soft
    assert "white cat & dog." in tall["tags"] and "cat on grass" in tall["tags"]


def test_manual_search_mixes_the_libraries(monkeypatch):
    monkeypatch.setenv("PIXABAY_API_KEY", "k")
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    monkeypatch.setattr(visuals, "_pixabay_search", lambda *a: [{"source": "pixabay", "id": i} for i in (1, 2, 3)])
    monkeypatch.setattr(visuals, "mixkit_search", lambda *a: [{"source": "mixkit", "id": 9}])
    assert [(r["source"], r["id"]) for r in visuals.search("cat")] == \
        [("pixabay", 1), ("mixkit", 9), ("pixabay", 2), ("pixabay", 3)]


def test_unsplash_ids_are_checked_before_any_request():
    import pytest

    with pytest.raises(ValueError):
        visuals._unsplash_download("../../etc")
