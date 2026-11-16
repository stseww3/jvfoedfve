"""Trial tree only (never delivered): what the dome room's air touches. Floods the air from a cell
inside the room and draws rows of the dome's foot as plans; lists the verdigris and the stone that
show a face to the room, row by row.

    cd build && python _trial_seen.py [row ...]
"""
import collections
import sys

from scenes import obs_int_domeroom as T
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import domeroom as D
from scenes.obs.main import _order as O

c = T.dressed()[0]
cx, cz = S.DOME_CENTRE
whole = O.disc(cx, cz, S.DOME_R)
room = D.room()
start = (cx + 5, 19, cz + 4)
assert c.name(*start) is None, c.name(*start)
seen, todo = {start}, collections.deque([start])
AROUND = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
faces = collections.defaultdict(list)
while todo:
    x, y, z = todo.popleft()
    for dx, dy, dz in AROUND:
        n = (x + dx, y + dy, z + dz)
        if (n[0], n[2]) not in whole or not 17 <= n[1] <= 40:
            continue
        if c.name(*n) is None:
            if n not in seen:
                seen.add(n)
                todo.append(n)
        else:
            faces[n].append((-dx, -dy, -dz))


def kind(name):
    if name is None:
        return "."
    n = name.rpartition(":")[2].split("[")[0]
    if n.startswith(("waxed_oxidized", "waxed_weathered")):
        return "v"                      # verdigris
    if n.startswith("oxidized"):
        return "i"                      # iron
    if "sandstone" in n:
        return "s"
    if "spruce" in n or "dark_oak" in n:
        return "w"
    if "glass" in n:
        return "g"
    return "?"


rows = collections.defaultdict(collections.Counter)
for (x, y, z) in faces:
    rows[y][kind(c.name(x, y, z))] += 1
print(len(seen), "air cells;", len(faces), "blocks show a face to the room's air (v verdigris, i iron, s stone, w wood)")
for y in sorted(rows):
    print(f"  y {y}: " + ", ".join(f"{k} {n}" for k, n in sorted(rows[y].items())))
print("verdigris and stone that show a face to the room, rows 18..27:")
for (x, y, z), fs in sorted(faces.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
    k = kind(c.name(x, y, z))
    if k in "vs" and 18 <= y <= 27 and not (y == 23 and fs == [(0, 1, 0)]):
        print(f"  ({x}, {y}, {z}) {c.name(x, y, z).rpartition(':')[2]}  faces {fs}")
for y in (int(a) for a in (sys.argv[1:] or ["24", "25", "26"])):
    print(f"row {y}: capital = shows a face to the room's air; ',' air outside the room's columns that the room's air reaches")
    for z in range(cz - 14, cz + 15):
        line = ""
        for x in range(cx - 14, cx + 15):
            k = kind(c.name(x, y, z))
            if (x, y, z) in seen:
                k = " " if (x, z) in room else ","
            elif k != "." and (x, y, z) in faces:
                k = k.upper()
            line += k
        print(f"  z {z:>3}  {line}")
