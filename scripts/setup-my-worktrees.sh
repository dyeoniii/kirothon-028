#!/usr/bin/env bash
set -euo pipefail
# Run in a clean clone of the shared repository, after the initial commit is pushed.
# Examples: bash scripts/setup-my-worktrees.sh A /absolute/path/to/workspaces
#           bash scripts/setup-my-worktrees.sh B /absolute/path/to/workspaces
ROLE="${1:-}"
BASE="${2:-}"
if [[ "$ROLE" != "A" && "$ROLE" != "B" || -z "$BASE" ]]; then
  echo 'Usage: bash scripts/setup-my-worktrees.sh A|B /absolute/path/to/workspaces' >&2; exit 2
fi
if ! git rev-parse --show-toplevel >/dev/null 2>&1; then echo 'Not in a Git repository' >&2; exit 2; fi
if [[ -n "$(git status --porcelain)" ]]; then echo 'Commit/stash changes first.' >&2; exit 2; fi
mkdir -p "$BASE"
if [[ "$ROLE" == "A" ]]; then
  BRANCHES=(feat/frontend feat/docs-pdf)
  NAMES=(potato-s1-fe potato-s2-doc)
else
  BRANCHES=(feat/backend-api feat/analysis)
  NAMES=(potato-s3-api potato-s4-ai)
fi
for i in 0 1; do
  b="${BRANCHES[$i]}"; dest="$BASE/${NAMES[$i]}"
  if [[ -e "$dest" ]]; then echo "Already exists: $dest (skipping)"; continue; fi
  if git show-ref --verify --quiet "refs/heads/$b"; then git worktree add "$dest" "$b"; else git worktree add -b "$b" "$dest" HEAD; fi
  echo "Created $dest → $b"
done
