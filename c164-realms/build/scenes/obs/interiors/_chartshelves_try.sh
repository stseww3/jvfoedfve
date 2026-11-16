#!/usr/bin/env bash
# The try branch's round on a worker node: the bookcase's elevation, the scene's check, the shots
# named in $1 (comma separated). Run from c164-realms/ by tools/nodejob.sh --wip.
set -uo pipefail
shots="${1:-v9,int_shelf,sh_east,sh_rake}"
(cd build && python -m scenes.obs.interiors._chartshelves_elev ../renders/_wip) || exit 1
python tools/check.py --scene obs_int_chartroom | grep -v "^\[PASS\]" | cut -c1-240
python tools/selfshots.py obs_int_chartroom --only "$shots" --out renders/_wip
