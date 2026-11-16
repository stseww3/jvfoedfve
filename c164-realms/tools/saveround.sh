#!/usr/bin/env bash
# The render station's round of a save, the half done in the session's own checkout: print the jobs
# that open the save in the real game, one for each node, so that they run side by side and the
# first one in is pushed first. Nothing is run here.
#
#   bash tools/saveround.sh <version> <commit of the dist branch> <sha256 of the zip> <board commit>
#   e.g. bash tools/saveround.sh B2 0123abcd 8c0d...976b 316941ab
#
# The jobs, each for a node of its own (run_workspace_job, branch = the render station's):
#   set     the 12 views, each once more after 2 s (what moved), frames a second at V1, V11, V12
#           and in the hall                                   -> renders/real-save/c164-<V>/
#   asked   the cloud terrace, the cable car, the lamps, the listening stops, V6 V9 V10 in a row
#                                                             -> renders/real-save/c164-<V>-asked/
#   guide   the greeting, the six charts, the close, joining again, two visitors, the plaques
#                                                             -> renders/real-save/c164-<V>-guide/
#   film    the tower's clock, the hall, V5                   -> renders/real-save/c164-<V>-film/
#   film2   the dome room, the power room, the time room      -> renders/real-save/c164-<V>-film2/
#   near    the close-ups the owners named (tools/win/shots/save-near.json), when there are any
#                                                             -> renders/real-save/c164-<V>-near/
set -u
[ $# -eq 4 ] || { sed -n '2,20p' "$0"; exit 1; }
V=$1; AT=$2; SHA=$3; BOARD=$4
DIST=${C164_DIST:-cursor/c164-dist-f4b8}
cd "$(dirname "$0")/.." || exit 1
save="--branch $DIST --at $AT --zip dist/$V/c164-$V.zip --sha256 $SHA"
job="bash c164-realms/tools/nodejob.sh --always --tail 30"
echo "JOB set (timeout 1200): $job --limit 1000 python tools/savetrip.py $save --board $BOARD --pairs 2 --fps v01_arrival,v11_lookout,v12_aerial,v07_hall --budget 860"
echo "JOB asked (timeout 1200): $job --limit 1000 env MC_SOUND_LOG=1 python tools/savetrip.py $save --board $BOARD --name c164-$V-asked --also save-asked.json --also save-listen.json --only v06_power,v09_chart_room,v10_time_room,cloud_terrace_west,cloud_station_east,cable_back,lamp_bracket_door,lamp_street_globe,lamp_street_under,lamp_street_foot,l1_hall_clock,l2_power_room,l3_power_fires,l4_time_console --again v06_power,v09_chart_room,v10_time_room --budget 820"
echo "JOB guide (timeout 1500): $job --limit 1300 env MC_SOUND_LOG=1 python tools/guidetrip.py $save --parts joined,title,walk,rejoin,second,plaques --budget 1100"
echo "JOB film (timeout 1100): $job --limit 900 python tools/savetrip.py $save --board $BOARD --name c164-$V-film --also save-film.json --only v05_tower,f1_tower_clock,v07_hall --clips f1_tower_clock:15,v07_hall:12,v05_tower:12 --budget 720"
echo "JOB film2 (timeout 1100): $job --limit 900 python tools/savetrip.py $save --board $BOARD --name c164-$V-film2 --also save-listen.json --only l2_power_room,v08_dome_room,v10_time_room --clips v08_dome_room:12,l2_power_room:12,v10_time_room:10 --budget 720"
if [ -s tools/win/shots/save-near.json ]; then
    names=$(python3 -c "import json,sys; print(','.join(s['name'] for s in json.load(open('tools/win/shots/save-near.json'))))")
    echo "JOB near (timeout 1100): $job --limit 900 python tools/savetrip.py $save --board $BOARD --name c164-$V-near --also save-near.json --only $names --budget 720"
fi
