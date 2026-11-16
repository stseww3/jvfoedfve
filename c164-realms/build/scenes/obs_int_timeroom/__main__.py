"""python -m scenes.obs_int_timeroom: the block light of the room by numbers.

Where one walks. The line of the finish (A0, 11-16 10:43; the light line, c331): at every cell one
can stand on, the cell of the foot or the cell of the head has 5 or more, a threshold as well. A
station here is a cell of the floor one steps on. The ways are the room's own: from the door up
the long axis to the stool before the console, in both files of cells, and from the axis to each
place where somebody works. The rest of the floor is counted over the whole building by
tools/darkfloor.py (c164-sound's), with the lamps the light line adds in this room.

The order of the lights (review cr4, 11-16): the instrument wall is the lightest thing of the
room, the rating bench comes next, the message desk beside V10's camera last; the floor at the
foot of the console is lighter than the floor by the door, which is V10's foreground.
"""
import sys

from scenes.obs.interiors import timeroom as T
from scenes.obs.sky import _lightkit

from . import build

ENOUGH = 5
WALL_LEAST = 8          # the least a face of the instrument wall has, from the shelf up to the cornice
DESK_MOST = 8           # the most the message desk has, and what lies on it
FLOOR_STEP = 3          # levels the floor at the foot of the console has over the floor by the door. Not more: every
#                         cell by the door has to have 5, and 12 is the top indoors


def ways():
    """{name: [(x, z), ...]}: the cells of each way, in the order they are walked."""
    door, stool = T.Z1 + 1, T.CONSOLE_Z + 2
    desk, bench = int(T.DESK_Z // 1), int(T.BENCH_Z // 1)
    out = {f"door to console, x {x}": [(x, z) for z in range(door, stool - 1, -1)] for x in T.DOOR_X}
    out["axis to the message desk"] = [(x, desk) for x in range(T.DOOR_X[1], T.DESK_LIGHT[0])]
    out["axis to the rating bench"] = [(x, bench) for x in range(T.DOOR_X[0], T.BENCH_LIGHT[0], -1)]
    out["door to the world clocks"] = ([(x, T.Z1 - 1) for x in range(T.DOOR_X[0], T.X0 + 1, -1)]
                                       + [(T.X0 + 1, z) for z in range(T.Z1 - 1, T.CLOCK_Z[0] - 1, -1)])
    out["before the card cabinets"] = [(x, T.Z1 - 1) for x in range(T.X0 + 2, T.DOOR_X[0])]
    return out


def faults(levels):
    """What a way's levels [(foot, head), ...] break of the rule: sentences."""
    return [f"station {i} has {max(pair)}, under {ENOUGH}" for i, pair in enumerate(levels) if max(pair) < ENOUGH]


def mean(values):
    return sum(values) / float(len(values))


def order(light):
    """The order of the lights: (the lines to print, what is out of order). The faces of the
    instrument wall take the light of the cells before them; a floor that of the cells over it;
    what lies on a desk that of the desk's own cell."""
    def at(x, y, z):
        return light.get((x, y, z), 0)

    xs = range(T.RACK_X[0], T.RACK_X[1] + 1)
    rows = {y: [at(x, y, T.CONSOLE_Z) for x in xs] for y in range(T.CORNICE_Y - 1, T.SILL - 1, -1)}
    lines = [f"wall, row {y}: " + " ".join(f"{v:2d}" for v in row) for y, row in rows.items()]
    wall = [v for row in rows.values() for v in row]
    foot = [at(x, T.FEET, z) for z in (T.CONSOLE_Z + 1, T.CONSOLE_Z + 2) for x in range(T.CONSOLE_X[0] - 1, T.CONSOLE_X[1] + 2)]
    door = [at(x, T.FEET, z) for z in range(T.Z1 - 3, T.Z1) for x in range(T.DOOR_X[0], T.DOOR_X[1] + 2)]     # V10's lower left
    bench = max(at(T.X0, T.FEET, int(T.BENCH_Z // 1) + dz) for dz in (0, 1))
    desk = max(at(T.X1, T.FEET, int(T.DESK_Z // 1) + dz) for dz in (-1, 0, 1))
    lines.append(f"wall {mean(wall):.1f} (least {min(wall)}), rating bench {bench}, message desk {desk}; "
                 f"floor at the console {mean(foot):.1f}, by the door {mean(door):.1f}")
    wrong = []
    if min(wall) < WALL_LEAST:
        wrong.append(f"a face of the instrument wall has {min(wall)}, under {WALL_LEAST}")
    if not mean(wall) > bench > desk:
        wrong.append(f"the wall ({mean(wall):.1f}), the rating bench ({bench}) and the message desk ({desk}) are not in that order")
    if desk > DESK_MOST:
        wrong.append(f"the message desk has {desk}, over {DESK_MOST}")
    if mean(foot) - mean(door) < FLOOR_STEP:
        wrong.append(f"the floor at the console ({mean(foot):.1f}) is not {FLOOR_STEP} over the floor by the door ({mean(door):.1f})")
    return lines, wrong


def main():
    c = build()
    light = _lightkit.levels(c, (T.X0 - 2, T.FEET - 2, T.Z0 - 2), (T.X1 + 2, T.TOP + 2, T.Z1 + 4))
    bad = 0
    for name, cells in ways().items():
        levels = [(light.get((x, T.FEET, z), 0), light.get((x, T.FEET + 1, z), 0)) for x, z in cells]
        wrong = faults(levels)
        bad += len(wrong)
        print(f"{name}: " + " ".join(f"{foot}/{head}" for foot, head in levels))
        for line in wrong:
            print(f"    FAIL {line}")
    lines, wrong = order(light)
    for line in lines:
        print(line)
    for line in wrong:
        print(f"    FAIL {line}")
    print(f"ways: {'PASS' if not bad else 'FAIL'} (foot/head at each cell; {ENOUGH} or more at one of them)")
    print(f"order: {'PASS' if not wrong else 'FAIL'} (the wall, the rating bench, the message desk; the floor at the "
          f"console {FLOOR_STEP} over the floor by the door)")
    return 1 if bad or wrong else 0


if __name__ == "__main__":
    sys.exit(main())
