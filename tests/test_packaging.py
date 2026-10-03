"""Checks for paths and launcher behavior; actual builds still need OS testing."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import app
from launcher import open_when_ready
from paths import RESOURCE_DIR, history_path, user_data_dir


class PackagingTests(unittest.TestCase):
    def test_source_history_stays_in_project(self):
        with patch("paths.sys.frozen", False, create=True):
            self.assertEqual(history_path(), RESOURCE_DIR / "data" / "history.json")

    def test_windows_packaged_history_is_outside_resources(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch("paths.sys.platform", "win32"), \
                patch("paths.sys.frozen", True, create=True), \
                patch.dict(os.environ, LOCALAPPDATA=folder):
            expected = Path(folder) / "PaperSift" / "history.json"
            self.assertEqual(history_path(), expected)
            self.assertFalse(expected.exists())

    def test_mac_data_path(self):
        with patch("paths.sys.platform", "darwin"):
            self.assertEqual(user_data_dir(), Path.home() / "Library" / "Application Support" / "PaperSift")

    def test_resources_available_and_quit_hidden_for_source(self):
        client = app.test_client()
        page = client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertNotIn(b'id="quit-button"', page.data)
        self.assertIn(b'class="workspace"', page.data)
        for resource in ("style.css", "script.js"):
            with client.get("/static/" + resource) as response:
                self.assertEqual(response.status_code, 200)
        self.assertTrue((RESOURCE_DIR / "demo.json").is_file())
        self.assertEqual(client.post("/api/quit").status_code, 404)

    def test_quit_requires_per_run_token(self):
        with patch.dict(app.config, QUIT_TOKEN="test-only-token", SHUTDOWN=lambda: None), \
                patch("app.threading.Thread") as thread:
            client = app.test_client()
            self.assertIn(b'id="quit-button"', client.get("/").data)
            self.assertEqual(client.post("/api/quit").status_code, 403)
            thread.assert_not_called()
            self.assertEqual(client.post("/api/quit", headers={"X-PaperSift-Quit": "test-only-token"}).status_code, 200)
            thread.return_value.start.assert_called_once()

    def test_browser_waits_for_ready_server(self):
        with patch("launcher.urlopen") as get, patch("launcher.webbrowser.open") as browser, \
                patch("launcher.time.sleep"):
            get.return_value.__enter__.return_value.status = 200
            open_when_ready("http://127.0.0.1:54321/")
            browser.assert_called_once_with("http://127.0.0.1:54321/")
            browser.reset_mock()
            get.side_effect = OSError("Not ready")
            open_when_ready("http://127.0.0.1:54321/")
            browser.assert_not_called()


if __name__ == "__main__":
    unittest.main()
