"""Build obs_int_timeroom and print the block light of the room by numbers."""
import sys
sys.path.insert(0, ".")
import scenes.obs_int_timeroom as scene
from scenes.obs.interiors import timeroom as T
from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import lights as SL

c = scene.build()
r = c.light_report
print("placed:", sorted((cell, v) for cell, v in r["placed"].items()))
for key in ("rejected", "moved", "capped", "merged", "problems"):
    if r.get(key):
        print(key + ":", r[key])
lv = L.levels(c, (T.X0 - 2, T.FLOOR_Y, T.Z0 - 1), (T.X1 + 2, T.CEIL_Y, T.Z1 + 1))
hexd = "0123456789abcdef"
def g(x, y, z):
    return hexd[lv.get((x, y, z), 0)]
print("rack faces (z -24), rows y 13..7, x 2..13:")
for y in range(13, 6, -1):
    print("  y%2d " % y + " ".join(g(x, y, T.CONSOLE_Z) for x in range(T.X0, T.X1 + 1)))
for y in (7, 9, 11, 13):
    print("plan at y %d, z from -25 (top) to -7, x 2..13:" % y)
    for z in range(T.Z0, T.Z1 + 1):
        print("  z%3d " % z + " ".join(g(x, y, z) for x in range(T.X0, T.X1 + 1)))
print("entities:", len(c.entities), "blocks:", len(c.b))
print("ceiling row y 13 again, and the floor's block at (8, 6, -15):", c.b.get((8, 6, -15)))
