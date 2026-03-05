# GitHub Project Status Analyzer

A Flask web app that fetches GitHub Projects V2 data and generates AI-powered status reports using Gemini or OpenAI.

## Running the project

```bash
# Start the web UI (runs on http://127.0.0.1:5000)
python web_ui.py

# Run CLI directly
python src/gitHubAISummary.py
```

## Configuration

Copy `config.example.py` to `config.py` and fill in:
- `GITHUB_TOKEN` — GitHub PAT with project read access
- `PROJECT_URL` — e.g. `https://github.com/orgs/<org>/projects/<n>`
- `AI_PROVIDER` — `"gemini"` or `"openai"`
- `GEMINI_API_KEY` / `OPENAI_API_KEY` — respective API keys

**Do not commit `config.py`** — it contains secrets.

## Running tests

```bash
python run_tests.py
```

Runs Python unittests (`tests/python/test_*.py`) and JavaScript tests (`tests/js/*.test.js`).

## Project structure

```
web_ui.py              # Flask server entry point (port 5000)
config.py              # Local config with secrets (gitignored)
config.example.py      # Template for config.py
requirements.txt       # Python deps: flask, requests
src/
  gitHubAISummary.py   # CLI entry point
  report_runner.py     # End-to-end pipeline orchestration
  settings.py          # Config loading/normalization
  github_client.py     # GitHub GraphQL transport
  github_queries.py    # GraphQL query strings
  project_target.py    # URL parsing, project ID resolution
  github_project_data.py  # Fetch project items
  payload_builder.py   # Transform raw data into prompt payload
  prompt_template.py   # Report prompt template
  ai_clients.py        # Provider dispatch
  ai_provider_gemini.py
  ai_provider_openai.py
  ai_http.py           # Shared HTTP/retry utility
  report_formatting.py # Post-process markdown output
  report_writer.py     # Save timestamped report files
  model_options.py     # Available AI model list
webui/                 # Static frontend assets
reports/               # Generated report output (gitignored)
tests/
  python/              # Python unittests
  js/                  # JavaScript tests
```

## Pipeline flow

1. Resolve project ID from URL (or explicit `PROJECT_ID`)
2. Fetch project items + comments via GitHub GraphQL
3. Build analysis prompt from raw data
4. Generate summary via Gemini or OpenAI
5. Format and return/save markdown report

## API endpoints

- `GET /api/config` — returns masked config values
- `POST /api/run` — runs report, returns JSON with markdown
- `POST /api/run-stream` — streams progress via NDJSON
