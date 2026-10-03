"""Domain models for factual engineering updates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FileChange:
    status: str
    path: str
    previous_path: str | None = None


@dataclass(frozen=True)
class Commit:
    sha: str
    author: str
    subject: str


@dataclass(frozen=True)
class ChangeSet:
    branch: str
    before: str
    after: str
    commits: tuple[Commit, ...]
    files: tuple[FileChange, ...]
    additions: int = 0
    deletions: int = 0

    SHORT_SHA_LENGTH = 7

    @property
    def event_id(self) -> str:
        return f"{self.branch}@{self.after}"

    @property
    def short_after_sha(self) -> str:
        return self.after[: self.SHORT_SHA_LENGTH]


@dataclass(frozen=True)
class Digest:
    title: str
    developers: tuple[str, ...]
    categories: tuple[str, ...]
    change_summary: str
    achieved: str
    technical_changes: tuple[str, ...]
    impact: str
