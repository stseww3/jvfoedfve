#!/usr/bin/env bash
# A trial of tools/guidetrip.py before a save with the guide is delivered. On the node: the tree
# of one commit of the assembly is put beside this one, tools/export.py of that tree makes a save
# of it (the main variant, the one for Realms), and guidetrip.py of this tree walks that save.
# The save stays on the node's disk and is thrown away; the pictures and the log are kept like
# those of any trip, and real.txt says they are a trial's.
#
#   bash tools/guidetry.sh <commit of the assembly> [options of guidetrip.py ...]      (in c164-realms/)
set -uo pipefail
at="${1:?the commit of the assembly}"; shift
assembly=cursor/c164-assembly-fable-a9f5
here="$(cd "$(dirname "$0")/.." && pwd)"
repo="$(git -C "$here" rev-parse --show-toplevel)"
side="${TMPDIR:-/tmp}/c164_s1_guidetry"
git -C "$repo" fetch -q origin "$assembly" || { echo "guidetry: the assembly could not be fetched" >&2; exit 3; }
full="$(git -C "$repo" rev-parse --verify -q "$at^{commit}")" || { echo "guidetry: no commit $at" >&2; exit 2; }
git -C "$repo" merge-base --is-ancestor "$full" FETCH_HEAD || { echo "guidetry: $at is not of the assembly" >&2; exit 2; }
git -C "$repo" worktree remove --force "$side" 2>/dev/null
rm -rf "$side"
git -C "$repo" worktree prune
git -C "$repo" worktree add -q --detach "$side" "$full" || { echo "guidetry: no tree of $at beside this one" >&2; exit 3; }
trap 'git -C "$repo" worktree remove --force "$side" 2>/dev/null; rm -rf "$side"; git -C "$repo" worktree prune' EXIT
( cd "$side/c164-realms" && python tools/export.py make --scene obs --name c164-T --assembly "$full" --out "$side/out" ) \
  || { echo "guidetry: tools/export.py of ${full:0:8} did not make the save" >&2; exit 4; }
cd "$here" && python tools/guidetrip.py --branch "$assembly" --at "$full" --file "$side/out/c164-T.zip" "$@"
