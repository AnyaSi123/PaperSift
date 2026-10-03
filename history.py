"""Local topic snapshots. A lock and temporary file keep saves safe and simple."""

import json
import os
from pathlib import Path
import re
import tempfile
import threading
from datetime import datetime, timezone
from uuid import uuid4

HISTORY_LOCK = threading.RLock()
LABELS = ("supporting", "conflicting", "nuanced", "unclear")


class HistoryError(Exception):
    """A history problem that can be shown without losing the current search."""


def normalized_query(query):
    return " ".join(query.split()).casefold()


def topic_title(query, demo):
    title = " ".join(query.split()).rstrip("?.")
    title = re.sub(r"^(does|do|can|is|are|will)\s+", "", title, flags=re.I)
    if len(title) > 65:
        title = title[:62].rsplit(" ", 1)[0] + "…"
    title = title[:1].upper() + title[1:]
    return ("[Demo] " if demo else "") + title


def valid_topic(topic):
    # Validate the fields the page uses; malformed data must not break rendering.
    if not isinstance(topic, dict):
        return False
    if not all(isinstance(topic.get(key), str) and topic[key]
               for key in ("id", "title", "query", "created_at")):
        return False
    result = topic.get("results")
    if not isinstance(result, dict):
        return False
    if result.get("question") != topic["query"] or type(result.get("demo")) is not bool:
        return False
    if not isinstance(result.get("search_terms"), str):
        return False
    papers = result.get("papers")
    if not isinstance(papers, list) or not papers:
        return False
    fields = ("title", "authors", "year", "venue", "abstract", "excerpt", "doi",
              "funding", "disclosure", "sample_size", "p_value", "confidence_interval", "study_type")
    for paper in papers:
        if not isinstance(paper, dict) or not all(isinstance(paper.get(key), str) for key in fields):
            return False
        if paper.get("classification") not in LABELS or not isinstance(paper.get("url", ""), str):
            return False
    expected = {label: sum(p["classification"] == label for p in papers) for label in LABELS}
    return result.get("counts") == expected


def read_topics(path):
    with HISTORY_LOCK:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            topics = data["topics"]
            if not isinstance(topics, list) or not all(valid_topic(t) for t in topics):
                raise ValueError("Invalid topic data")
            if len({t["id"] for t in topics}) != len(topics):
                raise ValueError("Duplicate IDs")
            return topics  # New topics are inserted first when saved.
        except FileNotFoundError:
            return []
        except (ValueError, KeyError, TypeError, UnicodeError) as error:
            raise HistoryError(f"Saved topics could not be read. Your history file was left unchanged. Move {path} aside to start fresh, or restore a valid backup.") from error
        except OSError as error:
            raise HistoryError("Cannot access saved topics. Check that the data folder is readable and writable.") from error


def write_topics(path, topics):
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Replace only after a complete write. An interrupted write keeps the old file.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="history-", suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            json.dump({"topics": topics}, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise HistoryError("Could not save topic changes. Check free disk space and permissions for the data folder.") from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass  # A leftover temporary file never replaces valid history.


def find_topic(path, query, demo):
    return next((topic for topic in read_topics(path)
                 if normalized_query(topic["query"]) == normalized_query(query)
                 and topic["results"]["demo"] == demo), None)


def save_topic(path, result):
    if not result["papers"]:
        return None
    with HISTORY_LOCK:
        topics = read_topics(path)
        # Recheck under the lock in case two tabs searched the same question.
        for topic in topics:
            if (normalized_query(topic["query"]) == normalized_query(result["question"])
                    and topic["results"]["demo"] == result["demo"]):
                return topic
        topic = {"id": str(uuid4()), "title": topic_title(result["question"], result["demo"]),
                 "query": result["question"], "created_at": datetime.now(timezone.utc).isoformat(),
                 "results": result}
        write_topics(path, [topic, *topics])
        return topic


def delete_topic(path, topic_id):
    with HISTORY_LOCK:
        topics = read_topics(path)
        remaining = [topic for topic in topics if topic["id"] != topic_id]
        if len(remaining) == len(topics):
            return False
        write_topics(path, remaining)
        return True
