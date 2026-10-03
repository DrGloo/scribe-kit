"""Discord embed rendering with platform limits."""

from __future__ import annotations

import json

from .models import ChangeSet, Digest


class DiscordEmbedRenderer:
    DESCRIPTION_LIMIT = 4096
    EMBED_COLOR = 5_793_266

    def render(
        self,
        digest: Digest,
        change_set: ChangeSet,
        commit_url: str | None,
    ) -> bytes:
        technical = "\n".join(f"• {item}" for item in digest.technical_changes)
        footer = self._footer(change_set, commit_url)
        sections = [
            f"**Developer**\n{', '.join(digest.developers)}",
            f"**Category**\n{', '.join(digest.categories)}",
            f"**What Changed**\n{digest.change_summary}",
            f"**What Was Achieved**\n{digest.achieved}",
            f"**Technical Changes**\n{technical or 'No file changes listed.'}",
            f"**Impact**\n{digest.impact}",
        ]
        description = self._fit_sections(sections, footer)
        payload = {
            "username": "The Scribe",
            "embeds": [
                {
                    "title": "🛠️ Development Update — The Scribe",
                    "description": description,
                    "color": self.EMBED_COLOR,
                }
            ],
        }
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def _fit_sections(self, sections: list[str], footer: str) -> str:
        available = self.DESCRIPTION_LIMIT - len(footer) - 2
        content = "\n\n".join(sections)
        if len(content) > available:
            content = content[: max(0, available - 1)].rstrip() + "…"
        return f"{content}\n\n{footer}"

    @staticmethod
    def _footer(change_set: ChangeSet, commit_url: str | None) -> str:
        abbreviated_sha = change_set.short_after_sha
        commit = (
            f"[`{abbreviated_sha}`]({commit_url})"
            if commit_url
            else f"`{abbreviated_sha}`"
        )
        link = f"\n\n[🔗 View Commit]({commit_url})" if commit_url else ""
        return (
            f"**Commit**\n{commit}\n"
            f"**Branch**\n`{change_set.branch}`"
            f"{link}"
        )
