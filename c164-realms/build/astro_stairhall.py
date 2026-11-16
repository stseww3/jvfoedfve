"""A scratch tool of astro (c360) for sky/lights: the grand stair hall's ways and the caged lamps
that would light them. Never merged anywhere; it only reads the master scene.

    cd build && python astro_stairhall.py dump <out.json>
        builds the master scene once and writes what a search needs: the blocks of the hall's
        box, the block light there as it stands, the sources sky/lights placed, the display
        entities in the box

    cd build && python astro_stairhall.py try <lamps.json> <stations.json> [--out file]
        builds the master scene, adds the lamps of the file as sky/lights would (a lamp on the
        wall block [x, y, z, facing, level], its source in the cell before it; or a pendant
        ["hang", x, y, z, level], its source in that cell) and prints the light before and after
        at the cells of the file and at the walk-through's stations in the hall
"""
import json
import sys

from artkit import blocks as AB

from scenes import obs
from scenes.obs.common import blocks as B
from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import lights
from scenes.obs_sky_lights import ways

LO, HI = (-14, -3, -9), (20, 17, 9)         # the stair hall, the star hall as far as the entrance


def _inside(cell):
    return all(LO[i] <= cell[i] <= HI[i] for i in range(3))


def dump(path):
    canvas = obs.build()
    light, _tops, placed = ways.survey(canvas)
    names, index, cells = [], {}, []
    for cell, state in canvas.b.items():
        if not _inside(cell):
            continue
        if state not in index:
            index[state] = len(names)
            names.append(state)
        cells.append([cell[0], cell[1], cell[2], index[state]])
    out = {
        "lo": LO, "hi": HI,
        "states": names,
        "stops": [bool(L._stops_light(s)) for s in names],
        "source": [AB.name_of(s) == B.LIGHT for s in names],
        "cells": cells,
        "light": [[c[0], c[1], c[2], v] for c, v in light.items() if _inside(c)],
        "placed": [[c[0], c[1], c[2], level, why] for c, (level, why) in placed.items() if _inside(c)],
        "entities": [[round(x, 3), round(y, 3), round(z, 3), str(nbt)[:260]]
                     for x, y, z, nbt in canvas.entities
                     if LO[0] <= x <= HI[0] + 1 and LO[1] <= y <= HI[1] + 1 and LO[2] <= z <= HI[2] + 1],
        "report": {k: v for k, v in lights.report(canvas).items() if k in ("notes", "problems", "ways", "stair")},
    }
    with open(path, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"{len(cells)} blocks, {len(out['light'])} lit cells, {len(out['placed'])} sources, "
          f"{len(out['entities'])} entities in the box {LO}..{HI}")
    return 0


def attempt(lamps_path, stations_path, out_file=None):
    with open(lamps_path) as f:
        plan = json.load(f)
    canvas = obs.build()
    before, tops, placed = ways.survey(canvas)
    text = []
    for entry in plan["lamps"]:
        if entry[0] == "hang":                      # a pendant: its source cell, hung from the first block over it
            _, x, y, z, level = entry
            cell, up = (x, y, z), y + 1
            while up <= HI[1] and not canvas.has(x, up, z):
                up += 1
            hanger = canvas.b.get((x, up, z))
            solid = hanger is not None and bool(L._stops_light(hanger))
            free = not canvas.has(*cell) or cell in placed
            text.append(f"pendant in {cell}, level {level}: hangs {up - y - 1} cells under {(x, up, z)} "
                        f"({AB.name_of(hanger) if hanger else 'nothing'}: {'a whole block' if solid else 'NOT A WHOLE BLOCK'}), "
                        f"its cell {'is free' if free else 'IS TAKEN by ' + str(canvas.b.get(cell))}")
            if solid and free:
                canvas.set(cell[0], cell[1], cell[2], L.light(level))
            continue
        x, y, z, facing, level = entry
        dx, dz = lights.FACE[facing]
        wall, cell = (x, y, z), (x + dx, y, z + dz)
        state = canvas.b.get(wall)
        solid = state is not None and AB.name_of(state) != B.LIGHT
        free = not canvas.has(*cell) or cell in placed
        text.append(f"lamp on {wall} facing {facing}, level {level}: wall {'stands' if solid else 'MISSING'}, "
                    f"the cell {cell} before it {'is free' if free else 'IS TAKEN by ' + str(canvas.b.get(cell))}")
        if solid and free:
            canvas.set(cell[0], cell[1], cell[2], L.light(level))
    after, _tops, _placed = ways.survey(canvas)
    text.append("")
    for name, cells in plan.get("cells", {}).items():
        rows = []
        for x, y, z in cells:
            b = max(before.get((x, y, z), 0), before.get((x, y + 1, z), 0))
            a = max(after.get((x, y, z), 0), after.get((x, y + 1, z), 0))
            rows.append((x, y, z, b, a))
        low = [r for r in rows if r[4] < ways.LIT]
        text.append(f"{name}: {len(rows)} cells; best of feet and head before {min(r[3] for r in rows)}.."
                    f"{max(r[3] for r in rows)}, after {min(r[4] for r in rows)}..{max(r[4] for r in rows)}; "
                    f"under {ways.LIT} after: {len(low)}")
        for x, y, z, b, a in rows:
            text.append(f"    ({x:>3}, {y:>2}, {z:>3})  {b:>2} -> {a:>2}{'   <--' if a < ways.LIT else ''}")
    text.append("")
    for name, cells in plan.get("keep_dark", {}).items():
        rows = [(c, before.get(tuple(c), 0), after.get(tuple(c), 0)) for c in cells]
        text.append(f"{name}: before {max(r[1] for r in rows)} at most, after {max(r[2] for r in rows)} at most; "
                    f"raised: {[(tuple(c), b, a) for c, b, a in rows if a > b]}")
    text.append("")
    cache = {}
    found = [p for p in ways.places(stations_path, canvas, cache)
             if LO[0] <= p[2][0] <= 3 and abs(p[2][2]) <= 6 and p[2][1] <= 13]
    for name, stretch, (x, y, z) in found:
        cx, cy, cz = int(x // 1), int((y + 1e-6) // 1), int(z // 1)
        b = (before.get((cx, cy, cz), 0), before.get((cx, cy + 1, cz), 0))
        a = (after.get((cx, cy, cz), 0), after.get((cx, cy + 1, cz), 0))
        text.append(f"  {name:<8} {x:>7.2f} {y:>6.2f} {z:>7.2f}  feet/head {b[0]}/{b[1]} -> {a[0]}/{a[1]}  "
                    f"{ways.verdict(*b)} -> {ways.verdict(*a)}")
    print("\n".join(text))
    if out_file:
        with open(out_file, "w") as f:
            f.write("\n".join(text) + "\n")
    return 0


def main(argv):
    if len(argv) >= 2 and argv[0] == "dump":
        return dump(argv[1])
    if len(argv) >= 3 and argv[0] == "try":
        out = argv[argv.index("--out") + 1] if "--out" in argv else None
        return attempt(argv[1], argv[2], out)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
