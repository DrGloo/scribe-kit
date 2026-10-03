"""Command-line interface."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .config import ScribeConfig
from .coordinator import ScribeCoordinator
from .publisher import PublishError
from .repository import GitCommandError, GitRepository


class ScribeCli:
    def run(self, arguments: list[str] | None = None) -> int:
        parser = self._build_parser()
        options = parser.parse_args(arguments)
        repository_path = Path(options.repository).resolve()
        if os.getenv("SCRIBE_SKIP") == "1" or os.getenv("SCRIBE_ENABLED") == "0":
            print("[scribe] disabled")
            return 0
        try:
            config = ScribeConfig.from_environment(repository_path, options.preview)
            coordinator = ScribeCoordinator(GitRepository(repository_path), config)
            outcome = coordinator.report(options.revision_range, options.branch)
        except (GitCommandError, PublishError, ValueError) as error:
            print(f"[scribe] error: {error}", file=sys.stderr)
            return 1
        print(f"[scribe] {outcome.value}: {options.branch} {options.revision_range}")
        return 0

    @staticmethod
    def _build_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="engineering-scribe",
            description="Publish a factual Git push journal entry to Discord.",
        )
        parser.add_argument("--range", dest="revision_range", required=True)
        parser.add_argument("--branch", required=True)
        parser.add_argument("--repository", default=".")
        parser.add_argument(
            "--preview",
            action="store_true",
            help="print the Discord payload without network access or ledger writes",
        )
        return parser


def main() -> int:
    return ScribeCli().run()


if __name__ == "__main__":
    raise SystemExit(main())
