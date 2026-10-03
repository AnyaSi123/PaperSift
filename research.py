"""Search PubMed, then fetch up to 12 abstracts. No API key is needed."""

import re
import threading
import time
import xml.etree.ElementTree as ET

import requests

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
API_LOCK = threading.Lock()
last_request = 0.0


class SearchError(Exception):
    """An understandable message the page can show instead of a traceback."""


def api_get(endpoint, params):
    global last_request
    # NCBI allows 3 requests/second without a key. Space calls across browser tabs.
    with API_LOCK:
        time.sleep(max(0, 0.4 - (time.monotonic() - last_request)))
        last_request = time.monotonic()
        response = requests.get(BASE_URL + endpoint, params={"tool": "PaperSift", **params},
                                timeout=20)
    response.raise_for_status()
    return response


def make_search_terms(question):
    # Remove question framing and directional claims so the search does not
    # deliberately ask PubMed for only papers agreeing with the hypothesis.
    words = re.findall(r"[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)?", question.lower())
    filler = set("does do did is are was were can could would will should the a an "
                 "of to in on for with and or how what whether between among than "
                 "have has having affect affects effect effects impact impacts "
                 "increase increases increased decrease decreases decreased "
                 "reduce reduces reduced cause causes causing lead leads "
                 "negatively positively improve improves worsen worsens "
                 "not no associated association relationship use using".split())
    return " ".join(word for word in words if word not in filler)


def node_text(node):
    return " ".join("".join(node.itertext()).split()) if node is not None else ""


def parse_papers(xml):
    root = ET.fromstring(xml)
    if root.find(".//ERROR") is not None:
        raise SearchError("PubMed could not complete this search. Try fewer topic words.")
    papers = []
    for record in root.findall("PubmedArticle"):
        article = record.find("MedlineCitation/Article")
        if article is None:
            continue
        pmid = node_text(record.find("MedlineCitation/PMID"))
        paragraphs = []
        for part in article.findall("Abstract/AbstractText"):
            label = part.get("Label", "")
            paragraphs.append((label + ": " if label else "") + node_text(part))
        authors = []
        for author in article.findall("AuthorList/Author"):
            name = node_text(author.find("CollectiveName")) or " ".join(filter(None, [
                node_text(author.find("ForeName")), node_text(author.find("LastName"))]))
            if name:
                authors.append(name)
        date = article.find("Journal/JournalIssue/PubDate")
        year = node_text(date.find("Year")) if date is not None else ""
        if not year and date is not None:
            match = re.search(r"\b(?:19|20)\d{2}\b", node_text(date))
            year = match.group() if match else ""
        doi = ""
        for identifier in record.findall("PubmedData/ArticleIdList/ArticleId"):
            if identifier.get("IdType") == "doi":
                doi = node_text(identifier)
        grants = []
        for grant in article.findall("GrantList/Grant"):
            grants.append(" — ".join(filter(None, [node_text(grant.find("Agency")),
                                                     node_text(grant.find("GrantID"))])))
        papers.append({
            "title": node_text(article.find("ArticleTitle")) or "Not reported",
            "authors": ", ".join(authors) or "Not reported",
            "year": year or "Not reported",
            "abstract": "\n\n".join(paragraphs),
            "venue": node_text(article.find("Journal/Title")) or "Not reported",
            "doi": doi or "Not reported",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            "funding": "; ".join(filter(None, grants)) or "Not reported",
            "disclosure": node_text(record.find("MedlineCitation/CoiStatement")) or "Not reported",
            "publication_types": [node_text(p) for p in article.findall("PublicationTypeList/PublicationType")],
        })
    return papers


def search_pubmed(question):
    terms = make_search_terms(question)
    if not terms:
        raise SearchError("Please include a topic, such as social media and depression.")
    try:
        result = api_get("esearch.fcgi", {"db": "pubmed", "term": terms,
                         "retmode": "json", "retmax": 12, "sort": "relevance"}).json()
        search = result.get("esearchresult")
        if not isinstance(search, dict) or "idlist" not in search or search.get("ERROR"):
            raise ValueError("Missing search results")
        ids = search["idlist"]
        if not ids:
            return [], terms
        response = api_get("efetch.fcgi", {"db": "pubmed", "id": ",".join(ids),
                           "retmode": "xml"})
        return parse_papers(response.content), terms
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 429:
            raise SearchError("PubMed is receiving too many requests. Wait a minute and try again, or use the offline demo.") from error
        raise SearchError("PubMed is temporarily unavailable. Please try again later or use the offline demo.") from error
    except (requests.RequestException, ValueError, ET.ParseError, TypeError, KeyError) as error:
        raise SearchError("We could not read a response from PubMed. Check your internet connection, try again, or use the offline demo.") from error
