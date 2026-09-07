"""
RentFlow desktop launcher (Windows .exe entry point and source runner).

It starts the bundled Django development server on a free localhost port in a
background thread, then opens that URL inside a native window via pywebview
(Edge WebView2 on Windows — the runtime that ships with Windows 10/11).

Run from source:        python run_desktop.py
Build the Windows app:  see scripts/build_windows.bat (uses PyInstaller)
"""

import os
import socket
import sys
import threading
import time

import webview


def _resource_root():
    """Folder containing templates/static (handles PyInstaller frozen mode)."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS  # noqa: SLF001
    return os.path.dirname(os.path.abspath(__file__))


def _free_port(preferred=8765):
    for port in (preferred,) + tuple(range(8766, 8820)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return 0  # let the OS choose


def start_server(port):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, _resource_root())

    import django
    django.setup()

    from django.core.management import call_command

    # Ensure DB schema exists (first run on a fresh machine).
    call_command("migrate", interactive=False, verbosity=0)

    server_thread = threading.Thread(
        target=call_command,
        kwargs={"runserver": None, "addrport": f"127.0.0.1:{port}",
                "use_reloader": False, "use_threading": True, "verbosity": 0},
        daemon=True,
    )
    server_thread.start()

    # Wait for the port to answer before opening the window.
    import urllib.request
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/login/", timeout=2)
            return
        except Exception:
            time.sleep(0.3)


def main():
    port = _free_port()
    start_server(port)
    url = f"http://127.0.0.1:{port}/"

    webview.create_window(
        title="RentFlow — Property Management",
        url=url,
        width=1440,
        height=900,
        min_size=(1024, 680),
        background_color="#f6f8fb",
    )
    webview.start(gui="edgechromium" if sys.platform.startswith("win") else None)


if __name__ == "__main__":
    main()
