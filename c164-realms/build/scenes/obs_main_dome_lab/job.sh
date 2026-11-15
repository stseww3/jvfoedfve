#!/bin/bash
# The bench's job on the node (tools/nodejob.sh --wip bash build/scenes/obs_main_dome_lab/job.sh):
# a full-size look at the top line, the slit's line-up and the views across the roofs.
set -e
L=/tmp/c164_dome/lab
rm -rf $L
mkdir -p $L/a $L/b $L/c $L/s renders/_wip
rm -f renders/_wip/*.png

draw() {
    python build/render.py $1 --shots build/scenes/$3/shots.json --out $L/$2/$2 ${4:+--only $4} > $L/$2.log 2>&1 \
        || { tail -20 $L/$2.log; exit 1; }
}

draw obs_main_dome a obs_main_dome v1,v2_axis,v11,roof,west,top &
draw obs_main_dome_b b obs_main_dome v1,v2_axis,v11,roof,west,top &
DOME_LAB="version=b;COLLAR_RELIEF={'a': 0.0, 'b': 0.0}" draw obs_main_dome_lab c obs_main_dome v1,v2_axis &
wait
draw obs_main_dome_slit s obs_main_dome_slit
cd build
python -m scenes.obs_main_dome.sheet $L/top1.png $L/a $L/b $L/c --only v1 --crop 520,290,780,420 --scale 4
python -m scenes.obs_main_dome.sheet $L/top2.png $L/a $L/b $L/c --only v2_axis --crop 500,230,780,330 --scale 4
python - <<PY
from PIL import Image
tiles = [Image.open("$L/top%d.png" % n) for n in (1, 2)]
sheet = Image.new("RGB", (max(t.width for t in tiles), sum(t.height for t in tiles)), (22, 24, 30))
y = 0
for t in tiles:
    sheet.paste(t, (0, y))
    y += t.height
sheet.save("../renders/_wip/look-tops.png")
PY
python -m scenes.obs_main_dome.sheet ../renders/_wip/look-slit-a.png $L/s --only a_closed,a_half,a_open --cols 3 --scale 1
python -m scenes.obs_main_dome.sheet ../renders/_wip/look-slit-b.png $L/s --only b_closed,b_half,b_open --cols 3 --scale 1
python -m scenes.obs_main_dome.sheet ../renders/_wip/look-wide.png $L/a $L/b --only v11,roof,west,top --scale 0.75
