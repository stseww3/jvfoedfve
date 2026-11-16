"""props/furniture -- the furniture of the observatory (plan ART-PLAN 7.3, part A6 section 2.6,
card plan/packages/props/furniture.md).

One family, one motif: dark wood carried on cast iron, brass where a hand goes. The iron is always
the same casting -- a flat bar bent in an S that ends in a rolled eye -- whether it is the end frame
of a bench, of a desk, or one claw of a column foot. Brass is small and bright where a hand goes
(pulls, a rail, a hook); the edges of a glass case are the dull brass, so that what lies in the case
is looked at and not its frame. Glass is not drawn; its reflection is (_kit.pane).

    bench            two blocks wide: slats on two cast end frames with arm rests (the terraces, the
                     cable-car station, the star hall)
    writing_desk     two blocks wide: a panelled top, three drawers in the frieze, a low gallery
    display_table    two blocks wide, one high: a flat glazed case on the desk's frames (the star hall)
    drafting_table   two blocks wide: a board tilted on a cast A-frame and held by a brass quadrant,
                     a sheet pinned to it
    swivel_chair     a round wooden seat, a bow of arms that rises to a crest at the back, on a
                     screw column and five claws
    stool            a tall screw stool: a round seat on the chair's column and three claws
    card_cabinet     two blocks tall: eighteen card drawers, each with its label and brass pull
    instrument_cabinet  two blocks tall and as deep as the card cabinet, so that they stand in one
                     row: a cupboard under glazed shelves of eyepieces (the dome room)
    library_ladder   three blocks tall, leans on a bookcase; its rollers ride on ladder_rail
    ladder_rail      one block of that brass rail (rail() lays a run of it)
    coat_stand       two blocks tall: a turned post on three claws, a crown of five brass hooks
    trunk            a travelling trunk in brown hide with darker straps and brass corners
    crate            a packing case of raw deal: boards with gaps between them, nailed to a cleat at
                     every corner, a line of stencilled marks
    crate_small      the same, small enough to stand on the trunk's lid
    display_case     one block square: a glazed brass case on a panelled base

Every piece is one display entity at scale 1 (16 texels to the block), and whatever is square to the
piece is drawn on that grid. Indoors nothing is placed from here: every room places what it needs
with place(). Out of doors the benches and the station's luggage are placed by site(), which
build() calls once the switch DRESS is on.

No piece shows a cross from any side. Feet and hooks come in threes and fives, never four at right
angles; nothing has a bar across a post (the coat stand's hooks rise like a crown, the stool has no
foot ring); a dark band never crosses another (the trunk's straps cross only the seam of its lid).

The look is judged in the test scene build/scenes/obs_props_furniture.
"""
import functools
import importlib
import importlib.util
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from . import _kit as K

PREFIX = "prop_furn_"

WOOD = P.mat("dark_wood")                         # slats, case sides
WOOD_L = P.mat("dark_wood", base=3)               # the lighter board: panels, drawer fronts
WOOD_D = P.mat("dark_wood", base=1)               # frames, plinths, cornices
DEAL = P.mat("dark_wood", base=4)                 # raw boards, the lightest wood there is: a packing case
LEATHER = P.mat("dark_wood", kind="plain", noise=0.10, base=1)
IRON = P.mat("iron", bevel="along")               # a cast bar: light and dark edge along it only
IRON_D = K.IRON_D
BRASS, BRASS_D = K.BRASS, K.BRASS_D
PIN = K.flat("brass", 4)
BOLT = K.flat("iron", 4)                          # a bolt head in wood: a cool dot, no lighter than the wood
# A travelling trunk is covered in brown hide: the brown of the lightest wood, laid on flat, with no
# grain and a worn edge, so that it is leather beside the boards of a packing case. What else was
# tried: the woven cream the card named (cream_cloth) came out the whitest thing on the stage after
# the lamps, and mottled; the darkest plain cream still read as a box painted white; old copper as a
# pink box under a lamp on the ramp's middle step and as a lilac one under the sky a step lower;
# enamel blue with tan straps as the loudest thing in the room.
HIDE = P.mat("dark_wood", kind="plain", noise=0.06, bevel=1, base=4)
SEAM = K.flat("dark_wood", 2)                     # the edge of the trunk's lid: two steps under its hide
# The bed of a display case is blue velvet: one flat tone of the night glass, the house's blue under
# its brass. Brass and paper laid on it are both far lighter than the bed (the darkest cream was as
# light as a wall of stone, and a sheet of paper on it was lost); not a speck on it that could be
# taken for an exhibit.
LINING = K.flat("night_glass", 2)
PAPER = K.flat("cream", 2)                        # a clean sheet: no speckle to be taken for pencil
PENCIL, INK, LABEL = P.RAMPS["cream"][0], P.RAMPS["iron"][2], P.RAMPS["cream"][1]

LEAN = 10.0                     # degrees a bench's back leans
TILT = 40.0                     # degrees the drafting board is tilted
RAIL_Y = 44.5 / 16.0            # the ladder rail's height above the floor the ladder stands on
RAIL_OUT = 1.0 / 16.0           # and how far its centre is off the bookcase front
# The bookcase a ladder leans on is the room's own (interiors/chartroom has one). What it keeps to,
# so that ladder, rail and cabinets fit it: this deep off the wall, the top of its plinth 4 texels
# up like the cabinets', a rail board from 43 to 46 for the rail to be fixed to, a cornice above.
SHELF_DEPTH = 6.0 / 16.0

# What is pinned to the drafting board: a chart being drawn, the seven stars of the Plough inked and
# joined in pencil, three fainter stars about them; no writing. A pencil circle with five dots in it
# read as the five of a die. The last row lies under the straightedge.
SHEET = Sprite("furn_draft_sheet", [
    "..................",
    "...p..............",
    "..............pi..",
    "............pp.p..",
    "......pippip...p..",
    "....ip....p....p..",
    "..pp.......p.ppi..",
    ".i.........ip.....",
    "........p.........",
    "................p.",
    "..................",
], {"p": PENCIL, "i": INK}, back=PAPER)


# ---- the casting ---------------------------------------------------------------------------------
def _cast(m, x, pts, width=2.0, thick=1.0, mat=IRON):
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


def _eye(m, x, z, y, radius, width=2.0, mat=IRON_D):
    """The rolled end of a cast bar: a disc in the plane at x."""
    m.tube("x", (y, z), x - width / 2.0, x + width / 2.0, radius, mat)
    return m


def _frame(m, x, z0, z1, top, crown=0.78, width=2.0):
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


def _claws(m, count, reach, hub, turn=0.0, width=1.5):
    """The foot of whatever stands on one column: `count` cast claws that leave the hub at height
    `hub`, rise a little and sweep down to a rolled toe `reach` out. Three or five, never four."""
    for i in range(count):
        with m.turned(("y", turn + 360.0 * i / count)):
            _cast(m, 0.0, [(0.5, hub), (reach * 0.5, hub + 0.5), (reach * 0.85, hub * 0.45), (reach, 0.7)],
                  width=width)
            _eye(m, 0.0, reach + 0.3, 0.7, 0.7, width)
    m.tube("y", (0.0, 0.0), hub - 1.0, hub + 1.0, 1.4, IRON_D)
    return m


# ---- joinery ---------------------------------------------------------------------------------------
def _boarded(m, lo, hi, mat, skip="", **kw):
    """A box of boards that run level round all four sides. One box has one grain and its two ends
    would be painted as end grain, so the ends come from a second box with the grain turned."""
    m.box(lo, hi, mat, grain="x", skip="ew" + skip, **kw)
    m.box(lo, hi, mat, grain="z", skip="nsud" + skip)
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


def _pull(m, x, y, z, w=2.0):
    """A brass drawer pull, w wide and one texel high, on a face that looks +z."""
    m.box((x - w / 2.0, y - 0.5, z), (x + w / 2.0, y + 0.5, z + 0.5), BRASS)
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
    ends = (-14.0, 14.0)
    for z0 in (-4.0, -1.0, 2.0):                                    # the seat: three slats
        m.box((-15.0, 6.0, z0), (15.0, 7.0, z0 + 2.0), WOOD, grain="x")
        for x in (-13.5, 13.5):
            K.rivet(m, (x, 7.0, z0 + 1.5), out="y", mat=BOLT, proud=0.25)
    with m.turned(("x", -LEAN), about=(0.0, 6.0, -4.0)):            # the back leans with its uprights
        m.box((-15.0, 9.0, -4.0), (15.0, 11.0, -3.0), WOOD, grain="x")
        m.box((-15.0, 12.0, -4.0), (15.0, 15.0, -3.0), WOOD, grain="x")
        m.box((-2.0, 13.0, -3.0), (2.0, 14.0, -2.75), BRASS)        # a small brass plate
        for x in ends:
            m.box((x - 1.0, 6.0, -5.0), (x + 1.0, 15.0, -4.0), IRON, grain="y")
            _eye(m, x, -4.5, 15.5, 1.0)
        for x in (-13.5, 13.5):
            for y in (10.5, 13.5):
                K.rivet(m, (x, y, -3.0), out="z", mat=BOLT, proud=0.25)
    for x in ends:
        y, z = _frame(m, x, -5.0, 5.0, 6.0)
        m.box((x - 1.0, 10.0, -5.5), (x + 1.0, 11.0, 5.0), IRON, grain="z")          # the arm rest
        _eye(m, x, 5.2, 10.4, 1.0)
        _cast(m, x, [(5.0, 9.8), (4.2, 8.2), (4.8, 6.0)])                             # and what holds it
    m.tube("x", (y, z), -13.0, 13.0, 0.5, IRON_D, sides=4)                           # the stretcher
    return m


def _writing_desk():
    m = M.Model(PREFIX + "writing_desk")
    for x in (-12.0, 12.0):
        y, z = _frame(m, x, -6.0, 6.0, 8.0, crown=0.55)
    m.tube("x", (y, z), -11.0, 11.0, 0.5, IRON_D, sides=4)
    _boarded(m, (-13.0, 8.0, -6.0), (13.0, 11.0, 6.0), WOOD)        # the frieze and its three drawers
    for x0 in (-13.0, -4.0, 5.0):
        m.box((x0, 8.0, 6.0), (x0 + 8.0, 11.0, 6.25), WOOD_L, grain="x")
        _pull(m, x0 + 4.0, 9.5, 6.25)
    _panelled(m, (-15.0, 11.0, -7.0), (15.0, 12.0, 7.0))
    # the gallery at the back: an upstand between two stationery drawers
    m.box((-9.0, 12.0, -7.0), (9.0, 14.0, -6.0), WOOD, grain="x")
    for x0 in (-15.0, 9.0):
        _boarded(m, (x0, 12.0, -7.0), (x0 + 6.0, 15.0, -3.0), WOOD, faces={"s": WOOD_L})
        _pull(m, x0 + 3.0, 13.5, -3.0)
    return m


def _display_table():
    """As wide as the desk and on the same frames, no higher than one block: a flat case of three
    panes, looked into from above. What lies in it lies on the lining, TOP["display_table"] up, and
    is no higher than three texels."""
    m = M.Model(PREFIX + "display_table")
    for x in (-12.0, 12.0):
        y, z = _frame(m, x, -6.0, 6.0, 8.0, crown=0.55)
    m.tube("x", (y, z), -11.0, 11.0, 0.5, IRON_D, sides=4)
    _boarded(m, (-14.0, 8.0, -6.0), (14.0, 10.0, 6.0), WOOD)        # the apron
    _boarded(m, (-15.0, 10.0, -7.0), (15.0, 11.0, 7.0), WOOD_D)     # the board the case stands on
    m.box((-14.0, 11.0, -6.0), (14.0, 11.25, 6.0), LINING)          # the lining
    bars = (-15.0, -5.0, 4.0, 14.0)                                 # the same thirds as the desk's drawers
    for z0 in (-7.0, 6.0):
        for x0 in bars:
            m.box((x0, 11.0, z0), (x0 + 1.0, 15.0, z0 + 1.0), BRASS_D, grain="y")
        m.box((-15.0, 15.0, z0), (15.0, 16.0, z0 + 1.0), BRASS_D, grain="x")
    for x0 in bars:
        m.box((x0, 15.0, -6.0), (x0 + 1.0, 16.0, 6.0), BRASS_D, grain="z")
    # a reflection in two of the three panes, and not the same one twice
    for (x0, x1), sheen in zip(((-14.0, -5.0), (-4.0, 4.0), (5.0, 14.0)), (True, False, 2)):
        K.pane(m, (x0, 15.5, -6.0), (x1, 15.75, 6.0), "u", sheen=sheen)
    return m


def _drafting_table():
    m = M.Model(PREFIX + "drafting_table")
    ay = 18.0                                                       # the height of the axle the board tips on
    by = ay + 0.5                                                   # the underside of the board, drawn level
    with m.turned(("x", TILT), about=(0.0, ay, 0.0)):
        m.box((-13.0, by, -8.0), (13.0, by + 1.0, 8.0), WOOD_L, grain="x")
        for x0 in (-15.0, 13.0):                                    # end cleats
            m.box((x0, by, -8.0), (x0 + 2.0, by + 1.0, 8.0), WOOD_D, grain="z")
        m.box((-15.0, by + 1.0, 7.0), (15.0, by + 2.0, 8.0), WOOD_D, grain="x")      # the pencil ledge
        m.box((-10.0, by + 1.0, -6.0), (8.0, by + 1.15, 5.0), PAPER, faces={"u": SHEET})
        for x0 in (-10.0, 7.0):                                     # drawing pins in its top corners
            m.box((x0, by + 1.15, -6.0), (x0 + 1.0, by + 1.4, -5.0), PIN)
        m.box((-13.0, by + 1.0, 4.0), (13.0, by + 1.5, 6.0), WOOD_D, grain="x")      # the straightedge, slid down
        for x0 in (-15.0, 13.0):
            m.box((x0, by + 1.0, 4.0), (x0 + 2.0, by + 1.6, 6.0), BRASS)
        for x in (-11.0, 11.0):                                     # bearers, and the quadrant under each
            m.box((x - 1.0, ay - 0.5, -7.0), (x + 1.0, by, 7.0), IRON, grain="z")
            m.ring("x", (x, ay, 0.0), 6.0, 1.0, 1.0, BRASS_D, sides=16, arc=(90.0, 270.0))
    m.tube("x", (ay, 0.0), -12.0, 12.0, 0.5, IRON_D, sides=4)                         # the axle
    for x in (-11.0, 11.0):
        m.box((x - 1.0, 0.0, -7.0), (x + 1.0, 1.0, 7.0), IRON, grain="z")           # the foot
        for s in (-1.0, 1.0):
            _eye(m, x, 7.0 * s, 0.9, 0.9)
            _cast(m, x, [(6.0 * s, 1.0), (3.0 * s, 5.5), (0.6 * s, 10.0)])            # the stays
        m.tube("y", (x, 0.0), 1.0, ay - 1.3, 0.9, IRON)                              # the column
        _eye(m, x, 0.0, ay, 1.3)                                                     # its bearing
        side = 1.0 if x > 0 else -1.0                                                # the wheel that clamps the quadrant
        m.tube("x", (ay - 6.0, 0.0), x + 1.0 * side, x + 2.0 * side, 1.5, BRASS)
    m.tube("x", (5.0, 0.0), -10.0, 10.0, 0.5, IRON_D, sides=4)                       # the stretcher
    return m


def _swivel_chair():
    """A revolving desk chair. The seat is round and turned; the arms are one thin bow that rises to
    a crest behind the sitter's back. A square seat under a bow two texels high all round read from
    behind as a hooped tub: it is the crest that makes the outline a chair's."""
    m = M.Model(PREFIX + "swivel_chair")
    _claws(m, 5, 5.6, 3.2, turn=36.0)
    m.tube("y", (0.0, 0.0), 4.2, 5.0, 1.6, BRASS_D)                 # the wheel that sets the height
    m.tube("y", (0.0, 0.0), 5.0, 6.0, 3.0, IRON_D)                  # the plate the seat turns on
    m.tube("y", (0.0, 0.0), 6.0, 7.0, 5.0, WOOD)                    # the seat
    m.ring("y", (0.0, 11.5, 0.0), 4.5, 1.0, 1.0, WOOD_D, sides=16, arc=(-20.0, 200.0))   # the bow of the arms
    m.ring("y", (0.0, 13.0, 0.0), 4.5, 1.0, 2.0, WOOD, sides=16, arc=(45.0, 135.0))      # the crest
    for deg in (20.0, 55.0, 90.0, 125.0, 160.0):                    # the spindles
        c, s = math.cos(math.radians(deg)), -math.sin(math.radians(deg))
        m.rod((4.3 * c, 7.0, 4.3 * s), (4.5 * c, 11.0, 4.5 * s), 0.5, WOOD_D, sides=4)
    return m


def _stool():
    """A screw stool: the chair's column, taller, on three claws."""
    m = M.Model(PREFIX + "stool")
    _claws(m, 3, 4.6, 3.2, turn=60.0)
    m.tube("y", (0.0, 0.0), 4.0, 8.0, 0.75, IRON)                   # the screw
    m.tube("y", (0.0, 0.0), 8.0, 9.0, 1.6, BRASS_D)                 # the wheel that sets the height
    m.tube("y", (0.0, 0.0), 9.0, 10.0, 2.4, IRON_D)
    m.tube("y", (0.0, 0.0), 10.0, 12.0, 3.5, WOOD)                  # the seat
    return m


def _card_cabinet():
    m = M.Model(PREFIX + "card_cabinet")
    _feet(m, 6.0, 5.0)
    _boarded(m, (-7.5, 2.0, -6.5), (7.5, 4.0, 6.5), WOOD_D)
    m.box((-7.0, 4.0, -6.0), (7.0, 28.0, 6.0), WOOD, grain="y")
    _boarded(m, (-7.5, 28.0, -6.5), (7.5, 30.0, 6.5), WOOD_D)
    for s in (-1.0, 1.0):                                           # the sides: a frame round a sunk panel
        xa, xb = sorted((7.0 * s, 7.25 * s))
        for z0 in (-6.0, 4.0):
            m.box((xa, 4.0, z0), (xb, 28.0, z0 + 2.0), WOOD_D, grain="y")
        for y0 in (4.0, 26.0):
            m.box((xa, y0, -4.0), (xb, y0 + 2.0, 4.0), WOOD_D, grain="z")
    front = Sprite("furn_card_drawer", ["cc"], {"c": LABEL}, back=WOOD_L)
    for row in range(6):                                            # each drawer: its label over its pull
        for col in range(3):
            x0, y0 = -6.0 + 4.0 * col, 4.0 + 4.0 * row
            m.box((x0, y0, 6.0), (x0 + 4.0, y0 + 4.0, 6.5), WOOD_L, grain="x", faces={"s": front})
            _pull(m, x0 + 2.0, y0 + 1.5, 6.5)
    return m


def _instrument_cabinet():
    """A cupboard below, shelves behind two glazed doors above. Plinth, cornice and depth are the
    card cabinet's, so the two kinds stand in one row."""
    m = M.Model(PREFIX + "instrument_cabinet")
    _feet(m, 6.0, 5.0)
    _boarded(m, (-7.5, 2.0, -6.5), (7.5, 4.0, 6.5), WOOD_D)
    m.box((-7.0, 4.0, -6.0), (7.0, 12.0, 6.0), WOOD, grain="y")     # the cupboard and its two doors
    for x0 in (-6.0, 1.0):
        m.box((x0, 5.0, 6.0), (x0 + 5.0, 11.0, 6.25), WOOD_L, grain="y")
    for x in (-1.5, 1.5):
        _pull(m, x, 8.5, 6.25, 1.0)
    _boarded(m, (-7.5, 12.0, -6.5), (7.5, 13.0, 6.5), WOOD_D)
    m.box((-7.0, 13.0, -6.0), (7.0, 28.0, -5.0), WOOD_D, grain="y")  # the back of the shelves
    for x0 in (-7.0, 6.0):
        m.box((x0, 13.0, -5.0), (x0 + 1.0, 28.0, 6.0), WOOD, grain="y")
    for y in (18.0, 23.0):
        m.box((-6.0, y, -5.0), (6.0, y + 1.0, 5.0), WOOD, grain="x")
    m.box((-1.0, 13.0, 5.0), (1.0, 27.0, 6.0), WOOD_D, grain="y")    # where the two glazed doors meet
    m.box((-6.0, 27.0, 5.0), (6.0, 28.0, 6.0), WOOD_D, grain="x")
    _pull(m, 0.0, 20.5, 6.0)
    for x0, sheen in ((-6.0, 3), (1.0, True)):                       # the two doors' glass: not one stamp twice
        K.pane(m, (x0, 13.0, 5.5), (x0 + 5.0, 27.0, 5.75), "s", sheen=sheen)
    _boarded(m, (-7.5, 28.0, -6.5), (7.5, 30.0, 6.5), WOOD_D)
    # on the shelves: eyepieces in brass, a cased lens, a porcelain jar
    for x, top in ((-4.5, 16.0), (-2.5, 15.0)):
        m.tube("y", (x, 0.0), 13.0, top, 0.75, BRASS)
    m.box((2.0, 13.0, -1.5), (5.0, 15.0, 1.5), WOOD_L, grain="x")
    m.tube("y", (-4.0, 0.5), 19.0, 21.0, 1.0, P.mat("porcelain"))
    m.tube("y", (3.5, 0.5), 19.0, 22.0, 1.0, BRASS_D)
    m.tube("x", (25.0, 0.0), -5.0, -2.0, 1.0, BRASS)
    m.tube("x", (24.75, 0.0), 2.0, 5.0, 0.75, BRASS_D)
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
    """A turned post on three claws. Its five hooks are the family's casting in brass: they rise out
    of a collar like a crown, so that from no side is there a bar across the post."""
    m = M.Model(PREFIX + "coat_stand")
    _claws(m, 3, 5.0, 3.2)
    m.tube("y", (0.0, 0.0), 3.0, 25.0, 0.9, WOOD)
    m.tube("y", (0.0, 0.0), 13.0, 14.5, 1.4, WOOD_D)                # a turned swell
    m.tube("y", (0.0, 0.0), 24.0, 26.0, 1.4, BRASS_D)               # the collar the hooks spring from
    for i in range(5):
        with m.turned(("y", 36.0 + 72.0 * i)):
            _cast(m, 0.0, [(0.9, 25.0), (2.6, 26.4), (3.3, 28.4), (4.4, 29.3)], width=1.0, mat=BRASS)
            _eye(m, 0.0, 4.9, 29.1, 0.7, 1.0, BRASS_D)
    m.ball((0.0, 26.9, 0.0), 1.1, WOOD_D, sides=8, layers=4)        # the knob that ends the post
    return m


def _trunk():
    m = M.Model(PREFIX + "trunk")
    straps = (-7.0, 5.0)
    for x0 in straps:                                                # runners
        m.box((x0, 0.0, -5.0), (x0 + 2.0, 1.0, 5.0), WOOD_D, grain="z")
    m.box((-11.0, 1.0, -5.0), (11.0, 11.0, 5.0), HIDE, grain="x")
    # the edge of the lid: a darker line and no more, so the straps cross nothing dark
    m.box((-11.25, 7.0, -5.25), (11.25, 8.0, 5.25), SEAM, grain="x", skip="ud")
    for x0 in straps:                                                # two straps and their buckles
        m.box((x0, 1.0, -5.5), (x0 + 2.0, 11.5, 5.5), LEATHER, grain="y")
        m.box((x0, 4.0, 5.5), (x0 + 2.0, 6.0, 5.75), BRASS)
    for x0 in (-11.25, 9.0):                                         # the corners: dull brass, eight of them
        for z0 in (-5.25, 3.0):
            for y0 in (0.75, 9.0):
                m.box((x0, y0, z0), (x0 + 2.25, y0 + 2.25, z0 + 2.25), BRASS_D)
    m.box((-1.0, 6.0, 5.0), (1.0, 9.0, 5.5), BRASS)                  # the lock: the one bright piece
    for x0 in (-11.5, 11.0):
        m.box((x0, 5.0, -2.0), (x0 + 0.5, 6.0, 2.0), LEATHER)        # end handles
    return m


CASE_DARK = K.flat("dark_wood", 0)              # what shows between two boards of a packing case
# a nail head in raw wood: iron came out a blue stud, and the darkest wood as dark as the gaps, so
# that two nails over a gap were two eyes over a mouth
NAIL = P.RAMPS["dark_wood"][1]
STENCIL = P.RAMPS["dark_wood"][2]               # marks stencilled on a board: faded paint, not slots
BOARD = 3.0                                     # texels a board of a packing case is high; one texel between two


def _cleat(boards, right):
    """The outer face of a packing case's corner cleat, two texels wide: a nail where each board
    crosses it, in the column next to the boards (the right one if `right`)."""
    rows = []
    for _ in range(boards):
        rows += ["..", ".n" if right else "n.", "..", ".."]
    return Sprite(f"furn_cleat_{boards}{'r' if right else 'l'}", rows[:-1], {"n": NAIL}, back=WOOD_L)


def _packing_case(name, w, d, boards, marks):
    """A packing case w by d texels: `boards` rings of raw boards with a dark gap between them, an
    upright cleat at every corner that the boards are nailed to and that stands a texel proud of
    them, a boarded lid. A frame round a panel on every side read as a chest of dark wood; boards,
    gaps and cleats are what a crate is. marks = (board, row): what is stencilled on the front, as
    one row of texels in the middle of that board (counted from the floor): a line of lettering too
    small to read, dots more than dashes (a row of dashes is a row of slits). No pasted label (a pale ticket with writing on it read as a socket, and three
    cases side by side showed it three times) and no arrow (three by five texels of arrow is a
    cross)."""
    m = M.Model(PREFIX + name)
    hx, hz = w / 2.0, d / 2.0
    top = (BOARD + 1.0) * boards - 1.0
    m.box((-hx + 1.25, 0.0, -hz + 1.25), (hx - 1.25, top, hz - 1.25), CASE_DARK, skip="u")
    for i in range(boards):
        y0 = (BOARD + 1.0) * i
        faces = {}
        if i == marks[0]:
            faces["s"] = Sprite(f"furn_stencil_{name}", ["", marks[1], ""], {"i": STENCIL}, back=DEAL)
        _boarded(m, (-hx + 1.0, y0, -hz + 1.0), (hx - 1.0, y0 + BOARD, hz - 1.0), DEAL, skip="ud", faces=faces)
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            (xa, xb), (za, zb) = sorted((sx * hx, sx * (hx - 2.0))), sorted((sz * hz, sz * (hz - 2.0)))
            # the nails are in the column towards the boards, whichever way the face is looked at
            faces = {"s" if sz > 0 else "n": _cleat(boards, right=(sx < 0) == (sz > 0)),
                     "e" if sx > 0 else "w": _cleat(boards, right=(sz > 0) == (sx > 0))}
            m.box((xa, 0.0, za), (xb, top, zb), WOOD_L, grain="y", faces=faces)
    for i in range(int(round(d / 4.0))):                             # the lid: boards four texels wide
        m.box((-hx, top, -hz + 4.0 * i), (hx, top + 1.0, -hz + 4.0 * i + 4.0), DEAL, grain="x")
    return m


def _crate():
    return _packing_case("crate", 12.0, 12.0, 3, (1, ".i.ii.i."))


def _crate_small():
    """Small enough for the lid of the trunk, which is ten texels deep."""
    return _packing_case("crate_small", 10.0, 8.0, 2, (0, ".ii.i."))


def _display_case():
    m = M.Model(PREFIX + "display_case")
    _feet(m, 6.0, 6.0)
    _boarded(m, (-7.5, 2.0, -7.5), (7.5, 4.0, 7.5), WOOD_D)
    m.box((-5.0, 4.0, -6.5), (5.0, 10.0, 6.5), WOOD_L, grain="x", skip="ewud")       # the base: sunk panels
    m.box((-6.5, 4.0, -5.0), (6.5, 10.0, 5.0), WOOD_L, grain="z", skip="nsud")
    for x0 in (-7.0, 5.0):                                           # between corner posts
        for z0 in (-7.0, 5.0):
            m.box((x0, 4.0, z0), (x0 + 2.0, 10.0, z0 + 2.0), WOOD_D, grain="y", skip="ud")
    _boarded(m, (-7.5, 10.0, -7.5), (7.5, 11.0, 7.5), WOOD_D)
    m.box((-6.0, 11.0, -6.0), (6.0, 11.25, 6.0), LINING)             # the lining the exhibit lies on
    for x0 in (-7.0, 6.0):                                           # the glass case: its edges of dull brass
        for z0 in (-7.0, 6.0):
            m.box((x0, 11.0, z0), (x0 + 1.0, 21.0, z0 + 1.0), BRASS_D, grain="y")
        m.box((x0, 20.0, -6.0), (x0 + 1.0, 21.0, 6.0), BRASS_D, grain="z")
    for z0 in (-7.0, 6.0):
        m.box((-6.0, 20.0, z0), (6.0, 21.0, z0 + 1.0), BRASS_D, grain="x")
    K.pane(m, (-6.0, 11.0, 6.5), (6.0, 20.0, 6.75), "s")
    K.pane(m, (-6.0, 11.0, -6.75), (6.0, 20.0, -6.5), "n")
    K.pane(m, (6.5, 11.0, -6.0), (6.75, 20.0, 6.0), "e")
    K.pane(m, (-6.75, 11.0, -6.0), (-6.5, 20.0, 6.0), "w")
    # the top is glass as well, and bare: what lies in the case is looked at through it
    K.pane(m, (-6.0, 20.5, -6.0), (6.0, 20.75, 6.0), "u", sheen=False)
    return m


SPEC = {
    "bench": dict(build=_bench, mount="floor"),
    "writing_desk": dict(build=_writing_desk, mount="floor"),
    "display_table": dict(build=_display_table, mount="floor"),
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
    "crate_small": dict(build=_crate_small, mount="floor"),
    "display_case": dict(build=_display_case, mount="floor"),
}
SCALE = {PREFIX + name: 1.0 for name in SPEC}
# how high above its foot a piece carries what is put on it (blocks); the trunk's is its lid, of
# which the two straps are STRAP proud
TOP = {"writing_desk": 12.0 / 16.0, "display_table": 11.25 / 16.0, "display_case": 11.25 / 16.0,
       "card_cabinet": 30.0 / 16.0, "instrument_cabinet": 30.0 / 16.0, "trunk": 11.0 / 16.0,
       "crate": 12.0 / 16.0, "crate_small": 8.0 / 16.0, "bench": 7.0 / 16.0, "swivel_chair": 7.0 / 16.0,
       "stool": 12.0 / 16.0}
STRAP = 0.5 / 16.0


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
    facing   the way the piece's front looks: where a sitter on the bench, the chair or the stool
             looks, the side of the desk and the drafting table one sits at, the doors and drawer
             fronts of a cabinet, the side of the display table one stands at; for the ladder and
             its rail the way the bookcase front looks. yaw (degrees) turns a standing piece freely
             instead.
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


# ---- the site --------------------------------------------------------------------------------------------
# Indoors every room places its own furniture. Out of doors it is placed from here: the packages of
# the site are blocks only and say where (site/cablecar: BENCHES, LUGGAGE), or leave the place and
# the choice to this package (the sunset terrace, the south lookout). Three groups:
#   station   two benches against the waiting room of the cable station, one under its lit gable
#             window and one at the foot of its front, and somebody's luggage set down by its door:
#             a trunk along the wall and a crate on the trunk.
#   sunset    four benches at the prow of the sunset terrace, their backs to the building, looking
#             west over the rail at the afterglow: a pair either side of the walk from the west
#             door, on the band of small stones between the walk and the strips, and a pair beyond
#             the strips, a block and a half further back, so that the row follows the curve of
#             the rail. The rail's piers stand on the axis and five and nine cells either side of
#             it (site/terrain: one every 15 degrees of the arc): every bench looks out through a
#             bay, a pier beyond each of its ends and none before it. In front of every row of a
#             bench more than two whole blocks are free to walk in, and the walk and the two strips
#             stay clear.
#   lookout   one bench on the south lookout, its back to the east rail. Who sits there looks west,
#             the observatory on the right. The view back (S.V11) is taken from the walk in the
#             middle of the lookout and looks north-west: the bench is behind its right edge.
DRESS = True            # on from the merge on (the fast lane, COMMON 0.10); a test scene may still ask
                        # for the site's furniture with dress(canvas), or call site() for its group
SUNSET_BENCHES = ((14.5, 3.5), (13.0, 7.5))     # (west of the terrace's middle, off the axis): a pair each
LOOKOUT_BENCH = (0.6, -1.5)     # in from the face of the east rail's kerb; from the lookout's middle row:
                                # half way between the rail's north corner and the pier at the prow's knuckle
# the luggage: (kind, the offset from the point the station gives, yaw). The trunk stands along the
# wall, clear of the door's jamb; the small packing case stands on the east end of its lid, on the
# strap, a little askew (the big one is deeper than the lid and taller than the trunk)
LUGGAGE = (("trunk", (0.25, 0.0, -0.05), -5.0), ("crate_small", (0.5, TOP["trunk"] + STRAP, -0.05), 6.0))
BENCH_ENDS = 0.8                # how far from its middle the floor under a bench is looked for
# The package of the site that lays the floor a group stands on; the sunset terrace is site/terrain's.
# Level ground is kept for a package before it is merged (the mountain's shelves): a bench is not
# set down on the bare rock of a shelf.
FLOORS = {"station": "site.cablecar", "lookout": "site.outbuildings"}

# What the packages of the site reported in the group, for a tree in which a package is not merged
# yet. Once it is, its own table is read instead: _told().
_REPORTED = {
    # c226, g2 #506. point: the middle of the piece's foot; a bench stands 0.45 off the wall behind it
    ("site.cablecar", "BENCHES"): {"gable": dict(point=(79.55, -4.0, -38.0), facing="west"),
                                   "front": dict(point=(81.5, -4.0, -35.55), facing="south")},
    ("site.cablecar", "LUGGAGE"): dict(point=(84.5, -4.0, -35.5)),
}


def _told(module, name):
    """What a package of the site says about its furniture, or the numbers it reported while it is
    not in the tree."""
    try:
        return getattr(importlib.import_module(f"..{module}", __package__), name)
    except (ImportError, AttributeError):
        return _REPORTED[module, name]


def floor_in_tree(group):
    """True when the package that lays the floor of a group's furniture is in this tree."""
    module = FLOORS.get(group)
    if module is None:
        return True
    return importlib.util.find_spec(f"{__package__.rpartition('.')[0]}.{module}") is not None


def luggage(point):
    """The luggage set down at `point` (a point at the foot of a wall that looks south) as
    [(kind, position, yaw)]; the first piece stands on the floor and carries the others."""
    x, y, z = (float(v) for v in point)
    return [(kind, (x + dx, y + dy, z + dz), yaw) for kind, (dx, dy, dz), yaw in LUGGAGE]


def site_pieces():
    """The furniture of the site as (group, kind, point, yaw, foot). point is the middle of the
    piece's foot in scene coordinates before the origin; foot is the point whose floor decides
    whether the piece is placed: its own, or that of the piece it stands on."""
    out = []
    for bench in _told("site.cablecar", "BENCHES").values():
        p = tuple(float(v) for v in bench["point"])
        out.append(("station", "bench", p, K.FACING[bench["facing"]], p))
    pieces = luggage(_told("site.cablecar", "LUGGAGE")["point"])
    for kind, p, yaw in pieces:
        out.append(("station", kind, p, yaw, pieces[0][1]))
    cx, cz = S.SUNSET_PLATFORM["centre"]
    for west, off in SUNSET_BENCHES:
        for side in (-1.0, 1.0):
            p = (S.mid(cx) - west, float(S.GROUND), S.mid(cz) + side * off)
            out.append(("sunset", "bench", p, K.FACING["west"], p))
    x0, z0, x1, z1 = S.SOUTH_LOOKOUT["box"]
    p = (x1 - LOOKOUT_BENCH[0], float(S.SOUTH_LOOKOUT["feet"]), S.mid(z0, z1) + LOOKOUT_BENCH[1])
    out.append(("lookout", "bench", p, K.FACING["west"], p))
    return out


def _stands(canvas, kind, foot, yaw, origin=(0, 0, 0)):
    """True when the piece has a floor under it on the canvas as it is, and room to stand in: under
    the middle of its foot, and for a bench under both its ends as well, the cell below is taken and
    the cell above that is free (a light source in it does not count)."""
    for along in ((-BENCH_ENDS, 0.0, BENCH_ENDS) if kind == "bench" else (0.0,)):
        dx, _, dz = K.turn(yaw, (along, 0.0, 0.0))
        x, z = math.floor(foot[0] + dx + origin[0]), math.floor(foot[2] + dz + origin[2])
        y = math.ceil(foot[1] + origin[1])
        if not canvas.has(x, y - 1, z) or canvas.name(x, y, z) not in (None, B.LIGHT):
            return False
    return True


def dress(canvas, on=True):
    """Ask for the furniture of the site on this canvas while the switch DRESS is off (a test scene).
    Call it before the lines are built."""
    canvas.furniture_dress = bool(on)


def site(canvas, origin=(0, 0, 0), groups=None):
    """Place the furniture of the site (site_pieces()), or of the groups named ("station", "sunset",
    "lookout"). A piece is only placed where the package that lays its floor is in the tree
    (floor_in_tree) and that floor is on the canvas as it is, so a tree without one of the site's
    packages has fewer pieces and none that floats or stands on bare rock; what was left out is
    kept in canvas.furniture_left_out as (group, kind, point). A piece is placed once: a second
    call, for the same groups or for more of them, adds what does not stand yet. Returns the number
    of display entities placed by this call."""
    origin = tuple(origin)
    placed = getattr(canvas, "furniture_placed", None)
    if placed is None:
        placed = canvas.furniture_placed = set()
    n, left = 0, list(getattr(canvas, "furniture_left_out", []))
    for group, kind, p, yaw, foot in site_pieces():
        if (groups is not None and group not in groups) or (kind, p, origin) in placed:
            continue
        if floor_in_tree(group) and _stands(canvas, kind, foot, yaw, origin):
            n += place(canvas, kind, p, yaw=yaw, origin=origin)
            placed.add((kind, p, origin))
        elif (group, kind, p) not in left:
            left.append((group, kind, p))
    canvas.furniture_left_out = [e for e in left if (e[1], e[2], origin) not in placed]
    return n


def build(canvas, origin=(0, 0, 0)):
    """What this package places in the master scene itself: the furniture of the site (site()), once
    the switch DRESS is on or a test scene has asked for it (dress()). Indoors the furniture is
    placed by the rooms, each piece where it is used, with place()."""
    if getattr(canvas, "furniture_dress", DRESS):
        return site(canvas, origin)
    return 0
