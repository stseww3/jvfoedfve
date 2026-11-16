"""The front elevation of the chart room's bookcase wall, texel for texel: the south face of every
part pasted where it stands, the nearest last. For looking at on the try branch only (the shared
machine draws nothing; a worker node runs this beside the room's shots).

    python -m scenes.obs.interiors._chartshelves_elev <folder>
"""
import os
import sys

import numpy as np
from PIL import Image

from ..common import palette as P
from . import _chartshelves as CS


def elevation():
    wide, high = int(CS.WIDE), int(CS.HIGH)
    img = np.zeros((high, wide, 4), dtype=np.uint8)
    todo, odd = [], []
    for piece in CS._pieces().values():
        m = piece.m
        faces = {(pi, f): (mat, w, h, grain, seed) for pi, f, mat, w, h, grain, seed in m.faces()}
        for pi, part in enumerate(m.parts):
            if (pi, "s") not in faces:
                continue
            mat, w, h, grain, seed = faces[(pi, "s")]
            size = (part["hi"][0] - part["lo"][0], part["hi"][1] - part["lo"][1])
            if abs(size[0] - w) > 1e-6 or abs(size[1] - h) > 1e-6:
                odd.append((m.name, pi, size, (w, h)))
            todo.append((part["hi"][2], part["lo"][0] + piece.mid, part["hi"][1] + piece.y0, mat.paint(w, h, grain, seed)))
    todo.sort(key=lambda t: t[0])
    for _z, u, y, tex in todo:
        h, w = tex.shape[:2]
        x0, y0 = int(np.floor(u + 0.5)), int(np.floor(high - y + 0.5))
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(wide, x0 + w), min(high, y0 + h)
        if xb <= xa or yb <= ya:
            continue
        sub = tex[ya - y0:yb - y0, xa - x0:xb - x0]
        mask = sub[..., 3] > 0
        img[ya:yb, xa:xb][mask] = sub[mask]
    return img, odd


def main(folder):
    os.makedirs(folder, exist_ok=True)
    img, odd = elevation()
    rgb = Image.fromarray(img, "RGBA").convert("RGB")
    wide, high = rgb.size
    rgb.resize((wide * 6, high * 6), Image.NEAREST).save(os.path.join(folder, "chartshelves-elev.png"))
    big = rgb.resize((wide * 10, high * 10), Image.NEAREST)
    big.crop((0, 0, wide * 5 + 100, high * 10)).save(os.path.join(folder, "chartshelves-elev-east.png"))
    big.crop((wide * 5 - 100, 0, wide * 10, high * 10)).save(os.path.join(folder, "chartshelves-elev-west.png"))
    pieces = CS._pieces()
    print(f"{len(pieces)} display entities; elements: "
          + " ".join(f"{p.m.name[len(CS.PREFIX):]}={len(p.m.parts)}" for p in pieces.values()))
    print("colours off the palette:", P.strays(img) or "none")
    print("front faces not on whole texels:", odd or "none")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../renders/_wip")
