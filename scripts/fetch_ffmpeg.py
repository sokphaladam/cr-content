"""Download FFmpeg for the desktop installer: src-tauri/ffmpeg-dist/ffmpeg(.exe) and ffprobe(.exe).

Run from the project root (npm run build does this):  python scripts/fetch_ffmpeg.py
The installed app puts this folder first on the engine's PATH (src-tauri/src/main.rs), so it works without
FFmpeg installed. Static builds with libass (the captions need it):
  Windows  gyan.dev "release essentials" (GPLv3), checked against its published SHA-256
  macOS    ffmpeg.martin-riedl.de release builds (signed), for this Mac's architecture (arm64 or amd64)
Already downloaded binaries are reused; --force downloads them again.
"""
import hashlib
import io
import os
import platform
import shutil
import ssl
import stat
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "src-tauri" / "ffmpeg-dist"
GYAN = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
RIEDL = "https://ffmpeg.martin-riedl.de/redirect/latest/macos/{arch}/release/{tool}.zip"


def _tls() -> ssl.SSLContext:
    """python.org's Python on a Mac has no certificates of its own; certifi (installed with requests) has them."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(url: str) -> bytes:
    print(f"  downloading {url}", flush=True)
    with urlopen(Request(url, headers={"User-Agent": "shorts-studio-build"}), timeout=300, context=_tls()) as r:
        return r.read()


def windows() -> None:
    data = fetch(GYAN)
    expected = fetch(GYAN + ".sha256").decode().split()[0].strip().lower()
    if hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit("The FFmpeg download doesn't match its published SHA-256. Try again.")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for tool in ("ffmpeg.exe", "ffprobe.exe"):
            member = next(n for n in z.namelist() if n.endswith(f"/bin/{tool}"))
            (DEST / tool).write_bytes(z.read(member))


def macos() -> None:
    arch = "arm64" if platform.machine() == "arm64" else "amd64"
    for tool in ("ffmpeg", "ffprobe"):
        with zipfile.ZipFile(io.BytesIO(fetch(RIEDL.format(arch=arch, tool=tool)))) as z:
            member = next(n for n in z.namelist() if Path(n).name == tool)
            out = DEST / tool
            out.write_bytes(z.read(member))
        out.chmod(out.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        # the download is signed, but re-check: an unsigned binary inside the app won't run on Apple Silicon
        if subprocess.run(["codesign", "--verify", str(out)], capture_output=True).returncode != 0:
            subprocess.run(["codesign", "--force", "--sign", "-", str(out)], check=True)


def check() -> None:
    """The captions are drawn by libass through the ass filter: refuse a build without it."""
    exe = DEST / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    filters = subprocess.run([str(exe), "-hide_banner", "-filters"], capture_output=True, text=True, check=True).stdout
    if not any(line.split()[1:2] == ["ass"] for line in filters.splitlines() if len(line.split()) > 1):
        raise SystemExit(f"{exe} has no libass (ass filter), so it can't draw captions.")
    version = subprocess.run([str(exe), "-version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    print(f"  ok: {version}")


def main() -> int:
    tools = ("ffmpeg.exe", "ffprobe.exe") if os.name == "nt" else ("ffmpeg", "ffprobe")
    if "--force" in sys.argv:
        shutil.rmtree(DEST, ignore_errors=True)
    DEST.mkdir(parents=True, exist_ok=True)
    if all((DEST / t).exists() for t in tools):
        print("FFmpeg already downloaded (use --force to download it again).")
    elif sys.platform == "win32":
        windows()
    elif sys.platform == "darwin":
        macos()
    else:
        print("No FFmpeg download for this system; the app will use the one on PATH.")
        return 0
    check()
    return 0


if __name__ == "__main__":
    sys.exit(main())
