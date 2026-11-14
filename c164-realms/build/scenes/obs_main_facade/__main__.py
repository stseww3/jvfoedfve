"""Writes shots.json of this test scene and of its two twins:  python -m scenes.obs_main_facade"""
import json
import os

from . import shots

if __name__ == "__main__":
    here = os.path.dirname(__file__)
    for folder, compare in ((here, False), (here + "_a", True), (here + "_c", True)):
        path = os.path.join(folder, "shots.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots(compare)) + "\n]\n")
        print(f"{len(shots(compare))} shots -> {path}")
