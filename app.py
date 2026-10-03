"""PaperSift's small local web server. Run with: python app.py"""

import json
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from analysis import analyze_paper
from research import SearchError, search_pubmed

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8_000


@app.get("/")
def index():
    return render_template("index.html")


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
        sample = json.loads(Path(__file__).with_name("demo.json").read_text(encoding="utf-8"))
        question, papers = sample["question"], sample["papers"]
        search_terms = "Offline sample — no PubMed search performed"
    else:
        try:
            papers, search_terms = search_pubmed(question)
        except SearchError as error:
            return jsonify(error=str(error)), 502

    papers = [analyze_paper(question, paper) for paper in papers]
    counts = {label: 0 for label in ("supporting", "conflicting", "nuanced", "unclear")}
    for paper in papers:
        counts[paper["classification"]] += 1
    return jsonify(question=question, papers=papers, counts=counts,
                   demo=demo, search_terms=search_terms)


@app.errorhandler(413)
def too_large(error):
    return jsonify(error="That request is too long. Please shorten your question."), 413


if __name__ == "__main__":
    # Loopback keeps this classroom project on your own computer.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
