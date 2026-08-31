"""Mind Desktop — native window wrapping the local Mind API.

Starts uvicorn (if not already running), then opens a native window
(pywebview → Edge WebView2 on Windows). Falls back to the default browser
if pywebview is unavailable.

Usage:  python mind_desktop.py
"""
from __future__ import annotations

import os
import sys
import time
import threading
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BAQA = os.path.join(BASE_DIR, "baqa")
PORT = 8001
URL = f"http://127.0.0.1:{PORT}/dashboard"


def api_up() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
            return r.status == 200
    except OSError:
        return False


def start_api():
    if api_up():
        return
    import subprocess
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app",
         "--port", str(PORT), "--host", "127.0.0.1"],
        cwd=BAQA,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def main():
    start_api()
    # wait for readiness
    for _ in range(40):
        if api_up():
            break
        time.sleep(0.5)
    if not api_up():
        print("Mind API failed to start on port", PORT)
        sys.exit(1)

    try:
        import webview
    except ImportError:
        print("pywebview not installed — opening browser instead")
        import webbrowser
        webbrowser.open(URL)
        return

    webview.create_window(
        "Mind — OneAgent SuperApp",
        URL,
        width=1280, height=840, min_size=(900, 600),
        background_color="#0b0e14",
    )
    webview.start()


if __name__ == "__main__":
    main()
