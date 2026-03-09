import time

import requests


def post_json_with_retries(url, *, json_body, headers=None, timeout_seconds=120, max_retries=0):
    attempts = max_retries + 1

    for attempt in range(1, attempts + 1):
        try:
            return requests.post(
                url,
                headers=headers,
                json=json_body,
                timeout=(15, timeout_seconds),
            )
        except requests.exceptions.ReadTimeout as exc:
            if attempt >= attempts:
                raise TimeoutError(
                    "AI provider read timeout after "
                    f"{attempts} attempt(s) with read timeout={timeout_seconds}s."
                ) from exc
            time.sleep(min(2 ** (attempt - 1), 4))
