"""Scratch, never delivered: what the wiring changes in the hall's pictures, in numbers.
python build/scenes/obs_int_starhall/wiring_look.py <folder of look pictures>   (from c164-realms)
Compares renders/<scene>/<shot>.png (the hall without the wiring) with <folder>/<scene>-<shot>.png."""
import sys

import numpy as np
from PIL import Image

PIER = {"v7": (600, 330, 680, 400), "v7_in": (590, 250, 690, 360)}     # a patch of the pier's east face


def luma(a):
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]) / 255.0


def main(folder):
    for scene in ("obs_int_starhall", "obs_int_starhall_b"):
        for shot in ("v7", "v7_in", "west", "aisle_n", "aisle_s"):
            a = np.asarray(Image.open(f"renders/{scene}/{shot}.png").convert("RGB")).astype(float)
            b = np.asarray(Image.open(f"{folder}/{scene}-{shot}.png").convert("RGB")).astype(float)
            mask = np.abs(a - b).max(axis=2) > 6
            n = int(mask.sum())
            line = f"{scene} {shot}: {n} px changed"
            if n:
                lb = luma(b)[mask]
                line += f", luma p50 {np.percentile(lb, 50):.3f} p90 {np.percentile(lb, 90):.3f} max {lb.max():.3f}"
            if shot in PIER:
                x0, y0, x1, y1 = PIER[shot]
                face = float(np.percentile(luma(b[y0:y1, x0:x1]), 50))
                over = int((mask & (luma(b) > face)).sum())
                line += f"; pier's face {face:.3f}, {over} px of the wiring over it"
            print(line)


if __name__ == "__main__":
    main(sys.argv[1])
