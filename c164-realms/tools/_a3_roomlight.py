#!/usr/bin/env python3
"""Scratch (a3, trial branch only): the block light on the floor of a room of the master scene, as
tools/darkfloor.py reads it (the better of the cell of the feet and the cell of the head), printed
as a plan, with candidate sources tried on top.

    python tools/_a3_roomlight.py x0,z0,x1,z1,feet ['[[x,y,z,level], ...]' ...]

Every further argument is one set of candidates (a JSON list); each set is tried by itself.
"""
import json
import sys

sys.path.insert(0, "build")

from artkit import blocks as AB  # noqa: E402
from artkit.blocks import st  # noqa: E402
from scenes import obs  # noqa: E402
from scenes.obs.common import blocks as B  # noqa: E402
from scenes.obs.sky import _lightkit as L  # noqa: E402

X0, Z0, X1, Z1, FEET = (int(v) for v in sys.argv[1].split(","))
MARGIN = 8


def plan(canvas, tag):
    light = L.levels(canvas, (X0 - MARGIN, FEET - 4, Z0 - MARGIN), (X1 + MARGIN, FEET + 9, Z1 + MARGIN))
    shut = {}

    def free(cell):
        state = canvas.b.get(cell)
        if state is None:
            return True
        if state not in shut:
            shut[state] = L._stops_light(state)
        return not shut[state]

    print(tag)
    print("        " + " ".join("%2d" % (x % 100) for x in range(X0, X1 + 1)))
    dark = []
    for z in range(Z0, Z1 + 1):
        row = []
        for x in range(X0, X1 + 1):
            if not (free((x, FEET, z)) and free((x, FEET + 1, z))) or free((x, FEET - 1, z)):
                row.append(" #")
                continue
            level = max(light.get((x, FEET, z), 0), light.get((x, FEET + 1, z), 0))
            row.append("%2d" % level)
            if level < 5:
                dark.append((x, z, level))
        print("z %4d  " % z + " ".join(row))
    print("%d under 5: %s" % (len(dark), " ".join("(%d,%d)=%d" % d for d in dark)))
    return dark


def main():
    canvas = obs.build()
    sources = sorted((cell, str(state)) for cell, state in canvas.b.items()
                     if AB.name_of(state) == B.LIGHT and X0 - 2 <= cell[0] <= X1 + 2 and Z0 - 2 <= cell[2] <= Z1 + 2
                     and FEET - 1 <= cell[1] <= FEET + 8)
    print("sources in the room:", " ".join("(%d,%d,%d)=%s" % (c[0], c[1], c[2], n.split("level=")[-1].rstrip("]"))
                                           for c, n in sources))
    plan(canvas, "as built")
    for text in sys.argv[2:]:
        tried = json.loads(text)
        before = {}
        for x, y, z, level in tried:
            before[(x, y, z)] = canvas.b.get((x, y, z))
            if before[(x, y, z)] is not None:
                print("   the cell (%d, %d, %d) holds %s" % (x, y, z, AB.name_of(before[(x, y, z)])))
            canvas.set(x, y, z, st(B.LIGHT, level=level))
        plan(canvas, "with " + text)
        for cell, state in before.items():
            if state is None:
                canvas.b.pop(cell, None)
            else:
                canvas.b[cell] = state


main()
