"""Deterministic digest generation without inferred behavior claims."""

from __future__ import annotations

import re
from collections import Counter

from .models import ChangeSet, Digest, FileChange


class PathClassifier:
    CATEGORY_RULES = (
        ("UI/UX", ("ui/", "frontend/", "client/", "components/", "views/")),
        ("Backend", ("server/", "backend/", "api/", "services/")),
        ("Testing", ("test/", "tests/", "spec/", "__tests__/")),
        ("Documentation", ("docs/", "readme", ".md")),
        ("Infrastructure", (".github/", "infra/", "deploy/", "docker")),
        ("Database", ("migrations/", "schema/", "database/", "db/")),
        ("Security", ("auth/", "security/", "permission")),
    )

    def classify(self, paths: tuple[FileChange, ...]) -> tuple[str, ...]:
        categories: list[str] = []
        lowered = [change.path.lower() for change in paths]
        for category, markers in self.CATEGORY_RULES:
            if any(any(marker in path for marker in markers) for path in lowered):
                categories.append(category)
        return tuple(categories or ["Engineering"])


class NoisePolicy:
    NOISE_NAMES = {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "wally.lock",
    }
    NOISE_PARTS = {"node_modules", "dist", "build", "vendor"}

    def substantive(self, changes: tuple[FileChange, ...]) -> tuple[FileChange, ...]:
        return tuple(change for change in changes if not self._is_noise(change.path))

    def _is_noise(self, path: str) -> bool:
        parts = set(path.split("/"))
        file_name = path.rsplit("/", 1)[-1].lower()
        return file_name in self.NOISE_NAMES or bool(parts & self.NOISE_PARTS)


class FactualDigestBuilder:
    CONVENTIONAL_PREFIX = re.compile(
        r"^(feat|fix|docs|chore|refactor|perf|test|build|ci|style)(\([^)]*\))?:\s*",
        re.IGNORECASE,
    )

    def __init__(self, classifier: PathClassifier | None = None) -> None:
        self.classifier = classifier or PathClassifier()

    def build(self, change_set: ChangeSet) -> Digest:
        subjects = [self._clean_subject(commit.subject) for commit in change_set.commits]
        title = subjects[-1] if subjects else "Development update"
        if len(subjects) > 1:
            title = f"{title} (+{len(subjects) - 1} more)"
        title = title[:80]
        developers = tuple(dict.fromkeys(commit.author for commit in change_set.commits))
        counts = Counter(change.status for change in change_set.files)
        statuses = ", ".join(
            f"{count} {self._status_name(status)}" for status, count in sorted(counts.items())
        )
        changed = (
            f"Commit subjects: {'; '.join(subjects[:5])}. "
            f"Files: {statuses or 'none'}; "
            f"diff size +{change_set.additions}/−{change_set.deletions}."
        )
        latest = subjects[-1] if subjects else "Development update"
        achieved = (
            f"Recorded outcome from commit subject only: {latest}. "
            "No additional behavior claims without code-level evidence."
        )
        technical = tuple(self._describe(change) for change in change_set.files[:8])
        impact = (
            f"Documents push `{change_set.branch}` at `{change_set.after[:7]}` "
            f"for the engineering journal ({len(change_set.files)} substantive files)."
        )
        return Digest(
            title=title,
            developers=developers or ("Unknown",),
            categories=self.classifier.classify(change_set.files),
            changed=changed,
            achieved=achieved,
            technical_changes=technical,
            impact=impact,
        )

    def _clean_subject(self, subject: str) -> str:
        return self.CONVENTIONAL_PREFIX.sub("", subject).strip() or subject

    @staticmethod
    def _status_name(status: str) -> str:
        return {"A": "added", "M": "modified", "D": "deleted", "R": "renamed"}.get(
            status, "changed"
        )

    def _describe(self, change: FileChange) -> str:
        action = self._status_name(change.status).capitalize()
        if change.previous_path:
            return f"{action} `{change.previous_path}` → `{change.path}`"
        return f"{action} `{change.path}`"
