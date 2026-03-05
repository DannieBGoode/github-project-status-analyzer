# GitHub Project Status Analyzer

A lightweight Python utility that generates an executive project status report from a GitHub Project (V2) using either Google Gemini or OpenAI.

## What This Project Does

The script in `src/gitHubAISummary.py` automates a simple reporting workflow:

1. Resolves your target project:
   - uses `PROJECT_ID` directly if provided, or
   - auto-resolves from `PROJECT_URL`.
2. Calls the GitHub GraphQL API to read up to `MAX_ITEMS` items from a GitHub Project V2 board (default: 40, maximum: 100).
3. Extracts issue/PR content and the project `Status` field.
4. Sends the raw JSON payload to your selected AI provider (`gemini` or `openai`) with a reporting prompt.
5. Generates an executive summary with sections for:
   - Key achievements
   - Risks
   - Issues/blockers
   - Utilization/throughput
6. Saves the report as a timestamped Markdown file in `reports/`.

Current implementation is a prototype with TODOs for:
- validating AI output structure,
- writing the summary to Google Docs,
- sending the summary to Slack.

## Repository Structure

- `src/` — Python source modules: entry point, pipeline orchestration, GitHub GraphQL client, AI provider integrations, report formatting, and output writing.
- `src/gitHubAISummary.py` — CLI entry point.
- `src/README.md` — source-level notes.
- `web_ui.py` — Flask web server for the local web UI.
- `webui/` — Web UI static assets (HTML, CSS, JavaScript).
- `tests/` — Python and JavaScript unit tests.
- `run_tests.py` — unified test runner (runs both suites).
- `reports/` — generated report output directory (created on first run).
- `requirements.txt` — Python dependencies.
- `config.example.py` — template for required secrets and config values.

## Prerequisites

- Python 3.9+
- A GitHub token with permission to read your target Project V2 data
- A GitHub Project V2 URL or Project V2 node ID
- One AI provider credential:
  - Gemini API key, or
  - OpenAI API key

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `config.py` in the project root by copying from the example:

```bash
# Linux/macOS
cp config.example.py config.py
# Windows
copy config.example.py config.py
```

4. Edit `config.py` with real values:

Required for all runs:
- `GITHUB_TOKEN`
- `AI_PROVIDER` (`"gemini"` or `"openai"`)

Project target (choose one):
- Preferred: `PROJECT_URL` (script auto-resolves `PROJECT_ID`)
- Optional override: `PROJECT_ID`

If `AI_PROVIDER = "gemini"`:
- `GEMINI_API_KEY`
- optional `GEMINI_MODEL`

If `AI_PROVIDER = "openai"`:
- `OPENAI_API_KEY`
- optional `OPENAI_MODEL`

Optional tuning values (with defaults from `config.example.py`):
- `LOOKBACK_DAYS` — report window in days (default: `14`)
- `MAX_ITEMS` — items fetched from the project board (default: `40`, maximum: `100`)
- `MAX_COMMENTS_PER_ITEM` — comments included per item (default: `20`)
- `AI_TIMEOUT_SECONDS` — per-request read timeout for AI calls (default: `120`)
- `AI_MAX_RETRIES` — retry attempts on timeout (default: `1`)
- `REPORT_TIMEZONE` — IANA timezone for report timestamps, e.g. `"America/New_York"`
- `REPORT_TIMEZONE_LABEL` — label appended to timestamps, e.g. `"ET"`

## Where To Get Keys And IDs

- `OPENAI_API_KEY`
  - OpenAI API keys page: `https://platform.openai.com/api-keys`
  - Create a new secret key and copy it into `config.py`.

- `GEMINI_API_KEY`
  - Google AI Studio: `https://aistudio.google.com/apikey`
  - Create an API key and copy it into `config.py`.

- `GITHUB_TOKEN`
  - GitHub fine-grained token creation: `https://github.com/settings/personal-access-tokens/new`
  - Create a token with access to the organization/repo/project you need.
  - At minimum, grant permissions required to read Project V2 data via GraphQL.

- `PROJECT_URL` (recommended)
  - Copy directly from your browser, for example:
    - `https://github.com/orgs/input-output-hk/projects/26`
    - `https://github.com/users/<username>/projects/<number>`

- `PROJECT_ID` (optional override)
  - This is auto-resolved from `PROJECT_URL` by default.
  - Only set manually if you want to bypass URL resolution.

## Run

From the repository root:

```bash
python src/gitHubAISummary.py
```

After each run, the report is saved as:
- `reports/report-YYYYMMDD-HHMMSS.md`

## Automated Tests

The repository now includes:
- Python unit tests under `tests/python`
- JavaScript unit tests under `tests/js` (Node test runner)

Run both suites with:

```bash
python run_tests.py
```

Run only Python tests:

```bash
python -m unittest discover -s tests/python -p "test_*.py"
```

Run only JavaScript tests:

```bash
node --test tests/js/*.test.js
```

## Web UI (Local)

Run a minimal local web UI with prefilled values from `config.py` (API keys shown masked):

```bash
python web_ui.py
```

Then open:

```text
http://127.0.0.1:5000
```

Capabilities:
- switch AI provider and model from the UI,
- edit runtime variables before execution,
- stream live progress output while the report is being generated,
- browse and view previously generated reports in a Reports tab,
- download any report as a Markdown file directly from the browser.

## How Data Is Queried

The GitHub GraphQL query fetches:
- project items (count controlled by `MAX_ITEMS`, default: 40),
- project name and URL,
- issue/PR number, title, body, state, URL, created/updated timestamps,
- issue/PR comment/review counts,
- latest issue/PR comments per item (up to `MAX_COMMENTS_PER_ITEM`, default 20), including comment body text, author, timestamp, URL,
- the project single-select field named `Status`.

Lookback behavior:
- The report window is the last 14 days by default (`LOOKBACK_DAYS` in `config.py`).
- The script computes a recent-item count based on item/content `updatedAt`.
- The script filters fetched comments to those created inside the lookback window before sending to AI.
- The model receives both recent-window metrics and full fetched items for context.

Not currently queried:
- Full discussion thread text outside fetched issue/PR comments
- Issue/PR timeline events
- Full pull request review text

## Known Limitations

- Error handling is minimal beyond `raise_for_status()`.
- Secrets are loaded from a plain Python module (`config.py`).
- Prompt quality and output consistency are not validated yet.

## Security Notes

- Never commit `config.py` with real tokens.
- Rotate credentials if exposed.
- Consider migrating secrets to environment variables for production usage.

## Suggested Next Improvements

- Add schema-safe parsing and AI-response validation.
- Add CLI arguments (project URL/ID, item limit, output format).
- Add optional outputs: Slack webhook, Google Docs.
