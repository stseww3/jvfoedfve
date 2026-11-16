#!/usr/bin/env bash
# The aide's helper scripts and the dealer's state go to a -wip branch of the aide's own, so that
# nothing is kept on this machine only (the director's rule of 11-16 07:53: machines may vanish).
# The branch is never merged; the assembly gets plan/ROSTER.md from the aide and nothing else.
#
#   bash /tmp/c164_aide/wip_push.sh ["<what changed, English>"]
#
# No worktree: the commit is built with an index of its own on top of the branch's last commit
# (the assembly's head the first time).
set -euo pipefail

TREE=/agent/repos/c164-aide-f3-b9ab
BR=cursor/c164-aide-f3-wip-b9ab
ASM=cursor/c164-assembly-fable-a9f5
SRC=/tmp/c164_aide
DEST=c164-realms/plan/aide-wip
msg="${1:-the helper scripts and the state of the dealer}"

cd "$TREE"
export GIT_INDEX_FILE="$SRC/.wip.index"

if git fetch -q origin "+refs/heads/$BR:refs/remotes/origin/$BR" 2>/dev/null; then
  parent=$(git rev-parse "origin/$BR")
else
  git fetch -q origin "+refs/heads/$ASM:refs/remotes/origin/$ASM"
  parent=$(git rev-parse "origin/$ASM")
fi

git read-tree "$parent"
git rm -q -r --cached --ignore-unmatch "$DEST" >/dev/null 2>&1 || true
for f in "$SRC"/*.py "$SRC"/*.sh "$SRC"/deal.json "$SRC"/deal_notes.md "$SRC"/scratch.txt \
         "$SRC"/asked.json "$SRC"/first_seen.json "$SRC"/lists-0935.md "$SRC"/newhires.md \
         "$SRC"/board.json \
         /cursor/stores/self/c164-aide-f3/NOTES.md; do
  [ -f "$f" ] || continue
  if grep -q "a_[0-9a-f]\{16\}" "$f"; then echo "wip_push: $f names an identity; left out"; continue; fi
  blob=$(git hash-object -w "$f")
  git update-index --add --cacheinfo "100644,$blob,$DEST/$(basename "$f")"
done

tree=$(git write-tree)
if [ "$tree" = "$(git rev-parse "$parent^{tree}")" ]; then
  echo "wip_push: nothing new"
  exit 0
fi
commit=$(git commit-tree "$tree" -p "$parent" -m "c164-aide: wip: $msg")
bash c164-realms/tools/provenance.sh "$commit" >/dev/null || { echo "wip_push: NOT CLEAN, nothing pushed"; exit 1; }
git push -q origin "$commit:refs/heads/$BR"
echo "wip_push: $BR at ${commit:0:8}"
