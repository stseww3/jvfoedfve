"""props/furniture -- the furniture of the observatory (plan ART-PLAN 7.3, part A6 section 2.6,
card plan/packages/props/furniture.md).

One family, one motif: dark wood carried on cast iron, brass where a hand goes. The iron is always
the same casting -- a flat bar bent in an S that ends in a rolled eye -- whether it is the end frame
of a bench, of a desk, or one claw of a column foot. Brass is small: pulls, bolts, a rail, a hook.

    bench            two blocks wide: slats on two cast end frames with arm rests (the terraces, the
                     cable-car station, the star hall)
    writing_desk     two blocks wide: a panelled top, three drawers in the frieze, a low gallery
    drafting_table   two blocks wide: a board tilted on a cast A-frame and held by a brass quadrant,
                     a sheet pinned to it
    swivel_chair     a wooden seat and bow back on a screw column and five claws
    stool            a tall round stool on three legs with a brass foot ring
    card_cabinet     two blocks tall: eighteen card drawers, each with its label and brass pull
    instrument_cabinet  two blocks tall: a cupboard under glazed shelves of eyepieces (the dome room)
    library_ladder   three blocks tall, leans on a bookcase; its rollers ride on ladder_rail
    ladder_rail      one block of that brass rail (rail() lays a run of it)
    coat_stand       two blocks tall: a turned post on three claws, brass hooks
    trunk            a canvas travelling trunk with leather straps and brass corners
    crate            a plank crate
    display_case     a glazed brass case on a panelled base (the star hall)

Every piece is one display entity at scale 1 (16 texels to the block). Nothing here is spread over
the building: the rooms and the site place what they need with place(); build() places nothing.
No piece has four arms at right angles about its column: feet and hooks come in threes and fives.

The look is judged in the test scene build/scenes/obs_props_furniture.
"""
import functools
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from . import _kit as K

PREFIX = "prop_furn_"

WOOD = P.mat("dark_wood")                         # slats, case sides
WOOD_L = P.mat("dark_wood", base=3)               # the lighter board: panels, drawer fronts
WOOD_D = P.mat("dark_wood", base=1)               # frames, plinths, cornices
LEATHER = P.mat("dark_wood", kind="plain", noise=0.10, base=1)
IRON = P.mat("iron", bevel="along")               # a cast bar: light and dark edge along it only
IRON_D = K.IRON_D
BRASS, BRASS_D = K.BRASS, K.BRASS_D
BOLT = K.flat("brass", 4)
CANVAS = P.mat("cream_cloth", base=1)
PAPER = P.mat("cream", base=2)
PENCIL, INK, LABEL = P.RAMPS["cream"][0], P.RAMPS["iron"][2], P.RAMPS["cream"][1]

LEAN = 10.0                     # degrees a bench's back leans
TILT = 40.0                     # degrees the drafting board is tilted
RAIL_Y = 44.5 / 16.0            # the ladder rail's height above the floor the ladder stands on
RAIL_OUT = 1.0 / 16.0           # and how far its centre is off the bookcase front

# what is pinned to the drafting board: a chart of a hemisphere, begun (pencil circle, inked stars,
# a few ruled ticks beside it; no writing)
SHEET = Sprite("furn_draft_sheet", [
    "..................",
    ".....ppppp........",
    "...pp.....pp......",
    "..p....i....p..ll.",
    "..p.i.......p.....",
    "..p......i..p..ll.",
    "..p..i......p.....",
    "..p.......i.p..ll.",
    "...pp.....pp......",
    ".....ppppp........",
    "..................",
], {"p": PENCIL, "l": PENCIL, "i": INK}, back=PAPER)


# ---- the casting ---------------------------------------------------------------------------------
def _cast(m, x, pts, width=1.5, thick=1.0, mat=IRON):
    """A cast bar bent through the points [(z, y), ...] of the upright plane at x: `width` across
    the plane, `thick` in it. Each length runs a little into the next, so the bends stay closed."""
    n = len(pts) - 1
    for i in range(n):
        (z0, y0), (z1, y1) = pts[i], pts[i + 1]
        d = math.hypot(z1 - z0, y1 - y0)
        ez, ey = (z1 - z0) / d, (y1 - y0) / d
        a = 0.35 * thick if i else 0.0
        b = 0.35 * thick if i < n - 1 else 0.0
        m.beam((x, y0 - ey * a, z0 - ez * a), (x, y1 + ey * b, z1 + ez * b), width, thick, mat)
    return m


def _eye(m, x, z, y, radius, width=1.5, mat=IRON_D):
    """The rolled end of a cast bar: a disc in the plane at x."""
    m.tube("x", (y, z), x - width / 2.0, x + width / 2.0, radius, mat)
    return m


def _frame(m, x, z0, z1, top, crown=0.78, width=1.5):
    """A cast end frame in the upright plane at x: a rail from z0 to z1 with its top at `top`, under
    each end of it an S leg that splays out to a rolled toe, and between the legs a low arch whose
    crown is at `crown` of the height under the rail. Returns (y, z) of the crown, where the
    stretcher that ties two frames together goes."""
    h = top - 1.0
    m.box((x - width / 2.0, h, z0), (x + width / 2.0, top, z1), IRON, grain="z")
    bends = []
    for zt, s in ((z0 + 0.9, -1.0), (z1 - 0.9, 1.0)):
        _cast(m, x, [(zt, h + 0.3), (zt + 0.9 * s, 0.68 * h), (zt - 0.3 * s, 0.35 * h), (zt + 0.6 * s, 0.6)], width)
        _eye(m, x, zt + 0.9 * s, 0.7, 0.7, width)
        bends.append(zt - 0.3 * s)
    za, zb = bends
    mid, q = (za + zb) / 2.0, (zb - za) / 4.0
    foot, shoulder = 0.44 * h, (0.44 + 0.75 * (crown - 0.44)) * h
    _cast(m, x, [(za, foot), (za + q, shoulder), (mid, crown * h), (zb - q, shoulder), (zb, foot)], width, thick=0.8)
    return crown * h, mid


def _claws(m, count, reach, hub, turn=0.0, width=1.25):
    """The foot of whatever stands on one column: `count` cast claws that leave the hub at height
    `hub`, rise a little and sweep down to a rolled toe `reach` out. Three or five, never four."""
    for i in range(count):
        with m.turned(("y", turn + 360.0 * i / count)):
            _cast(m, 0.0, [(0.5, hub), (reach * 0.5, hub + 0.5), (reach * 0.85, hub * 0.45), (reach, 0.7)],
                  width=width)
            _eye(m, 0.0, reach + 0.3, 0.7, 0.7, width)
    m.tube("y", (0.0, 0.0), hub - 1.0, hub + 1.0, 1.4, IRON_D)
    return m


def _pull(m, x, y, z, w=2.0):
    """A brass drawer pull, w wide and one texel high, on a face that looks +z."""
    m.box((x - w / 2.0, y - 0.5, z), (x + w / 2.0, y + 0.5, z + 0.5), BRASS)
    return m


def _panelled(m, lo, hi, frame=2.0, panel=WOOD_L):
    """A level board from lo to hi as joiners make it: a frame of four darker boards, `frame` wide,
    round a lighter panel."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    m.box((x0, y0, z1 - frame), (x1, y1, z1), WOOD_D, grain="x")
    m.box((x0, y0, z0), (x1, y1, z0 + frame), WOOD_D, grain="x")
    for xa in (x0, x1 - frame):
        m.box((xa, y0, z0 + frame), (xa + frame, y1, z1 - frame), WOOD_D, grain="z")
    m.box((x0 + frame, y0, z0 + frame), (x1 - frame, y1, z1 - frame), panel, grain="x")
    return m


def _feet(m, x, z, height=2.0):
    """Four short cast feet under a case, their middles at (+-x, +-z)."""
    for sx in (-x, x):
        for sz in (-z, z):
            m.box((sx - 1.0, 0.0, sz - 1.0), (sx + 1.0, height, sz + 1.0), IRON_D)
    return m


# ---- the pieces -------------------------------------------------------------------------------------
def _bench():
    m = M.Model(PREFIX + "bench")
    ends = (-14.25, 14.25)
    for z0 in (-3.5, -0.5, 2.5):                                    # the seat: three slats
        m.box((-15.0, 6.0, z0), (15.0, 7.0, z0 + 2.0), WOOD, grain="x")
        for x in ends:
            K.rivet(m, (x, 7.0, z0 + 1.0), out="y", mat=BOLT)
    with m.turned(("x", -LEAN), about=(0.0, 6.0, -4.1)):            # the back leans with its uprights
        m.box((-15.0, 8.5, -3.6), (15.0, 10.5, -2.8), WOOD, grain="x")
        m.box((-15.0, 11.5, -3.6), (15.0, 14.5, -2.8), WOOD, grain="x")
        m.box((-2.0, 12.5, -2.8), (2.0, 13.5, -2.55), BRASS)        # a small brass plate
        for x in ends:
            m.box((x - 0.75, 5.5, -4.6), (x + 0.75, 14.4, -3.6), IRON, grain="y")
            _eye(m, x, -4.35, 14.9, 0.95)
            for y in (9.5, 13.0):
                K.rivet(m, (x, y, -2.8), out="z", mat=BOLT)
    for x in ends:
        y, z = _frame(m, x, -4.6, 5.5, 6.0)
        m.box((x - 0.75, 10.72, -5.1), (x + 0.75, 11.47, 4.9), IRON, grain="z")      # the arm rest
        _eye(m, x, 5.2, 10.7, 1.0)
        _cast(m, x, [(5.0, 9.8), (4.2, 8.2), (5.0, 6.0)])                             # and what holds it
    m.tube("x", (y, z), -13.5, 13.5, 0.5, IRON_D, sides=4)                           # the stretcher
    return m


def _writing_desk():
    m = M.Model(PREFIX + "writing_desk")
    _panelled(m, (-15.0, 11.0, -7.0), (15.0, 12.0, 7.0))
    # the gallery at the back: an upstand between two stationery drawers
    m.box((-9.0, 12.0, -7.0), (9.0, 14.0, -6.0), WOOD, grain="x")
    for x0 in (-15.0, 9.0):
        m.box((x0, 12.0, -7.0), (x0 + 6.0, 15.0, -3.0), WOOD, grain="x")
        m.box((x0 + 0.5, 12.5, -3.0), (x0 + 5.5, 14.5, -2.75), WOOD_L, grain="x")
        _pull(m, x0 + 3.0, 13.5, -2.75, 1.0)
    # the frieze and its three drawers
    m.box((-13.0, 8.0, -6.0), (13.0, 11.0, 6.0), WOOD, grain="x")
    for x0 in (-12.5, -4.0, 4.5):
        m.box((x0, 8.5, 6.0), (x0 + 8.0, 10.5, 6.25), WOOD_L, grain="x")
        _pull(m, x0 + 4.0, 9.5, 6.25)
    for x in (-12.25, 12.25):
        y, z = _frame(m, x, -6.0, 6.0, 8.0, crown=0.55)
    m.tube("x", (y, z), -11.5, 11.5, 0.5, IRON_D, sides=4)
    return m


def _drafting_table():
    m = M.Model(PREFIX + "drafting_table")
    py = 17.6                                                       # the height of the pivot
    with m.turned(("x", TILT), about=(0.0, py, 0.0)):               # the board, drawn flat and tilted
        m.box((-13.0, py, -8.0), (13.0, py + 1.0, 8.0), WOOD_L, grain="x")
        for x0 in (-15.0, 13.0):                                    # end cleats
            m.box((x0, py, -8.0), (x0 + 2.0, py + 1.0, 8.0), WOOD_D, grain="z")
        m.box((-15.0, py + 1.0, 7.0), (15.0, py + 2.0, 8.0), WOOD_D, grain="x")      # the pencil ledge
        m.box((-10.0, py + 1.0, -6.5), (8.0, py + 1.15, 4.5), PAPER, faces={"u": SHEET})
        for x in (-9.5, 7.5):
            for z in (-6.0, 4.0):
                m.box((x - 0.5, py + 1.15, z - 0.5), (x + 0.5, py + 1.4, z + 0.5), BOLT)   # drawing pins
        m.box((-13.5, py + 1.0, -1.0), (13.5, py + 1.5, 1.0), WOOD_D, grain="x")      # the straightedge
        for x0 in (-15.0, 13.5):
            m.box((x0, py + 1.0, -1.0), (x0 + 1.5, py + 1.6, 1.0), BRASS)
        for x in (-11.0, 11.0):                                     # bearers and the quadrant under it
            m.box((x - 0.75, py - 0.8, -6.5), (x + 0.75, py, 6.5), IRON, grain="z")
            m.ring("x", (x, py - 0.4, 0.0), 6.0, 1.0, 0.75, BRASS_D, sides=16, arc=(90.0, 270.0))
    m.tube("x", (py - 0.4, 0.0), -11.75, 11.75, 0.5, IRON_D, sides=4)                # the axle
    for x in (-11.0, 11.0):
        m.box((x - 0.75, 0.0, -7.0), (x + 0.75, 1.25, 7.0), IRON, grain="z")         # the foot
        for s in (-1.0, 1.0):
            _eye(m, x, 7.0 * s, 0.9, 0.9)
            _cast(m, x, [(6.0 * s, 1.2), (3.0 * s, 5.5), (0.6 * s, 9.5)])             # the stays
        m.tube("y", (x, 0.0), 1.25, py - 1.4, 0.9, IRON)                             # the column
        _eye(m, x, 0.0, py - 0.4, 1.3)
        side = 1.0 if x > 0 else -1.0                                                 # the clamp wheel
        m.tube("x", (py - 6.4, 0.0), x + 0.75 * side, x + 1.5 * side, 1.5, BRASS)
        m.tube("x", (py - 6.4, 0.0), x + 1.5 * side, x + 2.25 * side, 0.5, BRASS_D, sides=4)
    m.tube("x", (5.0, 0.0), -10.25, 10.25, 0.5, IRON_D, sides=4)                     # the stretcher
    return m


def _swivel_chair():
    m = M.Model(PREFIX + "swivel_chair")
    _claws(m, 5, 5.6, 3.2, turn=36.0)
    m.tube("y", (0.0, 0.0), 3.0, 6.0, 0.75, IRON)                   # the screw column
    m.tube("y", (0.0, 0.0), 4.4, 5.2, 1.6, BRASS_D)                 # and the wheel that sets the height
    m.box((-3.0, 5.5, -3.0), (3.0, 6.0, 3.0), IRON_D)
    m.box((-5.0, 6.0, -5.0), (5.0, 7.5, 5.0), WOOD, grain="x")      # the seat
    m.ring("y", (0.0, 12.75, 0.0), 4.5, 1.0, 2.5, WOOD, sides=16, arc=(-20.0, 200.0))   # the bow back
    for deg in (20.0, 55.0, 90.0, 125.0, 160.0):                    # its spindles
        c, s = math.cos(math.radians(deg)), -math.sin(math.radians(deg))
        m.rod((4.3 * c, 7.5, 4.3 * s), (4.5 * c, 11.6, 4.5 * s), 0.5, WOOD_D, sides=4)
    return m


def _stool():
    m = M.Model(PREFIX + "stool")
    m.tube("y", (0.0, 0.0), 11.0, 12.5, 3.5, WOOD)
    m.tube("y", (0.0, 0.0), 10.2, 11.0, 2.4, IRON_D)
    for i in range(3):
        a = math.radians(90.0 + 120.0 * i)
        c, s = math.cos(a), math.sin(a)
        m.rod((1.6 * c, 10.4, 1.6 * s), (3.4 * c, 0.0, 3.4 * s), 0.5, IRON, sides=4)
    m.ring("y", (0.0, 4.2, 0.0), 2.7, 0.75, 0.75, BRASS, sides=12)  # the foot ring
    return m


def _card_cabinet():
    m = M.Model(PREFIX + "card_cabinet")
    _feet(m, 6.0, 5.0, 2.5)
    m.box((-7.5, 2.5, -6.5), (7.5, 4.0, 6.5), WOOD_D, grain="x")
    m.box((-7.0, 4.0, -6.0), (7.0, 28.5, 6.0), WOOD, grain="y")
    m.box((-7.5, 28.5, -6.5), (7.5, 30.0, 6.5), WOOD_D, grain="x")
    for s in (-1.0, 1.0):                                           # the sides: a frame round a sunk panel
        xa, xb = sorted((7.0 * s, 7.25 * s))
        for z0 in (-6.0, 4.0):
            m.box((xa, 4.0, z0), (xb, 28.5, z0 + 2.0), WOOD_D, grain="y")
        for y0 in (4.0, 26.5):
            m.box((xa, y0, -4.0), (xb, y0 + 2.0, 4.0), WOOD_D, grain="z")
    front = Sprite("furn_card_drawer", ["cc"], {"c": LABEL}, back=WOOD_L)
    for row in range(6):
        for col in range(3):
            x0, y0 = -6.0 + 4.0 * col, 4.25 + 4.0 * row
            m.box((x0, y0, 6.0), (x0 + 4.0, y0 + 4.0, 6.5), WOOD_L, grain="x", faces={"s": front})
            _pull(m, x0 + 2.0, y0 + 1.5, 6.5)
    return m


def _instrument_cabinet():
    """A cupboard below, open shelves behind a glazed front above: the glass is not drawn, the
    frame and what stands on the shelves say it."""
    m = M.Model(PREFIX + "instrument_cabinet")
    _feet(m, 6.0, 4.0)
    m.box((-7.5, 2.0, -5.5), (7.5, 3.5, 5.5), WOOD_D, grain="x")
    m.box((-7.0, 3.5, -5.0), (7.0, 12.0, 5.0), WOOD, grain="y")     # the cupboard and its two doors
    for x0 in (-6.5, 0.5):
        m.box((x0, 4.0, 5.0), (x0 + 6.0, 11.5, 5.25), WOOD_L, grain="y")
    for x in (-1.5, 1.5):
        _pull(m, x, 8.0, 5.25, 1.0)
    m.box((-7.5, 12.0, -5.5), (7.5, 13.0, 5.5), WOOD_D, grain="x")
    m.box((-7.0, 13.0, -5.0), (7.0, 28.5, -4.0), WOOD_D, grain="y")  # the back of the shelves
    for x0 in (-7.0, 6.0):
        m.box((x0, 13.0, -4.0), (x0 + 1.0, 28.5, 5.0), WOOD, grain="y")
    for y in (18.0, 23.0):
        m.box((-6.0, y, -4.0), (6.0, y + 1.0, 4.0), WOOD, grain="x")
    m.box((-0.5, 13.0, 4.0), (0.5, 27.5, 5.0), WOOD_D, grain="y")    # where the two glazed doors meet
    m.box((-6.0, 27.5, 4.0), (6.0, 28.5, 5.0), WOOD_D, grain="x")
    _pull(m, 0.0, 20.5, 5.0, 1.0)
    m.box((-7.5, 28.5, -5.5), (7.5, 30.0, 5.5), WOOD_D, grain="x")
    # on the shelves: eyepieces in brass, a porcelain jar, a cased lens
    porcelain = P.mat("porcelain")
    for x, top in ((-4.5, 16.0), (-2.5, 15.0)):
        m.tube("y", (x, 0.0), 13.0, top, 0.75, BRASS)
    m.box((2.0, 13.0, -1.5), (5.0, 15.0, 1.5), WOOD_L, grain="x")
    for x, top in ((-4.0, 21.0), (2.5, 22.0)):
        m.tube("y", (x, 0.5), 19.0, top, 1.0, porcelain if x < 0 else BRASS_D)
    m.tube("x", (25.0, 0.0), -4.5, -0.5, 1.0, BRASS)
    m.tube("x", (24.75, 0.0), 1.5, 4.5, 0.75, BRASS_D)
    return m


def _library_ladder():
    """Wall mount: z = 0 is the bookcase front, the anchor is at floor level."""
    m = M.Model(PREFIX + "library_ladder")
    foot, head = (2.0, 10.5), (43.5, 1.9)                           # (y, z) of a stile's two ends
    ry, rz = RAIL_Y * 16.0, RAIL_OUT * 16.0
    for x in (-3.5, 3.5):
        m.beam((x, foot[0], foot[1]), (x, head[0], head[1]), 1.0, 2.0, WOOD)
        m.tube("x", (1.25, foot[1] + 0.4), x - 0.5, x + 0.5, 1.25, IRON_D)             # a caster
        m.tube("x", (ry + 1.4, rz), x - 0.5, x + 0.5, 0.9, BRASS)                      # a roller on the rail
        m.beam((x, head[0] - 1.0, head[1] + 0.3), (x, ry + 1.4, rz), 1.0, 1.0, BRASS_D)
    for i in range(8):                                              # level treads
        t = (i + 0.75) / 8.5
        y, z = foot[0] + (head[0] - foot[0]) * t, foot[1] + (head[1] - foot[1]) * t
        m.box((-3.5, y - 0.5, z - 1.5), (3.5, y + 0.5, z + 1.5), WOOD_L, grain="x")
    return m


def _ladder_rail():
    """Wall mount: one block of the rail, the anchor on the bookcase front at the rail's height."""
    m = M.Model(PREFIX + "ladder_rail")
    rz = RAIL_OUT * 16.0
    m.tube("x", (0.0, rz), -8.0, 8.0, 0.5, BRASS, sides=4)
    m.box((-0.5, -0.5, 0.0), (0.5, 0.5, rz), BRASS_D)
    m.box((-1.0, -1.0, 0.0), (1.0, 1.0, 0.3), BRASS_D)
    return m


def _coat_stand():
    m = M.Model(PREFIX + "coat_stand")
    _claws(m, 3, 5.0, 3.2)
    m.tube("y", (0.0, 0.0), 3.0, 27.0, 0.9, WOOD)
    m.tube("y", (0.0, 0.0), 13.0, 14.5, 1.4, WOOD_D)
    m.tube("y", (0.0, 0.0), 26.0, 27.5, 1.4, BRASS_D)
    for i in range(3):
        with m.turned(("y", 120.0 * i)):                            # the coat hooks
            m.hose([(0.0, 26.8, 1.0), (0.0, 26.2, 3.4), (0.0, 27.8, 4.6)], 0.5, BRASS, sides=4)
            m.box((-0.5, 27.6, 4.2), (0.5, 28.6, 5.2), BRASS)
        with m.turned(("y", 60.0 + 120.0 * i)):                     # the hat pegs between them
            m.hose([(0.0, 22.0, 0.7), (0.0, 21.4, 2.4), (0.0, 22.6, 3.2)], 0.5, BRASS_D, sides=4)
    m.ball((0.0, 28.9, 0.0), 1.3, BRASS, sides=8, layers=4)
    return m


def _trunk():
    m = M.Model(PREFIX + "trunk")
    for x in (-7.5, 7.5):                                            # runners
        m.box((x - 1.0, 0.0, -5.5), (x + 1.0, 1.0, 5.5), WOOD_D, grain="z")
    m.box((-11.0, 1.0, -5.5), (11.0, 7.5, 5.5), CANVAS, grain="x")
    m.box((-11.25, 7.5, -5.75), (11.25, 11.0, 5.75), CANVAS, grain="x")
    m.box((-11.3, 7.0, -5.8), (11.3, 8.0, 5.8), LEATHER, grain="x", skip="ud")     # the binding of the lid
    for x in (-6.5, 5.0):                                            # two straps and their buckles
        m.box((x, 0.9, -6.0), (x + 1.5, 11.25, 6.0), LEATHER, grain="y")
        m.box((x - 0.25, 4.0, 6.0), (x + 1.75, 5.5, 6.3), BRASS)
    for x in (-11.5, 10.0):
        for z in (-6.0, 4.5):
            m.box((x, 0.75, z), (x + 1.5, 2.25, z + 1.5), BRASS)
            m.box((x, 9.75, z), (x + 1.5, 11.25, z + 1.5), BRASS)
    m.box((-1.0, 6.0, 5.75), (1.0, 9.0, 6.3), BRASS)                 # the lock
    for x in (-11.75, 11.25):
        m.box((x, 4.5, -1.5), (x + 0.5, 5.5, 1.5), LEATHER)          # end handles
    return m


def _crate():
    m = M.Model(PREFIX + "crate")
    m.box((-6.0, 0.0, -6.0), (6.0, 11.0, 6.0), WOOD_L, grain="x")
    for x in (-6.5, 5.0):
        for z in (-6.5, 5.0):
            m.box((x, 0.0, z), (x + 1.5, 11.0, z + 1.5), WOOD_D, grain="y")
    for y0 in (0.0, 9.0):                                            # battens round it, nailed
        m.box((-5.0, y0, -6.5), (5.0, y0 + 2.0, 6.5), WOOD, grain="x", skip="ud")
        m.box((-6.5, y0, -5.0), (6.5, y0 + 2.0, 5.0), WOOD, grain="z", skip="ud")
        for a in (-4.0, 4.0):
            for s in (-1.0, 1.0):
                K.rivet(m, (a, y0 + 1.0, 6.5 * s), out="z" if s > 0 else "-z")
                K.rivet(m, (6.5 * s, y0 + 1.0, a), out="x" if s > 0 else "-x")
    for z0 in (-6.5, -2.0, 2.5):                                     # the lid: three boards
        m.box((-6.5, 11.0, z0), (6.5, 12.0, z0 + 4.0), WOOD, grain="x")
    return m


def _display_case():
    m = M.Model(PREFIX + "display_case")
    _feet(m, 6.0, 6.0)
    m.box((-7.5, 2.0, -7.5), (7.5, 3.5, 7.5), WOOD_D, grain="x")
    m.box((-7.0, 3.5, -7.0), (7.0, 9.5, 7.0), WOOD_L, grain="x")
    for s in (-1.0, 1.0):                                            # corner stiles: the base is panelled
        for t in (-1.0, 1.0):
            xa, za = min(5.25 * s, 7.25 * s), min(5.25 * t, 7.25 * t)
            m.box((xa, 3.5, za), (xa + 2.0, 9.5, za + 2.0), WOOD_D, grain="y")
    m.box((-7.5, 9.5, -7.5), (7.5, 10.5, 7.5), WOOD_D, grain="x")
    m.box((-6.5, 10.5, -6.5), (6.5, 10.75, 6.5), CANVAS)             # the lining the exhibit lies on
    for x in (-6.75, 6.75):                                          # the glazed case: brass edges only
        for z in (-6.75, 6.75):
            m.box((x - 0.5, 10.5, z - 0.5), (x + 0.5, 21.0, z + 0.5), BRASS, grain="y")
    for z in (-6.75, 6.75):
        m.box((-6.25, 20.0, z - 0.5), (6.25, 21.0, z + 0.5), BRASS, grain="x")
    for x in (-6.75, 6.75):
        m.box((x - 0.5, 20.0, -6.25), (x + 0.5, 21.0, 6.25), BRASS, grain="z")
    return m


SPEC = {
    "bench": dict(build=_bench, mount="floor"),
    "writing_desk": dict(build=_writing_desk, mount="floor"),
    "drafting_table": dict(build=_drafting_table, mount="floor"),
    "swivel_chair": dict(build=_swivel_chair, mount="floor"),
    "stool": dict(build=_stool, mount="floor"),
    "card_cabinet": dict(build=_card_cabinet, mount="floor"),
    "instrument_cabinet": dict(build=_instrument_cabinet, mount="floor"),
    "library_ladder": dict(build=_library_ladder, mount="wall"),
    "ladder_rail": dict(build=_ladder_rail, mount="wall"),
    "coat_stand": dict(build=_coat_stand, mount="floor"),
    "trunk": dict(build=_trunk, mount="floor"),
    "crate": dict(build=_crate, mount="floor"),
    "display_case": dict(build=_display_case, mount="floor"),
}
SCALE = {PREFIX + name: 1.0 for name in SPEC}
# how high above its foot a piece carries what is put on it (blocks)
TOP = {"writing_desk": 12.0 / 16.0, "card_cabinet": 30.0 / 16.0, "trunk": 11.25 / 16.0, "crate": 12.0 / 16.0,
       "display_case": 10.75 / 16.0, "bench": 7.0 / 16.0, "stool": 12.5 / 16.0, "swivel_chair": 7.5 / 16.0}


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: spec["build"]() for name, spec in SPEC.items()}


def models():
    return dict(_models())


# ---- placing -------------------------------------------------------------------------------------------
def place(canvas, kind, pos, facing="south", origin=(0, 0, 0), yaw=None, **opts):
    """Put one piece of furniture into the scene; returns the number of display entities (1).

    kind     a key of SPEC.
    pos      scene coordinates: the middle of the piece's foot on the floor. For "library_ladder"
             the point at floor level on the front of the bookcase it leans on, for "ladder_rail"
             the point on that front at the rail's height (RAIL_Y above the floor).
    facing   the way the piece's front looks: where a sitter on the bench or the chair looks, the
             side of the desk and the drafting table one sits at, the drawer fronts of the cabinet;
             for the ladder and its rail the way the bookcase front looks. yaw (degrees) turns a
             standing piece freely instead.
    opts     go to artkit.models.display (brightness, view).
    A display entity stops nobody: where a piece must not be walked through, the room sees to it.
    """
    spec = SPEC[kind]
    yaw = K.FACING[facing] if yaw is None else yaw
    return K.put(canvas, _models()[PREFIX + kind], pos, mount=spec["mount"], yaw=yaw, origin=origin, **opts)


def rail(canvas, pos, blocks, facing="south", origin=(0, 0, 0)):
    """A run of ladder rail along a bookcase front: `blocks` pieces side by side, the first centred
    on pos (a point on the front at floor level; the rail goes RAIL_Y above it), the others to its
    right as one looks at the front. Returns the number of display entities."""
    yaw = K.FACING[facing]
    n = 0
    for i in range(blocks):
        dx, _, dz = K.turn(yaw, (float(i), 0.0, 0.0))
        n += place(canvas, "ladder_rail", (pos[0] + dx, pos[1] + RAIL_Y, pos[2] + dz), facing=facing, origin=origin)
    return n


def build(canvas, origin=(0, 0, 0)):
    """Furniture is placed by the rooms and the site, each piece where it is used: nothing here."""
    return 0
