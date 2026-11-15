"""Writes shots.json of this test scene and prints which lamps of the site stand in this tree:
    python -m scenes.obs_props_lamps_site"""
import json
import os
from collections import Counter

from scenes.obs.props import lamps

from . import build, shots

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}")
    c = build()
    left = {(group, kind, tuple(p)) for group, kind, p in getattr(c, "lamps_left_out", [])}
    table = lamps.site_lamps()
    stand = Counter((group, kind) for group, kind, p, _, _ in table if (group, kind, tuple(p)) not in left)
    print("display entities:", c.entity_counts)
    print("lamps of the site that stand:", ", ".join(f"{g} {k} x{n}" for (g, k), n in sorted(stand.items())) or "none")
    for group, kind, p in sorted(left):
        print(f"  left out, nothing to stand on or hang from: {group} {kind} {p}")
    for s in shots():
        x, y, z = (int(v // 1) for v in s["pos"])
        if c.has(x, y, z):
            print(f"  camera {s['name']} is inside a block at {(x, y, z)}: {c.get(x, y, z)}")
