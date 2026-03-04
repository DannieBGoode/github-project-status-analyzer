"""Example local configuration.

Copy this file to `config.py` and fill in real values.
Do not commit `config.py` with secrets.
"""

# Personal access token or GitHub App token with access to the target project.
GITHUB_TOKEN = "ghp_your_github_token_here"

# GitHub Project V2 node ID (looks like: PVT_kwDO...)
PROJECT_ID = "PVT_your_project_node_id_here"

# Select summary provider: "gemini" or "openai"
AI_PROVIDER = "gemini"

# Gemini settings
GEMINI_API_KEY = "AIzaSy_your_gemini_api_key_here"
GEMINI_MODEL = "gemini-2.5-flash"

# OpenAI settings
OPENAI_API_KEY = "sk-your-openai-api-key"
OPENAI_MODEL = "gpt-4.1-mini"
