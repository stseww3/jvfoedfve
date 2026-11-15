"""As sheet.py's near view, but with the furnace window's dither taken from pairs of shuffles given
here, to compare ways of ordering the points. Not part of the repo.

    python sheet2.py <out.png> <set> [<set> ...]        a set is a name from SETS below
"""
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, "/agent/repos/c164-chart-windows-f3-3477/c164-realms/build")

from scenes.obs.materials import windows as W  # noqa: E402

T = W.TILE
PIER = np.array([52, 50, 50], float)
SKY = np.array([0.25, 0.29, 0.44])
BACK = (16, 16, 20)


def digits(s):
    return tuple(int(c) for c in s)


L3, L4 = "0362514", "0415263"          # 3y and 4y
L2, L5 = "0246135", "0531642"          # 2y and 5y
SETS = {
    # what the branch has now: any shuffles, a pair to each light
    "now": None,
    # one table a plain count by three, the other with a fault or two
    "faults": [(a, b) for a in ("0164235", "0245316", "0135642", "0216435", "0213564", "0246531", "0132465", "0164532")
               for b in (L3, L4)],
    # the same, every other light the other way round: the faults in the rows
    "mixed": [((a, b) if (i + j) % 2 == 0 else (b, a))
              for i, a in enumerate(("0164235", "0245316", "0135642", "0216435", "0213564", "0246531", "0132465", "0164532"))
              for j, b in enumerate((L3, L4))],
    # the plain lattice the first painting had
    "lattice": [("0415263", "0531642")],
    # c235's pair
    "c235": [("0361425", "0526314")],
}


def ranks_from(pairs):
    def ranks(serial, width, height):
        a, b = pairs[serial % len(pairs)]
        A, B = digits(a), digits(b)
        turn = (3 * serial) % 7
        return [[(A[x % 7] + B[y % 7] + turn) % 7 for x in range(width)] for y in range(height)]
    return ranks


def bay(version, seed):
    rng = np.random.default_rng(seed)
    faces = W.furnace_face(version)
    dark = W.dark_face(version)
    rows = [np.hstack([dark[int(rng.integers(len(dark)))][..., :3] * SKY for _ in range(3)]) for r in range(1)]
    for r in reversed(range(len(faces))):
        rows.append(np.hstack([faces[r][int(rng.integers(len(faces[r])))][..., :3].astype(float) for _ in range(3)]))
    body = np.vstack(rows)
    pier = np.tile(PIER, (body.shape[0], T // 4, 1))
    return np.hstack([pier, body, pier])


out, names = sys.argv[1], sys.argv[2:]
original = W._ranks
parts = []
for name in names:
    version = "a"
    if name.endswith(":b"):
        name, version = name[:-2], "b"
    W._ranks = original if SETS[name] is None else ranks_from(SETS[name])
    sheet = bay(version, 7)
    img = Image.fromarray(sheet.round().astype(np.uint8))
    parts.append(img.resize((img.width * 8, img.height * 8), Image.NEAREST))
canvas = Image.new("RGB", (sum(p.width for p in parts) + 16 * (len(parts) + 1), parts[0].height + 32), BACK)
x = 16
for p in parts:
    canvas.paste(p, (x, 16))
    x += p.width + 16
canvas.save(out)
print(out, canvas.size)
