import math, sys
import numpy as np
from artkit import clouds
from artkit.canvas import Canvas
from scenes.obs.common import blocks as B

SQUASH, SINK = 0.7, 0.25

def puffs(c, x, y, z, heaps, wide, deep, seed=0, dither=0.9):
    high = int(max(lift + (SQUASH - SINK) * r for _, _, r, lift in heaps)) + 2
    f = clouds.Field(x - 2, y, z - 2, x + wide + 1, y + high, z + deep + 1)
    xs = np.arange(-2, wide + 2)[:, None] + 0.5
    zs = np.arange(-2, deep + 2)[None, :] + 0.5
    top = np.full((wide + 4, deep + 4), -1.0)
    for px, pz, r, lift in heaps:
        d2 = (xs - px) ** 2 + (zs - pz) ** 2
        h = lift - SINK * r + SQUASH * np.sqrt(np.maximum(r * r - d2, 0.0))
        top = np.where(d2 < r * r, np.maximum(top, h), top)
    ys = np.arange(high + 1)[None, :, None]
    f.solid |= ys < np.floor(top)[:, None, :] 
    n = f.write(c, seed=seed, dither=dither)
    return f, top, n

def show(heaps, wide, deep, seed=0, dither=0.9):
    c = Canvas()
    f, top, n = puffs(c, 0, 0, 0, heaps, wide, deep, seed, dither)
    tones = {b: i for i, b in enumerate(B.CLOUD)}
    print("blocks", n, "by tone (dark..light):", [sum(1 for v in c.b.values() if v.partition("[")[0] == b) for b in B.CLOUD])
    for zz in range(-2, deep + 2):
        row, row2 = "", ""
        for xx in range(-2, wide + 2):
            ht = max([yy for (a, yy, b) in c.b if a == xx and b == zz] or [-1])
            row += "." if ht < 0 else str(ht + 1)
            row2 += "." if ht < 0 else str(tones[c.b[(xx, ht, zz)].partition("[")[0]])
        print(row, " ", row2)
    return c

if __name__ == "__main__":
    heaps = eval(sys.argv[1])
    show(heaps, int(sys.argv[2]), int(sys.argv[3]), *(float(v) if "." in v else int(v) for v in sys.argv[4:]))
