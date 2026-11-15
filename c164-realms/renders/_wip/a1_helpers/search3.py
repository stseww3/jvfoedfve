import sys, itertools, math
sys.path.insert(0, "/tmp/c164_a1/proto")
from proj import project, W, H
def fr(a, b, step=0.5):
    n = int(round((b - a) / step)); return [round(a + i * step, 2) for i in range(n + 1)]
def best(cxs, pts, hs, zs, lys, lzs, margin=24, top=6):
    out = []
    for cx, h, zc, ly, lz in itertools.product(cxs, hs, zs, lys, lzs):
        if lz >= zc - 2: continue
        got = project((cx, h, zc), (cx, ly, lz), pts)
        if any(q is None or not (margin <= q[0] <= W - margin and margin <= q[1] <= H - margin) for q in got): continue
        xs = [q[0] for q in got]; ys = [q[1] for q in got]
        out.append(((max(xs) - min(xs)) * (max(ys) - min(ys)), (cx, h, zc), (cx, ly, lz), (min(xs), max(xs), min(ys), max(ys))))
    out.sort(reverse=True)
    return out[:top]
pts = [(31, 0, 1), (31, 0, 16), (46, 0, 16), (50, 0, 11), (78, 0, 11), (78, 0, 0), (58, 5, 0), (70, 5, 0), (38.5, 2, 0)]
for area, pos, look, box in best([53.0, 54.0, 54.5, 55.0], pts, fr(8, 20, 1.0), fr(16, 30, 1.0), [0.0, 2.0], fr(0, 12, 1.0)):
    pitch = math.degrees(math.atan2(pos[1] - look[1], pos[2] - look[2]))
    print("   area %7d  pos %s look %s pitch %.0f box x %d..%d y %d..%d" % (area, pos, look, pitch, *box))
