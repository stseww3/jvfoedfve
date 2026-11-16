#!/usr/bin/env bash
# The watch on the assembly's head (A0 #67664): what has come in since the head last looked at.
# Light: git only. Prints, for every commit on the line of first parents since then, who made it
# and, for a merge, what it brought in by area, with the paths outside the package's own category
# named; then the provenance of the new head. The head looked at is kept in head_seen.txt.
#
# Somebody who merges the assembly's head into his own line and pushes that (not the other way
# round) turns the stretch of the assembly he took in into the second parent of his merge. Such a
# merge ("merge the assembly ...") is opened: the commits on its second parent's line are listed as
# if they stood on the first-parent line, so that no delivery's merge is lost from the ledger.
#
#   bash /tmp/c164_s2/watch.sh          list what is new and remember the head
#   bash /tmp/c164_s2/watch.sh --peek   list only
set -uo pipefail
repo=/agent/repos/c164-s2-fable
state=/tmp/c164_s2/head_seen.txt
ledger=/tmp/c164_s2/ledger.tsv
peek=0; [ "${1:-}" = "--peek" ] && peek=1
cd "$repo" || exit 2
filt() { sed -E 's#https?://[^ ]+#<remote>#g'; }
git fetch -q origin cursor/c164-assembly-fable-a9f5 2>&1 | filt
head="$(git rev-parse FETCH_HEAD)"
seen="$(cat "$state" 2>/dev/null || echo "")"
if [ "$head" = "$seen" ]; then echo "head ${head:0:8}: nothing new"; exit 0; fi
if [ -z "$seen" ] || ! git merge-base --is-ancestor "$seen" "$head"; then
  echo "!! the head ${head:0:8} does not contain the head seen before (${seen:0:8}): the line was rewritten"
  exit 3
fi
echo "head ${seen:0:8} -> ${head:0:8}"

takes_in_the_assembly() {   # a merge whose subject says it merged the assembly into somebody's own line
  git log -1 --format='%s' "$1" | grep -q -i -E 'merge (the )?assembly|merge (remote-tracking )?branch .*c164-assembly-fable'
}

walk() {                    # the commits after $1 up to $2, oldest first, such merges opened
  local c parents
  for c in $(git rev-list --first-parent --reverse "$1..$2"); do
    parents=($(git rev-list --parents -n 1 "$c"))
    if [ "${#parents[@]}" -ge 3 ] && takes_in_the_assembly "$c"; then
      walk "${parents[1]}" "${parents[2]}"
    fi
    echo "$c"
  done
}

for c in $(walk "$seen" "$head"); do
  parents=($(git rev-list --parents -n 1 "$c")); n=$(( ${#parents[@]} - 1 ))
  echo "---- $(git log -1 --format='%h %ad %s' --date=format:'%H:%M' "$c" | filt | cut -c1-150)"
  if [ "$n" -ge 2 ] && takes_in_the_assembly "$c"; then
    echo "     took in the assembly's line up to ${parents[2]:0:8} (its commits are listed above); his own side is on the first-parent line"
  elif [ "$n" -ge 2 ]; then
    second="${parents[2]}"
    if [ "$peek" = 0 ]; then
      # the ledger STATUS is written from: time (UTC), who merged, what, the delivered commit, the merge
      git log -1 --format='%ad%x09%s' --date=format:'%m-%d %H:%M' "$c" | filt \
        | awk -F'\t' -v m="${c:0:8}" -v d="${second:0:8}" '{ who=$2; sub(/:.*/, "", who); what=$2; sub(/^[^:]*: */, "", what); sub(/ Co-authored-by.*/, "", what); print $1 "\t" who "\t" what "\t" d "\t" m }' >> "$ledger"
    fi
    echo "     merge of ${second:0:8} ($(git log -1 --format='%s' "$second" | filt | cut -c1-80))"
    git diff --name-only "$c^1" "$c" | sed 's#^c164-realms/##' | SUBJ="$(git log -1 --format='%s' "$c")" python3 -c '
import sys, collections, os, re
areas = collections.Counter(); odd = []
subject = os.environ.get("SUBJ", "")
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
# A merge its owner made himself (the director, 11-16 13:16: "(self)" in the subject) may touch his own
# package only: code of another category, a second module of his category, anything outside a package
# is for the approver.
if "(self)" in subject:
    m = re.search(r"merge ([a-z]+)/([\w\-]+)", subject)
    cat = m.group(1) if m else "?"
    code = sorted(k.split(" ", 1)[1] for k in areas if k.startswith("code "))
    cards = sorted(k.split(" ", 1)[1] for k in areas if k.startswith("card "))
    wrong = [c for c in code if not c.startswith(cat + "/")] + [c for c in cards if not c.startswith(cat + "/")]
    kit = [c for c in code if c.split("/", 1)[1].startswith("_kit")]
    notes = []
    if wrong:
        notes.append("another category: " + ", ".join(wrong))
    if kit:
        notes.append("a kit: " + ", ".join(kit))
    if odd:
        notes.append(str(len(odd)) + " paths outside a package")
    if len([c for c in code if c.startswith(cat + "/")]) > 1:
        notes.append("modules of " + cat + ": " + ", ".join(c for c in code if c.startswith(cat + "/")))
    print("     (self) " + (m.group(0)[6:] if m else "?") + (": !! NOT HIS ALONE -- " + "; ".join(notes) if (wrong or kit or odd) else
                                                         (": " + "; ".join(notes) + " (look)" if notes else ": his own package only")))
'
  else
    git diff --name-only "$c^1" "$c" | sed 's#^c164-realms/##' | head -8 | sed 's/^/     /'
  fi
done
bash c164-realms/tools/provenance.sh "$head" 2>&1 | tail -1 | sed 's/^/provenance: /'
[ "$peek" = 1 ] || echo "$head" > "$state"
