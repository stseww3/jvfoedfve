"""python -m scenes.obs_int_domeroom: the room as text (no game, no picture), then what the room must
keep clear of, checked cell by cell against the same box without the room. Ends with status 1 if a
check fails."""
import json
import math
import os
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
doors = D.doorways()
door_rows = range(S.DOME_ROOM_DOORS["y"][0], S.DOME_ROOM_DOORS["y"][1] + 1)
STONE = frozenset([*B.ASHLAR_ROUGH.all(), *B.ASHLAR_FINE.all(), *B.ASHLAR_PANEL.all(), B.ASHLAR_EMBLEM])
COPPER = D.SKIN - frozenset(B.IRON_RIVETED.all())
failed = []


def check(what, bad):
    bad = sorted(bad)
    print("%s  %s%s" % ("ok  " if not bad else "FAIL", what,
                        "" if not bad else ": %d, first %s" % (len(bad), bad[:6])))
    if bad:
        failed.append(what)


def cells(cols, rows):
    return {(x, y, z) for x, z in cols for y in rows}


def kind(x, y, z):
    """The block of a cell of the dressed box without its state; None for a free cell (a light
    source counts as free)."""
    name = c.name(x, y, z)
    name = None if name is None else name.rpartition(":")[2]
    return None if name == B.LIGHT else name


def walk(start):
    """The columns of the room one reaches on foot from `start`."""
    def open_(col):
        return (col in room and kind(col[0], D.FLOOR_Y, col[1]) is not None
                and all(kind(col[0], y, col[1]) is None for y in head))
    seen, todo = {start}, [start]
    while todo:
        col = todo.pop()
        for d in O.SIDES:
            n = O.step(col, d)
            if n not in seen and open_(n):
                seen.add(n)
                todo.append(n)
    return seen


print()
print("the room set %d cells (%d of them light) and placed %d display entities"
      % (len(added), len(added) - len(solid), placed))
check("the room takes nothing away", gone)
check("every cell lies in a column of the room or of the inner leaf, from the floor up",
      [k for k in solid if (k[0], k[2]) not in room | leaf or k[1] < D.FLOOR_Y])
check("over the inner leaf only the ring girder and the vault (rows %d and up)" % D.BASE_RING[0],
      [k for k in solid if (k[0], k[2]) in leaf and k[1] < D.BASE_RING[0]])
check("row %d is left to the track and the rollers (machines/domegear)" % D.LEDGE_Y,
      [k for k in solid if k[1] == D.LEDGE_Y])
check("row %d holds the ring girder over the inner leaf and nothing in the room's columns" % D.BASE_RING[0],
      [k for k in solid if k[1] == D.BASE_RING[0] and (k[0], k[2]) not in leaf])
check("the opening round the pier, its curb and its railing are left as main/shell lays them",
      [k for k in solid if (k[0], k[2]) in D.envelope() and k[1] <= D.WALL_TOP])
check("the two doorways are free to walk through", solid & cells(doors, door_rows))
targets = {EXIT} | (floor - D.envelope()) | set(D.GEAR_STAND)
check("from either door one walks to the stair's exit, over the observing floor's boards and to the hand wheel",
      [(door, t) for door in doors for t in targets - walk(door)])
check("the stair's exit, the three cells above it and the cells round it are free",
      solid & (cells({EXIT}, range(D.FEET, D.FEET + 3)) | cells(O.grow({EXIT}), head)))
check("the observing floor is free to stand on", solid & cells(floor, range(D.FEET, D.FEET + 3)))
check("the gear's shaft keeps its column of the wall, and its hand wheel the floor in front",
      solid & (cells(D.GEAR_SHAFT, range(D.FEET, D.LEDGE_Y + 1)) | cells(D.GEAR_STAND, head)))
dome = D._other("main", "dome")
if (getattr(dome, "VERSION", None), getattr(dome, "SLIT", None)) == ("a", "open"):
    check("the gear of the slit's leaves keeps its cells at the slit's foot and under the girders beside it",
          solid & D.gear_cells())
else:
    print("skip  the gear of the slit's leaves: its cells are laid out for main/dome's version a with the "
          "slit open, and that is not the dome in this box")
check("nothing stands in the open slit", [k for k in solid if (k[0], k[2]) in read.gap and k[1] >= D.SKIN_FROM])
bare_stone = []
for col in read.wall:
    for y in range(D.FEET, D.WALL_TOP):
        if kind(col[0], y, col[1]) is not None or read.glazed(col, y):
            continue
        if col in D.GEAR_SHAFT or (col in doors and y in door_rows):
            continue
        if any(O.step(col, d) in leaf and kind(O.step(col, d)[0], y, O.step(col, d)[1]) in STONE for d in O.SIDES):
            bare_stone.append((col[0], y, col[1]))
check("no stone shows indoors: the lining stands in front of the drum, but for the doors, the windows' "
      "reveals and the shaft's column", bare_stone)
check("every window the room sees keeps its reveal",
      [(col[0], y, col[1]) for col in read.wall for y in range(D.FEET, D.WALL_TOP)
       if read.glazed(col, y) and kind(col[0], y, col[1]) is not None])
green = []
for col in read.reach - read.gap:
    if read.soffit[col] is None:
        continue
    for y in range(D.LEDGE_Y, read.soffit[col] + 1):
        if kind(col[0], y, col[1]) is None and any(kind(col[0] + dx, y + dy, col[1] + dz) in COPPER
                                                   for dx, dy, dz in D.AROUND):
            green.append((col[0], y, col[1]))
check("no copper shows indoors: every plate has its board or its iron on the inside", green)
check("a light source sits in a free cell",
      [cell for cell, _level, _rank, _name in D.lights() if c.name(*cell) not in (None, B.LIGHT)])

# --- the dome's skeleton ----------------------------------------------------------------------------
skeleton = D.frame(read)
if skeleton is None:
    print("skip  the dome's skeleton: this dome has no slit to build the two arch girders beside")
else:
    def inside(p):
        """Is the point inside a block of the dressed box (a light source is not one)?"""
        return kind(int(math.floor(p[0])), int(math.floor(p[1])), int(math.floor(p[2]))) is not None

    bars = skeleton.lines()
    buried, in_slit = [], []
    for a, b, half in bars:
        n = max(2, int(math.dist(a, b) / 0.125) + 1)
        for i in range(n + 1):
            p = tuple(a[k] + (b[k] - a[k]) * i / n for k in range(3))
            # a bar may end in what it stands against: its two ends are not asked
            if 0.25 < math.dist(p, a) and 0.25 < math.dist(p, b) and inside(p):
                buried.append(tuple(round(v, 2) for v in p))
            col = (int(math.floor(p[0])), int(math.floor(p[2])))
            if col in read.gap and p[1] > D.BASE_RING[1] + 1:
                in_slit.append(tuple(round(v, 2) for v in p))
    print("the skeleton: %d display entities, %d bars; the arch girders' underside keeps to the line from %s to %s"
          % (len(skeleton.placed), len(bars), *("(%.3f, %.3f)" % (S.DOME_AXIS[0] - z, y) for z, y in skeleton.run())))
    check("no bar of the skeleton runs through a block (the boards, the ring girder's blocks, the piers)", buried)
    check("no bar of the skeleton crosses the open slit", in_slit)
    check("the room's display entities stay within a room's share (%d)" % S.BUDGET_PER_ROOM,
          [placed] if placed > S.BUDGET_PER_ROOM else [])
    scope = D._other("machines", "scope")
    if scope is None:
        print("skip  the telescope's sweep: machines/scope is not in the tree")
    else:
        (sx, sy, sz), reach = scope.sweep()
        check("the skeleton stays clear of everywhere the telescope can point (machines/scope.sweep)",
              [tuple(round(v, 2) for v in p) for a, b, half in bars for p in (a, b)
               if math.dist(p, (sx, sy, sz)) < reach + half])
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots.json"), encoding="utf-8") as fh:
            v8 = next(shot for shot in json.load(fh) if shot["name"] == "v8")
        at, look = scope.v8()
        check("the camera of V8 stands and looks where machines/scope says",
              [name for name, got, want in (("pos", v8["pos"], at), ("look_at", v8["look_at"], look))
               if math.dist(got, want) > 0.05])

print()
print("FAILED: " + "; ".join(failed) if failed else "all checks pass")
sys.exit(1 if failed else 0)
