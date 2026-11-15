#!/usr/bin/env bash
# Send one job to the director's machine and wait for its receipt.
#
# On 11-16 most worker nodes stopped at once. Until they are back, the director's own machine
# (4 cores, nobody else on it) draws for everyone: offline pictures and checks, one job at a
# time, in the order they arrive. The job runs through tools/nodejob.sh exactly as on a node:
# on the branch you are on, as GitHub has it, and what it wrote under renders/ comes back on
# that branch. Nothing goes through the bridge: the request and the receipt are two small files
# on the branch cursor/c164-jobs-a9f5.
#
#   bash tools/a0job.sh <the nodejob.sh options and your command>
#
#   bash tools/a0job.sh python tools/selfshots.py obs_main_tower
#   bash tools/a0job.sh --wip python tools/selfshots.py <scene> --only a,b --out renders/_wip
#   bash tools/a0job.sh --no-push python tools/check.py --scene <scene>
#
# Your branch does not have this file yet? Take it from the assembly each time:
#   git fetch -q origin cursor/c164-assembly-fable-a9f5 && git show FETCH_HEAD:c164-realms/tools/a0job.sh >/tmp/a0job.sh
#   bash /tmp/a0job.sh <the nodejob.sh options and your command>      (from inside your working tree)
#
# Options of this script, before everything else:
#   --wait <sec>     how long to stay and wait for the receipt (default 1500; 0: send and leave)
#   --receipt <id>   print the receipt of a job sent earlier, if it has come (exit 75: not yet)
#   --queue          the jobs that are waiting, the first of them running
#
# Short jobs go first: a gate (gate.sh, gatestack.sh, checkall.py) lets the looks waiting behind
# it pass until it has waited ten minutes itself.
# Push first: the machine sees GitHub, not your disk. A job gets 15 minutes there unless it says
# `--limit <seconds>` (a nodejob.sh option), and 30 minutes at the very most: split what is longer.
# The real game is not on that machine: real pictures stay with the picture-key holder.
# The exit status is the job's own (the `exit=` of the receipt); then `git pull`.
set -uo pipefail

Q="cursor/c164-jobs-a9f5"
usage() { sed -n '2,31p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

wait_s=1500 mode="send" want=""
while [ $# -gt 0 ]; do
  case "$1" in
    --wait) wait_s="${2:?--wait needs a number of seconds}"; shift 2 ;;
    --receipt) mode="receipt"; want="${2:?--receipt needs the id of a job}"; shift 2 ;;
    --queue) mode="queue"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) break ;;
  esac
done
case "$wait_s" in ''|*[!0-9]*) echo "a0job: --wait takes a whole number of seconds, not '$wait_s'" >&2; exit 2 ;; esac

repo="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "a0job: run it inside your working tree" >&2; exit 2; }
export GIT_TERMINAL_PROMPT=0
if [ -z "$(git -C "$repo" config user.name)" ]; then
  export GIT_AUTHOR_NAME="c164" GIT_AUTHOR_EMAIL="c164@users.noreply.github.com"
  export GIT_COMMITTER_NAME="c164" GIT_COMMITTER_EMAIL="c164@users.noreply.github.com"
fi

# tip: the queue branch as GitHub has it now (a commit id), or nothing when GitHub did not answer
tip() {
  timeout -k 5 60 git -C "$repo" fetch -q origin "$Q" >/dev/null 2>&1 || return 1
  git -C "$repo" rev-parse -q --verify FETCH_HEAD
}
# waiting <commit>: the ids of the jobs that have no receipt yet, oldest first
waiting() {
  local have
  have="$(git -C "$repo" ls-tree --name-only "$1:receipts" 2>/dev/null | sed 's/\.txt$//')"
  git -C "$repo" ls-tree --name-only "$1:queue" 2>/dev/null | sed 's/\.job$//' | sort \
    | { if [ -n "$have" ]; then grep -vxF -f <(printf '%s\n' "$have"); else cat; fi; }
}
# receipt <commit> <id>: print it and return the job's exit status; 75 when it has not come
receipt() {
  local text code
  text="$(git -C "$repo" show "$1:receipts/$2.txt" 2>/dev/null)" || return 75
  printf '%s\n' "$text"
  code="$(printf '%s\n' "$text" | sed -n 's/^a0job: exit=\([0-9][0-9]*\).*/\1/p' | tail -n 1)"
  return "${code:-1}"
}

if [ "$mode" = "queue" ]; then
  t="$(tip)" || { echo "a0job: GitHub did not answer" >&2; exit 1; }
  n=0
  for id in $(waiting "$t"); do n=$((n + 1)); echo "$n. $id"; done
  echo "$n waiting (the first is running or about to)"
  exit 0
fi
if [ "$mode" = "receipt" ]; then
  t="$(tip)" || { echo "a0job: GitHub did not answer" >&2; exit 1; }
  receipt "$t" "$want"; code=$?
  if [ "$code" = 75 ]; then echo "a0job: no receipt for $want yet"; fi
  exit "$code"
fi

if [ $# -eq 0 ]; then usage >&2; exit 2; fi
branch="$(git -C "$repo" rev-parse --abbrev-ref HEAD)"
case "$branch" in
  HEAD) echo "a0job: the tree is on no branch" >&2; exit 2 ;;
  cursor/c164-assembly-*|cursor/c164-realms-map-*|main|master|"$Q")
    echo "a0job: jobs run on your own branch, not on $branch" >&2; exit 2 ;;
  cursor/c164-*) ;;
  *) echo "a0job: $branch is not a c164 branch" >&2; exit 2 ;;
esac
head="$(git -C "$repo" rev-parse HEAD)"
there="$(timeout -k 5 60 git -C "$repo" ls-remote origin "refs/heads/$branch" 2>/dev/null | cut -f1)"
if [ "$there" != "$head" ]; then
  echo "a0job: GitHub has ${there:-nothing} on $branch and you are on $head: push first" >&2; exit 2
fi

who="${branch#cursor/c164-}"
id="$(date -u +%m%d-%H%M%S)-$(printf '%s' "$who" | tr -c 'A-Za-z0-9._-' '_' | cut -c1-40)-$RANDOM"
tmp="$(mktemp -d /tmp/c164_a0job.XXXXXX)"
trap 'rm -rf "$tmp"' EXIT
{
  echo "branch=$branch"
  echo "head=$head"
  printf 'args='; printf '%q ' "$@"; echo
} >"$tmp/job"

sent=0
for attempt in 1 2 3 4 5 6; do
  if t="$(tip)"; then
    blob="$(git -C "$repo" hash-object -w "$tmp/job")"
    tree="$(export GIT_INDEX_FILE="$tmp/index"; git -C "$repo" read-tree "$t" \
      && git -C "$repo" update-index --add --cacheinfo "100644,$blob,queue/$id.job" && git -C "$repo" write-tree)"
    commit="$(git -C "$repo" commit-tree "$tree" -p "$t" -m "job $id")"
    if [ -n "$commit" ] && timeout -k 5 90 git -C "$repo" push -q origin "$commit:refs/heads/$Q" >/dev/null 2>&1; then
      sent=1; break
    fi
  fi
  sleep $((attempt * 2))
done
if [ "$sent" != 1 ]; then echo "a0job: the request could not be put on $Q" >&2; exit 1; fi
ahead="$(waiting "$commit" | grep -n -x -F "$id" | cut -d: -f1)"
echo "a0job: sent $id ($(( ${ahead:-1} - 1 )) ahead of it)"
if [ "$wait_s" = 0 ]; then echo "a0job: later: bash tools/a0job.sh --receipt $id"; exit 0; fi

# The machine this runs on is shared by every session: ask GitHub seldom. The first look comes
# when the jobs ahead may be through (half a minute each), then one every 20 s.
t0=$SECONDS
nap=$(( (${ahead:-1} - 1) * 30 ))
if [ "$nap" -lt 15 ]; then nap=15; fi
if [ "$nap" -gt 300 ]; then nap=300; fi
while [ $((SECONDS - t0)) -lt "$wait_s" ]; do
  sleep "$nap"; nap=20
  t="$(tip)" || continue
  receipt "$t" "$id"; code=$?
  if [ "$code" != 75 ]; then exit "$code"; fi
done
echo "a0job: no receipt after $wait_s s; later: bash tools/a0job.sh --receipt $id"
exit 75
