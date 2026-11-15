"""Review mock-up (not part of any package): old copper variants as flat tiles under the light
factors measured in renders/obs_mat_brass (lamp: copper_twins; sky: roof). Writes two pictures
into the folder it is run from:  cd build && PYTHONPATH=. python ../plan/aesthetics/tools/mock_copper.py"""
import numpy as np
from PIL import Image, ImageDraw
from scenes.obs.materials import brass_oldcopper_small as m
from scenes.obs.common import palette as P
T = 16
C = m.C
V = [P.colour("verdigris", n) for n in range(5)]

def copper(seed, body=2, green=0.0, pits=0.04):
    lo, hi = max(0, body - 1), min(4, body + 1)
    px = m._worn(C, body, seed, pits=pits, light=0.015)
    m._raised(px, 0, 0, T, T, C[hi], C[lo])
    if green:
        yy, xx = np.mgrid[0:T, 0:T]
        roll = m._dice(xx, yy, seed + 77)
        seam = ((yy == T - 2) & (xx > 0) & (xx < T - 1)) | ((xx == T - 2) & (yy > 0) & (yy < T - 1))
        rim = ((yy == T - 1) | (xx == T - 1))
        px[seam & (roll < green * 0.5)] = (*V[0], 255)
        px[rim & (roll < green * 1.6)] = (*V[0], 255)
    return px

def cut(seed, body=2, green=0.0, pits=0.03):
    lo, hi = max(0, body - 1), min(4, body + 1)
    px = np.zeros((T, T, 4), np.uint8)
    for n, (x, y) in enumerate(((0, 0), (8, 0), (0, 8), (8, 8))):
        px[y:y + 8, x:x + 8] = m._worn(C, body, seed * 4 + n, 8, 8, pits=pits, light=0.01)
        m._raised(px, x, y, x + 8, y + 8, C[hi], C[lo])
    if green:
        yy, xx = np.mgrid[0:T, 0:T]
        roll = m._dice(xx, yy, seed + 91)
        rim = ((yy % 8 == 7) | (xx % 8 == 7))
        px[rim & (roll < green * 1.6)] = (*V[0], 255)
    return px

def wall(fn, n=4, **kw):
    vs = [fn(s, **kw) for s in (1, 2, 3)]
    out = np.zeros((T*n, T*n, 4), np.uint8)
    for j in range(n):
        for i in range(n):
            out[j*T:(j+1)*T, i*T:(i+1)*T] = vs[(i*7 + j*3 + (i*j) % 2) % 3]
    return out[..., :3]

LIGHTS = {"lamp": (0.73, 0.66, 0.68), "sky": (0.33, 0.385, 0.57)}
variants = [("now C2", dict(body=2)), ("A  C1", dict(body=1)),
            ("B  C2+green", dict(body=2, green=0.30)), ("C  C1+green", dict(body=1, green=0.30))]
N, K = 4, 3.75
cell = int(T*N*K)
for lname, f in LIGHTS.items():
    sheet = Image.new("RGB", (len(variants)*(cell+10), 2*(cell+18)), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    for c, (vname, kw) in enumerate(variants):
        for k, fn in enumerate((copper, cut)):
            a = wall(fn, N, **kw).astype(float) * np.array(f)
            im = Image.fromarray(a.clip(0, 255).astype(np.uint8)).resize((cell, cell), Image.NEAREST)
            x, y = 5 + c*(cell+10), k*(cell+18) + 16
            sheet.paste(im, (x, y))
            d.text((x, y - 13), f"{vname} / {'sheet' if k == 0 else 'cut'} / {lname}", fill=(235, 235, 235))
    sheet.save(f"mock_copper_{lname}.png"); print(lname, sheet.size)
