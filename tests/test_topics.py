"""Topic tests use temporary folders, never the user's research history."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import app
from history import read_topics
from research import SearchError

QUESTION = "Does social media use increase depression in teenagers?"


class TopicTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "data" / "history.json"
        config = patch.dict(app.config, HISTORY_PATH=self.path)
        config.start()
        self.addCleanup(config.stop)
        self.client = app.test_client()
        self.papers = json.loads(Path("demo.json").read_text(encoding="utf-8"))["papers"]

    def search(self, query=QUESTION):
        with patch("app.search_pubmed", return_value=(self.papers, "topic words")):
            response = self.client.post("/api/search", json={"question": query})
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_success_creates_complete_snapshot_and_reads_back(self):
        result = self.search()
        topic = read_topics(self.path)[0]
        self.assertEqual(topic["id"], result["topic_id"])
        self.assertEqual(topic["query"], QUESTION)
        self.assertTrue(topic["created_at"])
        self.assertTrue(topic["title"])
        for key in ("question", "papers", "counts", "demo", "search_terms"):
            self.assertEqual(topic["results"][key], result[key])
        # A fresh client reads only the file, with no API call or re-analysis.
        with patch("app.search_pubmed", side_effect=AssertionError("Must be offline")), \
                patch("app.analyze_paper", side_effect=AssertionError("Keep original analysis")):
            loaded = app.test_client().get("/api/topics/" + topic["id"]).get_json()
        self.assertEqual(loaded["papers"], result["papers"])
        self.assertEqual(loaded["counts"], result["counts"])
        self.assertTrue(loaded["restored"])

    def test_missing_file_starts_empty(self):
        self.assertEqual(self.client.get("/api/topics").get_json(), {"topics": []})
        self.assertFalse(self.path.exists())
        self.assertEqual(self.client.get("/api/topics/missing").status_code, 404)
        self.assertEqual(self.client.delete("/api/topics/missing").status_code, 404)

    def test_newest_first_and_delete_only_one(self):
        first = self.search()
        second = self.search("Does exercise reduce blood pressure?")
        listed = self.client.get("/api/topics").get_json()["topics"]
        self.assertEqual([t["id"] for t in listed], [second["topic_id"], first["topic_id"]])
        self.assertNotIn("results", listed[0])
        self.assertEqual(self.client.delete("/api/topics/" + first["topic_id"]).status_code, 200)
        remaining = read_topics(self.path)
        self.assertEqual([t["id"] for t in remaining], [second["topic_id"]])
        self.assertEqual(remaining[0]["results"]["papers"], second["papers"])

    def test_duplicate_case_and_whitespace_reopens_without_api(self):
        first = self.search()
        with patch("app.search_pubmed", side_effect=AssertionError("Do not repeat search")):
            second = self.client.post("/api/search", json={"question": "  DOES social   media use\n increase depression in teenagers?  "}).get_json()
        self.assertEqual(second["topic_id"], first["topic_id"])
        self.assertEqual(second["question"], QUESTION)
        self.assertEqual(second["papers"], first["papers"])
        self.assertTrue(second["restored"])
        self.assertEqual(len(read_topics(self.path)), 1)

    def test_demo_and_live_same_question_are_separate(self):
        live = self.search()
        demo = self.client.post("/api/search", json={"question": QUESTION, "demo": True}).get_json()
        self.assertNotEqual(live["topic_id"], demo["topic_id"])
        topics = read_topics(self.path)
        self.assertTrue(topics[0]["title"].startswith("[Demo]"))
        again = self.client.post("/api/search", json={"question": "Another demo question", "demo": True}).get_json()
        self.assertEqual(again["topic_id"], demo["topic_id"])
        self.assertEqual(len(read_topics(self.path)), 2)

    def test_failed_and_empty_searches_do_not_save(self):
        for outcome in (SearchError("Unavailable"), ([], "nothing")):
            with patch("app.search_pubmed") as search:
                if isinstance(outcome, Exception):
                    search.side_effect = outcome
                else:
                    search.return_value = outcome
                response = self.client.post("/api/search", json={"question": QUESTION})
            self.assertIn(response.status_code, (200, 502))
            self.assertEqual(read_topics(self.path), [])
        self.assertFalse(self.path.exists())

    def test_malformed_history_is_preserved_and_search_still_works(self):
        self.path.parent.mkdir()
        for broken in ('{broken', '[]', '{"topics": null}', '{"topics": [{}]}'):
            with self.subTest(broken=broken):
                self.path.write_text(broken, encoding="utf-8")
                self.assertEqual(self.client.get("/api/topics").status_code, 503)
                self.assertEqual(self.client.delete("/api/topics/any").status_code, 503)
                result = self.search()
                self.assertIsNone(result["topic_id"])
                self.assertTrue(result["warning"])
                self.assertEqual(len(result["papers"]), 6)
                self.assertEqual(self.path.read_text(encoding="utf-8"), broken)

    def test_invalid_paper_snapshot_does_not_crash_page(self):
        self.search()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        data["topics"][0]["results"]["papers"][0]["classification"] = "unknown-label"
        self.path.write_text(json.dumps(data), encoding="utf-8")
        response = self.client.get("/api/topics")
        self.assertEqual(response.status_code, 503)
        self.assertIn("left unchanged", response.get_json()["error"])

    def test_failed_replace_keeps_previous_history(self):
        first = self.search()
        original = self.path.read_bytes()
        with patch("history.os.replace", side_effect=PermissionError("Test failure")):
            result = self.search("Does exercise reduce blood pressure?")
            deletion = self.client.delete("/api/topics/" + first["topic_id"])
        self.assertEqual(deletion.status_code, 503)
        self.assertIsNone(result["topic_id"])
        self.assertIn("Could not save", result["warning"])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
