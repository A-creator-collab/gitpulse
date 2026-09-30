import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

API_BASE = "https://api.github.com"
HTML_BASE = "https://github.com"
CACHE_DIR = Path.home() / ".cache" / "gitpulse"
CACHE_TTL_SECONDS = 15 * 60


class GitHubError(Exception):
    pass


class UserNotFound(GitHubError):
    pass


class RateLimited(GitHubError):
    def __init__(self, reset_at: int | None = None):
        if reset_at is not None:
            minutes = max(0, (reset_at - int(time.time())) // 60)
            super().__init__(
                f"GitHub API rate limit exceeded. Resets in about {minutes} minute(s)."
            )
        else:
            super().__init__("GitHub API rate limit exceeded.")


class NetworkError(GitHubError):
    pass


def _cache_path(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def _read_cache(url: str) -> Any | None:
    path = _cache_path(url)
    if not path.exists():
        return None
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if time.time() - blob.get("_cached_at", 0) > CACHE_TTL_SECONDS:
        return None
    return blob.get("payload")


def _write_cache(url: str, payload: Any) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(url).write_text(
            json.dumps({"_cached_at": time.time(), "payload": payload}),
            encoding="utf-8",
        )
    except OSError:
        pass


class GitHubClient:
    def __init__(self, token: str | None = None, timeout: float = 15.0):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "gitpulse",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(
            headers=headers, timeout=timeout, follow_redirects=True
        )

    def close(self) -> None:
        self._client.close()

    def _request(self, url: str) -> httpx.Response:
        try:
            response = self._client.get(url)
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {url}") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error contacting {url}: {exc}") from exc

        if response.status_code == 404:
            raise UserNotFound(f"Not found: {url}")
        if response.status_code == 403:
            remaining = response.headers.get("x-ratelimit-remaining")
            if remaining == "0":
                reset = response.headers.get("x-ratelimit-reset")
                reset_at = int(reset) if reset and reset.isdigit() else None
                raise RateLimited(reset_at)
            raise GitHubError(f"Access forbidden: {url}")
        if response.status_code >= 400:
            raise GitHubError(f"HTTP {response.status_code} from {url}")
        return response

    def _get_json(self, url: str) -> Any:
        cached = _read_cache(url)
        if cached is not None:
            return cached
        response = self._request(url)
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise GitHubError(f"Invalid JSON received from {url}") from exc
        _write_cache(url, data)
        return data

    def _get_text(self, url: str) -> str:
        cached = _read_cache(url)
        if cached is not None:
            return cached
        response = self._request(url)
        text = response.text
        _write_cache(url, text)
        return text

    def get_user(self, username: str) -> dict:
        return self._get_json(f"{API_BASE}/users/{username}")

    def get_repos(self, username: str) -> list[dict]:
        repos: list[dict] = []
        page = 1
        while True:
            url = f"{API_BASE}/users/{username}/repos?per_page=100&page={page}&type=owner"
            batch = self._get_json(url)
            if not isinstance(batch, list):
                break
            repos.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return repos

    def get_contributions_html(self, username: str) -> str:
        return self._get_text(f"{HTML_BASE}/users/{username}/contributions")


_TD_RE = re.compile(r"<td\b([^>]*)>")
_TOOLTIP_RE = re.compile(r"<tool-tip\b([^>]*)>(.*?)</tool-tip>", re.DOTALL)
_DATE_ATTR_RE = re.compile(r'data-date="(\d{4}-\d{2}-\d{2})"')
_LABEL_ATTR_RE = re.compile(r'aria-labelledby="([^"]+)"')
_FOR_ATTR_RE = re.compile(r'for="([^"]+)"')
_COUNT_RE = re.compile(r"(\d+)\s+contribution")


def parse_contributions(html: str) -> list[tuple[str, int]]:
    dates_by_id: dict[str, str] = {}
    for match in _TD_RE.finditer(html):
        attrs = match.group(1)
        date_match = _DATE_ATTR_RE.search(attrs)
        label_match = _LABEL_ATTR_RE.search(attrs)
        if date_match and label_match:
            dates_by_id[label_match.group(1)] = date_match.group(1)

    counts_by_id: dict[str, int] = {}
    for match in _TOOLTIP_RE.finditer(html):
        attrs = match.group(1)
        for_match = _FOR_ATTR_RE.search(attrs)
        if not for_match:
            continue
        cid = for_match.group(1)
        body = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if "No contribution" in body:
            counts_by_id[cid] = 0
            continue
        count_match = _COUNT_RE.search(body)
        if count_match:
            counts_by_id[cid] = int(count_match.group(1))

    days = [
        (date, counts_by_id[cid])
        for cid, date in dates_by_id.items()
        if cid in counts_by_id
    ]
    days.sort(key=lambda item: item[0])
    return days


def compute_streaks(days: list[tuple[str, int]]) -> tuple[int, int]:
    longest = 0
    run = 0
    for _, count in days:
        if count > 0:
            run += 1
            if run > longest:
                longest = run
        else:
            run = 0

    current = 0
    if days:
        index = len(days) - 1
        # Today's cell may legitimately be zero without breaking the streak.
        if days[index][1] == 0:
            index -= 1
        while index >= 0 and days[index][1] > 0:
            current += 1
            index -= 1
    return current, longest