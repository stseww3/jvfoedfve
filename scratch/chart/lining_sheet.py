"""Enlarged sheet of the linings as a room wall shows them: ashlar piers between great windows of 3 by
6 blocks, everything at about the light the test room gives (a factor on the colours). Texture only,
for looking at a change before a render. Not part of the repo.

    python lining_sheet.py <out.png> [version] [factor]
"""
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, "/agent/repos/c164-chart-windows-f3-3477/c164-realms/build")

from scenes.obs.common import palette as P  # noqa: E402
from scenes.obs.materials import windows as W  # noqa: E402

out = sys.argv[1]
version = sys.argv[2] if len(sys.argv) > 2 else "a"
factor = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
T = W.TILE


def window(kind):
    """A window 3 by 6 as line() cuts it: the foot piece under the head piece."""
    if kind == "curtain":
        low, high = W.lining_picture(kind, 3, 3, 1, version), W.lining_picture(kind, 3, 3, 2, version)
    else:
        low, high = (W.lining_picture(kind, 3, 3, v % W.VARIANTS[kind], version) for v in (0, 1))
    return np.vstack([high, low])[..., :3].astype(float)


def dark():
    tiles = W.dark_face(version)
    rng = np.random.default_rng(3)
    return np.vstack([np.hstack([tiles[int(rng.integers(len(tiles)))] for _ in range(3)]) for _ in range(6)])[..., :3].astype(float)


pier = np.zeros((6 * T, T, 3))
pier[:] = P.colour("ashlar", 2)
pier[::8] = P.colour("ashlar", 1)           # courses, roughly
parts = [pier]
for kind in ("lit", None, "frosted", "curtain"):
    parts += [dark() if kind is None else window(kind), pier]
sheet = np.hstack(parts) * factor
img = Image.fromarray(sheet.round().clip(0, 255).astype(np.uint8))
img = img.resize((img.width * 4, img.height * 4), Image.NEAREST)
img.save(out)
print(out, img.size)
