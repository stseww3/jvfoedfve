"""python -m scenes.obs_int_timeroom: the block light where one walks in the room, by numbers.

The light line's rule for a way (c331, 11-16): at a station the cell of the foot or the cell of
the head has 5 or more; no more than three stations in a row have less; none has 0. A station
here is a cell of the floor one steps on. The ways are the room's own: from the door up the long
axis to the stool before the console, in both files of cells, and from the axis to each place
where somebody works.
"""
import sys

from scenes.obs.interiors import timeroom as T
from scenes.obs.sky import _lightkit

from . import build

ENOUGH = 5
RUN = 3                 # stations in a row that may have less


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
    wrong, run = [], 0
    for i, pair in enumerate(levels):
        best = max(pair)
        if best == 0:
            wrong.append(f"station {i} has no light")
        run = run + 1 if best < ENOUGH else 0
        if run == RUN + 1:
            wrong.append(f"stations {i - RUN}.. are more than {RUN} in a row under {ENOUGH}")
    return wrong


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
    print(f"ways: {'PASS' if not bad else 'FAIL'} (foot/head at each cell; {ENOUGH} or more at one of them, "
          f"at most {RUN} in a row under it, none at 0)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
