#!/usr/bin/env bash
# A card's new branch has been reported: check it and write it into the roster.
#
#   bash /tmp/c164_aide/claim.sh <new branch> <head it must hold> "<commit message, English>" [<delivered branch> <delivered commit>]
#
# Checks: the branch is on the remote, holds the first-shift head named (or any commit named, when
# the card has no predecessor), tools/provenance.sh calls it clean; when a delivered branch and
# commit are given, that the commit is on that branch. Then roster_sync.py --fix and roster_push.sh.
set -euo pipefail

TREE=/agent/repos/c164-aide-f3-b9ab
[ $# -ge 3 ] || { echo "claim: branch, base, message"; exit 2; }
branch="$1"; base="$2"; msg="$3"
cd "$TREE"

git fetch -q origin "+refs/heads/$branch:refs/remotes/origin/$branch" || { echo "claim: $branch is not on the remote"; exit 1; }
git merge-base --is-ancestor "$base" "origin/$branch" || { echo "claim: $branch does NOT hold $base"; exit 1; }
echo "claim: $branch holds $base"
bash c164-realms/tools/provenance.sh "origin/$branch" | tail -n 1
bash c164-realms/tools/provenance.sh "origin/$branch" >/dev/null || { echo "claim: $branch is NOT CLEAN; nothing written"; exit 1; }

if [ $# -ge 5 ]; then
  git fetch -q origin "+refs/heads/$4:refs/remotes/origin/$4" || { echo "claim: $4 is not on the remote"; exit 1; }
  if git merge-base --is-ancestor "$5" "origin/$4"; then
    echo "claim: delivered commit $5 is on $4"
  else
    echo "claim: delivered commit $5 is NOT on $4"
  fi
  git fetch -q origin "+refs/heads/cursor/c164-assembly-fable-a9f5:refs/remotes/origin/cursor/c164-assembly-fable-a9f5"
  if git merge-base --is-ancestor "$5" origin/cursor/c164-assembly-fable-a9f5; then
    echo "claim: $5 is in the assembly"
  else
    echo "claim: $5 is not in the assembly yet"
  fi
fi

python3 /tmp/c164_aide/roster_sync.py --fix "$branch" | tail -n 6
bash /tmp/c164_aide/roster_push.sh "$msg" | tail -n 3
