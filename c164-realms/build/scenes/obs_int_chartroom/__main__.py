"""python -m scenes.obs_int_chartroom [master]: the block light in the chart room, by numbers.

For the box scene, or with `master` for the room where it stands in the master scene:

  the sources    the invisible sources in and about the room: the room's own offers as the light
                 line settled them, and the light line's at the lit windows
  two plans      the level in the row of the feet (what the floor shows) and in the row over it
                 (what a head stands in): x across the page from west to east, z down it from the
                 door wall to the bookcase, one hex digit a cell
  the models     the level in the cell every display entity of the room is held in: a model takes
                 the light of that one cell, whatever its size
  the ways       the light line's rule for a way (c331, 11-16) on the room's own ways: at a station
                 the cell of the foot or of the head has 5 or more, no more than three stations in a
                 row have less, none has 0

The pictures are drawn with the game's own table of brightness; at the game's default setting a
level shows as SHOWN says, which is what a difference between two levels has to be read against.
"""
import math
import re
import sys

from artkit import blocks as AB

from scenes.obs.common import blocks as B
from scenes.obs.interiors import _chartshelves
from scenes.obs.interiors import chartroom as R
from scenes.obs.sky import _lightkit

ENOUGH = 5
RUN = 3                 # stations in a row that may have less
DIGITS = "0123456789abcdef"
REACH = 8               # the light is spread in the room's box and this far round it: the gallery behind the door,
#                         the recesses of the windows


def shown(level, setting=0.5):
    """What a block light of a level shows of a colour at the game's brightness setting (0 moody,
    0.5 the default, 1 bright): the table l / (4 - 3 l), then the setting's lift towards
    1 - (1 - x)^4."""
    l = level / 15.0
    x = l / (4.0 - 3.0 * l)
    return x + setting * ((1.0 - (1.0 - x) ** 4) - x)


def canvas(which):
    if which == "master":
        from scenes import obs
        return obs.build()
    from . import build
    return build()


def ways():
    """{name: [(x, z), ...]}: the cells of each way, in the order they are walked."""
    a, b = R.DOOR_X
    table = min(z for _, _, z in R.TABLE_CELLS)
    front = int(_chartshelves.FRONT_Z) - 1          # the row before the bookcase's rail
    west, east = a - 2, b + 2                       # the aisles: two cells off the table on either hand
    out = {f"door to the table, x {x}": [(x, z) for z in range(R.Z0, table)] for x in (a, b)}
    out["east aisle to the bookcase"] = ([(x, table - 2) for x in range(b + 1, east + 1)]
                                         + [(east, z) for z in range(table - 1, front + 1)])
    out["west aisle to the bookcase"] = ([(x, table - 2) for x in range(a - 1, west - 1, -1)]
                                         + [(west, z) for z in range(table - 1, front + 1)])
    out["before the bookcase"] = [(x, front) for x in range(R.X0 + 1, R.X1)]
    out["east aisle to the desk"] = [(x, int(R.bay_z(R.DESK_BAY))) for x in range(east + 1, R.X1)]
    out["west aisle to the drafting table"] = [(x, int(R.bay_z(R.DRAFT_BAY))) for x in range(west - 1, R.X0, -1)]
    return out


def faults(levels):
    """What a way's levels [(foot, head), ...] break of the rule: sentences."""
    wrong, run = [], 0
    for i, pair in enumerate(levels):
        best = max(pair)
        if best == 0:
            wrong.append(f"station {i} has no light")
        run = run + 1 if best < ENOUGH else 0
        if run == RUN + 1:
            wrong.append(f"stations {i - RUN}.. are more than {RUN} in a row under {ENOUGH}")
    return wrong


def main(argv):
    which = "master" if "master" in argv else "box"
    c = canvas(which)
    lo = (R.X0 - REACH, R.FEET - 2, R.Z0 - REACH)
    hi = (R.X1 + REACH, R.CEIL_Y + 1, R.Z1 + REACH)
    light = _lightkit.levels(c, lo, hi)
    print(f"the chart room in the {which} scene; a level shows at the game's default setting as: "
          + " ".join(f"{n}:{shown(n):.2f}" for n in range(4, 15)))

    print("\nsources in the room and in the cells round it (cell, level):")
    near = [(cell, int(AB.parse(state)[1]["level"])) for cell, state in c.b.items()
            if AB.name_of(state) == B.LIGHT and R.X0 - 2 <= cell[0] <= R.X1 + 2
            and R.FEET - 1 <= cell[1] <= R.CEIL_Y and R.Z0 - 2 <= cell[2] <= R.Z1 + 2]
    for cell, level in sorted(near, key=lambda s: (s[0][2], s[0][0], s[0][1])):
        print(f"  {cell}  {level}")

    for y, what in ((R.FEET, "feet"), (R.FEET + 1, "head")):
        print(f"\nthe row of the {what} (y {y}): x {R.X0}..{R.X1} across, z down")
        for z in range(R.Z0, R.Z1 + 1):
            print(f"  z {z:2d}  " + "".join(DIGITS[light.get((x, y, z), 0)] for x in range(R.X0, R.X1 + 1)))

    print("\nthe models, by the level of the cell each is held in (level, cell, model, its own brightness if it has one):")
    rows = []
    for x, y, z, nbt in c.entities:
        if R.WEST <= x <= R.EAST and R.FEET - 0.5 <= y <= R.CEIL_Y + 0.5 and R.NORTH - 0.5 <= z <= R.SOUTH:
            cell = tuple(int(math.floor(v)) for v in (x, y, z))
            name = re.search(r"c164:([a-z0-9_/]+)", str(nbt))
            own = nbt.get("brightness") if isinstance(nbt, dict) else None
            rows.append((light.get(cell, 0), cell, name.group(1) if name else "?", f"  own {own['block']}" if own else ""))
    for level, cell, name, own in sorted(rows, key=lambda r: (r[0], r[1][2], r[1][0], r[2])):
        print(f"  {level:2d}  {cell}  {name}{own}")

    bad = 0
    print()
    for name, cells in ways().items():
        levels = [(light.get((x, R.FEET, z), 0), light.get((x, R.FEET + 1, z), 0)) for x, z in cells]
        wrong = faults(levels)
        bad += len(wrong)
        print(f"{name}: " + " ".join(f"{foot}/{head}" for foot, head in levels))
        for line in wrong:
            print(f"    FAIL {line}")
    print(f"ways: {'PASS' if not bad else 'FAIL'} (foot/head at each cell; {ENOUGH} or more at one of them, "
          f"at most {RUN} in a row under it, none at 0)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
