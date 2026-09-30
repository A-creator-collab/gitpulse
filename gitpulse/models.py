from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    login: str
    name: str | None
    bio: str | None
    avatar_url: str
    followers: int
    following: int
    public_repos: int
    created_at: datetime


@dataclass
class Repo:
    name: str
    language: str | None
    stars: int
    forks: int
    updated_at: datetime
    description: str | None


@dataclass
class StreakInfo:
    current: int
    longest: int
    total: int