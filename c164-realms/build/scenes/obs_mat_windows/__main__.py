"""python -m scenes.obs_mat_windows: write shots.json from the layout."""
import json
import os

from . import shots

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots.json")
with open(path, "w") as fh:
    fh.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
print(path, len(shots()), "shots")
