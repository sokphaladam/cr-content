"""Build the Remotion graphics for the desktop app: src-tauri/remotion-dist/ (bundled as resources/remotion).

Run from the project root (npm run build does this):  python scripts/build_remotion.py
What goes in, so the installed app needs nothing on the user's PC (crcontent/shorts/motion.py):
  node(.exe)     Node from nodejs.org, the same version as the one building, checked against its SHASUMS256.txt
  bundle/        remotion/src prebuilt (no bundler at run time)
  render.mjs     the renderer script (transparent clips)
  still.mjs      the editor's preview frames of graphics (transparent PNGs)
  node_modules/  @remotion/renderer only (production), with the headless Chrome it renders in
Already downloaded Node is reused; --force downloads it again.
"""
import hashlib
import io
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

from fetch_ffmpeg import fetch  # same downloader, with the certifi fix for python.org Python on macOS

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "remotion"
DEST = ROOT / "src-tauri" / "remotion-dist"
NPM = "npm.cmd" if sys.platform == "win32" else "npm"



def node_binary(force: bool) -> None:
    """DEST/node(.exe): the official build of the Node that's building (Windows x64, macOS arm64/x64)."""
    win = sys.platform == "win32"
    out = DEST / ("node.exe" if win else "node")
    if out.exists() and not force:
        return
    version = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True).stdout.strip()
    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x64"
    name = f"node-{version}-win-{arch}.zip" if win else f"node-{version}-darwin-{arch}.tar.gz"
    base = f"https://nodejs.org/dist/{version}/"
    data = fetch(base + name)
    sums = dict(reversed(line.split()) for line in fetch(base + "SHASUMS256.txt").decode().splitlines() if line.strip())
    if hashlib.sha256(data).hexdigest() != sums.get(name):
        raise SystemExit(f"The Node download ({name}) doesn't match its published SHA-256. Try again.")
    inner = f"{name.rsplit('.zip', 1)[0]}/node.exe" if win else f"{name.rsplit('.tar.gz', 1)[0]}/bin/node"
    if win:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            out.write_bytes(z.read(inner))
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
            out.write_bytes(t.extractfile(inner).read())
        out.chmod(0o755)


def main() -> int:
    force = "--force" in sys.argv
    if not shutil.which("node"):
        print("Node.js not found: install it (nodejs.org), then run this again.", file=sys.stderr)
        return 1
    DEST.mkdir(parents=True, exist_ok=True)
    subprocess.run([NPM, "install", "--no-audit", "--no-fund"], cwd=SRC, check=True)
    shutil.rmtree(DEST / "bundle", ignore_errors=True)
    subprocess.run(["node", "bundle.mjs", str(DEST / "bundle")], cwd=SRC, check=True)
    for script in ("render.mjs", "still.mjs"):  # the clips, and the editor's preview frames (M5)
        shutil.copy(SRC / script, DEST / script)
    # the renderer alone, at the version the source was built and tested with
    version = json.loads((SRC / "node_modules" / "@remotion" / "renderer" / "package.json").read_text())["version"]
    (DEST / "package.json").write_text(json.dumps({"name": "crcontent-motion-runtime", "private": True, "type": "module",
                                                   "dependencies": {"@remotion/renderer": version}}, indent=2))
    subprocess.run([NPM, "install", "--omit=dev", "--no-audit", "--no-fund", "--no-package-lock"], cwd=DEST, check=True)
    print("  headless Chrome for the renderer", flush=True)
    for attempt in (1, 2):  # a ~130 MB download: one retry for a dropped connection
        if subprocess.run(["node", "-e", "import('@remotion/renderer').then(r => r.ensureBrowser())"], cwd=DEST).returncode == 0:
            break
        if attempt == 2:
            raise SystemExit("Couldn't download the headless Chrome Remotion renders in. Try again.")
    node_binary(force)
    size = sum(f.stat().st_size for f in DEST.rglob("*") if f.is_file()) / 1e6
    print(f"Remotion runtime ready in {DEST} ({size:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
