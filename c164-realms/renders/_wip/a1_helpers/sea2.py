import sys
import numpy as np
from artkit import clouds
from artkit.canvas import Canvas
from scenes.obs.common import blocks as B

def piece(c, x, y, z, wide, deep, seed=1, under=2, rim=4.0, base=0.0, dither=0.9, **how):
    f = clouds.Field(x, y - under, z, x + wide - 1, y + 12, z + deep - 1)
    def keep_out(X, Z):
        d = np.minimum(np.minimum(X - x, x + wide - 1 - X), np.minimum(Z - z, z + deep - 1 - Z))    # cells from the edge
        return np.clip(1.0 - (d + 0.5) / rim, 0.0, 0.95)
    f.sea(y + base, seed=seed, keep_out=keep_out, **how)
    f.solid[:, :under, :] = True
    tmp = Canvas()
    f.write(tmp, seed=seed, dither=dither)
    n = 0
    for (bx, by, bz), state in tmp.b.items():
        if by >= y:
            c.b[(bx, by, bz)] = state
            n += 1
    return f, n

def show(wide, deep, seed, **how):
    c = Canvas()
    f, n = piece(c, 0, 0, 0, wide, deep, seed, **how)
    tones = {b: i for i, b in enumerate(B.CLOUD)}
    print("seed", seed, how, "blocks", n, "by tone (dark..light):", [sum(1 for v in c.b.values() if v.partition('[')[0] == b) for b in B.CLOUD])
    for zz in range(deep):
        row, row2 = "", ""
        for xx in range(wide):
            ht = max([yy for (a, yy, b) in c.b if a == xx and b == zz] or [-1])
            row += "." if ht < 0 else "%x" % (ht + 1)
            row2 += "." if ht < 0 else str(tones[c.b[(xx, ht, zz)].partition("[")[0]])
        print(row, " ", row2)

if __name__ == "__main__":
    for seed in (int(v) for v in sys.argv[1].split(",")):
        show(28, 20, seed, **eval("dict(%s)" % sys.argv[2]))
