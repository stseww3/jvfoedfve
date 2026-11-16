"""Read the brightness of the clocks off this scene's own pictures (cr2 and cr3, 11-15).

    python -m scenes.obs_mach_clocks.measure [folder] [--scene obs_mach_clocks_b] [--marks folder]

folder holds the pictures as tools/selfshots.py leaves them: <shot>.png (renders/<scene>/, the
default) or <scene>-<shot>.png (renders/_wip/). Every number is the Rec.601 luma, 0..1, of the
pixels a piece covers in a picture: the piece is laid out in the scene's own coordinates, its
points are carried into the picture with the camera of the shot, and the median of the pixels they
fall on is taken (the median of a dial is its enamel: the marks and the hands are the smaller part).
--marks writes each picture again with the measured pixels tinted, to see that a region sits on its
piece.

What is asked of the numbers:
  dial        the enamel of a tower dial reads 0.30..0.40; the east and the south dial, in the one
              picture that holds both, differ by no more than 0.03
  ladder      on the east face the dial stands between the stone of the wall and the lit frosted
              window: stone < dial < window
  ball        the time ball is lighter than the sky round it by 0.05 or more (asked of the colour
              that hangs on the tower, clock.BALL; of the other one the number is only printed);
              seen from below, the darkest tenth of its underside is not under 0.05 (no black cap
              of iron on it)
  master      from V7 the master dial reads 0.35 or more, its enamel (the median) and the whole
              dial with its marks and hands (the mean) alike: it is what is seen first there
              (A0, 11-16). The orrery's sun is a stand-in in this scene; its number is printed
  plinth      from V7 the two brass lines of the plinth are lighter than the wood between them and
              than the slate step under the clock by 0.05 or more: the plinth is drawn in front of
              the dark foot of the pier (cr3, 11-16)
  case        the darkest hundredth of the master clock's case is not under 0.03: no black hole
  foot        from the door's axis (master_door), the pale floor in front of the clock's step
              against the same stone four blocks out; a number to look at, no limit (a pool of
              light with no lamp to be seen is what it would show). V7 looks up since it moved
              two blocks in (A0, 11-16) and holds no floor farther out than the clock's step
Exit 1 when a number is out or a picture is missing.
"""
import argparse
import importlib
import json
import math
import os
import sys

import numpy as np
from PIL import Image

BUILD = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BUILD)

from scenes import obs_mach_clocks as first           # noqa: E402
from scenes.obs.common import skeleton as S           # noqa: E402
from scenes.obs.machines import clock                 # noqa: E402

COEF = np.array([0.299, 0.587, 0.114])                 # Rec.601 luma, as the windows are read
FOV, ASPECT = 77.0, 16.0 / 9.0                         # build/render.py
STEP = 1.0 / 32.0                                      # the grid a piece is sampled on, in blocks

DIAL = (0.30, 0.40)
DIAL_APART = 0.03
BALL_OVER_SKY = 0.05
BALL_UNDER = 0.05
MASTER_DIAL = 0.35
PLINTH_LINES = 0.05
CASE_FLOOR = 0.03
TINT = {"dial": (255, 0, 255), "stone": (0, 255, 255), "plinth": (0, 255, 0), "step": (0, 255, 255), "window": (0, 255, 0), "ball": (255, 0, 255),
        "sky": (0, 255, 255), "sun": (0, 255, 0), "case": (255, 255, 0), "foot": (255, 0, 255), "floor": (0, 255, 255)}


class Camera:
    def __init__(self, shot, width, height):
        self.pos = np.array(shot["pos"], dtype=float)
        f = np.array(shot["look_at"], dtype=float) - self.pos
        self.f = f / np.linalg.norm(f)
        r = np.cross(self.f, (0.0, 1.0, 0.0))
        self.r = r / np.linalg.norm(r)
        self.u = np.cross(self.r, self.f)
        self.size = (width, height)
        self.t = math.tan(math.radians(FOV) / 2.0)

    def pixels(self, points):
        """The pixels (a set of (column, row)) the points fall on; points off the picture are dropped."""
        d = np.asarray(points, dtype=float) - self.pos
        depth = d @ self.f
        keep = depth > 1e-6
        d, depth = d[keep], depth[keep]
        w, h = self.size
        col = np.floor((0.5 + (d @ self.r) / depth / (2.0 * self.t * ASPECT)) * w).astype(int)
        row = np.floor((0.5 - (d @ self.u) / depth / (2.0 * self.t)) * h).astype(int)
        ok = (col >= 0) & (col < w) & (row >= 0) & (row < h)
        return set(zip(col[ok].tolist(), row[ok].tolist()))

    def facing(self, centre):
        """Two unit vectors across the line of sight to `centre`: to the right and upwards."""
        d = np.asarray(centre, dtype=float) - self.pos
        d = d / np.linalg.norm(d)
        r = np.cross(d, (0.0, 1.0, 0.0))
        r = r / np.linalg.norm(r)
        return r, np.cross(r, d)


def _grid(lo, hi):
    n = max(1, int(math.ceil((hi - lo) / STEP)))
    return lo + (np.arange(n) + 0.5) * (hi - lo) / n


def patch(corner, a, b):
    """The points of a flat piece: from `corner` along the edge vectors a and b."""
    corner, a, b = (np.asarray(v, dtype=float) for v in (corner, a, b))
    s = _grid(0.0, float(np.linalg.norm(a))) / np.linalg.norm(a)
    t = _grid(0.0, float(np.linalg.norm(b))) / np.linalg.norm(b)
    return (corner[None, None, :] + s[:, None, None] * a[None, None, :] + t[None, :, None] * b[None, None, :]).reshape(-1, 3)


def disc(centre, a, b, r0, r1, keep=None):
    """The points of a ring r0..r1 round `centre` in the plane of the unit vectors a and b; keep(x, y)
    picks among them by their place in that plane."""
    centre, a, b = (np.asarray(v, dtype=float) for v in (centre, a, b))
    g = _grid(-r1, r1)
    x, y = np.meshgrid(g, g)
    d = np.hypot(x, y)
    ok = (d >= r0) & (d <= r1)
    if keep is not None:
        ok &= keep(x, y)
    return centre[None, :] + x[ok][:, None] * a[None, :] + y[ok][:, None] * b[None, :]


def _shown(nbt):
    ref = ((nbt.get("item") or {}).get("components") or {}).get("minecraft:item_model") or ""
    return ref.rpartition(":")[2]


def _where(canvas, name):
    """The places of the display entities that show the model `name`."""
    return [np.array(e[:3], dtype=float) for e in canvas.entities if _shown(e[3]) == clock.PREFIX + name]


def _nearest(places, point):
    return min(places, key=lambda p: float(np.linalg.norm(p - np.asarray(point, dtype=float))))


class Reader:
    def __init__(self, scene, folder, marks):
        self.scene, self.folder, self.marks = scene, folder, marks
        self.module = importlib.import_module("scenes." + scene)
        self.shots = {s["name"]: s for s in self.module.shots()}
        self.canvas = self.module.build()
        self.bad = []
        self.rows = []
        self._open = {}

    def picture(self, shot):
        if shot not in self.shots:                      # the second scene holds the tower's shots only
            return None
        if shot not in self._open:
            for name in (f"{shot}.png", f"{self.scene}-{shot}.png"):
                path = os.path.join(self.folder, name)
                if os.path.exists(path):
                    img = Image.open(path).convert("RGB")
                    self._open[shot] = [np.asarray(img).astype(float) / 255.0, Camera(self.shots[shot], *img.size), {}]
                    break
            else:
                self._open[shot] = None
                self.bad.append(f"{shot}: no picture in {self.folder}")
        return self._open[shot]

    def read(self, shot, what, points, low=None, mean=False):
        """The median luma (the `low` quantile, or the mean) of the pixels the points fall on; None
        without a picture."""
        got = self.picture(shot)
        if got is None:
            return None
        rgb, cam, marked = got
        px = cam.pixels(points)
        if not px:
            self.bad.append(f"{shot}: {what} is not in the picture")
            return None
        cols, rows = (np.array(v) for v in zip(*px))
        luma = rgb[rows, cols] @ COEF
        marked.setdefault(what.split()[0], set()).update(px)
        value = float(luma.mean() if mean else np.median(luma) if low is None else np.quantile(luma, low))
        mean = rgb[rows, cols].mean(axis=0)
        self.rows.append((shot, what, value, len(px), "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in mean)))
        return value

    def ask(self, ok, text):
        if ok is None:
            return
        print(("  ok   " if ok else "  OUT  ") + text)
        if not ok:
            self.bad.append(text)

    def save_marks(self):
        if not self.marks:
            return
        os.makedirs(self.marks, exist_ok=True)
        for shot, got in self._open.items():
            if got is None:
                continue
            rgb, _cam, marked = got
            out = (rgb * 255.0).round().astype(np.uint8)
            for what, px in marked.items():
                tint = np.array(TINT.get(what, (255, 0, 255)), dtype=float)
                for col, row in px:
                    if (col + row) % 2 == 0:
                        out[row, col] = (out[row, col] * 0.5 + tint * 0.5).astype(np.uint8)
            Image.fromarray(out).save(os.path.join(self.marks, f"{self.scene}-{shot}-marks.png"))


def tower_dials(r):
    """The enamel of the east and the south dial, the stone under the east dial, the frosted window."""
    faces = _where(r.canvas, "face")
    axis_x, axis_z = clock.BALL_AXIS
    east = _nearest(faces, (S.CLOCK_SHAFT_X[1] + 1.0, clock.DIAL_Y, axis_z))
    south = _nearest(faces, (axis_x, clock.DIAL_Y, S.CLOCK_SHAFT_Z[1] + 1.0))
    front = 1.0 / 16.0                                  # the enamel stands a pixel in front of the back plane
    rad = 17.0 / 16.0                                   # inside the ring of marks' outer line
    east_dial = disc(east + (front, 0, 0), (0, 0, -1), (0, 1, 0), 0.0, rad)
    south_dial = disc(south + (0, 0, front), (1, 0, 0), (0, 1, 0), 0.0, rad)
    wall = S.CLOCK_SHAFT_X[1] + 1.0
    stone = patch((wall, 24.0, axis_z - 1.5), (0, 1.75, 0), (0, 0, 3.0))       # the plain courses under the recess
    z0 = first.TCZ - 1
    window = patch((wall - 1.0, S.WINDOW[0], z0), (0, S.WINDOW[1] + 1 - S.WINDOW[0], 0), (0, 0, 3.0))

    print("the tower's dials")
    for shot in ("v1_tower", "tower_far"):
        d = r.read(shot, "dial east", east_dial)
        s = r.read(shot, "stone east wall", stone)
        w = r.read(shot, "window frosted", window)
        if d is not None:
            r.ask(DIAL[0] <= d <= DIAL[1], f"{shot}: the east dial reads {d:.3f} ({DIAL[0]:.2f}..{DIAL[1]:.2f})")
        if None not in (d, s, w):
            r.ask(s < d < w, f"{shot}: stone {s:.3f} < dial {d:.3f} < frosted window {w:.3f}")
    e = r.read("dial_south", "dial east", east_dial)
    s = r.read("dial_south", "dial south", south_dial)
    if None not in (e, s):
        r.ask(DIAL[0] <= s <= DIAL[1], f"dial_south: the south dial reads {s:.3f} ({DIAL[0]:.2f}..{DIAL[1]:.2f})")
        r.ask(abs(e - s) <= DIAL_APART, f"dial_south: east {e:.3f} and south {s:.3f} are {abs(e - s):.3f} apart "
                                        f"(no more than {DIAL_APART:.2f})")
    r.read("dial_front", "dial east", east_dial)


def time_ball(r):
    """The ball on the mast against the sky round it: a ring from 1.3 to 2.2 radii, without the
    wedge under the ball (the roof) and the strip the mast runs through."""
    balls = [p for name, _tones in clock.BALL_TONES.values() for p in _where(r.canvas, name)]
    centre = _nearest(balls, (clock.BALL_AXIS[0], clock.BALL_HALF_Y, clock.BALL_AXIS[1]))
    rad = clock.BALL_R / 16.0
    chosen = getattr(r.module, "BALL", clock.BALL) == clock.BALL
    print("the time ball")
    for shot in ("v1_tower", "tower_far", "top_close"):
        got = r.picture(shot)
        if got is None:
            continue
        right, up = got[1].facing(centre)
        b = r.read(shot, "ball", disc(centre, right, up, 0.0, 0.8 * rad))
        sky = r.read(shot, "sky round the ball", disc(centre, right, up, 1.3 * rad, 2.2 * rad,
                                                     keep=lambda x, y: (np.abs(x) > 0.3 * rad) & (y > -np.abs(x))))
        if None not in (b, sky):
            text = f"{shot}: the ball {b:.3f} over the sky {sky:.3f} by {b - sky:.3f} ({BALL_OVER_SKY:.2f} or more)"
            if chosen:
                r.ask(b - sky >= BALL_OVER_SKY, text)
            else:
                print("  note " + text + ": the colour that was not chosen, nothing is asked of it")
    # from the foot of the tower the ball is seen from below: the collar and the sleeve under it
    # may not be a black cap on it (cr3, 11-16). The strip the mast runs through is left out.
    for shot in ("dial_close", "v5_up"):
        got = r.picture(shot)
        if got is None:
            continue
        right, up = got[1].facing(centre)
        low = r.read(shot, "under the ball, darkest tenth",
                     disc(centre - 0.5 * rad * up, right, up, 0.0, 0.45 * rad, keep=lambda x, y: np.abs(x) > 0.3 * rad),
                     low=0.10)
        if low is not None:
            r.ask(low >= BALL_UNDER, f"{shot}: the darkest tenth under the ball reads {low:.3f} ({BALL_UNDER:.2f} or more)")


def master_clock(r):
    """The master dial and the plinth from V7, the case's darkest hundredth, the floor at its foot
    from the door's axis."""
    x, y, z = clock.MASTER_AT
    dial_at = np.array(clock._out(clock.MASTER_AT, clock.MASTER_FACING, clock.MASTER_DIAL))
    dial = disc(dial_at + (1.0 / 16.0, 0, 0), (0, 0, -1), (0, 1, 0), 0.0, 7.5 / 16.0)
    whole = disc(dial_at + (1.0 / 16.0, 0, 0), (0, 0, -1), (0, 1, 0), 0.0, 8.0 / 16.0)      # inside the bezel
    cx, cz = (math.floor(v) for v in S.ORRERY_CENTRE)
    sun_y = math.floor(S.ORRERY_RING_Y)
    sun = patch((cx + 0.1, sun_y, cz + 0.1), (0.8, 0, 0), (0, 0, 0.8))          # the underside of the lit block
    front = x + 0.75
    case = patch((front, y + 0.1, z - 0.55), (0, 3.8, 0), (0, 0, 1.1))
    # the pale band of the floor on the axis: the two cells in front of the grating round the step,
    # and two cells of the same stone farther out, under the orrery
    foot = patch((8.0, 0.0, z - 0.5), (1.0, 0, 0), (0, 0, 1.0))
    floor = patch((12.0, 0.0, z - 0.5), (1.0, 0, 0), (0, 0, 1.0))

    print("the master clock")
    d = r.read("v7", "dial master", dial)
    m = r.read("v7", "dial master, hands and all", whole, mean=True)
    s = r.read("v7", "sun of the orrery", sun)
    if d is not None:
        r.ask(d >= MASTER_DIAL, f"v7: the enamel of the master dial reads {d:.3f} ({MASTER_DIAL:.2f} or more)")
        r.ask(m >= MASTER_DIAL, f"v7: the whole master dial, marks and hands with it, reads {m:.3f} "
                                f"({MASTER_DIAL:.2f} or more)")
    if s is not None:
        print(f"  note v7: the stand-in for the orrery's sun reads {s:.3f}")
    # the plinth, in pixels from the foot of the case: its brass lines at 1..2 and 8..9, proud of
    # the skirting and of the cap; the raised field between them; the east face of the step below
    lines = np.concatenate([patch((x + 12.25 / 16.0, y + a / 16.0, z - 0.75), (0, 1.0 / 16.0, 0), (0, 0, 1.5))
                            for a in (1.0, 8.0)])
    field = patch((x + 11.5 / 16.0, y + 3.0 / 16.0, z - 0.5), (0, 4.0 / 16.0, 0), (0, 0, 1.0))
    step = patch((x + 1.0, y - 0.85, z - 0.75), (0, 0.7, 0), (0, 0, 1.5))
    a = r.read("v7", "plinth brass lines", lines)
    b = r.read("v7", "plinth wood between", field)
    c = r.read("v7", "step under the clock", step)
    if None not in (a, b, c):
        r.ask(a - max(b, c) >= PLINTH_LINES, f"v7: the plinth's brass lines {a:.3f} over its wood {b:.3f} and the "
                                             f"step {c:.3f} by {a - max(b, c):.3f} ({PLINTH_LINES:.2f} or more)")
    for shot in ("master_close", "master_door"):
        r.read(shot, "dial master", dial)
    low = r.read("master_close", "case darkest hundredth", case, low=0.01)
    if low is not None:
        r.ask(low >= CASE_FLOOR, f"master_close: the darkest hundredth of the case reads {low:.3f} "
                                 f"({CASE_FLOOR:.2f} or more)")
    a = r.read("master_door", "foot of the clock", foot)
    b = r.read("master_door", "floor on the axis", floor)
    if None not in (a, b):
        print(f"  note the floor in front of the clock's step {a:.3f}, four blocks out {b:.3f}")


def main():
    ap = argparse.ArgumentParser(description="the brightness of the clocks, read off the scene's pictures")
    ap.add_argument("folder", nargs="?")
    ap.add_argument("--scene", default="obs_mach_clocks")
    ap.add_argument("--marks", help="write the pictures again with the measured pixels tinted, into this folder")
    args = ap.parse_args()
    folder = args.folder or os.path.join(BUILD, "..", "renders", args.scene)
    r = Reader(args.scene, folder, args.marks)
    tower_dials(r)
    time_ball(r)
    if "v7" in r.shots:
        master_clock(r)
    r.save_marks()
    print()
    print(f"{'shot':<16}{'piece':<26}{'luma':>6}{'pixels':>8}  mean colour")
    for shot, what, value, n, colour in r.rows:
        print(f"{shot:<16}{what:<26}{value:>6.3f}{n:>8}  {colour}")
    print()
    print(json.dumps({"scene": args.scene, "out": len(r.bad)}))
    for line in r.bad:
        print("OUT: " + line)
    return 1 if r.bad else 0


if __name__ == "__main__":
    sys.exit(main())
