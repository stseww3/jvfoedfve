"""One board picture measured: python board.py <shot> <picture> [<picture> ...] (Rec.601 luma, 0..1)."""
import sys
import numpy as np
from PIL import Image

BOXES = {
    "v07": {"sun": (625, 205, 655, 238), "clock": (622, 453, 657, 487), "pier": (600, 315, 676, 425),
            "flight_n": (490, 500, 565, 612), "flight_s": (715, 500, 790, 612), "lining_l": (0, 125, 150, 562),
            "lining_r": (1125, 125, 1280, 562), "wall_l": (306, 375, 425, 462), "globe": (440, 585, 497, 637),
            "switchbd": (792, 515, 862, 650), "arch_n": (520, 470, 570, 500), "arch_s": (712, 470, 762, 500)},
    "v08": {"eyepiece": (328, 412, 431, 550), "tube": (500, 312, 588, 412), "slit": (600, 62, 700, 225),
            "pier": (494, 500, 744, 638), "floor": (125, 650, 1125, 720), "wall_l": (25, 312, 288, 562),
            "wall_r": (1000, 312, 1250, 475), "clock_l": (75, 469, 162, 575), "dial_r": (1188, 481, 1262, 588),
            "wheel": (1015, 560, 1062, 606)},
    "v09": {"table": (550, 362, 912, 431), "shelves": (269, 188, 619, 375), "floor_fg": (375, 550, 1000, 700),
            "floor_tbl": (538, 438, 912, 500), "moon": (1119, 206, 1280, 306), "board": (890, 302, 988, 365),
            "desk_l": (0, 362, 250, 588), "brass": (281, 288, 412, 412), "ceiling": (312, 25, 875, 138)},
    "v10": {"wall": (675, 206, 969, 388), "papers": (1038, 456, 1225, 525), "lamp_in": (156, 175, 238, 206),
            "floor_fg": (0, 525, 500, 720), "floor_wall": (675, 381, 950, 412), "floor_mid": (375, 400, 625, 500),
            "clocks": (0, 238, 362, 325), "chair": (850, 425, 969, 562), "drawers": (0, 375, 375, 450)},
}


def main():
    shot, names = sys.argv[1], sys.argv[2:]
    for name in names:
        a = np.asarray(Image.open(name).convert("RGB"), dtype=np.float64) / 255.0
        y = a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114
        h, w = y.shape
        top = y >= np.percentile(y, 99)
        ys, xs = np.nonzero(top)
        print(f"{name}: {w}x{h} mean {y.mean():.3f} median {np.median(y):.3f} under 0.03 {100 * (y < 0.03).mean():.1f}% "
              f"under 0.05 {100 * (y < 0.05).mean():.1f}% over 0.60 {100 * (y > 0.60).mean():.2f}% "
              f"brightest 1% at ({xs.mean() / w:.2f}, {ys.mean() / h:.2f})")
        for key, (x0, y0, x1, y1) in BOXES[shot].items():
            r = y[y0:y1, x0:x1]
            c = a[y0:y1, x0:x1].reshape(-1, 3)
            print(f"   {key:<10} median {np.median(r):.3f}  p10 {np.percentile(r, 10):.3f}  p90 {np.percentile(r, 90):.3f}  "
                  f"max {r.max():.3f}  rgb ({np.median(c[:, 0]):.2f}, {np.median(c[:, 1]):.2f}, {np.median(c[:, 2]):.2f})")


main()
