from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table

from .models import Repo, StreakInfo, User

console = Console()


def _account_age_years(created_at: datetime) -> float:
    now = datetime.now(timezone.utc)
    return (now - created_at).days / 365.25


def _green(value: int | str) -> str:
    return f"[green]{value}[/green]"


def render_user(user: User) -> None:
    lines: list[str] = []
    if user.name:
        lines.append(f"[bold]{user.name}[/bold]")
    lines.append(f"[dim]@{user.login}[/dim]")
    if user.bio:
        lines.append("")
        lines.append(user.bio)
    lines.append("")
    lines.append(f"Avatar: {user.avatar_url}")
    lines.append(f"Followers: {_green(user.followers)}")
    lines.append(f"Following: {_green(user.following)}")
    lines.append(f"Public repos: {_green(user.public_repos)}")
    lines.append(f"Account age: {_green(f'{_account_age_years(user.created_at):.1f}')} years")
    console.print(
        Panel(
            "\n".join(lines),
            title="[cyan]👤 Profile[/cyan]",
            border_style="cyan",
            expand=False,
        )
    )


def render_streaks(info: StreakInfo, username: str) -> None:
    lines = [
        f"Current streak: {_green(info.current)} days",
        f"Longest streak: {_green(info.longest)} days",
        f"Contributions in window: {_green(info.total)}",
    ]
    console.print(
        Panel(
            "\n".join(lines),
            title=f"[cyan]🔥 Streak — {username}[/cyan]",
            border_style="cyan",
            expand=False,
        )
    )


def render_repos(repos: list[Repo]) -> None:
    if not repos:
        console.print("[yellow]No repositories matched.[/yellow]")
        return
    table = Table(title="[cyan]📦 Repositories[/cyan]", border_style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Language")
    table.add_column("Stars", justify="right", style="green")
    table.add_column("Forks", justify="right", style="green")
    table.add_column("Updated")
    for repo in repos:
        table.add_row(
            repo.name,
            repo.language or "—",
            str(repo.stars),
            str(repo.forks),
            repo.updated_at.strftime("%Y-%m-%d"),
        )
    console.print(table)


def render_langs(langs: list[tuple[str, int]]) -> None:
    if not langs:
        console.print("[yellow]No language data available.[/yellow]")
        return
    top = max(count for _, count in langs)
    table = Table(title="[cyan]🧪 Languages[/cyan]", border_style="cyan")
    table.add_column("Language", style="bold")
    table.add_column("Repos", justify="right", style="green")
    table.add_column("", no_wrap=True)
    for name, count in langs:
        bar = ProgressBar(
            total=top, completed=count, width=30, complete_style="cyan"
        )
        table.add_row(name, str(count), bar)
    console.print(table)


def render_compare(
    user1: User,
    user2: User,
    stars1: int,
    stars2: int,
    lang1: str,
    lang2: str,
) -> None:
    table = Table(title="[cyan]Comparison[/cyan]", border_style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column(f"@{user1.login}", justify="right")
    table.add_column(f"@{user2.login}", justify="right")
    table.add_row("Followers", _green(user1.followers), _green(user2.followers))
    table.add_row("Public repos", _green(user1.public_repos), _green(user2.public_repos))
    table.add_row("Total stars", _green(stars1), _green(stars2))
    table.add_row("Top language", lang1, lang2)
    console.print(table)