#!/usr/bin/env bash
# Put s2's working notes on GitHub: the branch cursor/c164-s2-notes-89df holds nothing but the
# files named below, one commit a save, each on top of the last (never forced). Nothing is checked
# out: the commit is made from a temporary index. Run from anywhere.
#
#   bash /tmp/c164_s2/savenotes.sh "what changed"
set -uo pipefail
repo=/agent/repos/c164-s2-fable
branch=cursor/c164-s2-notes-89df
cd /tmp/c164_s2 || exit 1
files=(inbox.md status_edit*.py values*.py base_stack*.txt)
if grep -l -E 'a_[0-9a-f]{16}|X-Agent|https?://|ghp_|github_pat' "${files[@]}" 2>/dev/null | grep -q .; then
  echo "savenotes: something that must not be pushed is in the notes" >&2; exit 1
fi
tmp="$(mktemp -d /tmp/c164_s2_notes.XXXXXX)"
trap 'rm -rf "$tmp"' EXIT
export GIT_INDEX_FILE="$tmp/index"
parent=""
if git -C "$repo" fetch -q origin "$branch" 2>/dev/null; then parent="$(git -C "$repo" rev-parse -q --verify FETCH_HEAD)"; fi
for f in "${files[@]}" savenotes.sh; do
  [ -f "$f" ] || continue
  blob="$(git -C "$repo" hash-object -w "/tmp/c164_s2/$f")"
  git -C "$repo" update-index --add --cacheinfo "100644,$blob,notes/$f"
done
tree="$(git -C "$repo" write-tree)"
if [ -n "$parent" ] && [ "$(git -C "$repo" rev-parse "$parent^{tree}")" = "$tree" ]; then echo "savenotes: nothing new"; exit 0; fi
commit="$(git -C "$repo" commit-tree "$tree" ${parent:+-p "$parent"} -m "c164-s2: notes: ${1:-saved}")"
git -C "$repo" push -q origin "$commit:refs/heads/$branch" 2>&1 | sed -E 's#https?://[^ ]+#<remote>#g' | tail -2
echo "savenotes: ${commit:0:8} on $branch"
