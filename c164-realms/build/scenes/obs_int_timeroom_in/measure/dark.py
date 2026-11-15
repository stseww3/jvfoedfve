"""Median luma and the share under 0.03 of a region and of the whole of some pictures."""
import sys
from PIL import Image
import numpy as np
REGIONS = {"ceiling": (300, 20, 980, 120), "floor near": (300, 640, 980, 715), "rack": (505, 280, 775, 430), "whole": (0, 0, 1280, 720)}
for path in sys.argv[1:]:
    im = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255.0
    luma = im @ np.array([0.299, 0.587, 0.114])
    out = []
    for name, (x0, y0, x1, y1) in REGIONS.items():
        r = luma[y0:y1, x0:x1].ravel()
        out.append("%s median %.3f, under 0.03: %4.1f%%" % (name, np.median(r), 100.0 * (r < 0.03).mean()))
    print(path, "|", " | ".join(out))
