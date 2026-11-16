"""Where a visitor walks in the rooms of the walk-in route, and what stands there without a
collision box (display models): maps on walkreach's half-block lattice, the boxes of the models,
the blocks of a few places, and every station of the route whose body would stand in a model.

A body (0.6 x 1.8 x 0.6 on its feet) stands in a model when it meets one of the model's boxes as
the display shows it: every box is tested as the slanted box it is (separating axes), not by the
box round it. What lies no higher than SKIN over the feet is floor finish (a rug, a rail let into
the floor) and is not counted.

Run in c164-realms/ after  walk.py stations ... --canvas <pickle> --out <stations.json>:
    python renders/_wip/m3_rooms.py <pickle> <stations.json>   -> renders/_wip/walkfix/rooms.txt"""
import importlib
import json
import math
import os
import pickle
import sys

sys.path.insert(0, "tools")
sys.path.insert(0, "build")
import walk as WK  # noqa: E402
import walkreach as W  # noqa: E402
from artkit import models as M  # noqa: E402
from scenes.obs.props import _kit as K  # noqa: E402

BODY, TALL, SKIN = 0.3, 1.8, 0.13
ROOMS = (("B the star hall", 0.0, (1.0, -6.0, 17.0, 6.5)),
         ("E the south gallery", 7.0, (-4.5, 2.5, 16.5, 7.0)), ("E the north gallery", 7.0, (-4.5, -6.0, 16.5, -1.5)),
         ("F the time room", 7.0, (2.0, -25.5, 15.0, -4.5)), ("G the chart room", 7.0, (2.0, 6.5, 14.0, 26.0)),
         ("I the dome room", 18.0, (-5.0, -10.5, 15.5, 11.5)), ("J the south end terrace and the small dome", 18.0, (0.0, 24.0, 16.5, 34.5)),
         ("K the north end terrace and the tower's lobby", 18.0, (0.0, -35.0, 17.5, -23.0)),
         ("the clock room", 24.0, (9.0, -34.0, 17.5, -26.0)),
         ("L the engine hall", -6.0, (68.0, 16.5, 89.5, 41.0)), ("M the meridian hut", 0.0, (30.0, -35.0, 41.0, -20.0)),
         ("N the plate vault", 0.0, (1.0, 3.5, 15.0, 27.0)), ("P the battery room", 0.0, (1.0, -25.5, 15.0, -2.5)))
BLOCKS = (("the engine hall's east side", (82, -6, 24), (89, -4, 31)),
          ("the tower: the lobby, the shaft, the clock room", (10, 18, -33), (16, 26, -27)),
          ("the small dome", (8, 18, 27), (15, 19, 33)),
          ("the dome room's south door", (10, 18, 9), (14, 19, 11)), ("the dome room's north door", (10, 18, -10), (14, 19, -8)))
SHAFT = (10, -33, 16, -27)                  # the tower: every height a person stands at in these columns
out = []


def say(text=""):
    out.append(text)


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(getattr(v, "value", 0.0))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


UNIT = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def solid_of(entity, models):
    """(name, lo, hi, boxes) of a display entity as the scene shows it: the box round all of it and
    every box of its model as (centre, three half edges, lo, hi) in the world."""
    x, y, z, nbt = entity[0], entity[1], entity[2], entity[3]
    try:
        name = nbt["item"]["components"]["minecraft:item_model"].split(":", 1)[1]
    except (KeyError, TypeError, IndexError):
        return None
    model = models.get(name)
    if model is None:
        return name, None, None, None
    t = nbt["transformation"]
    s = [num(v) for v in t["scale"]]
    qi = [num(v) for v in t["left_rotation"]]
    q = (-qi[0], qi[1], -qi[2], qi[3])
    yaw = num(nbt["Rotation"][0]) - 180.0

    def shown(v):
        return K.turn(yaw, M._qrot(q, [v[i] * s[i] / 16.0 for i in range(3)]))

    boxes = []
    for p in model.parts:
        c = [(p["lo"][i] + p["hi"][i]) / 2.0 for i in range(3)]
        h = [(p["hi"][i] - p["lo"][i]) / 2.0 for i in range(3)]
        own = p["rot"][0] if p["rot"] else M.IDENT
        d = shown([c[i] - model.anchor[i] for i in range(3)])
        centre = (x + d[0], y + d[1], z + d[2])
        edges = tuple(tuple(shown(M._qrot(own, [h[i] if k == i else 0.0 for k in range(3)]))) for i in range(3))
        r = [sum(abs(e[k]) for e in edges) for k in range(3)]
        boxes.append((centre, edges, tuple(centre[k] - r[k] for k in range(3)), tuple(centre[k] + r[k] for k in range(3))))
    lo = [min(b[2][k] for b in boxes) for k in range(3)]
    hi = [max(b[3][k] for b in boxes) for k in range(3)]
    return name, lo, hi, boxes


def _apart(centre, edges, bc, bh):
    """True when a plane parts the slanted box (centre, half edges) from the upright box (bc, half bh)."""
    d = (centre[0] - bc[0], centre[1] - bc[1], centre[2] - bc[2])
    axes = list(UNIT) + [_cross(edges[1], edges[2]), _cross(edges[2], edges[0]), _cross(edges[0], edges[1])]
    axes += [_cross(e, u) for e in edges for u in UNIT]
    for a in axes:
        size = math.sqrt(_dot(a, a))
        if size < 1e-12:
            continue
        mine = sum(abs(_dot(a, e)) for e in edges)
        body = abs(a[0]) * bh[0] + abs(a[1]) * bh[1] + abs(a[2]) * bh[2]
        if abs(_dot(a, d)) > mine + body - 1e-6 * size:
            return True
    return False


class Solids:
    """The display models of the scene, asked by where a body stands."""

    def __init__(self, solids):
        self.solids = solids
        self.by_cell = {}
        for k, (_, lo, hi, _) in enumerate(solids):
            for cx in range(math.floor(lo[0] - BODY), math.floor(hi[0] + BODY) + 1):
                for cz in range(math.floor(lo[2] - BODY), math.floor(hi[2] + BODY) + 1):
                    self.by_cell.setdefault((cx, cz), []).append(k)

    def hits(self, x, feet, z):
        """The names of the models a person standing at the point stands in."""
        y0, y1 = feet + SKIN, feet + TALL
        bc, bh = (x, (y0 + y1) / 2.0, z), (BODY, (y1 - y0) / 2.0, BODY)
        found = []
        for k in self.by_cell.get((math.floor(x), math.floor(z)), ()):
            name, lo, hi, boxes = self.solids[k]
            if lo[0] >= x + BODY or hi[0] <= x - BODY or lo[2] >= z + BODY or hi[2] <= z - BODY or lo[1] >= y1 or hi[1] <= y0:
                continue
            for centre, edges, blo, bhi in boxes:
                if blo[0] >= x + BODY or bhi[0] <= x - BODY or blo[2] >= z + BODY or bhi[2] <= z - BODY or blo[1] >= y1 or bhi[1] <= y0:
                    continue
                if not _apart(centre, edges, bc, bh):
                    found.append(name)
                    break
        return found


def blocks(cells, what, a, b):
    """The blocks of a box, a layer a level, with a letter for every kind."""
    say(f"== the blocks of {what}: x {a[0]} .. {b[0]} across, z {a[2]} .. {b[2]} down")
    letters, names = {}, []
    for yy in range(a[1], b[1] + 1):
        say(f"   y {yy}:   x " + "".join(str(abs(xx) % 10) for xx in range(a[0], b[0] + 1)))
        for zz in range(a[2], b[2] + 1):
            row = []
            for xx in range(a[0], b[0] + 1):
                state = cells.get((xx, yy, zz))
                if state is None or str(state).split("[")[0].split(":")[-1] in ("air", "cave_air"):
                    row.append(".")
                    continue
                state = str(state).replace("minecraft:", "")
                if state not in letters:
                    letters[state] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"[len(names) % 62]
                    names.append(state)
                row.append(letters[state])
            say(f"      z {zz:4d}  " + "".join(row))
    for state in names:
        say(f"      {letters[state]} = {state[:150]}")


def main():
    canvas, table_path = sys.argv[1], sys.argv[2]
    with open(canvas, "rb") as fh:
        kept = pickle.load(fh)
    cells, entities = kept["b"], kept["entities"]
    models = importlib.import_module("scenes.obs").build_models()
    solids, unknown = [], {}
    for e in entities:
        got = solid_of(e, models)
        if got is None:
            continue
        if got[1] is None:
            unknown[got[0]] = unknown.get(got[0], 0) + 1
        else:
            solids.append(got)
    inside = Solids(solids)
    say(f"{len(entities)} entities, {len(solids)} display models, {sum(len(s[3]) for s in solids)} boxes"
        + (f"; no model for {unknown}" if unknown else ""))
    route = json.load(open("plan/reviews/walk/in-route.json"))
    feet, source = WK.feet_finder(cells)
    pts = [p["at"] for s in route["stretches"] for p in s["points"]]
    bounds = (math.floor(min(p[0] for p in pts)) - WK.MARGIN, math.floor(min(p[2] for p in pts)) - WK.MARGIN,
              math.floor(max(p[0] for p in pts)) + WK.MARGIN, math.floor(max(p[2] for p in pts)) + WK.MARGIN)
    x, y, z = pts[0]
    reach = W.reach_of(cells, (x, feet(x, z, y), z), bounds)
    world = reach.world
    for name, level, (x0, z0, x1, z1) in ROOMS:
        say()
        say(f"== {name}: level {level:g}; a column every half block from x {x0:g} to {x1:g} (| marks whole x), rows z {z0:g} .. {z1:g}. "
            "o a place on the level walked to from the route's first station, x the same where the body stands in a display model, "
            "s / X the same two for a place nobody gets to from there on foot (the roofs, a shut room), h by a jump only, f by a drop, "
            "u/d a place half a block or more over/under the level, . nobody stands")
        xs = [x0 + 0.5 * k for k in range(int(round((x1 - x0) * 2)) + 1)]
        say("        " + "".join(("|" if abs(v - round(v)) < 1e-9 else " ") for v in xs))
        say("        " + "".join((str(int(abs(round(v))) % 10) if abs(v - round(v)) < 1e-9 else " ") for v in xs))
        seen = {}
        for k in range(int(round((z1 - z0) * 2)) + 1):
            zz = z0 + 0.5 * k
            row = []
            for xx in xs:
                i, j = world.lattice(xx, zz)
                mark = "."
                for top, _ in world.stand(i, j):
                    node = (i, j, int(round(top * W.Q)))
                    if abs(top - level) > 1.0 + 1e-6:
                        continue
                    kind = reach.kind.get(node, "s")
                    if abs(top - level) > 0.26:
                        mark = "u" if top > level else "d"
                    elif kind in ("walk", "s"):
                        found = inside.hits(xx, top, zz)
                        for n in found:
                            seen[n] = seen.get(n, 0) + 1
                        mark = ("x" if found else "o") if kind == "walk" else ("X" if found else "s")
                    else:
                        mark = kind[0]
                    if abs(top - level) <= 0.26:
                        break
                row.append(mark)
            say(f"{zz:7.1f} " + "".join(row))
        say("-- the models a body stands in somewhere on this map (places): "
            + (", ".join(f"{n} ({c})" for n, c in sorted(seen.items())) or "none"))
        say(f"-- the display models that reach into a body's height there (feet {level:g} to {level + TALL:g}; the box round each):")
        rows = []
        for mname, lo, hi, _ in solids:
            if lo[0] < x1 + 0.5 and hi[0] > x0 - 0.5 and lo[2] < z1 + 0.5 and hi[2] > z0 - 0.5 and lo[1] < level + TALL and hi[1] > level + SKIN:
                rows.append((round(lo[2], 2), f"   {mname:34s} x {lo[0]:6.2f} .. {hi[0]:6.2f}   z {lo[2]:6.2f} .. {hi[2]:6.2f}   y {lo[1]:5.2f} .. {hi[1]:5.2f}"))
        for _, line in sorted(rows):
            say(line)
    say()
    for what, a, b in BLOCKS:
        blocks(cells, what, a, b)
    say("== the tower: where a person stands in every column (x, z): feet heights between 17 and 32")
    x0, z0, x1, z1 = SHAFT
    for zc in range(z0, z1 + 1):
        row = []
        for xc in range(x0, x1 + 1):
            i, j = world.lattice(xc + 0.5, zc + 0.5)
            tops = [f"{top:g}" for top, _ in world.stand(i, j) if 17.0 <= top <= 32.0]
            row.append(f"x{xc}: " + (",".join(tops) or "-"))
        say(f"   z {zc}: " + "  ".join(row))
    say()
    table = json.load(open(table_path))
    say("== the stations of the route whose body stands in a display model (every stretch)")
    n = 0
    for s in table["stations"]:
        fx, fy, fz = s["feet"]
        if s.get("floor") is False:
            continue
        found = inside.hits(fx, fy, fz)
        if found:
            n += 1
            say(f"   {s['id']} ({fx:g}, {fy:g}, {fz:g}) {s.get('reach', '')}: " + ", ".join(sorted(set(found))))
    say(f"   {n} of {len(table['stations'])} stations")
    say()
    say("== every station: feet, how it is reached, what the tool notes")
    for s in table["stations"]:
        flags = {k: s[k] for k in ("floor", "leg", "round", "from", "how", "hop") if k in s}
        say(f"   {s['id']} {s['feet']} {s.get('reach')} {flags or ''} {s.get('views', '')} {(s.get('node') or '')[:44]}")
    os.makedirs("renders/_wip/walkfix", exist_ok=True)
    with open("renders/_wip/walkfix/rooms.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("\n".join(out[-70:]))


main()
