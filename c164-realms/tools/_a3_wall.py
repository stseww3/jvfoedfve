"""Scratch probe (trial branch only, never delivered): the dome room's wall as the test scene builds it.

    python tools/_a3_wall.py            plans of the rows 18..23 (the drum's lining and what stands by it)
    python tools/_a3_wall.py v8 P ...   where the points P = x,y,z fall in V8's picture (1280 x 720)
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "build"))

from scenes.obs.common import skeleton as S                     # noqa: E402
from scenes.obs.interiors import domeroom as D                  # noqa: E402

FOV = 70.0
W, H = 1280, 720


def short(state):
    if state is None:
        return " "
    name = state.partition("[")[0].split(":")[-1]
    if "light" == name:
        return "'"
    if "trapdoor" in name:
        return "T"
    if "barrier" in name:
        return "#"
    if "bars" in name:
        return "|"
    if "stairs" in name:
        return "s"
    if "slab" in name:
        return "-"
    return name[0]


def plans():
    from scenes.obs_int_domeroom import dressed
    c, _ = dressed()
    names = {}
    for y in range(18, 24):
        print("row y = %d (north up; x -9..17)" % y)
        for z in range(-12, 13):
            row = ""
            for x in range(-9, 18):
                state = c.get(x, y, z)
                row += short(state)
                if state is not None:
                    names.setdefault(short(state), set()).add(state.partition("[")[0].split(":")[-1])
            print("z %3d  %s" % (z, row.rstrip()))
    for k in sorted(names):
        print("  %s = %s" % (k, ", ".join(sorted(names[k]))))
    lined = D.lined()
    print("lined columns: %d; windows the room sees (column, row, side):" % len(lined))
    from scenes.obs_int_domeroom import shell
    read = D.Shell(shell())
    for col in sorted(lined):
        for y in range(D.FEET, D.WALL_TOP + 1):
            side = read.window(col, y)
            if side is not None:
                print("   ", col, y, side)


def project(points):
    pos, look = S.V8["pos"], S.V8["look_at"]
    f = [look[i] - pos[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in f))
    f = [v / n for v in f]
    r = [-f[2], 0.0, f[0]]                                  # right = forward x up (y), for z south, x east
    n = math.hypot(r[0], r[2])
    r = [v / n for v in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    ty = math.tan(math.radians(FOV) / 2.0)
    tx = ty * W / H
    for p in points:
        d = [p[i] - pos[i] for i in range(3)]
        zf = sum(d[i] * f[i] for i in range(3))
        xr = sum(d[i] * r[i] for i in range(3))
        yu = sum(d[i] * u[i] for i in range(3))
        if zf <= 0:
            print(p, "behind the camera")
            continue
        px = W / 2.0 + xr / zf / tx * W / 2.0
        py = H / 2.0 - yu / zf / ty * H / 2.0
        print("(%.2f, %.2f, %.2f) -> picture (%.0f, %.0f), %.1f blocks away%s"
              % (p[0], p[1], p[2], px, py, math.sqrt(sum(v * v for v in d)),
                 "" if 0 <= px <= W and 0 <= py <= H else "  (outside the frame)"))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "v8":
        project([tuple(float(v) for v in a.split(",")) for a in sys.argv[2:]])
    else:
        plans()
