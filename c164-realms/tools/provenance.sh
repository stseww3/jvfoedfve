#!/usr/bin/env bash
# Is a commit free of the second shift's work?
#
# Three shifts have worked on this project. The second one (the night of 11-15 to 11-16, chats c258
# to c297) turned out to run on another model than the one the admin wants, and he ruled that nothing
# it made is accepted. Its commits stay on GitHub as an archive: the old assembly branch
# cursor/c164-realms-map-b59c and the tips of the old work branches. Nothing with one of those commits
# in its history may reach the assembly, so the merge-key holder runs this on every delivered commit
# before merging it, and cloud_setup.sh runs the same test on the commit a new branch is cut from.
#
#   tools/provenance.sh <commit> [<commit> ...]
#
# exit 0: every commit given is clean. exit 1: one is not; its newest offending ancestors are listed.
#
# A commit of the second shift is one that
#   - was committed between 2026-11-15 13:40 and 17:58 UTC. The first shift's last commit is from
#     13:36, the third shift's first from 17:59, and nothing of the first or third shift lies between
#     (the director's commits of those hours were made anew, later, on the new assembly); or
#   - is listed in plan/shift2-commits.txt: the second shift's commits made after 17:58, while its
#     agents were being stopped (they all sit on older commits of theirs, so the dates alone catch
#     them; the list is the second net).
#
# This tests ancestry, which is what a tool can test. Copying a file or a picture out of the archive
# by hand is forbidden all the same (plan/roles/HANDOVER.md, section 0).
set -uo pipefail

LO=1794750000   # 2026-11-15T13:40:00Z
HI=1794765480   # 2026-11-15T17:58:00Z

if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
  sed -n '2,24p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 2
fi

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(git -C "$here" rev-parse --show-toplevel 2>/dev/null)" || { echo "provenance: not inside a git repository" >&2; exit 2; }
deny="$(dirname "$here")/plan/shift2-commits.txt"

bad=0
for c in "$@"; do
  full="$(git -C "$repo" rev-parse -q --verify "$c^{commit}")" \
    || { echo "provenance: no commit $c here (fetch its branch first)" >&2; exit 2; }
  found="$(TZ=UTC git -C "$repo" log --date=format-local:'%m-%d %H:%M' --format='%ct%x09%H%x09%cd%x09%s' "$full" \
    | awk -F'\t' -v lo="$LO" -v hi="$HI" -v deny="$deny" '
        BEGIN { while ((getline line < deny) > 0) { split(line, w, " "); if (w[1] != "" && w[1] !~ /^#/) listed[w[1]] = 1 } }
        ($1 >= lo && $1 <= hi) || ($2 in listed) { n++; if (n <= 5) printf "    %s  %s UTC  %s\n", substr($2, 1, 8), $3, substr($4, 1, 80) }
        END { if (n) printf "%d\n", n }')"
  if [ -z "$found" ]; then
    echo "clean      ${full:0:8}  ($(git -C "$repo" rev-list --count "$full") commits in its history)"
  else
    bad=1
    echo "NOT CLEAN  ${full:0:8}  $(printf '%s\n' "$found" | tail -n 1) commits of the second shift in its history; the newest:"
    printf '%s\n' "$found" | sed '$d'
  fi
done
exit "$bad"
