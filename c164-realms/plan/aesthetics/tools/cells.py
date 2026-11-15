"""How busy each cell of a wall of panels is, measured on a picture taken square on.

    python cells.py <picture> <x0,y0,x1,y1> <columns> <rows> [threshold]

The box is the wall in the picture (pixels). Per cell: mean Rec.601 luma x100 / share of the
cell's pixels brighter than the threshold (0.22 by default), in percent; then the share per row
and how many cells have no bright pixel at all. Two pixels are left off each side of a cell.
"""
import sys

import numpy as np
from PIL import Image


def cells(path, box, columns, rows, threshold=0.22):
    im = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255
    luma = 0.299 * im[..., 0] + 0.587 * im[..., 1] + 0.114 * im[..., 2]
    x0, y0, x1, y1 = box
    w, h = (x1 - x0) / columns, (y1 - y0) / rows
    out = []
    for r in range(rows):
        row = []
        for c in range(columns):
            a = luma[int(round(y0 + r * h)) + 2:int(round(y0 + (r + 1) * h)) - 2,
                     int(round(x0 + c * w)) + 2:int(round(x0 + (c + 1) * w)) - 2]
            row.append((a.mean() * 100, (a > threshold).mean() * 100))
        out.append(row)
    return out


if __name__ == "__main__":
    picture, box, columns, rows = sys.argv[1], [float(v) for v in sys.argv[2].split(",")], int(sys.argv[3]), int(sys.argv[4])
    threshold = float(sys.argv[5]) if len(sys.argv) > 5 else 0.22
    grid = cells(picture, box, columns, rows, threshold)
    for row in grid:
        print(" ".join(f"{m:2.0f}/{b:2.0f}" for m, b in row))
    print("rows, bright %:", " ".join(f"{np.mean([b for _, b in row]):.1f}" for row in grid))
    flat = [b for row in grid for _, b in row]
    print(f"cells with no bright pixel: {sum(b < 1 for b in flat)} of {len(flat)}; under 8%: {sum(b < 8 for b in flat)}")
