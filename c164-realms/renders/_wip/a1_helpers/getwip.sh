#!/usr/bin/env bash
# getwip.sh <dir>: the pictures of the scratch branch's head into /tmp/c164_a1/<dir> (a/b.png as a_b.png)
set -euo pipefail
cd /agent/repos/c164-a1-board-f3-09d2
git fetch -q origin cursor/c164-a1-board-f3-09d2-wip
mkdir -p "/tmp/c164_a1/$1"
for f in $(git ls-tree -r --name-only FETCH_HEAD -- c164-realms/renders/_wip); do
  rel="${f#c164-realms/renders/_wip/}"
  git show "FETCH_HEAD:$f" > "/tmp/c164_a1/$1/${rel//\//_}"
done
git log -1 --format='%h %s' FETCH_HEAD | cut -c1-120
ls "/tmp/c164_a1/$1"
