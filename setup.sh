#!/usr/bin/env bash
# ONE command: publishes Chrono-Sphere to GitHub and turns on automatic live sync.
# Usage:  bash setup.sh [repo-name]
set -uo pipefail
cd "$(dirname "$0")"
REPO="${1:-chrono-sphere}"
command -v git >/dev/null || { echo "Install git first: https://git-scm.com/downloads"; exit 1; }
command -v gh  >/dev/null || { echo "Install GitHub CLI first: https://cli.github.com"; exit 1; }
gh auth status >/dev/null 2>&1 || gh auth login --web --git-protocol https
OWNER="$(gh api user -q .login)"
[ -d .git ] || git init -q -b main
git add -A
git -c user.name="$OWNER" -c user.email="$OWNER@users.noreply.github.com" commit -q -m "Chrono-Sphere live deadline radar" || true
gh repo create "$REPO" --public --source=. --remote=origin --push || { echo "Repo create failed - try another name: bash setup.sh my-name"; exit 1; }
gh api -X POST "repos/$OWNER/$REPO/pages" -f build_type=workflow >/dev/null 2>&1 || gh api -X PUT "repos/$OWNER/$REPO/pages" -f build_type=workflow >/dev/null 2>&1 || true
sleep 4
gh workflow run sync.yml --repo "$OWNER/$REPO" >/dev/null 2>&1 || true
echo
echo "Done. First sync takes about 2 minutes. Your live site:"
echo "  https://$OWNER.github.io/$REPO/"
echo "Progress: https://github.com/$OWNER/$REPO/actions"
