#!/usr/bin/env bash
# Write plan/STATUS.md on the assembly's head and push it (never forced; again on the new head when
# somebody was faster).   bash /tmp/c164_s2/status_push.sh "HH:MM" "what the commit says"
set -uo pipefail
now="${1:?the time, HH:MM}"; msg="${2:?what the commit says}"
cd /tmp/c164_s2/asm || exit 2
for try in 1 2 3 4; do
  git fetch -q origin cursor/c164-assembly-fable-a9f5 2>&1 | sed -E 's#https?://[^ ]+#<remote>#g'
  git checkout -q --detach FETCH_HEAD || exit 2
  python3 /tmp/c164_s2/status_gen.py c164-realms/plan/STATUS.md "$now" || exit 1
  if git diff --quiet; then echo "status_push: nothing new"; exit 0; fi
  git commit -q -am "c164-s2: STATUS: $msg" || exit 1
  out="$(git push origin HEAD:cursor/c164-assembly-fable-a9f5 2>&1 | sed -E 's#https?://[^ ]+#<remote>#g' | tail -1)"
  echo "status_push try $try: $out"
  echo "$out" | grep -qE "rejected|error|fatal" || exit 0
  sleep 2
done
exit 1
