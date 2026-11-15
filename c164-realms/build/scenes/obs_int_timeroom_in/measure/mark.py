"""Mark what is under 0.03 in a picture (red), write it at full size."""
import sys
from PIL import Image
import numpy as np
src, dst = sys.argv[1], sys.argv[2]
im = np.asarray(Image.open(src).convert("RGB")).astype(float) / 255.0
luma = im @ np.array([0.299, 0.587, 0.114])
out = np.clip(im * 2.5, 0, 1)
out[luma < 0.03] = (1.0, 0.0, 0.0)
Image.fromarray((out * 255).astype("uint8")).save(dst)
