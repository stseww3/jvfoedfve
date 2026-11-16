#!/usr/bin/env bash
# The aide's one write path: bring the assembly in, commit plan/ROSTER.md on top of it, push to the
# assembly (fast-forward only) and to the aide's branch. Never forces. Refuses when any other file
# differs. The roster's commit sits on the assembly's head, so the assembly's first-parent line stays
# the merge keeper's; a merge commit is made only when the assembly moves between fetch and push.
#
#   bash /tmp/c164_aide/roster_push.sh "<what changed, in English>"
set -euo pipefail

TREE=/agent/repos/c164-aide-f3-b9ab
ASM=cursor/c164-assembly-fable-a9f5
MINE=cursor/c164-aide-f3-b9ab
ROSTER=c164-realms/plan/ROSTER.md

[ $# -eq 1 ] && [ -n "$1" ] || { echo "roster_push: give the commit message"; exit 2; }
cd "$TREE"
[ "$(git rev-parse --abbrev-ref HEAD)" = "$MINE" ] || { echo "roster_push: not on $MINE"; exit 1; }

other="$(git status --porcelain | grep -v " $ROSTER\$" || true)"
[ -z "$other" ] || { echo "roster_push: files other than the roster are changed:"; echo "$other"; exit 1; }

fetch_asm() { git fetch -q origin "+refs/heads/$ASM:refs/remotes/origin/$ASM" >/dev/null 2>&1; }

# Fast-forward to the assembly first, carrying the uncommitted roster across.
ok=0
for attempt in 1 2 3 4; do fetch_asm && { ok=1; break; }; sleep $((2 ** attempt)); done
[ "$ok" = 1 ] || { echo "roster_push: cannot fetch the assembly"; exit 1; }
if git merge-base --is-ancestor HEAD "origin/$ASM" && [ "$(git rev-parse HEAD)" != "$(git rev-parse "origin/$ASM")" ]; then
  dirty=0
  git diff --quiet -- "$ROSTER" || dirty=1
  # No `git stash`: the stash is one stack for every working tree of this repository (s2's rule).
  if [ "$dirty" = 1 ]; then
    keep="$(mktemp /tmp/c164_aide/roster.XXXXXX)"; base="$keep.base"
    cp "$ROSTER" "$keep"
    git show "HEAD:$ROSTER" > "$base"
    git checkout -q -- "$ROSTER"
    git merge -q --ff-only "origin/$ASM" || { echo "roster_push: cannot fast-forward; my roster is in $keep"; exit 1; }
    if ! cmp -s "$base" "$ROSTER"; then
      git merge-file -q "$keep" "$base" "$ROSTER" \
        || { echo "roster_push: the assembly changed the roster too and the two do not merge; my roster is in $keep"; exit 1; }
    fi
    cp "$keep" "$ROSTER"
    rm -f "$keep" "$base"
  else
    git merge -q --ff-only "origin/$ASM"
  fi
fi

stamp="$(TZ=Asia/Shanghai date '+%m-%d %H:%M')"
sed -i -E "3s/最近一次更新 [0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}/最近一次更新 $stamp/" "$ROSTER"

git add "$ROSTER"
if git diff --cached --quiet; then
  echo "roster_push: nothing to commit"
else
  git commit -q -m "c164-aide: $1"
fi

pushed=0
for attempt in 1 2 3 4; do
  fetch_asm || { sleep $((2 ** attempt)); continue; }
  if ! git merge-base --is-ancestor "origin/$ASM" HEAD; then
    git merge -q --no-edit -m "c164-aide: merge the assembly ($(git rev-parse --short=8 "origin/$ASM")) before pushing the roster" "origin/$ASM" \
      || { git merge --abort || true; echo "roster_push: the assembly does not merge cleanly; look by hand"; exit 1; }
  fi
  differs="$(git diff --name-only "origin/$ASM" HEAD)"
  if [ -z "$differs" ]; then echo "roster_push: the assembly already has this roster"; pushed=1; break; fi
  [ "$differs" = "$ROSTER" ] || { echo "roster_push: HEAD differs from the assembly in more than the roster:"; echo "$differs"; exit 1; }
  bash c164-realms/tools/provenance.sh HEAD >/dev/null || { echo "roster_push: HEAD is NOT CLEAN; nothing pushed"; exit 1; }
  if git push -q origin "HEAD:refs/heads/$ASM" >/dev/null 2>&1; then pushed=1; break; fi
  sleep $((2 ** attempt))
done
git push -q origin "HEAD:refs/heads/$MINE" >/dev/null 2>&1 || echo "roster_push: could not push $MINE"
if [ "$pushed" = 1 ]; then
  echo "roster_push: assembly and $MINE at $(git rev-parse --short=8 HEAD)"
else
  echo "roster_push: the assembly was NOT updated (rejected four times); $MINE at $(git rev-parse --short=8 HEAD)"
  exit 1
fi
