import re


def auto_link_issue_references(summary, data):
    items = data.get("items", []) or []
    number_to_urls = {}
    for item in items:
        content = item.get("content") or {}
        number = content.get("number")
        url = content.get("url")
        if isinstance(number, int) and isinstance(url, str) and url:
            number_to_urls.setdefault(number, set()).add(url)

    unique_links = {
        number: next(iter(urls))
        for number, urls in number_to_urls.items()
        if len(urls) == 1
    }
    if not unique_links:
        return summary

    pattern = re.compile(r"(?<!\[)#(\d+)\b")

    def replacer(match):
        number = int(match.group(1))
        url = unique_links.get(number)
        if not url:
            return match.group(0)
        return f"[#{number}]({url})"

    return pattern.sub(replacer, summary)


def normalize_subsection_headings(summary):
    normalized_lines = []
    pattern = re.compile(r"^\s*[*-]\s+\*\*(.+?)\*\*:\s*$")

    for line in summary.splitlines():
        match = pattern.match(line)
        if match:
            normalized_lines.append(f"### {match.group(1)}")
        else:
            normalized_lines.append(line)

    return "\n".join(normalized_lines)


def enforce_top_metrics_block(summary, data):
    metrics = data.get("metrics", {}) or {}
    total_items = metrics.get("total_items_fetched", 0)
    updated_items = metrics.get("items_updated_in_lookback_window", 0)
    comments_count = metrics.get("comments_created_in_lookback_window", 0)

    cleaned_lines = []
    metric_pattern = re.compile(
        r"^\s*[*-]?\s*(\*\*)?\s*"
        r"(Total Items Fetched|Items Updated in Lookback Window|Comments Created in Lookback Window)"
        r"\s*:\s*.*$"
    )
    for line in summary.splitlines():
        if metric_pattern.match(line.strip()):
            continue
        cleaned_lines.append(line)

    metrics_block = [
        f"*   **Total Items Fetched:** {total_items}",
        f"*   **Items Updated in Lookback Window:** {updated_items}",
        f"*   **Comments Created in Lookback Window:** {comments_count}",
        "",
    ]

    return "\n".join(metrics_block + cleaned_lines).strip() + "\n"
