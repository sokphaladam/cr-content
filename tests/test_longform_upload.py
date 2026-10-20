from pathlib import Path

import pytest

SAMPLE = Path(__file__).resolve().parent.parent / "scripts" / "smartest-birds.md"


@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from crcontent import web

    monkeypatch.setattr(web, "LONG_SCRIPTS", tmp_path / "scripts")
    started = []
    monkeypatch.setattr(web.renderer, "submit", lambda fn, *args: started.append((fn.__name__, args)))
    c = TestClient(web.app)
    c.started = started
    return c


def test_script_upload_starts_the_storyboard(client, tmp_path):
    r = client.post("/api/longform", files={"file": ("smartest-birds.md", SAMPLE.read_bytes(), "text/markdown")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scenes"] > 10 and body["title"]
    assert client.started == [("_run_storyboard", (body["id"], tmp_path / "scripts" / "smartest-birds.md"))]
    assert (tmp_path / "scripts" / "smartest-birds.md").read_bytes() == SAMPLE.read_bytes()


def test_wrong_file_type(client):
    r = client.post("/api/longform", files={"file": ("plan.xlsx", b"PK\x03\x04", "application/octet-stream")})
    assert r.status_code == 400 and ".md" in r.json()["detail"]
    assert client.started == []


def test_script_without_scenes(client):
    r = client.post("/api/longform", files={"file": ("notes.md", b"# Just notes\n\nNo table here.\n", "text/markdown")})
    assert r.status_code == 400 and "Time | Visual | On-screen Text | Voiceover" in r.json()["detail"]
    assert client.started == []


def test_file_name_cannot_escape_the_scripts_folder(client, tmp_path):
    r = client.post("/api/longform", files={"file": ("../../evil.md", SAMPLE.read_bytes(), "text/markdown")})
    assert r.status_code == 200
    assert (tmp_path / "scripts" / "evil.md").exists()
