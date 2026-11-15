"""Writes shots.json of the hall's two test scenes from the scene's numbers:
python -m scenes.obs_int_starhall"""
import json
import os

from . import shots

if __name__ == "__main__":
    here = os.path.dirname(__file__)
    for folder in (here, here + "_b"):
        path = os.path.join(folder, "shots.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
        print(f"{len(shots())} shots -> {path}")
