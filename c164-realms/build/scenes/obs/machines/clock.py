"""machines/clock.py -- the master clock, the four tower dials and their hands, the time ball.

Card plan/packages/machines/clocks.md; detail plan/parts/A5-machines.md 2.4; ART-PLAN 5.3, 7.2.
One family: brass rings, cream dials, dark hands, a dark-wood and brass master case.

  mach_clock_master    the star-hall mother clock -- a dark-wood long-case clock standing on the
                       east face of the telescope pier (skeleton MOTHER_CLOCK), dial and still hands
                       drawn in, the glazed trunk open so the movement and pendulum show. It is the
                       first thing seen from the main door, straight ahead on the pier (A0 g2 #207),
                       and the one source of time for the whole hill, so it is given some weight.
  mach_clock_pendulum  its pendulum (a brass bob on an iron rod), a separate entity: pivot at the
                       top, swings in the face plane about the dial normal, one second a swing (A8).
  mach_clock_tower_face  one tower dial (brass ring, cream face, Roman numerals, minute ticks),
                       placed on each of the four faces of the clock tower in c223's stone frames
                       (main/tower.py DIAL_Y 25..29, the lit circle of radius 2.4). The dial is
                       faintly self-lit so it reads as a warm circle on the skyline from V1 (~80
                       blocks); the east face (towards the court and cable station) matters most.
  mach_clock_hand_h / _m  the tower hour and minute hands (dark iron), separate entities so the
                       minute hand can be seen to move (A8); each turns about the dial normal.
  mach_clock_ball      the brass time ball, sleeved on c223's mast and parked at the top this round;
                       on the hour it drops down the mast (axis vertical, A8). The comet stands right
                       over the clean mast apex (A0 g2 #193), so the ball and pole are kept tidy.
  mach_clock_anemo     a small brass anemometer below the lightning rod (its cups spin, A8).

Entity budget: machines get S.BUDGET["machines"] = 400; this set places ~17 (master 1 + pendulum 1,
the master's own hands are drawn into its case; 4 tower faces + 4 hour + 4 minute hands; ball 1;
anemometer 1). build() returns the real count for S2 to watch the budget.

All dials are painted only from the palette (cream, brass, iron); Roman numerals use the letters I,
V and X only (the map-text red line: numbers and symbols only). px = scale on every model, so the
texture stays 16 pixels to the block, the same density as the blocks and the other models.
"""
import functools
import math

import numpy as np

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S

PREFIX = "mach_clock_"

# the way a face looks -> the yaw that points a model's +z that way (same table as props/_kit)
FACING = {"south": 0.0, "west": 90.0, "north": 180.0, "east": -90.0}

# the time every clock shows (the master clock is the one source): 10:10, the hands well spread
HOUR, MINUTE = 10, 10

# --- the clock-tower geometry, read from the skeleton and matched to c223's main/tower.py ----------
X0, X1 = S.CLOCK_SHAFT_X             # 10 .. 16, the 7-wide shaft; the east face is flush at x 16
Z0, Z1 = S.CLOCK_SHAFT_Z            # -33 .. -27
CX = (X0 + X1) // 2                 # 13, the central column
CZ = (Z0 + Z1) // 2                 # -30
DIAL_Y = (25, 29)                   # c223 main/tower.py DIAL_Y: the dial sits in these rows
DIAL_R = 2.4                        # c223's lit radius (blocks); the brass rim lands just inside it
BALL_Y = 47.5                       # the ball parked near the top of the brass mast (mast tips at 52)
ANEMO_Y = 50.0                      # the anemometer just under the lightning rod

# --- materials (palette only) ---------------------------------------------------------------------
WOOD = P.mat("dark_wood")
WOOD_D = P.mat("dark_wood", base=1)
WOOD_L = P.mat("dark_wood", base=3)
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")
IRON_D = P.mat("iron_dark")
CREAM = P.mat("cream")


# ==================================================================================================
# the dial face, painted to fit whatever pixel size it is asked for
# ==================================================================================================
_ROMAN = ["I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


def _stroke(buf, x0, y0, x1, y1, t):
    """Fill the pixels of a boolean buffer within t/2 of the segment (x0,y0)-(x1,y1)."""
    h, w = buf.shape
    yy, xx = np.ogrid[0:h, 0:w]
    dx, dy = x1 - x0, y1 - y0
    length2 = dx * dx + dy * dy
    if length2 < 1e-9:
        d = np.hypot(xx - x0, yy - y0)
    else:
        u = np.clip(((xx - x0) * dx + (yy - y0) * dy) / length2, 0.0, 1.0)
        d = np.hypot(xx - (x0 + u * dx), yy - (y0 + u * dy))
    buf |= d <= t / 2.0 + 1e-6


def _glyph(ch, gh, t):
    """A small boolean bitmap of one Roman letter -- I, V or X -- gh tall, strokes t thick."""
    if ch == "I":
        gw = int(max(t + 2, 3))
        buf = np.zeros((gh, gw), dtype=bool)
        cx = (gw - 1) / 2.0
        _stroke(buf, cx, 0, cx, gh - 1, t)
        _stroke(buf, 0, 0, gw - 1, 0, 1)                 # serifs top and bottom
        _stroke(buf, 0, gh - 1, gw - 1, gh - 1, 1)
        return buf
    gw = int(max(gh - 1, 3))
    buf = np.zeros((gh, gw), dtype=bool)
    if ch == "V":
        _stroke(buf, 0, 0, (gw - 1) / 2.0, gh - 1, t)
        _stroke(buf, gw - 1, 0, (gw - 1) / 2.0, gh - 1, t)
    else:  # X
        _stroke(buf, 0, 0, gw - 1, gh - 1, t)
        _stroke(buf, gw - 1, 0, 0, gh - 1, t)
    return buf


def _numeral(s, gh, t):
    """The bitmap of a Roman numeral, its glyphs set side by side with a one-pixel gap."""
    glyphs = [_glyph(ch, gh, t) for ch in s]
    gap = 1
    gw = sum(g.shape[1] for g in glyphs) + gap * (len(glyphs) - 1)
    buf = np.zeros((gh, gw), dtype=bool)
    x = 0
    for g in glyphs:
        buf[:, x:x + g.shape[1]] |= g
        x += g.shape[1] + gap
    return buf


class DialFace:
    """A clock dial painted to fill the face it is on: a cream disc, a dark chapter ring of minute
    ticks and twelve hour marks, Roman numerals, a brass hub. The brass rim is the model's ring, not
    painted here. Only palette colours, so tools/check.py strays stays empty. Adapts to its pixel
    size: a big dial (the tower, ~77 px) gets all twelve numerals and sixty minute ticks, a small one
    (the master clock) the four quarter numerals and twelve ticks.

    mirror / flip let a render fix the numeral handedness in one line without touching the geometry;
    the ticks, hub and rim are symmetric and read right either way.
    """

    def __init__(self, name, numerals=True, mirror=False, flip=False):
        self.name = name
        self.numerals = numerals
        self.mirror = mirror
        self.flip = flip

    def paint(self, w, h, grain="u", seed=0):
        out = np.zeros((h, w, 4), dtype=np.uint8)
        cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
        radius = min(w, h) / 2.0
        face = P.colour("cream", 3)
        face_sh = P.colour("cream", 2)
        mark = P.colour("iron", 1)
        hub = P.colour("brass", 4)
        hub_d = P.colour("brass", 1)
        yy, xx = np.ogrid[0:h, 0:w]
        r = np.hypot(xx - cx, yy - cy)
        disc = r <= radius
        out[disc, :3] = face
        out[disc, 3] = 255
        band = disc & (r >= radius * 0.80) & (r <= radius * 0.90)     # the chapter ring, a tone down
        out[band, :3] = face_sh
        many = radius >= 15.0
        if many:
            for k in range(60):                                       # minute ticks
                if k % 5 == 0:
                    continue
                self._tick(out, cx, cy, math.radians(k * 6), radius * 0.90, radius * 0.95, 1.0, mark)
        for k in range(12):                                          # the twelve hour marks
            self._tick(out, cx, cy, math.radians(k * 30), radius * 0.83, radius * 0.97,
                       max(1.0, radius * 0.05), mark)
        if self.numerals:
            gh = int(max(3, round(radius * (0.22 if many else 0.34))))
            t = max(1, int(round(gh / 5.0)))
            rr = radius * 0.65
            hours = range(1, 13) if many else (12, 3, 6, 9)
            for hour in hours:
                th = math.radians((hour % 12) * 30)
                gx = cx + math.sin(th) * rr
                gy = cy - math.cos(th) * rr
                self._blit(out, _numeral(_ROMAN[hour - 1], gh, t), gx, gy, mark)
        hole = max(1.6, radius * 0.07)
        out[r <= hole, :3] = hub
        out[r <= hole, 3] = 255
        ringm = (r > hole) & (r <= hole + max(1.2, radius * 0.03))
        out[ringm, :3] = hub_d
        out[ringm, 3] = 255
        if self.mirror:
            out = out[:, ::-1]
        if self.flip:
            out = out[::-1, :]
        return np.ascontiguousarray(out)

    @staticmethod
    def _tick(out, cx, cy, th, r0, r1, width, colour):
        h, w = out.shape[:2]
        dx, dy = math.sin(th), -math.cos(th)
        buf = np.zeros((h, w), dtype=bool)
        _stroke(buf, cx + dx * r0, cy + dy * r0, cx + dx * r1, cy + dy * r1, width)
        out[buf, :3] = colour
        out[buf, 3] = 255

    @staticmethod
    def _blit(out, glyph, gx, gy, colour):
        h, w = out.shape[:2]
        gh, gw = glyph.shape
        y0 = int(round(gy - gh / 2.0))
        x0 = int(round(gx - gw / 2.0))
        ys, xs = np.nonzero(glyph)
        for j, i in zip(ys, xs):
            y, x = y0 + j, x0 + i
            if 0 <= y < h and 0 <= x < w:
                out[y, x, :3] = colour
                out[y, x, 3] = 255


# ==================================================================================================
# models
# ==================================================================================================
def _tower_face():
    """One tower dial: a cream face (self-lit) with the painted ticks and numerals, a brass rim ring.
    px = 2, so one unit is an eighth of a block; the lit disc is 2.1 blocks across, the rim lands at
    c223's lit radius 2.4. Anchor: the centre of the dial on the stone face; +z looks out."""
    m = M.Model(PREFIX + "tower_face", px=2.0)
    r = 17.0                                                 # disc half-size in units (2.125 blocks)
    dial = DialFace(PREFIX + "tower_dial", numerals=True)
    m.box((-r, -r, -0.5), (r, r, 0.0), CREAM, faces={"s": dial}, emit=11, shade=False)
    m.ring("z", (0.0, 0.0, -0.5), 18.0, 3.4, 3.0, BRASS, sides=24)       # brass rim, proud of the face
    return m


def _hand(name, length, wide, tail):
    """A dark-iron clock hand pointing +y from the pivot at the anchor, standing a little proud of
    the dial (z) so it reads over the face. A8 turns it about z (the dial normal). px = 2."""
    m = M.Model(name, px=2.0)
    z0, z1 = 2.0, 3.4
    m.box((-wide, -tail, z0), (wide, length * 0.72, z1), IRON_D, grain="y")          # shaft
    m.box((-wide * 0.5, length * 0.72, z0), (wide * 0.5, length, z1), IRON_D, grain="y")  # tip
    m.tube("z", (0.0, 0.0), z0 - 0.6, z1 + 0.6, 1.8, IRON_D)                         # boss over the hub
    return m


def _pendulum():
    """The master clock's pendulum: an iron rod and a brass bob. Anchor at the pivot (top); it swings
    in the x-y (dial) plane about z, one second a swing (A8). px = 2."""
    m = M.Model(PREFIX + "pendulum", px=2.0)
    m.tube("z", (0.0, 0.0), -0.6, 0.6, 1.1, BRASS_D)                    # suspension at the pivot
    m.box((-0.4, -15.0, -0.4), (0.4, 0.0, 0.4), IRON_D, grain="y")      # rod
    m.tube("z", (0.0, -16.5), -0.6, 0.6, 3.2, BRASS)                    # bob (a brass disc)
    m.tube("z", (0.0, -16.5), -0.9, 0.9, 1.2, BRASS_D)                  # bob boss
    return m


def _still_hands(m, cx, cy, zf, radius):
    """The master clock's hands, drawn still at HOUR:MINUTE (its one moving part is the pendulum)."""
    ha, ma = _angles(HOUR, MINUTE)
    for ang, length, wide in ((ha, radius * 0.55, 1.1), (ma, radius * 0.90, 0.7)):
        with m.turned(("z", -math.degrees(ang)), about=(cx, cy, zf)):
            m.box((cx - wide, cy - 1.5, zf), (cx + wide, cy + length, zf + 0.6), IRON_D, grain="y")


def _mother():
    """The star-hall long-case clock. px = 2; units are eighths of a block. Anchor: the centre of the
    back foot on the floor. +z is the front (east), +y up, +x the width. Five blocks tall (y 0..40
    units), 1.5 wide, 1 deep; its back stands against the pier's east face (MOTHER_CLOCK back_x)."""
    m = M.Model(PREFIX + "master", px=2.0)
    half = 6.0          # half the width: 1.5 blocks = 12 units
    depth = 8.0         # 1 block
    # the plinth, with a stepped base cap and a brass line
    m.box((-half, 0.0, 0.0), (half, 7.0, depth), WOOD, grain="y")
    m.box((-half - 0.5, 6.0, -0.5), (half + 0.5, 8.0, depth + 0.5), WOOD_D, grain="x")
    m.box((-half + 0.4, 7.4, depth), (half - 0.4, 8.0, depth + 0.6), BRASS_D, grain="x")
    # the trunk: narrower, with two wood stiles and an open (glazed) door showing the pendulum
    tw = 4.5
    for x in (-tw, tw - 1.0):
        m.box((x, 8.0, 0.0), (x + 1.0, 28.0, depth), WOOD, grain="y")
    m.box((-tw, 8.0, 0.0), (tw, 28.0, 1.6), WOOD_D, grain="y")           # trunk back
    m.box((-tw, 8.0, 0.0), (tw, 9.4, depth), WOOD, grain="x")            # bottom rail
    m.box((-tw, 26.6, 0.0), (tw, 28.0, depth), WOOD, grain="x")          # top rail
    fr = depth - 0.4
    for x in (-tw + 0.9, tw - 1.3, -0.25):                               # brass glazing bars
        m.box((x, 9.4, fr), (x + 0.4, 26.6, fr + 0.4), BRASS_D, grain="y")
    # the movement behind the dial -- a couple of brass wheels seen over the hood floor
    m.tube("z", (-2.2, 30.5), 1.0, 2.0, 1.6, BRASS_D)
    m.tube("z", (2.2, 31.0), 1.0, 2.0, 2.2, BRASS)
    # the hood: the dial, flanked by two brass colonettes, a cornice and a finial
    m.box((-half, 28.0, 0.0), (half, 29.0, depth), WOOD_D, grain="x")    # hood floor
    for x in (-half, half - 1.0):
        m.box((x, 29.0, 0.0), (x + 1.0, 39.0, depth), WOOD, grain="y")   # hood sides
    m.box((-half, 29.0, 0.0), (half, 40.0, 1.6), WOOD_D, grain="y")      # hood back
    for x in (-half + 1.4, half - 1.9):
        m.tube("y", (x + 0.25, depth - 1.0), 29.5, 38.5, 0.8, BRASS)     # colonettes
    m.box((-half, 39.0, 0.0), (half, 40.5, depth), WOOD_D, grain="x")    # cornice
    m.box((-half + 0.5, 40.0, 0.5), (half - 0.5, 40.5, depth - 0.5), BRASS_D, grain="x")
    m.tube("y", (0.0, depth - 1.0), 40.5, 43.0, 0.6, BRASS)             # finial spike
    m.ball((0.0, 43.3, depth - 1.0), 1.2, BRASS, sides=8, layers=4)
    # the dial on the hood front, cream and faintly self-lit, with still hands
    dz, cy, rb = depth, 34.0, 5.2
    dial = DialFace(PREFIX + "master_dial", numerals=True)
    with m.moved((0.0, cy, 0.0)):
        m.box((-rb, -rb, dz - 1.2), (rb, rb, dz), CREAM, faces={"s": dial}, emit=5, shade=False)
        m.ring("z", (0.0, 0.0, dz - 0.4), 5.6, 1.2, 1.4, BRASS, sides=20)
        _still_hands(m, 0.0, 0.0, dz + 0.5, rb)
    return m


def _ball():
    """The brass time ball, sleeved on c223's mast; anchor at its centre. It drops down the mast on
    the hour (axis vertical) -- A8. px = 1 (1.9 blocks across)."""
    m = M.Model(PREFIX + "ball", px=1.0)
    m.ball((0.0, 0.0, 0.0), 15.0, BRASS, sides=12, layers=8, patchy=True)
    m.ring("y", (0.0, 8.0, 0.0), 4.5, 1.5, 1.5, BRASS_D, sides=12)       # collars gripping the mast
    m.ring("y", (0.0, -8.0, 0.0), 4.5, 1.5, 1.5, BRASS_D, sides=12)
    return m


def _anemo():
    """A small brass anemometer: a spindle and three cups on arms; it spins about y (A8). Anchor at
    the foot, on the mast cap. px = 1."""
    m = M.Model(PREFIX + "anemo", px=1.0)
    m.tube("y", (0.0, 0.0), 0.0, 6.0, 0.8, BRASS)                       # spindle
    for a in (0.0, 120.0, 240.0):
        th = math.radians(a)
        dx, dz = math.sin(th), math.cos(th)
        m.rod((0.0, 5.0, 0.0), (dx * 5.0, 5.0, dz * 5.0), 0.5, BRASS_D)             # arm
        m.ball((dx * 5.6, 5.0, dz * 5.6), 1.7, BRASS, sides=8, layers=4, part=(-1.0, 0.2))  # cup
    m.tube("y", (0.0, 0.0), 6.0, 7.5, 0.5, BRASS_D)                     # cap
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {
        PREFIX + "master": _mother(),
        PREFIX + "pendulum": _pendulum(),
        PREFIX + "tower_face": _tower_face(),
        PREFIX + "hand_h": _hand(PREFIX + "hand_h", 10.5, 1.6, 3.5),
        PREFIX + "hand_m": _hand(PREFIX + "hand_m", 15.5, 1.1, 4.0),
        PREFIX + "ball": _ball(),
        PREFIX + "anemo": _anemo(),
    }


def models():
    return dict(_models())


# ==================================================================================================
# placing
# ==================================================================================================
def _angles(hour, minute):
    """The hour and minute hand angles (radians, clockwise from twelve)."""
    minute_ang = minute / 60.0 * 2 * math.pi
    hour_ang = ((hour % 12) + minute / 60.0) / 12.0 * 2 * math.pi
    return hour_ang, minute_ang


def _place(canvas, model, pos, origin, yaw=0.0, scale=1.0, turns=(), brightness=None):
    x, y, z = (pos[i] + origin[i] for i in range(3))
    canvas.add_entity(x, y, z, M.display(model, yaw=yaw, scale=scale, turns=turns, brightness=brightness))
    return 1


def _tower_centre(face):
    """The centre point of the dial on one tower face, and the surface it sits on (nudged out a hair
    so the entity's cell is air). Matches c223's main/tower.py _clock_faces."""
    cy = S.mid(DIAL_Y[0], DIAL_Y[1])                 # 27.5
    along = S.mid(CZ - 2, CZ + 2)                     # -29.5, the middle of the 5-wide dial (east/west)
    across = S.mid(CX - 2, CX + 2)                    # 13.5 (north/south)
    if face == "east":
        return (X1 + 1 + 0.02, cy, along)
    if face == "west":
        return (X0 - 0.02, cy, along)
    if face == "north":
        return (across, cy, Z0 - 0.02)
    return (across, cy, Z1 + 1 + 0.02)               # south


def _mother_pivot(mc):
    """The pendulum's pivot point: inside the trunk near the top, on the clock's centre line."""
    return (mc["back_x"] + 0.5, S.GROUND + 3.5, mc["z"])


def _offer_lights(canvas, lights, why):
    """Hand the clocks' warm light sources to A2 (sky/_lightkit.take); until that is in the tree the
    blocks are put down here so a test scene is lit (never over a block already there)."""
    lights = [((int(x), int(y), int(z)), int(level)) for (x, y, z), level in lights]
    if not lights:
        return
    try:
        from ..sky import _lightkit
        take = getattr(_lightkit, "take", None)
    except ImportError:
        take = None
    if take is not None:
        take(canvas, lights, why)
        return
    for (x, y, z), level in lights:
        canvas.set(x, y, z, f"{B.LIGHT}[level={level}]", keep=True)


def build(canvas, origin=(0, 0, 0)):
    """Place the master clock, the four tower dials and hands, the time ball and the anemometer in
    the master scene; offer A2 the warm glow of the dials. Returns the display-entity count."""
    n = 0
    built = _models()
    ha, ma = _angles(HOUR, MINUTE)
    lights = []

    # the master clock on the east face of the telescope pier (first thing seen from the main door)
    mc = S.MOTHER_CLOCK
    yaw = FACING[mc["facing"]]
    n += _place(canvas, built[PREFIX + "master"], (mc["back_x"], S.GROUND, mc["z"]), origin,
                yaw=yaw, scale=2.0, brightness=(0, 5))
    n += _place(canvas, built[PREFIX + "pendulum"], _mother_pivot(mc), origin,
                yaw=yaw, scale=2.0, brightness=(0, 6))
    lights.append(((int(mc["back_x"] + 1), S.GROUND + 4, int(mc["z"])), 6))   # master dial, third rank

    # the four tower dials, their hands, and (on the mast) the ball and anemometer
    for face in ("east", "west", "north", "south"):
        c = _tower_centre(face)
        fyaw = FACING[face]
        n += _place(canvas, built[PREFIX + "tower_face"], c, origin, yaw=fyaw, scale=2.0,
                    brightness=(15, 11))
        n += _place(canvas, built[PREFIX + "hand_h"], c, origin, yaw=fyaw, scale=2.0,
                    turns=(("z", -math.degrees(ha)),), brightness=(15, 0))
        n += _place(canvas, built[PREFIX + "hand_m"], c, origin, yaw=fyaw, scale=2.0,
                    turns=(("z", -math.degrees(ma)),), brightness=(15, 0))
        lights.append((tuple(int(math.floor(v)) for v in c), 9))             # tower dial, second rank

    n += _place(canvas, built[PREFIX + "ball"], (S.mid(CX), BALL_Y, S.mid(CZ)), origin, scale=1.0)
    n += _place(canvas, built[PREFIX + "anemo"], (S.mid(CX), ANEMO_Y, S.mid(CZ)), origin, scale=1.0)

    _offer_lights(canvas, lights, "machines/clock")
    return n
