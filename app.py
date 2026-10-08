"""Start the web UI:  python app.py   (then open http://127.0.0.1:8000)

Options:
  --reload          dev mode: restart when code changes
  --no-browser      don't open the browser
  --port N          listen on another port (default 8000)
  --parent-pid PID  exit when that process ends (the desktop app runs the engine this way, so it never outlives
                    the app, even if the app crashes)
"""
import argparse
import os
import subprocess
import sys
import threading
import time
import webbrowser

import uvicorn
from dotenv import load_dotenv


def _exit_with_parent(pid: int) -> None:
    # Wait on the process itself, not on a pipe: on Windows a pending read on stdin blocks every DLL that
    # initialises its C runtime (numpy, torch...) until the read returns.
    if sys.platform == "win32":
        import ctypes

        SYNCHRONIZE, INFINITE = 0x00100000, 0xFFFFFFFF
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if handle:
            kernel32.WaitForSingleObject(handle, INFINITE)
    else:
        while os.getppid() == pid:
            time.sleep(1)
    os._exit(0)


def _serve_with_reload(port: int) -> None:
    """Run the engine in a child process and restart it whenever code in crcontent/ or web/ changes.

    uvicorn's own reloader asks the old server to stop with Ctrl+C, which never arrives on Windows when the engine is
    started without a console (npm run dev, the desktop app): the old code then keeps serving forever. Killing the
    child always works, and --parent-pid makes the child exit with this process.
    """
    from watchfiles import PythonFilter, watch

    cmd = [sys.executable, os.path.abspath(__file__), "--no-browser", "--port", str(port), "--parent-pid", str(os.getpid())]
    root = os.path.dirname(os.path.abspath(__file__))
    child = subprocess.Popen(cmd, cwd=root)
    try:
        for changes in watch(os.path.join(root, "crcontent"), os.path.join(root, "web"), watch_filter=PythonFilter()):
            names = ", ".join(sorted({os.path.relpath(path, root) for _, path in changes}))
            print(f"Code changed ({names}); restarting the engine", flush=True)
            child.kill()
            child.wait()
            child = subprocess.Popen(cmd, cwd=root)
    finally:
        child.kill()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--reload", action="store_true")
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--parent-pid", type=int)
    args = p.parse_args()

    from crcontent.config import ROOT
    load_dotenv(ROOT / ".env")
    if args.parent_pid:
        threading.Thread(target=_exit_with_parent, args=(args.parent_pid,), daemon=True).start()
    if not args.no_browser and not args.reload:
        webbrowser.open(f"http://127.0.0.1:{args.port}")
    if args.reload:
        _serve_with_reload(args.port)
    else:
        # graceful-shutdown cap: an open video stream must not block shutting down
        from crcontent.web import app
        uvicorn.run(app, host="127.0.0.1", port=args.port, timeout_graceful_shutdown=3)
