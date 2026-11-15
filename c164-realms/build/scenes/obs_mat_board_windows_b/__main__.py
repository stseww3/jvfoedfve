"""python -m scenes.obs_mat_board_windows_b: write shots.json from the layout."""
import json
import os

from . import shots

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots.json")
text = "[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n"     # before the file is opened
with open(path, "w") as fh:
    fh.write(text)
print(path, len(shots()), "shots")
