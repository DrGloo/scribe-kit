"""Bounded Git metadata collection."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .models import ChangeSet, Commit, FileChange


class GitCommandError(RuntimeError):
    pass


class GitRepository:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def collect(self, revision_range: str, branch: str) -> ChangeSet:
        before, after_ref = self._parse_range(revision_range)
        after = self._git("rev-parse", after_ref)
        commit_lines = self._git(
            "log",
            "--reverse",
            "--no-merges",
            "--format=%H%x09%an%x09%s",
            revision_range,
        )
        commits = tuple(self._parse_commit(line) for line in commit_lines.splitlines())
        files = tuple(self._collect_files(revision_range))
        additions, deletions = self._collect_diff_stats(revision_range)
        return ChangeSet(
            branch=branch,
            before=self._git("rev-parse", before),
            after=after,
            commits=commits,
            files=files,
            additions=additions,
            deletions=deletions,
        )

    def commit_url(self, sha: str) -> str | None:
        remote = self._git_optional("remote", "get-url", "origin")
        if not remote:
            return None
        remote = remote.removesuffix(".git")
        if remote.startswith("git@") and ":" in remote:
            host_path = remote[4:].replace(":", "/", 1)
            remote = f"https://{host_path}"
        if remote.startswith(("https://github.com/", "https://origin.cursor.com/")):
            return f"{remote}/commit/{sha}"
        return None

    def _collect_files(self, revision_range: str) -> list[FileChange]:
        output = self._git("diff", "--name-status", "--find-renames", revision_range)
        changes: list[FileChange] = []
        for line in output.splitlines():
            parts = line.split("\t")
            status = parts[0][0]
            if status == "R" and len(parts) >= 3:
                changes.append(FileChange(status, parts[2], parts[1]))
            elif len(parts) >= 2:
                changes.append(FileChange(status, parts[1]))
        return changes

    def _collect_diff_stats(self, revision_range: str) -> tuple[int, int]:
        output = self._git("diff", "--numstat", revision_range)
        additions = deletions = 0
        for line in output.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                additions += int(parts[0]) if parts[0].isdigit() else 0
                deletions += int(parts[1]) if parts[1].isdigit() else 0
        return additions, deletions

    @staticmethod
    def _parse_range(revision_range: str) -> tuple[str, str]:
        if ".." not in revision_range:
            raise GitCommandError("range must use BEFORE..AFTER syntax")
        before, after = revision_range.split("..", 1)
        if not before or not after:
            raise GitCommandError("range must include both revisions")
        return before, after

    @staticmethod
    def _parse_commit(line: str) -> Commit:
        sha, author, subject = line.split("\t", 2)
        return Commit(sha, author, subject)

    def _git(self, *arguments: str) -> str:
        process = subprocess.run(
            ["git", *arguments],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        if process.returncode:
            raise GitCommandError(process.stderr.strip() or "git command failed")
        return process.stdout.strip()

    def _git_optional(self, *arguments: str) -> str | None:
        try:
            return self._git(*arguments)
        except GitCommandError:
            return None
