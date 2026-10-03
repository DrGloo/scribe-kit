"""Configuration loading with no shell evaluation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class DotEnvLoader:
    """Loads literal SCRIBE_* assignments without overriding the environment."""

    def load(self, path: Path) -> None:
        if not path.is_file():
            return
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key.startswith("SCRIBE_") or not key.replace("_", "").isalnum():
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ.setdefault(key, value)


@dataclass(frozen=True)
class ScribeConfig:
    webhook_url: str | None
    connect_timeout: float
    request_timeout: float
    retries: int
    retry_after_cap: float
    cache_dir: Path
    preview: bool

    @classmethod
    def from_environment(
        cls, repository_path: Path, preview: bool = False
    ) -> "ScribeConfig":
        DotEnvLoader().load(repository_path / ".env")
        return cls(
            webhook_url=os.getenv("SCRIBE_DISCORD_WEBHOOK_URL") or None,
            connect_timeout=float(os.getenv("SCRIBE_DISCORD_CONNECT_TIMEOUT", "10")),
            request_timeout=float(os.getenv("SCRIBE_DISCORD_MAX_TIME", "30")),
            retries=max(1, int(os.getenv("SCRIBE_DISCORD_RETRIES", "3"))),
            retry_after_cap=float(os.getenv("SCRIBE_DISCORD_MAX_RETRY_AFTER", "30")),
            cache_dir=Path(
                os.getenv("SCRIBE_CACHE_DIR", repository_path / ".git" / "scribe-cache")
            ),
            preview=preview or os.getenv("SCRIBE_PREVIEW") == "1",
        )
