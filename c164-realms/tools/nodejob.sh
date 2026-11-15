#!/usr/bin/env bash
# Run one heavy c164 command on a worker node and bring what it wrote home through GitHub.
#
# The shared 4-core machine cannot carry forty people's pictures. Since 11-16 the admin's worker
# nodes take the heavy commands. You send a job with the bridge tool run_workspace_job; the node
# takes your branch from GitHub; this script makes the node ready (the same cloud_setup.sh you ran
# on your own machine), runs your command in c164-realms/, commits what it wrote under renders/
# and pushes that to your branch. The receipt arrives in your own read_chat; then `git pull`.
#
#   run_workspace_job(agent=<you>, node="node7", repo="stseww3/jvfoedfve", branch="<your branch>",
#       timeout_sec=1800,
#       command="bash c164-realms/tools/nodejob.sh python tools/selfshots.py obs_main_facade --only a,b,c,d")
#
# Options, before the command:
#   --keep <path>   commit this path afterwards (repeatable, from the repository root;
#                   default c164-realms/renders)
#   --to <branch>   push to this branch instead of the one the job runs on (made if it is new)
#   --always        commit and push even when the command fails (default: only when it exits 0)
#   --no-push       run only, commit nothing
#   --tail <n>      closing lines of the command's output to print (default 30)
#
# Push your own commits before you send the job: the node sees GitHub, not your disk. The command
# runs under `bash -c` in c164-realms/ with the node's venv first on PATH, so write it as you would
# type it there:  python tools/check.py --scene obs   or   cd build && python render.py obs ...
#
# A node keeps its disk between jobs, so the venv, the client jar and the compiled renderer are
# made once per node. A node runs one job at a time. Nothing is ever pushed to the assembly branch
# or to main from here: pictures reach the assembly through the merge-key holder.
set -uo pipefail

ASSEMBLY="cursor/c164-realms-map-b59c"

usage() { sed -n '2,27p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

keep=() to="" push=1 always=0 tail_n=30
while [ $# -gt 0 ]; do
  case "$1" in
    --keep) keep+=("${2:?--keep needs a path}"); shift 2 ;;
    --to) to="${2:?--to needs a branch}"; shift 2 ;;
    --always) always=1; shift ;;
    --no-push) push=0; shift ;;
    --tail) tail_n="${2:?--tail needs a number}"; shift 2 ;;
    --) shift; break ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "nodejob: unknown option $1" >&2; exit 2 ;;
    *) break ;;
  esac
done
if [ $# -eq 0 ]; then usage >&2; exit 2; fi
if [ ${#keep[@]} -eq 0 ]; then keep=("c164-realms/renders"); fi

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
proj="$(dirname "$here")"
repo="$(git -C "$proj" rev-parse --show-toplevel 2>/dev/null)" || { echo "nodejob: not inside a git repository" >&2; exit 2; }
root="${MC_ROOT:-/agent/realms-study}"
branch="$(git -C "$repo" rev-parse --abbrev-ref HEAD)"
if [ -z "$to" ]; then to="$branch"; fi
if [ "$push" = 1 ] && [ "$to" = "HEAD" ]; then
  echo "nodejob: the tree is on no branch; say where to push with --to <branch>, or --no-push" >&2; exit 2
fi
note=""
case "$to" in
  main|master|"$ASSEMBLY")
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
    if [ "$branch" != "HEAD" ] && git -C "$repo" fetch -q origin "$branch" >/dev/null 2>&1; then
      git -C "$repo" reset -q --hard FETCH_HEAD >/dev/null 2>&1
      git -C "$repo" clean -q -fd -- c164-realms >/dev/null 2>&1
    fi ;;
  *) note="not a node's job folder: the tree was used as it stands" ;;
esac
head="$(git -C "$repo" rev-parse --short=8 HEAD)"

# 2. the machine
setup_log="$(mktemp /tmp/c164_nodejob_setup.XXXXXX)"
if ! C164_REPO="$repo" MC_ROOT="$root" bash "$here/cloud_setup.sh" --no-smoke >"$setup_log" 2>&1; then
  tail -n 25 "$setup_log"
  note="cloud_setup.sh failed; the command was not run"
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
(cd "$proj" && bash -c "$*") >"$out" 2>&1 || code=$?
echo "---- $* ---- exit $code, $((SECONDS - t0)) s, last $tail_n lines of $(wc -l <"$out"):"
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
      -m "Run by tools/nodejob.sh on a worker node from $head; exit $code, $((SECONDS - t0)) s, $files files." >/dev/null 2>&1
    commit="$(git -C "$repo" rev-parse --short=8 HEAD)"
    for attempt in 1 2 3 4; do
      if git -C "$repo" push -q origin "HEAD:refs/heads/$to" >/dev/null 2>&1; then pushed="yes"; break; fi
      # someone pushed to the branch meanwhile: take theirs in, never force
      if git -C "$repo" fetch -q origin "$to" >/dev/null 2>&1; then
        git -C "$repo" "${ident[@]}" merge -q --no-edit FETCH_HEAD >/dev/null 2>&1 \
          || { git -C "$repo" merge --abort >/dev/null 2>&1; note="${note:+$note; }the branch moved and does not merge cleanly"; break; }
        commit="$(git -C "$repo" rev-parse --short=8 HEAD)"
      fi
      sleep $((2 ** attempt))
    done
    if [ "$pushed" != "yes" ]; then note="${note:+$note; }the push did not go through; the commit is on the node only"; fi
  fi
elif [ "$push" = 1 ]; then
  note="${note:+$note; }the command failed, so nothing was committed (--always to push anyway)"
fi

result "$code"
exit "$code"
