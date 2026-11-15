"""Mean luma (Rec.601) and mean colour of a few regions of a V10 picture."""
import sys
from PIL import Image
import numpy as np
REGIONS = {
    "floor near": (300, 640, 980, 715),
    "floor mid": (420, 520, 860, 580),
    "floor far": (540, 440, 740, 465),
    "rack": (505, 280, 775, 430),
    "ceiling": (300, 20, 980, 120),
    "left wall near": (20, 150, 200, 400),
    "right window": (1040, 150, 1240, 400),
    "whole": (0, 0, 1280, 720),
}
for path in sys.argv[1:]:
    im = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255.0
    print(path)
    for name, (x0, y0, x1, y1) in REGIONS.items():
        r = im[y0:y1, x0:x1].reshape(-1, 3)
        luma = r @ np.array([0.299, 0.587, 0.114])
        print("  %-15s luma %.3f  p10 %.3f p90 %.3f  rgb (%.2f %.2f %.2f)" % (name, luma.mean(), np.percentile(luma, 10), np.percentile(luma, 90), *r.mean(axis=0)))
