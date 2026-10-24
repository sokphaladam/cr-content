"""Where the app keeps its files, chosen in Settings and remembered in <APP_HOME>/locations.json:

  data folder     drafts, uploads, cache, assets, campaigns, songs (lyric videos), keys (.env, accounts.json), the upload schedule
  videos folder   finished videos, one folder per video ("" = <data folder>/output)

APP_HOME is the per-user app folder (the same one the desktop app keeps engine.log in), so dev runs, the installed
app and make.py all work on the same library. The first run moves data from where earlier versions kept it (the
project folder, and the desktop app's own app-data folder) into the default data folder.
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

APP_ID = "com.crcontent.shorts-studio"


def _app_home() -> Path:
    """Tauri's app_data_dir for APP_ID, so the engine and the desktop app agree on where engine.log etc. live."""
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / APP_ID


APP_HOME = _app_home()
FILE = APP_HOME / "locations.json"
# What the data folder holds (paths saved in drafts are relative to it, so these move together).
DATA_ENTRIES = ("drafts", "uploads", "cache", "assets", "campaigns", "songs", ".env", "accounts.json", "schedule.json")
OUTPUT = "output"  # the videos folder inside the data folder, unless another one is chosen
VIDEO_FOLDER = re.compile(r"^\d{8}-\d{6}-")  # a finished video's folder name (pipeline.py: <stamp>-<lang>-<slug>)
KEEP = {".gitkeep"}  # the project's placeholder files stay in the repo


def documents() -> Path:
    """The user's Documents folder, wherever Windows has it (OneDrive can move it)."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        from uuid import UUID

        class GUID(ctypes.Structure):
            _fields_ = [("data", ctypes.c_ubyte * 16)]

        folder_id = GUID()
        folder_id.data[:] = UUID("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}").bytes_le  # FOLDERID_Documents
        path = wintypes.LPWSTR()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(folder_id), 0, None, ctypes.byref(path)) == 0:
            try:
                return Path(path.value)
            finally:
                ctypes.windll.ole32.CoTaskMemFree(path)
    return Path.home() / "Documents"


def _default_data() -> Path:
    docs = documents()
    # Renders and the footage cache run to many GB: keep them out of a OneDrive-synced Documents folder.
    return (Path.home() if "onedrive" in str(docs).lower() else docs) / "Shorts Studio"


DEFAULT_DATA = _default_data()


def _saved() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(data: Path, videos: Path | None) -> None:
    APP_HOME.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"data": str(data), "videos": str(videos) if videos else ""}, indent=2), encoding="utf-8")
    tmp.replace(FILE)


def current() -> tuple[Path, Path, bool]:
    """(data folder, videos folder, whether the videos folder is the default one inside the data folder).
    CRCONTENT_DATA_DIR overrides the data folder (tests, a second library)."""
    saved = _saved()
    data = Path(os.getenv("CRCONTENT_DATA_DIR") or saved.get("data") or DEFAULT_DATA).resolve()
    videos = saved.get("videos") if not os.getenv("CRCONTENT_DATA_DIR") else ""
    return (data, Path(videos).resolve(), False) if videos else (data, data / OUTPUT, True)


def _move(src: Path, dst: Path, clashes: list[Path]) -> None:
    """Move src to dst, merging folders. When a file exists on both sides the newer one is kept at dst; the other
    stays where it was (listed in `clashes`), so nothing is ever deleted."""
    if src.name in KEEP:
        return
    if src.is_dir() and not dst.exists():
        dst.mkdir(parents=True)  # then merge into it, so the files in KEEP stay behind
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    elif src.is_dir() and dst.is_dir():
        for child in list(src.iterdir()):
            _move(child, dst / child.name, clashes)
        try:
            src.rmdir()
        except OSError:
            pass  # something stayed behind (a clash or a .gitkeep)
    elif src.is_file() and dst.is_file() and src.stat().st_mtime > dst.stat().st_mtime:
        older = dst.with_name(dst.name + ".older")
        dst.replace(older)
        shutil.move(str(src), str(dst))
        shutil.move(str(older), str(src))
        clashes.append(src)
    else:
        clashes.append(src)


def _move_videos(src: Path, dst: Path, clashes: list[Path]) -> None:
    """Move the finished videos only: a chosen videos folder may hold other files of the user's."""
    if not src.is_dir() or src == dst:
        return
    dst.mkdir(parents=True, exist_ok=True)
    for child in list(src.iterdir()):
        if child.is_dir() and VIDEO_FOLDER.match(child.name):
            _move(child, dst / child.name, clashes)
    try:
        src.rmdir()
    except OSError:
        pass


def _inside(path: Path, folder: Path) -> bool:
    return path == folder or folder in path.parents


def check(data: Path, videos: Path | None, code_dir: Path) -> None:
    """Raise ValueError when the folders can't hold the library."""
    for p in (data, videos):
        if p is None:
            continue
        if not p.is_absolute() or p.parent == p:
            raise ValueError(f"Pick a full folder path, not {p}.")
        if _inside(p, code_dir.resolve()) and not (code_dir / ".git").exists():
            raise ValueError("That's inside the app's install folder. Pick a folder of your own.")
        if p.exists() and not p.is_dir():
            raise ValueError(f"{p} is a file, not a folder.")
    if videos is not None:
        if videos == data:
            raise ValueError("Use a different folder for videos than for the data, or keep the default.")
        if _inside(data, videos):
            raise ValueError("The data folder can't be inside the videos folder.")
        if videos.parent == data and videos.name in DATA_ENTRIES:
            raise ValueError(f"'{videos.name}' is one of the data folder's own folders. Pick another.")


def relocate(data: Path, videos: Path | None, code_dir: Path) -> list[Path]:
    """Move the library to `data` (and the finished videos to `videos`, None = <data>/output), then remember the
    new places. Returns files that stayed behind because the new folder already had a newer copy."""
    data = data.resolve()
    videos = videos.resolve() if videos else None
    check(data, videos, code_dir)
    old_data, old_videos, _ = current()
    data.mkdir(parents=True, exist_ok=True)
    clashes: list[Path] = []
    if data != old_data:
        for name in DATA_ENTRIES:
            if (old_data / name).exists():
                _move(old_data / name, data / name, clashes)
    _move_videos(old_videos, videos or data / OUTPUT, clashes)
    _save(data, videos)
    return clashes


def first_run(code_dir: Path) -> None:
    """Once: start remembering locations, gathering the library from where earlier versions kept it."""
    if FILE.exists() or os.getenv("CRCONTENT_DATA_DIR"):
        return
    sources = [APP_HOME]  # the desktop app's data (its keys are the freshest)
    if not getattr(sys, "frozen", False):
        sources.append(code_dir)  # dev runs kept data in the project folder
    clashes: list[Path] = []
    for src in sources:
        if src.resolve() == DEFAULT_DATA.resolve():
            continue
        for name in (*DATA_ENTRIES, OUTPUT):
            if (src / name).exists():
                _move(src / name, DEFAULT_DATA / name, clashes)
    DEFAULT_DATA.mkdir(parents=True, exist_ok=True)
    _save(DEFAULT_DATA, None)
    if clashes:
        print(f"Moved the library to {DEFAULT_DATA}; {len(clashes)} older duplicate files stayed where they were.",
              flush=True)
