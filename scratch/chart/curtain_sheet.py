"""Enlarged sheet of the curtain linings (and the frosted one) as the room shows them. Texture only.

    python curtain_sheet.py <out.png> [version] [factor] [scale]
"""
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, "/agent/repos/c164-chart-windows-f3-3477/c164-realms/build")

from scenes.obs.common import palette as P  # noqa: E402
from scenes.obs.materials import windows as W  # noqa: E402

out = sys.argv[1]
version = sys.argv[2] if len(sys.argv) > 2 else "a"
factor = float(sys.argv[3]) if len(sys.argv) > 3 else 0.45
scale = int(sys.argv[4]) if len(sys.argv) > 4 else 5
T = W.TILE
WALL = np.array(P.colour("ashlar", 2), float)


def pic(kind, w, h, ends):
    return W.lining_picture(kind, w, h, W.PIECES[kind].index(ends), version)[..., :3].astype(float)


def framed(px, pad=6):
    high, wide = px.shape[:2]
    sheet = np.zeros((6 * T + 2 * pad, wide + 2 * pad, 3))
    sheet[:] = WALL
    sheet[::8] = P.colour("ashlar", 1)
    top = sheet.shape[0] - pad - high
    sheet[top:top + high, pad:pad + wide] = px
    return sheet


tall = np.vstack([pic("curtain", 3, 3, "_head"), pic("curtain", 3, 3, "_foot")])
three = np.vstack([pic("curtain", 2, 2, "_head"), pic("curtain", 2, 2, ""), pic("curtain", 2, 2, "_foot")])
wide = np.hstack([pic("curtain", 3, 2, "_whole"), pic("curtain", 3, 2, "_whole")])
parts = [framed(tall), framed(three), framed(pic("curtain", 2, 2, "_whole")), framed(pic("curtain", 1, 1, "_whole")),
         framed(wide), framed(np.vstack([pic("frosted", 3, 3, "")] * 2))]
sheet = np.hstack(parts) * factor
img = Image.fromarray(sheet.round().clip(0, 255).astype(np.uint8))
img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
img.save(out)
print(out, img.size)
for kind in W.PIECES:
    for ends in W.PIECES[kind]:
        px = W.lining_picture(kind, 3, 3, W.PIECES[kind].index(ends), version)[..., :3].astype(float) / 255.0
        print(f"{kind:8s}{ends:7s} luma {float((px * (0.299, 0.587, 0.114)).sum(-1).mean()):.3f}")
