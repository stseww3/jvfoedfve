#!/usr/bin/env bash
# The other end of tools/a0job.sh: the director's machine takes the jobs waiting on the branch
# cursor/c164-jobs-a9f5, oldest first, runs each through the tools/nodejob.sh of the branch it
# names, and puts the receipt on the same branch. Only the director starts this, on his own
# machine, in a tmux session:
#
#   bash tools/a0worker.sh            run until the file <state>/stop appears
#
# The job folder is /tmp/dais_jobs/c164a0, so nodejob.sh treats it as a node's: it takes the
# branch as GitHub has it and throws local state away. State and the log are in /tmp/c164_a0/worker.
#
# Several of these may run side by side on the machine (11-16 12:15: the whole team's short checks
# come here), each with a job folder and a state folder of its own:
#
#   C164_WORKER_JOB=/tmp/dais_jobs/c164a0b C164_WORKER_STATE=/tmp/c164_a0/worker-b \
#     C164_WORKER_LOG=/tmp/c164_a0/worker/log C164_WORKER_TAG=b bash tools/a0worker.sh
#
# A job belongs to the worker whose mkdir made its claim in /tmp/c164_a0/claims; a long job (a gate,
# every scene) takes every core, so only one of those runs at a time and the short ones go to the
# other workers meanwhile.
set -uo pipefail

Q="cursor/c164-jobs-a9f5"
SRC="${C164_SRC:-/agent/repos/c164-fable}"       # a working tree of the repository: the remote's address is read here
JOB="${C164_WORKER_JOB:-/tmp/dais_jobs/c164a0}"
STATE="${C164_WORKER_STATE:-/tmp/c164_a0/worker}"
ROOT="${MC_ROOT:-/agent/realms-study}"
CLAIMS="${C164_WORKER_CLAIMS:-/tmp/c164_a0/claims}"
TAG="${C164_WORKER_TAG:-a}"
LIMIT=900       # a job's time here, unless it says --limit
HARD=1800       # nothing runs longer than this here
export GIT_TERMINAL_PROMPT=0

mkdir -p "$STATE/done" "$CLAIMS" /tmp/dais_jobs
LOGFILE="${C164_WORKER_LOG:-$STATE/log}"
log() { echo "$(TZ=Asia/Shanghai date '+%m-%d %H:%M:%S') [$TAG] $*" >>"$LOGFILE"; }
g() { git -C "$JOB" "$@"; }

# The remote's address is kept without an access token. Git's own configuration on this machine
# puts the current token in at each use; a token copied into the job folder goes stale within the
# hour, and then every push from the folder is refused (11-16 06:33: four jobs' pictures lost).
plain="$(git -C "$SRC" config --get remote.origin.url | sed -E 's#//[^@/]*@#//#')"
if [ -z "$plain" ]; then echo "a0worker: $SRC has no remote" >&2; exit 1; fi
if [ ! -d "$JOB/.git" ]; then
  ref="$(git -C "$SRC" rev-parse --path-format=absolute --git-common-dir)" || exit 1
  git clone -q --no-checkout --reference "$ref" --dissociate "$plain" "$JOB" >/dev/null 2>&1 \
    || { echo "a0worker: the clone failed" >&2; exit 1; }
  g config user.name "c164-node"
  g config user.email "c164-node@users.noreply.github.com"
  log "cloned the job folder"
fi
g remote set-url origin "$plain"

# put <path> <file> <message>: one more file on the queue branch; never forced, tried again when
# the branch moved meanwhile
put() {
  local i base blob tree commit
  for i in 1 2 3 4 5 6 7 8; do
    if timeout -k 5 60 git -C "$JOB" fetch -q origin "$Q" >/dev/null 2>&1; then
      base="$(g rev-parse FETCH_HEAD)"
      blob="$(g hash-object -w "$2")"
      tree="$(export GIT_INDEX_FILE="$STATE/index"; g read-tree "$base" \
        && g update-index --add --cacheinfo "100644,$blob,$1" && g write-tree)"
      commit="$(g commit-tree "$tree" -p "$base" -m "$3")"
      if [ -n "$commit" ] && timeout -k 5 90 git -C "$JOB" push -q origin "$commit:refs/heads/$Q" >/dev/null 2>&1; then
        return 0
      fi
    fi
    sleep $((i * 2))
  done
  return 1
}

run_job() {
  local id="$1" tip="$2" req branch args want got="?" code=0 t0=$SECONDS
  local out="$STATE/out.txt" rec="$STATE/receipt.txt"
  req="$(g show "$tip:queue/$id.job" 2>/dev/null)"
  branch="$(sed -n 's/^branch=//p' <<<"$req" | head -n 1)"
  want="$(sed -n 's/^head=//p' <<<"$req" | head -n 1)"
  args="$(sed -n 's/^args=//p' <<<"$req" | head -n 1)"
  : >"$out"
  log "start $id ($branch): $(cut -c1-160 <<<"$args")"
  if ! [[ "$branch" =~ ^cursor/c164-[A-Za-z0-9._-]+$ ]] || [[ "$branch" == cursor/c164-assembly-* ]] \
     || [[ "$branch" == cursor/c164-realms-map-* ]] || [ "$branch" = "$Q" ]; then
    echo "a0worker: '$branch' is not a branch a job can run on" >"$out"; code=2
  elif [ -z "${args// /}" ]; then
    echo "a0worker: the request names no command" >"$out"; code=2
  elif ! timeout -k 10 300 git -C "$JOB" fetch -q origin "$branch" >/dev/null 2>&1; then
    echo "a0worker: GitHub has no branch $branch, or did not answer (push it, then send the job again)" >"$out"; code=2
  else
    g merge --abort >/dev/null 2>&1
    g checkout -q -f -B "$branch" FETCH_HEAD >/dev/null 2>&1
    g clean -q -fdx -- c164-realms >/dev/null 2>&1
    got="$(g rev-parse --short=8 HEAD)"
    if [ ! -f "$JOB/c164-realms/tools/nodejob.sh" ]; then
      echo "a0worker: $branch has no c164-realms/tools/nodejob.sh" >"$out"; code=2
    else
      (
        echo 1000 >"/proc/$BASHPID/oom_score_adj" 2>/dev/null
        cd "$JOB" || exit 2
        eval "set -- $args"
        export MC_ROOT="$ROOT" C164_JOB_LIMIT="$LIMIT"
        exec nice -n 5 timeout -k 20 "$HARD" bash c164-realms/tools/nodejob.sh "$@"
      ) >"$out" 2>&1 </dev/null || code=$?
    fi
  fi
  {
    echo "a0job $id: $branch @ $got on the director's machine"
    if [ -n "$want" ] && [ "$got" != "?" ] && [ "${want:0:8}" != "$got" ]; then
      echo "(the branch moved after the job was sent: it ran on $got, not on ${want:0:8})"
    fi
    tail -n 60 "$out" | cut -c1-240
    if [ "$code" = 124 ] && ! grep -q '^==== NODEJOB RESULT ====' "$out"; then
      echo "(stopped by the director's machine: nothing runs longer than $HARD s there)"
    fi
    echo "a0job: exit=$code secs=$((SECONDS - t0))"
  } >"$rec"
  if put "receipts/$id.txt" "$rec" "receipt $id: exit $code"; then
    log "done  $id: exit $code, $((SECONDS - t0)) s"
  else
    log "done  $id: exit $code, $((SECONDS - t0)) s; THE RECEIPT COULD NOT BE PUSHED"
    cp "$rec" "$STATE/unsent-$id.txt"
  fi
  : >"$STATE/done/$id"
}

# is_long <id> <tip>: the job is a gate, or checks every scene
is_long() { g show "$2:queue/$1.job" 2>/dev/null | grep -q -E '^args=.*(gate\.sh|gatestack\.sh|checkall\.py)'; }
# age <id>: the seconds since the job was sent, read off its id (MMDD-HHMMSS, UTC); a day when it cannot be read
age() {
  local then
  then="$(date -u -d "$(date -u +%Y)-${1:0:2}-${1:2:2} ${1:5:2}:${1:7:2}:${1:9:2}" +%s 2>/dev/null)" || { echo 86400; return; }
  echo $(( $(date -u +%s) - then ))
}

log "worker up (pid $$)"
while :; do
  if [ -e "$STATE/stop" ]; then log "stop file found: leaving"; exit 0; fi
  if ! timeout -k 5 60 git -C "$JOB" fetch -q origin "$Q" >/dev/null 2>&1; then sleep 10; continue; fi
  tip="$(g rev-parse -q --verify FETCH_HEAD)" || { sleep 10; continue; }
  have="$(g ls-tree --name-only "$tip:receipts" 2>/dev/null)"
  todo=()
  for f in $(g ls-tree --name-only "$tip:queue" 2>/dev/null | sort); do
    id="${f%.job}"
    if [ "$f" = "$id" ] || ! [[ "$id" =~ ^[A-Za-z0-9._-]+$ ]]; then continue; fi
    if [ -e "$STATE/done/$id" ]; then continue; fi
    if grep -qxF "$id.txt" <<<"$have"; then : >"$STATE/done/$id"; continue; fi
    if [ -d "$CLAIMS/$id" ]; then continue; fi
    todo+=("$id")
  done
  if [ ${#todo[@]} -eq 0 ]; then sleep 8; continue; fi
  long_free=1
  if [ -d "$CLAIMS/_long" ]; then
    holder="$(cat "$CLAIMS/_long/pid" 2>/dev/null)"
    if [ -n "$holder" ] && kill -0 "$holder" 2>/dev/null; then long_free=0; else rm -rf "$CLAIMS/_long"; fi
  fi
  next=""; next_long=0
  for id in "${todo[@]}"; do
    if is_long "$id" "$tip"; then
      if [ "$long_free" != 1 ]; then continue; fi
      if ! mkdir "$CLAIMS/_long" 2>/dev/null; then long_free=0; continue; fi
      echo $$ >"$CLAIMS/_long/pid"
      if mkdir "$CLAIMS/$id" 2>/dev/null; then next="$id"; next_long=1; break; fi
      rm -rf "$CLAIMS/_long"
    elif mkdir "$CLAIMS/$id" 2>/dev/null; then
      next="$id"; break
    fi
  done
  if [ -z "$next" ]; then sleep 5; continue; fi
  run_job "$next" "$tip"
  if [ "$next_long" = 1 ]; then rm -rf "$CLAIMS/_long"; fi
done
