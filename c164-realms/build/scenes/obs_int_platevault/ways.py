"""The light on the plate vault's ways, read as tools/darkfloor.py reads the master scene's:

    env PYTHONPATH=build python -m scenes.obs_int_platevault.ways      (from c164-realms/, on a worker node)

Builds the box scene, lets tools/walkreach.py find every place a person stands in the room coming
in by the door (on foot or with a hop: the tops of the darkroom's benches are such places), and
takes the block light there from sky/_lightkit.levels: the better of the cell of the feet and the
cell of the head. The line (cr2, 11-16): a floor cell has 5 or more, the threshold 7; the darkroom
end is the darkest place of the building and has no more than 6.

Prints the room as a plan, a cell a number, then what sky/lights made of the sources the room
asked for, and PASS or FAIL in the last line. Ends with 0 either way.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "tools")))
import walkreach as W  # noqa: E402

from scenes.obs.interiors import platevault as T  # noqa: E402
from scenes.obs.sky import _lightkit as L  # noqa: E402
from scenes.obs.sky import lights  # noqa: E402

from . import build  # noqa: E402

FLOOR = 5               # the line of a floor cell
STEP = 7                # of a threshold
DARK_TOP = 6            # what the darkroom end keeps under
THRESHOLD = (T.HALL_DOOR[0], T.FEET, T.HALL_DOOR[1])


def in_room(cell):
    return T.X0 <= cell[0] <= T.X1 and T.HALL_DOOR[1] <= cell[2] <= T.Z1 and T.FEET <= cell[1] <= T.TOP


def measure():
    """(the canvas, {cell: (how it is reached, its light)}) for every cell of the room a person stands in."""
    canvas = build()
    cells = canvas.b
    lo = tuple(min(c[i] for c in cells) for i in range(3))
    hi = tuple(max(c[i] for c in cells) for i in range(3))
    light = L.levels(canvas, lo, hi)
    reach = W.World(cells).reach((T.AXIS_X, float(T.FEET), T.Z0 + 0.5))
    rows = {}
    for (i, j, hq), how in reach.kind.items():
        if how not in ("walk", "hop") or i % 2 == 0 or j % 2 == 0:
            continue
        cell = (i // 2, int(math.floor(hq / float(W.Q) + 1e-6)), j // 2)
        if not in_room(cell) or (cell in rows and rows[cell][0] == "walk"):
            continue
        rows[cell] = (how, max(light.get(cell, 0), light.get((cell[0], cell[1] + 1, cell[2]), 0)))
    return canvas, rows


def need(cell):
    return STEP if cell == THRESHOLD else FLOOR


def plan(rows, y):
    out = [f"feet at {y}:", "        " + " ".join(f"{x:2d}" for x in range(T.X0, T.X1 + 1))]
    for z in range(T.HALL_DOOR[1], T.Z1 + 1):
        out.append(f"  z {z:2d}  " + " ".join(f"{rows[(x, y, z)][1]:2d}" if (x, y, z) in rows else " ."
                                              for x in range(T.X0, T.X1 + 1)))
    return out


def main():
    canvas, rows = measure()
    for y in sorted({c[1] for c in rows}):
        print("\n".join(plan(rows, y)))
    low = sorted(c for c, (_, v) in rows.items() if v < need(c))
    dark_end = {c: v for c, (_, v) in rows.items() if c[2] >= T.WALL_Z}
    stacks = {c: v for c, (_, v) in rows.items() if c[2] < T.WALL_Z and c != THRESHOLD}
    over = sorted(c for c, v in dark_end.items() if v > DARK_TOP)
    hops = sum(1 for how, _ in rows.values() if how == "hop")
    print(f"standing places: {len(rows)} ({hops} of them reached with a hop)")
    print(f"the threshold {THRESHOLD}: {rows[THRESHOLD][1] if THRESHOLD in rows else 'nobody stands there'} (line {STEP})")
    if stacks:
        print(f"the stacks: {min(stacks.values())} to {max(stacks.values())} (line {FLOOR})")
    if dark_end:
        print(f"the darkroom end: {min(dark_end.values())} to {max(dark_end.values())} (line {FLOOR}, no more than {DARK_TOP})")
    print(f"under the line: {len(low)}" + (f": {low[:24]}{' ...' if len(low) > 24 else ''}" if low else ""))
    print(f"over {DARK_TOP} in the darkroom end: {len(over)}" + (f": {over[:24]}" if over else ""))

    r = lights.report(canvas)
    mine = {c: v for c, v in r["placed"].items() if in_room(c)}
    by_why = {}
    for c, (level, why) in sorted(mine.items()):
        by_why.setdefault((why, level), []).append(c)
    print(f"sources in the room: {len(mine)}")
    for (why, level), where in sorted(by_why.items()):
        print(f"  {why} {level}: " + " ".join(f"({x},{y},{z})" for x, y, z in where))
    odd = 0
    for key, at in (("rejected", 0), ("capped", 0), ("merged", 0), ("moved", 0)):
        for entry in r[key]:
            if in_room(entry[at]):
                odd += 1
                print(f"  {key}: {entry}")
    ok = not low and not over and THRESHOLD in rows and not odd
    print("ways: " + ("PASS" if ok else "FAIL"))


if __name__ == "__main__":
    main()
