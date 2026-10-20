"""Upload finished videos to your YouTube channels (one or several), TikTok account, Facebook Page and Instagram account.

Each platform uses your own developer app (its keys are entered in the app) and OAuth: "Connect" opens the browser on the platform's
sign-in page, which redirects back to a small listener on http://127.0.0.1:<PUBLISH_CALLBACK_PORT>/callback.
Facebook and Instagram share one Meta app and one sign-in (Facebook Login): it gives the Pages you manage and the
Instagram professional accounts linked to them; both upload with the Page's token, which doesn't expire.
App keys, tokens and auto-upload settings are kept in <ROOT>/accounts.json; what was uploaded where in each video's
published.json.
"""
import base64
import hashlib
import json
import os
import re
import secrets
import subprocess
import threading
import time
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from .config import ROOT

PLATFORMS = ("youtube", "tiktok", "facebook", "instagram")
META = ("facebook", "instagram")  # one Meta developer app and one sign-in for both
ACCOUNTS_FILE = ROOT / "accounts.json"
CALLBACK_PORT = int(os.getenv("PUBLISH_CALLBACK_PORT", "8765"))
REDIRECT_URI = f"http://127.0.0.1:{CALLBACK_PORT}/callback"
TIKTOK_REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback/"  # TikTok's desktop Login Kit wants localhost

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
YOUTUBE_API = "https://www.googleapis.com/youtube/v3"
YOUTUBE_UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"
# force-ssl lets the app post the video's fact-check comment (comments can't be pinned through the API)
COMMENT_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
YOUTUBE_SCOPES = f"https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly {COMMENT_SCOPE}"
COMMENT_DELAY_MIN = 3  # after a scheduled video goes public
COMMENT_RETRIES = 3
# the categories a video can be uploaded to (YouTube's ids, the same in every region)
YT_CATEGORIES = {
    "1": "Film & Animation", "2": "Autos & Vehicles", "10": "Music", "15": "Pets & Animals", "17": "Sports",
    "19": "Travel & Events", "20": "Gaming", "22": "People & Blogs", "23": "Comedy", "24": "Entertainment",
    "25": "News & Politics", "26": "Howto & Style", "27": "Education", "28": "Science & Technology",
    "29": "Nonprofits & Activism",
}

# Meta (Facebook Login). Facebook allows http://localhost redirects while the app is in development mode, which is
# all a personal app needs: its own admins can grant the permissions without App Review.
META_REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback/"
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v25.0")
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
META_AUTH = f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth"
# Pages (list, post Reels and videos) and the Instagram accounts linked to them (publish Reels); business_management
# lists Pages owned by a business portfolio too
META_SCOPES = ("pages_show_list,pages_read_engagement,pages_manage_posts,business_management,"
               "instagram_basic,instagram_content_publish")
FB_REEL_MAX_SEC = 90  # longer (or landscape) videos go to the Page as regular videos
# Facebook publishes a scheduled post itself (the app needn't run then): at least 10 minutes ahead, at most ~a month
FB_SCHEDULE_MIN = timedelta(minutes=10)
FB_SCHEDULE_MAX = timedelta(days=28)
IG_CAPTION_MAX, IG_HASHTAGS_MAX = 2200, 30

TIKTOK_AUTH = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_API = "https://open.tiktokapis.com/v2"

# auto-upload timing: "now" = as soon as a render finishes; "slots" = at the next free time of day in `times`
DEFAULT_SETTINGS = {
    # privacy: public | unlisted | private; comment: post the video's pinned comment (fact check) after upload;
    # category: a YT_CATEGORIES id, or "auto" (Music for music videos, People & Blogs otherwise)
    # channel: the default channel's id (uploads without a chosen channel, auto and scheduled uploads); "" = the first
    "youtube": {"auto": False, "privacy": "public", "when": "now", "times": ["09:00", "18:00"], "comment": True,
                "category": "auto", "channel": ""},
    # direct: posts straight to the profile (an app TikTok hasn't audited may only post SELF_ONLY);
    # draft: lands in the TikTok app's inbox, where you add sounds and post it yourself
    "tiktok": {"auto": False, "privacy": "PUBLIC_TO_EVERYONE", "mode": "direct", "when": "now", "times": ["12:00", "19:00"]},
    # Reels on Pages and Instagram are always public. page / account_id: the default Page or Instagram account id ("" =
    # the first); share_to_feed: an Instagram Reel also shows in the profile's main grid
    "facebook": {"auto": False, "privacy": "public", "when": "now", "times": ["11:00", "20:00"], "page": ""},
    "instagram": {"auto": False, "privacy": "public", "when": "now", "times": ["11:00", "20:00"], "account_id": "",
                  "share_to_feed": True},
}

_lock = threading.Lock()
_pending: dict[str, dict] = {}  # OAuth state -> {platform, verifier}
_server: HTTPServer | None = None


class PublishError(RuntimeError):
    pass


# ---------- Stored accounts and settings ----------

def _load() -> dict:
    try:
        data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    # Before several channels could be connected, the one YouTube account was kept under "youtube"
    old = data.pop("youtube", None)
    if old and old.get("refresh_token"):
        channels = data.setdefault("youtube_channels", [])
        if not any(c.get("channel_id") == old.get("channel_id") for c in channels):
            channels.insert(0, old)
    return data


def _channels(data: dict) -> list[dict]:
    """The connected YouTube channels, in the order they were connected."""
    return [c for c in data.get("youtube_channels", []) if c.get("refresh_token")]


def _channel(data: dict, channel: str | None = None) -> dict | None:
    """A connected YouTube channel: the one with id `channel`, else the default (Settings), else the first.
    None when `channel` is given but isn't connected (any more)."""
    channels = _channels(data)
    if channel:
        return next((c for c in channels if c.get("channel_id") == channel), None)
    default = data.get("settings", {}).get("youtube", {}).get("channel", "")
    return next((c for c in channels if c.get("channel_id") == default), None) or (channels[0] if channels else None)


def _pages(data: dict) -> list[dict]:
    """The Facebook Pages the Meta sign-in gave (each with its token and linked Instagram account, if any)."""
    return [p for p in (data.get("meta") or {}).get("pages", []) if p.get("token")]


def _meta_account(data: dict, platform: str, choice: str | None = None) -> dict | None:
    """The Page (facebook) or Instagram account (instagram) to post as: the one with id `choice`, else the default
    in Settings, else the first. As {id, name, token, page_id}; None when there's none (or `choice` is gone)."""
    if platform == "facebook":
        found = [{"id": p["id"], "name": p["name"], "token": p["token"], "page_id": p["id"]} for p in _pages(data)]
    else:
        found = [{"id": p["ig"]["id"], "name": f"@{p['ig'].get('username', '')}", "token": p["token"], "page_id": p["id"]}
                 for p in _pages(data) if p.get("ig")]
    if choice:
        return next((a for a in found if a["id"] == choice), None)
    default = data.get("settings", {}).get(platform, {}).get("page" if platform == "facebook" else "account_id", "")
    return next((a for a in found if a["id"] == default), None) or (found[0] if found else None)


def _app_key(platform: str) -> str:
    """Where a platform's developer app keys are kept: Facebook and Instagram share the Meta app."""
    return "meta" if platform in META else platform


def _account(data: dict, platform: str, channel: str | None = None) -> dict | None:
    """The signed-in account to use: a YouTube channel (see _channel), a Page / Instagram account (_meta_account),
    or the TikTok account."""
    if platform == "youtube":
        return _channel(data, channel)
    if platform in META:
        return _meta_account(data, platform, channel)
    acct = data.get(platform)
    return acct if acct and acct.get("refresh_token") else None


def _save(data: dict) -> None:
    ACCOUNTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


ENV_KEYS = {"youtube": ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET"),
            "tiktok": ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET")}


def _import_env_keys() -> None:
    """Once: keys an earlier version read from .env move into the app's settings, where they're edited from now on."""
    with _lock:
        data = _load()
        if data.get("env_imported"):
            return
        apps = data.setdefault("apps", {})
        for p, (id_name, secret_name) in ENV_KEYS.items():
            client_id, secret = os.getenv(id_name, "").strip(), os.getenv(secret_name, "").strip()
            if client_id and secret and p not in apps:
                apps[p] = {"client_id": client_id, "client_secret": secret}
        data["env_imported"] = True
        _save(data)


try:
    _import_env_keys()  # the engine loads .env before importing this module
except OSError:
    pass


def _creds(platform: str) -> tuple[str, str]:
    """The developer app's client ID (TikTok: client key; Meta: app ID) and secret, as entered in the app."""
    app = _load().get("apps", {}).get(_app_key(platform)) or {}
    return app.get("client_id", ""), app.get("client_secret", "")


def set_app(platform: str, client_id: str, client_secret: str) -> None:
    """Save the developer app keys typed in the app ("" for both removes them). A different app can't use the
    old sign-in, so changing the client ID disconnects the account."""
    client_id, client_secret = client_id.strip(), client_secret.strip()
    key = _app_key(platform)
    with _lock:
        data = _load()
        apps = data.setdefault("apps", {})
        old = (apps.get(key) or {}).get("client_id", "")
        if client_id:
            if not client_secret:  # keep the saved secret when only the ID is edited
                client_secret = (apps.get(key) or {}).get("client_secret", "")
            if not client_secret:
                raise PublishError("Enter the client secret too.")
            apps[key] = {"client_id": client_id, "client_secret": client_secret}
        else:
            apps.pop(key, None)
        if client_id != old:
            data.pop("youtube_channels" if platform == "youtube" else key, None)
        _save(data)


def settings() -> dict:
    saved = _load().get("settings", {})
    return {p: {**DEFAULT_SETTINGS[p], **saved.get(p, {})} for p in PLATFORMS}


def update_settings(platform: str, changes: dict) -> dict:
    allowed = {"youtube": {"auto": (True, False), "privacy": ("public", "unlisted", "private"), "comment": (True, False),
                           "category": ("auto", *YT_CATEGORIES)},
               "tiktok": {"auto": (True, False), "mode": ("direct", "draft"),
                          "privacy": ("PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "SELF_ONLY")},
               "facebook": {"auto": (True, False)},
               "instagram": {"auto": (True, False), "share_to_feed": (True, False)}}
    with _lock:
        data = _load()
        current = data.setdefault("settings", {}).setdefault(platform, {})
        for key, value in changes.items():
            if key == "times" and isinstance(value, list):
                times = sorted({t for t in value if isinstance(t, str) and re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", t)})
                if times:
                    current["times"] = times[:12]
            elif key == "when" and value in ("now", "slots"):
                current["when"] = value
            elif key == "channel" and platform == "youtube" and _channel(data, value):
                current["channel"] = value
            elif key == "page" and platform == "facebook" and _meta_account(data, "facebook", value):
                current["page"] = value
            elif key == "account_id" and platform == "instagram" and _meta_account(data, "instagram", value):
                current["account_id"] = value
            elif key in allowed[platform] and value in allowed[platform][key]:
                current[key] = value
        _save(data)
    return settings()


def status() -> dict:
    """Per platform: whether its keys are set, the connected account and the settings (never secrets or tokens)."""
    data, prefs = _load(), settings()
    out = {}
    for p in PLATFORMS:
        acct = _account(data, p) or {}  # YouTube: the default channel
        client_id, _ = _creds(p)
        out[p] = {"configured": all(_creds(p)), "client_id": client_id, "connected": bool(acct),
                  "account": acct.get("name", ""),
                  "connecting": any(v["platform"] in (p, _app_key(p)) for v in _pending.values()), **prefs[p]}
        if p == "youtube":  # connections made before comments were added need to be made again
            out[p]["can_comment"] = COMMENT_SCOPE in acct.get("scope", "")
            out[p]["channel"] = acct.get("channel_id", "")
            out[p]["channels"] = [{"id": c.get("channel_id", ""), "name": c.get("name", ""),
                                   "can_comment": COMMENT_SCOPE in c.get("scope", "")} for c in _channels(data)]
        if p == "facebook":
            out[p]["page"] = acct.get("id", "")
            out[p]["pages"] = [{"id": pg["id"], "name": pg["name"]} for pg in _pages(data)]
        if p == "instagram":
            out[p]["account_id"] = acct.get("id", "")
            out[p]["accounts"] = [{"id": pg["ig"]["id"], "name": f"@{pg['ig'].get('username', '')}", "page": pg["name"]}
                                  for pg in _pages(data) if pg.get("ig")]
            # signed in, but none of the Pages has an Instagram professional account linked
            out[p]["no_linked_account"] = bool(_pages(data)) and not acct
    out["redirect_uri"] = {"youtube": REDIRECT_URI, "tiktok": TIKTOK_REDIRECT_URI, "facebook": META_REDIRECT_URI,
                           "instagram": META_REDIRECT_URI}
    out["youtube_categories"] = YT_CATEGORIES
    return out


def disconnect(platform: str, channel: str = "") -> None:
    """Forget the account; for YouTube only the channel `channel` when it's given, else every channel."""
    with _lock:
        data = _load()
        if platform == "youtube":
            data["youtube_channels"] = [c for c in data.get("youtube_channels", [])
                                        if channel and c.get("channel_id") != channel]
            prefs = data.get("settings", {}).get("youtube", {})
            if not channel or prefs.get("channel") == channel:
                prefs.pop("channel", None)  # the default goes back to the first channel left
        elif platform in META:  # one sign-in for both
            data.pop("meta", None)
            for p in META:
                data.get("settings", {}).get(p, {}).pop("page" if p == "facebook" else "account_id", None)
        else:
            data.pop(platform, None)
        _save(data)


def connected(platform: str, channel: str | None = None) -> bool:
    return _account(_load(), platform, channel) is not None


def channel_name(channel: str | None = None) -> str:
    """The YouTube channel's name (the default channel when `channel` is empty)."""
    return (_channel(_load(), channel) or {}).get("name", "")


# ---------- OAuth ----------

def start_connect(platform: str) -> str:
    """Open the platform's sign-in page in the browser; the callback listener finishes the connection."""
    client_id, secret = _creds(platform)
    if not client_id or not secret:
        raise PublishError("Enter your developer app's client ID and secret first.")
    _ensure_server()
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(64)[:96]
    digest = hashlib.sha256(verifier.encode()).digest()
    key = _app_key(platform)
    with _lock:
        for s in [s for s, v in _pending.items() if v["platform"] == key]:
            del _pending[s]  # a new attempt replaces an abandoned one
        _pending[state] = {"platform": key, "verifier": verifier}
    if key == "meta":
        url = META_AUTH + "?" + urlencode({
            "client_id": client_id, "redirect_uri": META_REDIRECT_URI, "response_type": "code", "scope": META_SCOPES,
            "state": state})
    elif platform == "youtube":
        url = GOOGLE_AUTH + "?" + urlencode({
            "client_id": client_id, "redirect_uri": REDIRECT_URI, "response_type": "code", "scope": YOUTUBE_SCOPES,
            "access_type": "offline", "prompt": "consent", "state": state,
            "code_challenge": base64.urlsafe_b64encode(digest).rstrip(b"=").decode(), "code_challenge_method": "S256"})
    else:
        scopes = os.getenv("TIKTOK_SCOPES", "user.info.basic,video.publish,video.upload")
        url = TIKTOK_AUTH + "?" + urlencode({
            "client_key": client_id, "redirect_uri": TIKTOK_REDIRECT_URI, "response_type": "code", "scope": scopes,
            "state": state, "code_challenge": digest.hex(), "code_challenge_method": "S256"})  # TikTok desktop: hex
    try:
        webbrowser.open(url)
    except Exception:
        pass  # the UI shows the link as well
    return url


def _finish_connect(platform: str, code: str, verifier: str) -> str:
    if platform == "meta":
        return _finish_meta(code)
    client_id, secret = _creds(platform)
    if platform == "youtube":
        r = requests.post(GOOGLE_TOKEN, data={
            "client_id": client_id, "client_secret": secret, "code": code, "code_verifier": verifier,
            "grant_type": "authorization_code", "redirect_uri": REDIRECT_URI}, timeout=30)
        tok = _json(r, "Google sign-in")
        if not tok.get("refresh_token"):
            raise PublishError("Google didn't return a refresh token. Remove the app's access in your Google account and connect again.")
        account = {"access_token": tok["access_token"], "refresh_token": tok["refresh_token"],
                   "expires": time.time() + tok.get("expires_in", 3600) - 60, "scope": tok.get("scope", "")}
        ch = requests.get(f"{YOUTUBE_API}/channels", params={"part": "snippet", "mine": "true"},
                          headers={"Authorization": f"Bearer {account['access_token']}"}, timeout=30)
        items = _json(ch, "YouTube").get("items") or []
        if not items:
            raise PublishError("This Google account has no YouTube channel. Create one on youtube.com first.")
        account["name"] = items[0]["snippet"]["title"]
        account["channel_id"] = items[0]["id"]
        with _lock:  # add the channel, or renew its sign-in when it's connected already
            data = _load()
            channels = data.setdefault("youtube_channels", [])
            same = [i for i, c in enumerate(channels) if c.get("channel_id") == account["channel_id"]]
            if same:
                channels[same[0]] = account
            else:
                channels.append(account)
            _save(data)
        return account["name"]
    else:
        r = requests.post(f"{TIKTOK_API}/oauth/token/", data={
            "client_key": client_id, "client_secret": secret, "code": code, "code_verifier": verifier,
            "grant_type": "authorization_code", "redirect_uri": TIKTOK_REDIRECT_URI}, timeout=30)
        tok = _json(r, "TikTok sign-in")
        if "access_token" not in tok:
            raise PublishError(f"TikTok sign-in failed: {tok.get('error_description') or tok.get('error') or tok}")
        account = {"access_token": tok["access_token"], "refresh_token": tok["refresh_token"],
                   "expires": time.time() + tok.get("expires_in", 86400) - 60, "open_id": tok.get("open_id", ""),
                   "scope": tok.get("scope", "")}
        info = requests.get(f"{TIKTOK_API}/user/info/", params={"fields": "display_name"},
                            headers={"Authorization": f"Bearer {account['access_token']}"}, timeout=30)
        account["name"] = (_json(info, "TikTok").get("data", {}).get("user", {}).get("display_name") or "TikTok account")
    with _lock:
        data = _load()
        data[platform] = account
        _save(data)
    return account["name"]


def _finish_meta(code: str) -> str:
    """Facebook Login: the code becomes a long-lived user token, which lists the Pages you manage with their tokens
    (those don't expire) and the Instagram professional account linked to each."""
    client_id, secret = _creds("facebook")
    r = requests.get(f"{GRAPH}/oauth/access_token", timeout=30, params={
        "client_id": client_id, "client_secret": secret, "redirect_uri": META_REDIRECT_URI, "code": code})
    short = _meta_json(r, "Facebook sign-in").get("access_token", "")
    r = requests.get(f"{GRAPH}/oauth/access_token", timeout=30, params={
        "grant_type": "fb_exchange_token", "client_id": client_id, "client_secret": secret, "fb_exchange_token": short})
    user_token = _meta_json(r, "Facebook sign-in").get("access_token", "")
    if not user_token:
        raise PublishError("Facebook didn't return a sign-in token. Try connecting again.")
    pages, url = [], f"{GRAPH}/me/accounts"
    params = {"fields": "id,name,access_token,instagram_business_account{id,username}", "limit": 100,
              "access_token": user_token}
    while url and len(pages) < 500:
        data = _meta_json(requests.get(url, params=params, timeout=30), "Facebook Pages")
        for p in data.get("data", []):
            ig = p.get("instagram_business_account") or None
            pages.append({"id": p["id"], "name": p.get("name", ""), "token": p.get("access_token", ""),
                          "ig": {"id": ig["id"], "username": ig.get("username", "")} if ig else None})
        url, params = (data.get("paging") or {}).get("next"), None  # the next link carries its own parameters
    pages = [p for p in pages if p["token"]]
    if not pages:
        raise PublishError("No Facebook Pages came back. Facebook and Instagram uploads go through a Page: when signing "
                           "in, pick the Pages (and Instagram accounts) to share, or create a Page and link your "
                           "Instagram professional account to it, then connect again.")
    with _lock:
        data = _load()
        data["meta"] = {"pages": pages, "connected": datetime.now().isoformat(timespec="seconds")}
        _save(data)
    names = ", ".join(p["name"] for p in pages[:3]) + ("…" if len(pages) > 3 else "")
    ig = [f"@{p['ig']['username']}" for p in pages if p["ig"]]
    return names + (f" (Instagram: {', '.join(ig[:3])})" if ig else " (no Instagram account linked to these Pages)")


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        q = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
        with _lock:
            pending = _pending.pop(q.get("state", ""), None)
        if not urlparse(self.path).path.startswith("/callback") or not pending:
            return self._page(404, "This sign-in link has expired. Go back to Shorts Studio and press Connect again.")
        name = {"youtube": "YouTube", "tiktok": "TikTok", "meta": "Facebook and Instagram"}[pending["platform"]]
        if "code" not in q:
            return self._page(400, f"{name} wasn't connected: {q.get('error_description') or q.get('error') or 'cancelled'}.")
        try:
            account = _finish_connect(pending["platform"], q["code"], pending["verifier"])
        except Exception as e:
            return self._page(500, f"{name} wasn't connected: {e}")
        self._page(200, f"{name} is connected as {account}. You can close this tab and go back to Shorts Studio.")

    def _page(self, code: int, text: str) -> None:
        body = (f"<!doctype html><meta charset=utf-8><title>Shorts Studio</title>"
                f"<body style='font:16px system-ui;margin:15vh auto;max-width:520px;padding:0 16px'>"
                f"<p>{text.replace('<', '&lt;')}</p>").encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _ensure_server() -> None:
    global _server
    if _server:
        return
    try:
        _server = HTTPServer(("127.0.0.1", CALLBACK_PORT), _CallbackHandler)
    except OSError:
        raise PublishError(f"Port {CALLBACK_PORT} is busy, so sign-in can't come back to the app. "
                           "Set PUBLISH_CALLBACK_PORT in .env to another port (and update the redirect URI in your developer app).")
    threading.Thread(target=_server.serve_forever, daemon=True).start()


def _json(r: requests.Response, what: str) -> dict:
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400:
        err = data.get("error")
        msg = (err.get("message") if isinstance(err, dict) else None) or data.get("error_description") or err or r.text[:300]
        raise PublishError(f"{what}: {msg}")
    return data


def _meta_json(r: requests.Response, what: str) -> dict:
    """A Graph API reply, or PublishError with Meta's message (and what to do for the usual problems)."""
    try:
        data = r.json()
    except ValueError:
        data = {}
    err = data.get("error") if isinstance(data, dict) else None
    if r.status_code < 400 and not err:
        return data
    err = err if isinstance(err, dict) else {}
    code = err.get("code")
    hints = {
        190: "The Facebook sign-in has expired or was revoked. Disconnect and connect Facebook & Instagram again.",
        10: "The Meta app wasn't granted this permission. Disconnect, connect again and allow every permission asked.",
        200: "The Meta app wasn't granted this permission. Disconnect, connect again and allow every permission asked.",
        4: "Meta's rate limit for this app was reached. Try again in an hour.",
        9: "Meta's posting limit for this account was reached. Try again later.",
    }
    msg = hints.get(code) or err.get("error_user_msg") or err.get("message") or r.text[:300]
    raise PublishError(f"{what}: {msg}")


def _token(platform: str, channel: str | None = None) -> str:
    """A valid access token (YouTube: for `channel`, else the default channel), refreshed when it has expired.
    Facebook / Instagram: the Page's token (it doesn't expire; a revoked one fails with what to do)."""
    if platform in META:
        acct = _meta_account(_load(), platform, channel)
        if not acct:
            raise PublishError(f"{'Facebook' if platform == 'facebook' else 'Instagram'} isn't connected"
                               f"{' (or that account is gone)' if channel else ''}. Connect it in Settings.")
        return acct["token"]
    with _lock:
        data = _load()
        acct = _account(data, platform, channel)
        if not acct:
            raise PublishError("That YouTube channel isn't connected any more. Connect it again in Settings." if channel
                               else f"{'YouTube' if platform == 'youtube' else 'TikTok'} isn't connected.")
        if acct.get("expires", 0) > time.time():
            return acct["access_token"]
        client_id, secret = _creds(platform)
        if not client_id or not secret:
            raise PublishError("The developer app keys were removed, so the sign-in can't be renewed. Enter them again.")
        if platform == "youtube":
            r = requests.post(GOOGLE_TOKEN, data={"client_id": client_id, "client_secret": secret,
                                                  "refresh_token": acct["refresh_token"], "grant_type": "refresh_token"}, timeout=30)
        else:
            r = requests.post(f"{TIKTOK_API}/oauth/token/", data={"client_key": client_id, "client_secret": secret,
                                                                  "refresh_token": acct["refresh_token"], "grant_type": "refresh_token"}, timeout=30)
        try:
            tok = _json(r, "Refreshing the sign-in")
        except PublishError as e:
            raise PublishError(f"{str(e).rstrip('.')}. Disconnect and connect the account again.")
        if "access_token" not in tok:
            raise PublishError("The sign-in has expired. Disconnect and connect the account again.")
        acct["access_token"] = tok["access_token"]
        acct["refresh_token"] = tok.get("refresh_token") or acct["refresh_token"]
        acct["expires"] = time.time() + tok.get("expires_in", 3600) - 60
        _save(data)
        return acct["access_token"]


# ---------- Post text ----------

def post_text(job: Path) -> tuple[str, str, list[str]]:
    """(title, description, hashtags) from the video's post.txt: title line, body, then the #tags line."""
    text = (job / "post.txt").read_text(encoding="utf-8").strip() if (job / "post.txt").exists() else ""
    if not text:
        title = job.name
        for name in ("script.json", "song.json"):
            if (job / name).exists():
                title = json.loads((job / name).read_text(encoding="utf-8")).get("title", title)
                break
        return title, "", []
    title, _, body = text.partition("\n")
    lines = [l for l in body.strip().splitlines()]
    tags = [w.lstrip("#") for l in lines if l.strip().startswith("#") for w in l.split() if w.startswith("#")]
    desc = re.sub(r"\n{3,}", "\n\n", "\n".join(l for l in lines if not l.strip().startswith("#"))).strip()
    return title.strip(), desc, tags


# ---------- Uploads ----------

def published(job: Path) -> dict:
    try:
        return json.loads((job / "published.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _record(job: Path, platform: str, info: dict) -> None:
    with _lock:
        data = published(job)
        data[platform] = {**info, "at": datetime.now().isoformat(timespec="seconds")}
        (job / "published.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def upload(job: Path, platform: str, log=print, privacy: str | None = None, publish_at: datetime | None = None,
           category: str | None = None, channel: str | None = None, tiktok_post: dict | None = None) -> dict:
    """`privacy`: YouTube public | unlisted | private, or a TikTok TIKTOK_PRIVACY level / "DRAFT". `publish_at`
    (local time): YouTube and Facebook upload now and make it public then (Facebook: FB_SCHEDULE_MIN to
    FB_SCHEDULE_MAX ahead). `category` is YouTube only. `channel`: the YouTube channel, Facebook Page or Instagram account
    id to post to (default: the one chosen in Settings). `tiktok_post`: the interactions and content disclosure picked
    for a TikTok direct post (see _upload_tiktok)."""
    video = job / "video.mp4"
    if not video.exists():
        raise PublishError("This video hasn't been rendered.")
    if platform == "youtube":
        acct = _channel(_load(), channel)
        if not acct:
            raise PublishError("That YouTube channel isn't connected any more. Connect it again in Settings." if channel
                               else "YouTube isn't connected.")
        info = {**_upload_youtube(job, video, log, privacy, publish_at, category, acct["channel_id"]),
                "channel": acct["channel_id"], "channel_name": acct.get("name", "")}
        _record(job, platform, info)
        info["comment"] = _comment_after_upload(job, privacy or settings()["youtube"]["privacy"], publish_at, log,
                                                acct["channel_id"])
        return info
    if platform == "facebook":
        info = _upload_facebook(job, video, log, channel, publish_at)
    elif platform == "instagram":
        info = _upload_instagram(job, video, log, channel)
    else:
        info = _upload_tiktok(job, video, log, privacy, tiktok_post)
    _record(job, platform, info)
    return info


# ---------- The video's comment (YouTube) ----------

def _own_comment(job: Path) -> str | None:
    """The comment you wrote for this video (meta.json yt_comment), None if you haven't written one."""
    try:
        own = json.loads((job / "meta.json").read_text(encoding="utf-8")).get("yt_comment")
    except (OSError, ValueError):
        return None
    return own if isinstance(own, str) else None


def comment_text(job: Path) -> str:
    """The comment posted under the video: yours if you wrote one, else the fact-check notes from script.json."""
    own = _own_comment(job)
    if own is not None:
        return own.strip()
    try:
        return json.loads((job / "script.json").read_text(encoding="utf-8")).get("pinned_comment", "").strip()
    except (OSError, ValueError):
        return ""


COMMENT_MAX = 9000  # YouTube allows 10,000 characters


def _youtube_state(job: Path, key: str, **state) -> dict:
    """Remember how a step after the YouTube upload went, in published.json (youtube.comment / youtube.thumbnail)."""
    with _lock:
        data = published(job)
        if "youtube" in data:
            data["youtube"][key] = state
            (job / "published.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def _comment_state(job: Path, **state) -> dict:
    return _youtube_state(job, "comment", **state)


def _comment_after_upload(job: Path, privacy: str, publish_at: datetime | None, log, channel: str) -> dict:
    """Post the comment now, or queue it for when a scheduled video goes public. Never fails the upload."""
    from . import schedule

    # a comment you wrote for this video is always posted; the setting is for the automatic fact-check notes
    if not comment_text(job) or (not settings()["youtube"]["comment"] and _own_comment(job) is None):
        return {}
    if COMMENT_SCOPE not in (_channel(_load(), channel) or {}).get("scope", ""):
        log("YouTube: the comment wasn't posted: connect this channel again in Settings to allow comments.")
        return _comment_state(job, status="error", error="Connect this channel again in Settings to allow comments.")
    if publish_at:
        at = publish_at + timedelta(minutes=COMMENT_DELAY_MIN)
        schedule.add(job.name, "youtube", at, source="auto", action="comment", channel=channel)
        log(f"YouTube: the comment will be posted when the video goes public ({at:%a %d %b, %H:%M}).")
        return _comment_state(job, status="pending", at=at.isoformat(timespec="minutes"))
    if privacy == "private":
        log("YouTube: no comment: comments can't be posted on a private video.")
        return _comment_state(job, status="skipped", error="Private videos can't have comments.")
    try:
        return post_comment(job, log, channel)
    except PublishError as e:
        log(f"YouTube: the comment wasn't posted: {e}")
        return _comment_state(job, status="error", error=str(e))


def post_comment(job: Path, log=print, channel: str | None = None) -> dict:
    """Post the video's comment under its YouTube upload, as the channel it was uploaded to (`channel`, else the
    one published.json names, else the default). Pinning it is left to you (the API can't pin)."""
    record = published(job).get("youtube") or {}
    video_id = record.get("id")
    channel = channel or record.get("channel") or None
    text = comment_text(job)
    if not video_id:
        raise PublishError("This video hasn't been uploaded to YouTube.")
    if not text:
        raise PublishError("Write a comment in the box above first.")
    r = requests.post(f"{YOUTUBE_API}/commentThreads", params={"part": "snippet"}, timeout=30,
                      headers={"Authorization": f"Bearer {_token('youtube', channel)}"},
                      json={"snippet": {"videoId": video_id, "topLevelComment": {"snippet": {"textOriginal": text[:COMMENT_MAX]}}}})
    data = _json(r, "YouTube comment")
    log("YouTube: comment posted. Pin it from YouTube Studio > Comments.")
    return _comment_state(job, status="posted", id=data.get("id", ""), at=datetime.now().isoformat(timespec="seconds"))


def _is_short(job: Path) -> bool:
    try:
        meta = json.loads((job / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        meta = {}
    return meta.get("aspect", "9:16") == "9:16"


def youtube_category(job: Path, choice: str | None = None) -> str:
    """The category id for an upload: `choice`, else the Settings default; "auto" = Music for music videos and
    People & Blogs for everything else."""
    choice = choice or settings()["youtube"]["category"]
    if choice in YT_CATEGORIES:
        return choice
    try:
        kind = json.loads((job / "meta.json").read_text(encoding="utf-8")).get("kind", "")
    except (OSError, ValueError):
        kind = ""
    return "10" if kind == "music_video" or (job / "song.json").exists() else "22"


THUMBNAIL_CHOICES = ("auto", "cover", "youtube")  # auto: the cover for videos, YouTube's frame for Shorts
TAGS_MAX_CHARS = 500  # YouTube's limit for all tags together (a tag with spaces counts its quotes too)


def clean_tags(tags: list[str]) -> list[str]:
    """Tags YouTube accepts: no #, < or >, no duplicates, and within TAGS_MAX_CHARS altogether."""
    out, used = [], 0
    for tag in tags:
        tag = re.sub(r"[<>#,]", "", re.sub(r"<[^>]*>", "", str(tag))).strip()[:100]
        if not tag or tag.lower() in (t.lower() for t in out):
            continue
        cost = len(tag) + (2 if " " in tag else 0) + (1 if out else 0)
        if used + cost > TAGS_MAX_CHARS:
            break
        out.append(tag)
        used += cost
    return out


def youtube_options(job: Path) -> dict:
    """A video's YouTube tags and thumbnail choice (meta.json yt_tags / yt_thumbnail). Tags default to its hashtags."""
    try:
        meta = json.loads((job / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        meta = {}
    custom = isinstance(meta.get("yt_tags"), list)
    tags = clean_tags(meta["yt_tags"] if custom else post_text(job)[2])
    choice = meta.get("yt_thumbnail") if meta.get("yt_thumbnail") in THUMBNAIL_CHOICES else "auto"
    return {"tags": tags, "custom_tags": custom, "thumbnail": choice, "short": _is_short(job),
            "comment": comment_text(job), "custom_comment": isinstance(meta.get("yt_comment"), str)}


def set_youtube_options(job: Path, tags: list[str] | None = None, thumbnail: str | None = None,
                        reset_tags: bool = False, comment: str | None = None, reset_comment: bool = False) -> dict:
    meta_path = job / "meta.json"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        meta = {}
    if reset_tags:
        meta.pop("yt_tags", None)
    elif tags is not None:
        meta["yt_tags"] = clean_tags(tags)
    if thumbnail in THUMBNAIL_CHOICES:
        meta["yt_thumbnail"] = thumbnail
    if reset_comment:
        meta.pop("yt_comment", None)
    elif comment is not None:
        meta["yt_comment"] = comment.strip()[:COMMENT_MAX]  # "" = no comment for this video
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return youtube_options(job)


def _thumbnail_file(job: Path) -> Path | None:
    """The cover as a JPEG under YouTube's 2 MB limit (recompressed into work/ when it's bigger)."""
    thumb = job / "thumbnail.jpg"
    if not thumb.exists():
        return None
    if thumb.stat().st_size <= 2_000_000:
        return thumb
    small = job / "work" / "thumbnail_youtube.jpg"
    small.parent.mkdir(exist_ok=True)
    for quality in (4, 8, 14):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(thumb), "-vf", "scale='min(1280,iw)':-2",
                        "-q:v", str(quality), str(small)], stdin=subprocess.DEVNULL, check=True)
        if small.stat().st_size <= 2_000_000:
            return small
    return None


def _upload_youtube(job: Path, video: Path, log, privacy: str | None = None, publish_at: datetime | None = None,
                    category: str | None = None, channel: str | None = None) -> dict:
    token = _token("youtube", channel)
    title, desc, tags = post_text(job)
    options = youtube_options(job)
    short = _is_short(job)
    if short and "#shorts" not in (title + desc).lower():
        desc = (desc + "\n\n#Shorts").strip()
    if tags:
        desc = (desc + "\n\n" + " ".join(f"#{t}" for t in tags)).strip()
    # YouTube rejects < and > and titles over 100 characters
    clean = lambda s: s.replace("<", "").replace(">", "")
    body = {"snippet": {"title": clean(title)[:100] or job.name, "description": clean(desc)[:5000],
                        "tags": options["tags"], "categoryId": youtube_category(job, category)},
            "status": {"privacyStatus": privacy or settings()["youtube"]["privacy"], "selfDeclaredMadeForKids": False}}
    if publish_at:  # YouTube Studio's "Schedule": private until YouTube makes it public at that time
        body["status"].update(privacyStatus="private",
                              publishAt=publish_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    size = video.stat().st_size
    log(f"YouTube: uploading {size / 1e6:.1f} MB…")
    r = requests.post(YOUTUBE_UPLOAD, params={"uploadType": "resumable", "part": "snippet,status"}, json=body,
                      headers={"Authorization": f"Bearer {token}", "X-Upload-Content-Type": "video/mp4",
                               "X-Upload-Content-Length": str(size)}, timeout=60)
    _json(r, "YouTube")
    location = r.headers["Location"]
    with open(video, "rb") as f:
        r = requests.put(location, data=f, headers={"Content-Type": "video/mp4", "Content-Length": str(size)}, timeout=None)
    video_id = _json(r, "YouTube upload")["id"]
    # auto: the cover for regular videos; Shorts are shown with a frame YouTube picks unless "cover" is chosen
    use_cover = options["thumbnail"] == "cover" or (options["thumbnail"] == "auto" and not short)
    thumbnail = {}
    if use_cover:
        try:
            thumbnail = _send_thumbnail(job, video_id, token, log)
        except PublishError as e:
            log(f"YouTube: {e}")
            thumbnail = {"status": "error", "error": str(e)}
    url = f"https://youtube.com/shorts/{video_id}" if short else f"https://youtu.be/{video_id}"
    info = {"id": video_id, "url": url, **({"thumbnail": thumbnail} if thumbnail else {})}
    if publish_at:
        log(f"YouTube: uploaded → {url} (goes public {publish_at:%a %d %b, %H:%M})")
        return {**info, "publish_at": publish_at.isoformat(timespec="minutes")}
    log(f"YouTube: uploaded → {url}")
    return info


THUMBNAIL_FORBIDDEN = ("YouTube didn't allow a custom cover on this channel yet. Verify the channel with your phone at "
                       "youtube.com/verify, then press Set cover again.")


def _send_thumbnail(job: Path, video_id: str, token: str, log) -> dict:
    """Set the video's cover as its YouTube thumbnail. Raises PublishError with what to do when it can't."""
    thumb = _thumbnail_file(job)
    if not thumb:
        raise PublishError("The cover wasn't set: make a cover first (or it's over YouTube's 2 MB limit).")
    try:
        with open(thumb, "rb") as f:
            t = requests.post("https://www.googleapis.com/upload/youtube/v3/thumbnails/set", params={"videoId": video_id},
                              data=f, headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"}, timeout=60)
    except requests.RequestException:
        raise PublishError("The cover wasn't set (network error). Try Set cover again.")
    if t.status_code == 403:  # custom thumbnails are an "intermediate feature": the channel must be phone-verified
        raise PublishError(THUMBNAIL_FORBIDDEN)
    _json(t, "YouTube thumbnail")
    log("YouTube: thumbnail set from your cover.")
    return {"status": "set", "at": datetime.now().isoformat(timespec="seconds")}


def set_youtube_thumbnail(job: Path, log=print) -> dict:
    """Set (again) the cover of a video already on YouTube, e.g. after verifying the channel. Remembered in
    published.json (youtube.thumbnail); raises PublishError when it still can't."""
    record = published(job).get("youtube") or {}
    if not record.get("id"):
        raise PublishError("This video hasn't been uploaded to YouTube.")
    try:
        state = _send_thumbnail(job, record["id"], _token("youtube", record.get("channel") or None), log)
    except PublishError as e:
        _youtube_state(job, "thumbnail", status="error", error=str(e))
        raise
    return _youtube_state(job, "thumbnail", **state)


def _tiktok_call(path: str, token: str, body: dict) -> dict:
    r = requests.post(f"{TIKTOK_API}{path}", json=body, timeout=60,
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"})
    data = r.json() if r.content else {}
    err = data.get("error") or {}
    if r.status_code >= 400 or (err.get("code") not in (None, "ok")):
        code = err.get("code", r.status_code)
        hints = {
            "unaudited_client_can_only_post_to_private_accounts":
                "TikTok hasn't audited your developer app yet, so it can only post to a private account as 'Only me'. "
                "In the TikTok app turn on Settings and privacy → Privacy → Private account, or switch to "
                "'Send to TikTok drafts' and post from the app.",
            "spam_risk_too_many_posts": "TikTok's daily post limit for this account was reached. Try again tomorrow.",
            "scope_not_authorized": "The TikTok app wasn't granted this permission. Disconnect and connect again.",
        }
        raise PublishError(f"TikTok: {hints.get(code) or err.get('message') or code}")
    return data.get("data", {})


TIKTOK_PRIVACY = ("PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "SELF_ONLY")


def tiktok_creator() -> dict:
    """Who is connected and which visibilities TikTok lets this account post with (an app TikTok hasn't audited
    gets only SELF_ONLY). TikTok asks apps to offer only these."""
    info = _tiktok_call("/post/publish/creator_info/query/", _token("tiktok"), {})
    return {"username": info.get("creator_username", ""), "nickname": info.get("creator_nickname", ""),
            "privacy_options": [o for o in info.get("privacy_level_options") or [] if o in TIKTOK_PRIVACY] or ["SELF_ONLY"],
            "max_seconds": info.get("max_video_post_duration_sec") or 0,
            # interactions the creator turned off in TikTok's own settings; the app can't allow them
            "comment_disabled": bool(info.get("comment_disabled")), "duet_disabled": bool(info.get("duet_disabled")),
            "stitch_disabled": bool(info.get("stitch_disabled"))}


def _cover_ms(job: Path, video: Path, log, name: str = "TikTok") -> int:
    """TikTok's and Instagram's cover is a frame of the video (apps can't upload an image): the frame your thumbnail
    was made from. Its headline text isn't part of the video, so the cover shows the picture without it."""
    from .render import duration

    try:
        meta = json.loads((job / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        meta = {}
    if meta.get("thumb_image"):  # the thumbnail uses a photo that isn't in the video
        log(f"{name}: your cover uses a photo that isn't in the video; the cover is the frame at 1 s.")
        return 1000
    at = float(meta.get("thumb_at", 1.0) or 0.0)
    try:
        at = min(at, max(duration(video) - 0.2, 0.0))
    except Exception:
        pass
    log(f"{name}: cover = the frame at {at:.1f} s (your thumbnail's picture, without its text).")
    return int(at * 1000)


def _upload_tiktok(job: Path, video: Path, log, privacy: str | None = None, post: dict | None = None) -> dict:
    """`privacy`: a TIKTOK_PRIVACY level, or "DRAFT" for your TikTok drafts, for this upload (None = Settings).
    `post`: allow_comment / allow_duet / allow_stitch and the disclosure brand_organic / brand_content, as picked on
    the Upload card (None for auto and scheduled uploads: interactions allowed, nothing disclosed)."""
    token = _token("tiktok")
    prefs = dict(settings()["tiktok"])
    if privacy == "DRAFT":
        prefs["mode"] = "draft"
    elif privacy in TIKTOK_PRIVACY:
        prefs.update(mode="direct", privacy=privacy)
    title, desc, tags = post_text(job)
    caption = "\n\n".join(x for x in (title, desc, " ".join(f"#{t}" for t in tags)) if x)[:2200]
    size = video.stat().st_size
    # one chunk up to 64 MB; otherwise 10 MB chunks with the remainder added to the last one
    chunk = size if size <= 64 * 1024 * 1024 else 10 * 1024 * 1024
    count = max(1, size // chunk)
    source = {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": count}
    if prefs["mode"] == "draft":
        log("TikTok: sending to your TikTok drafts…")
        init = _tiktok_call("/post/publish/inbox/video/init/", token, {"source_info": source})
    else:
        creator = _tiktok_call("/post/publish/creator_info/query/", token, {})
        options = creator.get("privacy_level_options") or ["SELF_ONLY"]
        privacy = prefs["privacy"] if prefs["privacy"] in options else ("SELF_ONLY" if "SELF_ONLY" in options else options[0])
        if privacy != prefs["privacy"]:
            log(f"TikTok: this account can't post as {prefs['privacy']}; posting as {privacy}.")
        allow = post or {"allow_comment": True, "allow_duet": True, "allow_stitch": True}
        post_info = {"title": caption, "privacy_level": privacy,
                "disable_comment": not allow.get("allow_comment") or bool(creator.get("comment_disabled")),
                "disable_duet": not allow.get("allow_duet") or bool(creator.get("duet_disabled")),
                "disable_stitch": not allow.get("allow_stitch") or bool(creator.get("stitch_disabled")),
                "video_cover_timestamp_ms": _cover_ms(job, video, log)}
        if post and (post.get("brand_organic") or post.get("brand_content")):
            if post.get("brand_content") and privacy == "SELF_ONLY":
                raise PublishError("TikTok: branded content can't be posted as 'Only me'. Pick another visibility.")
            post_info.update(brand_organic_toggle=bool(post.get("brand_organic")),
                        brand_content_toggle=bool(post.get("brand_content")))
        log(f"TikTok: posting to @{creator.get('creator_username', '')}…")
        init = _tiktok_call("/post/publish/video/init/", token, {"post_info": post_info, "source_info": source})
    publish_id, upload_url = init["publish_id"], init["upload_url"]
    log(f"TikTok: uploading {size / 1e6:.1f} MB…")
    with open(video, "rb") as f:
        for i in range(count):
            start = i * chunk
            end = size - 1 if i == count - 1 else start + chunk - 1
            part = f.read(end - start + 1)
            r = requests.put(upload_url, data=part, timeout=None, headers={
                "Content-Type": "video/mp4", "Content-Length": str(len(part)), "Content-Range": f"bytes {start}-{end}/{size}"})
            if r.status_code >= 400:
                raise PublishError(f"TikTok upload failed ({r.status_code}): {r.text[:200]}")
    log("TikTok: processing…")
    deadline = time.time() + 600
    while time.time() < deadline:
        st = _tiktok_call("/post/publish/status/fetch/", token, {"publish_id": publish_id})
        state = st.get("status", "")
        if state == "FAILED":
            raise PublishError(f"TikTok couldn't post the video: {st.get('fail_reason', 'unknown reason')}")
        if state in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
            break
        time.sleep(5)
    else:
        log("TikTok: still processing; it will appear on your profile when TikTok is done.")
    if prefs["mode"] == "draft":
        log("TikTok: sent. Open TikTok → Inbox to finish and post it.")
        return {"id": publish_id, "url": "", "draft": True}
    ids = st.get("publicaly_available_post_id") or st.get("publicly_available_post_id") or []
    url = f"https://www.tiktok.com/@{creator.get('creator_username', '')}/video/{ids[0]}" if ids else ""
    log(f"TikTok: posted{' → ' + url if url else ' (visible once TikTok finishes processing)'}")
    return {"id": str(ids[0]) if ids else publish_id, "url": url, "privacy": privacy}


# ---------- Facebook and Instagram (Meta Graph API) ----------

def _caption(job: Path, max_len: int, max_tags: int | None = None) -> str:
    title, desc, tags = post_text(job)
    tags = tags[:max_tags] if max_tags is not None else tags
    return "\n\n".join(x for x in (title, desc, " ".join(f"#{t}" for t in tags)) if x)[:max_len]


def _rupload(url: str, token: str, video: Path, what: str) -> None:
    """Send the video to Meta's upload host in one request (the resumable upload, from byte 0)."""
    size = video.stat().st_size
    with open(video, "rb") as f:
        r = requests.post(url, data=f, timeout=None, headers={
            "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size), "Content-Type": "application/octet-stream"})
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400 or not data.get("success", r.status_code < 300):
        info = data.get("debug_info") or data.get("error") or {}
        raise PublishError(f"{what} upload failed: {info.get('message') or r.text[:200]}")


def _audio_48k(job: Path, video: Path) -> Path:
    """Facebook Reels ask for 48 kHz audio; renders use 44.1 kHz. A copy with only the audio converted (fast: the
    picture isn't re-encoded), kept in work/."""
    try:
        rate = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate",
                               "-of", "csv=p=0", str(video)], capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return video
    if not rate or rate == "48000":
        return video
    out = job / "work" / "video_48k.mp4"
    if out.exists() and out.stat().st_mtime >= video.stat().st_mtime:
        return out
    out.parent.mkdir(exist_ok=True)
    done = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                           "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(out)], stdin=subprocess.DEVNULL)
    return out if done.returncode == 0 and out.exists() else video


def fb_can_schedule(at: datetime, now: datetime | None = None) -> bool:
    """Can Facebook itself publish a post at local time `at` (uploaded now)?"""
    ahead = at - (now or datetime.now())
    return FB_SCHEDULE_MIN <= ahead <= FB_SCHEDULE_MAX


def _upload_facebook(job: Path, video: Path, log, page_id: str | None = None, publish_at: datetime | None = None) -> dict:
    """A vertical video up to 90 s becomes a Reel on the Page; anything else a regular Page video. `publish_at`:
    uploaded now, and Facebook publishes it at that local time (it shows in Meta Business Suite's planner)."""
    from .render import duration

    page = _meta_account(_load(), "facebook", page_id)
    if not page:
        raise PublishError("Facebook isn't connected (or that Page is gone). Connect it in Settings.")
    if publish_at and not fb_can_schedule(publish_at):
        raise PublishError("Facebook schedules posts from 10 minutes to 28 days ahead. Pick a time in that range.")
    when = {"scheduled_publish_time": str(int(publish_at.timestamp()))} if publish_at else {}
    later = f" (goes public {publish_at:%a %d %b, %H:%M})" if publish_at else ""
    token, text = page["token"], _caption(job, 5000)
    try:
        seconds = duration(video)
    except Exception:
        seconds = 0.0
    if _is_short(job) and 3 <= seconds <= FB_REEL_MAX_SEC:
        upload_file = _audio_48k(job, video)
        log(f"Facebook: {'scheduling' if publish_at else 'posting'} a Reel to {page['name']}…")
        start = _meta_json(requests.post(f"{GRAPH}/{page['id']}/video_reels", timeout=60,
                                         data={"upload_phase": "start", "access_token": token}), "Facebook")
        video_id = start["video_id"]
        log(f"Facebook: uploading {upload_file.stat().st_size / 1e6:.1f} MB…")
        _rupload(start.get("upload_url") or f"https://rupload.facebook.com/video-upload/{GRAPH_VERSION}/{video_id}",
                 token, upload_file, "Facebook")
        _meta_json(requests.post(f"{GRAPH}/{page['id']}/video_reels", timeout=60, data={
            "upload_phase": "finish", "video_id": video_id, "video_state": "SCHEDULED" if publish_at else "PUBLISHED",
            "description": text, "access_token": token, **when}), "Facebook")
        log("Facebook: processing…")
        deadline = time.time() + 600
        while time.time() < deadline:
            st = _meta_json(requests.get(f"{GRAPH}/{video_id}", timeout=30,
                                         params={"fields": "status", "access_token": token}), "Facebook").get("status", {})
            if st.get("video_status") in ("error", "upload_failed", "expired"):
                reason = ((st.get("processing_phase") or {}).get("errors") or [{}])[0].get("message", st["video_status"])
                raise PublishError(f"Facebook couldn't post the Reel: {reason}")
            if (st.get("publishing_phase") or {}).get("status") == "complete" or st.get("video_status") == "ready":
                break
            if publish_at and (st.get("processing_phase") or {}).get("status") == "complete":
                break  # processed; it publishes at its time
            time.sleep(5)
        else:
            log("Facebook: still processing; the Reel appears on the Page when Facebook is done.")
        url = f"https://www.facebook.com/reel/{video_id}"
        log(f"Facebook: {'scheduled' if publish_at else 'posted'} → {url}{later}")
        return {"id": video_id, "url": url, "page": page["id"], "page_name": page["name"], "reel": True,
                **({"publish_at": publish_at.isoformat(timespec="minutes")} if publish_at else {})}
    title = post_text(job)[0]
    log(f"Facebook: uploading {video.stat().st_size / 1e6:.1f} MB to {page['name']}…")
    with open(video, "rb") as f:
        r = requests.post(f"https://graph-video.facebook.com/{GRAPH_VERSION}/{page['id']}/videos", timeout=None,
                          data={"title": title[:255], "description": text, "access_token": token,
                                **({"published": "false", **when} if publish_at else {})},
                          files={"source": (video.name, f, "video/mp4")})
    video_id = _meta_json(r, "Facebook").get("id", "")
    url = f"https://www.facebook.com/{page['id']}/videos/{video_id}"
    log(f"Facebook: {'scheduled' if publish_at else 'posted'} → {url}{later}")
    return {"id": video_id, "url": url, "page": page["id"], "page_name": page["name"],
            **({"publish_at": publish_at.isoformat(timespec="minutes")} if publish_at else {})}


def _upload_instagram(job: Path, video: Path, log, account_id: str | None = None) -> dict:
    """A Reel on the Instagram professional account (resumable upload, then publish once Instagram has processed it)."""
    acct = _meta_account(_load(), "instagram", account_id)
    if not acct:
        raise PublishError("Instagram isn't connected (or that account is gone). Connect it in Settings.")
    token = acct["token"]
    log(f"Instagram: posting a Reel to {acct['name']}…")
    container = _meta_json(requests.post(f"{GRAPH}/{acct['id']}/media", timeout=60, data={
        "media_type": "REELS", "upload_type": "resumable", "caption": _caption(job, IG_CAPTION_MAX, IG_HASHTAGS_MAX),
        "share_to_feed": "true" if settings()["instagram"]["share_to_feed"] else "false",
        "thumb_offset": str(_cover_ms(job, video, log, "Instagram")), "access_token": token}), "Instagram")
    cid = container["id"]
    log(f"Instagram: uploading {video.stat().st_size / 1e6:.1f} MB…")
    _rupload(container.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{GRAPH_VERSION}/{cid}", token, video,
             "Instagram")
    log("Instagram: processing…")
    deadline = time.time() + 900
    while time.time() < deadline:
        st = _meta_json(requests.get(f"{GRAPH}/{cid}", timeout=30,
                                     params={"fields": "status_code,status", "access_token": token}), "Instagram")
        code = st.get("status_code", "")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise PublishError(f"Instagram couldn't process the video: {st.get('status') or code}")
        time.sleep(6)
    else:
        raise PublishError("Instagram is still processing the video after 15 minutes. Try the upload again later.")
    media_id = _meta_json(requests.post(f"{GRAPH}/{acct['id']}/media_publish", timeout=60,
                                        data={"creation_id": cid, "access_token": token}), "Instagram").get("id", "")
    try:
        url = _meta_json(requests.get(f"{GRAPH}/{media_id}", timeout=30,
                                      params={"fields": "permalink", "access_token": token}), "Instagram").get("permalink", "")
    except (PublishError, requests.RequestException):
        url = ""
    log(f"Instagram: posted{' → ' + url if url else ''}")
    return {"id": media_id, "url": url, "account": acct["id"], "account_name": acct["name"]}
