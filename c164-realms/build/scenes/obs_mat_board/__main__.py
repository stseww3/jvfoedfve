"""python -m scenes.obs_mat_board: write shots.json from the layout. With `plan`: print the ground
tier from above and the blocks of the occupancy table that the board lacks, and write nothing."""
import json
import os
import sys

from . import build, lacking, plan, shots

if sys.argv[1:] == ["plan"]:
    canvas = build()
    print(plan(canvas))
    repainted, vanilla = lacking(canvas)
    print("repainted blocks not on the board:", ", ".join(repainted) or "none")
    print("blocks used as the game draws them, not on the board:", ", ".join(vanilla) or "none")
else:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots.json")
    text = "[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n"     # before the file is opened
    with open(path, "w") as fh:
        fh.write(text)
    print(path, len(shots()), "shots")
