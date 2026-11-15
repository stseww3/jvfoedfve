"""python -m scenes.obs_mat_ashlar_b: write shots.json (the same shots as obs_mat_ashlar)."""
import json
import os

from . import shots

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots.json")
with open(path, "w") as fh:
    fh.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
print(path, len(shots()), "shots")
