#!/usr/bin/env python3
"""The sky of a board view read by elevation, in pictures of that view (plan/packages/sky/look.md).

    python plan/parts/figs/sky_west.py --view v01_arrival --bearing 25 <picture> [<picture> ...]
        [--elevations 5,10,15,20,30,40,50] [--square 24] [--wall] [--ring <y>,<near>,<far>]
        [--sheet <file.jpg>] [--shots <shots.json>]

Every picture has to be of the one view named (the five moments of the west, say). For each
elevation it takes the square of the picture where a direction falls, that many degrees up and
`bearing` degrees from due west (to the north; negative to the south), and gives the square's
median colour, its brightness (Rec.601, as sky/_tones.py) and its hue. Several bearings give a
table each; the sky set against the wall (--wall) is that of the first bearing. Elevations below 0 look
down, into the cloud sea. A direction outside the picture is left out.

The view is one of the board's (tools/boardshots.py: the name of its shot, its camera worked out
from the skeleton), or a shot of a list given with --shots. The picture is the game's or the
offline renderer's: 16:9, 77 degrees high.

    --wall   also the front of the main building (the four corners of it, from the skeleton, drawn
             in a little): its median brightness, to set against the sky behind the building
    --ring   a ring on a level plane round the camera: y (scene) of the plane and two distances on
             the ground. Along the bearings of --bearings (default every 15 degrees that falls in
             the picture) the square at the near distance, the square at the far one, and how far
             apart the two are. For the join of the block clouds and the vanilla cloud layer: the
             plane is the top of the sea, the distances lie either side of where the blocks end
    --sheet  the first picture with every square drawn on it, to see that none sits on a roof

It reads pictures and prints; it judges nothing. Only numpy and Pillow.
"""
import argparse
import colorsys
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJECT, "tools"))

import boardshots as B  # noqa: E402

WEIGHTS = np.array([0.299, 0.587, 0.114])


def shot_of(name, shots=None):
    if shots:
        with open(shots, encoding="utf-8") as fh:
            found = [s for s in json.load(fh) if s["name"] == name]
    else:
        found = [s for s, _, _ in B.views() if s["name"] == name]
    if not found:
        raise SystemExit(f"no shot {name}" + ("" if shots else "; the board has " + ", ".join(s["name"] for s, _, _ in B.views())))
    return found[0]


def towards(bearing, elevation):
    """A direction: `elevation` degrees up, `bearing` degrees from due west towards the north."""
    b, e = math.radians(bearing), math.radians(elevation)
    return (-math.cos(e) * math.cos(b), math.sin(e), -math.cos(e) * math.sin(b))


def bearing_of(cam):
    """How far from due west the view looks, in degrees towards the north."""
    _, f, _, _ = cam
    return math.degrees(math.atan2(-f[2], -f[0]))


def spot(cam, direction, size):
    """Where a direction falls, in pixels of a picture of `size`; None outside it."""
    at = B.falls(cam, direction)
    if at is None or not (0.0 <= at[0] <= 1.0 and 0.0 <= at[1] <= 1.0):
        return None
    return at[0] * size[0], at[1] * size[1]


def square(rgb, at, side):
    """The pixels of a square of `side` centred on a spot, clipped to the picture."""
    h, w, _ = rgb.shape
    x0, y0 = int(round(at[0] - side / 2.0)), int(round(at[1] - side / 2.0))
    x0, y0 = max(0, min(w - side, x0)), max(0, min(h - side, y0))
    return rgb[y0:y0 + side, x0:x0 + side].reshape(-1, 3), (x0, y0, x0 + side, y0 + side)


def read(pixels):
    """(hex colour, brightness, hue in degrees) of the median of some pixels."""
    mid = np.median(pixels, axis=0)
    hue = colorsys.rgb_to_hsv(*mid)[0] * 360.0
    return "#" + "".join(f"{int(round(c * 255.0)):02x}" for c in mid), float(mid @ WEIGHTS), hue


def cell(pixels):
    colour, tone, hue = read(pixels)
    return f"{colour} {tone:.2f} {hue:3.0f}"


def front(cam, size, inset=0.12):
    """The front of the main building as a polygon of the picture, drawn in a little; None when a
    corner is behind the camera."""
    corners = {name: point for name, point in B.landmarks() if name.startswith("front, ")}
    order = ["front, north end, foot", "front, north end, parapet", "front, south end, parapet", "front, south end, foot"]
    eye = cam[0]
    out = []
    for name in order:
        at = B.falls(cam, [corners[name][i] - eye[i] for i in range(3)])
        if at is None:
            return None
        out.append((at[0] * size[0], at[1] * size[1]))
    cx, cy = sum(p[0] for p in out) / 4.0, sum(p[1] for p in out) / 4.0
    return [(cx + (x - cx) * (1.0 - inset), cy + (y - cy) * (1.0 - inset)) for x, y in out]


def inside(polygon, size):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    return np.asarray(mask) > 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="the sky of a board view by elevation, and a ring on the cloud sea")
    ap.add_argument("pictures", nargs="+")
    ap.add_argument("--view", required=True, help="the shot's name: v01_arrival, v02_axis, v12_aerial ...")
    ap.add_argument("--shots", help="a shots.json to take the shot from instead of the board")
    ap.add_argument("--bearing", default=None,
                    help="degrees from due west towards the north for the elevations; several, comma separated, "
                         "give a table each (default: where the view looks)")
    ap.add_argument("--elevations", default="5,10,15,20,30,40,50")
    ap.add_argument("--square", type=int, default=24, help="side of the squares in pixels (default 24)")
    ap.add_argument("--wall", action="store_true", help="also the front of the main building")
    ap.add_argument("--ring", help="y,near,far: a ring on a level plane, either side of a join")
    ap.add_argument("--bearings", help="bearings of the ring, comma separated (default: every 15 degrees in the picture)")
    ap.add_argument("--sheet", help="write the first picture with the squares drawn on it")
    args = ap.parse_args(argv)

    shot = shot_of(args.view, args.shots)
    cam = B.frame(shot)
    looks = bearing_of(cam)
    bearings = [looks] if args.bearing is None else [float(v) for v in args.bearing.split(",") if v.strip()]
    pitch = math.degrees(math.asin(cam[1][1]))
    names = [os.path.splitext(os.path.basename(p))[0] for p in args.pictures]
    if len(set(names)) < len(names):
        names = [os.path.basename(os.path.dirname(os.path.abspath(p))) + "/" + n for p, n in zip(args.pictures, names)]
    pictures = [np.asarray(Image.open(p).convert("RGB"), dtype=np.float64) / 255.0 for p in args.pictures]
    size = (pictures[0].shape[1], pictures[0].shape[0])
    for name, rgb in zip(names, pictures):
        if (rgb.shape[1], rgb.shape[0]) != size:
            raise SystemExit(f"{name} is {rgb.shape[1]}x{rgb.shape[0]}, the first picture {size[0]}x{size[1]}")
    print(f"{shot['name']}: looks {abs(looks):.1f} degrees {'north' if looks >= 0 else 'south'} of due west, "
          f"{abs(pitch):.1f} degrees {'up' if pitch >= 0 else 'down'}; pictures {size[0]}x{size[1]}")
    print("each cell: median colour, brightness, hue")
    width = max(18, max(len(n) for n in names))
    drawn = []

    tones = {}
    for bearing in bearings:
        print(f"\nby elevation, {abs(bearing):.0f} degrees {'north' if bearing >= 0 else 'south'} of due west:")
        print(f"{'':>8}  " + "  ".join(f"{n:<{width}}" for n in names))
        for elevation in [float(e) for e in args.elevations.split(",") if e.strip()]:
            at = spot(cam, towards(bearing, elevation), size)
            if at is None:
                continue
            cells = []
            for name, rgb in zip(names, pictures):
                pixels, box = square(rgb, at, args.square)
                cells.append(cell(pixels))
                tones.setdefault(name, {}).setdefault(elevation, read(pixels)[1])
            drawn.append((box, f"{elevation:g}"))
            print(f"{elevation:>6g}°  " + "  ".join(f"{c:<{width}}" for c in cells))

    if args.wall:
        polygon = front(cam, size)
        if polygon is None:
            print("\nthe front of the main building is not in this view")
        else:
            mask = inside(polygon, size)
            print(f"\nthe front of the main building ({int(mask.sum())} px), against the sky behind it:")
            print(f"{'':>8}  " + "  ".join(f"{n:<{width}}" for n in names))
            walls = {name: read(rgb[mask]) for name, rgb in zip(names, pictures)}
            print(f"{'wall':>8}  " + "  ".join(f"{f'{c} {t:.2f} {h:3.0f}':<{width}}" for c, t, h in walls.values()))
            for elevation in (10.0, 15.0, 20.0):
                if all(elevation in tones.get(n, {}) for n in names):
                    print(f"{f'sky {elevation:g}°':>8}  " + "  ".join(
                        f"{f'{tones[n][elevation]:.2f} ({tones[n][elevation] - walls[n][1]:+.2f})':<{width}}" for n in names))
            drawn.append((polygon, "wall"))

    if args.ring:
        level, near, far = [float(v) for v in args.ring.split(",")]
        eye = cam[0]
        drop = level - eye[1]
        if args.bearings:
            around = [float(b) for b in args.bearings.split(",")]
        else:
            around = [b for b in range(-180, 180, 15)]
        print(f"\na ring on the plane y {level:g} ({-drop:.1f} below the eye), {near:g} and {far:g} blocks out:")
        print(f"{'bearing':>8}  " + "  ".join(f"{n:<{2 * width + 8}}" for n in names))
        for b in around:
            ends = []
            for distance in (near, far):
                flat = towards(b, 0.0)
                ends.append(spot(cam, (flat[0] * distance, drop, flat[2] * distance), size))
            if None in ends:
                continue
            cells = []
            for name, rgb in zip(names, pictures):
                a, box_a = square(rgb, ends[0], args.square)
                c, box_c = square(rgb, ends[1], args.square)
                (ca, ta, _), (cc, tc, _) = read(a), read(c)
                apart = max(abs(int(ca[i:i + 2], 16) - int(cc[i:i + 2], 16)) for i in (1, 3, 5))
                cells.append(f"{ca} {ta:.2f} | {cc} {tc:.2f} | {tc - ta:+.2f}, {apart} of 255")
            drawn.append((box_a, f"{b:g}"))
            drawn.append((box_c, ""))
            print(f"{b:>7g}°  " + "  ".join(f"{c:<{2 * width + 8}}" for c in cells))

    if args.sheet:
        picture = Image.fromarray(np.uint8(np.round(pictures[0] * 255.0)), "RGB")
        pen = ImageDraw.Draw(picture)
        for shape, label in drawn:
            if isinstance(shape, tuple):
                pen.rectangle(shape, outline=(255, 214, 64))
                pen.text((shape[2] + 3, shape[1]), label, fill=(255, 214, 64))
            else:
                pen.polygon(shape, outline=(255, 214, 64))
                pen.text((shape[0][0] + 3, shape[0][1] + 3), label, fill=(255, 214, 64))
        os.makedirs(os.path.dirname(os.path.abspath(args.sheet)), exist_ok=True)
        picture.save(args.sheet, quality=88)
        print(f"\nsheet {args.sheet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
