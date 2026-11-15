"""Writes shots.json of the lamps-off test scene and prints what stands in this tree:
    python -m scenes.obs_props_lamps_site_off

The shots are obs_props_lamps_site's own list, unchanged, so that each picture has a twin under the
same name in that scene's folder and the two can be put against each other."""
import json
import os

from . import build, shots

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}")
    c = build()
    print("display entities:", c.entity_counts)
