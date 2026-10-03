"""Bounded Discord webhook delivery."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from .config import ScribeConfig


class PublishError(RuntimeError):
    pass


class DiscordPublisher:
    def __init__(self, config: ScribeConfig) -> None:
        self.config = config

    def publish(self, payload: bytes) -> None:
        if self.config.preview:
            print(payload.decode("utf-8"))
            return
        if not self.config.webhook_url:
            raise PublishError("SCRIBE_DISCORD_WEBHOOK_URL is not configured")
        last_error: Exception | None = None
        for attempt in range(self.config.retries):
            try:
                self._post(payload)
                return
            except urllib.error.HTTPError as error:
                last_error = error
                if error.code == 429:
                    self._wait_for_rate_limit(error, attempt)
                elif error.code >= 500:
                    self._wait_for_retry(attempt)
                else:
                    raise PublishError(f"Discord returned HTTP {error.code}") from error
            except (urllib.error.URLError, TimeoutError) as error:
                last_error = error
                self._wait_for_retry(attempt)
        raise PublishError("Discord delivery exhausted retries") from last_error

    def _post(self, payload: bytes) -> None:
        url = f"{self.config.webhook_url}?wait=true"
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "engineering-scribe/1"},
            method="POST",
        )
        timeout = max(self.config.connect_timeout, self.config.request_timeout)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status not in (200, 201, 204):
                raise PublishError(f"Discord returned HTTP {response.status}")

    def _wait_for_rate_limit(
        self, error: urllib.error.HTTPError, attempt: int
    ) -> None:
        retry_after = 2.0
        try:
            body = json.loads(error.read().decode("utf-8"))
            retry_after = float(body.get("retry_after", retry_after))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            pass
        time.sleep(min(retry_after, self.config.retry_after_cap))

    def _wait_for_retry(self, attempt: int) -> None:
        if attempt + 1 < self.config.retries:
            time.sleep(min(2**attempt, self.config.retry_after_cap))
