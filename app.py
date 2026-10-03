"""PaperSift's small local web server. Run with: python app.py"""

import json
import os
import secrets
import threading

from flask import Flask, jsonify, render_template, request

from analysis import analyze_paper
from research import SearchError, search_pubmed
from history import HistoryError, delete_topic, find_topic, read_topics, save_topic
from paths import RESOURCE_DIR, history_path

app = Flask(__name__, template_folder=str(RESOURCE_DIR / "templates"),
            static_folder=str(RESOURCE_DIR / "static"))
app.config["MAX_CONTENT_LENGTH"] = 8_000
app.config["HISTORY_PATH"] = history_path()


@app.get("/")
def index():
    return render_template("index.html", quit_token=app.config.get("QUIT_TOKEN"))


@app.post("/api/quit")
def quit_app():
    # Only the standalone launcher provides this callback and per-run token.
    shutdown = app.config.get("SHUTDOWN")
    if shutdown is None:
        return jsonify(error="Stop the source server with Ctrl+C in its terminal."), 404
    token = request.headers.get("X-PaperSift-Quit", "")
    if not secrets.compare_digest(token, app.config["QUIT_TOKEN"]):
        return jsonify(error="Please use the Quit button in PaperSift."), 403
    threading.Thread(target=shutdown, daemon=True).start()
    return jsonify(stopped=True)


@app.get("/api/topics")
def topics():
    saved = read_topics(app.config["HISTORY_PATH"])
    return jsonify(topics=[{key: topic[key] for key in ("id", "title", "query", "created_at")}
                           for topic in saved])


@app.get("/api/topics/<topic_id>")
def load_topic(topic_id):
    topic = next((t for t in read_topics(app.config["HISTORY_PATH"]) if t["id"] == topic_id), None)
    if topic is None:
        return jsonify(error="This topic no longer exists."), 404
    return jsonify(**topic["results"], topic_id=topic["id"], restored=True)


@app.delete("/api/topics/<topic_id>")
def remove_topic(topic_id):
    if not delete_topic(app.config["HISTORY_PATH"], topic_id):
        return jsonify(error="This topic no longer exists."), 404
    return jsonify(deleted=topic_id)


@app.errorhandler(HistoryError)
def history_error(error):
    return jsonify(error=str(error)), 503


@app.post("/api/search")
def search():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Please send a research question."), 400
    demo = data.get("demo") is True
    question = data.get("question", "")
    if not isinstance(question, str) or not 5 <= len(question.strip()) <= 500:
        return jsonify(error="Enter a question between 5 and 500 characters."), 400
    question = question.strip()

    if demo:
        sample = json.loads((RESOURCE_DIR / "demo.json").read_text(encoding="utf-8"))
        question, papers = sample["question"], sample["papers"]
        search_terms = "Offline sample — no PubMed search performed"

    # Reopening a duplicate preserves its original data and avoids a PubMed call.
    warning = None
    try:
        existing = find_topic(app.config["HISTORY_PATH"], question, demo)
        if existing:
            return jsonify(**existing["results"], topic_id=existing["id"], restored=True)
    except HistoryError as error:
        warning = str(error)

    if not demo:
        try:
            papers, search_terms = search_pubmed(question)
        except SearchError as error:
            return jsonify(error=str(error)), 502

    papers = [analyze_paper(question, paper) for paper in papers]
    counts = {label: 0 for label in ("supporting", "conflicting", "nuanced", "unclear")}
    for paper in papers:
        counts[paper["classification"]] += 1
    result = dict(question=question, papers=papers, counts=counts,
                  demo=demo, search_terms=search_terms)
    topic = None
    if papers and not warning:
        try:
            topic = save_topic(app.config["HISTORY_PATH"], result)
        except HistoryError as error:
            warning = str(error)
    if topic:
        return jsonify(**topic["results"], topic_id=topic["id"], restored=False)
    return jsonify(**result, topic_id=None, warning=warning)


@app.errorhandler(413)
def too_large(error):
    return jsonify(error="That request is too long. Please shorten your question."), 413


if __name__ == "__main__":
    # Loopback keeps this classroom project on your own computer.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
