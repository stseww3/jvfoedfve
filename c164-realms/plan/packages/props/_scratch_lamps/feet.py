"""What became of the source under the armillary and of the door lamps' sources in the master scene."""
from scenes.obs.machines import armillary as A
from scenes.obs.props import lamps
from scenes.obs.sky import lights as SL
from scenes.obs_props_lamps_site import L, build

c = build()
r = SL.report(c)
x, y, z = A.LIGHT_CELL
cell = (x, y - 1, z)
print("light cell", A.LIGHT_CELL, "source cell", cell, "FEET_GLOW", lamps.FEET_GLOW, "rank", lamps.FEET_RANK)
print("placed in the source cell:", r["placed"].get(cell))
for key in ("capped", "rejected", "moved"):
    for e in r.get(key, []):
        if "uplight" in str(e) or cell in tuple(e):
            print(" ", key, e)
print("block in the source cell:", c.b.get(cell), "| in the light cell:", c.b.get(A.LIGHT_CELL))
near = [(k, v) for k, v in r["placed"].items() if abs(k[0] - x) <= 4 and abs(k[2] - z) <= 4]
print("sources within 4 cells:", sorted(near))
lv = L.levels(c, (x - 4, y - 5, z - 4), (x + 4, y + 4, z + 4))
print("block light, the section through z", z, "(west to east; # taken, . none)")
for yy in range(y + 2, y - 5, -1):
    print("  y %2d  " % yy + " ".join("%2s" % lv.get((xx, yy, z), "#" if c.has(xx, yy, z) else ".")
                                       for xx in range(x - 4, x + 5)))
print("the rings' entities in the light cell:",
      sum(1 for ex, ey, ez, _ in c.entities if (int(ex // 1), int(ey // 1), int(ez // 1)) == (x, y, z)))
print("cage sources:", sorted((k, v) for k, v in r["placed"].items() if "cage" in v[1]))
print("keys of the report:", sorted(k for k in r if not k.startswith("_")))
