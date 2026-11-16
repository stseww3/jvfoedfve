"""Re-measure the windows' brightness, in the cloud, against c177's ladder (group g2 #89/#90).

    python -m scenes.obs_mat_windows.brightness        prints the table and exits 1 if any tier is out

Lit windows are drawn at emission 15 with shade and ao off (materials/windows.py LIT), so what shows
on screen is exactly the texture colour: a lit window's average brightness is the Rec.601 luma of its
picture, bars included. (Check: #ffc65a reads 0.79, #caa356 reads 0.65, as c177 has it.) Dark windows
are ordinary blocks the sky multiplies, so their shown brightness is the texture luma times c177's
east-front multipliers.

c177's targets, whole window with the glazing bars counted in:
    LIT      ~0.65   (glass #ffc65a, kept; not raised to #ffe9a6)
    FROSTED  0.52 - 0.55
    CURTAIN  0.38 - 0.42
    DARK     ~0.08 shown (A),  ~0.05 (B)
    BLIND    ~0.073 shown (A)
Both versions of the lit windows sit on the same ladder.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from scenes.obs.common import palette as P
from scenes.obs.materials import windows as W

COEF = np.array([0.299, 0.587, 0.114])                 # Rec.601 luma, as c177 reads the pictures
SKY = {"A": np.array([0.25, 0.29, 0.44]), "B": np.array([0.15, 0.18, 0.30])}   # east front, c177 g2 #82/#117
TARGET = {"LIT": (0.62, 0.67), "FROSTED": (0.52, 0.55), "CURTAIN": (0.38, 0.42)}


def _list(x):
    return x if isinstance(x, list) else [x]


def _bars(version):
    m = np.zeros((W.TILE, W.TILE), bool)
    for x in W._BARS[version]["cols"]:
        m[:, x] = True
    for y in W._BARS[version]["rows"]:
        m[y, :] = True
    return m


def luma(pics, mask=None, mult=None):
    """Average Rec.601 luma (0-1) over one or more pictures; `mask` keeps pixels, `mult` scales rgb."""
    vals = []
    for px in _list(pics):
        rgb = np.asarray(px)[..., :3].astype(float)
        if mult is not None:
            rgb = rgb * mult
        rgb = rgb.reshape(-1, 3) if mask is None else rgb[mask]
        vals.append((rgb @ COEF).mean() / 255.0)
    return float(np.mean(vals))


def table():
    rows, bad = [], []
    for v in W.VERSIONS:
        glass = ~_bars(v)
        for role, face in (("LIT", W.lit_face(v)), ("FROSTED", W.frosted_face(v)), ("CURTAIN", W.curtain_face(v))):
            whole, only = luma(face), luma(face, glass)
            lo, hi = TARGET[role]
            ok = lo <= whole <= hi
            rows.append((v, role, whole, only, f"{lo:.2f}-{hi:.2f}", "ok" if ok else "OUT"))
            if not ok:
                bad.append(f"windows {v} {role}: whole {whole:.3f} not in {lo:.2f}-{hi:.2f}")
        for role, face, tgt in (("DARK", W.dark_face(v), 0.08), ("BLIND", W.blind_face(v), 0.073)):
            rows.append((v, role, luma(face, mult=SKY["A"]), luma(face, mult=SKY["B"]), f"~{tgt:.3f} (A)", "sky"))
    return rows, bad


def main():
    print(f"glass glow[2]={P.RAMPS['glow'][2]}  opal[0]={P.RAMPS['opal'][0]}  "
          f"night_glass[3,4]={P.RAMPS['night_glass'][3]},{P.RAMPS['night_glass'][4]}  bar iron[1]={P.RAMPS['iron'][1]}")
    print(f"{'ver':3} {'role':8} {'whole/shownA':>12} {'glass/shownB':>12}  {'target':>11}  flag")
    rows, bad = table()
    for v, role, a, b, tgt, flag in rows:
        print(f"{v:3} {role:8} {a:12.3f} {b:12.3f}  {tgt:>11}  {flag}")
    if bad:
        print("\nOUT OF LADDER:")
        for line in bad:
            print("  " + line)
        return 1
    print("\nall three lit tiers on c177's ladder, both versions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
