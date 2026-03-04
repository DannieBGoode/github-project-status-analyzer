#pip install requests needed
import requests
import json
from datetime import datetime
import config

# --- CONFIGURATION ---


def fetch_github_project_data():
    """Fetches items and metadata from GitHub Project V2."""
    url = "https://api.github.com/graphql"
    
    # This query retrieves the last 40 items, their titles, bodies, and 'Status' field
    query = """
    query($id: ID!) {
      node(id: $id) {
        ... on ProjectV2 {
          items(first: 40) {
            nodes {
              content {
                ... on PullRequest { title body state }
                ... on Issue { title body state }
              }
              fieldValueByName(name: "Status") {
                ... on ProjectV2ItemFieldSingleSelectValue { name }
              }
            }
          }
        }
      }
    }
    """
    

    headers = {"Authorization": f"Bearer {config.GITHUB_TOKEN}"}
    variables = {"id": config.PROJECT_ID}
    
    response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
    response.raise_for_status()
    print(response.status_code)
    print(response.json())
    return response.json()

def get_gemini_summary(data):
    """Feeds the GitHub JSON to Gemini for an Executive Summary."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={config.GEMINI_API_KEY}"
    
    prompt = f"""
    Context: You are a CTO's reporting agent. You need to report on achievements, risks, issues at a high level. 
    
    Task: Review the following GitHub Project data and write a concise executive report.
    Structure:
    1. Key Achievements in the last 2 weeks.
    2. Risks.
    3. Issues and Blockers.
    4. Utilization & Throughput (how efficiently we are delivering).
    
    Raw Data: {json.dumps(data)}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    print(response.status_code)
    print(response.json())
    result = response.json()
    #TODO check the result to make sure it follows the structure mentioned in the prompt, otherwise prompt again
    return result['candidates'][0]['content']['parts'][0]['text']

def run_report():
    print(f"[{datetime.now()}] Fetching GitHub data...")
    raw_data = fetch_github_project_data()
    
    print(f"[{datetime.now()}] Generating AI summary...")

    summary = get_gemini_summary(raw_data)
    #TODO write the summary into a GoogleDoc using writeToGoogleDoc library

    #TODO send this to a Slack Webhook,
    print("\n--- EXECUTIVE REPORT ---\n")
    print(summary)

if __name__ == "__main__":
    run_report()