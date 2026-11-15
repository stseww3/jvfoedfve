"""python -m scenes.obs_int_domeroom: the room as text (no game, no picture), then what the room must
keep clear of, checked cell by cell against the same box without the room. Ends with status 1 if a
check fails."""
import sys

from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import domeroom as D
from scenes.obs.main import _order as O

from . import EXIT, dressed, shell

bare, (c, placed) = shell(), dressed()
cx, cz = S.DOME_CENTRE
print("section along the axis (z = %d), looking north" % cz)
print(O.section(c, "z", cz, (cx - 15, cx + 15), (S.DRUM_BASE, S.DOME_APEX + 2)))
print("section beside the slit (z = %d), looking north" % (cz + S.SLIT_W // 2 + 1))
print(O.section(c, "z", cz + S.SLIT_W // 2 + 1, (cx - 15, cx + 15), (S.DRUM_BASE, S.DOME_APEX + 2)))
print("section across (x = %d), looking west" % cx)
print(O.section(c, "x", cx, (cz - 15, cz + 15), (S.DRUM_BASE, S.DOME_APEX + 2)))
for y in (S.ROOF_FLOOR, S.ROOF_STAND, S.DRUM[1] - 1, S.DRUM[1], S.DOME_SPRING + 1, S.DOME_SPRING + 4,
          S.DOME_SPRING + 8):
    print("plan of row y = %d, north up" % y)
    for z in range(cz - 14, cz + 15):
        print("z %3d  %s" % (z, "".join(" " if c.get(x, y, z) is None else O.mark(c.get(x, y, z))
                                         for x in range(cx - 14, cx + 15)).rstrip()))

# --- the checks -------------------------------------------------------------------------------------
added = {k: v for k, v in c.b.items() if bare.b.get(k) != v}        # every cell the room set or changed
solid = {k for k, v in added.items() if v.partition("[")[0] != B.LIGHT}
gone = [k for k in bare.b if k not in c.b]
read = D.Shell(bare)
room, leaf = D.room(), D.leaf()
floor = D.observing_floor()
head = (D.FEET, D.FEET + 1)                                         # the two rows a person takes up
failed = []


def check(what, bad):
    bad = sorted(bad)
    print("%s  %s%s" % ("ok  " if not bad else "FAIL", what,
                        "" if not bad else ": %d, first %s" % (len(bad), bad[:6])))
    if bad:
        failed.append(what)


def cells(cols, rows):
    return {(x, y, z) for x, z in cols for y in rows}


print()
print("the room set %d cells (%d of them light) and placed %d display entities"
      % (len(added), len(added) - len(solid), placed))
check("the room takes nothing away", gone)
check("every cell lies in a column of the room or of the inner leaf, from the floor up",
      [k for k in solid if (k[0], k[2]) not in room | leaf or k[1] < D.FLOOR_Y])
check("over the inner leaf only the base ring and what hangs under the skin (rows %d and up)" % D.BASE_RING_Y,
      [k for k in solid if (k[0], k[2]) in leaf and k[1] < D.BASE_RING_Y])
check("row %d is left to the track and the rollers (machines/domegear)" % D.LEDGE_Y,
      [k for k in solid if k[1] == D.LEDGE_Y])
check("row %d holds the base ring over the inner leaf and nothing in the room's columns" % D.BASE_RING_Y,
      [k for k in solid if k[1] == D.BASE_RING_Y and (k[0], k[2]) not in leaf])
check("the opening round the pier and its curb: only the observing floor's boards, in the floor's row",
      [k for k in solid if (k[0], k[2]) in D.envelope() and k[1] <= D.WALL_TOP
       and not (k[1] == D.FLOOR_Y and (k[0], k[2]) in floor)])
check("the two doorways and the cells round them are free to walk through",
      solid & cells({n for door in D.doorways() for n in O.grow({door})}, head))
check("the stair's exit, the three cells above it and the cells round it are free",
      solid & (cells({EXIT}, range(D.FEET, D.FEET + 3)) | cells(O.grow({EXIT}), head)))
check("the observing floor is free to stand on", solid & cells(floor, range(D.FEET, D.FEET + 3)))
check("the gear's shaft keeps its column of the wall, and its hand wheel the floor in front",
      solid & (cells(D.GEAR_SHAFT, range(D.FEET, D.LEDGE_Y + 1)) | cells(D.GEAR_STAND, head)))
check("nothing stands in the open slit", [k for k in solid if (k[0], k[2]) in read.gap and k[1] >= D.SKIN_FROM])
check("the niches keep their windows: nothing between the furniture and the ring beam",
      [k for k in solid for side in D.niches().values()
       if (k[0], k[2]) in side and D.FEET + 2 <= k[1] < D.WALL_TOP])
check("a light source sits in a free cell",
      [cell for cell, _level, _rank, _name in D.lights() if c.name(*cell) not in (None, B.LIGHT)])

ribs = [a for a in D.rib_angles() if not read.in_slit(a)]
missing = []
for a in ribs:
    line = {col for col in read.reach if D._on_meridian(col[0], col[1], a) and D._polar(*col)[0] >= D.COLLAR[1]}
    if not any((k[0], k[2]) in line and k[1] >= D.SKIN_FROM for k in solid):
        missing.append(a)
print("%d ribs under the skin, %d meridians taken by the slit" % (len(ribs) - len(missing), D.RIBS - len(ribs)))
check("every rib outside the slit has its rib inside", missing)
check("the slit is open and takes two ribs", [] if read.gap and len(ribs) == D.RIBS - 2 else [len(ribs)])

print()
print("FAILED: " + "; ".join(failed) if failed else "all checks pass")
sys.exit(1 if failed else 0)
