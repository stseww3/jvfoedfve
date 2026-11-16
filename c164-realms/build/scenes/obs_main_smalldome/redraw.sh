#!/usr/bin/env bash
# Redraws this scene's pictures and the text files kept beside them (check.txt, hidden.txt,
# roofcheck.txt, domecheck.txt). Run from c164-realms/ on a worker node:
#     bash tools/nodejob.sh --limit 1200 --tail 30 'bash build/scenes/obs_main_smalldome/redraw.sh'
# The exit code is check.py's.
set -u
out=renders/obs_main_smalldome
(cd build && python -m scenes.obs_main_smalldome) || exit 1
python tools/selfshots.py obs_main_smalldome || exit 1
python tools/check.py --scene obs_main_smalldome > "$out/check.txt" 2>&1
status=$?
(
    cd build || exit 1
    python -m scenes.obs_main_smalldome.hidden > "../$out/hidden.txt" 2>&1
    python -m scenes.obs.main.roof check > "../$out/roofcheck.txt" 2>&1
    python -m scenes.obs.main.smalldome check > "../$out/domecheck.txt" 2>&1
)
tail -n 14 "$out/check.txt"
tail -n 1 "$out/hidden.txt" "$out/roofcheck.txt" "$out/domecheck.txt"
exit $status
