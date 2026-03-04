# Source Notes

- Main entry point: `gitHubAISummary.py`
- Run from repo root using: `python src/gitHubAISummary.py`
- Requires a root-level `config.py` matching `config.example.py`.

## Current Flow

1. Fetch project data from GitHub GraphQL API.
2. Build a reporting prompt from raw project JSON.
3. Generate summary through selected provider (`AI_PROVIDER`):
   - `gemini` via Google Gemini API
   - `openai` via OpenAI Chat Completions API
4. Print report to stdout.

## Planned Extensions (from TODOs in code)

- Validate generated report structure.
- Export report to Google Docs.
- Send report to Slack webhook.
