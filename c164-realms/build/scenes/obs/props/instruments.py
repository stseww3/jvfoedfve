"""props/instruments -- the small instruments of the observatory (plan ART-PLAN 7.3, part A6 section
2.5, card plan/packages/props/instruments.md).

One family, one motif: a graduated brass ring or arc, a knurled brass knob, a steady foot of dark
wood, cast iron or stone. Phosphor green is on dials only and nothing else glows.

    tripod_scope       a brass telescope on a wooden tripod, two blocks tall (the sunset terrace)
    celestial_globe    a star globe 20 px across in a three-legged floor stand (the star hall)
    globe              a table globe: a verdigris ball in a brass half meridian on a turned foot
    sextant            a sextant in its wooden cradle, for a table
    barometer          a banjo barometer for the wall, two blocks tall, the dial at the foot
    louvre_box         a white louvred thermometer screen on four legs and a stone slab
    regulator_clock    a precision pendulum clock in a long glazed case, two blocks tall; its
                       pendulum is the separate model regulator_pendulum (see PENDULUM)
    calc_machine       a hand-cranked calculating machine on a board, for a table
    sunshine_recorder  a glass ball before a brass bowl, for the stone pedestal of the weather station
                       (not on the card: site/outbuildings keeps a pedestal for it)

Every piece is one display entity at scale 1 (16 texels to the block), the clock two. For the other
lines:

    from scenes.obs.props import instruments
    n += instruments.place(canvas, "tripod_scope", (x, y, z), facing="west", origin=origin)

place() returns the number of display entities it placed. Nothing here is spread over the building:
the rooms and the outbuildings place what they need. build() places one piece, the telescope of the
sunset terrace, and that only once the switch DRESS is on (see site()).

No brass bar crosses another at right angles in any of these (RUBRIC red line 8): the globe's
horizon ring is wood seen from the side, its meridian stands off the main axes, the barometer's dial
is at the foot of its board.

The look is judged in the test scene build/scenes/obs_props_instruments.
"""
import functools
import math

import numpy as np

from artkit import models as M
from artkit import pixelart
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from . import _kit as K

PREFIX = "prop_inst_"

IRON, IRON_D, BRASS, BRASS_D = K.IRON, K.IRON_D, K.BRASS, K.BRASS_D
WOOD = P.mat("dark_wood")
WOOD_L = P.mat("dark_wood", base=3)               # the lighter board: door frames, the clock's dial board
WOOD_D = P.mat("dark_wood", base=1)               # feet, plinths, cornices, the inside of a case
STONE = P.mat("ashlar")
WHITE = P.mat("cream", base=2, bevel=1)           # white paint on wood: the thermometer screen
WHITE_D = P.mat("cream", base=1, bevel=1)
LENS = K.flat("night_glass", 2)                   # the glass of an objective: dark, it holds the sky
EYECUP = K.flat("iron", 1)
KNOB = K.flat("brass", 4)                         # the bright end of a knurled knob
ROD = K.flat("brass", 3)                          # a rod one pixel thick: one clean line, no edges
INK = P.RAMPS["iron"][1]
LUME = P.RAMPS["phosphor"][2]


# ---- painted surfaces ----------------------------------------------------------------------------
class _Scale(pixelart.Mat):
    """A graduated limb: an engraved line across the grain every `pitch` pixels along it, `reach`
    pixels long from one edge of the picture (edge: "first" or "last" row or column)."""
    pitch, phase, reach, edge, ink = 2, 1, 2, "last", 0

    def paint(self, w, h, grain="u", seed=0):
        out = super().paint(w, h, grain, seed)
        jj, ii = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        along, across, size = (ii, jj, h) if grain == "u" else (jj, ii, w)
        near = across < self.reach if self.edge == "first" else across >= size - self.reach
        out[near & (along % self.pitch == self.phase), :3] = self.ramp[self.ink]
        return out


def _scale(edge, pitch, phase, reach, ramp="brass", base=3, ink=0):
    s = _Scale(f"{ramp}_scale_{edge}_{pitch}_{phase}_{reach}", P.RAMPS[ramp], kind="flat", bevel=0, base=base)
    s.edge, s.pitch, s.phase, s.reach, s.ink = edge, pitch, phase, reach, ink
    return s


class _Stars(pixelart.Mat):
    """The painted sky of a celestial globe: enamel blue with single-pixel stars, one pixel in
    `rare`: most a dim cream, some the brightest cream, a few pale gold."""
    rare = 15

    def paint(self, w, h, grain="u", seed=0):
        out = super().paint(w, h, grain, seed)
        jj, ii = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        r = pixelart._hash(ii * 3 + 1, jj * 5 + 2, seed * 13 + 7) * self.rare
        out[r < 1.0, :3] = P.colour("cream", 1)
        out[r < 0.45, :3] = P.colour("cream", 3)
        out[r < 0.15, :3] = P.colour("brass", 5)
        return out


class _Lands(pixelart.Mat):
    """The map of a small globe: the metal of the seas with lighter lands in blocks of two pixels."""

    def paint(self, w, h, grain="u", seed=0):
        out = super().paint(w, h, grain, seed)
        jj, ii = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        land = pixelart._hash((ii + seed) // 2, (jj + seed * 3) // 2, seed * 7 + 3) < 0.38
        out[land, :3] = self.ramp[min(len(self.ramp) - 1, self.base + 2)]
        return out


class _Slats(pixelart.Mat):
    """Louvres: a lit slat and the shadow under it, two pixels to the pair, level whatever the grain."""

    def paint(self, w, h, grain="u", seed=0):
        out = super().paint(w, h, grain, seed)
        out[1::2, :, :3] = self.ramp[0]
        return out


class _Ribs(pixelart.Mat):
    """Slots cut across the grain, every other pixel along it: the drum of the calculating machine."""

    def paint(self, w, h, grain="u", seed=0):
        out = super().paint(w, h, grain, seed)
        if grain == "u":
            out[:, 1::2, :3] = self.ramp[0]
        elif grain == "v":
            out[1::2, :, :3] = self.ramp[0]
        return out


SKY = _Stars("enamel_stars", P.RAMPS["enamel"], kind="plain", noise=0.0, bevel=0, base=1)
LANDS = _Lands("verdigris_lands", P.RAMPS["verdigris"], kind="plain", noise=0.0, bevel=0, base=1)
SLATS = _Slats("cream_slats", P.RAMPS["cream"], kind="flat", bevel=0, base=3)
DRUM = _Ribs("iron_slots", P.RAMPS["iron"], kind="flat", bevel=0, base=3)


def _sprite(name, rows, **colours):
    return Sprite(PREFIX + name, rows, colours)


FACE, FACE_D = P.RAMPS["porcelain"][3], P.RAMPS["porcelain"][2]
DIAL_COLOURS = dict(c=FACE, d=FACE_D, k=INK, h=P.RAMPS["iron"][0], b=P.RAMPS["brass"][3], g=LUME)
# the barometer: a scale over the upper arc, three luminous marks, the hand at "fair"
BARO_DIAL = [
    "..ckgkc..",
    ".kcccchk.",
    "ccccchccc",
    "kcccchcck",
    "gcccbcccg",
    "kcchcccck",
    "ccccccccc",
    ".dcccccd.",
    "..ddddd..",
]
# the clock: twelve marks, the quarters luminous; the hands are drawn in by _hands()
CLOCK_DIAL = [
    "..kcgck..",
    ".ccccccc.",
    "kccccccck",
    "ccccccccc",
    "gcccbcccg",
    "ccccccccc",
    "kccccccck",
    ".dcccccd.",
    "..kdgdk..",
]
# every clock on the hill is stopped at one time, five minutes before the time ball drops (director,
# g2 #34140): the skeleton's CLOCK once it has it
CLOCK = getattr(S, "CLOCK", (7, 55))


def _hands(rows, hour, minute):
    """A nine-pixel dial with its hands drawn in from the middle: the hour hand two pixels long, the
    minute hand three, one pixel to each step along the way the hand leans most."""
    grid = [list(row) for row in rows]
    mid = len(rows) // 2
    for turn, length in (((hour % 12 + minute / 60.0) / 12.0, 2), (minute / 60.0, 3)):
        dx, dy = math.sin(2.0 * math.pi * turn), -math.cos(2.0 * math.pi * turn)
        for i in range(1, length + 1):
            if abs(dx) > abs(dy):
                x, y = mid + (i if dx > 0 else -i), int(round(mid + i * dy / abs(dx)))
            else:
                x, y = int(round(mid + i * dx / abs(dy))), mid + (i if dy > 0 else -i)
            grid[y][x] = "h"
    return ["".join(row) for row in grid]


def _lume(rows):
    """Only the luminous marks of a dial, for the plate that glows in front of it."""
    return ["".join(ch if ch == "g" else "." for ch in row) for row in rows]


GLINT = P.RAMPS["porcelain"][4]
STROKES = ((3, 1), (2, 2), (1, 3), (4, 3), (3, 4))      # the same two strokes as furniture._pane (c179, g2 #33282)


def _pane(m, lo, hi):
    """A pane of glass that looks +z, drawn the way the furniture draws its glass: the glass is
    left out and its glint says it is there, two short white strokes in the upper left corner."""
    w, h = int(round(hi[0] - lo[0])), int(round(hi[1] - lo[1]))
    rows = [["."] * w for _ in range(h)]
    for i, j in STROKES:
        if i < w and j < h:
            rows[j][i] = "g"
    m.box(lo, hi, BRASS, skip="nudew", faces={"s": _sprite(f"glint_{w}x{h}", ["".join(row) for row in rows], g=GLINT)})


def _sphere(m, centre, radius, mat, sides, layers):
    """A ball with a pattern on it, every face its own piece of the picture. m.ball() alone gives
    the layers of one girth the same pictures: each painted star would stand over its twin."""
    for i in range(layers):
        m.ball(centre, radius, mat, sides=sides, layers=1, patchy=True,
               part=(2.0 * i / layers - 1.0, 2.0 * (i + 1) / layers - 1.0))


def _dial(m, name, rows, centre, z):
    """A round dial nine pixels across on a face that looks +z: the painted face, and in front of it
    a plate with only its luminous marks, which glows in the dark."""
    x, y = centre
    half = len(rows) / 2.0
    m.box((x - half, y - half, z - 0.25), (x + half, y + half, z), K.flat("porcelain", 3), skip="nudew",
          faces={"s": _sprite(name, rows, **DIAL_COLOURS)})
    m.box((x - half, y - half, z), (x + half, y + half, z + 0.1), K.flat("phosphor", 2), skip="nudew",
          faces={"s": _sprite(name + "_lume", _lume(rows), g=LUME)}, emit=15, shade=False)


# ---- the models ------------------------------------------------------------------------------------
SCOPE_TILT = 18.0       # degrees above the horizon
SCOPE_PIVOT = 26.5      # height of the altitude axis
SCOPE_HUB = 20.5        # height of the tripod head


def _tripod_scope():
    """A brass refractor on a wooden tripod, 34 px tall and 30 px long. It looks along +z and up by
    SCOPE_TILT; one leg stands forward under the objective and the observer steps between the other
    two (the feet are 8.5 px from the middle). On the right of the fork the graduated altitude
    sector, on the left the clamp. Anchor: the floor under the middle of the tripod."""
    m = M.Model(PREFIX + "tripod_scope")
    hub = SCOPE_HUB
    for turn in (0.0, 120.0, 240.0):
        with m.turned(("y", turn)):
            with m.aimed((0.0, 0.0, 8.5), (0.0, hub - 0.5, 1.75), "y") as length:
                m.taper("y", (0, 0), 0.0, 2.5, 0.5, 1.0, IRON_D, sides=4, steps=2)      # pointed shoe
                m.tube("y", (0, 0), 2.5, length, 1.0, WOOD, sides=4)                    # leg
                m.tube("y", (0, 0), 10.0, 11.5, 1.25, BRASS_D, sides=4)                 # the clamp of the slide
    m.tube("y", (0, 0), hub - 1.5, hub + 0.5, 2.75, BRASS_D)                            # tripod head
    m.tube("y", (0, 0), hub + 0.5, hub + 1.5, 1.5, IRON)                                # azimuth bearing
    foot = hub + 1.5
    m.box((-4.0, foot, -1.5), (4.0, foot + 1.0, 1.5), IRON)                             # yoke: foot and cheeks
    for x in (-4.0, 3.0):
        m.box((x, foot + 1.0, -1.5), (x + 1.0, SCOPE_PIVOT + 1.5, 1.5), IRON, grain="y")
    m.tube("x", (SCOPE_PIVOT, 0), -5.5, -4.0, 1.5, BRASS_D, cap=KNOB)                   # clamp knob, on the left
    limb = _scale("first", 3, 1, 1)
    with m.turned(("x", -SCOPE_TILT), about=(0, SCOPE_PIVOT, 0)):
        c = (0, SCOPE_PIVOT)
        side, ends = 4.5, (101.25, 258.75)                                              # on the right the altitude
        m.ring("x", (side, SCOPE_PIVOT, 0), 5.5, 2.0, 0.75, BRASS, sides=16, arc=ends,
               faces={"w": limb, "e": limb})                                            # arc: a graduated sector
        for deg in ends:                                                                # hung from the axis
            a = math.radians(deg)
            m.beam((side, SCOPE_PIVOT, 0.0), (side, SCOPE_PIVOT + 4.75 * math.cos(a), 4.75 * math.sin(a)),
                   0.5, 1.0, BRASS_D)
        m.tube("x", (SCOPE_PIVOT, 0), 4.0, 5.25, 1.25, BRASS_D, cap=KNOB)               # its boss
        m.tube("z", c, -7.0, 12.0, 2.0, BRASS, sides=12)                                # main tube
        m.tube("z", c, -1.75, 1.75, 2.5, BRASS_D, sides=12)                             # cradle band
        m.tube("z", c, 6.5, 7.5, 2.25, BRASS_D, sides=12)
        m.tube("z", c, 12.0, 15.5, 2.5, BRASS_D, sides=12)                              # objective cell
        m.tube("z", c, 15.5, 15.75, 2.0, LENS, sides=12, cap=LENS)                      # the glass
        m.tube("z", c, -11.5, -7.0, 1.5, BRASS_D)                                       # draw tube
        m.tube("z", c, -14.0, -11.5, 1.0, BRASS, cap=EYECUP)                            # eyepiece
        m.tube("x", (SCOPE_PIVOT - 0.5, -8.5), 1.25, 3.0, 1.0, BRASS_D, cap=KNOB)       # focus knob
        m.tube("z", (0, SCOPE_PIVOT + 3.25), 1.0, 9.5, 1.0, BRASS_D, cap=LENS)          # finder
        for z in (2.5, 7.0):
            m.box((-0.75, SCOPE_PIVOT + 1.75, z), (0.75, SCOPE_PIVOT + 2.5, z + 1.0), IRON_D)
    return m


GLOBE_R = 10.0          # the sphere: 20 px across
GLOBE_Y = 19.0          # height of its centre and of the horizon ring
GLOBE_TILT = 38.0       # the polar axis leans this far from the vertical
GLOBE_YAW = 25.0        # the meridian ring stands this far off the model's x axis: never edge-on from the front


def _celestial_globe():
    """A star globe in a floor stand: three legs carry a wooden horizon ring with a brass scale let
    into its top, a graduated brass meridian ring stands in it and holds the sphere by its poles.
    28 px across the horizon ring, 31.5 px tall. Anchor: the floor under its middle."""
    m = M.Model(PREFIX + "celestial_globe")
    cy, r = GLOBE_Y, GLOBE_R
    for turn in (60.0, 180.0, 300.0):                   # two legs in front, one behind
        with m.turned(("y", turn)):
            z = 12.0
            m.box((-1.5, 0.0, z - 1.5), (1.5, 1.5, z + 1.5), WOOD_D)                    # foot
            m.box((-1.0, 1.5, z - 1.0), (1.0, 4.5, z + 1.0), WOOD, grain="y")
            m.box((-1.25, 4.5, z - 1.25), (1.25, 7.0, z + 1.25), WOOD_D)                # the block the stretcher meets
            m.box((-1.0, 7.0, z - 1.0), (1.0, 15.0, z + 1.0), WOOD, grain="y")
            m.box((-1.25, 15.0, z - 1.25), (1.25, 16.0, z + 1.25), BRASS_D)             # collar
            m.box((-1.25, 16.0, z - 1.25), (1.25, cy - 1.0, z + 1.25), WOOD_D)
            m.box((-1.0, 5.0, 2.0), (1.0, 6.5, z - 1.25), WOOD, grain="z")              # stretcher
    m.tube("y", (0, 0), 4.5, 6.5, 2.75, WOOD_D)                                         # hub of the stretchers
    m.ring("y", (0, cy, 0), 12.5, 3.0, 2.0, WOOD, sides=24, faces={"u": _scale("last", 2, 1, 2)})   # horizon ring
    with m.turned(("y", GLOBE_YAW)):
        for z in (-1.75, 0.75):                                                         # the cradle under the meridian
            m.box((-1.5, 6.5, z), (1.5, 8.75, z + 1.0), BRASS_D)
        m.ring("z", (0, cy, 0), r + 1.5, 2.0, 1.5, BRASS, sides=24,
               faces={"s": _scale("last", 3, 1, 1), "n": _scale("first", 3, 1, 1)})     # meridian ring
    with m.turned(("z", -GLOBE_TILT), ("y", GLOBE_YAW), about=(0, cy, 0)):
        _sphere(m, (0, cy, 0), r, SKY, sides=12, layers=10)
        m.tube("y", (0, 0), cy + r + 0.1, cy + r + 0.6, 2.5, BRASS_D)                   # hour circle
        for a0, a1 in ((cy - r - 3.25, cy - r), (cy + r, cy + r + 3.25)):               # the pins at the poles
            m.tube("y", (0, 0), a0, a1, 0.75, BRASS)
        for a0, a1 in ((cy - r - 3.5, cy - r - 2.5), (cy + r + 2.5, cy + r + 3.5)):     # and their nuts
            m.tube("y", (0, 0), a0, a1, 1.25, BRASS_D, cap=KNOB)
    return m


def _globe():
    """A table globe a block tall: a verdigris ball 10 px across, its axis leaning 23.5 degrees, in
    a graduated brass half meridian on a turned wooden foot. Anchor: the table under its middle."""
    m = M.Model(PREFIX + "globe")
    cy, r, tilt = 11.0, 5.0, 23.5
    m.tube("y", (0, 0), 0.0, 1.0, 4.0, WOOD_D)                                          # foot
    m.tube("y", (0, 0), 1.0, 2.0, 3.0, WOOD)
    m.tube("y", (0, 0), 2.0, 4.0, 1.25, WOOD)                                           # stem
    m.tube("y", (0, 0), 3.75, 5.0, 1.75, BRASS_D)                                       # the socket of the meridian
    north = 90.0 - tilt
    m.ring("z", (0, cy, 0), r + 1.25, 1.5, 1.25, BRASS, sides=24, arc=(north - 187.5, north + 7.5),
           faces={"s": _scale("last", 2, 0, 1), "n": _scale("first", 2, 0, 1)})         # half meridian
    with m.turned(("z", -tilt), about=(0, cy, 0)):
        _sphere(m, (0, cy, 0), r, LANDS, sides=12, layers=5)
        for a0, a1 in ((cy - r - 2.25, cy - r), (cy + r, cy + r + 2.25)):
            m.tube("y", (0, 0), a0, a1, 0.75, BRASS_D, cap=KNOB)
    return m


def _sextant():
    """A sextant standing in a wooden cradle, the limb down: a brass sector of sixty degrees with a
    graduated arc, the index arm with its clamp, the two glasses, a short telescope and the wooden
    grip behind the right arm. 14 px wide, 17 px tall, 7 px deep. Anchor: the table under its middle."""
    m = M.Model(PREFIX + "sextant")
    top = (0.0, 14.5, 0.0)                              # the pivot of the index arm
    reach = 10.5                                        # radius of the limb's middle line

    def at(deg, radius, z=0.0):
        a = math.radians(deg)
        return (top[0] + radius * math.cos(a), top[1] + radius * math.sin(a), z)

    m.box((-6.5, 0.0, -3.5), (6.5, 2.0, 3.5), WOOD_D)                                   # the cradle
    for x in (-5.5, 3.5):
        m.box((x, 2.0, -1.5), (x + 2.0, 4.0, 1.5), WOOD)
    m.ring("z", top, reach, 2.0, 1.5, BRASS, sides=36, arc=(240.0, 300.0),
           faces={"s": _scale("last", 2, 0, 1), "n": _scale("first", 2, 0, 1)})         # the limb
    for deg in (240.0, 300.0):                                                          # the frame: no cross brace
        m.beam(top, at(deg, reach - 0.5), 1.25, 1.5, BRASS_D)
    m.tube("z", (top[0], top[1]), -0.75, 2.25, 1.5, BRASS, cap=KNOB)                    # pivot
    arm = 280.0                                         # the index arm: off the middle, clear of the cradle
    m.beam(at(arm, 0.5, 1.25), at(arm, reach + 0.5, 1.25), 1.0, 1.25, BRASS)
    c = at(arm, reach, 1.25)
    m.box((c[0] - 1.25, c[1] - 1.25, 0.75), (c[0] + 1.25, c[1] + 1.25, 2.0), BRASS_D)   # its clamp and vernier
    m.tube("z", (c[0], c[1]), 2.0, 3.0, 0.75, BRASS_D, cap=KNOB)
    m.box((-0.5, top[1] - 0.25, 2.25), (0.5, top[1] + 2.5, 3.5), LENS)                  # index glass
    g = at(240.0, 5.5)
    m.box((g[0] - 0.5, g[1] - 1.25, 0.75), (g[0] + 0.5, g[1] + 1.25, 3.0), LENS)        # horizon glass
    t = at(300.0, 5.5)
    m.tube("x", (t[1], 1.75), t[0] - 0.5, t[0] + 4.5, 1.0, BRASS, cap=LENS)             # telescope
    m.tube("x", (t[1], 1.75), t[0] + 0.5, t[0] + 1.5, 1.25, BRASS_D)                    # and its collar
    m.beam(at(300.0, 3.0, -2.75), at(300.0, 9.5, -2.75), 1.5, 2.0, WOOD)                # the grip, behind the right arm
    for radius in (4.0, 8.5):                                                           # on its two posts
        p = at(300.0, radius)
        m.box((p[0] - 0.5, p[1] - 0.5, -2.25), (p[0] + 0.5, p[1] + 0.5, -0.5), BRASS_D)
    return m


BARO_DIAL_Y = 7.0       # height of the dial's centre above the piece's foot


def _barometer():
    """A banjo barometer for the wall, two blocks tall: the round dial at the foot, a long neck with a
    thermometer above it. The dial's marks glow. 12 px wide, 32 px tall, 3.5 px off the wall. Anchor:
    the point on the wall behind the foot."""
    m = M.Model(PREFIX + "barometer")
    y = BARO_DIAL_Y
    m.box((-1.5, 0.0, 0.0), (1.5, 1.0, 2.0), WOOD_D)                                    # drop under the case
    m.tube("z", (0, y), 0.0, 2.0, 6.0, WOOD, sides=16, cap=K.flat("dark_wood", 3))      # the round case
    m.ring("z", (0, y, 2.5), 5.0, 1.5, 1.0, BRASS, sides=16)                            # bezel
    _dial(m, "baro_dial", BARO_DIAL, (0.0, y), 2.5)
    m.tube("z", (0, y - 5.0), 3.0, 3.5, 0.75, BRASS_D, cap=KNOB)                        # set-hand knob, on the bezel
    m.box((-2.5, y + 5.0, 0.0), (2.5, 29.0, 1.0), WOOD, grain="y")                      # neck
    m.box((-1.5, 15.0, 1.0), (1.5, 27.0, 1.25), K.flat("porcelain", 3), skip="nudew",
          faces={"s": _sprite("baro_thermo", ["ctc", "ktc"] * 4 + ["cmc", "kmc"] * 2, c=FACE, k=INK,
                              t=P.RAMPS["porcelain"][4], m=P.RAMPS["iron"][5])})        # thermometer
    for ty in (14.0, 27.0):
        m.box((-1.5, ty, 1.0), (1.5, ty + 1.0, 2.0), BRASS_D)                           # its clips
    m.box((-3.5, 29.0, 0.0), (3.5, 30.0, 2.0), WOOD_D)                                  # cap
    m.box((-1.5, 30.0, 0.0), (1.5, 32.0, 2.0), BRASS_D, faces={"u": KNOB})              # the urn on it
    return m


CLOCK_DIAL_Y = 24.5     # height of the dial's centre above the case's foot
PENDULUM_PIVOT = (0.0, 24.5, 2.5)       # model units from the clock's anchor: behind the middle of the dial
PENDULUM_LENGTH = 17.0                  # pivot to the middle of the bob: a seconds pendulum, a block long


def _regulator_clock():
    """A precision pendulum clock in a long case, two blocks tall: the case 11 px wide, 13 px over the
    plinth and the cornice, 6 px off the wall. The dial fills the hood; under it a glazed door, and
    behind the glass the beat scale under the pendulum's tip. The pendulum is the model
    regulator_pendulum and hangs behind the dial board, the whole of its bob clear of the door's
    rails. Anchor: the point on the wall behind the middle of the case's foot.

    The case is an odd number of pixels wide, like the dial, so that all of it lies on one grid."""
    m = M.Model(PREFIX + "regulator_clock")
    m.box((-5.5, 2.0, 0.0), (5.5, 30.0, 1.0), WOOD_D)                                   # back board
    for x in (-5.5, 4.5):
        m.box((x, 2.0, 1.0), (x + 1.0, 30.0, 5.0), WOOD, grain="y")                     # sides
    m.box((-6.5, 0.0, 0.0), (6.5, 2.0, 6.0), WOOD_D)                                    # plinth
    m.box((-6.5, 30.0, 0.0), (6.5, 32.0, 6.0), WOOD_D)                                  # cornice
    m.box((-4.5, 19.0, 4.0), (4.5, 30.0, 5.0), WOOD_L)                                  # hood: the dial board
    _dial(m, "clock_dial", _hands(CLOCK_DIAL, *CLOCK), (0.0, CLOCK_DIAL_Y), 5.25)
    m.ring("z", (0, CLOCK_DIAL_Y, 5.375), 5.0, 1.0, 0.75, BRASS, sides=16)              # bezel
    for x in (-4.5, 3.5):                                                               # the door: stiles and rails
        m.box((x, 2.0, 4.0), (x + 1.0, 19.0, 5.0), WOOD_L, grain="y")
    for y in (2.0, 18.0):
        m.box((-3.5, y, 4.0), (3.5, y + 1.0, 5.0), WOOD_L, grain="x")
    _pane(m, (-3.5, 3.0, 4.65), (3.5, 18.0, 4.75))                                      # the door's glass
    m.box((-2.5, 3.0, 1.0), (2.5, 4.0, 1.25), K.flat("porcelain", 3), skip="nudew",
          faces={"s": _sprite("clock_beat", ["kckck"], c=FACE, k=INK)})                 # beat scale
    m.tube("z", (4.0, 11.0), 5.0, 6.0, 0.75, BRASS_D, cap=KNOB)                         # door knob
    return m


def _regulator_pendulum():
    """The pendulum of the regulator clock, hanging plumb: a rod and a brass bob with its rating nut.
    Anchor: the pivot it swings about; the swing is a turn about the model's z axis."""
    m = M.Model(PREFIX + "regulator_pendulum")
    m.box((-0.75, -0.75, -0.5), (0.75, 0.25, 0.5), BRASS_D)                             # suspension
    m.box((-0.5, -PENDULUM_LENGTH, -0.25), (0.5, -0.75, 0.25), ROD, grain="y")          # rod
    m.tube("z", (0, -PENDULUM_LENGTH), -0.6, 0.6, 2.5, BRASS, sides=12, cap=KNOB)       # bob
    m.tube("y", (0, 0), -PENDULUM_LENGTH - 3.5, -PENDULUM_LENGTH - 2.5, 0.75, BRASS_D)  # rating nut
    return m


def _louvre_box():
    """A thermometer screen: a white box louvred on all four sides under a pitched roof, on four legs
    bolted to a stone slab; the door is on the +z side. The slab 14 x 12 px, the roof 14 px long and
    15 px over the eaves, 31 px tall. Anchor: the ground under its middle."""
    m = M.Model(PREFIX + "louvre_box")
    m.box((-7.0, 0.0, -6.0), (7.0, 2.0, 6.0), STONE)                                    # slab
    for x in (-6.0, 4.0):
        for z in (-5.0, 3.0):
            m.box((x, 2.0, z), (x + 2.0, 3.0, z + 2.0), IRON_D)                         # iron shoes
            m.box((x, 3.0, z), (x + 2.0, 16.0, z + 2.0), WHITE_D, grain="y")            # legs
            m.box((x, 17.0, z), (x + 2.0, 26.0, z + 2.0), WHITE, grain="y")             # corner posts
    for x in (-6.0, 5.0):                                                               # rails between the legs
        m.box((x, 6.0, -3.0), (x + 1.0, 8.0, 3.0), WHITE_D, grain="z")
    m.box((-4.0, 6.0, -5.0), (4.0, 8.0, -4.0), WHITE_D, grain="x")
    m.box((-5.0, 17.0, -4.0), (5.0, 26.0, 4.0), SLATS)                                  # the louvred panels
    for y in (16.0, 26.0):
        m.box((-6.0, y, -5.0), (6.0, y + 1.0, 5.0), WHITE)                              # bottom and top frame
    m.box((-1.0, 17.0, 4.0), (1.0, 26.0, 5.0), WHITE, grain="y")                        # the meeting stile of the doors
    m.tube("z", (0.5, 21.5), 5.0, 6.0, 0.5, BRASS_D, sides=4, cap=KNOB)                 # door knob
    for half, y0, y1 in ((3.0, 27.0, 28.0), (1.0, 28.0, 29.0)):                         # gables, under the boards
        m.box((-6.0, y0, -half), (6.0, y1, half), WHITE)
    rise, run = 4.0, 7.5
    slope, pitch = math.hypot(rise, run), math.degrees(math.atan2(rise, run))
    for side in (1.0, -1.0):                                                            # the two roof boards: they
        with m.turned(("x", side * pitch), about=(0.0, 30.5, 0.0)):                     # rest on the gables' corners
            lo, hi = sorted((0.0, side * slope))
            m.box((-7.0, 29.5, lo), (7.0, 30.5, hi), WHITE_D, grain="x")
    m.box((-7.25, 30.0, -0.75), (7.25, 31.0, 0.75), IRON_D, grain="x")                  # ridge
    return m


def _calc_machine():
    """A hand-cranked calculating machine on a wooden board: the slotted drum between two iron side
    plates with a brass setting lever standing in each slot, the result register in the carriage in
    front, the crank on the right. 13 px wide, 15.5 px with the crank, 11 px deep, 9 px tall.
    Anchor: the table under the middle of the board."""
    m = M.Model(PREFIX + "calc_machine")
    m.box((-6.5, 0.0, -5.0), (6.5, 1.0, 6.0), WOOD_D)                                   # board
    m.box((-5.5, 1.0, 2.0), (5.5, 4.0, 5.0), IRON_D)                                    # carriage
    m.box((-4.5, 2.0, 5.0), (4.5, 3.0, 5.1), K.flat("porcelain", 3), skip="nudew",
          faces={"s": _sprite("calc_register", ["ckckckckc"], c=FACE, k=INK)})          # result windows
    m.box((-5.5, 1.0, -4.0), (5.5, 3.0, 2.0), IRON)                                     # body
    for x in (-5.5, 4.5):
        m.box((x, 3.0, -4.0), (x + 1.0, 8.0, 2.0), IRON, grain="y")                     # side plates
    axis = (5.0, -1.0)                                                                  # (y, z) of the drum's axis
    m.tube("x", axis, -4.5, 4.5, 3.0, DRUM, sides=12)                                   # the slotted drum
    for x, deg in ((-3.0, 20.0), (-1.0, 55.0), (1.0, 35.0), (3.0, 70.0)):               # a lever in each slot
        with m.turned(("x", deg), about=(0.0, axis[0], axis[1])):
            m.box((x - 0.5, axis[0] + 2.75, axis[1] - 0.5), (x + 0.5, axis[0] + 3.75, axis[1] + 0.5), KNOB)
    m.tube("x", axis, 5.5, 7.0, 0.75, BRASS_D)                                          # crank: axle, arm, grip
    m.beam((6.5, 5.0, -1.0), (6.5, 8.0, 1.0), 1.0, 1.0, BRASS)
    m.tube("x", (8.0, 1.0), 6.5, 9.0, 0.75, WOOD_D, cap=K.flat("dark_wood", 3))
    m.tube("x", (2.5, 3.5), -6.5, -5.5, 1.0, BRASS_D, cap=KNOB)                         # clearing knob on the carriage
    return m


LATITUDE = getattr(S, "LATITUDE", 45.0)         # how high the polar axis stands (the skeleton's, once it has it)


def _sunshine_recorder():
    """A sunshine recorder for a stone pedestal: a glass ball on a brass pillar burns the sun's track
    into the card that lies in the brass bowl behind and below it, a half ring square to the polar
    axis. The ball is seen from the front (+z, the side of the sun). 10 px wide, 10 px tall, 9 px
    deep. Anchor: the pedestal top under its middle."""
    m = M.Model(PREFIX + "sunshine_recorder")
    cy, r = 7.0, 3.0
    m.box((-5.0, 0.0, -5.0), (5.0, 1.0, 4.0), IRON_D)                                   # base plate
    for x in (-4.0, 4.0):
        m.tube("y", (x, 3.0), 1.0, 2.0, 0.75, BRASS_D, cap=KNOB)                        # levelling screws
    m.tube("y", (0, 0), 1.0, 2.0, 2.0, BRASS_D)                                         # the foot of the pillar
    m.tube("y", (0, 0), 2.0, cy - r + 0.25, 1.0, BRASS)                                 # pillar: the ball sits on it
    m.box((-1.0, 2.0, -3.0), (1.0, 3.0, -0.5), BRASS_D)                                 # the arm that carries the bowl
    with m.turned(("x", -LATITUDE), about=(0.0, cy, 0.0)):                              # y is the polar axis in here
        m.ring("y", (0.0, cy, 0.0), r + 1.5, 1.0, 3.0, BRASS, sides=16, arc=(0.0, 180.0),
               faces={"w": _scale("last", 2, 0, 2, ramp="cream")})                      # the bowl and the card in it
    m.ball((0.0, cy, 0.0), r, LENS, sides=12, layers=6)                                 # the glass ball
    # its glint: one white pixel on the facet that looks up and to the left of the front (the second
    # layer from the top, the facet 30 degrees round from +z towards -x), a hair proud of the glass
    girth = r * math.sqrt(1.0 - 0.5 * 0.5)
    with m.turned(("y", -30.0), about=(0.0, cy, 0.0)):
        m.box((-0.5, cy + 1.0, girth), (0.5, cy + 2.0, girth + 0.1), K.flat("porcelain", 4), skip="nudew",
              shade=False)
    return m


# name -> how it is mounted; "table" pieces stand on a floor too
SPEC = {
    "tripod_scope": dict(build=_tripod_scope, mount="floor"),
    "celestial_globe": dict(build=_celestial_globe, mount="floor"),
    "globe": dict(build=_globe, mount="floor"),
    "sextant": dict(build=_sextant, mount="floor"),
    "barometer": dict(build=_barometer, mount="wall"),
    "louvre_box": dict(build=_louvre_box, mount="floor"),
    "regulator_clock": dict(build=_regulator_clock, mount="wall"),
    "regulator_pendulum": dict(build=_regulator_pendulum, mount="wall"),
    "calc_machine": dict(build=_calc_machine, mount="floor"),
    "sunshine_recorder": dict(build=_sunshine_recorder, mount="floor"),
}
SCALE = {PREFIX + name: 1.0 for name in SPEC}
# what motion needs to swing the pendulum: the entity carries the tag, stands on the pivot and turns
# about the axis the clock faces along (the model's z); a seconds pendulum, a block long
PENDULUM = dict(tag="c164_pendulum", pivot=tuple(v / 16.0 for v in PENDULUM_PIVOT), axis="z",
                swing=3.0, period_ticks=40)


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: spec["build"]() for name, spec in SPEC.items()}


def models():
    return dict(_models())


# ---- placing -----------------------------------------------------------------------------------------
def place(canvas, kind, pos, facing="south", origin=(0, 0, 0), yaw=None, **opts):
    """Put one instrument into the scene; returns the number of display entities (1; the clock 2).

    kind     a key of SPEC ("regulator_pendulum" comes with the clock).
    pos      scene coordinates. A standing piece: the middle of its foot on the floor or on the
             table top. "barometer" and "regulator_clock": the point on the wall face behind the
             middle of the piece's foot (both are 2 blocks tall from there).
    facing   the way the piece's front looks: the telescope's objective, the door of the louvre
             box, the dials; for the two wall pieces the way the wall face looks. yaw (degrees)
             turns a standing piece freely instead.
    opts     go to artkit.models.display (brightness, view).
    """
    spec = SPEC[kind]
    yaw = K.FACING[facing] if yaw is None else yaw
    n = K.put(canvas, _models()[PREFIX + kind], pos, mount=spec["mount"], yaw=yaw, origin=origin, **opts)
    if kind == "regulator_clock":
        dx, dy, dz = K.turn(yaw, PENDULUM["pivot"])
        n += K.put(canvas, _models()[PREFIX + "regulator_pendulum"], (pos[0] + dx, pos[1] + dy, pos[2] + dz),
                   mount="wall", yaw=yaw, origin=origin, **opts)
        canvas.entities[-1][3]["Tags"].append(PENDULUM["tag"])
    return n


# ---- the site --------------------------------------------------------------------------------------------
# The rooms and the outbuildings place their instruments themselves, with place(). One piece is left
# to this package, because site/terrain is blocks only: the telescope of the sunset terrace (plan
# ART-PLAN 4). It stands on the axis at the west end of the walk from the west door, in line with the
# inner pair of benches that props/furniture sets either side of the walk, and looks west over the
# rail at the afterglow: who comes out of the west door walks straight up to its eyepiece. The two
# blocks between it and the rail stay free to walk in. The switch, dress() and site() work like
# those of props/furniture.
DRESS = False           # off in the master scene until the family has passed review; a test scene asks
                        # for the site's instruments with dress(canvas), or calls site()
SUNSET_SCOPE = 16.0     # blocks west of the middle of the terrace's half-circle, on the axis


def site_pieces():
    """The instruments of the site as (group, kind, point, yaw). point is the middle of the piece's
    foot in scene coordinates before the origin."""
    cx, cz = S.SUNSET_PLATFORM["centre"]
    return [("sunset", "tripod_scope", (S.mid(cx) - SUNSET_SCOPE, float(S.GROUND), S.mid(cz)), K.FACING["west"])]


def _stands(canvas, foot, origin=(0, 0, 0)):
    """True when the piece has a floor under the middle of its foot on the canvas as it is, and room
    to stand in: the cell below is taken and the cell above that is free (a light source in it
    does not count)."""
    x, z = math.floor(foot[0] + origin[0]), math.floor(foot[2] + origin[2])
    y = math.ceil(foot[1] + origin[1])
    return canvas.has(x, y - 1, z) and canvas.name(x, y, z) in (None, B.LIGHT)


def dress(canvas, on=True):
    """Ask for the instruments of the site on this canvas while the switch DRESS is off (a test
    scene). Call it before the lines are built."""
    canvas.instruments_dress = bool(on)


def site(canvas, origin=(0, 0, 0), groups=None):
    """Place the instruments of the site (site_pieces()), or of the groups named ("sunset"). A piece
    is only placed where its floor is on the canvas as it is, so a tree without the terrace has no
    telescope floating in the air; what was left out is kept in canvas.instruments_left_out as
    (group, kind, point). A piece is placed once: a second call adds what does not stand yet.
    Returns the number of display entities placed by this call."""
    origin = tuple(origin)
    placed = getattr(canvas, "instruments_placed", None)
    if placed is None:
        placed = canvas.instruments_placed = set()
    n, left = 0, list(getattr(canvas, "instruments_left_out", []))
    for group, kind, p, yaw in site_pieces():
        if (groups is not None and group not in groups) or (kind, p, origin) in placed:
            continue
        if _stands(canvas, p, origin):
            n += place(canvas, kind, p, yaw=yaw, origin=origin)
            placed.add((kind, p, origin))
        elif (group, kind, p) not in left:
            left.append((group, kind, p))
    canvas.instruments_left_out = [e for e in left if (e[1], e[2], origin) not in placed]
    return n


def build(canvas, origin=(0, 0, 0)):
    """What this package places in the master scene itself: the instruments of the site (site()),
    once the switch DRESS is on or a test scene has asked for it (dress()). Everything else is
    placed by the lines that build the rooms and the outbuildings, each piece where it is used,
    with place()."""
    if getattr(canvas, "instruments_dress", DRESS):
        return site(canvas, origin)
    return 0
