"""Where a visitor walks in three rooms, on the half-block lattice walkreach works on: the ways
from the route's first point, as tools/walk.py looks for them. For moving the stations of the
indoor walk's stretches B, F, L.  Run in c164-realms/:  python renders/_wip/m3_walkmap.py"""
import json
import math
import os
import sys

sys.path.insert(0, "tools")
sys.path.insert(0, "build")
import walk as WK  # noqa: E402
import walkreach as W  # noqa: E402

ROOMS = (("B", 0.0, (1.0, -6.0, 17.0, 6.5)), ("F", 7.0, (2.0, -25.5, 15.0, -4.5)), ("L", -6.0, (68.0, 16.5, 89.5, 41.0)))
out = []
route = json.load(open("plan/reviews/walk/in-route.json"))
cells = WK.scene_cells("obs", "/tmp/c164_walk/m3-canvas.pickle")
feet, source = WK.feet_finder(cells)
pts = [p["at"] for s in route["stretches"] for p in s["points"]]
bounds = (math.floor(min(p[0] for p in pts)) - WK.MARGIN, math.floor(min(p[2] for p in pts)) - WK.MARGIN,
          math.floor(max(p[0] for p in pts)) + WK.MARGIN, math.floor(max(p[2] for p in pts)) + WK.MARGIN)
x, y, z = pts[0]
reach = W.reach_of(cells, (x, feet(x, z, y), z), bounds)
out.append(f"ways from {pts[0]}: {len(reach.kind)} places; feet by {source}")
world = reach.world
for name, level, (x0, z0, x1, z1) in ROOMS:
    out.append(f"== {name}: level {level:g}; a column every half block from x {x0:g} to {x1:g} (| marks whole x), rows z {z0:g} .. {z1:g}. "
               "o a walked place on the level with a floor under the very point, w walked but the point's own floor is not the level's, "
               "h by a jump only, f by a drop, t no way back, u/d a walked place half a block or more over/under the level, . nobody stands")
    xs = [x0 + 0.5 * k for k in range(int(round((x1 - x0) * 2)) + 1)]
    out.append("        " + "".join(("|" if abs(v - round(v)) < 1e-9 else " ") for v in xs))
    out.append("        " + "".join((str(int(abs(round(v))) % 10) if abs(v - round(v)) < 1e-9 else " ") for v in xs))
    for k in range(int(round((z1 - z0) * 2)) + 1):
        zz = z0 + 0.5 * k
        row = []
        for xx in xs:
            i, j = world.lattice(xx, zz)
            mark = "."
            for top, _ in world.stand(i, j):
                node = (i, j, int(round(top * W.Q)))
                if node not in reach.kind or abs(top - level) > 1.0 + 1e-6:
                    continue
                kind = reach.kind[node]
                if abs(top - level) > 0.26:
                    mark = "u" if top > level else "d"
                elif kind == "walk":
                    under = feet(xx, zz, level)
                    mark = "o" if under is not None and abs(under - level) <= 0.01 else "w"
                else:
                    mark = kind[0]
                if abs(top - level) <= 0.26:
                    break
            row.append(mark)
        out.append(f"{zz:7.1f} " + "".join(row))
    out.append("")
os.makedirs("renders/_wip/walkfix", exist_ok=True)
open("renders/_wip/walkfix/walkmap.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
