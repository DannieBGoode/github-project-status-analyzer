from urllib.parse import urlparse

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


def parse_project_v2_url(project_url):
    parsed = urlparse(project_url)
    parts = [p for p in parsed.path.split("/") if p]

    if len(parts) == 4 and parts[2] == "projects" and parts[3].isdigit():
        scope = parts[0]
        owner = parts[1]
        project_number = int(parts[3])

        if scope not in {"orgs", "users"}:
            raise ValueError(
                "Unsupported project URL scope. Use /orgs/<org>/projects/<n> "
                "or /users/<user>/projects/<n>."
            )

        return scope, owner, project_number

    raise ValueError(
        "PROJECT_URL format not recognized. Expected: "
        "https://github.com/orgs/<org>/projects/<n> or "
        "https://github.com/users/<user>/projects/<n>."
    )


def resolve_project_id_from_url(github_token, project_url):
    scope, owner, project_number = parse_project_v2_url(project_url)

    if scope == "orgs":
        query = """
        query($owner: String!, $number: Int!) {
          organization(login: $owner) {
            projectV2(number: $number) {
              id
            }
          }
        }
        """
        body = github_graphql_request(
            github_token, query, {"owner": owner, "number": project_number}
        )
        project = body.get("data", {}).get("organization", {}).get("projectV2")
    else:
        query = """
        query($owner: String!, $number: Int!) {
          user(login: $owner) {
            projectV2(number: $number) {
              id
            }
          }
        }
        """
        body = github_graphql_request(
            github_token, query, {"owner": owner, "number": project_number}
        )
        project = body.get("data", {}).get("user", {}).get("projectV2")

    if not project or not project.get("id"):
        raise ValueError(
            "Could not resolve PROJECT_ID from PROJECT_URL. "
            "Check URL correctness and token permissions."
        )

    return project["id"]


def get_project_id(github_token, project_id, project_url):
    if project_id:
        return project_id
    if not project_url:
        raise ValueError("Set PROJECT_ID or PROJECT_URL in config.py.")
    return resolve_project_id_from_url(github_token, project_url)


def fetch_github_project_data(github_token, project_id, item_limit, comment_limit):
    query = """
    query($id: ID!, $itemLimit: Int!, $commentLimit: Int!) {
      node(id: $id) {
        ... on ProjectV2 {
          title
          url
          items(first: $itemLimit) {
            nodes {
              updatedAt
              content {
                ... on PullRequest {
                  number
                  title
                  body
                  state
                  url
                  createdAt
                  updatedAt
                  comments(last: $commentLimit) {
                    totalCount
                    nodes {
                      bodyText
                      createdAt
                      updatedAt
                      url
                      author {
                        login
                      }
                    }
                  }
                  reviews { totalCount }
                }
                ... on Issue {
                  number
                  title
                  body
                  state
                  url
                  createdAt
                  updatedAt
                  comments(last: $commentLimit) {
                    totalCount
                    nodes {
                      bodyText
                      createdAt
                      updatedAt
                      url
                      author {
                        login
                      }
                    }
                  }
                }
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

    return github_graphql_request(
        github_token,
        query,
        {"id": project_id, "itemLimit": item_limit, "commentLimit": comment_limit},
    )
