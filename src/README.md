# Source Notes

- Main entry point: `gitHubAISummary.py`
- Run from repo root using: `python src/gitHubAISummary.py`
- Requires a root-level `config.py` matching `config.example.py`.

## Current Flow

1. Fetch project data from GitHub GraphQL API.
2. Send data to Gemini for summarization.
3. Print report to stdout.

## Planned Extensions (from TODOs in code)

- Validate generated report structure.
- Export report to Google Docs.
- Send report to Slack webhook.
