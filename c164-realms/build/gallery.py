#!/usr/bin/env python3
"""Lay out a scene's custom models in a row of bays on the running server and write camera shots.

    gallery.py skyobs --pw-file <server>/.rcon_pw --at 3300 120 0 --shots /tmp/gallery.json

Each bay is eight blocks wide with a plain backdrop, so models can be judged on their own before
they go into the scene. Entities carry the tag c164gal and are replaced on every run.
"""
import argparse
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

from artkit import models as M  # noqa: E402
from artkit.nbtw import snbt  # noqa: E402
from rcon import Rcon  # noqa: E402

BAY = 8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--pw-file", required=True)
    ap.add_argument("--rcon-port", type=int, default=25598)
    ap.add_argument("--at", type=int, nargs=3, default=[3300, 120, 0], metavar=("X", "Y", "Z"))
    ap.add_argument("--shots", required=True, help="where to write the camera list")
    args = ap.parse_args()

    props = importlib.import_module(f"scenes.{args.scene}.props")
    models = props.build_models()
    bx, by, bz = args.at
    n = len(props.GALLERY)
    with open(args.pw_file) as fh:
        rc = Rcon(port=args.rcon_port, password=fh.read().strip(), timeout=120.0)

    def run(cmd):
        out = rc.command(cmd)
        if any(w in out for w in ("rror", "nknown", "ncorrect", "xpected")):
            print("!!", cmd[:120], "->", out.strip()[:200])

    x1 = bx + BAY * n
    run(f"forceload add {bx - 8} {bz - 16} {x1 + 8} {bz + 16}")
    run("kill @e[tag=c164gal]")
    run(f"fill {bx - 6} {by - 2} {bz - 9} {x1 + 6} {by + 16} {bz + 12} air")
    run(f"fill {bx - 6} {by - 1} {bz - 8} {x1 + 6} {by - 1} {bz + 12} smooth_stone")
    run(f"fill {bx - 6} {by} {bz - 8} {x1 + 6} {by + 14} {bz - 8} light_gray_concrete")
    shots = []
    for i, (name, parts, cam, look) in enumerate(props.GALLERY):
        ox, oz = bx + BAY * i + BAY / 2.0, bz + 0.5
        for model_name, offset, opts in parts:
            model = models[model_name]
            scale = props.SCALE[model_name]
            if offset is None:
                lo, _ = model.bounds()
                offset = (0.0, (model.anchor[1] - lo[1]) * scale / 16.0, 0.0)
            nbt = M.display(model, scale=scale, **opts)
            nbt.pop("id")
            nbt["Tags"] = ["c164gal"]
            run(f"summon minecraft:item_display {ox + offset[0]} {by + offset[1]} {oz + offset[2]} {snbt(nbt)}")
        shots.append({"name": name, "pos": [ox + cam[0], by + cam[1], oz + cam[2]],
                      "look_at": [ox + look[0], by + look[1], oz + look[2]]})
    rc.close()
    with open(args.shots, "w") as fh:
        json.dump(shots, fh, indent=1)
    print(f"{n} bays at {bx} {by} {bz}; shots -> {args.shots}")


if __name__ == "__main__":
    main()
