# PaperSift

Explore both sides of scientific research.

## What PaperSift Does

Enter a research question to search up to 12 PubMed papers. Read titles, authors, abstracts, journal names, and links to the originals. Simple keyword rules place papers into supporting, conflicting, nuanced, or unclear groups. All four groups remain visible.

PaperSift also finds sample-size phrases, p-values, confidence intervals, and study-type keywords. Missing information says **Not reported** or **Not identified**. Export the current results to CSV for a spreadsheet.

This is a tool for exploring literature, not deciding which hypothesis is true. It has no AI model, accounts, database, paid API key, or cloud backend.

## Download PaperSift

Standalone downloads need **no Python, Git, pip, or terminal**. Once releases are published, get the ZIP for your operating system from this repository's GitHub **Releases** page. No release has been published by these build scripts.

### Windows

1. Download `PaperSift-Windows.zip` from Releases.
2. Extract the whole ZIP to a folder you can keep.
3. Open `PaperSift.exe` inside the `PaperSift` folder. Keep its `_internal` folder alongside it.
4. Your default browser opens PaperSift, running locally on your computer.

### macOS (WIP)

1. Download `PaperSift-macOS.zip` from Releases.
2. Extract it if necessary and move `PaperSift.app` to a convenient folder.
3. Open `PaperSift.app`. Your default browser opens the local app.

These student builds are not signed/notarized. Windows SmartScreen or macOS Gatekeeper may warn or block them. Only use a build whose source you trust; follow your operating system's normal security guidance. There is no signing or notarization service built into this project. A Mac build supports the architecture it was built for (Apple Silicon or Intel); test and label that before release.

New scientific searches need internet access. Saved topics and the fictional demo work offline. Click **Quit PaperSift** on the page when finished: it stops the local server and closes the tab when your browser allows it. If the tab stays open, the page confirms shutdown and you can close it manually. Closing a browser tab alone does not stop the local server. Launching the package again while it is running reopens the same instance. The standalone app chooses a free `127.0.0.1` port automatically; the address can change each launch. If your browser does not open, see `address.txt` in the data folder below for the current address.

## Running From Source

Developers can continue using `python app.py`; this does not auto-open a browser or change existing development history. Follow the setup below.

### Requirements

- Python **3.10 or newer**. Get it from [python.org](https://www.python.org/downloads/). On Windows, select **Add Python to PATH** during installation.
- An internet connection for installing dependencies and live searches. The demo works offline after installation.
- A browser. Git is optional if you download the project as a ZIP.

### Get the project

Clone the repository using its actual URL (replace `YOUR_REPOSITORY_URL`):

```text
git clone YOUR_REPOSITORY_URL PaperSift
cd PaperSift
```

Alternatively, download and unzip the repository, then open a terminal in the extracted PaperSift folder. It should contain `app.py` and `requirements.txt`.

### Windows Setup

Open PowerShell in the PaperSift folder and run these commands one line at a time:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

If `python` is not recognized but the Python launcher is installed, use `py -3 -m venv .venv` for the first command. We call the virtual environment's Python directly so you do not need to change PowerShell's script execution policy or activate anything.

Open **http://localhost:5000** in your browser. Leave the terminal running. Press **Ctrl+C** there to stop the app.

Next time, you only need:

```powershell
.\.venv\Scripts\python.exe app.py
```

### macOS Setup

Open Terminal in the PaperSift folder and run:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Open **http://localhost:5000**. Leave Terminal running. Press **Ctrl+C** to stop.

Next time, run `.venv/bin/python app.py` from the same folder.

## Using PaperSift

1. Enter a question, such as **Does social media use increase depression in teenagers?** The example below the input fills it for you.
2. Click **Search PubMed**. A search may take several seconds.
3. Check the actual search terms displayed above the results. Topic words are kept while common question and direction words are removed, so the search does not deliberately favor the hypothesis. Try shorter keywords if results are poor.
4. Compare both columns and the **Unclear** section. Open **Full abstract & disclosures** to see all retrieved text, grant metadata, and disclosures.
5. Follow **Read original on PubMed** to check the paper yourself. Access to its full text may depend on the publisher.
6. Click **Export CSV** to download the current results. The export includes the question, source, heuristic label, extracted values, full abstract, and limitations. It opens in Excel and other spreadsheet programs.

PubMed mainly covers biomedical and health research. It is not a search engine for every scientific field. We request relevance-ranked results, not a complete or balanced review. Citation counts are omitted because this API does not provide them directly. An empty group does not mean no evidence exists for that group.

## Research Topics

Successful searches with papers are automatically saved locally, newest first. The folder and file are created as needed. The compact **Research Topics** sidebar sits to the left on desktop; its list scrolls independently. On narrow screens it stacks above the search with a capped height. Click a topic to restore its original question, papers, counts, and extracted information **without another PubMed request**. Repeating the same question (ignoring capitalization and extra whitespace) opens the saved topic. To collect fresh results for that question, delete its topic and search again.

**New Research** clears the screen but keeps your topics. The small **×** button removes only its topic; deleting the selected topic returns to a blank search. Demo topics are marked `[Demo]` and kept separate from live research. Failed searches and searches with no papers are not saved.

Topics survive app restarts. No account or cloud database is required. History is a plain local JSON file and is ignored by Git; if your project folder is inside OneDrive or another synced folder, that service may sync it. The file uses safe replacement when saving. If it is malformed or cannot be written, PaperSift shows a message and keeps the original file. Move a damaged file aside or restore a valid backup to resume saving. Use one running PaperSift process per project folder; this simple file store is intended for personal use.

## Where Is My Data Stored?

Packaged downloads save `history.json` in your own application-data folder:

- **Windows:** `%LOCALAPPDATA%\PaperSift\` (paste this into File Explorer's address bar).
- **macOS:** `~/Library/Application Support/PaperSift/` (use Finder → Go → Go to Folder).

Source runs keep using `data/history.json` inside the project. These are separate histories; existing development data is not moved or bundled. To transfer history, quit both versions, back up any destination history, and copy the source `history.json` to the packaged data folder. Replacing that file replaces its topics; there is no automatic merge.

No account or cloud database is required. Data survives app/computer restarts and replacing the app with a newer build. It is never written into the executable, `_internal`, `.app`, or a PyInstaller temporary folder. The packaged data folder also contains a small instance lock and, while running, `address.txt`; a startup failure may create `startup-error.txt`. History is plain text, so anyone with access to that folder can read it.

## Building PaperSift

We use [PyInstaller](https://pyinstaller.org/en/stable/usage.html) to bundle Python and the dependencies. Build **Windows on Windows** and **macOS on a Mac**, from the same source. Only the builder needs Python. The `.spec` file explicitly includes templates, static files, and `demo.json`; it does not include history, tests, virtual environments, or secrets. No API keys are needed.

In the project folder, Windows Command Prompt:

```cmd
python -m venv .venv
build_windows.bat
```

If you already have `.venv`, just run `build_windows.bat`. In PowerShell use `.\build_windows.bat`. If Python is available through the Windows launcher instead, use `py -3 -m venv .venv` for the first command.

On macOS, Terminal:

```bash
python3 -m venv .venv
sh build_macos.sh
```

Both scripts install `requirements-build.txt`, run PyInstaller, and create the matching ZIP in `dist/`. Windows output is `dist/PaperSift-Windows.zip`; macOS output is `dist/PaperSift-macOS.zip`. The scripts replace earlier build output, so quit a running packaged copy before rebuilding. Do not commit `build/`, `dist/`, binaries, or user history; `.gitignore` excludes them.

`paths.py` keeps read-only resources separate from writable data. It uses the module's `__file__`, which [PyInstaller sets inside the bundle](https://pyinstaller.org/en/stable/runtime-information.html), to find resources. `launcher.py` reuses the Flask app through Werkzeug's local server, waits for a successful page response, then opens the browser. It uses a free port and an OS file lock to avoid duplicate packaged instances. A per-run random token protects the Quit action; it is generated locally, not a bundled private API key.

### Testing and manual releases

1. Finish a version and run the source tests below.
2. Build on Windows and separately on macOS.
3. Extract each ZIP and test opening, a live search, demo mode, topic switching/deletion, Quit, and reopening with history intact. Test on a clean computer without Python before broad distribution.
4. Create a GitHub Release such as `v1.0.0` only after both builds have been tested.
5. Attach `PaperSift-Windows.zip` and `PaperSift-macOS.zip` and note supported OS versions/architectures.

No release, commit, push, or GitHub Actions workflow is created automatically. macOS packaging must be built and tested on an actual Mac; Windows testing does not validate the Mac bundle. These are local-use packages, not public web servers or installers. Browser tabs do not control process lifetime—use Quit PaperSift.

## Demo Mode

Click **Try offline demo**. It loads six **obviously fictional sample papers** from `demo.json` for the fixed social-media/depression question. It never calls PubMed. Your input is not used for demo classification; the demo question is shown above the results.

Every sample title, the page banner, and the exported CSV identify these as fictional. All sample authors and numerical findings are invented to demonstrate the software. **Do not cite them or treat them as scientific evidence.** Real live-search data is never replaced with samples automatically.

## How the rules work (and where they fail)

- `classify_paper(question, abstract)` in `analysis.py` is an ordinary Python function, **not AI**. It only understands simple increase/decrease/reduce questions. It looks for the same exposure and outcome words in explicitly labeled results or conclusion sections, then checks directional wording. A null association is provisionally conflicting; mixed or uncertain wording is nuanced. Other cases are unclear, including causal claims and unrecognized question phrasing.
- Many real abstracts will be **unclear**. That is expected. The rules cannot reliably interpret negation, synonyms, multiple outcomes, population differences, or complex sentences. They cannot verify causation or evaluate the quality of evidence.
- Regular expressions extract matching text from abstracts, including multiple matches. They may pick up subgroup sizes, references to other studies, or unrelated statistics. They do not tell you which outcome each statistic belongs to. A bare `95% CI` may be found without its bounds. Other formatting may be missed.
- Study types are taken from recognized PubMed publication types first, then explicit abstract keywords. An abstract may mention a different study, so verify the label.
- Funding is shown only when PubMed returns grant metadata; disclosures use PubMed's conflict-of-interest field. **Not reported means unavailable in the retrieved data, not absent from the full paper.**
- Abstract excerpts are copied text, not generated summaries. No conclusions or citations are invented for live results.
- A future LLM integration can replace `classify_paper` while keeping the same four return labels. It would still need careful validation and uncertainty handling. There is no LLM integration or key requirement in this version.

## Files and presentation walkthrough

```text
app.py                 Flask page and search endpoint
research.py            PubMed search and XML metadata parsing
analysis.py            Statistics, study types, and classification rules
history.py             Read, save, and delete local topic snapshots
paths.py               Read-only resources and writable data locations
launcher.py            Standalone startup, browser opening, and shutdown
PaperSift.spec         Shared PyInstaller build configuration
build_windows.bat      Windows build and ZIP script
build_macos.sh         macOS build and ZIP script
requirements-build.txt Build-only dependencies
data/history.json      Your saved topics (created automatically; ignored by Git)
demo.json              Six fictional offline examples
templates/index.html   The page structure
static/style.css       Styling and small-screen layout
static/script.js       Search, paper cards, and CSV download
tests/test_papersift.py Focused automated checks
tests/test_topics.py    Topic persistence and error-handling checks
tests/test_packaging.py Paths, bundled resources, and launcher checks
requirements.txt       Flask and requests
```

For a presentation: the browser sends a new question to Flask → Flask asks PubMed for IDs and abstracts → Python extracts text and assigns provisional labels → Flask saves a topic snapshot → JavaScript displays the cards. Opening an existing topic reads its saved snapshot. Export runs in the browser.

## Troubleshooting

- **No papers found:** try fewer topic words or a health-related question. Long questions are not interpreted by a language model.
- **PubMed unavailable or rate-limited:** wait a minute and retry, check Wi-Fi, or click the offline demo. The app spaces API calls and shows errors instead of silently substituting data.
- **Cannot connect:** for a download, open PaperSift again and use the new browser tab (the port may change); check `address.txt` in its data folder if needed. For source runs, keep the server terminal open and also try `http://127.0.0.1:5000`.
- **Port 5000 already in use:** choose 5001. In PowerShell run `$env:PORT="5001"`, then the normal start command. On macOS run `PORT=5001 .venv/bin/python app.py`. Open `http://localhost:5001`. macOS AirPlay Receiver sometimes uses port 5000.
- **Missing Flask/requests:** install requirements with the same `.venv` Python used to start the app.

## Checking changes

Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

macOS:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The tests run offline and check extraction, conservative classification, PubMed parsing, errors, invalid input, and the demo. Also try a live search, a demo, and CSV export in your browser after making changes. macOS instructions use standard virtual-environment commands; they need testing on a Mac if you change setup behavior.

Quit button browser-logic regression checks (requires Node.js for development only):
```
node --test tests/quit.test.cjs
```

## Data source and privacy

Live results come from [NCBI PubMed E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25499/), using ESearch and EFetch. NCBI's [usage guidance](https://www.nlm.nih.gov/dataguide/eutilities/utilities.html) allows at most three requests per second without an API key; this single-process app spaces calls by at least 0.4 seconds. Other apps on the same network can still affect rate limits.

The app runs on your computer's loopback address. New live search terms are sent to NCBI. There are no analytics or accounts. Research topics and their results are stored in the local history file described above. Downloaded CSV files remain wherever your browser saves them. Abstracts may have publisher copyright restrictions: links and excerpts are for reviewing papers, not a license to redistribute a collection of abstracts.

The included `.gitignore` excludes virtual environments, Python caches, environment files, and logs. No API keys are needed. Do not commit your `.venv` folder or secrets.

PaperSift automatically extracts information from research abstracts. Results may be incomplete or incorrectly classified. Always review the original paper before drawing scientific conclusions.
