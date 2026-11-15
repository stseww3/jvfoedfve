"""Sheets a reviewer reads a picture from (cr3; machines and interiors). It renders nothing: it only
cuts, shrinks and lays side by side pictures that exist already, and counts pixels in them. Needs
numpy and Pillow, about a second a picture, so it may run on the shared machine.

    python plan/aesthetics/tools/cr3_sheet.py stamps <out.png> <picture> [<picture> ...] [--width 160]
    python plan/aesthetics/tools/cr3_sheet.py pair   <out.png> <picture> [<picture> ...] [--width 640] [--cols 2] [--names]
    python plan/aesthetics/tools/cr3_sheet.py crop   <out.png> <picture> x0,y0,x1,y1 [--scale 3]
    python plan/aesthetics/tools/cr3_sheet.py runs   <picture> x0,y0,x1,y1 [--across rows|cols] [--over 0.04]
    python plan/aesthetics/tools/cr3_sheet.py tones  <picture> [name=x0,y0,x1,y1 ...]

  stamps  every picture three times at stamp width: as it is, grey, and in two flat tones (split
          at Otsu's threshold): what is left of a machine's silhouette when the picture is small
  pair    pictures at one width in a grid, lettered A, B, C ... (the file names only with --names):
          for looking at the versions of a package before knowing which is which
  crop    a box of a picture, enlarged without smoothing: one screen pixel stays one square
  runs    how wide the things crossing a box are, in screen pixels: along every row (or column) of
          the box, the runs of pixels that differ from that line's median brightness by more than
          --over. A rod under two pixels wide is one that will flicker or break into dashes
  tones   brightness of the whole picture and of named boxes: median, mean, the darkest and the
          brightest hundredth, the share above 0.60 and below 0.03

A box is x0,y0,x1,y1 in pixels, or in fractions of the picture when no number is above 1.
Brightness is Rec.601 luma of the picture's own values, 0 to 1, the same as sky/_tones.py reads,
so the numbers of the two can be set side by side.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

COEF = np.array([0.299, 0.587, 0.114])
DEAD, BRIGHT = 0.03, 0.60
PAPER, INK = (16, 18, 28), (235, 235, 235)
GAP = 6


def load(path):
    return Image.open(path).convert("RGB")


def luma(picture):
    return (np.asarray(picture, dtype=np.float64) / 255.0) @ COEF


def box_of(text, size):
    numbers = [float(v) for v in text.split(",")]
    if len(numbers) != 4:
        raise SystemExit(f"a box is x0,y0,x1,y1, not {text!r}")
    x0, y0, x1, y1 = numbers
    if max(numbers) <= 1.0:
        x0, x1, y0, y1 = x0 * size[0], x1 * size[0], y0 * size[1], y1 * size[1]
    x0, x1 = sorted((int(round(x0)), int(round(x1))))
    y0, y1 = sorted((int(round(y0)), int(round(y1))))
    x0, y0 = max(0, min(size[0] - 1, x0)), max(0, min(size[1] - 1, y0))
    return x0, y0, max(x0 + 1, min(size[0], x1)), max(y0 + 1, min(size[1], y1))


def otsu(grey):
    """The threshold that parts a picture's greys into two groups as far apart as they go."""
    counts, edges = np.histogram(grey, bins=256, range=(0.0, 1.0))
    total = counts.sum()
    mids = (edges[:-1] + edges[1:]) / 2.0
    below = np.cumsum(counts)
    weight = np.cumsum(counts * mids)
    best, where = -1.0, 0.5
    for i in range(255):
        lo, hi = below[i], total - below[i]
        if lo == 0 or hi == 0:
            continue
        between = lo * hi * (weight[i] / lo - (weight[-1] - weight[i]) / hi) ** 2
        if between > best:
            best, where = between, edges[i + 1]
    return where


def shrink(picture, width):
    height = max(1, round(picture.size[1] * width / picture.size[0]))
    return picture.resize((width, height), Image.LANCZOS)


def stamps(out, paths, width):
    rows = []
    for path in paths:
        small = shrink(load(path), width)
        grey = luma(small)
        flat = np.where(grey > otsu(grey), 200, 30).astype(np.uint8)
        rows.append((small, Image.fromarray((grey * 255).astype(np.uint8)).convert("RGB"),
                     Image.fromarray(flat).convert("RGB")))
    height = max(r[0].size[1] for r in rows)
    sheet = Image.new("RGB", (3 * width + 4 * GAP, len(rows) * (height + GAP) + GAP), PAPER)
    for j, row in enumerate(rows):
        for i, panel in enumerate(row):
            sheet.paste(panel, (GAP + i * (width + GAP), GAP + j * (height + GAP)))
    sheet.save(out)
    for j, path in enumerate(paths):
        print(f"row {j + 1}: {path}")


def pair(out, paths, width, cols, names):
    panels = [shrink(load(path), width) for path in paths]
    height = max(p.size[1] for p in panels)
    label = 14
    lines = -(-len(panels) // cols)
    sheet = Image.new("RGB", (cols * (width + GAP) + GAP, lines * (height + label + GAP) + GAP), PAPER)
    draw = ImageDraw.Draw(sheet)
    for n, (panel, path) in enumerate(zip(panels, paths)):
        x, y = GAP + (n % cols) * (width + GAP), GAP + (n // cols) * (height + label + GAP)
        draw.text((x, y), Path(path).stem if names else chr(ord("A") + n), fill=INK)
        sheet.paste(panel, (x, y + label))
        print(f"{chr(ord('A') + n)}: {path}")
    sheet.save(out)


def crop(out, path, box, scale):
    picture = load(path)
    x0, y0, x1, y1 = box_of(box, picture.size)
    cut = picture.crop((x0, y0, x1, y1))
    cut.resize((cut.size[0] * scale, cut.size[1] * scale), Image.NEAREST).save(out)
    print(f"{path}: {x0},{y0} to {x1},{y1} ({x1 - x0} x {y1 - y0} pixels), enlarged {scale} times")


def runs(path, box, across, over):
    picture = load(path)
    x0, y0, x1, y1 = box_of(box, picture.size)
    grey = luma(picture)[y0:y1, x0:x1]
    if across == "cols":
        grey = grey.T
    widths = []
    for line in grey:
        differs = np.abs(line - np.median(line)) > over
        edges = np.flatnonzero(np.diff(np.concatenate(([0], differs.astype(np.int8), [0]))))
        widths.extend((edges[1::2] - edges[0::2]).tolist())
    if not widths:
        print(f"{path} {box}: nothing in the box differs from its lines' medians by more than {over}")
        return
    widths = np.array(widths)
    share = lambda n: 100.0 * np.count_nonzero(widths == n) / len(widths)
    print(f"{path} {x0},{y0},{x1},{y1} across {across}: {len(widths)} runs; median {np.median(widths):.1f} px, "
          f"mean {widths.mean():.2f}; 1 px {share(1):.0f}%, 2 px {share(2):.0f}%, 3 px {share(3):.0f}%, "
          f"wider {100.0 * np.count_nonzero(widths > 3) / len(widths):.0f}%")


def tones(path, probes):
    picture = load(path)
    grey = luma(picture)
    rgb = np.asarray(picture, dtype=np.float64) / 255.0

    def line(name, area, colour):
        lo, mid, hi = np.percentile(area, (1, 50, 99))
        mean = "#" + "".join(f"{int(round(c * 255)):02x}" for c in colour.reshape(-1, 3).mean(axis=0))
        print(f"  {name:<14} median {mid:.3f}  mean {area.mean():.3f}  darkest 1% {lo:.3f}  brightest 1% {hi:.3f}  "
              f"above {BRIGHT:.2f}: {100.0 * (area > BRIGHT).mean():.1f}%  below {DEAD:.2f}: "
              f"{100.0 * (area < DEAD).mean():.1f}%  {mean}  ({area.size} px)")

    print(f"{path} ({picture.size[0]} x {picture.size[1]})")
    line("picture", grey, rgb)
    for probe in probes:
        name, _, numbers = probe.partition("=")
        x0, y0, x1, y1 = box_of(numbers, picture.size)
        line(name, grey[y0:y1, x0:x1], rgb[y0:y1, x0:x1])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="what", required=True)
    p = sub.add_parser("stamps"); p.add_argument("out"); p.add_argument("pictures", nargs="+")
    p.add_argument("--width", type=int, default=160)
    p = sub.add_parser("pair"); p.add_argument("out"); p.add_argument("pictures", nargs="+")
    p.add_argument("--width", type=int, default=640); p.add_argument("--cols", type=int, default=2)
    p.add_argument("--names", action="store_true")
    p = sub.add_parser("crop"); p.add_argument("out"); p.add_argument("picture"); p.add_argument("box")
    p.add_argument("--scale", type=int, default=3)
    p = sub.add_parser("runs"); p.add_argument("picture"); p.add_argument("box")
    p.add_argument("--across", choices=("rows", "cols"), default="rows")
    p.add_argument("--over", type=float, default=0.04)
    p = sub.add_parser("tones"); p.add_argument("picture"); p.add_argument("probes", nargs="*")
    args = parser.parse_args()
    if args.what == "stamps":
        stamps(args.out, args.pictures, args.width)
    elif args.what == "pair":
        pair(args.out, args.pictures, args.width, args.cols, args.names)
    elif args.what == "crop":
        crop(args.out, args.picture, args.box, args.scale)
    elif args.what == "runs":
        runs(args.picture, args.box, args.across, args.over)
    else:
        tones(args.picture, args.probes)


if __name__ == "__main__":
    sys.exit(main())
