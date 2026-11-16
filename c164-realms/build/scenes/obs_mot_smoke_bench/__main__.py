"""Writes shots.json of this test scene:  python -m scenes.obs_mot_smoke_bench"""
import json
import os

from . import shots

if __name__ == "__main__":
    listed = shots()
    path = os.path.join(os.path.dirname(__file__), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in listed) + "\n]\n")
    print(f"{len(listed)} shots -> {path}")
