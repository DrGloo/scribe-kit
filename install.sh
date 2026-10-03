#!/usr/bin/env bash
# Vendor Engineering Scribe into another Git repository.
set -eu

PACKAGE_ROOT="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
TARGET="${1:-.}"
TARGET="$(CDPATH='' cd -- "$TARGET" && pwd)"

if [ ! -d "$TARGET/.git" ]; then
	echo "error: target is not a Git repository: $TARGET" >&2
	exit 2
fi

mkdir -p "$TARGET/.scribe" "$TARGET/.github/workflows" "$TARGET/.githooks"
rm -rf "$TARGET/.scribe/engineering_scribe"
cp -R "$PACKAGE_ROOT/src/engineering_scribe" "$TARGET/.scribe/engineering_scribe"
rm -rf "$TARGET/.scribe/engineering_scribe/__pycache__"
cp "$PACKAGE_ROOT/templates/scribe.yml" "$TARGET/.github/workflows/scribe.yml"
cp "$PACKAGE_ROOT/templates/scribe-pre-push" "$TARGET/.githooks/scribe-pre-push"
chmod +x "$TARGET/.githooks/scribe-pre-push"

append_ignore() {
	local pattern="$1"
	touch "$TARGET/.gitignore"
	# Ensure the file ends with a newline before appending.
	if [ -s "$TARGET/.gitignore" ] && [ "$(tail -c 1 "$TARGET/.gitignore" | wc -l)" -eq 0 ]; then
		printf '\n' >>"$TARGET/.gitignore"
	fi
	grep -Fxq "$pattern" "$TARGET/.gitignore" || printf '%s\n' "$pattern" >>"$TARGET/.gitignore"
}

append_ignore ".scribe-ci-cache/"
append_ignore ".env"

if [ ! -e "$TARGET/.githooks/pre-push" ]; then
	cp "$TARGET/.githooks/scribe-pre-push" "$TARGET/.githooks/pre-push"
	chmod +x "$TARGET/.githooks/pre-push"
	echo "Installed local preview as .githooks/pre-push"
elif cmp -s "$TARGET/.githooks/pre-push" "$TARGET/.githooks/scribe-pre-push"; then
	echo "Local preview hook already installed"
else
	echo "Preserved existing .githooks/pre-push."
	echo "Integrate .githooks/scribe-pre-push with that hook if previews are wanted."
fi

cat <<EOF
Engineering Scribe installed in:
  $TARGET/.scribe

Next:
  1. Add repository secret SCRIBE_DISCORD_WEBHOOK_URL.
  2. Ensure that repository uses its .githooks directory.
  3. Preview with:
     PYTHONPATH="$TARGET/.scribe" python3 -m engineering_scribe.cli \\
       --preview --range HEAD~1..HEAD --branch "\$(git -C "$TARGET" branch --show-current)"
  4. Commit .scribe, .github/workflows/scribe.yml, and hook changes.
EOF
