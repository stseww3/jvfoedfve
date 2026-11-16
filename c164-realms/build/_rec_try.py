"""Scratch of c356, not for the assembly: V4 of the master scene with the entrance's plate shown in
several lights, one picture each (renders/_wip/doorplate-s<sky>b<block>-v04.png)."""
import json
import sys

import render
from scenes.obs.props import signs

SHOTS = "/tmp/rec_try_shots.json"
with open(SHOTS, "w") as f:
    json.dump([dict(name="v04", pos=[27.5, 1.62, 3.5], look_at=[17.5, 4.5, 0.5], time=14000)], f)
for shown in [tuple(int(v) for v in arg.split(",")) for arg in sys.argv[1:]]:
    signs.DOOR_PLATE_SHOWN = shown
    sys.argv = ["render.py", "obs", "--shots", SHOTS, "--out", "../renders/_wip/doorplate-s%db%d" % shown]
    render.main()
