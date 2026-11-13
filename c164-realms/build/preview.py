#!/usr/bin/env python3
"""Rough pictures of a scene without the game: a plan from above and an elevation from the south.

    preview.py skyobs --out /tmp/skyobs
    preview.py skyobs --out /tmp/skyobs --shots shots.json [--only hero,low]

With --shots it draws a camera picture per shot of a tools/shoot.py list instead (scene coordinates):
blocks only, one flat colour per block, faces shaded as the game shades them, shade under roofs.

Flat colours by block name and simple shading only. It is for checking layout and proportions in
seconds; what the scene really looks like has to be judged in the game.
"""
import argparse
import importlib
import json
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
    ("pale_oak_leaves", (226, 170, 48)), ("leaf_litter", (170, 120, 50)),
    ("leaves", (62, 118, 52)), ("grass_block", (118, 170, 70)), ("moss", (96, 130, 50)), ("water", (60, 130, 205)),
    ("copper", (86, 164, 134)), ("prismarine", (52, 92, 80)), ("brick", (150, 92, 76)), ("deepslate", (72, 72, 78)),
    ("calcite", (223, 224, 220)), ("basalt", (74, 74, 80)), ("lapis", (16, 26, 62)),
    ("tuff", (108, 110, 104)), ("stone", (128, 128, 128)), ("andesite", (136, 137, 138)), ("cobble", (122, 122, 122)),
    ("spruce", (112, 82, 48)), ("dark_oak", (64, 42, 20)), ("oak", (160, 130, 78)), ("planks", (150, 112, 66)),
    ("white_glazed", (232, 221, 190)), ("yellow_glazed", (205, 190, 150)), ("red_glazed", (172, 60, 48)),
    ("orange_glazed", (130, 42, 36)),
    ("log", (98, 76, 46)), ("wool", (190, 80, 70)), ("white_terracotta", (210, 178, 161)),
    ("red_terracotta", (143, 61, 47)), ("terracotta", (160, 90, 70)), ("dirt", (134, 96, 67)),
    ("path", (148, 122, 65)), ("gravel", (130, 127, 126)), ("lantern", (250, 200, 90)), ("glass", (190, 220, 235)),
]
SKIP = ("light", "air", "barrier", "structure_void")
# models that matter for the composition of a wide picture: part of the name -> dot colour
MARKS = [("crystal", (70, 230, 220)), ("chain", (40, 42, 50)), ("telescope", (200, 160, 60))]


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


class Blocks:
    """The scene as an array, for looking at it from a camera position."""

    def __init__(self, canvas):
        cells = [(k, v) for k, v in canvas.b.items() if v.partition("[")[0] not in SKIP]
        pts = np.array([k for k, _ in cells])
        self.lo = pts.min(axis=0) - 1
        self.shape = pts.max(axis=0) - self.lo + 2
        index, rgb, flat = {}, [(0, 0, 0)], [False]
        ids = np.empty(len(cells), dtype=np.uint16)
        for n, (_, state) in enumerate(cells):
            i = index.get(state)
            if i is None:
                i = index[state] = len(rgb)
                rgb.append(colour(state))
                flat.append(state in PAINTED)
            ids[n] = i
        rel = pts - self.lo
        self.grid = np.zeros(self.shape, dtype=np.uint16)
        self.grid[rel[:, 0], rel[:, 1], rel[:, 2]] = ids
        self.rgb = np.array(rgb, dtype=float)
        self.flat = np.array(flat)
        # the highest block of every column: what lies below it gets no direct sky light
        solid = self.grid > 0
        self.roof = np.where(solid.any(axis=1), self.shape[1] - 1 - np.argmax(solid[:, ::-1, :], axis=1), -1)

    def march(self, p, d, far):
        """First block on each ray: palette index (0 = none), distance, axis crossed, step sign, cell."""
        n = len(p)
        d = np.where(np.abs(d) < 1e-9, 1e-9, d)
        q = p - self.lo
        t0, t1 = (0 - q) / d, (self.shape - q) / d
        start = np.maximum(np.minimum(t0, t1).max(axis=1), 0.0) + 1e-4
        alive = (np.maximum(t0, t1).min(axis=1) > start) & (start < far)

        hit = np.zeros(n, dtype=np.uint16)
        dist = np.full(n, np.inf)
        axis = np.zeros(n, dtype=np.int64)
        where = np.zeros((n, 3), dtype=np.int64)
        idx = np.nonzero(alive)[0]
        pos = q[idx] + d[idx] * start[idx, None]
        cell = np.clip(np.floor(pos).astype(np.int64), 0, self.shape - 1)
        step = np.where(d[idx] > 0, 1, -1)
        tdelta = np.abs(1.0 / d[idx])
        tmax = start[idx, None] + (cell + (step > 0) - pos) / d[idx]
        t = start[idx]
        ax = np.argmax(np.minimum(t0, t1)[idx], axis=1)
        for _ in range(int(self.shape.sum()) + 3):
            if not len(idx):
                break
            v = self.grid[cell[:, 0], cell[:, 1], cell[:, 2]]
            got = v > 0
            if got.any():
                g = idx[got]
                hit[g], dist[g], axis[g], where[g] = v[got], t[got], ax[got], cell[got]
            rows = np.arange(len(idx))
            ax = np.argmin(tmax, axis=1)
            t = tmax[rows, ax]
            tmax[rows, ax] += tdelta[rows, ax]
            cell[rows, ax] += step[rows, ax]
            keep = ~got & (t < far) & ((cell >= 0) & (cell < self.shape)).all(axis=1)
            idx, cell, step, tdelta, tmax, t, ax = (a[keep] for a in (idx, cell, step, tdelta, tmax, t, ax))
        sign = np.where(d[np.arange(n), axis] > 0, 1, -1)
        return hit, dist, axis, sign, where

    def view(self, pos, look_at, size=(640, 360), fov=70.0, far=520.0, marks=()):
        """A picture from a camera position, block faces shaded the way the game shades them.
        marks = [((x, y, z), colour, size in blocks)] are drawn as dots unless a block hides them."""
        w, h = size
        pos, look_at = np.array(pos, dtype=float), np.array(look_at, dtype=float)
        f = (look_at - pos) / np.linalg.norm(look_at - pos)
        r = np.cross(f, (0.0, 1.0, 0.0))
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        half = np.tan(np.radians(fov) / 2)
        sx = ((np.arange(w) + 0.5) / w * 2 - 1) * half * w / h
        sy = (1 - (np.arange(h) + 0.5) / h * 2) * half
        d = f[None, None] + sx[None, :, None] * r[None, None] + sy[:, None, None] * u[None, None]
        d = (d / np.linalg.norm(d, axis=2, keepdims=True)).reshape(-1, 3)
        hit, dist, axis, sign, cell = self.march(np.broadcast_to(pos, d.shape), d, far)

        # sky: paler towards the horizon
        up = np.clip(d[:, 1], -1, 1)
        horizon, zenith = np.array([206.0, 226, 242]), np.array([104.0, 156, 226])
        img = horizon + (zenith - horizon) * np.clip(up * 1.6, 0, 1)[:, None] ** 0.8
        got = hit > 0
        face = np.where(axis == 1, np.where(sign < 0, 1.0, 0.5), np.where(axis == 2, 0.8, 0.6))
        # the cell in front of the face that was hit: under a roof it is in shade
        front = cell.copy()
        front[np.arange(len(front)), axis] -= sign
        front = np.clip(front, 0, self.shape - 1)
        shade = np.where(front[:, 1] < self.roof[front[:, 0], front[:, 2]], 0.58, 1.0)
        grain = 0.94 + 0.12 * ((cell[:, 0] * 73856093 ^ cell[:, 1] * 19349663 ^ cell[:, 2] * 83492791) % 97) / 96.0
        lit = np.where(self.flat[hit], 1.0, face * shade * grain)
        rgb = self.rgb[hit] * lit[:, None]
        haze = (1 - np.exp(-(np.where(got, dist, 0.0) / 420.0) ** 1.5))[:, None]
        img = np.where(got[:, None], rgb * (1 - haze) + horizon * haze, img).reshape(h, w, 3)
        # models are not drawn; the larger ones get a dot where they stand, sized by their scale
        depth = dist.reshape(h, w)
        for at, colour, size in marks:
            v = np.array(at, dtype=float) - pos
            z = float(v @ f)
            if z < 0.5:
                continue
            px = int((float(v @ r) / z / (half * w / h) + 1) * w / 2)
            py = int((1 - float(v @ u) / z / half) * h / 2)
            rad = max(1, int(round(size * h / (2 * half * z))))
            if not (0 <= px < w and 0 <= py < h) or depth[py, px] < np.linalg.norm(v) - 1.5:
                continue
            img[max(0, py - rad):py + rad + 1, max(0, px - rad):px + rad + 1] = colour
        return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--shots", help="shot list as used by tools/shoot.py: a camera picture per shot instead")
    ap.add_argument("--only", help="comma separated shot names")
    ap.add_argument("--size", default="640x360")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    scene = importlib.import_module(f"scenes.{args.scene}")
    canvas = scene.build()
    print(f"{len(canvas.b)} blocks, {len(canvas.entities)} entities")
    if not args.shots:
        render(canvas, args.out, args.scale)
        return
    with open(args.shots) as fh:
        shots = json.load(fh)
    if args.only:
        shots = [s for s in shots if s["name"] in args.only.split(",")]
    blocks = Blocks(canvas)
    size = tuple(int(v) for v in args.size.split("x"))
    marks = []
    for x, y, z, nbt in canvas.entities:
        model = nbt["item"]["components"]["minecraft:item_model"].partition(":")[2]
        scale = float(nbt["transformation"]["scale"][0])
        for key, colour in MARKS:
            if key in model and scale >= 1.5:
                marks.append(((x, y, z), colour, scale * 0.35))
                break
    for shot in shots:
        path = f"{args.out}-{shot['name']}.png"
        blocks.view(shot["pos"], shot["look_at"], size, marks=marks).save(path)
        print(path)


if __name__ == "__main__":
    main()
