from urllib.parse import urlparse

from github_client import github_graphql_request
from github_queries import PROJECT_ID_BY_ORG_QUERY, PROJECT_ID_BY_USER_QUERY


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
        body = github_graphql_request(
            github_token,
            PROJECT_ID_BY_ORG_QUERY,
            {"owner": owner, "number": project_number},
        )
        project = body.get("data", {}).get("organization", {}).get("projectV2")
    else:
        body = github_graphql_request(
            github_token,
            PROJECT_ID_BY_USER_QUERY,
            {"owner": owner, "number": project_number},
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
