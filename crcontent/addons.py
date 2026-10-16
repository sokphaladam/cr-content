"""The AI add-on: torch (CUDA), Stable Diffusion, Whisper lyric timing and beat detection, installed from Settings.

On an Apple Silicon Mac, scene art runs on the Mac's GPU through Metal (torch from PyPI); an Intel Mac has no GPU
torch can use, so it gets the music extras only (Whisper lyric timing, beat detection, vocal separation).

How it installs depends on where the engine runs (_mode()):
  venv        dev runs: pip installs into the engine's own Python (the project's .venv); usable right away.
  embed       the Windows app: its engine is frozen (PyInstaller) without these libraries (~3 GB, mostly torch), so
              the add-on goes to <ROOT>/addons/ai: the official embeddable Python of the engine's version
              (python.org), pip, then the exact package versions the app is tested with (PINNED; CUDA 12.4 torch).
  standalone  the Mac app: the same, with a python-build-standalone Python of the engine's minor version
              (python.org has no portable Mac build).
activate() then puts that Python's site-packages (and its full standard library, which PyInstaller trims) on the
engine's import path, so `import torch` works as if it had been bundled.
"""
import hashlib
import importlib
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import zipfile
from pathlib import Path

import requests

from .config import ROOT

ADDON_DIR = ROOT / "addons" / "ai"
PY_DIR = ADDON_DIR / "python"
MARKER = ADDON_DIR / "installed.json"
TORCH_INDEX = "https://download.pytorch.org/whl/cu124"
# what the engine is tested with (the project's .venv); one pip run resolves them all together
PINNED = [
    "torch==2.6.0+cu124", "torchaudio==2.6.0+cu124",
    "diffusers==0.41.0", "transformers==5.19.0", "accelerate==1.15.0", "huggingface_hub==1.33.0", "hf_xet==1.7.0",
    "safetensors==0.8.0", "tokenizers==0.23.3",
    "stable-ts==2.19.1", "openai-whisper==20250625", "demucs==4.1.0",
    "librosa==0.11.0", "numba==0.68.0", "soundfile==0.14.0", "numpy==2.4.6", "scipy==1.17.1",
]
APPROX_BYTES = 3_100_000_000  # what pip downloads in all (torch's CUDA wheel is ~2.5 GB of it)

MAC = sys.platform == "darwin"
# Apple Silicon: scene art on the Mac's GPU (Metal); an Intel Mac gets the music extras only
MUSIC_ONLY = MAC and platform.machine() != "arm64"
# Mac: torch from PyPI (Metal on Apple Silicon); pip picks versions that fit the engine's Python
MAC_PACKAGES = ["torch", "torchaudio", "stable-ts>=2.17", "openai-whisper", "demucs>=4.0", "librosa>=0.10",
                "soundfile"]
if not MUSIC_ONLY:
    MAC_PACKAGES += ["diffusers>=0.32", "transformers>=4.46", "accelerate>=1.0", "huggingface_hub", "hf_xet",
                     "safetensors"]
MAC_APPROX_BYTES = 400_000_000 if MUSIC_ONLY else 600_000_000
# what each kind of install makes importable
MODULES = ("torch", "stable_whisper", "librosa") if MUSIC_ONLY else ("torch", "diffusers", "stable_whisper", "librosa")
STANDALONE_LATEST = ("https://raw.githubusercontent.com/astral-sh/python-build-standalone/latest-release/"
                     "latest-release.json")

_lock = threading.Lock()
_state: dict = {"installing": False, "stage": "", "done": 0, "total": 0, "speed": 0, "error": ""}


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _ver() -> str:
    return platform.python_version()  # e.g. 3.11.9


def _mode() -> str:
    """How the add-on installs here (see the module docstring); "" = it can't."""
    if not frozen():
        return "venv"
    return "embed" if sys.platform == "win32" else "standalone" if MAC else ""


def _lib() -> Path:
    """The add-on Python's standard library."""
    return PY_DIR if sys.platform == "win32" else PY_DIR / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}"


def _stdlib() -> tuple[Path, ...]:
    """Where the add-on Python's standard library is: a zip and the folder (Windows), or lib/pythonX.Y."""
    if sys.platform == "win32":
        return PY_DIR / f"python{''.join(_ver().split('.')[:2])}.zip", PY_DIR
    return _lib(), _lib() / "lib-dynload"


def _site() -> Path:
    return PY_DIR / "Lib" / "site-packages" if sys.platform == "win32" else _lib() / "site-packages"


def _present() -> bool:
    """The libraries the add-on provides can be imported in this engine."""
    try:
        return all(importlib.util.find_spec(m) for m in MODULES)
    except (ImportError, ValueError):
        return False


def ready() -> bool:
    if _mode() == "venv":
        return _present()
    # every module, so a Mac add-on installed before scene art ran on Macs is offered again (pip adds what's missing)
    return MARKER.exists() and all((_site() / m).exists() for m in MODULES)


def needed() -> bool:
    """Can the add-on be installed here, and is it missing?"""
    return bool(_mode()) and not ready() and not _present()


class _SubmoduleFinder:
    """Finds submodules the engine's bundled copy of a package lacks, in the add-on's complete copy.

    PyInstaller bundles only the parts of a package the engine imports (FastAPI's jinja2, say), and Python then
    searches only that package's own folder for its submodules, so diffusers' `import jinja2.meta` would fail. The
    same goes for the standard library (torch's `import unittest.mock`, when the engine bundled only `unittest`).
    This finder runs last (after the bundled and normal finders gave up) and looks in the add-on instead."""

    def find_spec(self, name, path=None, target=None):
        from importlib.machinery import PathFinder

        parts = name.split(".")
        if len(parts) < 2:
            return None  # top-level packages are found through sys.path
        folders = [root.joinpath(*parts[:-1]) for root in (_site(), *_stdlib())]
        # a folder inside the Windows stdlib zip isn't a real folder; PathFinder still searches it
        return PathFinder.find_spec(name, [str(f) for f in folders if f.is_dir() or ".zip" in str(f)])


def activate() -> bool:
    """Make an installed add-on importable in this (frozen) engine. Safe to call again; True when active."""
    if not frozen() or not ready():
        return False
    for path in (_site(), *_stdlib()):
        # appended: the engine's own (bundled) modules still win; the add-on fills in what's missing, including
        # standard-library modules PyInstaller left out because the engine itself never imports them
        if str(path) not in sys.path:
            sys.path.append(str(path))
    for dll_dir in (PY_DIR, _site() / "torch" / "lib"):
        if dll_dir.exists() and hasattr(os, "add_dll_directory"):  # Windows
            os.add_dll_directory(str(dll_dir))
    if not any(isinstance(f, _SubmoduleFinder) for f in sys.meta_path):
        sys.meta_path.append(_SubmoduleFinder())
    importlib.invalidate_caches()
    return True


def status() -> dict:
    with _lock:
        state = dict(_state)
    venv = _mode() == "venv"
    return {"needed": needed(), "ready": ready(), "scope": "music" if MUSIC_ONLY else "all",
            "size": "about 1 GB" if MUSIC_ONLY else "about 1.5 GB" if MAC else "about 3 GB", "folder": str(Path(sys.prefix) if venv else ADDON_DIR),
            **state}


def _set(**kw) -> None:
    with _lock:
        _state.update(kw)


def _fetch(url: str, dest: Path, stage: str) -> None:
    """Download with live byte progress."""
    _set(stage=stage, done=0, total=0, speed=0)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        _set(total=total)
        got, start = 0, time.time()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
                got += len(chunk)
                _set(done=got, speed=int(got / max(time.time() - start, 0.1)))
        tmp.replace(dest)


def _python() -> Path:
    if _mode() == "venv":
        return Path(sys.executable)
    return PY_DIR / "python.exe" if sys.platform == "win32" else PY_DIR / "bin" / "python3"


def _prepare_python() -> None:
    if _mode() == "standalone":
        _prepare_standalone()
    elif _mode() == "embed":
        _prepare_embed()


def _standalone() -> tuple[str, str]:
    """python-build-standalone's newest Mac build of the engine's Python (same minor version, so the same ABI):
    (download url, sha256). Its small release index and checksum list, not GitHub's API (too slow to list)."""
    arch = {"arm64": "aarch64"}.get(platform.machine(), platform.machine())
    latest = requests.get(STANDALONE_LATEST, timeout=30)
    latest.raise_for_status()
    prefix = latest.json()["asset_url_prefix"]
    sums = requests.get(f"{prefix}/SHA256SUMS", timeout=30)
    sums.raise_for_status()
    minor = ".".join(_ver().split(".")[:2])
    name = re.compile(rf"^cpython-{re.escape(minor)}\.\d+\+\d+-{arch}-apple-darwin-install_only\.tar\.gz$")
    for line in sums.text.splitlines():
        digest, _, file = line.strip().partition("  ")
        if name.match(file):
            return f"{prefix}/{file}", digest
    raise RuntimeError(f"No portable Python {minor} for this Mac was found to install the add-on into.")


def _prepare_standalone() -> None:
    """A portable Python of the engine's version (it comes with pip)."""
    if _python().exists() and (_site() / "pip").exists():
        return
    _set(stage="Finding Python")
    url, digest = _standalone()
    archive = ADDON_DIR / url.rsplit("/", 1)[-1]
    if not archive.exists():
        _fetch(url, archive, "Downloading Python")
    if hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
        archive.unlink()
        raise RuntimeError("The Python download was damaged. Try again.")
    shutil.rmtree(PY_DIR, ignore_errors=True)
    with tarfile.open(archive) as t:
        t.extractall(ADDON_DIR, filter="data")  # the archive holds python/...


def _prepare_embed() -> None:
    """The embeddable Python, with `import site` switched on so pip and site-packages work."""
    if _python().exists() and (_site() / "pip").exists():
        return
    PY_DIR.mkdir(parents=True, exist_ok=True)
    archive = ADDON_DIR / f"python-{_ver()}-embed-amd64.zip"
    if not archive.exists():
        _fetch(f"https://www.python.org/ftp/python/{_ver()}/python-{_ver()}-embed-amd64.zip", archive,
               f"Downloading Python {_ver()}")
    with zipfile.ZipFile(archive) as z:
        z.extractall(PY_DIR)
    pth = next(PY_DIR.glob("python*._pth"))
    lines = [ln for ln in pth.read_text().splitlines() if ln.strip() and ln.strip() != "#import site"]
    pth.write_text("\n".join([*lines, "Lib\\site-packages", "import site", ""]))
    getpip = ADDON_DIR / "get-pip.py"
    _fetch("https://bootstrap.pypa.io/get-pip.py", getpip, "Downloading pip")
    _set(stage="Setting up pip", done=0, total=0)
    _run([str(_python()), str(getpip), "--no-warn-script-location"])


def _run(cmd: list[str], on_line=None) -> None:
    proc = subprocess.Popen(cmd, cwd=ADDON_DIR, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    tail: list[str] = []
    for line in proc.stdout:
        line = line.rstrip()
        tail = (tail + [line])[-25:]
        if on_line:
            on_line(line)
    if proc.wait() != 0:
        raise RuntimeError("\n".join(ln for ln in tail if ln.strip())[-1500:])


# "Downloading torch-2.6.0+cu124-cp311-cp311-win_amd64.whl (2502.3 MB)" / "Using cached librosa-0.11.0-....whl (260 kB)"
# (not the "...whl.metadata" lines pip fetches first)
_FILE = re.compile(r"^(Downloading|Using cached) ([A-Za-z0-9_.]+?)-\d\S*?(?:\.whl|\.tar\.gz|\.zip) \(([\d.]+) (k?B|MB|GB)\)")
_PROGRESS = re.compile(r"Progress (\d+) of (\d+)")
_UNITS = {"B": 1, "kB": 1e3, "MB": 1e6, "GB": 1e9}


def _install_packages() -> None:
    """pip with --progress-bar raw prints "Progress <bytes> of <total>" while each file downloads: summed into one
    bar. Files pip already has in its cache count as done straight away."""
    finished = 0  # bytes of the files finished so far (downloaded or found in pip's cache)
    current = {"done": 0, "total": 0}
    fetched = 0  # bytes really downloaded, for the speed
    start = time.time()

    approx = MAC_APPROX_BYTES if MAC else APPROX_BYTES

    def show() -> None:
        got = finished + current["done"]
        _set(done=got, total=max(approx, got), speed=int(fetched / max(time.time() - start, 0.1)))

    def on_line(line: str) -> None:
        nonlocal finished, fetched
        if m := _PROGRESS.search(line):
            done = int(m.group(1))
            fetched += max(done - current["done"], 0)
            current["done"] = done
            show()
        elif m := _FILE.match(line.strip()):
            finished += current["total"]  # the previous file is complete
            size = int(float(m.group(3)) * _UNITS[m.group(4)])
            if m.group(1) == "Using cached":
                finished += size
                current.update(done=0, total=0)
            else:
                current.update(done=0, total=size)
            _set(stage=f"Downloading {m.group(2)}")
            show()
        elif line.startswith("Installing collected packages"):
            _set(stage="Installing (a few minutes)", done=approx, total=approx, speed=0)
        elif line.startswith(("Building wheel", "Preparing metadata")):
            _set(stage="Preparing packages")

    _set(stage="Downloading packages", done=0, total=approx)
    packages = MAC_PACKAGES if MAC else ["--extra-index-url", TORCH_INDEX, *PINNED]
    _run([str(_python()), "-m", "pip", "install", "--no-warn-script-location", "--disable-pip-version-check",
          "--progress-bar", "raw", *packages], on_line)


def _install() -> None:
    try:
        ADDON_DIR.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(_python().parent if _mode() == "venv" else ADDON_DIR).free
        need = 3e9 if MUSIC_ONLY else 5e9 if MAC else 10e9
        if free < need:
            raise RuntimeError(f"The AI add-on needs about {need / 1e9:.0f} GB free disk space ({free / 1e9:.1f} GB free).")
        _prepare_python()
        _install_packages()
        if _mode() != "venv":
            MARKER.write_text(json.dumps({"python": _ver(), "packages": MAC_PACKAGES if MAC else PINNED,
                                          "installed": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=2))
        activate()
        importlib.invalidate_caches()  # the new packages can be imported without a restart
        _set(stage="Installed", error="")
    except Exception as e:
        _set(error=f"{type(e).__name__}: {str(e).strip()[-600:]}", stage="")
    finally:
        _set(installing=False, speed=0)


def install() -> bool:
    """Start installing in the background (no-op while one runs). Progress comes from status()."""
    if not _mode():
        _set(error="The AI add-on can't be installed on this system.")
        return False
    with _lock:
        if _state["installing"]:
            return False
        _state.update(installing=True, stage="Starting", done=0, total=0, speed=0, error="")
    threading.Thread(target=_install, daemon=True).start()
    return True
