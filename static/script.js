// All paper text is inserted with textContent, so external abstracts are not HTML.
const questionInput = document.querySelector("#question");
const statusText = document.querySelector("#status");
const errorText = document.querySelector("#error");
const results = document.querySelector("#results");
const example = "Does social media use increase depression in teenagers?";
let currentResults = null;
let currentTopicId = null;
let savedTopics = [];
let busy = false;
const topicsError = document.querySelector("#topics-error");

function setBusy(value) {
  busy = value;
  document.querySelectorAll("#search-form button, #example-button, .topics-panel button")
    .forEach(button => { button.disabled = value; });
  questionInput.disabled = value;
}

function renderTopics() {
  const list = document.querySelector("#topic-list");
  list.replaceChildren();
  document.querySelector("#topics-empty").textContent = savedTopics.length ? "" : "No saved topics yet. Search for papers to create one.";
  for (const topic of savedTopics) {
    const row = element("li", undefined, "topic-row");
    const open = element("button", topic.title, "topic-open");
    open.type = "button";
    open.title = topic.query;
    open.setAttribute("aria-current", String(topic.id === currentTopicId));
    open.append(element("span", new Date(topic.created_at).toLocaleString(), "topic-date"));
    open.addEventListener("click", () => openTopic(topic.id));
    const remove = element("button", "Delete", "topic-delete");
    remove.type = "button";
    remove.setAttribute("aria-label", `Delete topic: ${topic.title}`);
    remove.addEventListener("click", () => removeTopic(topic.id));
    open.disabled = remove.disabled = busy;
    row.append(open, remove);
    list.append(row);
  }
}

async function topicRequest(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Could not access saved topics.");
  return data;
}

async function refreshTopics() {
  try {
    const data = await topicRequest("/api/topics");
    savedTopics = data.topics;
    renderTopics();
    topicsError.hidden = true;
  } catch (error) {
    topicsError.textContent = error.message;
    topicsError.hidden = false;
    document.querySelector("#topics-empty").textContent = "Saved topics are unavailable. You can still search.";
  }
}

function newResearch() {
  currentResults = null;
  currentTopicId = null;
  questionInput.value = "";
  results.hidden = true;
  errorText.hidden = true;
  statusText.textContent = "Enter a question above, or explore the offline sample.";
  renderTopics();
  questionInput.focus();
}

async function openTopic(id) {
  if (busy) return;
  setBusy(true);
  errorText.hidden = true;
  try {
    showResults(await topicRequest(`/api/topics/${encodeURIComponent(id)}`));
    topicsError.hidden = true;
  } catch (error) {
    topicsError.textContent = error.message;
    topicsError.hidden = false;
  } finally {
    setBusy(false);
  }
}

async function removeTopic(id) {
  if (busy) return;
  setBusy(true);
  try {
    await topicRequest(`/api/topics/${encodeURIComponent(id)}`, { method: "DELETE" });
    savedTopics = savedTopics.filter(topic => topic.id !== id);
    if (id === currentTopicId) newResearch();
    renderTopics();
    topicsError.hidden = true;
  } catch (error) {
    topicsError.textContent = error.message;
    topicsError.hidden = false;
  } finally {
    setBusy(false);
    if (!currentTopicId) questionInput.focus();
  }
}

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function paperCard(paper, demo) {
  const card = element("article", undefined, "paper-card");
  card.append(element("span", `${paper.classification} · heuristic`, `badge ${paper.classification}`));
  card.append(element("h3", paper.title));
  card.append(element("p", paper.authors, "meta"));
  card.append(element("p", `${paper.year} · ${paper.venue}`, "meta"));
  if (demo) card.append(element("p", "FICTIONAL SAMPLE — do not cite", "meta"));
  card.append(element("div", "ABSTRACT EXCERPT · verbatim", "excerpt-label"));
  card.append(element("p", paper.excerpt, "excerpt"));
  const facts = element("dl");
  for (const [label, key] of [["Sample size(s)", "sample_size"], ["p-value(s)", "p_value"],
    ["Confidence interval(s)", "confidence_interval"], ["Study type", "study_type"]]) {
    const row = element("div");
    row.append(element("dt", label), element("dd", paper[key]));
    facts.append(row);
  }
  card.append(facts);
  const details = element("details");
  details.append(element("summary", "Full abstract & disclosures"));
  details.append(element("p", paper.abstract || "Abstract: Not reported", "full-abstract"));
  details.append(element("p", `Funding (PubMed grant metadata): ${paper.funding}`));
  details.append(element("p", `Disclosure: ${paper.disclosure}`));
  details.append(element("p", `DOI: ${paper.doi}`));
  card.append(details);
  if (!demo && paper.url && /^https:\/\/pubmed\.ncbi\.nlm\.nih\.gov\/\d+\/$/.test(paper.url)) {
    const link = element("a", "Read original on PubMed ↗", "paper-link");
    link.href = paper.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    card.append(link);
  } else {
    card.append(element("p", demo ? "No original paper — fictional sample." : "Paper URL: Not reported", "small"));
  }
  return card;
}

function showResults(data) {
  currentResults = data;
  currentTopicId = data.topic_id || null;
  questionInput.value = data.question;
  renderTopics();
  results.hidden = false;
  document.querySelector("#demo-notice").hidden = !data.demo;
  document.querySelector("#result-question").textContent = data.question;
  document.querySelector("#search-terms").textContent = `Search terms: ${data.search_terms}`;
  const summary = document.querySelector("#summary");
  summary.replaceChildren(element("span", `Papers analyzed: ${data.papers.length}`));
  for (const [label, count] of Object.entries(data.counts)) {
    summary.append(element("span", `${label[0].toUpperCase() + label.slice(1)}: ${count}`));
  }
  const groups = { supporting: [], other: [], unclear: [] };
  for (const paper of data.papers) {
    const group = ["conflicting", "nuanced"].includes(paper.classification) ? "other" : paper.classification;
    groups[group].push(paper);
  }
  for (const [group, papers] of Object.entries(groups)) {
    const list = document.querySelector(`#${group}-papers`);
    list.replaceChildren(...papers.map(paper => paperCard(paper, data.demo)));
    document.querySelector(`#${group}-count`).textContent = `(${papers.length})`;
    if (!papers.length) list.append(element("p", "No papers placed here. This does not mean this kind of evidence does not exist.", "empty"));
  }
  document.querySelector("#export-button").disabled = !data.papers.length;
  statusText.textContent = data.papers.length
    ? `${data.restored ? "Saved topic restored — no new search" : data.demo ? "Offline sample loaded" : "Search complete"}. ${data.papers.length} papers shown.${data.topic_id ? " Saved locally." : " Results not saved."}`
    : "No papers found. Try fewer topic words, a different term, or a health-related question.";
}

async function search(demo) {
  if (busy) return;
  setBusy(true);
  results.hidden = true;
  currentResults = null;
  currentTopicId = null;
  renderTopics();
  errorText.hidden = true;
  statusText.textContent = demo ? "Loading offline sample…" : "Searching PubMed and reading abstracts…";
  results.setAttribute("aria-busy", "true");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 55000);
  try {
    const response = await fetch("/api/search", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: demo ? example : questionInput.value.trim(), demo }),
      signal: controller.signal,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The search could not be completed.");
    showResults(data);
    await refreshTopics();
    if (data.warning) {
      topicsError.textContent = `Results were not saved. ${data.warning}`;
      topicsError.hidden = false;
    }
  } catch (error) {
    errorText.textContent = error.name === "AbortError"
      ? "The search took too long. Please try again or use the offline demo."
      : error.message === "Failed to fetch"
        ? "Cannot reach PaperSift. Make sure python app.py is still running."
        : error.message;
    errorText.hidden = false;
    statusText.textContent = "Search unsuccessful.";
  } finally {
    clearTimeout(timeout);
    setBusy(false);
    results.setAttribute("aria-busy", "false");
  }
}

document.querySelector("#search-form").addEventListener("submit", event => {
  event.preventDefault();
  search(false);
});
document.querySelector("#demo-button").addEventListener("click", () => search(true));
document.querySelector("#example-button").addEventListener("click", () => {
  questionInput.value = example;
  questionInput.focus();
});
document.querySelector("#new-topic-button").addEventListener("click", newResearch);
setBusy(true);
refreshTopics().finally(() => setBusy(false));

function csvCell(value) {
  let text = String(value ?? "");
  // Avoid spreadsheet formulas in titles or other externally supplied text.
  if (/^[\s]*[=+@-]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
}

document.querySelector("#export-button").addEventListener("click", () => {
  if (!currentResults) return;
  const columns = [["Title", "title"], ["Authors", "authors"], ["Year", "year"],
    ["Classification (heuristic)", "classification"], ["Sample Size", "sample_size"],
    ["P-Value", "p_value"], ["Confidence Interval", "confidence_interval"], ["Study Type", "study_type"],
    ["Venue", "venue"], ["DOI", "doi"], ["URL", "url"], ["Funding", "funding"],
    ["Disclosure", "disclosure"], ["Abstract", "abstract"]];
  const rows = [["Question", "Data source", "Limitations", ...columns.map(([label]) => label)]];
  for (const paper of currentResults.papers) {
    rows.push([currentResults.question, currentResults.demo ? "FICTIONAL SAMPLE — DO NOT CITE" : "PubMed",
      "Keyword heuristic, not AI. Abstract extraction may be incomplete or incorrect. Review the original paper.",
      ...columns.map(([, key]) => paper[key])]);
  }
  const csv = "\uFEFF" + rows.map(row => row.map(csvCell).join(",")).join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8;" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = currentResults.demo ? "papersift-FICTIONAL-demo.csv" : "papersift-results.csv";
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
