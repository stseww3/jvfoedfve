#!/usr/bin/env python3
"""Where the ways a visitor walks are dark: the list for "the ways are all lit" (the closing list
of 11-16, item 3). It only reads; the lamps are sky/lights' to place.

    python tools/darkfloor.py [--out <folder>] [--floor 5] [--step 7] [--head <assembly commit>]

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
apart: a cell under the open sky (no block over the head; the night lights it), and the dome
room (the director, #442: it is kept dark). The dark cells are put in heaps: by room
(main/shell.room_at) or, outside the shell's rooms, by the stretch of the walk-through route whose
point is nearest; within that, cells that touch are one heap, with its box, its darkest cell and
the nearest source sky/lights has placed.

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
    """{(x, z): [(y0, y1)]} of the doorways."""
    out = {}

    def add(cells, y):
        for x, z in cells:
            out.setdefault((int(x), int(z)), []).append((int(y[0]), int(y[1])))

    try:
        from scenes.obs.main import facade
        for d in facade.doors():
            add(d["cells"], d["y"])
    except Exception as e:  # noqa: BLE001  the list is still worth having without them
        print(f"darkfloor: facade.doors() not read ({e})")
    try:
        from scenes.obs.main import shell
        for d in shell.doors():
            add(d["cells"], d["y"])
    except Exception as e:  # noqa: BLE001
        print(f"darkfloor: shell.doors() not read ({e})")
    add(S.DOME_ROOM_DOORS["cells"], S.DOME_ROOM_DOORS["y"])
    return out


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
        if under.endswith(("_stairs", "_slab")):
            kind = "step"
        elif any(y0 <= cy <= y1 for y0, y1 in doors.get((cx, cz), ())):
            kind = "threshold"
        else:
            kind = "floor"
        best = max(light.get(cell, 0), light.get((cx, cy + 1, cz), 0))
        rows[cell] = dict(how=how, kind=kind, light=best, need=args.floor if kind == "floor" else args.step,
                          sky=tops.get((cx, cz), -10 ** 9) <= cy + 1, room=room_at(cx, cy, cz), under=under)

    def section(cell, row):
        if row["room"]:
            return "room: " + row["room"]
        best = None
        for label, at in points:
            d = math.sqrt((at[0] - cell[0] - 0.5) ** 2 + (LEVELS * (at[1] - cell[1])) ** 2 + (at[2] - cell[2] - 0.5) ** 2)
            if best is None or d < best[0]:
                best = (d, label)
        return best[1] if best is not None and best[0] <= NEAR else "off the routes"

    dark, open_sky, dome = {}, {}, []
    for cell, row in rows.items():
        if row["light"] >= row["need"]:
            continue
        if row["room"] == "dome room":
            dome.append(cell)
        elif row["sky"]:
            open_sky.setdefault(section(cell, row), []).append(cell)
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
                hop=sum(rows[c]["how"] == "hop" for c in heap),
                nearest=None if near is None else dict(steps=near[0], level=near[1], why=near[2], cell=list(near[3])),
                list=sorted([list(c) + [rows[c]["light"], rows[c]["kind"]] for c in heap])))
        found_heaps.sort(key=lambda hp: (-hp["cells"], hp["lo"]))
        sections.append(dict(name=name, cells=len(dark[name]), darkest=min(rows[c]["light"] for c in dark[name]),
                             heaps=found_heaps))

    roofed = sum(not r["sky"] for r in rows.values())
    n_dark = sum(s["cells"] for s in sections)
    by_kind = {k: sum(hp["kinds"][k] for s in sections for hp in s["heaps"]) for k in KINDS}
    n_heaps = sum(len(s["heaps"]) for s in sections)
    n_sky = sum(len(v) for v in open_sky.values())
    report = dict(
        head=args.head, floor=args.floor, step=args.step,
        standing=dict(cells=len(rows), walk=sum(r["how"] == "walk" for r in rows.values()),
                      hop=sum(r["how"] == "hop" for r in rows.values()), roofed=roofed, fall_only_nodes=fell),
        starts=[dict(start=name, new=new) for name, new in used], no_standing_at=lost,
        dark=dict(cells=n_dark, heaps=n_heaps, **by_kind), sections=sections,
        open_sky={name: dict(cells=len(v), lo=box(v)[0], hi=box(v)[1]) for name, v in sorted(open_sky.items())},
        dome_room=dict(cells=len(dome)), sources=len(placed))

    title = (f"总装 {args.head}" if args.head else "总场景") if master else f"场景 {args.scene}"
    md = [f"# 路上的光：暗格清单（{title}）", "",
          f"量法：`tools/walkreach.py` 算人走得到的地方（从出生点起；再加两条走查路线上出生点走不到的点），"
          f"`sky/_lightkit.levels` 算块光，取脚格和头格里亮的那个（同 `obs_sky_lights/ways.py`）。"
          f"地面低于 {args.floor}、台阶（脚下是 `_stairs`、`_slab`）和门槛（`facade.doors()`、`shell.doors()`、"
          f"`S.DOME_ROOM_DOORS` 的格）低于 {args.step} 算暗。露天的（头上没有块）和穹顶室不算，另列。坐标是格子的整数坐标，y 是脚所在的那一行。",
          "",
          f"- 站得住的格：{len(rows)}（走得到 {report['standing']['walk']}，要跳一下 {report['standing']['hop']}），"
          f"其中屋顶下 {roofed}。只能掉下去才到的地方不算（{fell} 个落脚点）。",
          f"- **暗：{n_dark} 格，{n_heaps} 堆**（地面 {by_kind['floor']}，台阶 {by_kind['step']}，门槛 {by_kind['threshold']}）。",
          f"- 露天不算暗：{n_sky} 格。穹顶室不算：{len(dome)} 格。sky/lights 现在放了 {len(placed)} 个光源。"]
    if lost:
        md.append(f"- 路线上站不住人的点（没有从那里起算）：{len(lost)} 个，如 {'；'.join(lost[:4])}")
    md += ["", "每堆一行：范围（x，y，z）、格数、最暗的块光、地面/台阶/门槛各几格、最近的 sky/lights 光源（走格数、级、它的说明）。", ""]
    for s in sections:
        md += [f"## {s['name']}：暗 {s['cells']} 格，{len(s['heaps'])} 堆，最暗 {s['darkest']}", "",
               "| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |", "| --- | --- | --- | --- | --- | --- | --- |"]
        for hp in s["heaps"]:
            lo, hi, near = hp["lo"], hp["hi"], hp["nearest"]
            said = "没有" if near is None else f"{near['steps']} 格外，{near['level']} 级，{near['why']} @ {tuple(near['cell'])}"
            md.append(f"| {span(lo, hi, 0)} | {span(lo, hi, 1)} | {span(lo, hi, 2)} | {hp['cells']} | {hp['darkest']} | "
                      f"{hp['kinds']['floor']}/{hp['kinds']['step']}/{hp['kinds']['threshold']} | {said} |")
        md.append("")
    md += ["## 露天的（不算暗，天光照得到）", "", "| 地段 | 格数 | x | y | z |", "| --- | --- | --- | --- | --- |"]
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
          f"open sky {n_sky}, dome room {len(dome)}; {time.time() - t0:.0f} s")
    for s in sections:
        big = s["heaps"][0]
        print(f"  {s['name']}: {s['cells']} cells in {len(s['heaps'])} heaps, darkest {s['darkest']}; the largest "
              f"x {span(big['lo'], big['hi'], 0)} y {span(big['lo'], big['hi'], 1)} z {span(big['lo'], big['hi'], 2)} "
              f"({big['cells']})")
    print(f"written: {args.out}/dark.md, dark.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
