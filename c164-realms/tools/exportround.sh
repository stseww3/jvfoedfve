#!/usr/bin/env bash
# The node's part of one round of the whole save (plan/packages/common/export.md): every variant
# of save A<n> made and verified, one after the other, in the job tools/exportnext.sh prints.
#
#   bash tools/exportround.sh <n> <commit of the assembly> [variant ...]      (in c164-realms/)
#
# Variants (default: main and plain, in this order, so the one for Realms is there first):
#   main    c164-A<n>.zip         without the look's registry files; the look is in the resource
#                                 pack as core shaders when the tree has them (the one for Realms)
#   plain   c164-A<n>-plain.zip   the same without the shaders: the game's own night sky. The
#                                 fallback when a client refuses the resource pack (the director's
#                                 #73709: a shader that does not compile takes the whole pack down)
#   noguide c164-A<n>-noguide.zip the same as main without the guide (the title on arrival, the
#                                 plaques, the star charts: plan/packages/motion/guide.md). On
#                                 request only: the card asks that such a save can be made
#   look    c164-A<n>-look.zip    with our biome and timeline: single player only, not for Realms.
#                                 Only where the tree's look is still the data pack's: once the
#                                 resource pack carries it (artkit.mood.Carried) export.py refuses.
#
# A variant that fails does not stop the others. The closing line names each with the exit codes
# of make and verify; the script ends with 1 when any of them is not 0.
set -uo pipefail

n="${1:?the number of the save}" at="${2:?the commit of the assembly}"; shift 2
[ $# -gt 0 ] || set -- main plain
bad=0 line=""
for v in "$@"; do
  case "$v" in
    main)  name="c164-A$n"       opts=() ;;
    plain) name="c164-A$n-plain" opts=(--shaders off) ;;
    noguide) name="c164-A$n-noguide" opts=(--no-guide) ;;
    look)  name="c164-A$n-look"  opts=(--look on) ;;
    *) echo "exportround: no variant $v (main, plain, noguide, look)" >&2; exit 2 ;;
  esac
  a=0 b=-
  python tools/export.py make --scene obs --name "$name" "${opts[@]}" --assembly "$at" --out "dist/A$n" || a=$?
  if [ "$a" = 0 ]; then
    b=0
    python tools/export.py verify "dist/A$n/$name.zip" || b=$?
  fi
  [ "$a" = 0 ] && [ "$b" = 0 ] || bad=1
  line="$line $v: make=$a verify=$b;"
done
echo "A$n of $at --$line"
exit "$bad"
