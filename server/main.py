"""Shorts Studio cloud: Google sign-in, and each user's library synced between their computers.

The desktop app never talks to the database: it signs in through this server and gets its own token. The list of
files lives in MySQL; their contents in S3-compatible storage (Cloudflare R2, Backblaze B2, DO Spaces...), which the
app uploads to and downloads from directly
with short-lived signed links.

Run:  uvicorn server.main:app --host 0.0.0.0 --port 8080
Settings (environment, on the server only):
  DATABASE_URL          mysql+pymysql://user:pass@host:25060/cr-content   (sqlite:///... for tests)
  DATABASE_CA           path to the database's CA certificate (DigitalOcean: Download CA certificate)
  GOOGLE_CLIENT_ID      the "Desktop app" OAuth client
  GOOGLE_CLIENT_SECRET
  S3_ENDPOINT           R2: https://<account id>.r2.cloudflarestorage.com   Spaces: https://sgp1.digitaloceanspaces.com
  S3_KEY, S3_SECRET, S3_BUCKET, S3_REGION (R2: auto)
"""
import base64
import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import (BigInteger, Column, DateTime, MetaData, String, Table, create_engine, delete, insert, select,
                        update)

GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
SESSION_DAYS = 90
LINK_SECONDS = 3600
PATH = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.?(?:/|$))[^\\\x00]{1,512}$")  # relative, no ./.. segments, no backslash
SHA = re.compile(r"^[0-9a-f]{64}$")

meta = MetaData()
users = Table("users", meta,
              Column("id", String(64), primary_key=True),  # Google's account id ("sub"): it never changes, email can
              Column("email", String(320), nullable=False),
              Column("name", String(200), nullable=False, default=""),
              Column("picture", String(1000), nullable=False, default=""),
              Column("created_at", DateTime, nullable=False))
sessions = Table("sessions", meta,
                 Column("token_hash", String(64), primary_key=True),  # sha256 of the token: a leaked table can't sign in
                 Column("user_id", String(64), nullable=False, index=True),
                 Column("device", String(200), nullable=False, default=""),
                 Column("expires_at", DateTime, nullable=False))
files = Table("files", meta,
              Column("user_id", String(64), primary_key=True),
              Column("path", String(512), primary_key=True),
              Column("sha256", String(64), nullable=False),
              Column("size", BigInteger, nullable=False),
              Column("device", String(200), nullable=False, default=""),
              Column("updated_at", DateTime, nullable=False))


load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))  # server/.env; real environment variables win
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))  # then the project's .env, for local runs
missing = [k for k in ("DATABASE_URL", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET") if not os.getenv(k)]
if missing:
    raise SystemExit(f"Missing settings: {', '.join(missing)}. Put them in server/.env (see server/README.md).")


def _engine():
    url = os.environ["DATABASE_URL"]
    if url.startswith("mysql://"):  # the form DigitalOcean shows; use the PyMySQL driver
        url = "mysql+pymysql://" + url.removeprefix("mysql://")
    args = {}
    if url.startswith("mysql"):
        if os.getenv("DATABASE_CA"):
            args = {"ssl": {"ca": os.environ["DATABASE_CA"]}}
        else:
            # shortcut: encrypted but the server's certificate isn't checked; set DATABASE_CA before going live
            print("Warning: DATABASE_CA isn't set, so the database's certificate isn't checked.")
            args = {"ssl": {"check_hostname": False}}
    return create_engine(url, connect_args=args, pool_pre_ping=True, pool_recycle=1800)


db = _engine()
meta.create_all(db)


class Bucket:
    """S3-compatible storage: signed links, so file contents never pass through this server."""

    def __init__(self):
        import boto3
        from botocore.config import Config

        self.bucket = os.environ["S3_BUCKET"]
        self.s3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"], region_name=os.getenv("S3_REGION", "auto"),
                               aws_access_key_id=os.environ["S3_KEY"], aws_secret_access_key=os.environ["S3_SECRET"],
                               config=Config(signature_version="s3v4"))  # R2 only accepts v4 signed links

    def upload_url(self, key: str) -> str:
        return self.s3.generate_presigned_url("put_object", Params={"Bucket": self.bucket, "Key": key},
                                              ExpiresIn=LINK_SECONDS)

    def download_url(self, key: str) -> str:
        return self.s3.generate_presigned_url("get_object", Params={"Bucket": self.bucket, "Key": key},
                                              ExpiresIn=LINK_SECONDS)

    def size(self, key: str) -> int | None:
        try:
            return self.s3.head_object(Bucket=self.bucket, Key=key)["ContentLength"]
        except self.s3.exceptions.ClientError:
            return None

    def delete(self, key: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=key)


storage = None  # set on first use (tests put a fake here)


def _storage():
    global storage
    if storage is None:
        storage = Bucket()
    return storage


app = FastAPI(title="Shorts Studio cloud")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _key(user_id: str, path: str) -> str:
    return f"users/{user_id}/{path}"


def current_user(authorization: str = Header("")) -> dict:
    token = authorization.removeprefix("Bearer ").strip()
    with db.begin() as c:
        row = c.execute(select(sessions).where(sessions.c.token_hash == _hash(token))).mappings().first() if token else None
        if not row or row["expires_at"] < _now():
            raise HTTPException(401, "Signed out. Sign in again.")
        user = c.execute(select(users).where(users.c.id == row["user_id"])).mappings().first()
    if not user:
        raise HTTPException(401, "Signed out. Sign in again.")
    return {**user, "device": row["device"], "token_hash": row["token_hash"]}


def _public(user: dict) -> dict:
    return {"email": user["email"], "name": user["name"], "picture": user["picture"]}


def _google_identity(code: str, verifier: str, redirect_uri: str) -> dict:
    """Trade the sign-in code for Google's ID token. It comes straight from Google over HTTPS, so (per OpenID
    Connect) its claims can be read without checking the signature; the audience is still checked."""
    client_id = os.environ["GOOGLE_CLIENT_ID"]
    r = requests.post(GOOGLE_TOKEN, timeout=30, data={
        "client_id": client_id, "client_secret": os.environ["GOOGLE_CLIENT_SECRET"], "code": code,
        "code_verifier": verifier, "grant_type": "authorization_code", "redirect_uri": redirect_uri})
    if r.status_code >= 400 or "id_token" not in r.text:
        raise HTTPException(401, "Google didn't accept the sign-in. Try again.")
    payload = r.json()["id_token"].split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    if claims.get("aud") != client_id or claims.get("iss") not in ("https://accounts.google.com", "accounts.google.com"):
        raise HTTPException(401, "That sign-in wasn't for Shorts Studio.")
    if not claims.get("email_verified"):
        raise HTTPException(401, "Verify your Google account's email first.")
    return claims


class GoogleSignIn(BaseModel):
    code: str
    verifier: str
    redirect_uri: str
    device: str = ""


@app.post("/auth/google")
def sign_in(req: GoogleSignIn):
    if not re.match(r"^http://127\.0\.0\.1:\d+/", req.redirect_uri):
        raise HTTPException(400, "Sign in from the Shorts Studio app.")
    g = _google_identity(req.code, req.verifier, req.redirect_uri)
    user = {"id": g["sub"], "email": g["email"], "name": g.get("name", "")[:200], "picture": g.get("picture", "")[:1000]}
    token = secrets.token_urlsafe(32)
    with db.begin() as c:
        if c.execute(update(users).where(users.c.id == user["id"]).values(
                email=user["email"], name=user["name"], picture=user["picture"])).rowcount == 0:
            c.execute(insert(users).values(**user, created_at=_now()))
        c.execute(insert(sessions).values(token_hash=_hash(token), user_id=user["id"], device=req.device[:200],
                                          expires_at=_now() + timedelta(days=SESSION_DAYS)))
    return {"token": token, "user": _public(user)}


@app.post("/auth/logout")
def sign_out(user: dict = Depends(current_user)):
    with db.begin() as c:
        c.execute(delete(sessions).where(sessions.c.token_hash == user["token_hash"]))
    return {"ok": True}


@app.get("/me")
def me(user: dict = Depends(current_user)):
    return _public(user)


@app.get("/files")
def list_files(user: dict = Depends(current_user)):
    with db.begin() as c:
        rows = c.execute(select(files.c.path, files.c.sha256, files.c.size, files.c.updated_at)
                         .where(files.c.user_id == user["id"])).mappings().all()
    return {"files": [{**r, "updated_at": r["updated_at"].isoformat()} for r in rows]}


class FileRef(BaseModel):
    path: str


class FileVersion(FileRef):
    sha256: str
    size: int


def _check(path: str) -> str:
    if not PATH.match(path):
        raise HTTPException(400, f"Bad file path: {path[:80]}")
    return path


@app.post("/files/upload")
def upload_link(req: FileVersion, user: dict = Depends(current_user)):
    if not SHA.match(req.sha256) or req.size < 0:
        raise HTTPException(400, "Bad file version.")
    return {"url": _storage().upload_url(_key(user["id"], _check(req.path)))}


@app.post("/files/commit")
def commit(req: FileVersion, user: dict = Depends(current_user)):
    """Record an upload, once the file really is in storage (the same size)."""
    if not SHA.match(req.sha256):
        raise HTTPException(400, "Bad file version.")
    if _storage().size(_key(user["id"], _check(req.path))) != req.size:
        raise HTTPException(409, f"{req.path} didn't finish uploading. Sync again.")
    values = {"sha256": req.sha256, "size": req.size, "device": user["device"], "updated_at": _now()}
    where = (files.c.user_id == user["id"]) & (files.c.path == req.path)
    with db.begin() as c:
        if c.execute(update(files).where(where).values(**values)).rowcount == 0:
            c.execute(insert(files).values(user_id=user["id"], path=req.path, **values))
    return {"ok": True}


def _owned(c, user: dict, path: str):
    row = c.execute(select(files).where((files.c.user_id == user["id"]) & (files.c.path == _check(path)))).first()
    if not row:
        raise HTTPException(404, f"{path} isn't in your library.")


@app.post("/files/download")
def download_link(req: FileRef, user: dict = Depends(current_user)):
    with db.begin() as c:
        _owned(c, user, req.path)
    return {"url": _storage().download_url(_key(user["id"], req.path))}


@app.post("/files/delete")
def delete_file(req: FileRef, user: dict = Depends(current_user)):
    with db.begin() as c:
        _owned(c, user, req.path)
        c.execute(delete(files).where((files.c.user_id == user["id"]) & (files.c.path == req.path)))
    _storage().delete(_key(user["id"], req.path))
    return {"ok": True}
