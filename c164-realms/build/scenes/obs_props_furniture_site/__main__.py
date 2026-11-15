"""Writes shots.json of this test scene:  python -m scenes.obs_props_furniture_site
With --report it also builds the scene (the whole master scene: a node's job) and prints the
furniture of the site as it is in this tree: which pieces stand, which were left out for want of
a floor, and any camera that stands inside a block."""
import json
import os
import sys
from collections import Counter

from scenes.obs.props import furniture

from . import FLOORS, build, in_tree, shots

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}")
    for group, module in FLOORS.items():
        if not in_tree(group):
            print(f"  no cameras for the group {group}: {module.replace('.', '/')} is not in this tree")
    if "--report" in sys.argv[1:]:
        c = build()
        left = {(group, kind, tuple(p)) for group, kind, p in getattr(c, "furniture_left_out", [])}
        stand = Counter((group, kind) for group, kind, p, _, _ in furniture.site_pieces()
                        if (group, kind, tuple(p)) not in left)
        print("display entities:", c.entity_counts)
        print("furniture of the site that stands:",
              ", ".join(f"{g} {k} x{n}" for (g, k), n in sorted(stand.items())) or "none")
        for group, kind, p in sorted(left):
            print(f"  left out, no floor under it: {group} {kind} {p}")
        for s in shots():
            x, y, z = (int(v // 1) for v in s["pos"])
            if c.has(x, y, z):
                print(f"  camera {s['name']} is inside a block at {(x, y, z)}: {c.get(x, y, z)}")
