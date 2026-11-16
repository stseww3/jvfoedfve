"""Writes shots.json of this test scene and says where the home signal stands in this tree, what it
stands on, how many pieces it has and which camera stands inside a block:
    python -m scenes.obs_props_signals_site"""
import json
import math
import os
from collections import Counter

from artkit import models as M
from scenes.obs.props import signals

from . import build, seat, shots

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}")
    c = build()
    x, y, z = seat()
    cell = [int(math.floor(x)), int(math.floor(y + 1e-6)), int(math.floor(z))]
    print(f"the signal's post passes the rails at ({x:g}, {y:g}, {z:g}), cell {tuple(cell)}"
          + (": TAKEN by " + str(c.get(*cell)) if c.has(*cell) else ""))
    while cell[1] > y - 32 and not c.has(*cell):
        cell[1] -= 1
    print(f"under it: {c.get(*cell) if c.has(*cell) else 'nothing within 32 blocks'} at y {cell[1]}")
    pieces = Counter()
    for ex, ey, ez, nbt in c.entities:
        name = M.shown_model(nbt)
        if name.startswith(signals.PREFIX):
            pieces[(name, float(nbt.get("view_range", 0.0)))] += 1
    print("pieces:", ", ".join(f"{name[len(signals.PREFIX):]} x{n} ({view:g})" for (name, view), n in sorted(pieces.items()))
          or "NONE: the signal does not stand")
    wire = signals._home()["wire_to"]
    if wire is not None:
        wx, wy, wz = wire[0]
        wall = (int(math.floor(wx - 0.5)), int(math.floor(wy)), int(math.floor(wz)))
        print(f"the wire goes in at ({wx:g}, {wy:g}, {wz:g}), wall cell {wall}: {c.get(*wall) if c.has(*wall) else 'NO WALL'}")
    for s in shots():
        cx, cy, cz = (int(v // 1) for v in s["pos"])
        if c.has(cx, cy, cz):
            print(f"  camera {s['name']} is inside a block at {(cx, cy, cz)}: {c.get(cx, cy, cz)}")
    for dx in range(-2, 3):
        column = []
        for dz in range(-2, 3):
            top = c.top(int(math.floor(x)) + dx, int(math.floor(z)) + dz, int(y) + 8, int(y) - 40)
            column.append("%4s" % ("." if top is None else top))
        print(f"  tops x {int(math.floor(x)) + dx}: z {int(math.floor(z)) - 2}..{int(math.floor(z)) + 2}:" + "".join(column))
