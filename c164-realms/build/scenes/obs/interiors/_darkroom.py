"""interiors/_darkroom: what stands in the darkroom of the plate vault, and the hand lift that takes
the plates up to the chart room (card plan/packages/interiors/platevault.md). A kit: the room
(interiors/platevault) owns the walls, the light and the places, and calls dress() and lift(), or
place() piece by piece. A module whose name starts with "_" is no package of its own.

Pieces (place(canvas, kind, pos, facing)); every one is a single display entity, 16 texels to the block:

  against a wall (pos: the point of the wall face at floor level under the piece's middle;
  facing: the way the piece looks into the room)
    sink        a stone trough three cells wide on two piers, two brass taps on a copper supply
                that comes down the wall, a lead waste into the wall, water standing in it
    bench       two cells of the wet bench: a slate top on a wooden frame, a jug and spare trays
                on its low shelf. Put side by side they make a longer bench.
    rack        a cell and a half of drying rack: two tiers of glass plates on edge over a zinc
                drip tray. Two of them fill three cells.
  on a wall (pos: the point of the wall face behind the piece's middle)
    shelf       a bracketed shelf of chemicals: stoppered bottles, a jar, a tin
    safelight   the red lamp: a tin lantern on a bracket, red glass to the front, the sides and
                below; the only thing in the room that glows (LIGHT is its cell, see light_cell())
    timer       the darkroom clock: one hand on a dial of sixty, a bell on top
    crank       the lift's winch: a crank wheel on a bearing plate, on the side of the shaft's frame
  on a surface (pos: the middle of the piece's underside)
    tray_dev, tray_stop, tray_fix   the three developing trays, a plate lying in the first and the last
  the lift (pos: the middle of the shaft cell's floor; facing: the way its opening looks)
    lift_frame  three blocks of the shaft's iron frame, latticed on three sides; they stack
    lift_car    the car, a wooden box open to the front, a box of plates in it
    rope        (not placed by kind) the hoisting rope, stretched by lift()

TOP gives the heights of the surfaces things stand on, SIZE the room each piece takes (across,
up, out, in blocks): a display entity stops nobody, the room sets what must not be walked through.
"""
import functools
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from ..props import _kit as K

PREFIX = "int_vault_dark_"
PX = 1.0 / 16.0

STONE = P.mat("ashlar", base=2)                         # the trough: the hill's pale stone, a step down in the dark
PIER = P.mat("slate")
WOOD = P.mat("dark_wood")
WOOD_L = P.mat("dark_wood", base=3)
SLATE = P.mat("slate", noise=0.16, bevel=0)
ZINC = P.mat("iron", base=4)
LEAD = P.mat("iron_dark")
WATER = K.flat("night_glass", 1)
ENAMEL_W = P.mat("porcelain")                           # enamelled ware: trays, the jug
PLATE_GLASS = P.mat("night_glass", base=2)              # a glass plate seen edge on
BROWN, BROWN_D = K.flat("old_copper", 1), K.flat("old_copper", 0)       # brown bottle glass
BLUE = K.flat("enamel", 2)                              # the one blue bottle
CORK = K.flat("old_copper", 3)
LABEL = K.flat("cream", 2)
ROPE = P.mat("cream", base=1)
RED, RED_HOT, RED_DIM = K.flat("signal", 2), K.flat("signal", 3), K.flat("signal", 1)

# what a tray holds: (the bath's tone, does a plate lie in it)
BATHS = {"dev": (K.flat("old_copper", 0), True), "stop": (K.flat("night_glass", 2), False),
         "fix": (K.flat("iron", 3), True)}

SINK_W, SINK_OUT, SINK_RIM = 46.0, 13.0, 14.0           # texels: across, out from the wall, the rim's height
BENCH_W, BENCH_OUT, BENCH_TOP = 32.0, 13.5, 14.5
RACK_W, RACK_OUT, RACK_H = 24.0, 12.0, 30.0
TIERS = (9.0, 19.5)                                     # the rails of the rack's two tiers
TRAY = (12.0, 2.25, 9.0)
CAR = 12.5                                              # the car is this wide and deep; the frame is the cell
CAR_H = 13.0
LANTERN = (8.0, 9.0, 6.0)                               # the safelight's housing: across, up, out
GLASS_H = 7.0                                           # its red front is this high, about the anchor

# heights above the floor, in blocks, of the surfaces things are put on
TOP = {"bench": BENCH_TOP * PX, "sink": SINK_RIM * PX, "car": 1.0 * PX}
# the room a piece takes, in blocks: (across, up, out of the wall or front to back)
SIZE = {"sink": (3.0, 24.0 * PX, SINK_OUT * PX), "bench": (2.0, BENCH_TOP * PX, BENCH_OUT * PX),
        "rack": (1.5, RACK_H * PX, RACK_OUT * PX), "shelf": (28.0 * PX, 13.0 * PX, 5.0 * PX),
        "safelight": (8.5 * PX, 17.0 * PX, 9.5 * PX), "timer": (10.0 * PX, 15.5 * PX, 3.0 * PX),
        "lift_frame": (1.0, 3.0, 1.0), "lift_car": (CAR * PX, 14.5 * PX, CAR * PX)}
LIGHT = (0.0, 0.0, 0.4)                                 # blocks from the safelight's anchor to the cell it lights from
TAP = (9.0 * PX, 17.0 * PX, 5.0 * PX)                   # the right tap's mouth from the sink's anchor (the other: -x)


# ---- against a wall -------------------------------------------------------------------------------
def _sink():
    """Anchor: on the wall face at floor level, under the middle. +z comes out of the wall."""
    m = M.Model(PREFIX + "sink")
    w, out, rim = SINK_W / 2.0, SINK_OUT, SINK_RIM
    for x in (-21.0, 16.0):
        m.box((x, 0, 1.5), (x + 5.0, 8, out - 2.0), PIER, grain="y")
    m.box((-w, 8, 0.25), (w, 9.5, out), STONE)                              # the trough: a floor and four walls
    m.box((-w, 9.5, out - 1.75), (w, rim, out), STONE)
    m.box((-w, 9.5, 0.25), (w, rim, 2.0), STONE)
    for x in (-w, w - 1.75):
        m.box((x, 9.5, 2.0), (x + 1.75, rim, out - 1.75), STONE)
    m.box((-w + 1.75, 9.5, 2.0), (w - 1.75, 11.5, out - 1.75), WATER, skip="nsewd")
    m.box((-w, rim, 0), (w, 20, 1), STONE)                                  # the splash back
    # the supply: down the wall beside the lamp, along the top of the splash back, a tap at either end
    m.tube("y", (-15.0, 1.0), 21.5, 40.0, 0.75, K.COPPER)
    K.wall_entry(m, -15.0, 40.0)
    m.tube("x", (21.5, 1.0), -15.75, 9.75, 0.75, K.COPPER)
    for x in (-9.0, 9.0):
        m.tube("z", (x, 21.5), 1.0, 5.0, 0.9, K.BRASS)
        m.tube("y", (x, 5.0), 17.0, 22.4, 0.9, K.BRASS)
        m.box((x - 0.5, 22.4, 4.5), (x + 0.5, 23.25, 5.5), K.BRASS_D)
        m.box((x - 2.0, 23.25, 4.5), (x + 2.0, 24.0, 5.5), K.BRASS)
    # the waste: a lead trap under the trough, into the wall
    m.tube("y", (0.0, 6.5), 3.0, 8.0, 1.25, LEAD)
    m.tube("z", (0.0, 3.0), 0.75, 7.75, 1.25, LEAD)
    m.tube("z", (0.0, 3.0), 0.0, 0.75, 2.25, K.IRON)
    return m


def _bench():
    """Anchor: on the wall face at floor level, under the middle."""
    m = M.Model(PREFIX + "bench")
    w, out, top = BENCH_W / 2.0, BENCH_OUT, BENCH_TOP
    m.box((-w, top - 1.5, 0.25), (w, top, out), SLATE)
    for x in (-w + 1.0, w - 3.0):
        for z in (1.5, out - 3.0):
            m.box((x, 0, z), (x + 2.0, top - 1.5, z + 2.0), WOOD, grain="y")
    for z in (2.0, out - 2.5):
        m.box((-w + 3.0, top - 4.0, z), (w - 3.0, top - 1.5, z + 1.0), WOOD, grain="x")
    for x in (-w + 1.5, w - 2.5):
        m.box((x, top - 4.0, 3.5), (x + 1.0, top - 1.5, out - 3.0), WOOD, grain="z")
    m.box((-w + 1.5, 3.5, 2.0), (w - 1.5, 4.5, out - 1.5), WOOD_L, grain="x")       # the low shelf
    # on it: an enamelled jug and a stack of spare trays
    m.tube("y", (-9.0, 7.0), 4.5, 9.5, 2.5, ENAMEL_W)
    m.tube("y", (-9.0, 7.0), 9.5, 10.0, 2.75, K.flat("enamel", 1))
    m.box((-6.5, 6.5, 6.5), (-5.5, 8.5, 7.5), ENAMEL_W)
    for i, shift in enumerate((0.0, 0.5, -0.25)):
        m.box((1.0 + shift, 4.5 + 1.25 * i, 3.0), (12.0 + shift, 5.5 + 1.25 * i, 10.5), ENAMEL_W)
    return m


def _rack():
    """Anchor: on the wall face at floor level, under the middle."""
    m = M.Model(PREFIX + "rack")
    w, out, h = RACK_W / 2.0, RACK_OUT, RACK_H
    for x in (-w, w - 1.5):
        for z in (1.0, out - 2.5):
            m.box((x, 0, z), (x + 1.5, h, z + 1.5), WOOD, grain="y")
        for y in (2.5, h - 1.5):
            m.box((x, y, 2.5), (x + 1.5, y + 1.5, out - 2.5), WOOD, grain="z")
    m.box((-w + 1.0, 4.0, 1.0), (w - 1.0, 4.75, out - 1.0), ZINC)                   # the drip tray
    m.box((-w + 1.0, 4.75, out - 1.5), (w - 1.0, 5.5, out - 1.0), ZINC)
    for tier, y in enumerate(TIERS):
        for z in (1.25, out - 2.75):
            m.box((-w + 1.5, y, z), (w - 1.5, y + 1.0, z + 1.5), WOOD_L, grain="x")
        # plates on edge, across the rails; not every slot is taken
        for i in range(9):
            if (i + 3 * tier) % 5 == 4:
                continue
            x = -8.6 + 2.15 * i
            m.box((x, y + 1.0, 1.5), (x + 0.4, y + 1.0 + (8.0 if (i + tier) % 3 else 6.5), out - 1.5), PLATE_GLASS)
    return m


# ---- on a wall ------------------------------------------------------------------------------------
def _bottle(m, x, z, radius, height, glass, label=True):
    """A stoppered bottle standing on the plane y 0 at (x, z)."""
    m.tube("y", (x, z), 0.0, height, radius, glass)
    m.tube("y", (x, z), height, height + 0.75, radius * 0.6, glass)
    m.tube("y", (x, z), height + 0.75, height + 2.0, 0.6, glass)
    m.tube("y", (x, z), height + 2.0, height + 2.75, 0.8, CORK)
    if label:
        m.box((x - radius * 0.4, height * 0.3, z + radius), (x + radius * 0.4, height * 0.7, z + radius + 0.1), LABEL,
              skip="nudew")


def _shelf():
    """Anchor: on the wall face, at the middle of the board's top edge. +z comes out of the wall."""
    m = M.Model(PREFIX + "shelf")
    m.box((-14, -0.75, 0), (14, 0, 5), WOOD, grain="x")
    for x in (-10.5, 9.5):
        m.box((x, -5.0, 0), (x + 1.0, -0.75, 1.0), K.IRON)
        m.box((x, -1.5, 1.0), (x + 1.0, -0.75, 4.5), K.IRON)
        m.beam((x + 0.5, -4.5, 1.0), (x + 0.5, -1.5, 4.0), 0.75, 0.75, K.IRON_D)
    _bottle(m, -11.5, 2.5, 1.75, 5.0, BROWN)
    _bottle(m, -7.0, 2.75, 1.25, 7.0, BLUE)
    m.tube("y", (-2.25, 2.5), 0.0, 4.5, 2.25, ENAMEL_W)                             # a jar with a brass lid
    m.tube("y", (-2.25, 2.5), 4.5, 5.25, 2.4, K.BRASS_D)
    _bottle(m, 3.0, 2.5, 1.75, 6.0, BROWN_D)
    m.box((6.0, 0, 1.0), (9.5, 5.0, 4.0), ZINC)                                     # a tin
    m.box((6.75, 1.5, 4.0), (8.75, 3.5, 4.1), LABEL, skip="nudew")
    _bottle(m, 12.0, 2.75, 1.5, 4.0, BROWN, label=False)
    return m


def _safelight():
    """Anchor: on the wall face, level with the middle of the red glass. +z comes out of the wall."""
    m = M.Model(PREFIX + "safelight")
    w, h, out = LANTERN[0] / 2.0, LANTERN[1] / 2.0, LANTERN[2]
    g = GLASS_H / 2.0
    lit = dict(emit=15, shade=False)
    m.box((-3.5, -5.5, 0), (3.5, 5.5, 0.75), K.IRON, grain="y")
    for x in (-2.5, 2.5):
        for y in (-4.5, 4.5):
            K.rivet(m, (x, y, 0.75))
    m.box((-1.0, -1.0, 0.75), (1.0, 1.0, 3.0), K.IRON_D)
    m.tube("y", (0.0, 1.0), 5.5, 11.5, 0.6, K.IRON_D)                               # the conduit, up and into the wall
    K.wall_entry(m, 0.0, 11.5, 0.6)
    z0, z1 = 3.0, 3.0 + out
    m.box((-w, -h, z0), (w, h, z1), K.IRON)                                         # the lantern
    m.box((-w - 0.5, h, z0 - 0.5), (w + 0.5, h + 0.75, z1 + 0.5), K.IRON_D)
    m.tube("y", (0.0, (z0 + z1) / 2.0), h + 0.75, h + 2.5, 1.5, K.IRON_D)           # its vent
    m.tube("y", (0.0, (z0 + z1) / 2.0), h + 2.5, h + 3.25, 2.25, K.IRON)
    m.box((-w + 1.0, -g, z1), (w - 1.0, g, z1 + 0.25), RED, skip="nudew", **lit)    # the red glass
    m.box((-w + 2.5, -g + 1.5, z1 + 0.25), (w - 2.5, g - 1.5, z1 + 0.4), RED_HOT, skip="nudew", **lit)
    m.box((w, -g, z0 + 1.0), (w + 0.25, g, z1 - 1.0), RED, skip="nsudw", **lit)
    m.box((-w - 0.25, -g, z0 + 1.0), (-w, g, z1 - 1.0), RED, skip="nsude", **lit)
    m.box((-w + 1.0, -h - 0.25, z0 + 1.0), (w - 1.0, -h, z1 - 1.0), RED_DIM, skip="nsewu", **lit)
    return m


FACE, MARK = P.RAMPS["porcelain"][3], P.RAMPS["iron"][5]
DIAL = [
    "..mchcm..",
    ".mcchccm.",
    "cccchcccc",
    "mccchcccm",
    "ccccbcccr",
    "mcccccccm",
    "ccccccccc",
    ".mcccccm.",
    "..mcmcm..",
]
DIAL_COLOURS = dict(c=FACE, m=MARK, h=P.RAMPS["iron"][0], b=P.RAMPS["brass"][3], r=P.RAMPS["signal"][2])


def _timer():
    """Anchor: on the wall face, behind the middle of the dial. The hand stands at nought; the red
    mark is where it was set to ring."""
    m = M.Model(PREFIX + "timer")
    m.tube("z", (0.0, 0.0), 0.0, 2.0, 5.0, K.BRASS_D, sides=12)
    m.tube("z", (0.0, 0.0), 2.0, 2.5, 5.0, K.BRASS, sides=12, cap=K.BRASS)
    m.box((-4.5, -4.5, 2.5), (4.5, 4.5, 2.75), K.flat("porcelain", 3), skip="nudew",
          faces={"s": Sprite(PREFIX + "timer_dial", DIAL, DIAL_COLOURS)})
    m.ball((0.0, 5.0, 2.25), 2.25, K.BRASS, sides=8, layers=3, part=(0.0, 1.0))     # the bell
    m.box((-0.4, 7.25, 1.85), (0.4, 8.0, 2.65), K.BRASS_D)
    m.box((-0.5, -6.5, 0.75), (0.5, -5.0, 1.5), K.BRASS_D)                          # the key
    m.box((-1.5, -7.5, 0.75), (1.5, -6.5, 1.5), K.BRASS)
    return m


def _crank():
    """Anchor: on the face it is fixed to, at the axle. +z comes out of that face."""
    m = M.Model(PREFIX + "crank")
    m.box((-2.0, -2.5, 0), (2.0, 2.5, 0.75), K.IRON, grain="y")
    m.tube("z", (0.0, 0.0), 0.75, 3.25, 0.6, K.IRON_D)
    m.tube("z", (0.0, 0.0), 0.75, 2.0, 1.75, K.IRON)                                # the drum's cheek
    m.ring("z", (0.0, 0.0, 2.75), 4.25, 0.9, 0.9, K.IRON, sides=16)
    m.box((-4.25, -0.4, 2.35), (4.25, 0.4, 3.15), K.IRON_D)
    m.box((-0.4, -4.25, 2.35), (0.4, 4.25, 3.15), K.IRON_D)
    m.tube("z", (3.0, 3.0), 3.15, 6.0, 0.6, K.BRASS)                                # the handle
    return m


# ---- on a surface ---------------------------------------------------------------------------------
NEGATIVE = [
    "ccdcc",
    "cdccc",
    "cccdc",
    "dcccc",
]


def _tray(name):
    """Anchor: the middle of the underside."""
    bath, plate = BATHS[name]
    m = M.Model(PREFIX + "tray_" + name)
    w, h, d = TRAY[0] / 2.0, TRAY[1], TRAY[2] / 2.0
    m.box((-w, 0, -d), (w, 0.5, d), ENAMEL_W)
    for z in (-d, d - 0.75):
        m.box((-w, 0.5, z), (w, h, z + 0.75), ENAMEL_W)
    for x in (-w, w - 0.75):
        m.box((x, 0.5, -d + 0.75), (x + 0.75, h, d - 0.75), ENAMEL_W)
    m.box((-w + 0.75, 0.5, -d + 0.75), (w - 0.75, 1.5, d - 0.75), bath, skip="nsewd")
    if plate:
        tones = {"c": P.RAMPS["iron"][4], "d": P.RAMPS["iron"][1]}
        m.box((-2.5, 1.5, -2.0), (2.5, 1.75, 2.0), K.flat("iron", 4), skip="d",
              faces={"u": Sprite(PREFIX + "negative_" + name, NEGATIVE, tones)})
    return m


# ---- the lift -------------------------------------------------------------------------------------
def _lift_frame():
    """Three blocks of the shaft: four angle posts, bands and a lattice on the back and the sides,
    guides for the car; open to the front (+z). Anchor: the middle of the cell's floor."""
    m = M.Model(PREFIX + "lift_frame")
    for x in (-8.0, 6.75):
        for z in (-8.0, 6.75):
            m.box((x, 0, z), (x + 1.25, 48, z + 1.25), K.IRON, grain="y")
    for y in (0.0, 23.4, 46.75):
        m.box((-6.75, y, -8.0), (6.75, y + 1.25, -7.25), K.IRON)
        for x in (-8.0, 7.25):
            m.box((x, y, -6.75), (x + 0.75, y + 1.25, 6.75), K.IRON)
    for y0, y1 in ((1.25, 23.4), (24.65, 46.75)):
        for a, b in ((-6.75, 6.75), (6.75, -6.75)):
            m.beam((a, y0, -7.6), (b, y1, -7.6), 0.5, 0.75, K.IRON_D)
            for x in (-7.6, 7.6):
                m.beam((x, y0, a), (x, y1, b), 0.5, 0.75, K.IRON_D)
    for x in (-7.25, 6.5):
        m.box((x, 0, -0.5), (x + 0.75, 48, 0.5), K.IRON_D, grain="y")
    return m


def _lift_car():
    """The car: a wooden box open to the front (+z), an eye for the rope on its top; in it a box of
    plates with brass corners. Anchor: the middle of the underside."""
    m = M.Model(PREFIX + "lift_car")
    w, h = CAR / 2.0, CAR_H
    m.box((-w, 0, -w), (w, 1, w), WOOD, grain="x")
    m.box((-w, 1, -w), (w, h - 1.0, -w + 0.75), WOOD_L, grain="y")
    for x in (-w, w - 0.75):
        m.box((x, 1, -w + 0.75), (x + 0.75, h - 1.0, w), WOOD_L, grain="y")
    m.box((-w, h - 1.0, -w), (w, h, w), WOOD, grain="x")
    m.box((-w + 0.75, 1, w - 0.75), (w - 0.75, 2.0, w), WOOD, grain="x")            # the lip that keeps the box in
    m.tube("y", (0.0, 0.0), h, h + 0.75, 1.5, K.IRON)
    m.ring("x", (0.0, h + 1.5, 0.0), 0.9, 0.5, 0.5, K.IRON_D, sides=8)
    # the box of plates
    m.box((-4.0, 1, -3.5), (4.0, 6.0, 3.0), WOOD, grain="x")
    m.box((-4.25, 5.0, -3.75), (4.25, 6.5, 3.25), WOOD_L, grain="x")                # its lid
    for x in (-4.3, 3.3):
        m.box((x, 1, 2.3), (x + 1.0, 2.0, 3.05), K.BRASS_D)
        m.box((x, 5.5, 2.3), (x + 1.0, 6.5, 3.3), K.BRASS_D)
    m.box((-1.5, 2.5, 3.0), (1.5, 4.25, 3.1), LABEL, skip="nudew")
    m.box((-0.5, 4.5, 3.25), (0.5, 5.5, 3.6), K.BRASS)                              # the clasp
    return m


def _rope():
    """The hoisting rope: along +z from the anchor, 48 long; lift() stretches it."""
    m = M.Model(PREFIX + "rope")
    m.box((-0.5, -0.5, 0), (0.5, 0.5, 48), ROPE, grain="z")
    return m


# name -> how it is made and how it is mounted
SPEC = {
    "sink": dict(build=_sink, mount="wall"),
    "bench": dict(build=_bench, mount="wall"),
    "rack": dict(build=_rack, mount="wall"),
    "shelf": dict(build=_shelf, mount="wall"),
    "safelight": dict(build=_safelight, mount="wall"),
    "timer": dict(build=_timer, mount="wall"),
    "crank": dict(build=_crank, mount="wall"),
    "tray_dev": dict(build=lambda: _tray("dev"), mount="floor"),
    "tray_stop": dict(build=lambda: _tray("stop"), mount="floor"),
    "tray_fix": dict(build=lambda: _tray("fix"), mount="floor"),
    "lift_frame": dict(build=_lift_frame, mount="floor"),
    "lift_car": dict(build=_lift_car, mount="floor"),
}
KINDS = tuple(SPEC)


@functools.lru_cache(maxsize=None)
def _models():
    built = {PREFIX + kind: spec["build"]() for kind, spec in SPEC.items()}
    built[PREFIX + "rope"] = _rope()
    return built


def models():
    """Every model of the kit, by name, for the scene's pack."""
    return dict(_models())


def place(canvas, kind, pos, facing="north", origin=(0, 0, 0), yaw=None, **opts):
    """Put one piece into the scene; returns the number of display entities (1). pos is as the head
    of this file says for the piece's kind; opts go to artkit.models.display (brightness, view)."""
    spec = SPEC[kind]
    yaw = K.FACING[facing] if yaw is None else yaw
    return K.put(canvas, _models()[PREFIX + kind], pos, mount=spec["mount"], yaw=yaw, origin=origin, **opts)


def light_cell(pos, facing="north", origin=(0, 0, 0)):
    """The cell before a safelight placed at pos, where the room asks for its light."""
    return K.light_cell(pos, K.FACING[facing], LIGHT, origin)


# ---- the darkroom as the card has it -------------------------------------------------------------
# Skeleton coordinates (vault, 11-16): the room's clear cells are x 2..13, z 23..25, feet at y 0; the
# south wall's face is z 26. Along that wall, from the west: the drying racks (x 3..5), the sink
# (x 6..8) with the red lamp over it on the room's axis, the timer, the wet bench (x 9..12) with the
# three trays and the shelf of chemicals over it.
WALL_Z = 26.0
FEET = 0
AXIS_X = 7.5
LAMP_Y = 2.45                                           # the red glass is seen under the arch's head (y 3.0)
RACKS_X = (3.75, 5.25)
BENCH_X = (10.0, 12.0)
TRAYS = (("tray_dev", 9.75), ("tray_stop", 11.0), ("tray_fix", 12.25))
SHELF_AT = (11.0, 1.625)
TIMER_AT = (9.375, 1.75)


def dress(canvas, origin=(0, 0, 0), wall_z=WALL_Z, feet=FEET, **opts):
    """The darkroom's pieces along its south wall; returns the number of display entities (11)."""
    put = functools.partial(place, canvas, facing="north", origin=origin, **opts)
    n = put("sink", (AXIS_X, feet, wall_z))
    n += put("safelight", (AXIS_X, feet + LAMP_Y, wall_z))
    n += put("timer", (TIMER_AT[0], feet + TIMER_AT[1], wall_z))
    n += put("shelf", (SHELF_AT[0], feet + SHELF_AT[1], wall_z))
    for x in RACKS_X:
        n += put("rack", (x, feet, wall_z))
    for x in BENCH_X:
        n += put("bench", (x, feet, wall_z))
    z = wall_z - (BENCH_OUT / 2.0 + 0.5) * PX
    for kind, x in TRAYS:
        n += put(kind, (x, feet + TOP["bench"], z))
    return n


def lamp_cell(origin=(0, 0, 0), wall_z=WALL_Z, feet=FEET):
    """The cell the room asks the red lamp's light for, when the darkroom is dressed by dress()."""
    return light_cell((AXIS_X, feet + LAMP_Y, wall_z), "north", origin)


# ---- the hand lift --------------------------------------------------------------------------------
CAR_AT = 0.75           # the car's floor above the shaft's: it waits at the height of a table
CRANK_AT = 1.125        # the winch's axle above the floor


def lift(canvas, cell, facing="east", origin=(0, 0, 0), top=6, car=CAR_AT, **opts):
    """The hand lift in the shaft cell `cell` = (x, y, z), y its floor: the frame from the floor to
    `top` blocks above it (in lengths of three), the car `car` blocks up with its box of plates,
    the rope from the car to the top, and the winch on the frame's left side as one looks in (for an
    opening that looks east: its south side), its wheel in the cell beside the shaft. facing is the
    way the opening looks. The shaft's cells are air. Returns the number of display entities (5
    for top=6)."""
    yaw = K.FACING[facing]
    x, y, z = cell[0] + 0.5, float(cell[1]), cell[2] + 0.5
    n = 0
    for i in range(int(math.ceil(top / 3.0))):
        n += place(canvas, "lift_frame", (x, y + 3.0 * i, z), origin=origin, yaw=yaw, **opts)
    n += place(canvas, "lift_car", (x, y + car, z), origin=origin, yaw=yaw, **opts)
    a = (x + origin[0], y + car + (CAR_H + 2.0) * PX + origin[1], z + origin[2])
    b = (a[0], y + top + origin[1], a[2])
    canvas.add_entity(a[0], a[1], a[2], M.between(_models()[PREFIX + "rope"], a, b, thick=0.75, **opts))
    n += 1
    dx, _, dz = K.turn(yaw, (-0.5, 0.0, 0.0))
    n += place(canvas, "crank", (x + dx, y + CRANK_AT, z + dz), origin=origin, yaw=yaw + 90.0, **opts)
    return n
