"""Stopping a sync keeps what was done, so the next sync continues instead of starting over or seeing conflicts."""
import threading

from crcontent import cloud


def setup(tmp_path, monkeypatch, remote):
    root = tmp_path / "drafts"
    root.mkdir()
    for n in "abc":
        (root / f"{n}.txt").write_text(n)
    monkeypatch.setattr(cloud, "_roots", lambda: {"drafts": root})
    monkeypatch.setattr(cloud, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(cloud, "_api", lambda *a, **k: {"files": remote})
    monkeypatch.setattr(cloud, "_stop", threading.Event())  # a fresh flag, not left set for other tests


def test_stop_while_checking_keeps_fingerprints(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, [])
    real = cloud._sha
    monkeypatch.setattr(cloud, "_sha", lambda f: (cloud._stop.set(), real(f))[1])  # stop after the first file
    assert cloud.sync() == {}
    assert len(cloud._read(cloud.STATE)["hashes"]) == 1


def test_stop_while_sending_keeps_the_rest_for_next_time(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, [])
    sent = []
    monkeypatch.setattr(cloud, "_upload", lambda path, sha: (sent.append(path), cloud._stop.set()))
    done = cloud.sync()
    assert sent == ["drafts/a.txt"] and done["uploaded"] == 1
    files = cloud._read(cloud.STATE)["files"]
    assert list(files) == ["drafts/a.txt"]  # b and c are still "new here": the next sync uploads them
