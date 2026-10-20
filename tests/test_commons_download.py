import pytest

from crcontent import commons


class _Response:
    def __init__(self, status, headers=None):
        self.status_code, self.headers = status, headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"{self.status_code}")

    def iter_content(self, size):
        yield b"jpeg bytes"


def _setup(monkeypatch, tmp_path, answers):
    monkeypatch.setattr(commons, "CACHE", tmp_path)
    monkeypatch.setattr(commons, "_next_at", 0.0)
    slept = []
    monkeypatch.setattr(commons.time, "sleep", lambda s: slept.append(s))
    calls = iter(answers)
    monkeypatch.setattr(commons.requests, "get", lambda *a, **k: next(calls))
    return slept


def test_a_429_is_waited_out_and_retried(monkeypatch, tmp_path):
    slept = _setup(monkeypatch, tmp_path, [_Response(429, {"retry-after": "5"}), _Response(200)])
    path = commons.download({"url": "https://upload.wikimedia.org/a.jpg", "title": "a"})
    assert path.read_bytes() == b"jpeg bytes"
    assert slept and 4 <= slept[0] <= 5


def test_a_429_asking_for_a_long_wait_fails_fast(monkeypatch, tmp_path):
    slept = _setup(monkeypatch, tmp_path, [_Response(429, {"retry-after": "600"})])
    with pytest.raises(ValueError, match="asked to wait"):
        commons.download({"url": "https://upload.wikimedia.org/b.jpg", "title": "b"})
    assert not slept  # never sits out ten minutes: the scene tries its other libraries instead
