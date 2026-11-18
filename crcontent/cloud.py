"""Sign in with Google and sync the library with the Shorts Studio cloud (server/main.py), so it follows you to
another computer.

Sign-in: the browser opens Google's page, which comes back to this engine (/api/auth/google/callback on
127.0.0.1); the engine hands the code to the cloud server, which checks it with Google and returns our own token.
The token is kept in APP_HOME/session.json, outside the data folder, so it never syncs.

Sync: drafts, uploads, assets, campaigns, songs and the finished videos. Not .env, accounts.json or the upload
schedule: those hold keys and sign-ins, and two computers running one schedule would upload everything twice.
Each side is compared with how it looked at the last sync (APP_HOME/sync-state.json): what changed on one side
goes to the other, deletes included. A file changed on both computers is never overwritten: this computer's copy
is kept next to it as "<name>.conflict-<computer><ext>" and synced too.
"""
import base64
import hashlib
import json
import os
import platform
import secrets
import threading
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import requests

from . import locations
from .config import OUTPUT_DIR, ROOT

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
SESSION = locations.APP_HOME / "session.json"
STATE = locations.APP_HOME / "sync-state.json"
SYNCED = ("drafts", "uploads", "assets", "campaigns", "songs")  # in the data folder; videos sync as "output/..."
VIDEOS = "output"
SKIP_SUFFIXES = (".tmp", ".part", ".partial")


class CloudError(Exception):
    pass


def server() -> str:
    return os.getenv("CLOUD_URL", "").strip().rstrip("/")


def client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "").strip()


def configured() -> bool:
    return bool(server() and client_id())


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def user() -> dict | None:
    return _read(SESSION).get("user")


# ---------- Sign-in ----------

_pending: dict[str, dict] = {}
_lock = threading.Lock()


def start_sign_in(redirect_uri: str) -> str:
    """Open Google's sign-in page in the browser; /api/auth/google/callback finishes it."""
    if not configured():
        raise CloudError("Cloud sync isn't set up: add CLOUD_URL and GOOGLE_CLIENT_ID to .env.")
    state, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    with _lock:
        _pending.clear()  # a new attempt replaces an abandoned one
        _pending[state] = {"verifier": verifier, "redirect_uri": redirect_uri}
    url = GOOGLE_AUTH + "?" + urlencode({
        "client_id": client_id(), "redirect_uri": redirect_uri, "response_type": "code", "scope": "openid email profile",
        "state": state, "code_challenge": challenge, "code_challenge_method": "S256", "prompt": "select_account"})
    try:
        webbrowser.open(url)
    except Exception:
        pass  # the UI shows the link as well
    return url


def finish_sign_in(state: str, code: str) -> dict:
    with _lock:
        pending = _pending.pop(state, None)
    if not pending:
        raise CloudError("This sign-in link has expired. Go back to Shorts Studio and sign in again.")
    try:
        r = requests.post(f"{server()}/auth/google", timeout=30, json={
            "code": code, "verifier": pending["verifier"], "redirect_uri": pending["redirect_uri"],
            "device": platform.node()[:200]})
    except requests.RequestException:
        raise CloudError(f"Can't reach the cloud server at {server()}. Start it, then sign in again.")
    data = _reply(r)
    old = user()
    if old and old.get("email") != data["user"]["email"]:
        STATE.unlink(missing_ok=True)  # another account: nothing here has been synced with it yet
    _write(SESSION, {"token": data["token"], "user": data["user"]})
    return data["user"]


def sign_out() -> None:
    token = _read(SESSION).get("token")
    if token:
        try:
            requests.post(f"{server()}/auth/logout", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        except requests.RequestException:
            pass  # signed out here either way; the server's session expires by itself
    SESSION.unlink(missing_ok=True)


def _reply(r: requests.Response) -> dict:
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code == 401:
        SESSION.unlink(missing_ok=True)
    if r.status_code >= 400:
        raise CloudError(data.get("detail") or f"The cloud server answered {r.status_code}.")
    return data


def _api(method: str, path: str, **kw) -> dict:
    token = _read(SESSION).get("token")
    if not token:
        raise CloudError("Sign in with Google first.")
    try:
        r = requests.request(method, f"{server()}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=60, **kw)
    except requests.RequestException as e:
        raise CloudError(f"Can't reach the cloud server ({type(e).__name__}).")
    return _reply(r)


# ---------- Sync ----------

def plan(local: dict, remote: dict, base: dict) -> list[tuple[str, str]]:
    """What to do with each path, from its sha256 here, in the cloud and at the last sync (missing = no file)."""
    actions = []
    for p in sorted(set(local) | set(remote) | set(base)):
        l, r, b = local.get(p), remote.get(p), base.get(p)
        if l == r:
            continue
        if r == b:  # only this computer changed it
            actions.append(("upload" if l else "delete_remote", p))
        elif l == b:  # only the cloud changed it
            actions.append(("download" if r else "delete_local", p))
        elif l is None:  # deleted here, changed there: keep the change
            actions.append(("download", p))
        elif r is None:
            actions.append(("upload", p))
        else:
            actions.append(("conflict", p))
    return actions


def _roots() -> dict[str, Path]:
    return {**{name: ROOT / name for name in SYNCED}, VIDEOS: OUTPUT_DIR}


def _local_path(path: str) -> Path:
    top, _, rest = path.partition("/")
    base = _roots().get(top)
    target = (base / rest).resolve() if base and rest else None
    if not target or not target.is_relative_to(base.resolve()):
        raise CloudError(f"Unexpected path from the cloud: {path[:80]}")
    return target


def _sha(file: Path) -> str:
    h = hashlib.sha256()
    with file.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(hashes: dict, report: bool = False) -> dict[str, str]:
    """path -> sha256 of every synced file here. `hashes` (path -> [size, mtime_ns, sha]) skips re-reading files that
    didn't change since the last scan, and is updated in place. `report`: count the files checked in `status`."""
    files = [(top, base, f) for top, base in _roots().items() if base.is_dir() for f in base.rglob("*")
             if f.is_file() and not f.name.startswith(".") and not f.name.endswith(SKIP_SUFFIXES)]
    if report:
        status.update(stage="checking", done=0, total=len(files))
    found = {}
    for top, base, f in files:
        if report:
            if _stop.is_set():
                raise _Stopped
            status["done"] += 1
        path = f"{top}/{f.relative_to(base).as_posix()}"
        st = f.stat()
        known = hashes.get(path)
        if not (known and known[0] == st.st_size and known[1] == st.st_mtime_ns):
            known = hashes[path] = [st.st_size, st.st_mtime_ns, _sha(f)]
        found[path] = known[2]
    for gone in set(hashes) - set(found):
        del hashes[gone]
    return found


def _upload(path: str, sha: str) -> None:
    file = _local_path(path)
    size = file.stat().st_size
    url = _api("POST", "/files/upload", json={"path": path, "sha256": sha, "size": size})["url"]
    with file.open("rb") as f:
        r = requests.put(url, data=f, timeout=(30, 600))
    if r.status_code >= 400:
        raise CloudError(f"Uploading {path} failed ({r.status_code}).")
    _api("POST", "/files/commit", json={"path": path, "sha256": sha, "size": size})


def _download(path: str) -> None:
    file = _local_path(path)
    url = _api("POST", "/files/download", json={"path": path})["url"]
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp = file.with_name(file.name + ".part")  # never leave half a file where the real one goes
    with requests.get(url, stream=True, timeout=(30, 600)) as r:
        if r.status_code >= 400:
            raise CloudError(f"Downloading {path} failed ({r.status_code}).")
        with tmp.open("wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    os.replace(tmp, file)


def _conflict_name(path: str) -> str:
    stem, dot, ext = path.rpartition(".")
    if not dot or "/" in ext:
        stem, ext = path, ""
    tag = f"conflict-{(platform.node() or 'pc').split('.')[0]}-{datetime.now():%Y%m%d-%H%M%S}"
    return f"{stem}.{tag}.{ext}" if ext else f"{stem}.{tag}"


class _Stopped(Exception):
    pass


_stop = threading.Event()
status = {"running": False, "last": "", "error": "", "summary": "", "stage": "", "done": 0, "total": 0}  # stage checking|syncing, done/total files


def sync() -> dict:
    """One full sync. Returns what was done; each failed file is retried by the next sync."""
    state = _read(STATE)
    if state.get("root") != str(ROOT):  # another data folder: compare from scratch (no deletes, only conflicts)
        state = {"root": str(ROOT)}
    base, hashes = state.get("files", {}), state.get("hashes", {})
    remote = {f["path"]: f["sha256"] for f in _api("GET", "/files")["files"]}
    try:
        local = scan(hashes, report=True)
    except _Stopped:  # keep the fingerprints made so far: the next sync skips those files
        _write(STATE, {"root": str(ROOT), "files": base, "hashes": hashes})
        return {}
    done = {"uploaded": 0, "downloaded": 0, "deleted": 0, "conflicts": 0, "failed": 0}
    new_base = {p: s for p, s in local.items() if remote.get(p) == s}
    actions = plan(local, remote, base)
    status.update(stage="syncing", done=0, total=len(actions))
    for i, (action, path) in enumerate(actions):
        if _stop.is_set():  # the rest stay as they were, so the next sync picks them up
            new_base.update({p: base[p] for _, p in actions[i:] if p in base})
            break
        status["done"] += 1  # counted as it starts, so the bar moves on the first file
        try:
            if action == "upload":
                _upload(path, local[path])
                new_base[path] = local[path]
                done["uploaded"] += 1
            elif action == "download":
                _download(path)
                new_base[path] = remote[path]
                done["downloaded"] += 1
            elif action == "delete_remote":
                _api("POST", "/files/delete", json={"path": path})
                new_base.pop(path, None)
                done["deleted"] += 1
            elif action == "delete_local":
                _local_path(path).unlink(missing_ok=True)
                new_base.pop(path, None)
                done["deleted"] += 1
            else:  # changed on both: keep ours under another name, take theirs, send ours up too
                mine = _conflict_name(path)
                os.replace(_local_path(path), _local_path(mine))
                _download(path)
                new_base[path] = remote[path]
                _upload(mine, local[path])
                new_base[mine] = local[path]
                done["conflicts"] += 1
        except CloudError as e:
            if "Sign in" in str(e) or "Signed out" in str(e):
                raise
            done["failed"] += 1
            print(f"cloud sync: {action} {path}: {e}")
            if path in base:
                new_base[path] = base[path]  # unchanged knowledge: the next sync tries again
        except OSError as e:
            done["failed"] += 1
            print(f"cloud sync: {action} {path}: {e}")
    scan(hashes)  # pick up what was downloaded, so the next sync doesn't hash it again
    _write(STATE, {"root": str(ROOT), "files": new_base, "hashes": hashes})
    return done


def _summary(done: dict) -> str:
    parts = [f"{n} {k}" for k, n in done.items() if n]
    return ", ".join(parts) if parts else "Everything is up to date"


def stop_sync() -> None:
    """Stop the running sync after the file it is on (a file is never left half sent)."""
    if status["running"]:
        _stop.set()
        status["stage"] = "stopping"


def sync_in_background() -> bool:
    """Start a sync unless one is running. False when one already was."""
    with _lock:
        if status["running"]:
            return False
        status.update(running=True, error="", stage="", done=0, total=0)
        _stop.clear()

    def run():
        try:
            done = sync()
            stopped = _stop.is_set()
            status["summary"] = (f"Stopped ({_summary(done)})" if any(done.values()) else "Stopped") if stopped else _summary(done)
        except Exception as e:
            if not isinstance(e, CloudError):
                traceback.print_exc()
            status["error"] = str(e)
        finally:
            status.update(running=False, last=datetime.now().isoformat(timespec="seconds"))

    threading.Thread(target=run, daemon=True).start()
    return True
