"""Writes shots.json of this test scene and prints the lamps of the site as they are in this tree:
which stand and which were left out, the source the sky line's light tool gave each of them, and
the block light on the floor of the way in, as two plans (the pools are judged by these numbers
before they are judged in a picture):
    python -m scenes.obs_props_lamps_site"""
import json
import math
import os
from collections import Counter

from scenes.obs.common import skeleton as S
from scenes.obs.props import lamps

from . import L, build, shots

try:
    from scenes.obs.sky import lights as SL
except ImportError:         # the sky line's lights are not merged yet
    SL = None

WHY = "props/lamps:"
REACH = 14                  # the brightest source there is lights this many cells


def _near(p, cell):
    """How far a source's cell is from a lamp's point, or None when it cannot be that lamp's: a lamp's
    glowing part is over its foot or under its hanging point, never beside it."""
    d = [cell[i] + 0.5 - p[i] for i in range(3)]
    if max(abs(d[0]), abs(d[2])) > 1.5 or not -3.0 <= d[1] <= 6.0:
        return None
    return math.hypot(*d)


def sources(c, table, left):
    """A line for every lamp of the site that stands: the source it was given, or why it has none."""
    r = SL.report(c)
    out = []
    for group, kind, p, level, _ in table:
        if (group, kind, tuple(p)) in left:
            continue
        mine = [(_near(p, cell), cell, lv) for cell, (lv, why) in r["placed"].items()
                if why.startswith(WHY + kind) and _near(p, cell) is not None]
        text = f"  {group:<8}{kind:<8}{str(tuple(p)):<22}"
        if mine:
            _, cell, lv = min(mine)
            asked = [a for at, a, given, why in r["capped"] if at == cell and why.startswith(WHY + kind)]
            out.append(text + f"source {cell} level {lv}" + (f" (asked {asked[0]})" if asked else ""))
            continue
        said = [reason for cell, _, why, reason in r["rejected"]
                if why.startswith(WHY + kind) and _near(p, cell) is not None]
        out.append(text + "NO SOURCE" + (f": {said[0]}" if said else ""))
    return out


def plan(c, x0, x1, z0, z1, y):
    """The block light in the row of cells y, where feet stand: west to east across, north at the
    top, one hex digit a cell ('.' none, '#' a cell that is taken: a pedestal, a pier, a step)."""
    lv = L.levels(c, (x0 - REACH, y - 1, z0 - REACH), (x1 + REACH, y + REACH, z1 + REACH))
    rows = []
    for z in range(z0, z1 + 1):
        row = ""
        for x in range(x0, x1 + 1):
            if (x, y, z) in lv:
                row += "%x" % lv[x, y, z]
            else:
                row += "#" if c.has(x, y, z) else "."
        rows.append(f"  z {z:>4} {row}")
    return rows


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}")
    c = build()
    left = {(group, kind, tuple(p)) for group, kind, p in getattr(c, "lamps_left_out", [])}
    table = lamps.site_lamps()
    stand = Counter((group, kind) for group, kind, p, _, _ in table if (group, kind, tuple(p)) not in left)
    print("display entities:", c.entity_counts)
    print("lamps of the site that stand:", ", ".join(f"{g} {k} x{n}" for (g, k), n in sorted(stand.items())) or "none")
    for group, kind, p in sorted(left):
        print(f"  left out, nothing to stand on or hang from: {group} {kind} {p}")
    for s in shots():
        x, y, z = (int(v // 1) for v in s["pos"])
        if c.has(x, y, z):
            print(f"  camera {s['name']} is inside a block at {(x, y, z)}: {c.get(x, y, z)}")
    if L is None or SL is None:
        print("the sky line's light tool is not in this tree: no sources to list")
    else:
        print("the lamps' sources:")
        print("\n".join(sources(c, table, left)))
        for line in SL.summary(c):
            if line.startswith(("sources placed", "dressed", "capped", "moved", "merged", "rejected", "PROBLEM")):
                print("  " + line)
        court, low = S.FRONT_COURT, S.LOWER_PLATFORM
        print(f"block light where feet stand on the court (y {S.GROUND}), x {court[0]}..{court[2] + 1}:")
        print("\n".join(plan(c, court[0], court[2] + 1, -12, 13, S.GROUND)))
        print(f"block light where feet stand on the lower platform (y {S.LOWER_GROUND}), x {low[0]}..{low[2]}:")
        print("\n".join(plan(c, low[0], low[2], -20, 14, S.LOWER_GROUND)))
