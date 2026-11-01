#!/usr/bin/env bash
# Publish one run without deleting earlier runs or its existing diagnostic files.
set -euo pipefail
source_dir=$(cd "$1" && pwd -P)
remote=$2
run_id=$3
work=$4
if [[ ! "$run_id" =~ ^[0-9]+$ ]]; then echo "Run id must be numeric" >&2; exit 2; fi
mkdir -p "$work"
cd "$work"
git init -q
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git remote add origin "$remote"
if git fetch -q --depth 1 origin previews 2>/dev/null; then
  git checkout -q -B previews FETCH_HEAD
else
  git checkout -q --orphan previews
fi
destination="previews/$run_id"
mkdir -p "$destination"
cp -R "$source_dir/." "$destination/"
git add "$destination"
if git diff --cached --quiet; then exit 0; fi
git commit -q -m "Review copy for run $run_id"
for attempt in 1 2 3; do
  if git push -q origin HEAD:previews; then exit 0; fi
  git fetch -q origin previews
  git rebase origin/previews
done
echo "Review publication failed after concurrent-update retries" >&2
exit 1
