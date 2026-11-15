"""Brightness of snow, rock, cloud tones and sky in a picture of the whole board (all, all_b, all_c)."""
import sys
sys.path.insert(0, "/tmp/c164_a1/proto")
import numpy as np
from PIL import Image
from proj import project
from scenes import obs_mat_board as M
from scenes.obs.common import blocks as B

path, name = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "all")
shot = next(s for s in M.shots() if s["name"] == name)
a = np.asarray(Image.open(path).convert("RGB")).astype(float)


def mean(p, q, label):
    (x0, y0), (x1, y1) = project(shot["pos"], shot["look_at"], [p, q])
    x0, x1 = sorted((int(round(x0)), int(round(x1))))
    y0, y1 = sorted((int(round(y0)), int(round(y1))))
    px = a[y0:max(y1, y0 + 2), x0:max(x1, x0 + 2)].reshape(-1, 3)
    rgb = px.mean(axis=0)
    lum601 = (px @ np.array([0.299, 0.587, 0.114])) / 255.0
    print(f"{label:28s} {lum601.mean():.3f}  top 1% {np.percentile(lum601, 99):.3f}  rgb {tuple(int(round(v)) for v in rgb)}  ({x0},{y0})..({x1},{y1})")


S = M.SNOW_AT
mean((S + 2, 6, 1), (S + 6, 2, 1), "snow wall, its face")
mean((S + 1.5, 0.5, 5.2), (S + 6.5, 0.5, 5.8), "drift, four layers deep")
mean((S + 1.5, 0.125, 8.2), (S + 6.5, 0.125, 8.8), "drift, one layer deep")
mean((S + 1.5, 1.0, 1.2), (S + 6.5, 1.0, 1.8), "drift, eight layers deep")
for i, block in enumerate(B.CLOUD):
    x = M.TONES_AT + M.TONE * i
    mean((x + 0.6, 0, M.SHELF - 1.7), (x + 3.4, 0, M.SHELF - 0.3), f"cloud tone {i} in the rock")
for i, block in enumerate(B.CLOUD):
    x0, x1, z1 = M.CLOUD_AT + 2 * i, M.CLOUD_AT + 28 - 2 * i, 11 - 2 * i
    if i < 4:
        mean((x0 + 0.4, i + 1, z1 - 1.7), (x1 - 0.4, i + 1, z1 - 0.3), f"cloud bank, step {i} (top)")
    else:
        mean((x0 + 0.5, i + 1, 0.5), (x1 - 0.5, i + 1, z1 - 0.5), f"cloud bank, crest {i}")
mean((1.0, 0, 9.3), (6.5, 0, 11.6), "rock floor, beside the tones")
mean((2.5, 0, 5.0), (7.0, 0, 7.5), "rock floor, further in")
h, w = a.shape[:2]
px = a[int(h * 0.42):int(h * 0.62), 10:70].reshape(-1, 3)
print(f"{'sky, left of the board':28s} {((px @ np.array([0.299, 0.587, 0.114])) / 255.0).mean():.3f}  rgb {tuple(int(round(v)) for v in np.median(px, axis=0))} (median)")
