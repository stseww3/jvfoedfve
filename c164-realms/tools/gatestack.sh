#!/usr/bin/env bash
# The merge gate for several deliveries merged one on top of the other, in one job for the node: each
# is held to tools/gate.sh on the tree it was merged into, not on the tree of those merged after it.
#
#   bash c164-realms/tools/nodejob.sh --wip --always --tail 120 \
#       bash tools/gatestack.sh [--until <commit>] <base> <category>/<package> <commit> [<category>/<package> <commit> ...]
#
# <base> is the assembly as it was before the first of them. HEAD holds them all, merged in the order
# given (git merge --no-ff <commit>), with whatever the merge-key holder committed after a merge on
# that delivery's account (a change to a public file the delivery asks for). The tree a delivery is
# held to is the last commit before the next delivery's merge, HEAD for the last one; the assembly
# as it was, for that delivery, is the tree of the one before it. So a delivery's kept pictures are
# compared with what its own merged tree draws: that a later delivery of the same job changes them
# is found by tools/keptshots.py afterwards, not held against it here.
#
# Two cards delivered in one commit: name the commit twice, once for each card. Both are held to the
# same tree; the pictures are drawn for the first only.
#
#   --until <commit>   before <base>: the last delivery is held to this commit of HEAD's line and not
#                      to HEAD, when the merge-key holder's own changes that come after it (a change
#                      to the renderer, say) are not on any delivery's account.
#
# Each delivery's report is tools/gate.sh's own, in renders/_wip/gate/<package>/. The closing lines
# name every delivery with PASS or FAIL; exit 0 when all of them may be merged.
set -uo pipefail

main() {
  local until=""
  if [ "${1:-}" = "--until" ]; then
    until="${2:-}"
    if [ -z "$until" ]; then echo "gatestack: --until needs a commit" >&2; return 2; fi
    shift 2
  fi
  if [ $# -lt 3 ] || [ $(( ($# - 1) % 2 )) != 0 ]; then
    sed -n '2,24p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//' >&2; return 2
  fi
  local here proj repo base head back
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  proj="$(dirname "$here")"
  repo="$(git -C "$proj" rev-parse --show-toplevel 2>/dev/null)" || { echo "gatestack: not inside a git repository" >&2; return 2; }
  base="$(git -C "$repo" rev-parse -q --verify "$1^{commit}")" || { echo "gatestack: no such base $1" >&2; return 2; }
  shift
  head="$(git -C "$repo" rev-parse HEAD)"
  back="$(git -C "$repo" symbolic-ref -q --short HEAD || echo "$head")"
  if [ -n "$(git -C "$repo" status --porcelain --untracked-files=no)" ]; then
    echo "gatestack: the tree has changes that are not committed; it is checked out commit by commit" >&2; return 2
  fi
  if [ -n "$until" ]; then
    local last on=0 one
    last="$(git -C "$repo" rev-parse -q --verify "$until^{commit}")" || { echo "gatestack: no such commit $until" >&2; return 2; }
    while read -r one; do [ "$one" = "$last" ] && on=1; done < <(git -C "$repo" rev-list --first-parent "$base..$head")
    if [ "$on" = 0 ]; then
      echo "gatestack: ${last:0:8} (--until) is not on the line of first parents from ${base:0:8} to HEAD" >&2; return 2
    fi
    head="$last"
  fi

  # the commits from the base to HEAD along the first parents, oldest first
  local chain=() line
  while read -r line; do chain+=("$line"); done < <(git -C "$repo" rev-list --first-parent --reverse "$base..$head")
  if [ ${#chain[@]} = 0 ] || [ "$(git -C "$repo" rev-parse "${chain[0]}^1")" != "$base" ]; then
    echo "gatestack: ${base:0:8} is not on the line of first parents of HEAD" >&2; return 2
  fi

  # each delivery: its card, its commit, where on that line it was merged
  local cards=() commits=() at=() full i j found
  while [ $# -gt 0 ]; do
    full="$(git -C "$repo" rev-parse -q --verify "$2^{commit}")" || { echo "gatestack: no commit $2 here" >&2; return 2; }
    found=-1
    for i in "${!chain[@]}"; do
      if [ "$(git -C "$repo" rev-parse -q --verify "${chain[$i]}^2^{commit}" 2>/dev/null)" = "$full" ]; then found=$i; break; fi
    done
    if [ "$found" -lt 0 ]; then
      echo "gatestack: ${full:0:8} ($1) was not merged between ${base:0:8} and HEAD (git merge --no-ff)" >&2; return 2
    fi
    if [ ${#at[@]} -gt 0 ] && [ "$found" -lt "${at[$(( ${#at[@]} - 1 ))]}" ]; then
      echo "gatestack: name the deliveries in the order they were merged; $1 was merged before ${cards[$(( ${#cards[@]} - 1 ))]}" >&2; return 2
    fi
    cards+=("$1"); commits+=("$full"); at+=("$found"); shift 2
  done

  # each delivery's tree (the last commit before the next other delivery's merge) and its base
  local n=${#cards[@]} trees=() bases=() next tree prev
  for i in "${!cards[@]}"; do
    next=-1
    for (( j = i + 1; j < n; j++ )); do
      if [ "${at[$j]}" != "${at[$i]}" ]; then next="${at[$j]}"; break; fi
    done
    if [ "$next" -lt 0 ]; then tree="$head"; else tree="${chain[$(( next - 1 ))]}"; fi
    if [ "${at[$i]}" = 0 ]; then prev="$base"; else prev="${chain[$(( ${at[$i]} - 1 ))]}"; fi
    trees+=("$tree"); bases+=("$prev")
  done

  local results=() bad=0 code more seen=" "
  for i in "${!cards[@]}"; do
    more=()
    case "$seen" in *" ${commits[$i]} "*) more=(--no-verify) ;; esac
    seen="$seen${commits[$i]} "
    echo "==== gatestack: ${cards[$i]} ${commits[$i]:0:8} on the tree ${trees[$i]:0:8}, the assembly as it was ${bases[$i]:0:8} ===="
    if ! git -C "$repo" checkout -q --detach "${trees[$i]}"; then
      echo "gatestack: could not check out ${trees[$i]:0:8}" >&2
      results+=("FAIL ${cards[$i]} ${commits[$i]:0:8}: its tree could not be checked out"); bad=1; continue
    fi
    code=0
    bash "$proj/tools/gate.sh" "${cards[$i]}" "${commits[$i]}" --base "${bases[$i]}" ${more[@]+"${more[@]}"} || code=$?
    if [ "$code" = 0 ]; then
      results+=("PASS ${cards[$i]} ${commits[$i]:0:8} on ${trees[$i]:0:8}")
    else
      results+=("FAIL ${cards[$i]} ${commits[$i]:0:8} on ${trees[$i]:0:8} (gate.sh ended with $code)"); bad=1
    fi
  done
  git -C "$repo" checkout -q "$back" || echo "gatestack: could not go back to $back" >&2

  echo "==== gatestack: ${#cards[@]} deliveries from ${base:0:8} to ${head:0:8} ===="
  printf '%s\n' "${results[@]}"
  echo "result: $([ "$bad" = 0 ] && echo PASS || echo FAIL)"
  return "$bad"
}

main "$@"; exit $?
