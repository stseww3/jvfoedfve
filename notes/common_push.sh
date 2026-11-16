#!/bin/bash
# common_push.sh <commit on my branch> "<what, in English>"
# Brings one of my own common commits (tested on a node) into the assembly as a merge on its first-parent
# line, the way the approvers' merges go in; then my branch follows the assembly. Light: git only.
set -u
sha="$1"; what="$2"
asm=/tmp/c164_s2/asm
mine=/agent/repos/c164-s2-fable
branch=cursor/c164-assembly-fable-a9f5
filt() { sed -E 's#https?://[^ ]+#<remote>#g'; }
cd "$asm" || exit 1
for try in 1 2 3 4; do
  git fetch -q origin "$branch" 2>&1 | filt
  git checkout -q --detach FETCH_HEAD 2>&1 | filt
  if ! git merge -q --no-ff --no-edit -m "c164-s2: merge common $(git rev-parse --short=8 "$sha"): $what" "$sha" 2>&1 | filt; then
    echo "common_push: the merge does not go in cleanly"; git merge --abort 2>/dev/null; exit 1
  fi
  if ! bash c164-realms/tools/provenance.sh HEAD 2>&1 | filt | tail -n 1 | grep -q clean; then
    bash c164-realms/tools/provenance.sh HEAD 2>&1 | filt | tail -n 3
    echo "common_push: provenance is not clean; nothing pushed"; exit 1
  fi
  if git push -q origin "HEAD:$branch" 2>&1 | filt | grep -q -E 'rejected|error|fatal'; then
    echo "common_push try $try: the head moved, again"; sleep $((try * 2)); continue
  fi
  new=$(git rev-parse --short=8 HEAD)
  echo "common_push: $new on the assembly ($(git diff --stat HEAD^1 HEAD | tail -n 1 | sed 's/^ *//'))"
  cd "$mine" && git merge -q --ff-only "$new" 2>&1 | filt && git push -q -u origin cursor/c164-s2-fable-89df 2>&1 | filt | tail -n 1
  echo "my branch: $(git rev-parse --short=8 HEAD)"
  exit 0
done
echo "common_push: gave up after four tries"; exit 1
