"""Build the Python engine for the desktop installer: src-tauri/engine-dist/engine/engine.exe (PyInstaller, one folder).

Run from the project root (npm run build does this):  python scripts/build_engine.py
Uses the project's .venv, which needs requirements.txt and requirements-build.txt installed.
The optional music-video extras (torch, stable-ts, librosa) are left out: they are several GB, and the engine
falls back to even lyric spacing and bpm-based cuts without them.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = next((p for p in (ROOT / ".venv/Scripts/python.exe", ROOT / ".venv/bin/python") if p.exists()), None)


def main() -> int:
    if not VENV_PYTHON:
        print("Python virtualenv not found. In the project root run:\n  python -m venv .venv\n"
              "  .venv\\Scripts\\pip install -r requirements.txt -r requirements-build.txt", file=sys.stderr)
        return 1
    build = ROOT / "build"
    cmd = [
        str(VENV_PYTHON), "-m", "PyInstaller", str(ROOT / "app.py"),
        "--name", "engine", "--onedir", "--noconfirm", "--clean",
        "--distpath", str(ROOT / "src-tauri" / "engine-dist"),
        "--workpath", str(build / "pyinstaller"),
        "--specpath", str(build),
        "--add-data", f"{ROOT / 'web'}{os.pathsep}web",
        "--collect-submodules", "crcontent",
        "--collect-submodules", "uvicorn",
        "--collect-data", "edge_tts",
        *[arg for mod in ("torch", "torchaudio", "stable_whisper", "whisper", "librosa", "numba", "tkinter")
          for arg in ("--exclude-module", mod)],
    ]
    return subprocess.run(cmd, cwd=ROOT).returncode


if __name__ == "__main__":
    sys.exit(main())
