#!/usr/bin/env bash
# Run one heavy c164 command on a worker node and bring what it wrote home through GitHub.
#
# The shared 4-core machine cannot carry forty people's pictures. Since 11-16 the admin's worker
# nodes take the heavy commands. You send a job with the bridge tool run_workspace_job; the node
# takes your branch from GitHub; this script makes the node ready (the same cloud_setup.sh you ran
# on your own machine), runs your command in c164-realms/, commits what it wrote under renders/
# and pushes that to your branch. The receipt arrives in your own read_chat; then `git pull`.
#
#   run_workspace_job(agent=<you>, node="<your node>", repo="stseww3/jvfoedfve", branch="<your branch>",
#       timeout_sec=1800,
#       command="bash c164-realms/tools/nodejob.sh python tools/selfshots.py obs_main_facade")
#
# Options, before the command:
#   --wip           pictures for a look, not for keeping: commit c164-realms/renders/_wip only and
#                   push it to the scratch branch <your branch>-wip, which is never merged anywhere.
#                   Draw into that folder:  --wip python tools/selfshots.py <scene> --only a,b --out renders/_wip
#   --keep <path>   commit this path afterwards (repeatable, from the repository root;
#                   default c164-realms/renders)
#   --to <branch>   push to this branch instead of the one the job runs on (made if it is new)
#   --always        commit and push even when the command fails (default: only when it exits 0)
#   --no-push       run only, commit nothing
#   --tail <n>      closing lines of the command's output to print (default 30)
#   --limit <sec>   the job's time, all of it: set-up, the command and the push home (default 1700,
#                   or $C164_JOB_LIMIT). When it runs out, the command and everything it started
#                   are stopped and the receipt still comes (exit=124). A longer job says so:
#                   --limit 3500 with timeout_sec=3600. Keep it 100 s under the timeout_sec you send.
#
# Push your own commits before you send the job: the node sees GitHub, not your disk. The command
# runs under `bash -c` in c164-realms/ with the node's venv first on PATH, so write it as you would
# type it there:  python tools/check.py --scene obs   or   cd build && python render.py obs ...
#
# A node keeps its disk between jobs, so the venv, the client jar and the compiled renderer are
# made once per node. A node runs one job at a time. Nothing is ever pushed to an assembly branch
# or to main from here: pictures reach the assembly through the merge-key holder.
#
# Nothing in here waits for ever. On 11-16 eight nodes went silent within ten minutes, each on a
# job that never came back, with the machine idle; a node that never answers is lost to everyone.
# So the whole job has a time (--limit), every step runs inside it under a watch, a fetch or a
# push gets three minutes at most, nothing waits for the keyboard, and the receipt says what was
# stopped.
set -uo pipefail

ASSEMBLY="cursor/c164-assembly-fable-a9f5"
OLD_ASSEMBLY="cursor/c164-realms-map-b59c"   # frozen on 11-16: the archive of the shift whose work was not accepted

usage() { sed -n '2,35p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

# kin <pid>: every process below this one, parents before their children.
kin() {
  local p
  for p in $(ps -o pid= --ppid "$1" 2>/dev/null || cat "/proc/$1/task/"*/children 2>/dev/null); do
    echo "$p"; kin "$p"
  done
}
# run <seconds> <command...>: the command with a watch beside it, both in this script's own process
# group, so whoever stops the job by its group still stops everything. At the limit the watch
# stops the command and everything it started (the list is taken before the first signal, while
# the family tree is still whole; TERM, then KILL 15 s later). The command reads from /dev/null.
# Returns the command's status; HIT_LIMIT is 1 when the watch stopped it (the status is then 124).
HIT_LIMIT=0
run() {
  local limit="$1"; shift
  local mark code=0 t0=$SECONDS cmd watch
  mark="/tmp/c164_nodejob_mark.$$.$RANDOM"
  HIT_LIMIT=0
  "$@" </dev/null &
  cmd=$!
  (
    until [ $((SECONDS - t0)) -ge "$limit" ]; do
      kill -0 "$cmd" 2>/dev/null || exit 0
      sleep 2
    done
    kill -0 "$cmd" 2>/dev/null || exit 0
    : >"$mark"
    family="$cmd $(kin "$cmd" | tr '\n' ' ')"
    kill -TERM $family 2>/dev/null
    for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
      kill -0 $family 2>/dev/null || exit 0
      sleep 1
    done
    kill -KILL $family 2>/dev/null
  ) >/dev/null 2>&1 &
  watch=$!
  { wait "$cmd"; } 2>/dev/null || code=$?
  kill "$watch" 2>/dev/null
  { wait "$watch"; } 2>/dev/null
  if [ -e "$mark" ]; then rm -f "$mark"; HIT_LIMIT=1; return 124; fi
  return "$code"
}
# within <seconds> [<held back>]: <seconds>, or what is left of the job's time less what is held
# back for the steps still to come, whichever is smaller; never less than 1.
within() {
  local s="$1" l=$((limit - SECONDS - ${2:-0}))
  if [ "$l" -lt "$s" ]; then s="$l"; fi
  if [ "$s" -lt 1 ]; then s=1; fi
  echo "$s"
}
GIT_LIMIT=180       # one fetch or one push
SETUP_LIMIT=1200    # cloud_setup.sh: a new node downloads the client and builds the venv once
PUSH_HOLD=90        # kept back from the command's time for the commit and the push home (a quarter of the job's time at most)
export GIT_TERMINAL_PROMPT=0   # git asks nobody for a password: it fails instead

keep=() to="" push=1 always=0 tail_n=30 wip=0 limit="${C164_JOB_LIMIT:-1700}"
while [ $# -gt 0 ]; do
  case "$1" in
    --wip) wip=1; shift ;;
    --keep) keep+=("${2:?--keep needs a path}"); shift 2 ;;
    --to) to="${2:?--to needs a branch}"; shift 2 ;;
    --always) always=1; shift ;;
    --no-push) push=0; shift ;;
    --tail) tail_n="${2:?--tail needs a number}"; shift 2 ;;
    --limit) limit="${2:?--limit needs a number of seconds}"; shift 2 ;;
    --) shift; break ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "nodejob: unknown option $1" >&2; exit 2 ;;
    *) break ;;
  esac
done
if [ $# -eq 0 ]; then usage >&2; exit 2; fi
case "$limit" in
  ''|*[!0-9]*|0*) echo "nodejob: the time limit is a whole number of seconds, not '$limit'" >&2; exit 2 ;;
esac
if [ "$wip" = 1 ] && [ ${#keep[@]} -eq 0 ]; then keep=("c164-realms/renders/_wip"); fi
if [ ${#keep[@]} -eq 0 ]; then keep=("c164-realms/renders"); fi

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
proj="$(dirname "$here")"
repo="$(git -C "$proj" rev-parse --show-toplevel 2>/dev/null)" || { echo "nodejob: not inside a git repository" >&2; exit 2; }
root="${MC_ROOT:-/agent/realms-study}"
branch="$(git -C "$repo" rev-parse --abbrev-ref HEAD)"
if [ "$wip" = 1 ] && [ -z "$to" ] && [ "$branch" != "HEAD" ]; then to="$branch-wip"; fi
if [ -z "$to" ]; then to="$branch"; fi
if [ "$push" = 1 ] && [ "$to" = "HEAD" ]; then
  echo "nodejob: the tree is on no branch; say where to push with --to <branch>, or --no-push" >&2; exit 2
fi
note=""
case "$to" in
  main|master|"$ASSEMBLY"|"$OLD_ASSEMBLY")
    if [ "$push" = 1 ]; then push=0; note="nothing is pushed to $to from a node"; fi ;;
esac

result() {   # the last lines of the receipt: one line a reader, or a script, can pick the facts from
  echo "==== NODEJOB RESULT ===="
  echo "exit=$1 secs=$SECONDS host=$(hostname) cores=$(nproc) head=${head:-?} commit=${commit:-none} pushed=${pushed:-no} branch=$to files=${files:-0}${note:+ note=\"$note\"}"
}

# 1. the tree as GitHub has it. A node only checks the branch out, it does not move it forward, and
#    a job that died may have left files behind. This throws local state away, so it is done only
#    in a node's job folder: run by hand in your own working tree, the tree is left exactly as it is.
head="?" commit="none" pushed="no" files=0
case "$repo" in
  /tmp/dais_jobs/*)
    if [ "$branch" != "HEAD" ]; then
      if run "$(within "$GIT_LIMIT")" git -C "$repo" fetch -q origin "$branch" >/dev/null 2>&1; then
        git -C "$repo" reset -q --hard FETCH_HEAD >/dev/null 2>&1
        git -C "$repo" clean -q -fd -- c164-realms >/dev/null 2>&1
      else
        note="the fetch of $branch did not go through: the tree is as the node had it"
      fi
    fi ;;
  *) note="not a node's job folder: the tree was used as it stands" ;;
esac
head="$(git -C "$repo" rev-parse --short=8 HEAD)"

# 2. the machine
setup_log="$(mktemp /tmp/c164_nodejob_setup.XXXXXX)"
rc=0 s0=$SECONDS
run "$(within "$SETUP_LIMIT")" env C164_REPO="$repo" MC_ROOT="$root" bash "$here/cloud_setup.sh" --no-smoke >"$setup_log" 2>&1 || rc=$?
if [ "$rc" != 0 ]; then
  tail -n 25 "$setup_log" | cut -c1-240
  why="cloud_setup.sh failed"
  if [ "$HIT_LIMIT" = 1 ]; then why="cloud_setup.sh was stopped after $((SECONDS - s0)) s (it gets $SETUP_LIMIT s at most, inside the job's $limit s)"; fi
  note="${note:+$note; }$why; the command was not run"
  result 3; exit 3
fi
grep -E 'machine:|python: [0-9]|ready' "$setup_log" | sed 's/^/  /'

# 3. the command
export PATH="$root/.venv/bin:$PATH" MC_ROOT="$root" PYTHONUNBUFFERED=1
export NUMBA_CACHE_DIR="${NUMBA_CACHE_DIR:-$root/numba-cache}"
mkdir -p "$NUMBA_CACHE_DIR" 2>/dev/null || true
out="$(mktemp /tmp/c164_nodejob_out.XXXXXX)"
code=0
t0=$SECONDS
hold=5
if [ "$push" = 1 ]; then hold=$PUSH_HOLD; fi
if [ "$hold" -gt $((limit / 4)) ]; then hold=$((limit / 4)); fi
in_proj() { cd "$proj" && exec bash -c "$*"; }
run "$(within "$limit" "$hold")" in_proj "$@" >"$out" 2>&1 || code=$?
took=$((SECONDS - t0))
if [ "$HIT_LIMIT" = 1 ]; then
  note="${note:+$note; }the command was stopped after $took s: the job's time is $limit s (--limit <seconds> gives it longer)"
fi
echo "---- $* ---- exit $code, $took s, last $tail_n lines of $(wc -l <"$out"):"
tail -n "$tail_n" "$out" | cut -c1-240

# 4. home through GitHub
if [ "$push" = 1 ] && { [ "$code" = 0 ] || [ "$always" = 1 ]; }; then
  git -C "$repo" add -A -- "${keep[@]}" >/dev/null 2>&1
  if git -C "$repo" diff --cached --quiet; then
    note="${note:+$note; }the command changed nothing under ${keep[*]}"
  else
    files="$(git -C "$repo" diff --cached --name-only | wc -l)"
    ident=()
    if [ -z "$(git -C "$repo" config user.name)" ]; then
      ident=(-c user.name="c164-node" -c user.email="c164-node@users.noreply.github.com")
    fi
    git -C "$repo" "${ident[@]}" commit -q \
      -m "c164-node: $(printf '%s' "$*" | cut -c1-140)" \
      -m "Run by tools/nodejob.sh on a worker node from $head; exit $code, $took s, $files files." >/dev/null 2>&1
    commit="$(git -C "$repo" rev-parse --short=8 HEAD)"
    late=0
    for attempt in 1 2 3 4; do
      if [ $((limit - SECONDS)) -lt 3 ]; then late=1; break; fi
      if run "$(within "$GIT_LIMIT")" git -C "$repo" push -q origin "HEAD:refs/heads/$to" >/dev/null 2>&1; then pushed="yes"; break; fi
      # The branch moved meanwhile: take theirs in, never force. A scratch branch (--wip) holds the
      # last look only: what was there becomes history and this job's tree stands.
      how=()
      if [ "$wip" = 1 ]; then how=(-s ours); fi
      if run "$(within "$GIT_LIMIT")" git -C "$repo" fetch -q origin "$to" >/dev/null 2>&1; then
        git -C "$repo" "${ident[@]}" merge -q "${how[@]}" -m "c164-node: take in $to, which moved while the job ran" FETCH_HEAD >/dev/null 2>&1 \
          || { git -C "$repo" merge --abort >/dev/null 2>&1; note="${note:+$note; }the branch moved and does not merge cleanly"; break; }
        commit="$(git -C "$repo" rev-parse --short=8 HEAD)"
      fi
      if [ "$attempt" -lt 4 ]; then sleep "$(within $((2 ** attempt)))"; fi
    done
    if [ "$pushed" != "yes" ]; then
      why="the push did not go through"
      if [ "$late" = 1 ]; then why="the job's time ran out before the push went through"; fi
      note="${note:+$note; }$why; the commit is on the node only"
    fi
  fi
elif [ "$push" = 1 ]; then
  note="${note:+$note; }the command failed, so nothing was committed (--always to push anyway)"
fi

result "$code"
exit "$code"
