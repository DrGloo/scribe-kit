# Engineering Scribe

A standalone, dependency-free Python package that posts factual Git push summaries to Discord.
GitHub Actions is the sole publisher; local hooks only preview payloads.

## Install into a repository

```bash
/Users/rai/Documents/GitHub/scribe-kit/install.sh /path/to/repository
```

The installer vendors the runtime into `.scribe/`, adds the workflow, and installs a local
preview hook without replacing an existing `pre-push` hook. Commit those generated files so
GitHub Actions has the exact runtime tested locally.

Add `SCRIBE_DISCORD_WEBHOOK_URL` as a GitHub repository Actions secret. Do not commit the URL.
If the target repository does not already use `.githooks`, enable that directory using the
repository's normal hook setup. If it has an existing `pre-push`, integrate
`.githooks/scribe-pre-push` while preserving stdin for both hooks.

## Preview

From an installed repository:

```bash
PYTHONPATH=.scribe python3 -m engineering_scribe.cli \
  --preview \
  --range HEAD~1..HEAD \
  --branch "$(git branch --show-current)"
```

Preview mode performs no network request and writes no idempotency marker.

## Configuration

Only literal `SCRIBE_*` entries are read from a local `.env`; values are never evaluated and
existing environment variables win.

```dotenv
SCRIBE_DISCORD_WEBHOOK_URL=
SCRIBE_DISCORD_CONNECT_TIMEOUT=10
SCRIBE_DISCORD_MAX_TIME=30
SCRIBE_DISCORD_RETRIES=3
SCRIBE_DISCORD_MAX_RETRY_AFTER=30
```

Additional controls:

- `SCRIBE_SKIP=1` — suppress invocation.
- `SCRIBE_ENABLED=0` — disable invocation.
- `SCRIBE_CACHE_DIR=/path` — override the local ledger location.
- `SCRIBE_PREVIEW=1` — force preview mode.

## Behavior

- Reports non-merge commits in `BEFORE..AFTER`.
- Uses commit subjects, authors, name-status, and numstat only.
- Labels generated text as low-confidence and makes no inferred behavior claims.
- Removes common generated/vendor/lockfile-only changes.
- Supports multiple authors.
- Preserves commit and branch metadata when truncating Discord embeds.
- Keys idempotency by `branch@tip-sha`.
- Retries transient Discord errors and honors bounded `retry_after`.

`PathClassifier.CATEGORY_RULES` and `NoisePolicy` in `digest.py` are the intended extension
points for project-specific categorization.

## Update installed repositories

Run the installer again. It replaces only the vendored `.scribe/engineering_scribe` runtime,
the Scribe workflow, and the dedicated `scribe-pre-push` helper. It preserves unrelated hooks
and project files.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m pip install -e .
engineering-scribe --help
```

Requires Python 3.10 or newer and Git. Runtime dependencies are standard-library only.
