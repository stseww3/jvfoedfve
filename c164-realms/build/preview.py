#!/usr/bin/env python3
"""Rough pictures of a scene without the game: a plan from above and an elevation from the south.

    preview.py skyobs --out /tmp/skyobs

Flat colours by block name and simple shading only. It is for checking layout and proportions in
seconds; what the scene really looks like has to be judged in the game.
"""
import argparse
import importlib
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from artkit import clouds  # noqa: E402

# blocks the resource pack repaints without shading: shown in exactly their painted colour
PAINTED = {b: tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for b, c in zip(clouds.TONES, clouds.COLOURS)}
COLOURS = [
    ("snow", (244, 247, 250)), ("white_concrete", (214, 220, 226)), ("cherry_leaves", (236, 170, 200)),
    ("leaves", (62, 118, 52)), ("grass_block", (118, 170, 70)), ("moss", (96, 130, 50)), ("water", (60, 130, 205)),
    ("copper", (86, 164, 134)), ("prismarine", (52, 92, 80)), ("brick", (150, 92, 76)), ("deepslate", (72, 72, 78)),
    ("tuff", (108, 110, 104)), ("stone", (128, 128, 128)), ("andesite", (136, 137, 138)), ("cobble", (122, 122, 122)),
    ("spruce", (112, 82, 48)), ("dark_oak", (64, 42, 20)), ("oak", (160, 130, 78)), ("planks", (150, 112, 66)),
    ("log", (98, 76, 46)), ("wool", (190, 80, 70)), ("terracotta", (160, 90, 70)), ("dirt", (134, 96, 67)),
    ("path", (148, 122, 65)), ("gravel", (130, 127, 126)), ("lantern", (250, 200, 90)), ("glass", (190, 220, 235)),
]
SKIP = ("light", "air", "barrier", "structure_void")


def colour(state, cache={}):
    hit = cache.get(state)
    if hit is None:
        name = state.partition("[")[0]
        hit = (150, 150, 150)
        if name in PAINTED:
            hit = PAINTED[name]
        else:
            for key, rgb in COLOURS:
                if key in name:
                    hit = rgb
                    break
        cache[state] = hit
    return hit


def render(canvas, out, scale=2):
    cells = [(k, v) for k, v in canvas.b.items() if v.partition("[")[0] not in SKIP]
    xs = [k[0] for k, _ in cells]
    ys = [k[1] for k, _ in cells]
    zs = [k[2] for k, _ in cells]
    x0, x1, y0, y1, z0, z1 = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    nx, ny, nz = x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1

    top_y = np.full((nz, nx), -10**6)
    top_c = np.zeros((nz, nx, 3), dtype=float)
    top_flat = np.zeros((nz, nx), dtype=bool)
    front_z = np.full((ny, nx), -10**6)
    front_c = np.zeros((ny, nx, 3), dtype=float)
    for (x, y, z), state in cells:
        i, j, k = x - x0, y - y0, z - z0
        if y > top_y[k, i]:
            top_y[k, i] = y
            top_c[k, i] = colour(state)
            top_flat[k, i] = state in PAINTED
        if z > front_z[ny - 1 - j, i]:
            front_z[ny - 1 - j, i] = z
            front_c[ny - 1 - j, i] = colour(state)

    sky = np.array([150, 185, 235], dtype=float)
    # plan: light from the north-west, higher ground a little brighter
    h = np.where(top_y > -10**5, top_y, y0).astype(float)
    slope = (np.roll(h, 1, axis=0) - h) + (np.roll(h, 1, axis=1) - h)
    shade = np.clip(1.0 - 0.07 * slope, 0.55, 1.25) * (0.8 + 0.2 * (h - y0) / max(1, y1 - y0))
    shade = np.where(top_flat, 1.0, shade)
    plan = np.where((top_y > -10**5)[..., None], top_c * shade[..., None], sky)
    # elevation: farther away is paler
    depth = np.where(front_z > -10**5, (z1 - front_z) / max(1, nz), 0.0)
    elev = np.where((front_z > -10**5)[..., None], front_c * (1.0 - 0.45 * depth[..., None]) + sky * 0.45 * depth[..., None], sky)

    for name, img in (("plan", plan), ("south", elev)):
        im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        path = f"{out}-{name}.png"
        im.save(path)
        print(path, im.size, f"x {x0}..{x1} y {y0}..{y1} z {z0}..{z1}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=int, default=2)
    args = ap.parse_args()
    scene = importlib.import_module(f"scenes.{args.scene}")
    canvas = scene.build()
    print(f"{len(canvas.b)} blocks, {len(canvas.entities)} entities")
    render(canvas, args.out, args.scale)


if __name__ == "__main__":
    main()
