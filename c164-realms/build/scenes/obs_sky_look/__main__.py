"""python -m scenes.obs_sky_look (in build/): write this scene's shots.json."""
import json
import os

from . import shots

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots.json")
with open(path, "w") as fh:
    fh.write("[\n" + ",\n".join(" " + json.dumps(shot) for shot in shots()) + "\n]\n")
print(f"{len(shots())} shots -> {path}")
