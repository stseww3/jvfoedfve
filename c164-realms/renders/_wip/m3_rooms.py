"""Where a visitor walks in the chart room and on the south gallery, and what stands there without
a collision box (display models): maps on walkreach's half-block lattice, the boxes of the models,
and every station of the route whose body would stand in a model.
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

BODY, TALL = 0.3, 1.8
ROOMS = (("B the star hall", 0.0, (1.0, -6.0, 17.0, 6.5)),
         ("E the south gallery", 7.0, (-4.5, 2.5, 16.5, 7.0)), ("E the north gallery", 7.0, (-4.5, -6.0, 16.5, -1.5)),
         ("F the time room", 7.0, (2.0, -25.5, 15.0, -4.5)), ("G the chart room", 7.0, (2.0, 6.5, 14.0, 26.0)),
         ("I the dome room", 18.0, (-5.0, -10.5, 15.5, 11.5)), ("J the south end terrace and the small dome", 18.0, (0.0, 24.0, 16.5, 34.5)),
         ("K the north end terrace and the tower's lobby", 18.0, (0.0, -35.0, 17.5, -23.0)),
         ("the clock room", 24.0, (9.0, -34.0, 17.5, -26.0)),
         ("L the engine hall", -6.0, (68.0, 16.5, 89.5, 41.0)), ("M the meridian hut", 0.0, (30.0, -35.0, 41.0, -20.0)),
         ("N the plate vault", 0.0, (1.0, 3.5, 15.0, 27.0)), ("P the battery room", 0.0, (1.0, -25.5, 15.0, -2.5)))
LOOK = (("the small dome's door", (9, 18, 30), (9, 19, 30)), ("the tower's west door", (10, 18, -30), (10, 19, -30)),
        ("the hatch into the clock room", (11, 23, -32), (11, 24, -32)))
SHAFT = (10, -33, 16, -27)                  # the tower: every height a person stands at in these columns
out = []


def say(text=""):
    out.append(text)


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(getattr(v, "value", 0.0))


def box_of(entity, models):
    """(name, lo, hi) of a display entity in the scene: the box round its model as it is shown."""
    x, y, z, nbt = entity[0], entity[1], entity[2], entity[3]
    try:
        name = nbt["item"]["components"]["minecraft:item_model"].split(":", 1)[1]
    except (KeyError, TypeError, IndexError):
        return None
    model = models.get(name)
    if model is None:
        return name, None, None
    lo, hi = model.reach()
    t = nbt["transformation"]
    s = [num(v) for v in t["scale"]]
    qi = [num(v) for v in t["left_rotation"]]
    q = (-qi[0], qi[1], -qi[2], qi[3])
    yaw = num(nbt["Rotation"][0]) - 180.0
    wl, wh = [1e9] * 3, [-1e9] * 3
    for cx in (lo[0], hi[0]):
        for cy in (lo[1], hi[1]):
            for cz in (lo[2], hi[2]):
                v = [(c - a) * k / 16.0 for c, a, k in zip((cx, cy, cz), model.anchor, s)]
                v = K.turn(yaw, M._qrot(q, v))
                for i, p in enumerate((x + v[0], y + v[1], z + v[2])):
                    wl[i], wh[i] = min(wl[i], p), max(wh[i], p)
    return name, wl, wh


def hits(boxes, x, feet, z):
    """The models a person standing at the point stands in."""
    found = []
    for name, lo, hi in boxes:
        if lo[0] < x + BODY - 1e-6 and hi[0] > x - BODY + 1e-6 and lo[2] < z + BODY - 1e-6 and hi[2] > z - BODY + 1e-6 \
                and lo[1] < feet + TALL - 1e-6 and hi[1] > feet + 0.05:
            found.append(name)
    return found


def main():
    canvas, table_path = sys.argv[1], sys.argv[2]
    with open(canvas, "rb") as fh:
        kept = pickle.load(fh)
    cells, entities = kept["b"], kept["entities"]
    models = importlib.import_module("scenes.obs").build_models()
    boxes, unknown = [], {}
    for e in entities:
        got = box_of(e, models)
        if got is None:
            continue
        if got[1] is None:
            unknown[got[0]] = unknown.get(got[0], 0) + 1
        else:
            boxes.append(got)
    say(f"{len(entities)} entities, {len(boxes)} display models with a box" + (f"; no model for {unknown}" if unknown else ""))
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
                        inside = hits(boxes, xx, top, zz)
                        mark = ("x" if inside else "o") if kind == "walk" else ("X" if inside else "s")
                    else:
                        mark = kind[0]
                    if abs(top - level) <= 0.26:
                        break
                row.append(mark)
            say(f"{zz:7.1f} " + "".join(row))
        say(f"-- the display models that reach into a body's height there (feet {level:g} to {level + TALL:g}):")
        rows = []
        for mname, lo, hi in boxes:
            if lo[0] < x1 + 0.5 and hi[0] > x0 - 0.5 and lo[2] < z1 + 0.5 and hi[2] > z0 - 0.5 and lo[1] < level + TALL and hi[1] > level + 0.05:
                rows.append((round(lo[2], 2), f"   {mname:34s} x {lo[0]:6.2f} .. {hi[0]:6.2f}   z {lo[2]:6.2f} .. {hi[2]:6.2f}   y {lo[1]:5.2f} .. {hi[1]:5.2f}"))
        for _, line in sorted(rows):
            say(line)
    say()
    say("== doors and the hatch (the blocks)")
    for what, a, b in LOOK:
        say(f"   {what}: " + "; ".join(f"{c} {cells.get(c)}" for c in (a, b)))
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
        fy = s.get("floor", fy)
        found = hits(boxes, fx, fy, fz)
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
