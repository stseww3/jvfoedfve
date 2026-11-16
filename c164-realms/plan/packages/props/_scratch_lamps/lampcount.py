"""Display entities of the master scene by line and by package, and what the opal-globe lamps of
props/lamps (street, post, bracket_a, pendant_a) cost when each takes EXTRA more display entities.

Run in build/ on a worker node:  PYTHONPATH=. python lampcount.py [shot list]
The shot list defaults to tools/win/shots/obs-board.json (the twelve board views).
"""
import json
import math
import os
import sys

import numpy as np

from artkit.canvas import Canvas
from scenes import obs
from scenes.obs.common import skeleton as S

GLOBES = ("street", "post", "bracket_a", "pendant_a")
PREFIX = "prop_lamp_"
EXTRA = 3
DISPLAYS = {"minecraft:item_display", "minecraft:block_display", "minecraft:text_display"}
FOV, ASPECT = 77.0, 16.0 / 9.0

now = {"line": None, "package": None}
log = []            # (line, package, model, x, y, z, view range)
_add = Canvas.add_entity


def add_entity(self, x, y, z, nbt):
    if nbt.get("id") in DISPLAYS:
        ref = ((nbt.get("item") or {}).get("components") or {}).get("minecraft:item_model") or "?"
        log.append((now["line"], now["package"], ref.split(":", 1)[-1], float(x), float(y), float(z),
                    float(nbt.get("view_range", 1.0)) * 64.0))
    return _add(self, x, y, z, nbt)


Canvas.add_entity = add_entity


def wrap(module):
    inner = getattr(module, "build", None)
    if inner is None or getattr(inner, "_counted", False):
        return
    name = module.__name__.rsplit(".", 1)[-1]

    def build(canvas, origin=(0, 0, 0), *a, **kw):
        before = now["package"]
        now["package"] = name
        try:
            return inner(canvas, origin, *a, **kw)
        finally:
            now["package"] = before

    build._counted = True
    module.build = build


def globe(model):
    return model[len(PREFIX):] if model.startswith(PREFIX) and model[len(PREFIX):] in GLOBES else None


def tally(rows):
    out = {k: 0 for k in GLOBES}
    for row in rows:
        k = globe(row[2])
        if k:
            out[k] += 1
    return out


def words(t):
    return ", ".join(f"{k} {v}" for k, v in t.items() if v) or "none"


def main():
    c = Canvas()
    c.master = True
    counts = {}
    for line in obs.LINES:
        module = obs._line(line)
        cat = getattr(module, "_cat", None)
        if cat is not None:
            for part in cat.parts():
                wrap(part)
        now["line"], now["package"] = line, None
        counts[line] = int(module.build(c, obs.ORIGIN) or 0)
    shown = [e for e in c.entities if e[3].get("id") in DISPLAYS]
    print(f"display entities: {len(shown)} of {S.ENTITY_TOTAL} (logged {len(log)}); returned by line: "
          + ", ".join(f"{k} {v}" for k, v in counts.items() if v))
    print(f"budgets: props {S.BUDGET['props_outdoor']}, interiors {S.BUDGET['props_indoor']} "
          f"({S.BUDGET_PER_ROOM} a room), machines {S.BUDGET['machines']}, a view {S.ENTITY_PER_VIEW}, "
          f"props in a view {S.PROPS_PER_VIEW}")

    globes_all = tally(log)
    more_all = EXTRA * sum(globes_all.values())
    print(f"opal-globe lamps in all: {words(globes_all)} = {sum(globes_all.values())}; "
          f"+{EXTRA} each = +{more_all}: {len(shown)} -> {len(shown) + more_all} of {S.ENTITY_TOTAL}")

    print("by line and package: entities, opal-globe lamps, entities with +3 a lamp")
    lines = {}
    for row in log:
        lines.setdefault(row[0], {}).setdefault(row[1] or "-", []).append(row)
    budget = {"props": S.BUDGET["props_outdoor"], "interiors": S.BUDGET["props_indoor"], "machines": S.BUDGET["machines"]}
    for line in obs.LINES:
        packages = lines.get(line, {})
        if not packages:
            continue
        rows = [r for p in packages.values() for r in p]
        t = tally(rows)
        more = EXTRA * sum(t.values())
        cap = budget.get(line)
        print(f"  {line}: {len(rows)}" + (f" of {cap}" if cap else "") + f"; lamps {words(t)}; with them {len(rows) + more}"
              + (f" ({cap - len(rows) - more:+d} to the budget)" if cap else ""))
        for package in sorted(packages, key=lambda p: -len(packages[p])):
            rows = packages[package]
            t = tally(rows)
            more = EXTRA * sum(t.values())
            note = ""
            if line == "interiors":
                note = f" of {S.BUDGET_PER_ROOM}" + ("  OVER" if len(rows) + more > S.BUDGET_PER_ROOM else "")
            print(f"    {package}: {len(rows)}; lamps {words(t)}; with them {len(rows) + more}{note}")

    # where the lamps of a room come from: a room may hang lamps itself or leave them to props/lamps
    print("opal-globe lamps by who placed them:")
    for (line, package), t in sorted({(r[0], r[1] or "-"): tally([q for q in log if (q[0], q[1] or "-") == (r[0], r[1] or "-")])
                                      for r in log if globe(r[2])}.items()):
        print(f"  {line}/{package}: {words(t)}")

    try:
        from scenes.obs.main import shell
        rooms = dict(shell.ROOMS)
    except Exception as err:
        rooms = {}
        print(f"  (no room table: {err})")

    def where(x, y, z):
        for name, room in rooms.items():
            feet, top = room.get("feet", -1e9), room.get("ceiling")
            if "box" in room:
                x0, z0, x1, z1 = room["box"]
                if x0 <= x <= x1 + 1 and z0 <= z <= z1 + 1 and feet - 0.5 <= y <= (1e9 if top is None else top) + 0.5:
                    return name
            elif "centre" in room:
                cx, cz = room["centre"]
                if math.hypot(x - cx, z - cz) <= room["radius"] + 1 and y >= feet - 0.5:
                    return name
        return "outside main/shell's rooms"

    print("by where a thing stands (the rooms of main/shell.ROOMS, whoever placed it): entities, lamps, with +3 a lamp")
    spots = {}
    for r in log:
        spots.setdefault(where(r[3], r[4], r[5]), []).append(r)
    for name, rows in sorted(spots.items()):
        t = tally(rows)
        print(f"  {name}: {len(rows)}; lamps {words(t)}; with them {len(rows) + EXTRA * sum(t.values())}")

    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("..", "tools", "win", "shots", "obs-board.json")
    with open(path, encoding="utf-8") as fh:
        shots = json.load(fh)
    pts = np.array([[r[3], r[4], r[5]] for r in log], dtype=float).reshape(-1, 3)
    reach = np.array([r[6] for r in log])
    is_globe = np.array([globe(r[2]) is not None for r in log], dtype=bool)
    is_props = np.array([r[0] == "props" for r in log], dtype=bool)
    ty = math.tan(math.radians(FOV) / 2.0)
    print(f"by view ({os.path.basename(path)}): in view, lamps in view, with +3 a lamp (limit {S.ENTITY_PER_VIEW}); "
          f"props alone, with them (limit {S.PROPS_PER_VIEW})")
    for shot in shots:
        pos = np.array(shot["pos"], dtype=float)
        f = np.array(shot["look_at"], dtype=float) - pos
        f = f / np.linalg.norm(f)
        r = np.cross(f, (0.0, 1.0, 0.0))
        r = r / np.linalg.norm(r)
        u = np.cross(r, f)
        v = pts - pos
        depth = v @ f
        inside = ((np.linalg.norm(v, axis=1) <= reach) & (depth > -2.0) & (np.abs(v @ r) <= depth * ty * ASPECT + 2.0)
                  & (np.abs(v @ u) <= depth * ty + 2.0))
        n, g = int(inside.sum()), int((inside & is_globe).sum())
        p, pg = int((inside & is_props).sum()), int((inside & is_props & is_globe).sum())
        flag = "  OVER" if n + EXTRA * g > S.ENTITY_PER_VIEW or p + EXTRA * pg > S.PROPS_PER_VIEW else ""
        print(f"  {shot['name']}: {n}, {g}, {n + EXTRA * g}; props {p}, {p + EXTRA * pg}{flag}")


if __name__ == "__main__":
    main()
