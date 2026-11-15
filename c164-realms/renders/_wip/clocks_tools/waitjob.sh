#!/usr/bin/env bash
# waitjob.sh <job id> [seconds]: wait for the receipt of a job sent with a0job.sh --wait 0
id="${1:?job id}"; limit="${2:-600}"
cd /agent/repos/c164-clocks-f3-00d6 || exit 2
t0=$SECONDS
while [ $((SECONDS - t0)) -lt "$limit" ]; do
  out="$(bash /tmp/a0job.sh --receipt "$id" 2>&1)"; code=$?
  if [ "$code" != 75 ]; then printf '%s\n' "$out" | tail -n 45; echo "receipt exit=$code"; exit "$code"; fi
  sleep 20
done
bash /tmp/a0job.sh --queue 2>&1 | grep -n "clocks" | head -3
echo "no receipt yet after $limit s"
exit 75
