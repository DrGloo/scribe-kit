from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from engineering_scribe.digest import FactualDigestBuilder, NoisePolicy
from engineering_scribe.ledger import EventLedger
from engineering_scribe.models import ChangeSet, Commit, FileChange
from engineering_scribe.render import DiscordEmbedRenderer


class Fixture:
    @staticmethod
    def change_set() -> ChangeSet:
        return ChangeSet(
            branch="feature/scribe",
            before="a" * 40,
            after="b" * 40,
            commits=(
                Commit("b" * 40, "Ada", "feat: add factual reporting"),
                Commit("c" * 40, "Grace", "fix: cap Discord payload"),
            ),
            files=(
                FileChange("A", "src/report.py"),
                FileChange("M", "tests/test_report.py"),
            ),
            additions=42,
            deletions=7,
        )


class FactualDigestTests(unittest.TestCase):
    def test_digest_uses_only_observed_metadata(self) -> None:
        change_set = Fixture.change_set()
        digest = FactualDigestBuilder().build(change_set)
        self.assertEqual(digest.confidence, "low")
        self.assertEqual(digest.developers, ("Ada", "Grace"))
        self.assertIn("cap Discord payload", digest.title)
        self.assertIn("+42/−7", digest.changed)

    def test_noise_policy_removes_generated_paths(self) -> None:
        changes = (
            FileChange("M", "dist/app.js"),
            FileChange("M", "src/app.py"),
            FileChange("M", "package-lock.json"),
        )
        self.assertEqual(
            NoisePolicy().substantive(changes),
            (FileChange("M", "src/app.py"),),
        )


class RenderingTests(unittest.TestCase):
    def test_payload_is_valid_and_preserves_footer(self) -> None:
        change_set = Fixture.change_set()
        digest = FactualDigestBuilder().build(change_set)
        payload = DiscordEmbedRenderer().render(
            digest, change_set, "https://github.com/example/repo/commit/" + "b" * 40
        )
        embed = json.loads(payload)["embeds"][0]
        self.assertLessEqual(len(embed["description"]), 4096)
        self.assertIn("**Commit**", embed["description"])
        self.assertIn("**Branch**", embed["description"])


class LedgerTests(unittest.TestCase):
    def test_event_is_marked_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = EventLedger(Path(directory), maximum_entries=2)
            ledger.mark("main@one")
            ledger.mark("main@one")
            self.assertTrue(ledger.contains("main@one"))
            self.assertEqual(ledger.path.read_text().splitlines(), ["main@one"])


if __name__ == "__main__":
    unittest.main()
