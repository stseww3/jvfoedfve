import sys, itertools
sys.path.insert(0, "/tmp/c164_a1/proto")
from proj import project, W, H

def best(cx, pts, hs, zs, lys, lzs, margin=24, top=5):
    out = []
    for h, zc, ly, lz in itertools.product(hs, zs, lys, lzs):
        if lz >= zc - 2:
            continue
        got = project((cx, h, zc), (cx, ly, lz), pts)
        if any(q is None or not (margin <= q[0] <= W - margin and margin <= q[1] <= H - margin) for q in got):
            continue
        xs = [q[0] for q in got]; ys = [q[1] for q in got]
        out.append(((max(xs) - min(xs)) * (max(ys) - min(ys)), (cx, h, zc), (cx, ly, lz), (min(xs), max(xs), min(ys), max(ys))))
    out.sort(reverse=True)
    return out[:top]

def fr(a, b, step=0.5):
    n = int(round((b - a) / step))
    return [round(a + i * step, 2) for i in range(n + 1)]

jobs = {
    "ground_left": (14.0, [(0, 8, 0), (28, 8, 0), (-1, 0, 12), (29, 0, 12), (29, 1, 12), (-1, 0, 0)], fr(5, 12), fr(14, 26), fr(0, 4), fr(0, 8)),
    "ground_right": (54.5, [(31, 0, 1), (31, 0, 16), (46, 0, 16), (37, 0, 19), (30, 0, 21), (50, 0, 10), (78, 0, 10), (78, 5, 0), (58, 5, 0), (79, 0, 12), (30, 2, 0)], fr(8, 22), fr(22, 40), fr(0, 4), fr(0, 12)),
    "ground_rock": (9.0, [(0, 8, 0), (18, 8, 0), (0, 0, 3), (18, 0.5, 6), (15, 0.5, 6)], fr(4, 9), fr(9, 16), fr(1, 5), fr(0, 4)),
    "ground_snow": (24.0, [(20, 8, 0), (28, 8, 0), (20, 0, 9), (28, 0, 9), (21, 1, 12), (29, 1, 12)], fr(7, 14), fr(12, 22), fr(0, 4), fr(0, 8)),
    "ground_inlay": (38.5, [(31, 0, 1), (46, 0, 1), (31, 0, 16), (46, 0, 16), (30, 0, 21), (47, 0, 21), (38.5, 2, 0)], fr(9, 18), fr(18, 30), fr(0, 2), fr(4, 14)),
    "ground_cloud": (64.0, [(50, 0, 10), (78, 0, 10), (58, 5, 0), (70, 5, 0), (50, 0, 0), (78, 0, 0)], fr(5, 12), fr(14, 24), fr(0, 4), fr(0, 8)),
}
for name in (sys.argv[1:] or jobs):
    cx, pts, hs, zs, lys, lzs = jobs[name]
    print(name)
    for area, pos, look, box in best(cx, pts, hs, zs, lys, lzs):
        print("   area %7d  pos %s look %s  box x %d..%d y %d..%d" % (area, pos, look, *box))
