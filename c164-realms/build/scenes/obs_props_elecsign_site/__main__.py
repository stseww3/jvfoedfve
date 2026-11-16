"""Writes shots.json of this test scene, and with --hung builds the master scene as it stands in
this tree and lists what the package hangs in it (a whole build: on a node, not on the shared
machine):
    python -m scenes.obs_props_elecsign_site [--hung]"""
import json
import os
import sys

from . import build, hung, shots

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}")
    if "--hung" in sys.argv[1:]:
        pieces = hung(build())
        print(f"{len(pieces)} display entities of props/electrics-signs in the master scene:")
        for name, (x, y, z) in pieces:
            print(f"  {name:28s} ({x:7.2f}, {y:6.2f}, {z:7.2f})")
