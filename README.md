# GitHub Project Status Analyzer

A lightweight Python utility that generates an executive project status report from a GitHub Project (V2) using either Google Gemini or OpenAI.

## What This Project Does

The script in `src/gitHubAISummary.py` automates a simple reporting workflow:

1. Calls the GitHub GraphQL API to read up to 40 items from a GitHub Project V2 board.
2. Extracts issue/PR content and the project `Status` field.
3. Sends the raw JSON payload to your selected AI provider (`gemini` or `openai`) with a reporting prompt.
4. Prints an executive summary with sections for:
   - Key achievements
   - Risks
   - Issues/blockers
   - Utilization/throughput

Current implementation is a prototype with TODOs for:
- validating AI output structure,
- writing the summary to Google Docs,
- sending the summary to Slack.

## Repository Structure

- `src/gitHubAISummary.py`: main script and orchestration logic.
- `src/README.md`: source-level notes.
- `requirements.txt`: Python dependencies.
- `config.example.py`: template for required secrets/config values.

## Prerequisites

- Python 3.9+
- A GitHub token with permission to read your target Project V2 data
- A GitHub Project V2 node ID
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
copy config.example.py config.py
```

4. Edit `config.py` with real values:

Required for all runs:
- `GITHUB_TOKEN`
- `PROJECT_ID`
- `AI_PROVIDER` (`"gemini"` or `"openai"`)

If `AI_PROVIDER = "gemini"`:
- `GEMINI_API_KEY`
- optional `GEMINI_MODEL`

If `AI_PROVIDER = "openai"`:
- `OPENAI_API_KEY`
- optional `OPENAI_MODEL`

## Run

From the repository root:

```bash
python src/gitHubAISummary.py
```

## How Data Is Queried

The GitHub GraphQL query fetches:
- project items (`first: 40`),
- issue/PR title, body, and state,
- the project single-select field named `Status`.

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
- Add retries/backoff policies for API calls.
- Add CLI arguments (project ID, item limit, output format).
- Add unit tests with mocked GitHub/AI API responses.
- Add optional outputs: markdown file, Slack webhook, Google Docs.
