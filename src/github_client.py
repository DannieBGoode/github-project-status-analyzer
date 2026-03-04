import requests


def github_graphql_request(github_token, query, variables, timeout=30):
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        url,
        json={"query": query, "variables": variables},
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()

    if "errors" in body:
        raise ValueError(f"GitHub GraphQL error: {body['errors']}")

    return body
