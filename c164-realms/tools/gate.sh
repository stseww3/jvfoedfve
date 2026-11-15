#!/usr/bin/env bash
# The merge gate for one delivery, in one command for the node (plan/roles/S2-integrator.md,
# plan/roles/INTERFACE.md section 6): everything the merge-key holder runs before a delivered commit
# reaches the assembly.
#
# The merge-key holder merges the delivered commit into his own branch, which stands on the
# assembly (git merge --no-ff <commit>), pushes that branch, not the assembly, and sends
#
#   bash c164-realms/tools/nodejob.sh --wip --always --tail 80 bash tools/gate.sh <category>/<package> <commit>
#
# HEAD has to be that merge: its first parent the assembly as it was, its second the delivered
# commit. On the merged tree the gate runs
#
#   1. tools/delivery.py <card> <commit> --base HEAD^1   what the delivery brings, read off git: shift
#                                                        (tools/provenance.sh: nothing of the second
#                                                        shift), scope, files, secrets, origin, commits,
#                                                        pictures, merge
#   2. tools/checkall.py                                 check.py on every scene, the master scene and
#                                                        the other packages' test scenes with it
#   3. tools/selfshots.py <scene> --verify               for every test scene the delivery touches that
#                                                        keeps pictures: are they what the merged code
#                                                        draws? A scene that fails is drawn again on the
#                                                        delivered commit itself, which tells a picture
#                                                        that never was what its code draws (the
#                                                        delivery goes back) from one that another
#                                                        package in the assembly changed (merged; the
#                                                        shots are named, to be drawn again)
#
# Options, after the commit:
#   --base <commit>   the assembly as it was, when HEAD is not the merge itself
#   --no-verify       leave step 3 out
#   --only-verify     step 3 alone
#
# The whole of what each step said goes to renders/_wip/gate/<package>/ (nodejob.sh --wip brings that
# home); the closing lines are the summary, also kept there as summary.txt. Exit 0: the delivery
# may be merged. Exit 1: it may not; what to send back is in the summary.
set -uo pipefail

usage() { sed -n '2,36p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }
if [ $# -lt 2 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then usage >&2; exit 2; fi
card="$1" commit="$2"; shift 2
base="" verify=1 others=1
while [ $# -gt 0 ]; do
  case "$1" in
    --base) base="${2:?--base needs a commit}"; shift 2 ;;
    --no-verify) verify=0; shift ;;
    --only-verify) others=0; shift ;;
    *) echo "gate: unknown option $1" >&2; exit 2 ;;
  esac
done

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
proj="$(dirname "$here")"
repo="$(git -C "$proj" rev-parse --show-toplevel 2>/dev/null)" || { echo "gate: not inside a git repository" >&2; exit 2; }
cat="${card%%/*}" pkg="${card#*/}"
case "$cat" in
  materials) abbr=mat ;; sky) abbr=sky ;; main) abbr=main ;; site) abbr=site ;; machines) abbr=mach ;;
  props) abbr=props ;; interiors) abbr=int ;; motion) abbr=mot ;; common) abbr=common ;;
  *) echo "gate: the card is <category>/<package>; no category $cat" >&2; exit 2 ;;
esac
if [ -z "$pkg" ] || [ "$pkg" = "$card" ]; then echo "gate: the card is <category>/<package>" >&2; exit 2; fi
full="$(git -C "$repo" rev-parse -q --verify "$commit^{commit}")" \
  || { echo "gate: no commit $commit here (is it in the history of the branch the job runs on?)" >&2; exit 2; }
if [ -z "$base" ]; then
  if [ "$(git -C "$repo" rev-parse -q --verify 'HEAD^2^{commit}' 2>/dev/null)" != "$full" ]; then
    echo "gate: HEAD is not the merge of ${full:0:8} (git merge --no-ff); say what the assembly was with --base" >&2; exit 2
  fi
  base="HEAD^1"
fi
base="$(git -C "$repo" rev-parse -q --verify "$base^{commit}")" || { echo "gate: no such base" >&2; exit 2; }
git -C "$repo" merge-base --is-ancestor "$full" HEAD \
  || { echo "gate: ${full:0:8} is not merged into HEAD; the gate looks at the merged tree" >&2; exit 2; }

py="$(command -v python || command -v python3)"
# The kept helper class (tools/win/helper) is what javac 25.0.5 builds; a node's own javac is 21 and
# lays the same bytes out otherwise. Where the node has the 25.0.5 one, delivery.py is given it.
jdk="${MC_ROOT:-/agent/realms-study}/jdk/jdk-25.0.5+8/bin/javac"
if [ -z "${JAVAC:-}" ] && [ -x "$jdk" ]; then export JAVAC="$jdk"; fi
out="$proj/renders/_wip/gate/$pkg"
rm -rf "$out"; mkdir -p "$out"
sum="$out/summary.txt"
bad=0
say() { printf '%s\n' "$*" >>"$sum"; }
say "gate $card ${full:0:8}: the merged tree $(git -C "$repo" rev-parse --short=8 HEAD), the assembly as it was ${base:0:8}"

if [ "$others" = 1 ]; then
  # 1. what the delivery brings
  code=0
  (cd "$proj" && "$py" tools/delivery.py "$card" "$full" --base "$base") >"$out/delivery.txt" 2>&1 || code=$?
  if grep -q '^result: ' "$out/delivery.txt"; then
    say "delivery.py: $(grep '^result: ' "$out/delivery.txt" | tail -n 1 | cut -c9-)"
    awk '/^\[(FAIL|WARN)\]/ { on = 1; n = 0; print; next } /^[^ ]/ { on = 0 } on && n < 6 { n++; print }' \
      "$out/delivery.txt" | cut -c1-230 | sed 's/^/    /' >>"$sum"
  else
    say "delivery.py: ended with $code and no result"
    tail -n 5 "$out/delivery.txt" | cut -c1-230 | sed 's/^/    /' >>"$sum"
  fi
  [ "$code" = 0 ] || bad=1

  # 2. what the merged tree generates
  code=0
  (cd "$proj" && "$py" tools/checkall.py --out "$out/check") >"$out/checkall.txt" 2>&1 || code=$?
  say "check.py: $(tail -n 1 "$out/checkall.txt" | cut -c1-230)"
  awk '/^FAIL / { on = 1; n = 0; print; next } /^[^ ]/ { on = 0 } on && n < 8 { n++; print }' \
    "$out/checkall.txt" | cut -c1-230 | sed 's/^/    /' >>"$sum"
  [ "$code" = 0 ] || bad=1
fi

# 3. the kept pictures of the scenes the delivery touches
if [ "$verify" = 1 ]; then
  module="${pkg//-/_}"
  scenes="$( { git -C "$repo" diff --name-only "$base" HEAD -- c164-realms/build/scenes c164-realms/renders \
                 | sed -n 's#^c164-realms/\(build/scenes\|renders\)/\(obs_[a-z]*_[^/]*\)/.*#\2#p'
               ls "$proj/build/scenes" | grep -E "^obs_${abbr}_${module}(_.*)?$"; } | sort -u )"
  drawn=0
  for scene in $scenes; do
    [ -f "$proj/build/scenes/$scene/shots.json" ] || continue
    if ! ls "$proj/renders/$scene"/*.png >/dev/null 2>&1; then
      say "pictures: $scene keeps none"
      continue
    fi
    drawn=1
    code=0
    (cd "$proj" && "$py" tools/selfshots.py "$scene" --verify) >"$out/verify-$scene.txt" 2>&1 || code=$?
    line="$(grep -E '^\[(PASS|WARN|FAIL)\] selfshots' "$out/verify-$scene.txt" | tail -n 1 | cut -c1-230)"
    if [ "$code" = 0 ]; then
      say "pictures: ${line:-$scene: verified}"
      grep -A8 -E '^\[WARN\] selfshots' "$out/verify-$scene.txt" | tail -n +2 | cut -c1-230 | sed 's/^ */    /' >>"$sum"
      continue
    fi
    # not what the merged code draws: was it ever what the delivered code draws?
    tree="$(mktemp -d /tmp/c164_gate.XXXXXX)"
    again=1
    if git -C "$repo" worktree add -q --detach "$tree/w" "$full" >/dev/null 2>&1; then
      again=0
      (cd "$proj" && "$py" tools/selfshots.py "$scene" --verify --project "$tree/w/c164-realms") \
        >"$out/verify-$scene-delivered.txt" 2>&1 || again=$?
      git -C "$repo" worktree remove --force "$tree/w" >/dev/null 2>&1
    fi
    rm -rf "$tree"
    if [ "$again" = 0 ]; then
      say "pictures: $scene: the kept pictures are what the delivered commit draws; in the merged tree they are out of date, to be drawn again:"
    else
      bad=1
      say "pictures: $scene: the kept pictures are NOT what the delivered commit ${full:0:8} draws (it goes back):"
    fi
    say "    ${line:-selfshots.py ended with $code and no result}"
    grep -A12 -E '^\[FAIL\] selfshots' "$out/verify-$scene.txt" | tail -n +2 | cut -c1-230 | sed 's/^ */    /' >>"$sum"
  done
  [ "$drawn" = 1 ] || say "pictures: nothing to verify (no test scene of the delivery keeps pictures)"
fi

say "result: $([ "$bad" = 0 ] && echo PASS || echo FAIL)"
cat "$sum"
exit "$bad"
