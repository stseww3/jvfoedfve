#!/usr/bin/env python3
"""The ledger of view ranges in the master scene: which package has how many display entities in
which band (artkit.models FAR, MID, NEAR, SMALL), and how many of them each board view counts.

    python tools/viewbands.py                         the table by package
    python tools/viewbands.py interiors/chartroom     that package's models: band, how many, and the
                                                      board views that count them (what VIEW_KEEP is for)
    python tools/viewbands.py --lamps                 what sky/lights left out and why (its notes)
    python tools/viewbands.py --selftest              models.band and the assembly's VIEW, on a canvas of its own

A view counts an entity when it stands in the camera's cone and within its own view range, walls or
no walls: the game draws a display entity whatever stands between (tools/check.py, views).
"""
import json
import math
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check as C                                   # noqa: E402  (it puts build/ on the path)
import numpy as np                                  # noqa: E402
from artkit import models as M                      # noqa: E402
from artkit.canvas import Canvas                    # noqa: E402
from scenes.obs.common import assembly              # noqa: E402


def band_of(nbt):
    reach = float(nbt.get("view_range", 1.0))
    return next((name for name, value in M.BANDS if abs(reach - value) < 1e-6), f"{reach:g}")


def masks(shown):
    """{view name: which of `shown` the view counts}, as tools/check.py's views counts them."""
    with open(C.BOARD, encoding="utf-8") as fh:
        shots = json.load(fh)
    pts = np.array([[x, y, z] for x, y, z, _ in shown], dtype=float).reshape(-1, 3)
    reach = np.array([float(nbt.get("view_range", 1.0)) * 64.0 for _, _, _, nbt in shown])
    ty = math.tan(math.radians(C.FOV) / 2.0)
    out = {}
    for shot in shots:
        pos, f, r, u = C._frame(shot)
        v = pts - pos
        depth = v @ f
        out[shot["name"]] = ((np.linalg.norm(v, axis=1) <= reach) & (depth > -2.0)
                             & (np.abs(v @ r) <= depth * ty * C.ASPECT + 2.0) & (np.abs(v @ u) <= depth * ty + 2.0))
    return out


def short(view):
    return "V" + str(int(view[1:3])) if view[:1] == "v" and view[1:3].isdigit() else view


def table(package=None):
    from scenes import obs
    canvas = obs.build()
    shown = C._displays(canvas)
    whose = C._whose(canvas, shown)
    seen = masks(shown)
    names = [name for name, _ in M.BANDS]
    if package is None:
        rows = {}
        for i, (_, _, _, nbt) in enumerate(shown):
            row = rows.setdefault(whose[i], {})
            row[band_of(nbt)] = row.get(band_of(nbt), 0) + 1
        extra = sorted({k for row in rows.values() for k in row} - set(names))
        print(f"{'package':34s}" + "".join(f"{k:>7s}" for k in names + extra) + "   in the board's views")
        for owner in sorted(rows, key=lambda o: -sum(rows[o].values())):
            mine = whose == owner
            views = ", ".join(f"{short(v)} {int((m & mine).sum())}" for v, m in seen.items() if (m & mine).any())
            print(f"{owner:34s}" + "".join(f"{rows[owner].get(k, 0):7d}" for k in names + extra) + "   " + views)
        print(f"{'all':34s}" + "".join(f"{sum(row.get(k, 0) for row in rows.values()):7d}" for k in names + extra)
              + "   " + ", ".join(f"{short(v)} {int(m.sum())}" for v, m in seen.items()))
        return 0
    rows = {}
    for i, (_, _, _, nbt) in enumerate(shown):
        if whose[i] != package:
            continue
        key = (M.shown_model(nbt) or nbt.get("id", "?").split(":")[-1], band_of(nbt))
        row = rows.setdefault(key, {"n": 0, "views": {}})
        row["n"] += 1
        for v, m in seen.items():
            if m[i]:
                row["views"][v] = row["views"].get(v, 0) + 1
    if not rows:
        print(f"{package}: no display entities (packages: {', '.join(sorted(set(whose)))})")
        return 1
    for (name, band), row in sorted(rows.items()):
        print(f"{name:44s} {band:6s} x{row['n']:<4d} " + ", ".join(f"{short(v)} {n}" for v, n in row["views"].items()))
    return 0


def lamps():
    from scenes import obs
    from scenes.obs.sky import lights
    for line in lights.summary(obs.build()):
        if line.startswith(("note", "PROBLEM", "dressed")):
            print(line)
    return 0


def selftest():
    model = types.SimpleNamespace(name="t_thing", anchor=(8.0, 8.0, 8.0), shift=lambda: (0.0, 0.0, 0.0))
    other = types.SimpleNamespace(name="t_window_piece", anchor=(8.0, 8.0, 8.0), shift=lambda: (0.0, 0.0, 0.0))

    def build(canvas, origin=(0, 0, 0)):
        canvas.add_entity(0, 0, 0, M.display(model))                        # 3.0, as display() gives it
        canvas.add_entity(1, 0, 0, M.display(other))                        # kept by name
        canvas.add_entity(2, 0, 0, M.display(model, view=M.SMALL))          # less already: stays
        canvas.add_entity(3, 0, 0, {"id": "minecraft:marker"})              # no display entity
        canvas.add_entity(4, 0, 0, {"id": "minecraft:text_display", "view_range": M.Float(1.0)})
        return 4

    c = Canvas()
    c.add_entity(9, 0, 0, M.display(model))                                 # before `first`: not touched
    first = len(c.entities)
    build(c)
    assert M.band(c, first, M.NEAR, keep=("t_window_*",)) == 2
    got = [float(nbt.get("view_range", -1.0)) for _, _, _, nbt in c.entities]
    assert got == [3.0, 0.5, 3.0, 0.25, -1.0, 0.5], got
    assert M.band(c, first, M.NEAR, keep=("t_window_*",)) == 0             # a second time changes nothing

    c = Canvas()
    plain = types.SimpleNamespace(__name__="scenes.obs.interiors.plain", build=build)
    near = types.SimpleNamespace(__name__="scenes.obs.interiors.near", build=build, VIEW=M.NEAR, VIEW_KEEP=("t_window_piece",))
    cat = assembly.Category("scenes.obs.interiors")
    cat.parts = lambda: [plain, near]
    assert cat.build(c) == 8
    got = [float(nbt.get("view_range", -1.0)) for _, _, _, nbt in c.entities]
    assert got == [3.0, 3.0, 0.25, -1.0, 1.0, 0.5, 3.0, 0.25, -1.0, 0.5], got
    assert c.entity_owners == [(0, 5, "interiors/plain"), (5, 10, "interiors/near")], c.entity_owners
    whose = C._whose(c, C._displays(c))
    assert list(whose) == ["interiors/plain"] * 4 + ["interiors/near"] * 4, list(whose)
    print("viewbands selftest: band() lowers and keeps, the assembly applies VIEW and notes the owners -- ok")
    return 0


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        return selftest()
    if "--lamps" in args:
        return lamps()
    return table(args[0] if args else None)


if __name__ == "__main__":
    sys.exit(main())
