#!/usr/bin/env python3
"""Where the ways a visitor walks are dark: the list for "the ways are all lit" (the closing list
of 11-16, item 3). It only reads; the lamps are sky/lights' to place.

    python tools/darkfloor.py [--out <folder>] [--floor 5] [--step 7] [--head <assembly commit>]
                              [--before <the dark.json of the list before this one>]

Builds the master scene once (on a worker node, never on the shared machine) and puts three things
that exist already on top of one another:

    where a person stands    tools/walkreach.py: every place reached on foot or with a hop from the
                             spawn, and from the points of the two walk-through routes that the spawn
                             does not reach (a room behind a door that is a block); what is reached
                             only by a fall is left out and counted
    the light there          sky/_lightkit.levels, read as scenes/obs_sky_lights/ways.py reads it:
                             the better of the cell of the feet and the cell of the head
    what kind of place       a step: the feet rest on a block whose name ends in _stairs or _slab;
                             a threshold: a cell of facade.doors(), shell.doors() or
                             S.DOME_ROOM_DOORS; anything else is floor

A floor cell is dark under --floor, a step and a threshold under --step. Not counted, and listed
apart: a cell the sky lights, and the dome room (the director, #442: it is kept dark). The sky
lights a cell that is open to it straight up (glass over it does not shut it; a whole block, a
stair, a slab or a trapdoor does), and outside the shell's rooms a cell under an overhang that
its light reaches from the side at SKY_NEAR or more (the game takes a level off with every step:
the strip under a cornice, the first cells inside an open gateway). In a room of the shell only
block light counts, whatever the windows let in. The dark cells are put in heaps: by room
(main/shell.room_at) or, outside the shell's rooms, by the stretch of the walk-through route whose
point is nearest; within that, cells that touch are one heap, with its box, its darkest cell and
the nearest source sky/lights has placed.

Every heap is given to somebody (OWNERS: as sky/lights dealt them out; what he did not name goes
to the room's own package with a star, or stays undealt). With --before every heap also says how
many cells it had in the list before: a cell that is still dark counts for the heap it is in now,
a cell that is not for the heap that holds most of what is left of its old heap; an old heap of
which nothing is left is listed as cleared. The dark thresholds are listed cell by cell.

Writes <folder>/dark.md (the list, in Chinese) and <folder>/dark.json (every cell), and prints the
head of the list. Ends with 0 whatever it finds.
"""
import argparse
import importlib
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import walkreach as W  # noqa: E402  (puts build/ on the path)

from artkit import blocks as AB  # noqa: E402
from scenes import obs  # noqa: E402
from scenes.obs.common import blocks as B  # noqa: E402
from scenes.obs.common import skeleton as S  # noqa: E402
from scenes.obs.sky import _lightkit as L  # noqa: E402

ROUTES = ("plan/reviews/walk/in-route.json", "plan/reviews/walk/out-route.json")
NEAR = 24.0             # a cell further than this from every route point is "off the routes"
LEVELS = 3.0            # a block up or down counts as this many along, when the nearest point is looked for
KINDS = ("floor", "step", "threshold")
ROOFING = ("_stairs", "_slab", "_trapdoor")     # shapes with a whole face: the sky's light is not let through them
SKY_NEAR = 13           # the sky's light from which a cell under an overhang counts as lit by the sky

# Who lights which heap, as sky/lights (c331) dealt them out on 11-16 (#74750) and cr2 after him
# (the plate vault: floor 5, thresholds 7 as everywhere, its darkroom end at 5 to 6). The first line
# that fits a cell names its owner: (who, the section's name starts with, the box
# (x0, y0, z0, x1, y1, z1) in the building's own coordinates or None for the whole section).
NOBODY = "未分"
OWNERS = (
    ("不补（总监 #58129）", "room: star hall", (12, 0, -5, 15, 0, 5)),        # inside the east doors
    ("lights：路灯 7 盏", "room: star hall", (2, 0, -3, 3, 0, 3)),            # the pier's foot
    ("lights：路灯 7 盏", "room: star hall", (1, 7, -4, 7, 17, 4)),           # the ring stair and the deck under its runs
    ("lights：路灯 7 盏", "room: star hall", (2, 7, -5, 3, 8, 5)),            # where the cross gallery meets the side galleries
    ("lights：路灯 7 盏", "in-H", None),                                      # the ring stair
    ("lights：路灯 7 盏", "room: stair hall", (-1, 7, -5, 1, 8, 5)),          # the cross gallery
    ("lights：astro 找位置", "room: stair hall", (-7, 1, -5, 1, 13, 5)),      # the mezzanine and the two flights
    ("hall：下一次交付", "room: stair hall", (-7, 0, -5, 1, 0, 5)),           # the way to the west door
    ("hall：下一次交付", "in-C", None),
    ("m2", "room: time room", None),
    ("vault", "room: plate vault", None),                                     # cr2, #75753: the vault is a way like the others
    ("power", "in-L", None),
    ("dome", "in-I", None),                                                   # the roof round the dome room (the room itself is not counted)
    ("dome", "in-J", None),
    ("dome", "in-K", None),
    ("不补（观测室）", "in-M", None),
)
# the rooms' own packages (plan/ROSTER.md), for what sky/lights did not name: shown with a star
ROOM_OWNERS = {"star hall": "hall", "stair hall": "lights", "time room": "m2", "chart room": "chart",
               "plate vault": "vault", "battery room": "astro"}


def owner_of(section, cell):
    for who, start, b in OWNERS:
        if section.startswith(start) and (b is None or all(b[i] <= cell[i] <= b[i + 3] for i in range(3))):
            return who
    if section.startswith("room: ") and section[6:] in ROOM_OWNERS:
        return ROOM_OWNERS[section[6:]] + "*"
    return NOBODY


def owners_of(section, cells):
    """{who: cells} of a heap, the one with most cells first."""
    count = {}
    for c in cells:
        who = owner_of(section, tuple(c[:3]))
        count[who] = count.get(who, 0) + 1
    return dict(sorted(count.items(), key=lambda kv: (-kv[1], kv[0])))


def said_owners(count):
    return "；".join(who if len(count) == 1 else f"{who} {n} 格" for who, n in count.items())


def survey(canvas):
    """As scenes/obs_sky_lights/ways.survey: the block light of every cell that has any, and the
    highest block of every column that is not a light source."""
    source, tops = {}, {}
    lo, hi = [10 ** 9] * 3, [-10 ** 9] * 3
    for cell, state in canvas.b.items():
        for i in range(3):
            lo[i] = min(lo[i], cell[i])
            hi[i] = max(hi[i], cell[i])
        if state not in source:
            source[state] = AB.name_of(state) == B.LIGHT
        if not source[state] and cell[1] > tops.get((cell[0], cell[2]), -10 ** 9):
            tops[(cell[0], cell[2])] = cell[1]
    return L.levels(canvas, tuple(lo), tuple(hi)), tops


def sky_light(cells, least=SKY_NEAR):
    """The sky's light as the game spreads it, where it is `least` or more but not the full 15:
    ({cell: level}, {(x, z): the lowest row of the column that is open to the sky}). Straight down a
    column it is 15 as far as the first block that stops it; from a cell of 15 it loses a level
    with every step sideways, up or down. Whole blocks stop it, and so do stairs, slabs and
    trapdoors (the game lets a little by on their open sides; here none passes, so that nothing
    roofed with them counts as lit by the sky). Glass does not stop it."""
    stop, none = {}, -10 ** 9

    def stops(state):
        if state not in stop:
            stop[state] = L._stops_light(state) or AB.name_of(state).endswith(ROOFING)
        return stop[state]

    open_y, bottom = {}, 10 ** 9
    for (x, y, z), state in cells.items():
        bottom = min(bottom, y)
        if stops(state) and y + 1 > open_y.get((x, z), none):
            open_y[(x, z)] = y + 1
    out, ring = {}, []
    for (x, z), low in open_y.items():              # the cells under a roof that stand beside a cell of 15
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for y in range(max(open_y.get((x + dx, z + dz), none), bottom - 1), low):
                cell = (x, y, z)
                state = cells.get(cell)
                if (state is None or not stops(state)) and cell not in out:
                    out[cell] = 14
                    ring.append(cell)
    level = 14
    while level > least and ring:
        following = []
        for x, y, z in ring:
            for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z), (x, y, z + 1), (x, y, z - 1)):
                if n in out or n[1] >= open_y.get((n[0], n[2]), none):
                    continue
                state = cells.get(n)
                if state is not None and stops(state):
                    continue
                out[n] = level - 1
                following.append(n)
        ring, level = following, level - 1
    return out, open_y


def route_points(root):
    """[(label, (x, y, z))] of every point of the two routes, and the labels in the routes' order."""
    out, order = [], []
    for path in ROUTES:
        full = os.path.join(root, path)
        if not os.path.exists(full):
            continue
        with open(full, encoding="utf-8") as fh:
            data = json.load(fh)
        for stretch in data.get("stretches", ()):
            label = f"{data.get('prefix', 'way')}-{stretch['id']} {stretch.get('name', '')}".strip()
            order.append(label)
            for p in stretch.get("points", ()):
                out.append((label, tuple(float(v) for v in p["at"])))
    return out, order


def standing(world, starts):
    """{(i, j, h in 32nds): "walk" | "hop"} from every start that the ones before it did not reach,
    how many nodes were reached by a fall only, and the starts used and those nobody can stand at."""
    found, fell, used, lost = {}, set(), [], []
    for name, at in starts:
        node = world.node(at[0], at[2], at[1], reach=2)
        if node is None:
            lost.append(name)
            continue
        if node in found:
            continue
        reach = world.reach(at)
        new = 0
        for n, kind in reach.kind.items():
            if kind in ("walk", "hop"):
                if n not in found:
                    new += 1
                if found.get(n) != "walk":
                    found[n] = kind
            else:
                fell.add(n)
        used.append((name, new))
    return found, len(fell - set(found)), used, lost


def thresholds():
    """{(x, z): [(y0, y1, which doorway)]} of the doorways."""
    out = {}

    def add(cells, y, which):
        for x, z in cells:
            out.setdefault((int(x), int(z)), []).append((int(y[0]), int(y[1]), which))

    try:
        from scenes.obs.main import facade
        for d in facade.doors():
            add(d["cells"], d["y"], f"外墙 {d['front']} 面第 {d['bay']} 开间（{d['kind']}）")
    except Exception as e:  # noqa: BLE001  the list is still worth having without them
        print(f"darkfloor: facade.doors() not read ({e})")
    try:
        from scenes.obs.main import shell
        for d in shell.doors():
            add(d["cells"], d["y"], f"{d['room']} 的门")
    except Exception as e:  # noqa: BLE001
        print(f"darkfloor: shell.doors() not read ({e})")
    add(S.DOME_ROOM_DOORS["cells"], S.DOME_ROOM_DOORS["y"], "dome room 的门")
    return out


def heaps_before(path):
    """The list before this one: (its head, [(section, {cell: its light then})] heap by heap)."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("head", ""), [(s["name"], {tuple(c[:3]): c[3] for c in hp["list"]})
                                  for s in data.get("sections", ()) for hp in s["heaps"]]


def room_of():
    try:
        from scenes.obs.main import shell
        return shell.room_at
    except Exception as e:  # noqa: BLE001
        print(f"darkfloor: shell.room_at not read ({e})")
        return lambda x, y, z: None


def placed_sources(canvas):
    try:
        from scenes.obs.sky import lights
        return dict(lights.report(canvas)["placed"])
    except Exception as e:  # noqa: BLE001
        print(f"darkfloor: sky/lights' sources not read ({e})")
        return {}


def heaps(cells):
    """The cells that touch (a step along x or z, up to one row up or down), as lists."""
    left, out = set(cells), []
    while left:
        first = left.pop()
        heap, todo = [first], [first]
        while todo:
            x, y, z = todo.pop()
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for dy in (0, 1, -1):
                    n = (x + dx, y + dy, z + dz)
                    if n in left:
                        left.remove(n)
                        heap.append(n)
                        todo.append(n)
        out.append(heap)
    return out


def main():
    ap = argparse.ArgumentParser(description="the dark cells of the ways a visitor walks")
    ap.add_argument("--out", default="renders/_wip/light")
    ap.add_argument("--floor", type=int, default=5)
    ap.add_argument("--step", type=int, default=7)
    ap.add_argument("--head", default="", help="the assembly commit the list is of (for its title)")
    ap.add_argument("--before", default="", help="the dark.json of the list before this one: every heap says what it had then")
    ap.add_argument("--scene", default="obs", help="another scene than the master scene (a test scene: give --start)")
    ap.add_argument("--start", action="append", default=[], help="x,y,z of one more place to start from (repeatable)")
    args = ap.parse_args()
    root = os.path.normpath(os.path.join(HERE, ".."))
    t0 = time.time()
    master = args.scene == "obs"
    canvas = obs.build() if master else importlib.import_module(f"scenes.{args.scene}").build()
    cells = canvas.b
    print(f"darkfloor: the master scene, {len(cells)} blocks ({time.time() - t0:.0f} s)")
    light, tops = survey(canvas)
    print(f"darkfloor: block light in {len(light)} cells ({time.time() - t0:.0f} s)")
    sky, open_y = sky_light(cells)
    print(f"darkfloor: the sky's light reaches {len(sky)} cells under a roof from the side ({time.time() - t0:.0f} s)")
    if master:
        m = S.mass_bounds()
        world = W.World(cells, (m[0] - 40, m[2] - 40, m[3] + 40, m[5] + 40))
        points, _order = route_points(root)
        starts = [("spawn", W.landmarks()["spawn"])] + [(f"{label} #{n}", at) for n, (label, at) in enumerate(points)]
    else:
        world, points, starts = W.World(cells), [], []
    starts += [(f"--start {text}", tuple(float(v) for v in text.split(","))) for text in args.start]
    found, fell, used, lost = standing(world, starts)
    print(f"darkfloor: {len(found)} standing places from {len(used)} starts ({time.time() - t0:.0f} s)")

    doors, room_at, placed = thresholds(), room_of(), placed_sources(canvas)
    names = {}

    def name_of(state):
        if state not in names:
            names[state] = AB.name_of(state)
        return names[state]

    # one row for every cell a person stands in the middle of
    rows = {}
    for (i, j, hq), how in found.items():
        if i % 2 == 0 or j % 2 == 0:
            continue
        h = hq / float(W.Q)
        cell = (i // 2, int(math.floor(h + 1e-6)), j // 2)
        if cell in rows and rows[cell]["how"] == "walk":
            continue
        cx, cy, cz = cell
        under = cells.get(cell) if h - cy > 1e-6 else cells.get((cx, cy - 1, cz))
        under = name_of(under) if under is not None else ""
        door = next((which for y0, y1, which in doors.get((cx, cz), ()) if y0 <= cy <= y1), None)
        if under.endswith(("_stairs", "_slab")):
            kind = "step"
        elif door:
            kind = "threshold"
        else:
            kind = "floor"
        best = max(light.get(cell, 0), light.get((cx, cy + 1, cz), 0))
        # the sky's light, like the lamps', is the better of the feet's cell and the head's: on a
        # stair or a slab the feet are in the block's own cell, which the sky's beam does not enter
        from_sky = 15 if cy + 1 >= open_y.get((cx, cz), -10 ** 9) else max(sky.get(cell, 0), sky.get((cx, cy + 1, cz), 0))
        room = room_at(cx, cy, cz)
        rows[cell] = dict(how=how, kind=kind, light=best, need=args.floor if kind == "floor" else args.step,
                          sky=from_sky, room=room, under=under, door=door,
                          place="room" if room else "open" if from_sky == 15 else "eaves" if from_sky >= SKY_NEAR else "roofed")

    def section(cell, row):
        if row["room"]:
            return "room: " + row["room"]
        best = None
        for label, at in points:
            d = math.sqrt((at[0] - cell[0] - 0.5) ** 2 + (LEVELS * (at[1] - cell[1])) ** 2 + (at[2] - cell[2] - 0.5) ** 2)
            if best is None or d < best[0]:
                best = (d, label)
        return best[1] if best is not None and best[0] <= NEAR else "off the routes"

    dark, open_sky, eaves, dome = {}, {}, {}, []
    for cell, row in rows.items():
        if row["light"] >= row["need"]:
            continue
        if row["room"] == "dome room":
            dome.append(cell)
        elif row["place"] == "open":
            open_sky.setdefault(section(cell, row), []).append(cell)
        elif row["place"] == "eaves":
            eaves.setdefault(section(cell, row), []).append(cell)
        else:
            dark.setdefault(section(cell, row), []).append(cell)

    def nearest(heap):
        best = None
        for c, (level, why) in placed.items():
            d = min(abs(c[0] - x) + abs(c[1] - y - 1) + abs(c[2] - z) for x, y, z in heap)
            if best is None or d < best[0]:
                best = (d, level, why, c)
        return best

    def box(heap):
        lo = [min(c[i] for c in heap) for i in range(3)]
        hi = [max(c[i] for c in heap) for i in range(3)]
        return lo, hi

    def span(lo, hi, i):
        return f"{lo[i]}" if lo[i] == hi[i] else f"{lo[i]}..{hi[i]}"

    sections = []
    for name in sorted(dark, key=lambda s: (-len(dark[s]), s)):
        found_heaps = []
        for heap in heaps(dark[name]):
            lo, hi = box(heap)
            near = nearest(heap)
            found_heaps.append(dict(
                lo=lo, hi=hi, cells=len(heap), darkest=min(rows[c]["light"] for c in heap),
                kinds={k: sum(rows[c]["kind"] == k for c in heap) for k in KINDS},
                hop=sum(rows[c]["how"] == "hop" for c in heap), owner=owners_of(name, heap), was=None, kept=None,
                nearest=None if near is None else dict(steps=near[0], level=near[1], why=near[2], cell=list(near[3])),
                list=sorted([list(c) + [rows[c]["light"], rows[c]["kind"]] for c in heap])))
        found_heaps.sort(key=lambda hp: (-hp["cells"], hp["lo"]))
        sections.append(dict(name=name, cells=len(dark[name]), darkest=min(rows[c]["light"] for c in dark[name]),
                             was=None, heaps=found_heaps))

    # against the list before: what every heap had then, and the heaps of which nothing is left
    before, cleared, gone = None, [], dict(lit=0, no_standing=0, apart=0)
    if args.before:
        head_before, old_heaps = heaps_before(args.before)
        now = {tuple(c[:3]): (si, hi) for si, s in enumerate(sections) for hi, hp in enumerate(s["heaps"]) for c in hp["list"]}
        for s in sections:
            s["was"] = 0
            for hp in s["heaps"]:
                hp["was"], hp["kept"] = 0, 0
        was_in = {}
        for name, old in old_heaps:
            was_in[name] = was_in.get(name, 0) + len(old)
            heirs = {}
            for c in old:
                if c in now:
                    heirs[now[c]] = heirs.get(now[c], 0) + 1
                elif c not in rows:
                    gone["no_standing"] += 1
                elif rows[c]["light"] >= rows[c]["need"]:
                    gone["lit"] += 1
                else:
                    gone["apart"] += 1
            if not heirs:
                lo, hi = box(list(old))
                cleared.append(dict(name=name, lo=lo, hi=hi, cells=len(old), darkest=min(old.values()),
                                    owner=owners_of(name, old),
                                    light_now=[min(v), max(v)] if (v := [rows[c]["light"] for c in old if c in rows]) else None))
                continue
            for (si, hi), n in heirs.items():
                sections[si]["heaps"][hi]["was"] += n
                sections[si]["heaps"][hi]["kept"] += n
            si, hi = max(heirs, key=lambda k: (heirs[k], -k[0], -k[1]))
            sections[si]["heaps"][hi]["was"] += len(old) - sum(heirs.values())
        for s in sections:
            s["was"] = was_in.get(s["name"], 0)
        cleared.sort(key=lambda hp: (-hp["cells"], hp["name"], hp["lo"]))
        before = dict(head=head_before, cells=sum(len(old) for _name, old in old_heaps), heaps=len(old_heaps),
                      still_dark=sum(hp["kept"] for s in sections for hp in s["heaps"]), **gone)
        before["new_dark"] = sum(s["cells"] for s in sections) - before["still_dark"]

    by_owner = {}
    for s in sections:
        for hp in s["heaps"]:
            for who, n in hp["owner"].items():
                entry = by_owner.setdefault(who, dict(cells=0, heaps=0))
                entry["cells"] += n
                entry["heaps"] += 1
    by_owner = dict(sorted(by_owner.items(), key=lambda kv: (-kv[1]["cells"], kv[0])))
    sills = sorted((list(c) + [rows[c]["light"], rows[c]["door"], s["name"], owner_of(s["name"], c)])
                   for s in sections for hp in s["heaps"] for c in map(tuple, (e[:3] for e in hp["list"]))
                   if rows[c]["kind"] == "threshold")

    roofed = sum(r["place"] in ("room", "roofed") for r in rows.values())
    n_eaves = sum(len(v) for v in eaves.values())
    n_dark = sum(s["cells"] for s in sections)
    by_kind = {k: sum(hp["kinds"][k] for s in sections for hp in s["heaps"]) for k in KINDS}
    n_heaps = sum(len(s["heaps"]) for s in sections)
    n_sky = sum(len(v) for v in open_sky.values())
    report = dict(
        head=args.head, floor=args.floor, step=args.step,
        standing=dict(cells=len(rows), walk=sum(r["how"] == "walk" for r in rows.values()),
                      hop=sum(r["how"] == "hop" for r in rows.values()), roofed=roofed, fall_only_nodes=fell),
        starts=[dict(start=name, new=new) for name, new in used], no_standing_at=lost,
        dark=dict(cells=n_dark, heaps=n_heaps, **by_kind), before=before, by_owner=by_owner, sections=sections,
        thresholds=sills, cleared=cleared,
        open_sky={name: dict(cells=len(v), lo=box(v)[0], hi=box(v)[1]) for name, v in sorted(open_sky.items())},
        eaves={name: [dict(cells=len(hp), lo=box(hp)[0], hi=box(hp)[1], darkest=min(rows[c]["light"] for c in hp))
                      for hp in sorted(heaps(v), key=lambda hp: -len(hp))] for name, v in sorted(eaves.items())},
        dome_room=dict(cells=len(dome)), sources=len(placed))

    def change(was, cells):
        if was is None:
            return "—"
        if not was:
            return "新"
        if was == cells:
            return f"{was} → {cells}（没变）"
        return f"{was} → {cells}（{'少' if was > cells else '多'} {abs(was - cells)}）"

    title = (f"总装 {args.head}" if args.head else "总场景") if master else f"场景 {args.scene}"
    md = [f"# 路上的光：暗格清单（{title}）", "",
          f"量法：`tools/walkreach.py` 算人走得到的地方（从出生点起；再加两条走查路线上出生点走不到的点），"
          f"`sky/_lightkit.levels` 算块光，取脚格和头格里亮的那个（同 `obs_sky_lights/ways.py`）。"
          f"地面低于 {args.floor}、台阶（脚下是 `_stairs`、`_slab`）和门槛（`facade.doors()`、`shell.doors()`、"
          f"`S.DOME_ROOM_DOORS` 的格）低于 {args.step} 算暗。坐标是格子的整数坐标，y 是脚所在的那一行。",
          "",
          f"不算暗、另列的三种：露天（正上方到天没有挡光的块；玻璃不挡，整块、台阶、半砖、活板门挡）；檐下"
          f"（头上有东西，但天光从旁边照进来还有 {SKY_NEAR} 级以上，按游戏的算法每走一格减一级：檐口下贴墙的那一条、"
          f"水塔底下、敞开的门洞里头两格）；穹顶室（总监 #442）。壳里的房间（`shell.room_at` 认得的）一律只看块光，不管窗子透进多少天光。",
          "",
          f"- 站得住的格：{len(rows)}（走得到 {report['standing']['walk']}，要跳一下 {report['standing']['hop']}），"
          f"其中屋顶下 {roofed}。只能掉下去才到的地方不算（{fell} 个落脚点）。",
          f"- **暗：{n_dark} 格，{n_heaps} 堆**（地面 {by_kind['floor']}，台阶 {by_kind['step']}，门槛 {by_kind['threshold']}）。",
          f"- 不算暗：露天 {n_sky} 格，檐下 {n_eaves} 格，穹顶室 {len(dome)} 格。sky/lights 现在放了 {len(placed)} 个光源。"]
    if before:
        md.append(f"- 比上一版（{('总装 ' + before['head']) if before['head'] else '没写总装号'}，暗 {before['cells']} 格 {before['heaps']} 堆）："
                  f"还暗着 {before['still_dark']} 格，新暗 {before['new_dark']} 格；上一版的暗格里亮了 {before['lit']} 格，"
                  f"现在站不了人的 {before['no_standing']} 格，改算露天、檐下或穹顶室的 {before['apart']} 格；"
                  f"整堆清掉的 {len(cleared)} 堆（见后面）。")
    if lost:
        md.append(f"- 路线上站不住人的点（没有从那里起算）：{len(lost)} 个，如 {'；'.join(lost[:4])}")
    md += ["", "## 按归属", "",
           "归属照 lights（c331）11-16 的分法（#74750）；带 * 的是他没点到、按房间主人填的；「未分」是还没人认的。", "",
           "| 归谁 | 格数 | 堆数 |", "| --- | --- | --- |"]
    md += [f"| {who} | {v['cells']} | {v['heaps']} |" for who, v in by_owner.items()]
    md += ["", "每堆一行：范围（x，y，z）、格数、最暗的块光、地面/台阶/门槛各几格、归谁、比上一版（上一版这一堆的格数 → 现在的；"
           "还暗着的格算在它现在所在的堆里，亮了的格算在老堆剩得最多的那一堆里）、最近的 sky/lights 光源（走格数、级、它的说明）。", ""]
    for s in sections:
        was = "" if s["was"] is None else f"（上一版 {s['was']} 格）"
        md += [f"## {s['name']}：暗 {s['cells']} 格{was}，{len(s['heaps'])} 堆，最暗 {s['darkest']}", "",
               "| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |",
               "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for hp in s["heaps"]:
            lo, hi, near = hp["lo"], hp["hi"], hp["nearest"]
            said = "没有" if near is None else f"{near['steps']} 格外，{near['level']} 级，{near['why']} @ {tuple(near['cell'])}"
            md.append(f"| {span(lo, hi, 0)} | {span(lo, hi, 1)} | {span(lo, hi, 2)} | {hp['cells']} | {hp['darkest']} | "
                      f"{hp['kinds']['floor']}/{hp['kinds']['step']}/{hp['kinds']['threshold']} | {said_owners(hp['owner'])} | "
                      f"{change(hp['was'], hp['cells'])} | {said} |")
        md.append("")
    md += [f"## 暗的门槛，逐格（{len(sills)} 格）", "",
           "| x | y | z | 块光 | 哪道门 | 地段 | 归谁 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    md += [f"| {x} | {y} | {z} | {level} | {door} | {name} | {who} |" for x, y, z, level, door, name, who in sills]
    md.append("")
    if before:
        md += [f"## 上一版暗、这一版整堆清掉的（{len(cleared)} 堆，{sum(hp['cells'] for hp in cleared)} 格）", "",
               "| 地段（上一版的） | x | y | z | 格数 | 那时最暗 | 现在的块光 | 归谁 |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for hp in cleared:
            lit = "站不了人了" if hp["light_now"] is None else (
                f"{hp['light_now'][0]}" if hp["light_now"][0] == hp["light_now"][1] else f"{hp['light_now'][0]}..{hp['light_now'][1]}")
            md.append(f"| {hp['name']} | {span(hp['lo'], hp['hi'], 0)} | {span(hp['lo'], hp['hi'], 1)} | {span(hp['lo'], hp['hi'], 2)} | "
                      f"{hp['cells']} | {hp['darkest']} | {lit} | {said_owners(hp['owner'])} |")
        md.append("")
    md += ["## 檐下的（不算暗：天光从旁边照得到；块光不够，要不要补由 lights 看）", "",
           "| 地段 | x | y | z | 格数 | 最暗的块光 |", "| --- | --- | --- | --- | --- | --- |"]
    for name, found_heaps in sorted(report["eaves"].items(), key=lambda kv: -sum(hp["cells"] for hp in kv[1])):
        for hp in found_heaps:
            md.append(f"| {name} | {span(hp['lo'], hp['hi'], 0)} | {span(hp['lo'], hp['hi'], 1)} | "
                      f"{span(hp['lo'], hp['hi'], 2)} | {hp['cells']} | {hp['darkest']} |")
    md += ["", "## 露天的（不算暗）", "", "| 地段 | 格数 | x | y | z |", "| --- | --- | --- | --- | --- |"]
    for name, v in sorted(open_sky.items(), key=lambda kv: -len(kv[1])):
        lo, hi = box(v)
        md.append(f"| {name} | {len(v)} | {span(lo, hi, 0)} | {span(lo, hi, 1)} | {span(lo, hi, 2)} |")
    md += ["", "## 起算的点", ""] + [f"- {name}：新到 {new} 个落脚点" for name, new in used] + [""]

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "dark.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(md))
    with open(os.path.join(args.out, "dark.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"darkfloor: {len(rows)} standing cells, {roofed} under a roof; dark {n_dark} in {n_heaps} heaps "
          f"(floor {by_kind['floor']}, step {by_kind['step']}, threshold {by_kind['threshold']}); "
          f"open sky {n_sky}, under eaves {n_eaves}, dome room {len(dome)}; {time.time() - t0:.0f} s")
    if before:
        print(f"  against {before['head'] or 'the list before'} ({before['cells']} in {before['heaps']} heaps): still dark "
              f"{before['still_dark']}, new {before['new_dark']}; lit {before['lit']}, no standing place now {before['no_standing']}, "
              f"counted apart now {before['apart']}; {len(cleared)} heaps cleared")
    for who, v in by_owner.items():
        print(f"  owner {who}: {v['cells']} cells in {v['heaps']} heaps")
    for s in sections:
        big = s["heaps"][0]
        print(f"  {s['name']}: {s['cells']} cells{'' if s['was'] is None else ' (' + str(s['was']) + ' before)'} in {len(s['heaps'])} heaps, "
              f"darkest {s['darkest']}; the largest "
              f"x {span(big['lo'], big['hi'], 0)} y {span(big['lo'], big['hi'], 1)} z {span(big['lo'], big['hi'], 2)} "
              f"({big['cells']})")
    print(f"written: {args.out}/dark.md, dark.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
