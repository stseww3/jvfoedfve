#!/bin/bash
# The bench's job on the node (tools/nodejob.sh --wip bash build/scenes/obs_main_dome_lab/job.sh):
# the top line of both versions and the near views, after the ribs' relief was taken off the cap.
set -e
L=/tmp/c164_dome/lab
rm -rf $L
mkdir -p $L/a $L/b renders/_wip
rm -f renders/_wip/*.png

draw() {
    python build/render.py $1 --shots build/scenes/obs_main_dome/shots.json --out $L/$2/$2 > $L/$2.log 2>&1 \
        || { tail -20 $L/$2.log; exit 1; }
}

draw obs_main_dome a &
draw obs_main_dome_b b &
wait
cd build
python -m scenes.obs_main_dome.sheet $L/top1.png $L/a $L/b --only v1 --crop 520,290,780,420 --scale 4
python -m scenes.obs_main_dome.sheet $L/top2.png $L/a $L/b --only v2_axis --crop 500,230,780,330 --scale 4
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
python -m scenes.obs_main_dome.sheet ../renders/_wip/look-b-near.png $L/b --only roof,drum,ridge,gallery --cols 2 --scale 0.75
python -m scenes.obs_main_dome.sheet ../renders/_wip/look-b-above.png $L/b --only aerial,top,slit,west --cols 2 --scale 0.75
python -m scenes.obs_main_dome.sheet ../renders/_wip/look-a-near.png $L/a --only roof,drum,ridge,gallery --cols 2 --scale 0.75
