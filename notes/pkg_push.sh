#!/bin/bash
# pkg_push.sh <category>/<package> <delivered commit>
# The approver's merge of one delivery of the common line (the author's gate has passed; its summary and
# the provenance are looked at before this is called): in the detached worktree, on the assembly's
# head, merge --no-ff, provenance of the result, push; when the head has moved, again. Never forced.
# Light: git only.
set -u
card="$1"; sha="$2"
asm=/tmp/c164_s2/asm
branch=cursor/c164-assembly-fable-a9f5
filt() { sed -E 's#https?://[^ ]+#<remote>#g'; }
cd "$asm" || exit 1
for try in 1 2 3 4; do
  git fetch -q origin "$branch" 2>&1 | filt
  git checkout -q --detach FETCH_HEAD 2>&1 | filt
  base=$(git rev-parse --short=8 HEAD)
  if ! bash c164-realms/tools/provenance.sh "$sha" 2>&1 | filt | tail -n 1 | grep -q clean; then
    echo "pkg_push: the provenance of $sha is not clean; nothing merged"; exit 1
  fi
  if ! git merge -q --no-ff --no-edit -m "c164-s2: merge $card $(git rev-parse --short=8 "$sha")" "$sha" 2>&1 | filt; then
    echo "pkg_push: the merge does not go in cleanly"; git merge --abort 2>/dev/null; exit 1
  fi
  if ! bash c164-realms/tools/provenance.sh HEAD 2>&1 | filt | tail -n 1 | grep -q clean; then
    echo "pkg_push: the provenance of the merge is not clean; nothing pushed"; exit 1
  fi
  out=$(git push -q origin "HEAD:$branch" 2>&1 | filt)
  if echo "$out" | grep -q -E 'rejected|error|fatal'; then
    echo "pkg_push try $try: the head moved, again"; sleep $((try * 2)); continue
  fi
  echo "pkg_push: $card $(git rev-parse --short=8 "$sha") -> $(git rev-parse --short=8 HEAD) (base $base; $(git diff --stat HEAD^1 HEAD | tail -n 1 | sed 's/^ *//'))"
  exit 0
done
echo "pkg_push: gave up after four tries"; exit 1
