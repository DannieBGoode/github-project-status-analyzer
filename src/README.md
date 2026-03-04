# Source Notes

- Main entry point: `gitHubAISummary.py`
- Run from repo root using: `python src/gitHubAISummary.py`
- Requires a root-level `config.py` matching `config.example.py`.

## Modules

- `settings.py`: loads and normalizes runtime settings from `config.py`.
- `github_client.py`: low-level GitHub GraphQL transport.
- `github_queries.py`: GitHub GraphQL query strings.
- `project_target.py`: project URL parsing and `PROJECT_ID` resolution.
- `github_project_data.py`: project item retrieval from GitHub.
- `payload_builder.py`: transforms raw GitHub data into analysis payload + metrics.
- `prompt_template.py`: report prompt template and prompt rendering.
- `ai_http.py`: shared HTTP/retry utility for AI providers.
- `ai_provider_gemini.py`: Gemini API integration.
- `ai_provider_openai.py`: OpenAI API integration.
- `ai_clients.py`: provider dispatch orchestration.
- `report_formatting.py`: post-processing (issue links, headings, top metrics block).
- `report_writer.py`: timestamped markdown report file output.
- `report_runner.py`: end-to-end report pipeline orchestration.

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
