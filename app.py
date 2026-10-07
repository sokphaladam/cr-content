"""Start the web UI:  python app.py   (then open http://127.0.0.1:8000)"""
import sys
import webbrowser

import uvicorn
from dotenv import load_dotenv

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    reload = "--reload" in sys.argv
    if "--no-browser" not in sys.argv and not reload:
        webbrowser.open("http://127.0.0.1:8000")
    # graceful-shutdown cap: an open video stream must not block a code reload forever
    uvicorn.run("crcontent.web:app", host="127.0.0.1", port=8000, reload=reload, timeout_graceful_shutdown=3,
                reload_dirs=["crcontent", "web"] if reload else None)
