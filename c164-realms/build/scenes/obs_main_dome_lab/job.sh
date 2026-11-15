#!/bin/bash
# The bench's job on the node (tools/nodejob.sh --wip bash build/scenes/obs_main_dome_lab/job.sh):
# the slit's line-up and the two versions' main views, laid side by side into renders/_wip.
set -e
L=/tmp/c164_dome/lab
rm -rf $L
mkdir -p $L/a $L/b $L/s renders/_wip
rm -f renders/_wip/*.png

draw() {
    python build/render.py $1 --shots build/scenes/$1/shots.json --out $L/$2/$2 ${3:+--only $3} > $L/$2.log 2>&1 \
        || { tail -20 $L/$2.log; exit 1; }
}

draw obs_main_dome a v1,v2_axis,gallery,west &
draw obs_main_dome_b b v1,v2_axis,gallery,west &
draw obs_main_dome_slit s &
wait
cd build
python -m scenes.obs_main_dome.sheet ../renders/_wip/lab-slit.png $L/s --only a_closed,a_half,a_open,b_closed,b_half,b_open --cols 3 --scale 0.5
python -m scenes.obs_main_dome.sheet ../renders/_wip/lab-slit-rows.png $L/s --only a_row,b_row,a_top,b_top --cols 2 --scale 0.5
python -m scenes.obs_main_dome.sheet ../renders/_wip/lab-main.png $L/a $L/b --only v1,v2_axis --scale 0.75
python -m scenes.obs_main_dome.sheet ../renders/_wip/lab-walk.png $L/a $L/b --only gallery,west --scale 0.75
