"""Example local configuration.

Copy this file to `config.py` and fill in real values.
Do not commit `config.py` with secrets.
"""

# Personal access token or GitHub App token with access to the target project.
# Create one at: https://github.com/settings/personal-access-tokens/new
GITHUB_TOKEN = "ghp_your_github_token_here"

# Preferred: set PROJECT_URL and let the script resolve PROJECT_ID automatically.
# Supported formats:
# - https://github.com/orgs/<org>/projects/<number>
# - https://github.com/users/<user>/projects/<number>
PROJECT_URL = ""

# Optional: explicit Project V2 node ID (looks like: PVT_kwDO...).
# If set, this takes precedence over PROJECT_URL.
# Get it from GraphQL API docs: https://docs.github.com/en/graphql
PROJECT_ID = ""

# Select summary provider: "gemini" or "openai"
AI_PROVIDER = "gemini"

# Reporting query controls
# Only items updated within this many days are considered "recent" in the report.
LOOKBACK_DAYS = 14
# Number of project items to fetch (GitHub GraphQL hard cap: 100).
MAX_ITEMS = 40
# Comments fetched per item; higher values increase prompt size and AI cost.
MAX_COMMENTS_PER_ITEM = 20
# Seconds to wait for an AI provider response before timing out.
AI_TIMEOUT_SECONDS = 120
# Number of additional retry attempts on AI provider read timeout (0 = no retries).
AI_MAX_RETRIES = 1

# Gemini settings
# Create API key at: https://aistudio.google.com/apikey
GEMINI_API_KEY = "AIzaSy_your_gemini_api_key_here"
GEMINI_MODEL = "gemini-2.5-flash-lite-preview-09-2025"

# OpenAI settings
# Create API key at: https://platform.openai.com/api-keys
OPENAI_API_KEY = "sk-your-openai-api-key"
OPENAI_MODEL = "gpt-5-nano"

# Optional: timezone for the "Generated" timestamp in the report.
# Use IANA zone names (e.g. "America/New_York", "Europe/London", "Asia/Tokyo").
# Leave empty to use the server's local timezone.
REPORT_TIMEZONE = ""
# Optional: display label for the timezone shown in the report (e.g. "ET", "BST").
# Leave empty to use the abbreviation derived from REPORT_TIMEZONE.
REPORT_TIMEZONE_LABEL = ""
