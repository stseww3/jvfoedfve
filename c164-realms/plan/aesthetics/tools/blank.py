#!/usr/bin/env python3
"""How much of a picture is blank: the share of its cells in which nothing is to be seen.

    python blank.py <picture> [<picture> ...] [--out DIR] [--before DIR] [--cell 40] [--edge 0.12] [--least 0.10]

The director's order of 11-16 12:47 (plan/fine.md, 6.3): the picture is cut into small cells, the
edges in every cell are measured, the sky left out; the emptiest cells are marked and one number is
reported, the share of blank cells. The number is to fall from version to version.

How it is measured (every figure is of a 1280x720 picture; other sizes are scaled to it):

  edge    The picture is smoothed over 3x3 pixels (a JPEG's noise is gone). At every pixel the slope
          is taken in each of the three colours, across two pixels, and the strongest colour counts.
          The slope is set against how bright the place is: the brightest colour averaged over 9x9
          pixels, plus 0.10. A pixel is an edge when the slope is over --edge (0.12) of that: on
          stone lit to 0.3 a step of 0.14 between two faces, in a dim room at 0.1 a step of 0.07,
          on a lit pane at 0.9 one of 0.36. A dark iron bar on stone, a brass rim, a glazing bar
          are edges; the joints and the grain of a plain wall, of paving, of boarding are not. Set
          against the brightness, a face gains nothing by a brighter lamp alone.
  cell    --cell pixels square (40: 32 x 18 cells). At ten blocks' distance a block is 45 pixels.
  sky     A cell is sky when six tenths of it are sky. A pixel is sky when it is joined, through
          pixels like itself, to the top or a side of the picture, and is one of three things:
          smooth and blue (no slope over 0.006 within two pixels; blue over red by 0.04 or more,
          blue 0.18 or more), which is the sky and the still cloud sea; smooth and rose (red
          0.30 or more, red over green by 0.02, blue not under green), which is the glow on the
          horizon; or light blue with no slope over 0.03 (blue 0.40 or more, over red by 0.10),
          which is the cloud sea where its billows show. A pocket of such pixels shut off from
          the edge (by a ridge line, a plume of smoke, a mast) is sky when it lies within 16
          pixels of sky and is light (blue 0.28 or more). Far ridges and smooth snow count as
          sky where they meet these terms. An island of up to four cells in the sky, a quarter
          of it sky (the comet, a cluster of stars), is sky. What is left of a cell that is
          partly sky is measured by itself: the edges are counted against the pixels that are
          not sky.
  against the sky
          Within 16 pixels of the sky an edge counts from a slope of 0.015 on, whatever the
          brightness: a lattice mast, a roof line, a far ridge stand dark on a dark sky with a
          third of the contrast things have on the ground, and they are what the picture is made
          of. (The sky itself has no slope over 0.003 but for its stars.)
  blank   A cell that is not sky and has fewer than --least (a tenth) of its pixels on an edge:
          those are the cells marked on the picture.
  share   Of the cells that are not sky, how many are blank. So that a cell at the line does not
          tip the number, a cell counts in part between half of --least and one and a half of it:
          with under 5 % of its pixels on an edge wholly, at 10 % as a half, over 15 % not at
          all. Two pictures of one view taken two seconds apart differ by 0.2 of a point on
          average and by 0.4 at most (B1, twelve views): a change of under one point is none.

What it prints for a picture: the share, the cells counted, and the blank places, the largest
first: a place is the largest box of nothing but blank cells, then the largest in what is left,
and so on (boxes in 1280x720 coordinates; one of 120 pixels square at ten blocks' distance is the
3x3 blocks of bare face the page allows no more of out of doors). With --out it saves
<name>_blank.jpg: the picture with every blank cell tinted red, the sky hatched blue, and the five
largest places framed and numbered. With --before DIR (the same pictures of the version before) it
prints the change of the share.

How the two figures were set (11-16, on the save pictures of A8, V2 to V5): 349 cells a reviewer
called empty (plain paving, the plain band and the base of the wall, the hut's walls) and 189 in
the parts he called worked (window bays, the canopy, the iron gates). With 0.12 and a tenth, nine
in ten of the empty ones come out blank, and a quarter of the others, which are the plain faces
between the windows. A slope not set against the brightness (over 0.04) sorts those cells as
well, but in a dim room it loses the railing and half of the telescope, and outdoors it lets the
paving under a lamp pass for its joints.

What the number is not: a count of parts. One long edge through a cell fills it; a wall drawn with
strong joints passes. It finds where nothing is, which is what it is for; whether what is there is
any good is looked at as before.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

W, H = 1280, 720
AROUND = 9              # pixels: the brightness of a place is taken over this many, square
DARK = 0.10             # added to it: in the dark a slope is not set against nothing
SMOOTH = 0.006
BILLOW = 0.03           # the cloud sea's billows: no slope over this
POCKET = 12             # coarse cells: a pocket of sky shut off from the edge is at least this large, ...
POCKET_BLUE = 0.28      # ... this light, and within NEAR_SKY coarse cells of sky
EDGE_BY_SKY = 0.015
NEAR_SKY = 2            # coarse cells: 16 pixels
BLUE_OVER_RED = 0.04
BLUE_LEAST = 0.18
SKY_SHARE = 0.6
COARSE = 8
ISLAND = 4              # cells: no more than this many, none on the bottom row, ...
ISLAND_SKY = 0.25       # ... and a quarter of them sky: an island in the sky is sky


def load(path):
    im = Image.open(path).convert("RGB")
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    return im, np.asarray(im, dtype=float) / 255.0


def box3(a):
    p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode="edge")
    return sum(p[i:i + a.shape[0], j:j + a.shape[1]] for i in range(3) for j in range(3)) / 9.0


def slope(a):
    """Per pixel, the slope of the strongest colour (a range of 1, per pixel)."""
    s = box3(a)
    gx = np.zeros_like(s)
    gy = np.zeros_like(s)
    gx[:, 1:-1] = (s[:, 2:] - s[:, :-2]) / 2.0
    gy[1:-1, :] = (s[2:, :] - s[:-2, :]) / 2.0
    return np.sqrt(gx ** 2 + gy ** 2).max(axis=2)


def spread(g, reach=2):
    """The largest value within `reach` pixels, sides and corners."""
    p = np.pad(g, reach, mode="edge")
    out = np.zeros_like(g)
    for i in range(2 * reach + 1):
        for j in range(2 * reach + 1):
            np.maximum(out, p[i:i + g.shape[0], j:j + g.shape[1]], out=out)
    return out


def groups(mask, corners=False):
    """Lists of (row, column) of the cells of `mask` that touch."""
    rows, cols = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    steps = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if corners:
        steps += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    found = []
    for r, c in zip(*np.nonzero(mask)):
        if seen[r, c]:
            continue
        seen[r, c] = True
        stack, cells = [(r, c)], []
        while stack:
            y, x = stack.pop()
            cells.append((y, x))
            for dy, dx in steps:
                ny, nx = y + dy, x + dx
                if 0 <= ny < rows and 0 <= nx < cols and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        found.append(cells)
    return found


def largest_box(mask):
    """(cells, r0, c0, r1, c1) of the largest box of True cells, None when there is none."""
    rows, cols = mask.shape
    height = np.zeros(cols, dtype=int)
    best = None
    for r in range(rows):
        height = np.where(mask[r], height + 1, 0)
        for c0 in range(cols):
            low = height[c0]
            for c1 in range(c0, cols):
                low = min(low, height[c1])
                if low == 0:
                    break
                area = low * (c1 - c0 + 1)
                if best is None or area > best[0]:
                    best = (area, r - low + 1, c0, r + 1, c1 + 1)
    return best


def boxes(blank, cell, least_cells=2):
    """The blank places: the largest box of blank cells, then the largest of the rest, and so on."""
    left = blank.copy()
    out = []
    while True:
        b = largest_box(left)
        if b is None or b[0] < least_cells:
            break
        area, r0, c0, r1, c1 = b
        left[r0:r1, c0:c1] = False
        out.append(dict(cells=area, box=(c0 * cell, r0 * cell, c1 * cell, r1 * cell),
                        members=[(r, c) for r in range(r0, r1) for c in range(c0, c1)]))
    return out


def mean_box(v, n):
    """The mean of `v` over n x n pixels around each pixel (n odd)."""
    r = n // 2
    p = np.pad(v, r, mode="edge")
    c = np.pad(np.cumsum(np.cumsum(p, axis=0), axis=1), ((1, 0), (1, 0)))
    return (c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]) / float(n * n)


def grow(mask, steps):
    """`mask` with the cells within `steps` of it, sides only."""
    out = mask.copy()
    for _ in range(steps):
        grown = out.copy()
        grown[1:, :] |= out[:-1, :]
        grown[:-1, :] |= out[1:, :]
        grown[:, 1:] |= out[:, :-1]
        grown[:, :-1] |= out[:, 1:]
        out = grown
    return out


def sky_of(a, g):
    """Two boolean pictures: the sky (smooth, blue, joined to the top or a side), and the sky with
    what lies within NEAR_SKY coarse cells of it."""
    red, green, blue = a[..., 0], a[..., 1], a[..., 2]
    around = spread(g)
    like = (around < SMOOTH) & (blue - red >= BLUE_OVER_RED) & (blue >= BLUE_LEAST)
    like |= (around < SMOOTH) & (red >= 0.30) & (red - green >= 0.02) & (blue >= green - 0.01)
    like |= (around < BILLOW) & (blue >= 0.40) & (blue - red >= 0.10)
    rows, cols = H // COARSE, W // COARSE
    share = like[:rows * COARSE, :cols * COARSE].reshape(rows, COARSE, cols, COARSE).mean(axis=(1, 3))
    coarse = share >= 0.5
    keep = np.zeros_like(coarse)
    for cells in groups(coarse, corners=True):
        if any(r == 0 or c == 0 or c == cols - 1 for r, c in cells):
            for r, c in cells:
                keep[r, c] = True
    near = grow(keep, NEAR_SKY)
    light = blue[:rows * COARSE, :cols * COARSE].reshape(rows, COARSE, cols, COARSE).mean(axis=(1, 3))
    for cells in groups(coarse & ~keep, corners=True):      # a pocket shut off from the edge
        if len(cells) >= POCKET and any(near[r, c] for r, c in cells) and \
                np.median([light[r, c] for r, c in cells]) >= POCKET_BLUE:
            for r, c in cells:
                keep[r, c] = True
    near = grow(keep, NEAR_SKY)
    one = np.ones((COARSE, COARSE), dtype=bool)
    return np.kron(keep, one), np.kron(near, one)


def measure(path, cell=40, edge=0.12, least=0.10):
    im, a = load(path)
    g = slope(a)
    sky, by_sky = sky_of(a, g)
    rows, cols = H // cell, W // cell
    cut = (slice(0, rows * cell), slice(0, cols * cell))
    is_edge = g > edge * (mean_box(a.max(axis=2), AROUND) + DARK)
    is_edge[:by_sky.shape[0], :by_sky.shape[1]] |= by_sky & (g[:by_sky.shape[0], :by_sky.shape[1]] > EDGE_BY_SKY)
    sky_share = sky[cut].reshape(rows, cell, cols, cell).mean(axis=(1, 3))
    dens = is_edge[cut].reshape(rows, cell, cols, cell).mean(axis=(1, 3))
    dens = np.minimum(1.0, dens / np.maximum(1.0 - sky_share, 1.0 - SKY_SHARE))     # against what is not sky
    is_sky = sky_share >= SKY_SHARE
    for cells in groups(~is_sky):                           # an island in the sky: the comet, a cluster of stars
        if len(cells) <= ISLAND and all(r < rows - 1 for r, _ in cells) and \
                np.mean([sky_share[r, c] for r, c in cells]) >= ISLAND_SKY:
            for r, c in cells:
                is_sky[r, c] = True
    blank = ~is_sky & (dens < least)
    places = boxes(blank, cell)
    counted = int((~is_sky).sum())
    part = np.clip(1.5 - dens / least, 0.0, 1.0)            # 1 under half of `least`, 0 over one and a half of it
    return dict(image=im, cell=cell, rows=rows, cols=cols, dens=dens, is_sky=is_sky, blank=blank, places=places,
                counted=counted, sky=int(is_sky.sum()), blanks=int(blank.sum()),
                share=(float(part[~is_sky].sum()) / counted if counted else 0.0))


def draw(m, path):
    im = m["image"].point(lambda v: min(255, int((v / 255.0) ** 0.75 * 255)))
    over = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    cell = m["cell"]
    for r in range(m["rows"]):
        for c in range(m["cols"]):
            x0, y0 = c * cell, r * cell
            if m["blank"][r, c]:
                d.rectangle((x0, y0, x0 + cell - 1, y0 + cell - 1), fill=(255, 40, 40, 70))
            elif m["is_sky"][r, c]:
                d.line((x0, y0 + cell - 1, x0 + cell - 1, y0), fill=(90, 140, 255, 110), width=1)
    for n, p in enumerate(m["places"][:5]):
        x0, y0, x1, y1 = p["box"]
        mem = set(p["members"])
        for r, c in mem:                                    # the outline of the place, cell by cell
            cx, cy = c * cell, r * cell
            if (r - 1, c) not in mem:
                d.line((cx, cy, cx + cell, cy), fill=(255, 255, 0, 255), width=2)
            if (r + 1, c) not in mem:
                d.line((cx, cy + cell - 1, cx + cell, cy + cell - 1), fill=(255, 255, 0, 255), width=2)
            if (r, c - 1) not in mem:
                d.line((cx, cy, cx, cy + cell), fill=(255, 255, 0, 255), width=2)
            if (r, c + 1) not in mem:
                d.line((cx + cell - 1, cy, cx + cell - 1, cy + cell), fill=(255, 255, 0, 255), width=2)
        r0, c0 = min(mem)
        d.rectangle((c0 * cell + 3, r0 * cell + 3, c0 * cell + 17, r0 * cell + 15), fill=(0, 0, 0, 200))
        d.text((c0 * cell + 7, r0 * cell + 3), str(n + 1), fill=(255, 255, 0, 255))
    out = Image.alpha_composite(im.convert("RGBA"), over).convert("RGB")
    d2 = ImageDraw.Draw(out)
    label = "blank %.0f%% of %d cells (sky %d left out)" % (m["share"] * 100, m["counted"], m["sky"])
    d2.rectangle((0, H - 16, 8 + 6 * len(label), H), fill=(0, 0, 0))
    d2.text((4, H - 14), label, fill=(255, 255, 0))
    out.save(path, quality=82)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pictures", nargs="+")
    ap.add_argument("--out", help="folder for <name>_blank.jpg")
    ap.add_argument("--before", help="folder with the same pictures of the version before")
    ap.add_argument("--cell", type=int, default=40)
    ap.add_argument("--edge", type=float, default=0.12)
    ap.add_argument("--least", type=float, default=0.10)
    ap.add_argument("--places", type=int, default=5, help="how many blank places to list")
    args = ap.parse_args()
    if args.out:
        os.makedirs(args.out, exist_ok=True)
    total_blank = total_counted = 0
    for path in args.pictures:
        m = measure(path, args.cell, args.edge, args.least)
        name = os.path.splitext(os.path.basename(path))[0]
        line = "%-18s blank %5.1f%%  (%3d of %3d cells marked; sky %3d)" % (name, m["share"] * 100, m["blanks"], m["counted"], m["sky"])
        if args.before:
            old = os.path.join(args.before, os.path.basename(path))
            if os.path.exists(old):
                b = measure(old, args.cell, args.edge, args.least)
                line += "  before %5.1f%%  change %+5.1f" % (b["share"] * 100, (m["share"] - b["share"]) * 100)
        print(line)
        for n, p in enumerate(m["places"][:args.places]):
            print("    %d. %3d cells  box %d,%d,%d,%d" % ((n + 1, p["cells"]) + p["box"]))
        total_blank += m["share"] * m["counted"]
        total_counted += m["counted"]
        if args.out:
            draw(m, os.path.join(args.out, name + "_blank.jpg"))
    if len(args.pictures) > 1 and total_counted:
        print("all %d pictures: blank %.1f%% of %d cells" % (len(args.pictures), 100.0 * total_blank / total_counted, total_counted))
    return 0


if __name__ == "__main__":
    sys.exit(main())
