#!/usr/bin/env bash
# Redraws this scene's pictures and the text files kept beside them (check.txt, selfcheck.txt).
# Run from c164-realms/ on a worker node:
#     bash tools/nodejob.sh --limit 1200 --tail 30 'bash build/scenes/obs_mach_meridian_astrograph/redraw.sh'
# With "check" as its argument nothing is drawn: the scene is built and checked and the two text
# files are written, a matter of seconds.
# The exit code is check.py's; 1 when a self-check has findings or shots.json is not what the
# scene's numbers give.
set -u
scene=obs_mach_meridian_astrograph
out=renders/$scene
(cd build && python -m scenes.$scene) || exit 1
if ! git diff --quiet -- build/scenes/$scene/shots.json; then
    echo "shots.json is not what the scene writes:"
    git diff -- build/scenes/$scene/shots.json | head -n 40
    git checkout -- build/scenes/$scene/shots.json
    exit 1
fi
if [ "${1:-}" != "check" ]; then
    python tools/selfshots.py $scene || exit 1
fi
python tools/check.py --scene $scene > "$out/check.txt" 2>&1
status=$?
(
    cd build || exit 1
    python -m scenes.obs.machines.meridian
    a=$?
    python -m scenes.obs.machines.astro
    b=$?
    [ "$a" -eq 0 ] && [ "$b" -eq 0 ]
) > "$out/selfcheck.txt" 2>&1 || status=1
tail -n 14 "$out/check.txt"
grep -n "self-check\|railing\|line under\|guard" "$out/selfcheck.txt"
exit $status
