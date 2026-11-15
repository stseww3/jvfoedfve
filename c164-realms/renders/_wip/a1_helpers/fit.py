"""Scratch: for a pitch, the nearest camera on the board's middle line that holds the whole board."""
import math, sys
sys.path.insert(0, ".")
import numpy as np
import scenes.obs_mat_board as S

TY = math.tan(math.radians(77.0) / 2.0); TX = TY * 16.0 / 9.0
w = S.width(); K = len(S.TIERS); top = S.at(K - 1)[0] + S.N
pts = []
for x in (-1, w + 1):
    pts += [(x, 0, S.FRONT + 1), (x, 0, 0)]
    for k in range(K):
        y, z = S.at(k)
        pts += [(x, y, z), (x, y + S.N + 1, z - 1)]
pts = np.array(pts, float)

def fit(p, margin=0.06):
    p = math.radians(p)
    f = np.array([0, -math.sin(p), -math.cos(p)]); u = np.array([0, math.cos(p), -math.sin(p)]); r = np.array([1.0, 0, 0])
    best = None
    for d in np.arange(20, 200, 0.5):
        # camera = c0 - d f, c0 on the line x = w/2; slide c0 along u to balance top and bottom
        lo, hi = -100.0, 100.0
        for _ in range(40):
            s = (lo + hi) / 2
            cam = np.array([w / 2.0, 0, 0]) + s * u - d * f
            v = pts - cam
            dep = v @ f
            sy = (v @ u) / (dep * TY)
            if sy.max() + sy.min() > 0: lo = s
            else: hi = s
        v = pts - cam; dep = v @ f
        if dep.min() <= 1: continue
        sx = (v @ r) / (dep * TX); sy = (v @ u) / (dep * TY)
        if abs(sx).max() <= 1 - margin and abs(sy).max() <= 1 - margin:
            best = (d, cam, sx, sy, dep); break
    d, cam, sx, sy, dep = best
    look = cam + 60 * f
    gz = S.at(K - 1)
    def px(y, z):
        v = np.array([[0, y, z], [8, y, z]], float) - cam
        dd = v @ f
        return (v @ r)[1] / (dd[1] * TX) * 640 - (v @ r)[0] / (dd[0] * TX) * 640
    print(f"pitch {math.degrees(p):4.0f}: cam ({cam[0]:.1f}, {cam[1]:.1f}, {cam[2]:.1f}) look ({look[0]:.1f}, {look[1]:.1f}, {look[2]:.1f})"
          f"  |sx| {abs(sx).max():.2f} |sy| {abs(sy).max():.2f}  wall px: ground {px(4, 0):.0f}, glass {px(gz[0] + 4, gz[1]):.0f}"
          f"  wall height shown {math.cos(p):.2f}")
for p in (10, 17, 22, 27, 32, 37, 42, 50):
    fit(p)
