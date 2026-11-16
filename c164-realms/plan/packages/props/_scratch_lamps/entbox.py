"""Where do the display entities' models fall in a shot's frame, by their real boxes? Run in build/
with PYTHONPATH=.:/tmp/c164_lamps

    python entbox.py <scene> [<shot>[,<shot>...]] [substring of the model's name]

Every face corner of every box of the model is put where the entity hangs and projected (1280x720,
vertical field of view 77). Per entity: the frame box of what is before the camera, and whether
the model is whole in the frame, cut by its edge, or out. Nothing is said about what hides it.
"""
import importlib
import sys

import numpy as np

from artkit import models as M

import mview
from inframe import camera, W, H


def load(scene):
    orig = M.display

    def display(model, yaw=0.0, scale=1.0, turns=(), **kw):
        nbt = orig(model, yaw=yaw, scale=scale, turns=turns, **kw)
        nbt["_view"] = (model, yaw, scale, tuple(turns))
        return nbt

    M.display = display
    try:
        mod = importlib.import_module("scenes." + scene)
        canvas = mod.build()
    finally:
        M.display = orig
    return mod, canvas


def corners(nbt, pos):
    model, yaw, scale, turns = nbt["_view"]
    s = np.array((scale, scale, scale) if isinstance(scale, (int, float)) else scale, float)
    q = M.IDENT
    for axis, deg in turns:
        q = M._qmul(M.quat(axis, deg), q)
    world = mview._yaw(yaw) @ mview._rot(q) @ np.diag(s) / 16.0
    pos = np.array(pos, float)
    out = []
    for o, eu, ev, _, _ in mview.quads(model, 0.0, 1.0):
        for a, b in ((0, 0), (1, 0), (0, 1), (1, 1)):
            out.append(world @ (o + a * eu + b * ev) + pos)
    return np.array(out)


def main():
    scene = sys.argv[1]
    want_shots = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] != "-" else None
    want = sys.argv[3] if len(sys.argv) > 3 else ""
    mod, canvas = load(scene)
    for shot in mod.shots():
        if want_shots and shot["name"] not in want_shots:
            continue
        px = camera(shot["pos"], shot["look_at"])
        print("shot", shot["name"], "pos", shot["pos"], "look_at", shot["look_at"])
        for x, y, z, nbt in canvas.entities:
            if "_view" not in nbt:
                continue
            name = nbt["item"]["components"]["minecraft:item_model"].split(":")[-1]
            if want not in name:
                continue
            pts = corners(nbt, (x, y, z))
            lo, hi = pts.min(axis=0), pts.max(axis=0)
            proj = [px(p) for p in pts]
            before = [p for p in proj if p]
            if not before:
                continue
            xs, ys = [p[0] for p in before], [p[1] for p in before]
            inside = [p for p in before if 0 <= p[0] < W and 0 <= p[1] < H]
            if not inside:
                verdict = "out"
            elif len(inside) == len(proj):
                verdict = "whole"
            else:
                verdict = "CUT"
            if verdict == "out" and not (-300 < min(xs) < W + 300 and -300 < min(ys) < H + 300):
                continue
            print(f"  {name:26s} box x {lo[0]:5.2f}..{hi[0]:5.2f} y {lo[1]:5.2f}..{hi[1]:5.2f} z {lo[2]:5.2f}..{hi[2]:5.2f}"
                  f" -> px x {min(xs):5.0f}..{max(xs):5.0f} y {min(ys):5.0f}..{max(ys):5.0f} {verdict:5s}"
                  f" {min(p[2] for p in before):.2f} off")


if __name__ == "__main__":
    main()
