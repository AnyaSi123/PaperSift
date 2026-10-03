"""Small, deliberately limited rules; this is text matching, not an AI model."""

import re

NOT_REPORTED = "Not reported"


def find_values(pattern, abstract):
    matches = re.finditer(pattern, abstract, flags=re.I)
    return "; ".join(dict.fromkeys(match.group().strip() for match in matches)) or NOT_REPORTED


def extract_statistics(abstract):
    # Preserve the matched text, including inequality signs and multiple values.
    number = r"(?:\d{1,3}(?:[, \u00a0]\d{3})+|\d+)"
    value = r"[-−+]?\d*\.?\d+"
    return {
        "sample_size": find_values(rf"\b[nN]\s*=\s*{number}\b|(?<![\d.,])\b{number}\s+(?:participants|patients|subjects|students|adolescents|teenagers|children|adults)\b", abstract),
        "p_value": find_values(r"\bp\s*(?:<=|>=|[<>=≤≥])\s*(?:0?\.\d+|1(?:\.0+)?)(?:\s*[eE][-+]?\d+)?\b", abstract),
        "confidence_interval": find_values(rf"\b\d{{2}}%\s*(?:CI|confidence interval)\b(?:\s*[:=]?\s*[\[(]?\s*{value}\s*(?:to|[–−—,\-])\s*{value}\s*[\])]?)?", abstract),
    }


def identify_study_type(abstract, publication_types):
    patterns = [
        (r"\bmeta[- ]analysis\b", "Meta-Analysis"),
        (r"\bsystematic review\b", "Systematic Review"),
        (r"\brandomi[sz]ed controlled trial\b", "Randomized Controlled Trial"),
        (r"\bcross[- ]sectional (?:study|studies|survey|analysis)\b", "Cross-Sectional Study"),
        (r"\bcohort study\b", "Cohort Study"),
        (r"\bobservational study\b", "Observational Study"),
    ]
    # Metadata is stronger than an abstract mentioning a different study.
    for source in (" ".join(publication_types), abstract):
        found = [label for pattern, label in patterns if re.search(pattern, source, re.I)]
        if found:
            return "; ".join(found)
    return "Not identified"


def topic_words(text):
    ignored = set("does do can will the a an of to use using level levels amount more less".split())
    return [word for word in re.findall(r"[a-z]+", text.lower()) if word not in ignored]


def classify_paper(question, abstract):
    """Return a provisional bucket. Replace this function to add an LLM later.

    Only simple 'Does X increase/decrease Y?' questions are understood. Require
    exposure and outcome words in the same results/conclusion sentence. A null
    association weakens either directional hypothesis; it does not prove no effect.
    """
    question = question.lower().strip(" ?.")
    if re.search(r"\b(not|no|prevent|cause|causes)\b", question):
        return "unclear"  # Negation and causal claims need more than these rules.
    hypothesis = re.fullmatch(r"(?:does |do |can |will )?(.+?)\s+(increase|increases|decrease|decreases|reduce|reduces|improve|improves|worsen|worsens)\s+(.+)", question)
    if not hypothesis or not abstract:
        return "unclear"
    exposure, verb, outcome = hypothesis.groups()
    outcome = re.split(r"\b(?:in|among|for)\b", outcome)[0]
    exposure_words, outcome_words = topic_words(exposure), topic_words(outcome)
    if not exposure_words or not outcome_words:
        return "unclear"
    # 'Improve' and 'worsen' are ambiguous without understanding the outcome.
    if verb.startswith(("improve", "worsen")):
        return "unclear"
    expected = "up" if verb.startswith("increase") else "down"
    # Focus on reported findings, not the introduction's description of prior work.
    sections = re.split(r"\b(?:results?|conclusions?|findings)\s*:", abstract, flags=re.I)
    if len(sections) < 2:
        return "unclear"
    findings = " ".join(sections[1:]).lower()
    votes = set()
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", findings):
        words = set(re.findall(r"[a-z]+", sentence))
        if not all(word in words for word in exposure_words + outcome_words):
            continue
        if re.search(r"\b(mixed|inconsistent|varied|however|but|only|may|might|could|uncertain)\b", sentence):
            votes.add("nuanced")
        elif re.search(r"\bno (?:significant |statistically significant )?(?:association|relationship|difference|effect)\b|\bnot (?:significantly )?associated\b", sentence):
            votes.add("conflicting")
        elif not re.search(r"\b(no|not|without|hypothesized|expected)\b", sentence):
            # A direction must immediately describe the outcome, not the exposure.
            outcome_pattern = r"\s+".join(re.escape(word) for word in outcome_words)
            up = re.search(rf"\b(?:higher|increased|greater|increase in)\s+{outcome_pattern}\b", sentence)
            down = re.search(rf"\b(?:lower|decreased|reduced|decrease in)\s+{outcome_pattern}\b", sentence)
            if up and down:
                votes.add("nuanced")
            elif up or down:
                direction = "up" if up else "down"
                votes.add("supporting" if direction == expected else "conflicting")
    if "nuanced" in votes or len(votes) > 1:
        return "nuanced"
    return next(iter(votes)) if votes else "unclear"


def analyze_paper(question, paper):
    paper = dict(paper)
    abstract = paper.get("abstract", "")
    paper.update(extract_statistics(abstract))
    paper["study_type"] = identify_study_type(abstract, paper.get("publication_types", []))
    paper["classification"] = classify_paper(question, abstract)
    # This is a verbatim excerpt, never a generated scientific conclusion.
    paper["excerpt"] = abstract[:450] + ("…" if len(abstract) > 450 else "") if abstract else NOT_REPORTED
    for field in ("authors", "year", "venue", "doi", "funding", "disclosure"):
        paper.setdefault(field, NOT_REPORTED)
    return paper
