#!/usr/bin/env bash
# The approver's look at the assembly after a run of merges (the director's #87977: merged first,
# the gate made up afterwards on one's own node), in one job for the node. Sent on a branch that
# stands on the assembly's head:
#
#   bash c164-realms/tools/nodejob.sh --wip --always --tail 70 --limit 1700 \
#       'git fetch -q origin cursor/c164-cr3-f3-998d && git show FETCH_HEAD:c164-realms/plan/aesthetics/tools/cr3_gate.sh | bash -s -- [--no-check] <merge commit> ...'
#
# For every merge commit named (one of mine on the assembly's line: "c164-cr3: merge <category>/<package> ..."):
# tools/delivery.py on what it brought (the delivered commit is its second parent, the assembly as it
# was its first; delivery.py reads git and checks nothing out). Then tools/checkall.py on the head,
# unless --no-check. Everything goes to renders/_wip/gate/cr3/, which nodejob.sh --wip brings home;
# the closing lines are the summary. It always ends with 0: the summary says what is red.
set -uo pipefail

check=1
if [ "${1:-}" = "--no-check" ]; then check=0; shift; fi
py="$(command -v python || command -v python3)"
jdk="${MC_ROOT:-/agent/realms-study}/jdk/jdk-25.0.5+8/bin/javac"
if [ -z "${JAVAC:-}" ] && [ -x "$jdk" ]; then export JAVAC="$jdk"; fi
out="renders/_wip/gate/cr3"
rm -rf "$out"; mkdir -p "$out"
sum="$out/summary.txt"
say() { printf '%s\n' "$*" | tee -a "$sum"; }
say "cr3 gate: the head $(git rev-parse --short=8 HEAD), $(date -u +%H:%M:%S) UTC"

for merge in "$@"; do
  full="$(git rev-parse -q --verify "$merge^{commit}")" || { say "delivery: no commit $merge here"; continue; }
  card="$(git log -1 --format=%s "$full" | sed -n 's#^c164-cr3: merge \([a-z]*/[a-z0-9_-]*\) .*#\1#p')"
  brought="$(git rev-parse -q --verify "$full^2^{commit}")"
  if [ -z "$card" ] || [ -z "$brought" ]; then say "delivery: ${full:0:8} is not one of my merges"; continue; fi
  log="$out/delivery-${full:0:8}.txt"
  code=0
  "$py" tools/delivery.py "$card" "$brought" --base "$full^1" >"$log" 2>&1 || code=$?
  result="$(grep '^result: ' "$log" | tail -n 1 | cut -c9-)"
  say "delivery ${full:0:8} $card ${brought:0:8}: ${result:-ended with $code and no result}"
  awk '/^\[FAIL\]/ { on = 1; n = 0; print; next } /^[^ ]/ { on = 0 } on && n < 3 { n++; print }' "$log" \
    | cut -c1-200 | sed 's/^/    /' | tee -a "$sum"
done

if [ "$check" = 1 ]; then
  code=0
  "$py" tools/checkall.py --out "$out/check" >"$out/checkall.txt" 2>&1 || code=$?
  say "checkall (exit $code): $(tail -n 1 "$out/checkall.txt" | cut -c1-200)"
  awk '/^FAIL / { on = 1; n = 0; print; next } /^[^ ]/ { on = 0 } on && n < 6 { n++; print }' "$out/checkall.txt" \
    | cut -c1-200 | sed 's/^/    /' | tee -a "$sum"
fi
exit 0
