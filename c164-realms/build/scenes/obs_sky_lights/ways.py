"""python -m scenes.obs_sky_lights.ways <file.json> [...] (in build/): the light on the ways a
visitor walks. Builds the master scene once (every line, with the switches as they stand) and
reads the block light where he stands:

    a station table of the walk-through (tools/walk.py: {"stations": [{"id", "stretch", "feet"}]})
        every station, in the cell of the feet and the cell of the head;
    a route file ({"prefix", "stretches": [{"id", "points": [{"at", "hop"}]}]})
        a place every STEP blocks along the way, feet put on the floor found near the line.

Block light is all there is under a roof; under the sky the night gives its own (a place is
under the sky when no block of any kind is over its head). A place is

    lit     LIT or more at the feet or at the head: one sees where one steps
    dim     under LIT, over nothing
    dark    no block light at all

and a way is walked from lit place to lit place: what is counted against it is a dark place under
a roof, and a run of dim ones longer than RUN. With --out <file> the table is written there too.
The whole master scene is built: run it on a node. Ends with 1 when a way has a dark place under
a roof.
"""
import json
import math
import statistics
import sys

from artkit import blocks as AB

from scenes import obs
from scenes.obs.common import blocks as B
from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import lights

LIT = 5                     # the third rank's lowest: what a caged lamp leaves two cells from its glass
STEP = 4.0                  # as the walk-through steps
RUN = 3                     # dim places in a row that a way may have before it counts as unlit
SEEK = (0, 1, -1, 2, -2, 3, -3)     # rows tried for the floor near a route's line, nearest first


def _stops(canvas, cache, cell):
    state = canvas.b.get(cell)
    if state is None:
        return False
    if state not in cache:
        cache[state] = L._stops_light(state)
    return cache[state]


def _floor(canvas, cache, x, y, z):
    """The level feet find near y in that column: free for two rows, something under it."""
    cx, cz = int(math.floor(x)), int(math.floor(z))
    for d in SEEK:
        row = int(math.floor(y)) + d
        if canvas.b.get((cx, row - 1, cz)) is not None and not _stops(canvas, cache, (cx, row, cz)) \
                and not _stops(canvas, cache, (cx, row + 1, cz)):
            return float(row)
    return float(y)


def places(path, canvas, cache):
    """[(name, stretch, (x, y, z) of the feet)] of a station table or of a route file."""
    with open(path) as f:
        data = json.load(f)
    if "stations" in data:
        return [(s["id"], s.get("stretch", "?"), tuple(s["feet"])) for s in data["stations"]]
    out, last = [], None
    for stretch in data.get("stretches", ()):
        n = 0
        for p in stretch.get("points", ()):
            at = tuple(float(v) for v in p["at"])
            steps = [at]
            if last is not None and not p.get("hop"):
                gap = math.dist(last, at)
                k = max(1, int(math.ceil(gap / STEP)))
                steps = [tuple(last[i] + (at[i] - last[i]) * j / k for i in range(3)) for j in range(1, k + 1)]
            for x, y, z in steps:
                n += 1
                out.append((f"{data.get('prefix', 'way')}-{stretch['id']}{n:02d}", stretch["id"],
                            (round(x, 2), _floor(canvas, cache, x, y, z), round(z, 2))))
            last = at
    return out


def survey(canvas):
    """What the table reads, taken once: (the block light of every cell that has any, the highest
    block of every column, a light source not counted, the sources sky/lights placed)."""
    source, tops = {}, {}
    lo, hi = [10 ** 9] * 3, [-10 ** 9] * 3
    for cell, state in canvas.b.items():
        for i in range(3):
            if cell[i] < lo[i]:
                lo[i] = cell[i]
            if cell[i] > hi[i]:
                hi[i] = cell[i]
        if state not in source:
            source[state] = AB.name_of(state) == B.LIGHT
        if not source[state] and cell[1] > tops.get((cell[0], cell[2]), -10 ** 9):
            tops[(cell[0], cell[2])] = cell[1]
    return L.levels(canvas, tuple(lo), tuple(hi)), tops, lights.report(canvas)["placed"]


def table(found, light, tops, placed):
    """One row for every place: (name, stretch, feet, the light at the feet, at the head, under the
    sky or not, the nearest source as (distance, level, why, cell) or None)."""
    rows = []
    for name, stretch, (x, y, z) in found:
        cx, cy, cz = int(math.floor(x)), int(math.floor(y + 1e-6)), int(math.floor(z))
        feet, head = light.get((cx, cy, cz), 0), light.get((cx, cy + 1, cz), 0)
        sky = tops.get((cx, cz), -10 ** 9) <= cy + 1
        near = min(((abs(c[0] - cx) + abs(c[1] - cy - 1) + abs(c[2] - cz), level, why, c)
                    for c, (level, why) in placed.items()), default=None)
        rows.append((name, stretch, (x, y, z), feet, head, sky, near))
    return rows


def verdict(feet, head):
    best = max(feet, head)
    return "lit" if best >= LIT else "dim" if best > 0 else "dark"


def lines(rows, title):
    out, bad = [f"{title}: {len(rows)} places"], 0
    by = {}
    for row in rows:
        by.setdefault(row[1], []).append(row)
    for stretch, group in by.items():
        best = [max(r[3], r[4]) for r in group]
        said = [verdict(r[3], r[4]) for r in group]
        roofed = [not r[5] for r in group]
        dark = [r for r, v, under in zip(group, said, roofed) if v == "dark" and under]
        run = longest = 0
        for v, under in zip(said, roofed):
            run = run + 1 if (v != "lit" and under) else 0
            longest = max(longest, run)
        fault = bool(dark) or longest > RUN
        bad += fault
        out.append(f"  {stretch}: {len(group)} places, {sum(roofed)} under a roof; light {min(best)}..{max(best)}, "
                   f"median {statistics.median(best):g}; lit {said.count('lit')}, dim {said.count('dim')}, "
                   f"dark {said.count('dark')} ({len(dark)} under a roof); longest run unlit under a roof "
                   f"{longest}{'   <-- unlit' if fault else ''}")
    out.append("")
    for name, stretch, (x, y, z), feet, head, sky, near in rows:
        said = verdict(feet, head)
        where = "sky " if sky else "roof"
        src = f"nearest source {near[1]} {near[2]} at {near[3]}, {near[0]} cells" if near else "no source"
        mark = "" if said == "lit" else "  <--" if not sky else "  (sky)"
        out.append(f"  {name:<10} {x:>7.2f} {y:>6.2f} {z:>7.2f}  {where}  feet {feet:>2} head {head:>2}  {said:<4}{mark}"
                   + ("" if said == "lit" else f"   {src}"))
    return out, bad


def main(argv):
    out_file = None
    if "--out" in argv:
        i = argv.index("--out")
        out_file = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if not argv:
        print(__doc__)
        return 2
    canvas = obs.build()
    light, tops, placed = survey(canvas)
    cache, text, bad = {}, [], 0
    for path in argv:
        rows = table(places(path, canvas, cache), light, tops, placed)
        more, n = lines(rows, path)
        text += more + [""]
        bad += n
    text.append(f"ways with a dark place under a roof or more than {RUN} unlit places in a row: {bad}")
    print("\n".join(text))
    if out_file:
        with open(out_file, "w") as f:
            f.write("\n".join(text) + "\n")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
