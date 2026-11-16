"""Writes shots.json of this test scene:  python -m scenes.obs_props_plaques_site
With --report it also builds the scene (the whole master scene: a node's job) and prints the
plaques of the site as they are in this tree: which hang, which were left out for want of the
wall behind them, any camera that stands inside a block, and the plaques a camera of the board
stands near enough to show."""
import json
import os
import sys

from scenes.obs.props import plaques

from . import build, in_board, shots

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}")
    table = plaques.site_plaques()
    print(f"{len(table)} of {len(plaques.TEXT)} plaques are in the tables; "
          f"not placed by either half: {', '.join(k for k in plaques.TEXT if k not in table) or 'none'}")
    for key, view, far in in_board():
        print(f"  {key} hangs {far:.1f} blocks from {view} and looks its way: the board may show it")
    if "--report" in sys.argv[1:]:
        c = build()
        left = list(getattr(c, "plaques_left_out", []))
        print("display entities:", c.entity_counts)
        print("plaques that hang:", ", ".join(k for k in table if k not in left) or "none")
        for key in left:
            print(f"  left out, nothing stands behind it: {key} at {table[key]['pos']}")
        for s in shots():
            x, y, z = (int(v // 1) for v in s["pos"])
            if c.has(x, y, z):
                print(f"  camera {s['name']} is inside a block at {(x, y, z)}: {c.get(x, y, z)}")
