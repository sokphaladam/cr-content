"""Build the Python engine for the desktop app: src-tauri/engine-dist/engine/engine(.exe) (PyInstaller, one folder).

Run from the project root (npm run build does this):  python scripts/build_engine.py
Uses the project's .venv, which needs requirements.txt and requirements-build.txt installed.
The AI libraries (torch, diffusers, Whisper, librosa...) are left out entirely: they are ~3 GB, so the installed app
gets them as a one-time add-on from Settings (crcontent/addons.py). Partial copies must not be bundled either: they
would shadow the add-on's complete ones.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = next((p for p in (ROOT / ".venv/Scripts/python.exe", ROOT / ".venv/bin/python") if p.exists()), None)


# provided by the AI add-on; numpy and scipy only ever come in through these
AI_MODULES = ("torch", "torchaudio", "torchvision", "stable_whisper", "whisper", "demucs", "librosa", "numba",
              "llvmlite", "soundfile", "diffusers", "transformers", "accelerate", "huggingface_hub", "hf_xet",
              "safetensors", "tokenizers", "numpy", "scipy", "tkinter")


def stdlib_extensions() -> list[str]:
    """Every compiled standard-library module of the engine's Python (cmath, _lsprof...), bundled even though the
    engine doesn't import them: the AI add-on's libraries may (torch needs cmath), and the add-on's own Python can't
    lend them on a Mac (python-build-standalone builds them into its executable, not into files)."""
    # where they are: lib-dynload (macOS, Linux) or DLLs (Windows), found through one that's always compiled
    out = subprocess.run([str(VENV_PYTHON), "-c", "import _ctypes, os; print(os.path.dirname(_ctypes.__file__))"],
                         capture_output=True, text=True, check=True).stdout.strip()
    names = {f.name.split(".")[0] for f in Path(out).iterdir() if f.suffix in (".so", ".pyd")}
    skip = ("_test", "xx", "_xx", "_ctypes_test", "_tkinter")  # CPython's own tests, and Tk (never used)
    return sorted(n for n in names if n and not n.startswith(skip))


def main() -> int:
    if not VENV_PYTHON:
        print("Python virtualenv not found. In the project root run:\n  python -m venv .venv\n"
              "  .venv/bin/pip (Windows: .venv\\Scripts\\pip) install -r requirements.txt -r requirements-build.txt", file=sys.stderr)
        return 1
    build = ROOT / "build"
    cmd = [
        str(VENV_PYTHON), "-m", "PyInstaller", str(ROOT / "app.py"),
        "--name", "engine", "--onedir", "--noconfirm", "--clean",
        "--distpath", str(ROOT / "src-tauri" / "engine-dist"),
        "--workpath", str(build / "pyinstaller"),
        "--specpath", str(build),
        "--add-data", f"{ROOT / 'web'}{os.pathsep}web",
        "--add-data", f"{ROOT / '.env.example'}{os.pathsep}.",  # app.py copies it to the data folder on first run
        "--collect-submodules", "crcontent",
        "--collect-submodules", "uvicorn",
        "--collect-data", "edge_tts",
        "--collect-data", "cv2",  # the Haar cascade .xml files Smart Highlights finds faces with
        "--hidden-import", "resvg_py",  # imported lazily by crcontent.art
        "--collect-submodules", "yt_dlp",  # campaign reference downloads; its site extractors load lazily
        *[arg for mod in AI_MODULES for arg in ("--exclude-module", mod)],
        *[arg for mod in stdlib_extensions() for arg in ("--hidden-import", mod)],
    ]
    code = subprocess.run(cmd, cwd=ROOT).returncode
    # `tauri build` copies the engine next to target/*/shorts-studio.exe without removing files an older engine had
    # (an old numpy there broke startup); a fresh copy of the new engine goes there instead
    for profile in ("release", "debug"):
        shutil.rmtree(ROOT / "src-tauri" / "target" / profile / "engine", ignore_errors=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
