#!/usr/bin/env python3
"""What moved between pictures taken from one place: how many places, where, how much.

    python tools/moved.py a.jpg b.jpg [c.jpg ...] [--out moved.jpg] [--level 30]

Two pictures of a view taken some seconds apart differ where something moves: a hand of a clock, a
flame, a wheel, smoke. A pixel has changed when one of its three colours differs by more than
--level (of 255; 30 is well over what the game's dithering and a JPEG do to a standing picture).
The picture is cut into cells of 8 pixels; cells with changed pixels that touch, corners too,
are one place. A place of fewer than 6 changed pixels is not counted: a star that twinkles is
no machine.

With more than two pictures a pixel has changed when it differs between any two that follow each
other. --out draws the first picture with a frame around every place and its number.

Used by looktrip.py (an author's look at a piece of work) and by the acceptance pictures of a
version (savetrip.py --pairs): `places(pictures)` returns the list, `draw` the picture.
"""
import argparse
import sys

import numpy as np
from PIL import Image, ImageDraw

CELL = 8
LEAST = 6
LEVEL = 30


def changed(pictures, level=LEVEL):
    """The pixels that differ between any two pictures that follow each other: a boolean array."""
    frames = [np.asarray(Image.open(p).convert("RGB"), dtype=np.int16) if isinstance(p, str)
              else np.asarray(p.convert("RGB"), dtype=np.int16) for p in pictures]
    mask = np.zeros(frames[0].shape[:2], dtype=bool)
    for a, b in zip(frames, frames[1:]):
        if a.shape != b.shape:
            raise ValueError("the pictures are not of one size")
        mask |= np.abs(a - b).max(axis=2) > level
    return mask


def places(pictures, level=LEVEL, cell=CELL, least=LEAST):
    """[(x0, y0, x1, y1, changed pixels)] of the places that moved, the largest first, and the
    share of the picture that changed."""
    mask = changed(pictures, level)
    h, w = mask.shape
    rows, cols = -(-h // cell), -(-w // cell)
    padded = np.zeros((rows * cell, cols * cell), dtype=bool)
    padded[:h, :w] = mask
    counts = padded.reshape(rows, cell, cols, cell).sum(axis=(1, 3))
    seen = np.zeros((rows, cols), dtype=bool)
    found = []
    for r, c in zip(*np.nonzero(counts)):
        if seen[r, c]:
            continue
        seen[r, c] = True
        stack, cells = [(r, c)], []
        while stack:
            y, x = stack.pop()
            cells.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < rows and 0 <= xx < cols and counts[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True
                        stack.append((yy, xx))
        pixels = int(sum(counts[y, x] for y, x in cells))
        if pixels < least:
            continue
        ys, xs = [y for y, _ in cells], [x for _, x in cells]
        found.append((int(min(xs)) * cell, int(min(ys)) * cell, min(w, (int(max(xs)) + 1) * cell),
                      min(h, (int(max(ys)) + 1) * cell), pixels))
    found.sort(key=lambda p: -p[4])
    return found, float(mask.mean())


def draw(picture, found, out, most=40):
    """The picture with a frame around every place that moved and its number beside it."""
    image = Image.open(picture).convert("RGB") if isinstance(picture, str) else picture.convert("RGB")
    pen = ImageDraw.Draw(image)
    for i, (x0, y0, x1, y1, _) in enumerate(found[:most], 1):
        pen.rectangle((x0 - 2, y0 - 2, x1 + 1, y1 + 1), outline=(255, 80, 60), width=2)
        pen.text((x0, max(0, y0 - 13)), str(i), fill=(255, 220, 90))
    image.save(out, quality=88)


def told(name, found, share, most=8):
    """One line for a report."""
    if not found:
        return f"{name}: nothing moved"
    listed = "; ".join(f"{i}. x {x0}-{x1}, y {y0}-{y1} ({n} px)" for i, (x0, y0, x1, y1, n) in enumerate(found[:most], 1))
    more = f"; and {len(found) - most} smaller" if len(found) > most else ""
    return f"{name}: {len(found)} place{'s' if len(found) != 1 else ''} moved, {share:.2%} of the picture: {listed}{more}"


def main():
    ap = argparse.ArgumentParser(description="what moved between pictures taken from one place")
    ap.add_argument("pictures", nargs="+")
    ap.add_argument("--out")
    ap.add_argument("--level", type=int, default=LEVEL)
    args = ap.parse_args()
    if len(args.pictures) < 2:
        sys.exit("two pictures at least")
    found, share = places(args.pictures, args.level)
    print(told(args.pictures[0], found, share))
    if args.out:
        draw(args.pictures[0], found, args.out)


if __name__ == "__main__":
    main()
