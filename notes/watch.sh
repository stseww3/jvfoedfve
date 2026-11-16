#!/usr/bin/env bash
# The watch on the assembly's head (A0 #67664): what has come in since the head last looked at.
# Light: git only. Prints, for every commit on the line of first parents since then, who made it
# and, for a merge, what it brought in by area, with the paths outside the package's own category
# named; then the provenance of the new head. The head looked at is kept in head_seen.txt.
#
#   bash /tmp/c164_s2/watch.sh          list what is new and remember the head
#   bash /tmp/c164_s2/watch.sh --peek   list only
set -uo pipefail
repo=/agent/repos/c164-s2-fable
state=/tmp/c164_s2/head_seen.txt
peek=0; [ "${1:-}" = "--peek" ] && peek=1
cd "$repo" || exit 2
git fetch -q origin cursor/c164-assembly-fable-a9f5 2>&1 | sed -E 's#https?://[^ ]+#<remote>#g'
head="$(git rev-parse FETCH_HEAD)"
seen="$(cat "$state" 2>/dev/null || echo "")"
if [ "$head" = "$seen" ]; then echo "head ${head:0:8}: nothing new"; exit 0; fi
if [ -z "$seen" ] || ! git merge-base --is-ancestor "$seen" "$head"; then
  echo "!! the head ${head:0:8} does not contain the head seen before (${seen:0:8}): the line was rewritten"
  exit 3
fi
echo "head ${seen:0:8} -> ${head:0:8}"
for c in $(git rev-list --first-parent --reverse "$seen..$head"); do
  parents=($(git rev-list --parents -n 1 "$c")); n=$(( ${#parents[@]} - 1 ))
  echo "---- $(git log -1 --format='%h %ad %s' --date=format:'%H:%M' "$c" | sed -E 's#https?://[^ ]+#<remote>#g' | cut -c1-150)"
  if [ "$n" -ge 2 ]; then
    second="${parents[2]}"
    if [ "$peek" = 0 ]; then
      # the ledger STATUS is written from: time (UTC), who merged, what, the delivered commit, the merge
      git log -1 --format='%ad%x09%s' --date=format:'%m-%d %H:%M' "$c" | sed -E 's#https?://[^ ]+#<remote>#g' \
        | awk -F'\t' -v m="${c:0:8}" -v d="${second:0:8}" '{ who=$2; sub(/:.*/, "", who); what=$2; sub(/^[^:]*: */, "", what); sub(/ Co-authored-by.*/, "", what); print $1 "\t" who "\t" what "\t" d "\t" m }' >> /tmp/c164_s2/ledger.tsv
    fi
    echo "     merge of ${second:0:8} ($(git log -1 --format='%s' "$second" | sed -E 's#https?://[^ ]+#<remote>#g' | cut -c1-80))"
    git diff --name-only "$c^1" "$c" | sed 's#^c164-realms/##' | python3 -c '
import sys, collections
areas = collections.Counter(); odd = []
for p in sys.stdin.read().split("\n"):
    if not p: continue
    s = p.split("/")
    if p.startswith("build/scenes/obs/") and len(s) >= 5 and s[3] != "common":
        areas["code " + s[3] + "/" + s[4].replace(".py", "")] += 1
    elif p.startswith("build/scenes/obs_"):
        areas["scene " + s[2]] += 1
    elif p.startswith("renders/"):
        areas["pictures " + s[1]] += 1
    elif p.startswith("plan/packages/"):
        areas["card " + "/".join(s[2:])] += 1
    elif p.startswith("plan/aesthetics/"):
        areas["review " + s[2]] += 1
    else:
        odd.append(p)
print("     " + "; ".join(f"{k} x{v}" for k, v in sorted(areas.items())))
if odd:
    print("     !! outside a package: " + ", ".join(odd[:14]) + (" ..." if len(odd) > 14 else ""))
'
  else
    git diff --name-only "$c^1" "$c" | sed 's#^c164-realms/##' | head -8 | sed 's/^/     /'
  fi
done
bash c164-realms/tools/provenance.sh "$head" 2>&1 | tail -1 | sed 's/^/provenance: /'
[ "$peek" = 1 ] || echo "$head" > "$state"
