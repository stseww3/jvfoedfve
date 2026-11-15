"""Enlarged sheet of the furnace window as a boiler bay shows it: three columns, the three furnace rows
under three rows of dark glass. For looking at a texture change before a render. Not part of the repo.

    python /tmp/c164_chart/f3/sheet.py <out stem> [version] [seed] [--rise 0:0,13:0,31:1,39:3,47:6] ...

Several --rise may be given: they are shown side by side, with the same draw of pictures.
Writes <stem>_near.png: a bay at 8 screen pixels to a texture pixel (as from a block or two away);
<stem>_far.png: two bays as a screen shows them from about 8, 16, 32 and 64 blocks (4, 2, 1, 0.5 screen
pixels to a texture pixel, box filtered), each enlarged again so the screen pixels can be told apart.
Which picture a block shows is drawn at random per block, as the game does by position.
"""
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, "/agent/repos/c164-chart-windows-f3-3477/c164-realms/build")

from scenes.obs.materials import windows as W  # noqa: E402

args = list(sys.argv[1:])
rises = []
while "--rise" in args:
    i = args.index("--rise")
    rises.append(tuple(tuple(float(v) for v in pair.split(":")) for pair in args[i + 1].split(",")))
    del args[i:i + 2]
out = args[0]
version = args[1] if len(args) > 1 else "a"
seed = int(args[2]) if len(args) > 2 else 0
rises = rises or [W._RISE]

T = W.TILE
PIER = np.array([52, 50, 50], float)        # a brick pier by night, roughly
SKY = np.array([0.25, 0.29, 0.44])
BACK = (16, 16, 20)


def sheet_of(rise, bays):
    W._RISE = rise
    rng = np.random.default_rng(seed)
    faces = W.furnace_face(version)             # [row][picture]
    dark = W.dark_face(version)
    parts = []
    for b in range(bays):
        rows = []
        for r in range(3):
            rows.append(np.hstack([dark[int(rng.integers(len(dark)))][..., :3] * SKY for _ in range(3)]))
        for r in reversed(range(len(faces))):
            rows.append(np.hstack([faces[r][int(rng.integers(len(faces[r])))][..., :3].astype(float)
                                   for _ in range(3)]))
        parts.append(np.tile(PIER, (6 * T, T // 2, 1)))
        parts.append(np.vstack(rows))
    parts.append(np.tile(PIER, (6 * T, T // 2, 1)))
    return np.hstack(parts)


def shown(sheet, per_texel, enlarge):
    h, w = sheet.shape[:2]
    img = Image.fromarray(sheet.round().astype(np.uint8))
    small = img.resize((int(w * per_texel), int(h * per_texel)), Image.BOX)
    return small.resize((small.width * enlarge, small.height * enlarge), Image.NEAREST)


def row(pictures, gap=16):
    w = sum(p.width for p in pictures) + gap * (len(pictures) + 1)
    h = max(p.height for p in pictures) + 2 * gap
    canvas = Image.new("RGB", (w, h), BACK)
    x = gap
    for p in pictures:
        canvas.paste(p, (x, gap))
        x += p.width + gap
    return canvas


def stack(pictures):
    canvas = Image.new("RGB", (max(p.width for p in pictures), sum(p.height for p in pictures)), BACK)
    y = 0
    for p in pictures:
        canvas.paste(p, (0, y))
        y += p.height
    return canvas


scale = 8 if len(rises) <= 2 else 5
near = row([shown(sheet_of(rise, 1), scale, 1) for rise in rises])
near.save(out + "_near.png")
far = stack([row([shown(sheet_of(rise, 2), per, enlarge) for per, enlarge in ((4, 1), (2, 2), (1, 4), (0.5, 4))])
             for rise in rises])
far.save(out + "_far.png")
print(out, near.size, far.size)
