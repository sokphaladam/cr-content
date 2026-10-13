"""The AI add-on for the desktop app: torch (CUDA), Stable Diffusion, Whisper lyric timing and beat detection.

The installed app's engine is frozen (PyInstaller) without these libraries: they are ~3 GB and most of it is
torch. Instead, Settings offers a one-time install into <ROOT>/addons/ai:
  1. the official embeddable Python of the same version as the engine (python.org),
  2. pip, then the exact package versions the app is tested with (PINNED; torch from the CUDA 12.4 index).
activate() then puts that Python's site-packages (and its full standard library, which PyInstaller trims) on the
engine's import path, so `import torch` works as if it had been bundled. Dev runs use the project's .venv instead.
"""
import importlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
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

_lock = threading.Lock()
_state: dict = {"installing": False, "stage": "", "done": 0, "total": 0, "speed": 0, "error": ""}


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _ver() -> str:
    return platform.python_version()  # e.g. 3.11.9


def _site() -> Path:
    return PY_DIR / "Lib" / "site-packages"


def ready() -> bool:
    return MARKER.exists() and (_site() / "torch").exists()


def needed() -> bool:
    """Does this engine need the add-on for AI features? (Dev runs have the libraries in .venv.)"""
    if not frozen():
        return False
    try:
        importlib.import_module("torch")
        return False
    except ImportError:
        return True


class _SubmoduleFinder:
    """Finds submodules the engine's bundled copy of a package lacks, in the add-on's complete copy.

    PyInstaller bundles only the parts of a package the engine imports (FastAPI's jinja2, say), and Python then
    searches only that package's own folder for its submodules, so diffusers' `import jinja2.meta` would fail.
    This finder runs last (after the bundled and normal finders gave up) and looks in the add-on instead."""

    def find_spec(self, name, path=None, target=None):
        from importlib.machinery import PathFinder

        parts = name.split(".")
        if len(parts) < 2:
            return None  # top-level packages are found through sys.path
        folder = _site().joinpath(*parts[:-1])
        return PathFinder.find_spec(name, [str(folder)]) if folder.is_dir() else None


def activate() -> bool:
    """Make an installed add-on importable in this (frozen) engine. Safe to call again; True when active."""
    if not frozen() or not ready():
        return False
    major_minor = "".join(_ver().split(".")[:2])
    for path in (_site(), PY_DIR / f"python{major_minor}.zip", PY_DIR):
        # appended: the engine's own (bundled) modules still win; the add-on fills in what's missing, including
        # standard-library modules PyInstaller left out because the engine itself never imports them
        if str(path) not in sys.path:
            sys.path.append(str(path))
    for dll_dir in (PY_DIR, _site() / "torch" / "lib"):
        if dll_dir.exists():
            os.add_dll_directory(str(dll_dir))
    if not any(isinstance(f, _SubmoduleFinder) for f in sys.meta_path):
        sys.meta_path.append(_SubmoduleFinder())
    importlib.invalidate_caches()
    return True


def status() -> dict:
    with _lock:
        state = dict(_state)
    return {"needed": needed() and not ready(), "ready": ready(), "folder": str(ADDON_DIR), **state}


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
    return PY_DIR / "python.exe"


def _prepare_python() -> None:
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
    proc = subprocess.Popen(cmd, cwd=PY_DIR, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
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

    def show() -> None:
        got = finished + current["done"]
        _set(done=got, total=max(APPROX_BYTES, got), speed=int(fetched / max(time.time() - start, 0.1)))

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
            _set(stage="Installing (a few minutes, unpacking ~6 GB)", done=APPROX_BYTES, total=APPROX_BYTES, speed=0)
        elif line.startswith(("Building wheel", "Preparing metadata")):
            _set(stage="Preparing packages")

    _set(stage="Downloading packages", done=0, total=APPROX_BYTES)
    _run([str(_python()), "-m", "pip", "install", "--no-warn-script-location", "--disable-pip-version-check",
          "--progress-bar", "raw", "--extra-index-url", TORCH_INDEX, *PINNED], on_line)


def _install() -> None:
    try:
        ADDON_DIR.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(ADDON_DIR).free
        if free < 10e9:
            raise RuntimeError(f"The AI add-on needs about 10 GB free on {ADDON_DIR.anchor} ({free / 1e9:.1f} GB free).")
        _prepare_python()
        _install_packages()
        MARKER.write_text(json.dumps({"python": _ver(), "packages": PINNED,
                                      "installed": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=2))
        activate()
        _set(stage="Installed", error="")
    except Exception as e:
        _set(error=f"{type(e).__name__}: {str(e).strip()[-600:]}", stage="")
    finally:
        _set(installing=False, speed=0)


def install() -> bool:
    """Start installing in the background (no-op while one runs). Progress comes from status()."""
    with _lock:
        if _state["installing"]:
            return False
        _state.update(installing=True, stage="Starting", done=0, total=0, speed=0, error="")
    threading.Thread(target=_install, daemon=True).start()
    return True
