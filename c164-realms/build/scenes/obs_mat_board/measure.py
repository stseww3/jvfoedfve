"""Read the brightness of the materials off the board's own pictures: the numbers the card keeps.

    python -m scenes.obs_mat_board.measure [folder] [--scene obs_mat_board_ashlar_a] [--marks folder]

folder holds the pictures as tools/selfshots.py leaves them: <shot>.png (renders/<scene>/, the
default) or <scene>-<shot>.png (renders/_wip/). Read are the three pictures of the whole board, one
to a light version (all 14000, all_b 18000, all_c 12900); a column of the table to each.

Every number is the mean Rec.601 luma, 0..1, of the pixels a patch covers in a picture, as the
windows, the snow and the clocks are read. A patch is laid out in the board's own coordinates, from
the constants the board is built from, and carried into the picture with the camera of the shot:
when the layout moves, the patches move with it. --marks writes each picture again with the read
pixels tinted, to see that every patch sits on its material.

    walls     the middle four by four cells of every wall of eight by eight. On a window's wall
              that is glass and glazing bars, no frame
    riser     the stone behind the walls of a tier, once for each ground the tier has (the
              board's dark stone; tuff brick behind iron and slate tile), at the last wall that
              stands before it: the row over the wall, under the sky alone, and the cell to the
              left of it, the middle four rows, which is what parts two walls
    snow      the wall of whole blocks (a face to the south); the drift where it lies seven, four
              and one layer deep (a face to the sky)
    rock      the mountain's rock the drift and the cloud tones lie in: beside the tones, and
              further in, nearer the lamp at the far end of the bare rock
    cloud     the five tones, dark to light, let into the rock; the same five as the bank's steps
    sky       a strip at the left edge of the picture, level with the board's middle

Nothing is asked of the numbers: the board is where materials are told apart, and which is to be
lighter than which is the matter of the cards that paint them. Exit 1 when a picture is missing.
"""
import argparse
import math
import os
import sys

import numpy as np
from PIL import Image

BUILD = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BUILD)

from scenes import obs_mat_board as M                 # noqa: E402
from scenes.obs.common import blocks as B             # noqa: E402

COEF = np.array([0.299, 0.587, 0.114])                 # Rec.601 luma
STEP = 1.0 / 16.0                                      # the grid a patch is sampled on, in cells
LIGHTS = ("all", "all_b", "all_c")
BANK = (3 * M.PITCH - 2, M.SHELF - 1)                  # the cloud bank as ground() lays it: wide, deep
TINT = np.array([255.0, 40.0, 200.0])


def patches():
    """[(group, name, corner, corner)]: flat patches, each a rectangle that lies in a plane of the
    board (one coordinate the same in both corners), in the board's coordinates."""
    out = []
    for k, (tier, walls) in enumerate(M.TIERS):
        if not walls:
            continue
        y, z = M.at(k)
        xs = M.places(k)
        over = {}                                   # a ground -> the last wall that stands before it
        for x, (name, _, _) in zip(xs, walls):
            out.append((tier, name, (x + 2, y + 2, z + 1), (x + M.N - 2, y + M.N - 2, z + 1)))
            over[M.GROUNDS.get(name, M.FLOOR)] = (x, name)
        for x, name in over.values():
            out.append((tier, f"riser over {name}", (x + 1, y + M.N + 0.1, z), (x + M.N - 1, y + M.N + 0.9, z)))
            out.append((tier, f"riser left of {name}", (x - 0.9, y + 2, z), (x - 0.1, y + M.N - 2, z)))
    y, z = M.at("ground")
    s, n = M.SNOW_AT, M.N
    out.append(("snow", "wall", (s + 2, y + 2, z + 1), (s + n - 2, y + n - 2, z + 1)))
    for layers in (7, 4, 1):                        # not 8: whole blocks at the wall's foot, in its shade
        row = next(r for r in range(n) if max(1, 8 - r * 8 // n) == layers)     # as _board.snow() lays the drift
        out.append(("snow", f"drift {layers}", (s + 1.5, y + layers / 8.0, z + 1.2 + row),
                    (s + n - 1.5, y + layers / 8.0, z + 1.8 + row)))
    out.append(("rock", "by the tones", (1.0, y, z + M.SHELF - 2.7), (M.TONES_AT - 1.5, y, z + M.SHELF - 0.4)))
    out.append(("rock", "further in", (2.5, y, z + 5.0), (7.0, y, z + 7.5)))
    for i in range(len(B.CLOUD)):
        x = M.TONES_AT + M.TONE * i
        out.append(("cloud", f"tone {i + 1}", (x + 0.6, y, z + M.SHELF - 1.7), (x + M.TONE - 0.6, y, z + M.SHELF - 0.3)))
    wide, deep = BANK
    for i in range(len(B.CLOUD)):
        x0, x1, z1 = M.CLOUD_AT + 2 * i, M.CLOUD_AT + wide - 2 * i, z + deep - 2 * i
        crest = i == len(B.CLOUD) - 1               # a step shows its front two cells, the crest all of its top
        out.append(("cloud", f"bank {i + 1}", (x0 + 0.5, y + i + 1, z + 0.5 if crest else z1 - 1.7),
                    (x1 - 0.5, y + i + 1, z1 - (0.5 if crest else 0.3))))
    return out


def camera(shot, size):
    """world -> (column, row) of a picture of `size` taken as build/render.py takes the shot."""
    pos, to = np.array(shot["pos"], float), np.array(shot["look_at"], float)
    fwd = (to - pos) / np.linalg.norm(to - pos)
    right = np.cross(fwd, (0.0, 1.0, 0.0))
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    half = size[1] / 2.0 / math.tan(math.radians(M.FOV) / 2.0)

    def carry(points):
        d = np.asarray(points, float) - pos
        depth = d @ fwd
        return np.stack([size[0] / 2.0 + (d @ right) / depth * half, size[1] / 2.0 - (d @ up) / depth * half], axis=1)
    return carry


def pixels(carry, a, b, size):
    """The pixels of the picture the patch from a to b falls on: a mask."""
    axes = [np.arange(min(p, q) + STEP / 2.0, max(p, q), STEP) if p != q else np.array([float(p)]) for p, q in zip(a, b)]
    grid = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
    at = np.floor(carry(grid)).astype(int)
    at = at[(at[:, 0] >= 0) & (at[:, 0] < size[0]) & (at[:, 1] >= 0) & (at[:, 1] < size[1])]
    mask = np.zeros((size[1], size[0]), bool)
    mask[at[:, 1], at[:, 0]] = True
    return mask


def sky(size):
    mask = np.zeros((size[1], size[0]), bool)
    mask[int(size[1] * 0.42):int(size[1] * 0.62), 10:70] = True
    return mask


def read(path, shot, marks=None):
    """{(group, name): luma} of one picture of the whole board."""
    image = np.asarray(Image.open(path).convert("RGB")).astype(float)
    size = (image.shape[1], image.shape[0])
    carry = camera(shot, size)
    masks = [((group, name), pixels(carry, a, b, size)) for group, name, a, b in patches()]
    masks.append((("sky", "left of the board"), sky(size)))
    luma = image @ COEF / 255.0
    if marks:
        marked = image.copy()
        for _, mask in masks:
            marked[mask] = marked[mask] * 0.5 + TINT * 0.5
        os.makedirs(marks, exist_ok=True)
        Image.fromarray(marked.round().astype(np.uint8)).save(os.path.join(marks, os.path.basename(path)))
    return {key: (float(luma[mask].mean()) if mask.any() else None) for key, mask in masks}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", nargs="?")
    ap.add_argument("--scene", default="obs_mat_board", help="whose pictures: the board, or a scene that compares versions on it")
    ap.add_argument("--marks", metavar="FOLDER", help="write the pictures here with the read pixels tinted")
    args = ap.parse_args()
    folder = args.folder or os.path.join(os.path.dirname(BUILD), "renders", args.scene)
    shots = {s["name"]: s for s in M.shots()}
    columns, missing = {}, []
    for name in LIGHTS:
        path = next((p for p in (os.path.join(folder, f"{name}.png"), os.path.join(folder, f"{args.scene}-{name}.png"))
                     if os.path.exists(p)), None)
        if path is None:
            missing.append(name)
            continue
        columns[name] = read(path, shots[name], args.marks)
    if not columns:
        sys.exit(f"measure: no picture of the whole board in {folder}")
    print(f"{args.scene}: Rec.601 luma, 0..1")
    print(f"{'':36s}" + "".join(f"{name + ' ' + str(shots[name]['time']):>14s}" for name in columns))
    for key in next(iter(columns.values())):
        values = [columns[name][key] for name in columns]
        print(f"{key[0]:8s}{key[1]:28s}" + "".join(f"{'-' if v is None else format(v, '.3f'):>14s}" for v in values))
    if missing:
        sys.exit(f"measure: no picture of {', '.join(missing)} in {folder}")


if __name__ == "__main__":
    main()
