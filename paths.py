"""Bundled read-only resources and writable history are separate locations."""

import os
from pathlib import Path
import sys

# PyInstaller sets __file__ to a location inside its resource directory.
RESOURCE_DIR = Path(__file__).resolve().parent


def user_data_dir():
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "PaperSift"


def history_path():
    # Keep existing development topics exactly where they already are.
    folder = user_data_dir() if getattr(sys, "frozen", False) else RESOURCE_DIR / "data"
    return folder / "history.json"
