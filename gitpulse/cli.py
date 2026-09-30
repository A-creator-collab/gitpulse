import os
from collections import Counter
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, NoReturn

import typer

from . import __version__
from .api import (
    GitHubClient,
    GitHubError,
    compute_streaks,
    parse_contributions,
)
from .display import (
    console,
    render_compare,
    render_langs,
    render_repos,
    render_streaks,
    render_user,
)
from .models import Repo, StreakInfo, User

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"gitpulse [green]{__version__}[/green]")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass


@contextmanager
def _client() -> Iterator[GitHubClient]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        console.print(
            "[yellow]Warning: GITHUB_TOKEN is not set. Unauthenticated requests "
            "are rate limited to 60 per hour.[/yellow]"
        )
    client = GitHubClient(token=token)
    try:
        yield client
    finally:
        client.close()


def _fail(error: Exception) -> NoReturn:
    console.print(f"[red]Error: {error}[/red]")
    raise typer.Exit(code=1)


def _user_from_api(data: dict) -> User:
    return User(
        login=data["login"],
        name=data.get("name"),
        bio=data.get("bio"),
        avatar_url=data["avatar_url"],
        followers=int(data.get("followers") or 0),
        following=int(data.get("following") or 0),
        public_repos=int(data.get("public_repos") or 0),
        created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
    )


def _repo_from_api(data: dict) -> Repo:
    return Repo(
        name=data["name"],
        language=data.get("language"),
        stars=int(data.get("stargazers_count") or 0),
        forks=int(data.get("forks_count") or 0),
        updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
        description=data.get("description"),
    )


def _count_languages(repos: list[Repo]) -> list[tuple[str, int]]:
    counts = Counter(repo.language for repo in repos if repo.language)
    return counts.most_common()


@app.command()
def user(username: str) -> None:
    """Show a profile card for a GitHub user."""
    with _client() as client:
        try:
            data = client.get_user(username)
        except GitHubError as exc:
            _fail(exc)
    render_user(_user_from_api(data))


@app.command()
def streak(username: str) -> None:
    """Show current and longest contribution streaks."""
    with _client() as client:
        try:
            client.get_user(username)
            html = client.get_contributions_html(username)
        except GitHubError as exc:
            _fail(exc)
    days = parse_contributions(html)
    if not days:
        console.print(
            "[yellow]No contribution data could be parsed for this user.[/yellow]"
        )
        raise typer.Exit(code=1)
    current, longest = compute_streaks(days)
    total = sum(count for _, count in days)
    render_streaks(StreakInfo(current=current, longest=longest, total=total), username)


@app.command()
def repos(
    username: str,
    lang: str | None = typer.Option(
        None, "--lang", help="Filter by programming language (case-insensitive)."
    ),
    sort: str = typer.Option(
        "stars", "--sort", help="Sort order: stars, updated, or name."
    ),
) -> None:
    """List repositories with optional language filtering and sorting."""
    if sort not in {"stars", "updated", "name"}:
        console.print("[red]Error: --sort must be one of stars, updated, name.[/red]")
        raise typer.Exit(code=1)

    with _client() as client:
        try:
            data = client.get_repos(username)
        except GitHubError as exc:
            _fail(exc)

    parsed = [_repo_from_api(item) for item in data]

    if lang:
        target = lang.lower()
        parsed = [r for r in parsed if (r.language or "").lower() == target]

    if sort == "stars":
        parsed.sort(key=lambda r: r.stars, reverse=True)
    elif sort == "updated":
        parsed.sort(key=lambda r: r.updated_at, reverse=True)
    else:
        parsed.sort(key=lambda r: r.name.lower())

    render_repos(parsed)


@app.command()
def langs(username: str) -> None:
    """Show a bar chart of top languages by repo count."""
    with _client() as client:
        try:
            data = client.get_repos(username)
        except GitHubError as exc:
            _fail(exc)
    repos = [_repo_from_api(item) for item in data]
    render_langs(_count_languages(repos))


@app.command()
def compare(user1: str, user2: str) -> None:
    """Compare two GitHub users side by side."""
    with _client() as client:
        try:
            data1 = client.get_user(user1)
            data2 = client.get_user(user2)
            repos1 = client.get_repos(user1)
            repos2 = client.get_repos(user2)
        except GitHubError as exc:
            _fail(exc)

    parsed1 = [_repo_from_api(item) for item in repos1]
    parsed2 = [_repo_from_api(item) for item in repos2]
    langs1 = _count_languages(parsed1)
    langs2 = _count_languages(parsed2)

    render_compare(
        _user_from_api(data1),
        _user_from_api(data2),
        sum(repo.stars for repo in parsed1),
        sum(repo.stars for repo in parsed2),
        langs1[0][0] if langs1 else "—",
        langs2[0][0] if langs2 else "—",
    )


if __name__ == "__main__":
    app()