#!/usr/bin/env python3
"""The game's stars, as its code builds them: which lie on top of each other, and where they stand.

    python plan/parts/figs/sky_stars.py [--star-angle <degrees>] [--view v02_axis ...]
        [--scan] [--comet <bearing>,<elevation>] [--clear 2] [--least 0.02] [--picture <file>]

The game draws 1500 squares of one brightness (SkyRenderer.buildStars, seed 10842), turned with
`star_angle` about the north-south axis. A star adds star_brightness squared to the sky behind it
(the colour and its opacity are both the brightness, the blend adds). Where two squares overlap
the sums add up, so a pair shows as one star of twice the light: at 0.60 it adds 0.72 where its
neighbours add 0.36, at 0.80 it is white. The comet's head is to be the brightest point of the
sky (the director, 11-16), so the pairs must not stand near it.

Without --scan: the pairs at one star_angle (default: the one of sky/mood.py) with the share of
the smaller star that is covered, their bearing from due west towards the north and their
elevation, and the stars that stand within --clear of the comet's head; with --view also where
each falls in that board view's picture (1280x720), and with --picture the brightest value of
the picture there, to check the reading against the game.

    --scan    every whole star_angle that leaves no pair above the horizon and no star within
              --clear of the comet's head: how far below the horizon the highest pair stands and
              how far off the head the nearest star, the deepest pair first
    --comet   where the comet's head stands: bearing and elevation (default 0,41: read off the
              game's V2, where the head is 151 pixels above the middle of the picture)
    --clear   degrees round the head that are to hold no star (default 2)
    --least   leave out pairs that cover less than this share of the smaller star (default 0.02;
              the one pair there is covers 0.12 and shows one pixel of twice the light)

It prints; it judges nothing. Only numpy (and Pillow for --picture).
"""
import argparse
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJECT, "tools"))
sys.path.insert(0, os.path.join(PROJECT, "build"))

SEED, COUNT, FAR = 10842, 1500, 100.0


class Random:
    """java.util.Random, which the game's single-threaded source is."""

    def __init__(self, seed):
        self.s = (seed ^ 0x5DEECE66D) & ((1 << 48) - 1)

    def next(self, bits):
        self.s = (self.s * 0x5DEECE66D + 0xB) & ((1 << 48) - 1)
        return self.s >> (48 - bits)

    def float(self):
        return self.next(24) / float(1 << 24)

    def double(self):
        return ((self.next(26) << 27) + self.next(27)) / float(1 << 53)


def stars():
    """(direction, half side, turn) of every star, in the frame the game builds them in."""
    rnd, out = Random(SEED), []
    for _ in range(COUNT):
        v = np.array([rnd.float() * 2.0 - 1.0, rnd.float() * 2.0 - 1.0, rnd.float() * 2.0 - 1.0])
        half = 0.15 + rnd.float() * 0.1
        d2 = float(v @ v)
        if d2 <= 0.010000001 or d2 >= 1.0:
            continue
        turn = rnd.double() * math.pi * 2.0
        out.append((v / math.sqrt(d2), half, turn))
    return out


def corners(star, frame):
    """The star's square in a plane 100 away, as four points of `frame` (centre, right, up)."""
    c, half, turn = star
    # the game: rotateTowards(-c, up) then rotateZ(turn); any pair of axes square to c will do for
    # the outline once the turn is in, and pairs only need the outlines
    a = np.cross(c, (0.0, 1.0, 0.0) if abs(c[1]) < 0.99 else (1.0, 0.0, 0.0))
    a /= np.linalg.norm(a)
    b = np.cross(c, a)
    a, b = a * math.cos(turn) + b * math.sin(turn), b * math.cos(turn) - a * math.sin(turn)
    centre, right, up = frame
    out = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        p = c * FAR + a * (sx * half) + b * (sy * half)
        p = p * (FAR / float(p @ centre))          # onto the plane of the frame
        out.append((float(p @ right), float(p @ up)))
    return out


def clip(subject, clipper):
    """Sutherland-Hodgman: the part of one convex polygon inside another."""
    def area2(poly):
        return sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly)))

    if area2(clipper) < 0:
        clipper = clipper[::-1]
    out = subject
    for i in range(len(clipper)):
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        src, out = out, []
        if not src:
            break

        def side(p):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])

        for j in range(len(src)):
            p, q = src[j], src[(j + 1) % len(src)]
            sp, sq = side(p), side(q)
            if sp >= 0:
                out.append(p)
            if (sp >= 0) != (sq >= 0):
                t = sp / (sp - sq)
                out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return abs(area2(out)) / 2.0 if len(out) >= 3 else 0.0


def pairs(field, least):
    """Stars that lie on each other: (share of the smaller one covered, i, j, middle direction)."""
    dirs = np.array([s[0] for s in field])
    out = []
    reach = 2.0 * 0.25 * math.sqrt(2.0) / FAR
    for i in range(len(field)):
        near = np.nonzero(dirs[i + 1:] @ dirs[i] > math.cos(reach))[0] + i + 1
        for j in near:
            mid = dirs[i] + dirs[j]
            mid /= np.linalg.norm(mid)
            right = np.cross(mid, (0.0, 1.0, 0.0) if abs(mid[1]) < 0.99 else (1.0, 0.0, 0.0))
            right /= np.linalg.norm(right)
            frame = (mid, right, np.cross(mid, right))
            both = clip(corners(field[i], frame), corners(field[j], frame))
            small = (2.0 * min(field[i][1], field[j][1])) ** 2
            if both / small >= least:
                out.append((both / small, i, int(j), mid))
    return sorted(out, key=lambda p: -p[0])


def world(v, star_angle):
    """A direction of the stars' frame in the world: turned by star_angle about x, then a quarter
    turn about y (SkyRenderer.renderSunMoonAndStars)."""
    t = math.radians(star_angle)
    y, z = v[1] * math.cos(t) - v[2] * math.sin(t), v[1] * math.sin(t) + v[2] * math.cos(t)
    return np.array([-z, y, v[0]])


def where(d):
    """(bearing from due west towards the north, elevation) of a world direction, in degrees."""
    return math.degrees(math.atan2(-d[2], -d[0])), math.degrees(math.asin(max(-1.0, min(1.0, d[1]))))


def apart(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, float(a @ b)))))


def towards(bearing, elevation):
    b, e = math.radians(bearing), math.radians(elevation)
    return np.array([-math.cos(e) * math.cos(b), math.sin(e), -math.cos(e) * math.sin(b)])


def main(argv=None):
    ap = argparse.ArgumentParser(description="the game's stars: the pairs that lie on each other and where they stand")
    ap.add_argument("--star-angle", type=float, default=None)
    ap.add_argument("--view", action="append", default=[], help="a board view: where the pairs fall in its picture")
    ap.add_argument("--picture", help="a picture of the (first) view: the brightest value where each pair falls")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--comet", default="0,41")
    ap.add_argument("--clear", type=float, default=2.0)
    ap.add_argument("--least", type=float, default=0.02)
    args = ap.parse_args(argv)

    field = stars()
    found = pairs(field, args.least)
    head = towards(*[float(v) for v in args.comet.split(",")])
    dirs = [star[0] for star in field]
    print(f"{len(field)} stars; {len(found)} pairs cover {args.least:.2f} of the smaller star or more")

    if args.scan:
        rows = []
        for angle in range(360):
            highest = max((where(world(p[3], angle))[1] for p in found), default=-90.0)
            nearest = min(apart(world(d, angle), head) for d in dirs)
            rows.append((highest, nearest, angle))
        good = sorted(r for r in rows if r[0] < 0.0 and r[1] >= args.clear)
        print(f"star_angle: elevation of the highest pair, degrees from the comet's head ({args.comet}) to the nearest star")
        for highest, nearest, angle in good[:16]:
            print(f"  {angle:3d}: {highest:6.1f}  {nearest:4.1f}")
        print(f"  ({len(good)} of 360 angles keep every pair below the horizon and {args.clear:g} degrees round the head clear)")
        now = rows[0]
        print(f"    0: {now[0]:6.1f}  {now[1]:4.1f}")
        return 0

    angle = args.star_angle
    if angle is None:
        from scenes.obs.sky import mood
        angle = mood.STAR_ANGLE
    print(f"star_angle {angle:g}: share covered, bearing north of due west, elevation, degrees off the comet's head")
    cams = []
    if args.view:
        import boardshots as B
        for name in args.view:
            shot = [s for s, _, _ in B.views() if s["name"] == name]
            if not shot:
                raise SystemExit(f"no board view {name}")
            cams.append((name, B, B.frame(shot[0])))
    rgb = None
    if args.picture:
        from PIL import Image
        rgb = np.asarray(Image.open(args.picture).convert("RGB"), dtype=np.float64) / 255.0
    for share, i, j, mid in found:
        d = world(mid, angle)
        bearing, elevation = where(d)
        line = f"  {share:4.2f}  {bearing:7.1f} {elevation:6.1f}  {apart(d, head):5.1f} off"
        if elevation <= 0.0:
            line += "  (below the horizon)"
        for name, B, cam in cams:
            at = B.falls(cam, tuple(d))
            if at is not None and 0.0 <= at[0] <= 1.0 and 0.0 <= at[1] <= 1.0:
                x, y = at[0] * 1280.0, at[1] * 720.0
                line += f"  {name} ({x:.0f}, {y:.0f})"
                if rgb is not None and name == cams[0][0]:
                    h, w, _ = rgb.shape
                    px, py = int(round(x * w / 1280.0)), int(round(y * h / 720.0))
                    patch = rgb[max(0, py - 4):py + 5, max(0, px - 4):px + 5] @ np.array([0.299, 0.587, 0.114])
                    if patch.size:
                        line += f" brightest {patch.max():.2f}"
        print(line)
    close = sorted((apart(world(d, angle), head), k) for k, d in enumerate(dirs))
    close = [(off, k) for off, k in close if off <= args.clear]
    print(f"stars within {args.clear:g} degrees of the comet's head: {len(close)}"
          + "".join(f"\n  {off:4.2f} degrees off, {2.0 * field[k][1] / FAR * 180.0 / math.pi:.2f} degrees wide" for off, k in close))
    return 0


if __name__ == "__main__":
    sys.exit(main())
