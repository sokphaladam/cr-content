"""Cloud sign-in and sync: the server (on SQLite, with storage in memory) and two computers syncing through it."""
import base64
import importlib
import io
import json

import pytest

pytest.importorskip("sqlalchemy")
from fastapi.testclient import TestClient  # noqa: E402

from crcontent import cloud  # noqa: E402


def test_plan():
    a, b, c = "a" * 64, "b" * 64, "c" * 64
    assert cloud.plan({"x": a}, {}, {}) == [("upload", "x")]
    assert cloud.plan({}, {"x": a}, {}) == [("download", "x")]
    assert cloud.plan({"x": b}, {"x": a}, {"x": a}) == [("upload", "x")]
    assert cloud.plan({"x": a}, {"x": b}, {"x": a}) == [("download", "x")]
    assert cloud.plan({}, {"x": a}, {"x": a}) == [("delete_remote", "x")]
    assert cloud.plan({"x": a}, {}, {"x": a}) == [("delete_local", "x")]
    assert cloud.plan({"x": b}, {"x": c}, {"x": a}) == [("conflict", "x")]
    assert cloud.plan({}, {"x": c}, {"x": a}) == [("download", "x")]  # an edit beats a delete
    assert cloud.plan({"x": b}, {}, {"x": a}) == [("upload", "x")]
    assert cloud.plan({"x": a}, {"x": a}, {}) == []


class MemoryStorage:
    def __init__(self):
        self.blobs = {}

    def upload_url(self, key):
        return f"mem://{key}"

    def download_url(self, key):
        return f"mem://{key}"

    def size(self, key):
        return len(self.blobs[key]) if key in self.blobs else None

    def delete(self, key):
        self.blobs.pop(key, None)


def _id_token(sub, email, aud):
    body = base64.urlsafe_b64encode(json.dumps(
        {"sub": sub, "email": email, "email_verified": True, "aud": aud, "iss": "https://accounts.google.com"}).encode())
    return f"x.{body.decode().rstrip('=')}.y"


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cloud.db'}")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    import server.main as main

    main = importlib.reload(main)
    main.storage = MemoryStorage()

    class GoogleReply:
        status_code = 200

        def __init__(self, sub):
            self.text = json.dumps({"id_token": _id_token(sub, f"{sub}@example.com", "client")})

        def json(self):
            return json.loads(self.text)

    monkeypatch.setattr(main.requests, "post", lambda url, data, timeout: GoogleReply(data["code"]))
    return main, TestClient(main.app)


def _sign_in(client, who):
    r = client.post("/auth/google", json={"code": who, "verifier": "v", "redirect_uri": "http://127.0.0.1:9/cb"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_users_only_see_their_own_files(server):
    main, client = server
    alice, bob = _sign_in(client, "alice"), _sign_in(client, "bob")
    sha = "a" * 64
    main.storage.blobs["users/alice/drafts/a.json"] = b"hi"
    assert client.post("/files/commit", headers=alice, json={"path": "drafts/a.json", "sha256": sha, "size": 2}).status_code == 200
    assert [f["path"] for f in client.get("/files", headers=alice).json()["files"]] == ["drafts/a.json"]
    assert client.get("/files", headers=bob).json()["files"] == []
    assert client.post("/files/download", headers=bob, json={"path": "drafts/a.json"}).status_code == 404
    assert client.post("/files/delete", headers=bob, json={"path": "drafts/a.json"}).status_code == 404
    assert client.get("/files").status_code == 401
    for bad in ("../x", "/etc/passwd", "drafts/../../x", "a\\b"):
        assert client.post("/files/upload", headers=alice, json={"path": bad, "sha256": sha, "size": 1}).status_code == 400
    # a commit for a file that never reached storage isn't recorded
    assert client.post("/files/commit", headers=alice, json={"path": "drafts/b.json", "sha256": sha, "size": 2}).status_code == 409
    client.post("/auth/logout", headers=alice)
    assert client.get("/me", headers=alice).status_code == 401


def test_two_computers_sync(server, tmp_path, monkeypatch):
    main, client = server
    headers = _sign_in(client, "alice")

    def api(method, path, **kw):
        r = client.request(method, path, headers=headers, **kw)
        assert r.status_code < 400, r.text
        return r.json()

    class Get(io.BytesIO):
        status_code = 200

        def iter_content(self, n):
            return iter([self.getvalue()])

    def put(url, data, timeout):
        main.storage.blobs[url.removeprefix("mem://")] = data.read()
        return Get()

    monkeypatch.setattr(cloud, "_api", api)
    monkeypatch.setattr(cloud.requests, "put", put)
    monkeypatch.setattr(cloud.requests, "get", lambda url, stream, timeout: Get(main.storage.blobs[url.removeprefix("mem://")]))

    def computer(name):
        root = tmp_path / name
        for d in (*cloud.SYNCED, "output"):
            (root / d).mkdir(parents=True)
        return root

    pc1, pc2 = computer("pc1"), computer("pc2")

    def sync_on(root):
        monkeypatch.setattr(cloud, "ROOT", root)
        monkeypatch.setattr(cloud, "OUTPUT_DIR", root / "output")
        monkeypatch.setattr(cloud, "STATE", root.parent / f"{root.name}-state.json")
        return cloud.sync()

    (pc1 / "drafts" / "d1").mkdir()
    (pc1 / "drafts" / "d1" / "script.json").write_text("v1")
    (pc1 / "output" / "video.mp4").write_bytes(b"\x00video")
    (pc1 / ".env").write_text("SECRET=1")  # never synced
    assert sync_on(pc1)["uploaded"] == 2
    assert sync_on(pc2)["downloaded"] == 2
    assert (pc2 / "drafts" / "d1" / "script.json").read_text() == "v1"
    assert (pc2 / "output" / "video.mp4").read_bytes() == b"\x00video"
    assert not (pc2 / ".env").exists()
    assert sync_on(pc2) == {"uploaded": 0, "downloaded": 0, "deleted": 0, "conflicts": 0, "failed": 0}

    # an edit on one computer and a delete on the other both travel
    (pc2 / "drafts" / "d1" / "script.json").write_text("v2")
    (pc2 / "output" / "video.mp4").unlink()
    sync_on(pc2)
    sync_on(pc1)
    assert (pc1 / "drafts" / "d1" / "script.json").read_text() == "v2"
    assert not (pc1 / "output" / "video.mp4").exists()

    # changed on both: neither copy is lost
    (pc1 / "drafts" / "d1" / "script.json").write_text("from pc1")
    (pc2 / "drafts" / "d1" / "script.json").write_text("from pc2")
    sync_on(pc1)
    assert sync_on(pc2)["conflicts"] == 1
    sync_on(pc1)
    for pc in (pc1, pc2):
        texts = sorted(f.read_text() for f in (pc / "drafts" / "d1").iterdir())
        assert texts == ["from pc1", "from pc2"], pc
