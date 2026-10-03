"""Bounded local idempotency ledger."""

from __future__ import annotations

from pathlib import Path


class EventLedger:
    DEFAULT_MAXIMUM_ENTRIES = 5000

    def __init__(
        self, cache_dir: Path, maximum_entries: int = DEFAULT_MAXIMUM_ENTRIES
    ) -> None:
        self.cache_dir = cache_dir
        self.maximum_entries = maximum_entries
        self.path = cache_dir / "posted.log"

    def contains(self, event_id: str) -> bool:
        if not self.path.is_file():
            return False
        return any(
            line == event_id
            for line in self.path.read_text(encoding="utf-8").splitlines()
        )

    def mark(self, event_id: str) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        entries = self.path.read_text(encoding="utf-8").splitlines() if self.path.exists() else []
        if event_id not in entries:
            entries.append(event_id)
        bounded = entries[-self.maximum_entries :]
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text("\n".join(bounded) + "\n", encoding="utf-8")
        temporary.replace(self.path)
