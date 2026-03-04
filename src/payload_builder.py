from datetime import datetime, timedelta, timezone


def parse_github_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def truncate_text(value, limit=600):
    if value is None:
        return ""
    text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def build_analysis_payload(
    raw_data, lookback_days, effective_item_limit, max_comments_per_item
):
    project = raw_data.get("data", {}).get("node", {}) or {}
    items = project.get("items", {}).get("nodes", []) or []

    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=lookback_days)

    recent_count = 0
    recent_comments_total = 0
    filtered_items = []

    for item in items:
        item_updated_at = parse_github_datetime(item.get("updatedAt"))
        content = item.get("content") or {}
        content_updated_at = parse_github_datetime(content.get("updatedAt"))

        is_recent = False
        if item_updated_at and item_updated_at >= cutoff:
            is_recent = True
        if content_updated_at and content_updated_at >= cutoff:
            is_recent = True
        if is_recent:
            recent_count += 1

        comments = content.get("comments", {}).get("nodes", []) or []
        recent_comments = []
        for comment in comments:
            created_at = parse_github_datetime(comment.get("createdAt"))
            if created_at and created_at >= cutoff:
                recent_comments.append(
                    {
                        "author": (comment.get("author") or {}).get("login"),
                        "createdAt": comment.get("createdAt"),
                        "updatedAt": comment.get("updatedAt"),
                        "url": comment.get("url"),
                        "bodyText": truncate_text(comment.get("bodyText")),
                    }
                )

        recent_comments_total += len(recent_comments)

        filtered_content = dict(content)
        filtered_content["recentComments"] = recent_comments
        filtered_content.pop("comments", None)
        filtered_items.append({**item, "content": filtered_content})

    return {
        "project": {
            "title": project.get("title"),
            "url": project.get("url"),
        },
        "query_scope": {
            "description": "Fetched Project V2 items via GitHub GraphQL.",
            "item_limit": effective_item_limit,
            "comment_limit_per_item": max_comments_per_item,
            "lookback_days": lookback_days,
            "lookback_start_utc": cutoff.isoformat(),
            "queried_fields": [
                "project.title",
                "project.url",
                "project.items.nodes.updatedAt",
                "content for Issue/PullRequest: number, title, body, state, url, createdAt, updatedAt",
                "Issue comments.totalCount and comments(last: MAX_COMMENTS_PER_ITEM){bodyText, createdAt, updatedAt, url, author.login}",
                "PullRequest comments.totalCount and comments(last: MAX_COMMENTS_PER_ITEM){bodyText, createdAt, updatedAt, url, author.login}",
                "PullRequest reviews.totalCount",
                "project fieldValueByName('Status').name",
            ],
            "not_included": [
                "Issue/PR timeline events",
                "discussion thread text",
                "full review text",
            ],
        },
        "metrics": {
            "total_items_fetched": len(items),
            "items_updated_in_lookback_window": recent_count,
            "comments_created_in_lookback_window": recent_comments_total,
        },
        "items": filtered_items,
    }
