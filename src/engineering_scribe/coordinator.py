"""Application coordinator for report generation and publication."""

from __future__ import annotations

from dataclasses import replace

from .config import ScribeConfig
from .digest import FactualDigestBuilder, NoisePolicy
from .ledger import EventLedger
from .publisher import DiscordPublisher
from .render import DiscordEmbedRenderer
from .repository import GitRepository


class ScribeCoordinator:
    def __init__(
        self,
        repository: GitRepository,
        config: ScribeConfig,
        noise_policy: NoisePolicy | None = None,
    ) -> None:
        self.repository = repository
        self.config = config
        self.noise_policy = noise_policy or NoisePolicy()
        self.digest_builder = FactualDigestBuilder()
        self.renderer = DiscordEmbedRenderer()
        self.publisher = DiscordPublisher(config)
        self.ledger = EventLedger(config.cache_dir)

    def report(self, revision_range: str, branch: str) -> str:
        change_set = self.repository.collect(revision_range, branch)
        substantive = self.noise_policy.substantive(change_set.files)
        if not change_set.commits or not substantive:
            return "suppressed"
        change_set = replace(change_set, files=substantive)
        if self.ledger.contains(change_set.event_id):
            return "duplicate"
        digest = self.digest_builder.build(change_set)
        payload = self.renderer.render(
            digest,
            change_set,
            self.repository.commit_url(change_set.after),
        )
        self.publisher.publish(payload)
        if not self.config.preview:
            self.ledger.mark(change_set.event_id)
        return "previewed" if self.config.preview else "posted"
