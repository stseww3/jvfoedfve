"""Writes shots.json of this test scene and of its three twins:  python -m scenes.obs_main_facade"""
import json
import os

from . import COMPARE, HEADS, shots

if __name__ == "__main__":
    here = os.path.dirname(__file__)
    for folder, only in ((here, None), (here + "_a", COMPARE), (here + "_c", COMPARE), (here + "_nocrown", HEADS)):
        path = os.path.join(folder, "shots.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots(only)) + "\n]\n")
        print(f"{len(shots(only))} shots -> {path}")
