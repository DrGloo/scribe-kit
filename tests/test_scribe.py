from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from engineering_scribe.config import ScribeConfig
from engineering_scribe.digest import FactualDigestBuilder, NoisePolicy, PathClassifier
from engineering_scribe.ledger import EventLedger
from engineering_scribe.models import ChangeSet, Commit, FileChange
from engineering_scribe.publisher import DiscordPublisher, PublishError
from engineering_scribe.render import DiscordEmbedRenderer
from engineering_scribe.repository import GitCommandError, GitRepository


class SampleChangeSet:
    @staticmethod
    def build() -> ChangeSet:
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
        change_set = SampleChangeSet.build()
        digest = FactualDigestBuilder().build(change_set)
        self.assertEqual(digest.developers, ("Ada", "Grace"))
        self.assertIn("cap Discord payload", digest.title)
        self.assertIn("+42/−7", digest.change_summary)

    def test_noise_policy_removes_generated_paths(self) -> None:
        changes = (
            FileChange("M", "dist/app.js"),
            FileChange("M", "src/app.py"),
            FileChange("M", "package-lock.json"),
        )
        self.assertEqual(
            NoisePolicy().filter_substantive(changes),
            (FileChange("M", "src/app.py"),),
        )


class PathClassifierTests(unittest.TestCase):
    def test_avoids_substring_false_positives(self) -> None:
        classifier = PathClassifier()
        categories = classifier.classify(
            (
                FileChange("M", "src/myreadmenu.py"),
                FileChange("M", "src/permissionless.py"),
            )
        )
        self.assertEqual(categories, ("Engineering",))

    def test_matches_path_segments_and_prefixed_dirs(self) -> None:
        classifier = PathClassifier()
        categories = classifier.classify(
            (
                FileChange("M", "docs/guide.md"),
                FileChange("M", "README.md"),
                FileChange("M", "auth/login.py"),
                FileChange("A", "docker/compose.yml"),
            )
        )
        self.assertIn("Documentation", categories)
        self.assertIn("Security", categories)
        self.assertIn("Infrastructure", categories)

    def test_matches_dot_directories_and_plural_segments(self) -> None:
        classifier = PathClassifier()
        self.assertEqual(
            classifier.classify((FileChange("M", ".github/workflows/test.yml"),)),
            ("Infrastructure",),
        )
        self.assertEqual(
            classifier.classify((FileChange("M", "src/permissions.py"),)),
            ("Security",),
        )
        self.assertEqual(
            classifier.classify((FileChange("A", "Dockerfile"),)),
            ("Infrastructure",),
        )


class RenderingTests(unittest.TestCase):
    def test_payload_is_valid_and_preserves_footer(self) -> None:
        change_set = SampleChangeSet.build()
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


class RepositoryTests(unittest.TestCase):
    def test_collect_files_handles_copy_status(self) -> None:
        repository = GitRepository(Path("."))
        with patch.object(
            repository,
            "_git",
            return_value="C100\told.py\tnew.py\nM\tsrc/app.py",
        ):
            files = repository._collect_files("HEAD~1..HEAD")
        self.assertEqual(
            files,
            (
                FileChange("C", "new.py", "old.py"),
                FileChange("M", "src/app.py"),
            ),
        )

    def test_parse_commit_rejects_malformed_lines(self) -> None:
        with self.assertRaises(GitCommandError):
            GitRepository._parse_commit("not-a-valid-commit-line")

    def test_git_timeout_raises_command_error(self) -> None:
        repository = GitRepository(Path("."))
        with patch(
            "engineering_scribe.repository.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["git"], timeout=30),
        ):
            with self.assertRaises(GitCommandError) as context:
                repository._git("status")
        self.assertIn("timed out", str(context.exception))


class PublisherTests(unittest.TestCase):
    def test_http_error_response_is_closed(self) -> None:
        config = ScribeConfig(
            webhook_url="https://discord.example/webhook",
            connect_timeout=1,
            request_timeout=1,
            retries=1,
            retry_after_cap=1,
            cache_dir=Path("."),
            preview=False,
        )
        publisher = DiscordPublisher(config)
        error = urllib.error.HTTPError(
            url="https://discord.example/webhook",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(b"bad"),
        )
        close = MagicMock(wraps=error.close)
        error.close = close  # type: ignore[method-assign]
        with patch.object(publisher, "_post", side_effect=error):
            with self.assertRaises(PublishError):
                publisher.publish(b"{}")
        close.assert_called()


if __name__ == "__main__":
    unittest.main()
