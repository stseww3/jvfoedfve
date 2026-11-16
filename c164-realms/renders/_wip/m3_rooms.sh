#!/bin/bash
# The route's own check, its station table on this tree, and the rooms' maps (run in c164-realms/).
set -u
C=/tmp/c164_walk/m3-canvas-$(git rev-parse --short=8 HEAD:c164-realms/build).pickle
O=renders/_wip/walkfix
mkdir -p $O /tmp/c164_walk
python tools/walk.py check plan/reviews/walk/in-route.json | tail -3 | tee $O/check.txt
python tools/walk.py stations plan/reviews/walk/in-route.json --canvas $C --out $O/stations.json > $O/stations-report.txt 2>&1
tail -14 $O/stations-report.txt | cut -c1-200
python renders/_wip/m3_rooms.py $C $O/stations.json | tail -45
