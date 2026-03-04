# Source Notes

- Main entry point: `gitHubAISummary.py`
- Run from repo root using: `python src/gitHubAISummary.py`
- Requires a root-level `config.py` matching `config.example.py`.

## Current Flow

1. Resolve project target:
   - Use `PROJECT_ID` if provided, otherwise
   - Resolve from `PROJECT_URL` (`/orgs/.../projects/<n>` or `/users/.../projects/<n>`) via GitHub GraphQL.
2. Fetch project data from GitHub GraphQL API.
   - Includes issue/PR comment nodes (capped per item), then filters comments to the lookback window.
3. Build a reporting prompt from raw project JSON.
4. Generate summary through selected provider (`AI_PROVIDER`):
   - `gemini` via Google Gemini API
   - `openai` via OpenAI Chat Completions API
5. Save report to `reports/report-YYYYMMDD-HHMMSS.md`.
6. Print report to stdout.

## Planned Extensions (from TODOs in code)

- Validate generated report structure.
- Export report to Google Docs.
- Send report to Slack webhook.
