from github_client import github_graphql_request
from github_queries import PROJECT_ITEMS_QUERY


def fetch_github_project_data(github_token, project_id, item_limit, comment_limit):
    return github_graphql_request(
        github_token,
        PROJECT_ITEMS_QUERY,
        {"id": project_id, "itemLimit": item_limit, "commentLimit": comment_limit},
    )
