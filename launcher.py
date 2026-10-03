"""Standalone entry point: start the existing Flask app and open a browser."""

import logging
import secrets
import sys
import threading
import time
import traceback
from urllib.request import urlopen
import webbrowser

from werkzeug.serving import make_server

from app import app
from paths import user_data_dir


def lock_instance(file):
    """Prevent two packaged processes writing the same history at once.

    The OS releases this lock even if PaperSift crashes. Keep the file open
    for the lifetime of the app; do not delete the lock file on shutdown.
    """
    file.seek(0)
    if sys.platform == "win32":
        import msvcrt
        msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def open_when_ready(url):
    for _ in range(50):
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except OSError:
            time.sleep(0.1)


def main():
    folder = user_data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    address = folder / "address.txt"
    with (folder / "instance.lock").open("a+b") as lock:
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        try:
            lock_instance(lock)
        except OSError:
            # A second launch just opens the existing instance's browser page.
            for _ in range(30):
                if address.exists():
                    url = address.read_text(encoding="utf-8").strip()
                    if url.startswith("http://127.0.0.1:"):
                        open_when_ready(url)
                        return
                time.sleep(0.1)
            return

        # Port 0 asks the OS for a free port, avoiding port 5000 conflicts.
        app.config["TRUSTED_HOSTS"] = ["127.0.0.1", "localhost"]
        app.config["QUIT_TOKEN"] = secrets.token_urlsafe(32)
        logging.getLogger("werkzeug").disabled = True
        server = make_server("127.0.0.1", 0, app, threaded=True)
        app.config["SHUTDOWN"] = server.shutdown
        url = f"http://127.0.0.1:{server.server_port}/"
        address.write_text(url, encoding="utf-8")
        threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()
        try:
            server.serve_forever()
        finally:
            server.server_close()
            address.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # A windowless build still leaves an understandable way to diagnose failure.
        error_file = user_data_dir() / "startup-error.txt"
        error_file.parent.mkdir(parents=True, exist_ok=True)
        error_file.write_text("PaperSift could not start.\n\n" + traceback.format_exc(), encoding="utf-8")
        webbrowser.open(error_file.as_uri())
