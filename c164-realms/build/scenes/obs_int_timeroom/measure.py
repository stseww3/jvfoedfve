"""python -m scenes.obs_int_timeroom.measure <picture> [<picture> ...] [--shot v10]: a picture of the
room by numbers.

What the review reads off the game's picture of V10 (cr4, 11-16): is the instrument wall lighter
than the desk beside the camera, where do the lightest pixels of the picture lie, is the floor at
the foot of the wall lighter than the floor of the foreground. The regions are the room's own
places, projected into the picture with the shot's camera, so they hold for any picture of that
shot, the offline one or the game's. Luma is Rec. 709 of the sRGB values, 0 to 1, as tools/walk.py
measures it; the same of the linear values stands beside it in brackets.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

from scenes.obs.interiors import timeroom as T

FOV = 77.0              # degrees from the top of the picture to its bottom: the game's, and the offline renderer's
LIGHTEST = 0.01         # the share of the picture's pixels that count as its lightest
HERE = os.path.dirname(os.path.abspath(__file__))
WEIGHTS = np.array([0.2126, 0.7152, 0.0722])


def camera(shot):
    """The shot's camera: where it stands, and its forward, right and up."""
    with open(os.path.join(HERE, "shots.json"), encoding="utf-8") as fh:
        spec = next(s for s in json.load(fh) if s["name"] == shot)
    pos, at = np.array(spec["pos"], dtype=float), np.array(spec["look_at"], dtype=float)
    forward = (at - pos) / np.linalg.norm(at - pos)
    right = np.cross(forward, (0.0, 1.0, 0.0))
    right /= np.linalg.norm(right)
    return pos, forward, right, np.cross(right, forward)


def project(cam, size, point):
    """A point of the room in the picture, in pixels; None when it lies behind the camera."""
    pos, forward, right, up = cam
    d = np.array(point, dtype=float) - pos
    depth = float(d @ forward)
    if depth < 0.05:
        return None
    w, h = size
    half = math.tan(math.radians(FOV / 2.0))
    return (w / 2.0 * (1.0 + float(d @ right) / depth / (half * w / h)), h / 2.0 * (1.0 - float(d @ up) / depth / half))


def box(lo, hi):
    """The six faces of a box as lists of corners."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    c = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    return [[c[i] for i in face] for face in ((0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5))]


def regions():
    """{name: [faces]}: the places of the room that are measured, each a box or a flat patch."""
    feet = float(T.FEET)
    furniture = T.theirs("furniture")
    top = feet + (T.BOARD_TOP if furniture is None else furniture.TOP["writing_desk"])
    face = T.RACK_Z + 1.0
    half = T.DESK_DEEP / 2.0
    return {
        "wall": box((T.RACK_X[0], T.SILL, face), (T.RACK_X[1] + 1.0, T.CORNICE_Y, face)),
        "desk": box((T.DESK_X - half, top, T.DESK_Z - 1.0), (T.DESK_X + half, top + 1.0, T.DESK_Z + 1.0)),
        "bench": box((T.BENCH_X - half, top, T.BENCH_Z - 1.0), (T.BENCH_X + half, top + 0.5, T.BENCH_Z + 1.0)),
        "clocks": box((T.PANEL_W, T.DIAL_Y - 0.5, T.CLOCK_Z[0]), (T.PANEL_W, T.DIAL_Y + 0.5, T.CLOCK_Z[1] + 1.0)),
        "floor at the console": box((T.CONSOLE_X[0] - 1.0, feet, T.CONSOLE_Z + 1.0), (T.CONSOLE_X[1] + 2.0, feet, T.CONSOLE_Z + 3.0)),
        "floor at the bench": box((T.X0 + 2.0, feet, T.BENCH_Z - 1.5), (T.X0 + 4.0, feet, T.BENCH_Z + 1.5)),
        "floor by the door": box((T.DOOR_X[0], feet, T.Z1 - 3.0), (T.DOOR_X[1] + 2.0, feet, T.Z1 - 1.0)),   # V10's lower left
    }


def mask(cam, size, faces):
    """The pixels a region covers: a boolean array, None when no face of it is before the camera."""
    sheet = Image.new("1", size, 0)
    pen, drawn = ImageDraw.Draw(sheet), False
    for corners in faces:
        points = [project(cam, size, p) for p in corners]
        if all(p is not None for p in points):
            pen.polygon(points, fill=1)
            drawn = True
    return np.asarray(sheet, dtype=bool) if drawn else None


def measure(path, shot):
    """The lines for one picture."""
    picture = Image.open(path).convert("RGB")
    a = np.asarray(picture, dtype=np.float64) / 255.0
    luma = a @ WEIGHTS
    linear = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4) @ WEIGHTS
    cam, size = camera(shot), picture.size
    lines, got, masks = [f"{os.path.basename(path)} ({shot}, {size[0]}x{size[1]}): whole picture {luma.mean():.3f} [{linear.mean():.3f}]"], {}, {}
    for name, faces in regions().items():
        m = mask(cam, size, faces)
        if m is None or not m.any():
            lines.append(f"  {name}: not in the picture")
            continue
        masks[name] = m
        got[name] = (float(luma[m].mean()), float(linear[m].mean()))
        lines.append(f"  {name}: {got[name][0]:.3f} [{got[name][1]:.3f}], median {float(np.median(luma[m])):.3f}, "
                     f"the lightest tenth {float(np.quantile(luma[m], 0.9)):.3f}, {int(m.sum())} px")
    cut = np.quantile(luma, 1.0 - LIGHTEST)
    lightest = luma >= cut
    ys, xs = np.nonzero(lightest)
    shares = ", ".join(f"{name} {float((lightest & m).sum()) / float(lightest.sum()):.2f}" for name, m in masks.items()
                       if not name.startswith("floor"))
    lines.append(f"  the lightest {LIGHTEST:.0%} (from {cut:.3f} up): middle at ({xs.mean() / size[0]:.2f}, {ys.mean() / size[1]:.2f}); of it on: {shares}")
    if "wall" in got and "desk" in got:
        lines.append(f"  wall against desk: {got['wall'][0] / got['desk'][0]:.2f} [{got['wall'][1] / got['desk'][1]:.2f}]")
    if "floor at the console" in got and "floor by the door" in got:
        ratio = [got["floor at the console"][k] / got["floor by the door"][k] for k in (0, 1)]
        lines.append(f"  floor at the console against floor by the door: {ratio[0]:.2f} [{ratio[1]:.2f}]")
    return lines


def main(argv):
    shot, paths = "v10", []
    for arg in argv:
        if arg.startswith("--shot="):
            shot = arg.split("=", 1)[1]
        else:
            paths.append(arg)
    if not paths:
        print(__doc__)
        return 2
    for path in paths:
        print("\n".join(measure(path, shot)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
