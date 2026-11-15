#!/bin/bash
# The bench's job on the node (tools/nodejob.sh --wip bash build/scenes/obs_main_dome_lab/job.sh):
# draws the variants named below and lays them side by side into renders/_wip.
set -e
L=/tmp/c164_dome/lab
rm -rf $L
mkdir -p $L renders/_wip
rm -f renders/_wip/*.png
SHOTS=build/scenes/obs_main_dome/shots.json
ONLY=v1,v2_axis,v11,roof,drum,gallery,ridge,aerial,top

draw() {
    mkdir -p $L/$1
    DOME_LAB="$2" python build/render.py obs_main_dome_lab --shots $SHOTS --only $ONLY --out $L/$1/$1 > $L/$1.log 2>&1 \
        || { tail -20 $L/$1.log; exit 1; }
}

draw A3 "version=a;RUNS={'a': None, 'b': None}" &
draw A7 "version=a;RUNS={'a': (1, 1, 1, 1, 1), 'b': None}" &
draw A8 "version=a" &
wait
draw A9 "version=a;RUNS={'a': (2, 2, 2, 2, 2), 'b': None}" &
draw B1 "version=b" &
draw B4 "version=b;COLLAR_RELIEF={'a': 0.0, 'b': 0.0}" &
wait
ALL="$L/A3 $L/A7 $L/A8 $L/A9 $L/B1 $L/B4"
cd build
python -m scenes.obs_main_dome.sheet $L/far1.png $ALL --only v1 --crop 480,280,800,460 --scale 2
python -m scenes.obs_main_dome.sheet $L/far2.png $ALL --only v2_axis --crop 480,190,800,370 --scale 2
python -m scenes.obs_main_dome.sheet $L/far3.png $ALL --only v11 --crop 480,130,800,310 --scale 2
python -m scenes.obs_main_dome.sheet ../renders/_wip/lab-near.png $ALL --only roof,drum --scale 0.5
python -m scenes.obs_main_dome.sheet ../renders/_wip/lab-above.png $ALL --only aerial,top --scale 0.5
python - <<PY
from PIL import Image
tiles = [Image.open("$L/far%d.png" % n) for n in (1, 2, 3)]
sheet = Image.new("RGB", (max(t.width for t in tiles), sum(t.height for t in tiles)), (22, 24, 30))
y = 0
for t in tiles:
    sheet.paste(t, (0, y))
    y += t.height
sheet.save("../renders/_wip/lab-far.png")
PY
python -m scenes.obs_main_dome.sheet ../renders/_wip/lab-walk.png $L/A8 $L/B1 --only gallery,ridge --scale 0.75
