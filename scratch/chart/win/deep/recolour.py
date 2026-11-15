"""Recolour the frosted linings of a rendered picture: what another glass tone would show.
Light script on one picture; the linings are found by hand-drawn boxes and by being grey."""
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, "/agent/repos/c164-chart-windows-f3-3477/c164-realms/build")
from scenes.obs.common import palette as P

COEF = np.array([0.2126, 0.7152, 0.0722])
src = "/tmp/c164_chart/f3/peers/m2/in-v10.png"
im = np.asarray(Image.open(src).convert("RGB")).astype(float)
# boxes of the linings in the picture (x0, y0, x1, y1), generous; the mask keeps the grey glass
BOXES = [(1068, 0, 1280, 440), (268, 95, 378, 420), (790, 250, 838, 420), (455, 255, 492, 410)]
WAS = np.array(P.colour("iron", 5), float)


def mask(im):
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    l = im @ COEF / 255.0
    grey = (np.abs(r - b) < 14) & (np.abs(r - g) < 10) & (l > 0.06) & (l < 0.2)
    m = np.zeros(im.shape[:2], bool)
    for x0, y0, x1, y1 in BOXES:
        m[y0:y1, x0:x1] = True
    return m & grey


def recolour(to):
    out = im.copy()
    m = mask(im)
    k = np.array(P.colour(*to), float) / WAS
    out[m] = np.clip(im[m] * k, 0, 255)
    return out, m


if __name__ == "__main__":
    names = {"iron4": ("iron", 4), "ng3": ("night_glass", 3), "snow4": ("snow", 4), "iron3": ("iron", 3), "snow0": ("snow", 0)}
    for name, to in names.items():
        out, m = recolour(to)
        Image.fromarray(out.astype(np.uint8)).save(f"/tmp/c164_chart/f3/win/deep/v10_{name}.png")
        box = out[0:440, 1068:1280].reshape(-1, 3)
        print(name, "mask px", int(m.sum()), "right lining mean luma", round(float((box @ COEF).mean() / 255), 3),
              "glass", [int(v) for v in out[m].mean(0)])
    Image.fromarray((mask(im) * 255).astype(np.uint8)).save("/tmp/c164_chart/f3/win/deep/mask.png")
