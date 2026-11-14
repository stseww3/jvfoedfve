"""Writes shots.json of this test scene from the skeleton's cameras:  python -m scenes.obs_sky_cloudsea_a"""
import json
import os

from . import shots

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}")
