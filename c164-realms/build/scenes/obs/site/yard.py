"""site/yard: the works yard on the lower platform (plan/round2.md, section 丙二; plan/fine.md; card
plan/packages/site/yard.md).

Coal comes up the mountain by the train and is burnt in the power house, at the other end of the
platform. Between the two lies a tramway of narrow gauge, set into the paving so that the yard stays
a floor to walk on:

  line A   along the pilaster line north of the stair that carries the first buttress (the row of
           the paving's band there): from the coal heap at the foot of the retaining wall, under
           the station's south side, to a stub with a buffer stop
  table    a turntable where line A meets line B: a round iron deck in a square seat, on which one
           tub at a time is turned a quarter turn from one line into the other
  line B   from the table south along the apron's outer column, across the foot of the grand stair
           and down the middle of the walk to the power house, to its door. Between the two foot
           pedestals of the stair (the forecourt, the main axis) nothing ever stands on it.

What is set into the floor is blocks: one row of riveted iron plate in the paving course, and the
table's seat, three by three, of plain plate; and where they lie in the field of dark setts, a kerb
of the paving's light band stone either side of them (KERB), as a tramway in a paved street has.
They are what the yard is from far off and from above: a dark line in a light strip from the
station's corner to the power house, and a square on it. Where the line lies in a band, the apron or
the walk to the door, the stone beside it is that already; the kerb changes field stone only, and
nothing that something stands on. Everything else is
models on the paving, none of them higher than a tub with its load (a block and a quarter):

  rails    two rails a texel proud of the plate, worn bright on top, in chairs and with a tie bar
           to every block, fishplates where two lengths meet; no collision, so the yard is walked
           on as before (a4: nothing set in the floor stands higher than the floor for the feet)
  rope     west of the table the tubs are hauled by an endless wire rope that runs on rollers
           between the rails; it comes up out of the floor by the table and goes round a return
           sheave in front of the west stop
  tubs     iron tubs on four wheels, strapped and riveted, with a timber headstock at each end:
           two of them coupled, with coal, on the rope; one with coal on the table; one empty on
           the stub
  stops    a timber beam on two bent rails at the west and the east end of line A
  heap     the coal stock in a bin of two plank sides at the foot of the wall, a shovel in it
  scale    a weighbridge in line A where the tubs stop by the heap: a plate under the rails in a
           frame, and beside the track its pillar with the dial
  stack    spare sleepers in a crib and two lengths of rail on bearers, by the stub
  plate    the table's number, No. 05 (props/nameplates, plan/parts/numbers.md), flat on its seat
The tubs carry their numbers in white paint (the station's letters, props/_kit.letters).

What moves (the motion kit, scenes/obs/motion/_kit):
  * the two tubs on the rope go from the table's side to the heap and back, RUN blocks in CYCLE
    ticks, a slide with a slow start and a slow stop;
  * the return sheave turns with the rope, as far as the rope has gone round it, and stands when
    the tubs stand;
  * the needle of the weighbridge goes up when the first tub rolls onto the plate, swings past
    the weight and settles, and falls back when the last wheel is off;
  * the table turns a quarter turn with the tub that is on it, stands in line with line B, and
    turns back. (It is to be worked by hand, with the handle on its rim, once the kit has the
    switch for it: director, round 2 section 丙三.)
The poses they are placed in are where the loop starts: the tubs by the table, the table in line A.

Where a moving tub stops it leaves a block free before whatever stands at the end of its way (the
west stop, the table), so nobody is shown caught between the two (a4).

The traces (plan/fine.md, the near layer: oil round the table's pivot and under the axle boxes, coal
dust by the heap and along the line, the chalk on the tubs) are the materials line's shapes
(materials/traces: a1, 11-16 13:05) and are put on with them when they are there; none is drawn here.

The view bands (INTERFACE 7; s2, 11-16 13:12: what stands on a line and the cars keep the far band,
what is a texel or two from far off goes down): the tubs, the deck, the heap, the scale's pillar and
the stack are drawn across the site (FAR_MODELS); the rails, the seat's ring, the stops and the sheave
within a terrace (M.MID); the needle from near (M.NEAR). From above and from far off the blocks tell
the line and those stand on it.
"""
import functools
import math
import random

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..motion import _kit as MK
from ..props import _kit as PK
from ..props import nameplates
from . import _kit as K
from . import powerhouse

PREFIX = "site_yard_"
VIEW = M.MID
FAR_MODELS = tuple(PREFIX + name for name in ("rake", "tub", "tub_empty", "deck", "coal", "scale", "stack"))
NEAR_MODELS = (PREFIX + "needle",)
# the assembly brings every other entity of the package down to VIEW (the number plate is the props line's)
VIEW_KEEP = FAR_MODELS + NEAR_MODELS + (nameplates.PREFIX + "*",)
PX = 1.0 / 16.0

FEET = S.LOWER_GROUND               # -6: the top of the paving
PY = S.LOWER_PAVING_Y               # -7: the paving course

# --- where it lies (cells; a4, 11-16 12:43) ----------------------------------------------------------
ROW = -22                           # line A: the row of the first buttress north of the stair
TABLE = (74, ROW)                   # the turntable's middle cell
TABLE_HALF = 1                      # its seat is three cells square
A_WEST = (64, TABLE[0] - TABLE_HALF - 1)            # x 64..72
A_EAST = (TABLE[0] + TABLE_HALF + 1, 79)            # x 76..79: it ends west of the walk from the station
DOOR = powerhouse.DOOR_AT["cell"]                   # the power house's wicket
B_Z = (ROW + TABLE_HALF + 1, DOOR[1] - 1)           # line B, column TABLE[0]: z -20 .. the cell before the wicket
HEAP = (64, -19)                    # the middle cell of the coal heap (three by three)
SCALE_X = 68.0                      # the middle of the weighbridge's plate on line A (cells 67 and 68)
STACK = (78, ROW - 2)               # the cell the crib of sleepers stands in, north of the stub
NUMBER = 5                          # the table's number in the station's list of machines

BED = B.IRON_RIVETED.block          # the plate the rails lie on
SEAT = B.IRON_PLATE                 # the table's seat
KERB = True                         # the switch: a kerb of the band's stone either side of the plate, in the field
FIELD, CURB = K.EDGE, K.STRIP       # the lower platform's setts, and the stone of its bands (site/lowerplatform)

# --- the track, in texels ----------------------------------------------------------------------------
GAUGE = 5.0                         # from the middle of the track to the middle of a rail
RAIL = 1.0                          # a rail's half width; it stands RAIL_UP proud of the plate
RAIL_UP = 1.0
LENGTH = 3                          # blocks in one length of rail (a model is three blocks at most)

# --- the tubs -----------------------------------------------------------------------------------------
TUB = 11.0                          # half the length of a tub over its headstocks
COUPLED = 24.0                      # from the middle of one tub of the rake to the middle of the other
WHEEL = 3.0                         # a wheel's radius
REST_X = 71.0                       # the middle of the rake where it is placed, by the table
RUN = 4.0                           # blocks it is hauled west from there
CYCLE = 30 * MK.SECOND
EASE = (0.3, MK.SECOND)             # the first and the last of a run: this far in this many ticks
HAUL = 8 * MK.SECOND                # the run between the two
LEAVES = (2 * MK.SECOND, 17 * MK.SECOND)        # when it sets off west, and back east

NUMBERS = {"tub": 2, "tub_empty": 9, "rake": (4, 7)}     # what is painted on each tub
PAINT = P.RAMPS["cream"][1]

# --- the weighbridge ----------------------------------------------------------------------------------
PLATE_HALF = (15.0, 7.6)            # the plate's half length and half width
PILLAR = 16.0                       # from the middle of the track to the middle of the pillar, southwards
DIAL = (3.5, 17.5)                  # the dial's face: how far east of the pillar's middle, and how high its middle
DIAL_R = 3.6
ZERO = 135.0                        # the needle at rest: turned this far from upright, to the lower left of the dial
WEIGHT = (215.0, 200.0, -12.0)      # degrees it swings to, settles at, and falls back past

# --- the sheave ---------------------------------------------------------------------------------------
SHEAVE = 4.0                        # its radius
SHEAVE_AT = (12.0, 4.0)             # its middle in the west stop's model: along the track, and above the plate

# --- the table ----------------------------------------------------------------------------------------
DECK = 20.0                         # the deck's radius
RING = (20.4, 22.0)                  # the seat's ring round it, from and to
TABLE_CYCLE = 60 * MK.SECOND
QUARTER = 5 * MK.SECOND             # ticks a quarter turn takes
TABLE_TURNS = (6 * MK.SECOND, 36 * MK.SECOND)   # when it turns into line B, and back
BOLT = (14.0, 8.6)                  # the handle on the deck: east of the middle, south of the south rail
SOCKET = 21.2                       # how far from the middle the bolt's socket stands on the ring

IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
IRON_L = P.mat("iron", base=4)
WHITE = P.mat("porcelain", kind="flat", base=3, bevel=0)
HEAD = P.mat("iron", base=5, noise=0.10, bevel=0)           # worn bright: a rail's head, a tread, a grip
PLATE = P.mat("iron", kind="flat", base=2, bevel=0)
WIRE = P.mat("iron", kind="rope", base=3, bevel=0)
WOOD = P.mat("dark_wood")
WOOD_L = P.mat("dark_wood", base=3)
BRASS = P.mat("brass")
RED = P.mat("signal")
# the coal of the power house's bin (interiors/powerhouse): the same three lumps on the same dark core
COAL_CORE = P.mat("slate", kind="flat", base=0, bevel=0)
COAL_LUMP = (P.mat("slate", base=0, noise=0.5), P.mat("slate", base=1, noise=0.5), P.mat("iron", base=1, noise=0.4))


def _rivet(m, x, y, z, out, mat=IRON_L, proud=0.4):
    """A rivet head, a texel square, on a face that looks along `out` ("x", "-x", "y", "z", "-z")."""
    k = M.AXES.index(out[-1])
    lo, hi = [x - 0.5, y - 0.5, z - 0.5], [x + 0.5, y + 0.5, z + 0.5]
    at = (x, y, z)[k]
    lo[k], hi[k] = sorted((at, at + (-proud if out.startswith("-") else proud)))
    m.box(tuple(lo), tuple(hi), mat, seed=900)


# --- the rails ------------------------------------------------------------------------------------------
def _rail(name, blocks, rope=False):
    """A length of track along x, `blocks` long, its middle on the plate at the anchor."""
    m = M.Model(name)
    half = 8.0 * blocks
    for s in (-1, 1):
        z = s * GAUGE
        m.box((-half, 0.0, z - RAIL), (half, RAIL_UP, z + RAIL), IRON_D, faces={"u": HEAD}, grain="x", seed=1)
        for i in range(blocks):
            for x in (-half + 16.0 * i + 4.0, -half + 16.0 * i + 12.0):
                # a chair: a lug either side of the rail, a bolt in each
                m.box((x - 1.0, 0.0, z - RAIL - 1.5), (x + 1.0, 0.6, z + RAIL + 1.5), IRON, seed=2)
                for t in (-1, 1):
                    _rivet(m, x, 0.6, z + t * (RAIL + 0.9), "y", proud=0.3)
        for end in (-1, 1):
            # half a fishplate on the rail's outer side; the next length brings the other half
            a, b = sorted((end * half, end * (half - 3.0)))
            m.box((a, 0.0, z + s * RAIL), (b, 0.8, z + s * (RAIL + 0.7)), IRON, seed=3)
            _rivet(m, end * (half - 1.5), 0.8, z + s * (RAIL + 0.35), "y", proud=0.25)
    for i in range(blocks):
        x = -half + 16.0 * i + 8.0
        m.box((x - 0.5, 0.0, -GAUGE + RAIL), (x + 0.5, 0.5, GAUGE - RAIL), IRON, grain="z", seed=4)      # the tie bar
        if rope:
            for t in (-1, 1):                                                                        # the roller's two cheeks
                m.box((x - 1.0, 0.5, t * 1.6 - 0.3), (x + 1.0, 1.3, t * 1.6 + 0.3), IRON, seed=5)
            m.tube("z", (x, 0.9), -1.3, 1.3, 0.55, HEAD, sides=6, seed=6)
    if rope:
        m.box((-half, 1.25, -0.35), (half, 1.95, 0.35), WIRE, grain="x", seed=7)
    return m


# --- a tub ----------------------------------------------------------------------------------------------
def _lumps(m, rnd, spots):
    for i, (x, y, z) in enumerate(spots):
        size = rnd.choice((2.0, 2.5, 3.0, 3.0, 3.5))
        c = (x, y + size / 2.0, z)
        h = size / 2.0
        m.box((c[0] - h, c[1] - h, c[2] - h), (c[0] + h, c[1] + h, c[2] + h), COAL_LUMP[i % len(COAL_LUMP)],
              rot=("xyz", (rnd.uniform(-25, 25), rnd.uniform(0, 90), rnd.uniform(-25, 25)), c), seed=100 + i % 9)


def _figure(m, number):
    """A tub's number in white paint on both its sides, between the straps."""
    rows = PK.letters(str(number), ink="k")
    half = len(rows[0]) / 2.0
    paint = Sprite(f"{PREFIX}no{number}", rows, {"k": PAINT})
    for s in (-1, 1):
        a, b = sorted((s * 7.0, s * 7.06))
        m.box((-half, 14.3 - len(rows), a), (half, 14.3, b), IRON, skip="udew" + ("n" if s > 0 else "s"),
              faces={"s" if s > 0 else "n": paint}, shade=False, seed=50 + number)


def _tub(m, at=0.0, coal=True, seed=1890, number=None):
    """A tub drawn into m: the middle of its wheelbase at x = at, its wheels on y = 0 (the rail heads),
    the track along x."""
    rnd = random.Random(seed)
    with m.moved((at, 0.0, 0.0)):
        for x in (-6.0, 6.0):
            m.tube("z", (x, WHEEL), -GAUGE, GAUGE, 0.7, IRON_D, sides=6, seed=10)                 # the axle
            for s in (-1, 1):
                z = s * GAUGE
                m.tube("z", (x, WHEEL), z - 0.9, z + 0.9, WHEEL, IRON, sides=12, seed=11)         # the wheel
                m.tube("z", (x, WHEEL), z - 1.1, z + 1.1, 1.0, IRON_D, sides=6, seed=12)          # its boss
                m.box((x - 1.6, 2.0, s * 2.7), (x + 1.6, 4.4, s * 3.9), IRON, seed=13)            # the axle box
                m.box((x - 0.6, 4.4, s * 2.9), (x + 0.6, 4.9, s * 3.7), BRASS, seed=14)           # its oil cup
        for s in (-1, 1):
            m.box((-10.0, 4.6, s * 2.8), (10.0, 6.0, s * 3.8), IRON_D, grain="x", seed=15)        # the sole bars
        for e in (-1, 1):
            a, b = sorted((e * 9.6, e * TUB))
            m.box((a, 3.6, -6.5), (b, 6.6, 6.5), WOOD, grain="z", seed=16)                        # the headstock
            for z in (-5.0, 5.0):
                _rivet(m, e * TUB, 5.1, z, "x" if e > 0 else "-x")
            a, b = sorted((e * TUB, e * (TUB + 1.0)))
            m.box((a, 4.4, -1.0), (b, 5.8, 1.0), IRON, seed=17)                                   # the drawbar's plate
        # the body: a floor and four sides of plate, an angle iron round the top, straps and corner
        # angles riveted on
        m.box((-9.0, 6.0, -7.0), (9.0, 7.0, 7.0), IRON_D, seed=20)
        for s in (-1, 1):
            a, b = sorted((s * 6.0, s * 7.0))
            m.box((-9.0, 7.0, a), (9.0, 15.0, b), IRON, faces={"n" if s > 0 else "s": PLATE}, grain="x", seed=21)
            a, b = sorted((s * 7.0, s * 7.45))
            for x in (-5.0, 5.0):
                m.box((x - 0.6, 6.0, a), (x + 0.6, 14.5, b), IRON_D, grain="y", seed=22)           # a strap
                for y in (7.5, 10.5, 13.5):
                    _rivet(m, x, y, s * 7.45, "z" if s > 0 else "-z", proud=0.3)
            a, b = sorted((s * 6.6, s * 7.6))
            m.box((-9.6, 14.4, a), (9.6, 15.4, b), IRON_L, grain="x", seed=23)                    # the rim
        for e in (-1, 1):
            a, b = sorted((e * 8.0, e * 9.0))
            m.box((a, 7.0, -6.0), (b, 15.0, 6.0), IRON, faces={"w" if e > 0 else "e": PLATE}, grain="z", seed=24)
            a, b = sorted((e * 8.6, e * 9.6))
            m.box((a, 14.4, -6.6), (b, 15.4, 6.6), IRON_L, grain="z", seed=25)                    # the rim
            for s in (-1, 1):
                za, zb = sorted((s * 6.4, s * 7.45))
                xa, xb = sorted((e * 8.4, e * 9.45))
                m.box((xa, 6.0, za), (xb, 14.4, zb), IRON_D, grain="y", seed=26)                   # a corner angle
            # the end door's bar and its catch
            a, b = sorted((e * 9.0, e * 9.5))
            m.box((a, 10.0, -5.6), (b, 11.2, 5.6), IRON_D, grain="z", seed=27)
            a, b = sorted((e * 9.5, e * 10.0))
            m.box((a, 9.8, -0.8), (b, 11.4, 0.8), HEAD, seed=28)
        if number is not None:
            _figure(m, number)
        if coal:
            m.box((-8.0, 7.0, -6.0), (8.0, 14.6, 6.0), COAL_CORE, skip="d", seed=30)
            spots = []
            for i in range(6):
                for j in range(5):
                    x, z = -6.9 + i * 2.75 + rnd.uniform(-0.5, 0.5), -5.0 + j * 2.5 + rnd.uniform(-0.4, 0.4)
                    crown = 3.4 * (1.0 - (x / 9.5) ** 2) * (1.0 - (z / 7.5) ** 2)
                    spots.append((x, 13.2 + crown + rnd.uniform(-0.5, 0.5), z))
            _lumps(m, rnd, spots)
        else:
            # what is left in an empty one: dust in the corners, the floor rubbed bright in the middle
            m.box((-8.0, 7.0, -6.0), (8.0, 7.3, 6.0), COAL_CORE, skip="d", seed=31)
            m.box((-4.5, 7.3, -3.0), (4.0, 7.45, 2.5), IRON_L, skip="d", seed=32)
            _lumps(m, rnd, [(-6.6, 7.0, -4.6), (-6.2, 7.0, 4.4), (6.4, 7.0, -4.2), (5.2, 7.2, 4.6), (-3.0, 7.0, 4.9)])
    return m


def _link(m, x):
    """The coupling between two tubs whose drawbar plates face each other across x."""
    m.box((x - 1.6, 4.7, -0.45), (x + 1.6, 5.5, 0.45), HEAD, grain="x", seed=40)
    for e in (-1, 1):
        m.box((x + e * 1.2 - 0.4, 4.3, -0.8), (x + e * 1.2 + 0.4, 5.9, 0.8), IRON_D, seed=41)


def _grip(m, x):
    """The clip that holds a tub to the rope, under its headstock at x: a jaw on the rope and its screw."""
    m.box((x - 0.8, 1.9, -0.9), (x + 0.8, 3.8, 0.9), IRON, seed=42)
    m.box((x - 0.4, 3.8, -0.4), (x + 0.4, 4.6, 0.4), HEAD, seed=43)
    m.box((x - 1.4, 2.6, -0.3), (x + 1.4, 3.0, 0.3), HEAD, seed=44)


def _tub_models():
    one = _tub(M.Model(PREFIX + "tub"), seed=1891, number=NUMBERS["tub"])
    empty = _tub(M.Model(PREFIX + "tub_empty"), coal=False, seed=1892, number=NUMBERS["tub_empty"])
    rake = M.Model(PREFIX + "rake")
    _tub(rake, -COUPLED / 2.0, seed=1893, number=NUMBERS["rake"][0])
    _tub(rake, COUPLED / 2.0, seed=1894, number=NUMBERS["rake"][1])
    _link(rake, 0.0)
    _grip(rake, -COUPLED / 2.0 - 8.0)
    return [one, empty, rake]


# --- the stops and the sheave -----------------------------------------------------------------------------
def _stop(name, sheave=False):
    """The end of a line: the anchor in the middle of the track on the plate where the rails end,
    the track running off along +x. Two rails bent up, a timber across them, a strut behind each.
    With sheave: the housing of the rope's return sheave before it (the wheel is a model of its own)."""
    m = M.Model(name)
    for s in (-1, 1):
        z = s * GAUGE
        m.box((2.0, 0.0, z - RAIL), (4.0, 9.5, z + RAIL), IRON_D, faces={"e": HEAD}, grain="y", seed=1)      # the post
        m.beam((0.4, 0.6, z), (2.6, 7.0, z), 1.2, 1.2, IRON, seed=2)                                          # its strut
        m.box((1.2, 0.0, z - 2.0), (5.0, 0.6, z + 2.0), IRON, seed=3)                                         # the foot plate
        for x in (1.8, 4.4):
            for t in (-1, 1):
                _rivet(m, x, 0.6, z + t * 1.5, "y", proud=0.3)
    m.box((4.0, 5.0, -7.5), (7.0, 9.0, 7.5), WOOD, grain="z", seed=4)                                         # the beam
    for s in (-1, 1):
        a, b = sorted((s * 6.2, s * 7.6))
        m.box((3.9, 4.9, a), (7.1, 9.1, b), IRON_D, seed=5)                                                   # its end straps
        for y in (6.0, 8.0):
            _rivet(m, 7.1, y, s * 6.9, "x", proud=0.3)
        _rivet(m, 7.0, 7.0, s * GAUGE, "x", mat=HEAD, proud=0.5)                                              # the bolts through the posts
    m.box((7.0, 5.6, -2.2), (7.4, 8.4, 2.2), RED, seed=6)                                                     # the red plate in the middle
    if sheave:
        x, y = SHEAVE_AT
        for s in (-1, 1):
            a, b = sorted((s * 1.2, s * 2.0))
            m.box((x - 4.5, 0.0, a), (x + 4.5, 1.6, b), IRON, grain="x", seed=7)                              # a cheek: its foot,
            m.box((x - 2.6, 1.6, a), (x + 2.6, 3.2, b), IRON, grain="x", seed=8)                              # its waist
            m.box((x - 1.3, 3.2, a), (x + 1.3, y + 1.3, b), IRON, seed=9)                                     # and its head
            a, b = sorted((s * 2.0, s * 2.7))
            m.box((x - 1.0, y - 1.0, a), (x + 1.0, y + 1.0, b), BRASS, seed=10)                               # the bearing
            m.box((x - 0.4, y + 1.0, a), (x + 0.4, y + 1.7, b), BRASS, seed=11)                               # its oil cup
            for t in (-3.6, 3.6):
                _rivet(m, x + t, 1.6, s * 1.6, "y", proud=0.3)
        m.box((x - 5.5, 0.0, -2.9), (x + 5.5, 0.4, 2.9), IRON_D, seed=12)                                     # the bed plate
        # the rope: up from the last roller over the wheel, and down behind it into the floor
        m.rod((24.0, 1.6, 0.0), (x + 0.6, y + SHEAVE + 0.3, 0.0), 0.35, WIRE, sides=6, seed=13)
        m.rod((x - SHEAVE - 0.3, y - 0.4, 0.0), (x - SHEAVE - 0.3, 0.0, 0.0), 0.35, WIRE, sides=6, seed=13)
        m.box((x - SHEAVE - 1.3, 0.0, -1.0), (x - SHEAVE + 0.7, 0.5, 1.0), IRON_D, seed=14)                   # the slot's lip
    return m


def _sheave():
    """The return sheave: a spoked wheel on the axle across the track; the anchor on its axis."""
    m = M.Model(PREFIX + "sheave")
    m.ring("z", (0.0, 0.0, 0.0), SHEAVE - 0.6, 1.2, 1.0, IRON_L, sides=12, seed=1)
    for k in range(3):
        with m.turned(("z", 60.0 * k)):
            m.box((-SHEAVE + 1.0, -0.4, -0.3), (SHEAVE - 1.0, 0.4, 0.3), IRON_D, grain="x", seed=2)
    m.tube("z", (0.0, 0.0), -2.0, 2.0, 0.45, HEAD, sides=6, seed=3)
    m.tube("z", (0.0, 0.0), -0.8, 0.8, 1.2, IRON, sides=6, seed=4)
    return m


# --- the table ------------------------------------------------------------------------------------------
def _deck():
    """The turning deck: the anchor in its middle on the seat; its rails along x where it is placed."""
    m = M.Model(PREFIX + "deck")
    m.tube("y", (0.0, 0.0), 0.0, 0.5, DECK, IRON_D, sides=16, seed=1)
    m.ring("y", (0.0, 0.6, 0.0), DECK - 1.0, 2.0, 0.3, IRON, sides=32, seed=2)                    # the rim band
    for k in range(16):
        a = math.radians(22.5 * k + 11.25)
        _rivet(m, (DECK - 1.0) * math.cos(a), 0.75, (DECK - 1.0) * math.sin(a), "y", proud=0.3)
    reach = math.sqrt(DECK ** 2 - (GAUGE + RAIL) ** 2) - 0.4
    for s in (-1, 1):
        z = s * GAUGE
        m.box((-reach, 0.5, z - RAIL), (reach, RAIL_UP, z + RAIL), IRON_D, faces={"u": HEAD}, grain="x", seed=3)
        for x in (-13.0, 0.0, 13.0):
            m.box((x - 1.0, 0.5, z - RAIL - 1.5), (x + 1.0, 0.8, z + RAIL + 1.5), IRON, seed=4)
        # a cover plate either side of the track, bolted down at its corners; its lifting ring
        a, b = sorted((s * 8.6, s * 15.4))
        m.box((-10.0, 0.5, a), (10.0, 0.8, b), IRON, grain="x", seed=5)
        for x in (-8.6, 8.6):
            for z2 in (a + 1.2, b - 1.2):
                _rivet(m, x, 0.8, z2, "y", proud=0.25)
        m.box((-1.5, 0.8, s * 12.0 - 0.4), (1.5, 1.1, s * 12.0 + 0.4), HEAD, seed=6)
    m.tube("y", (0.0, 0.0), 0.5, 1.4, 2.6, IRON, sides=12, seed=7)                                # the pivot's cap
    m.tube("y", (0.0, 0.0), 1.4, 1.9, 1.0, BRASS, sides=6, seed=8)                                # its grease cup
    # the handle, by the east end of the south rail: a lever in a quadrant, its grip rubbed bright.
    # It draws the bolt that holds the deck in line: the bolt's nose stands in a socket of the seat's ring
    x, z = BOLT
    m.box((x - 2.0, 0.5, z - 1.0), (x + 2.0, 1.0, z + 1.0), IRON, seed=10)
    m.ring("z", (x, 1.0, z), 3.0, 0.6, 0.6, IRON_D, sides=12, arc=(0.0, 180.0), seed=11)
    m.beam((x, 1.0, z), (x - 2.2, 9.0, z), 0.8, 0.8, IRON_L, seed=12)
    m.box((x - 3.0, 9.0, z - 0.7), (x - 1.6, 11.4, z + 0.7), HEAD, seed=13)
    m.box((x + 1.2, 0.5, z - 0.5), (SOCKET + 0.6, 1.2, z + 0.5), HEAD, grain="x", seed=14)          # the bolt
    return m


def _pit():
    """What does not turn: the ring round the deck, the ends of the three lines on it, the bolt's two
    sockets, the mouth the rope comes out of, a stop where no line leaves."""
    m = M.Model(PREFIX + "pit")
    inner, outer = RING
    m.ring("y", (0.0, 0.35, 0.0), (inner + outer) / 2.0, outer - inner, 0.7, IRON, sides=32, seed=1)
    for k in range(16):
        a = math.radians(22.5 * k + 11.25)
        _rivet(m, (inner + outer) / 2.0 * math.cos(a), 0.7, (inner + outer) / 2.0 * math.sin(a), "y", proud=0.3)
    for s in (-1, 1):
        z = s * GAUGE
        for e in (-1, 1):                           # line A, west and east
            a, b = sorted((e * (DECK + 0.3), e * 24.0))
            m.box((a, 0.0, z - RAIL), (b, RAIL_UP, z + RAIL), IRON_D, faces={"u": HEAD}, grain="x", seed=2)
        m.box((z - RAIL, 0.0, DECK + 0.3), (z + RAIL, RAIL_UP, 24.0), IRON_D, faces={"u": HEAD}, grain="z", seed=3)   # line B
    # the sockets: where the bolt stands with the deck in line A, and a quarter turn on, in line B
    x, z = SOCKET, BOLT[1]
    for cx, cz in ((x, z), (z, -x)):
        m.box((cx - 1.1, 0.0, cz - 1.1), (cx + 1.1, 1.5, cz + 1.1), IRON_D, seed=4)
        m.box((cx - 0.6, 1.5, cz - 0.6), (cx + 0.6, 1.7, cz + 0.6), PLATE, seed=5)
    m.box((-GAUGE - RAIL, 0.0, -24.0), (GAUGE + RAIL, 2.2, -DECK - 0.4), IRON, grain="x", seed=6)  # north: the stop
    for x in (-GAUGE, 0.0, GAUGE):
        _rivet(m, x, 2.2, -22.2, "y", proud=0.3)
    # west, between the rails: the hood the rope comes up under
    m.box((-24.0, 0.0, -1.5), (-DECK - 0.4, 2.3, 1.5), IRON, seed=7)
    m.box((-24.0, 2.3, -1.9), (-DECK - 0.2, 2.8, 1.9), IRON_D, seed=8)
    for z in (-1.0, 1.0):
        _rivet(m, -22.2, 2.8, z, "y", proud=0.3)
    return m


# --- the coal -------------------------------------------------------------------------------------------
HEAP_HALF = (22.0, 20.0)            # the heap's half size east-west and north-south
HEAP_HIGH = 17.0


def _height(x, z):
    """How high the heap stands at (x, z): full against the two plank sides (west and south), down
    to nothing at the open edges (east and north)."""
    fx = min(1.0, max(0.0, (HEAP_HALF[0] - 2.0 - x) / 15.0))
    fz = min(1.0, max(0.0, (z + HEAP_HALF[1] - 1.0) / 14.0))
    return HEAP_HIGH * min(1.0, fx * 1.15) * min(1.0, fz * 1.15)


def _coal():
    """The coal stock: the anchor in the middle of its three cells by three, on the paving. A bin of
    two plank sides on iron stakes, west (towards the wall) and south; the heap runs out towards the
    track (north) and the yard (east), where a sleeper keeps it off the paving. A shovel in it."""
    m = M.Model(PREFIX + "coal")
    hx, hz = HEAP_HALF
    rnd = random.Random(1887)
    # the core, in steps under the lumps: the middle cell is filled to its top (the collision)
    m.box((-hx + 1.5, 0.0, -8.0), (8.0, 16.0, hz - 1.5), COAL_CORE, skip="d", seed=1)
    m.box((-hx + 1.5, 0.0, -13.0), (11.0, 10.0, hz - 1.5), COAL_CORE, skip="d", seed=2)
    m.box((-hx + 1.5, 0.0, -17.0), (15.0, 5.0, hz - 1.5), COAL_CORE, skip="d", seed=3)
    spots = []
    n, k = 14, 13
    for i in range(n):
        for j in range(k):
            x = -hx + 3.0 + i * (2.0 * hx - 5.0) / (n - 1) + rnd.uniform(-0.6, 0.6)
            z = -hz + 1.0 + j * (2.0 * hz - 3.5) / (k - 1) + rnd.uniform(-0.6, 0.6)
            top = _height(x, z)
            if top < 1.2 and rnd.random() < 0.55:
                continue                            # the edge is ragged
            spots.append((x, max(0.0, top - 1.8 + rnd.uniform(-0.7, 0.7)), z))
    _lumps(m, rnd, spots)
    for x, z in ((17.5, -18.5), (20.5, -12.0), (12.0, -21.5), (21.5, 4.0), (4.0, -22.0), (-9.0, -21.0)):
        _lumps(m, rnd, [(x, 0.0, z)])               # a few that have rolled off
    # the bin: planks on edge, three high, on stakes of old rail
    for row in range(3):
        y = 4.3 * row
        m.box((-hx, y, -hz + 3.0), (-hx + 1.5, y + 4.0, hz), WOOD if row % 2 else WOOD_L, grain="z", seed=10 + row)
        m.box((-hx, y, hz - 1.5), (hx - 2.0, y + 4.0, hz), WOOD_L if row % 2 else WOOD, grain="x", seed=13 + row)
    for x, z in ((-hx - 0.9, -hz + 5.0), (-hx - 0.9, 0.0), (-hx - 0.9, hz - 4.0)):
        m.box((x, 0.0, z - 0.8), (x + 0.9, 14.0, z + 0.8), IRON_D, grain="y", seed=16)
        for y in (2.0, 6.3, 10.6):
            _rivet(m, x, y, z, "-x", proud=0.3)
    for x in (-hx + 5.0, -2.0, hx - 6.0):
        m.box((x - 0.8, 0.0, hz), (x + 0.8, 14.0, hz + 0.9), IRON_D, grain="y", seed=17)
        for y in (2.0, 6.3, 10.6):
            _rivet(m, x, y, hz + 0.9, "z", proud=0.3)
    m.box((hx - 1.5, 0.0, -hz + 4.0), (hx + 1.0, 2.5, hz - 1.5), WOOD, grain="z", seed=18)       # the sleeper on the east side
    for z in (-hz + 6.0, hz - 4.0):
        _rivet(m, hx - 0.25, 2.5, z, "y", mat=IRON_D, proud=0.4)                                 # its two spikes
    # the shovel, where the last man left it: the blade in the coal, the handle up
    a, b = (9.0, 5.5, -9.5), (13.5, 21.0, -6.5)
    m.beam(a, b, 1.0, 1.0, WOOD_L, seed=20)
    m.box((a[0] - 2.5, 1.0, a[2] - 0.5), (a[0] + 2.5, 6.5, a[2] + 0.5), IRON, rot=("x", -16.0, a), seed=21)
    m.box((b[0] - 1.6, b[1] - 0.4, b[2] - 0.5), (b[0] + 1.6, b[1] + 0.6, b[2] + 0.5), WOOD, seed=22)     # the D of the handle
    return m


# --- the weighbridge ------------------------------------------------------------------------------------
def _scale():
    """The weighbridge: the anchor in the middle of its plate, on the bed, the track along x. The
    plate lies under the rails (their heads stand out of it) in a frame; a cover runs from it to the
    pillar on the south side, under which the lever goes; the pillar carries the dial on its east face."""
    m = M.Model(PREFIX + "scale")
    hx, hz = PLATE_HALF
    m.box((-hx, 0.0, -hz), (hx, 0.7, hz), IRON, grain="x", seed=1)
    for s in (-1, 1):
        a, b = sorted((s * hz, s * (hz + 0.7)))
        m.box((-hx - 0.7, 0.0, a), (hx + 0.7, 0.85, b), IRON_D, grain="x", seed=2)                # the frame
        a, b = sorted((s * hx, s * (hx + 0.7)))
        m.box((a, 0.0, -hz), (b, 0.85, hz), IRON_D, grain="z", seed=3)
        for z in (-GAUGE, GAUGE):
            m.box((s * hx - 0.2, 0.7, z - RAIL - 0.1), (s * hx + 0.2, RAIL_UP + 0.04, z + RAIL + 0.1), PLATE, seed=4)   # the rails' joints
        for x in (-hx + 1.5, -5.0, 5.0, hx - 1.5):
            _rivet(m, x, 0.7, s * (hz - 1.0), "y", proud=0.25)
        for x in (-9.0, 9.0):
            m.box((x - 1.4, 0.7, s * 2.5 - 0.9), (x + 1.4, 0.9, s * 2.5 + 0.9), IRON_D, seed=5)   # the lids over the knife edges
            m.box((x - 0.5, 0.9, s * 2.5 - 0.25), (x + 0.5, 1.1, s * 2.5 + 0.25), HEAD, seed=6)
    z = PILLAR
    m.box((-1.6, 0.0, hz + 0.7), (1.6, 0.5, z - 6.0), IRON, grain="z", seed=7)                    # the cover over the lever
    for at in (hz + 1.8, z - 7.0):
        _rivet(m, 0.0, 0.5, at, "y", proud=0.25)
    m.box((-6.0, 0.0, z - 6.0), (6.0, 3.0, z + 6.0), IRON_D, seed=8)                              # the pillar: its foot,
    for x in (-4.8, 4.8):
        for dz in (-4.8, 4.8):
            _rivet(m, x, 3.0, z + dz, "y", mat=HEAD, proud=0.4)
    m.box((-3.0, 3.0, z - 3.0), (3.0, 13.5, z + 3.0), IRON, grain="y", seed=9)                    # its shaft,
    m.box((3.0, 5.0, z - 1.8), (3.3, 11.5, z + 1.8), IRON_D, seed=10)                             # the shaft's door and its knob
    m.box((3.3, 8.0, z + 0.8), (3.7, 8.8, z + 1.4), BRASS, seed=11)
    m.box((-3.6, 13.0, z - 3.6), (3.6, 13.8, z + 3.6), IRON_D, seed=12)                           # the collar
    x, y = DIAL
    m.tube("x", (y, z), -3.0, x, DIAL_R + 0.9, IRON, sides=12, seed=13)                           # and the drum of the dial
    m.tube("x", (y, z), x, x + 0.2, DIAL_R, WHITE, sides=12, seed=14)
    m.ring("x", (x + 0.3, y, z), DIAL_R + 0.45, 0.9, 0.6, BRASS, sides=12, seed=15)
    for k in range(7):                              # the marks, from the zero round by the top
        with m.turned(("x", ZERO - 45.0 * k), about=(x, y, z)):
            m.box((x + 0.2, y + DIAL_R - 1.1, z - 0.2), (x + 0.28, y + DIAL_R - 0.2, z + 0.2), PLATE, seed=16)
    m.box((-1.0, y + DIAL_R + 0.9, z - 1.0), (1.0, y + DIAL_R + 1.9, z + 1.0), IRON_D, seed=17)   # the cap
    return m


def _needle():
    """The dial's needle: the anchor on its pivot; it stands at the zero."""
    m = M.Model(PREFIX + "needle")
    with m.turned(("x", ZERO)):
        m.box((0.0, -0.9, -0.22), (0.12, DIAL_R - 0.9, 0.22), RED, seed=1)
        m.box((0.0, -1.3, -0.45), (0.12, -0.7, 0.45), RED, seed=2)                                # its tail
    m.tube("x", (0.0, 0.0), 0.0, 0.3, 0.55, BRASS, sides=6, seed=3)
    return m


def weighing():
    """The ticks of the rake's cycle at which its first wheel rolls onto the plate and its last one
    off again: the same wheel both times, the one that leads on the way west."""
    lead = (COUPLED / 2.0 + 6.0) * PX               # from the rake's middle to that axle
    at = (SCALE_X + PLATE_HALF[0] * PX) - (REST_X - lead)       # where the rake is (blocks east of its rest) with the axle on the plate's east end
    out, here = [], 0.0
    for start, to, ticks in moves():
        if min(here, to) <= at <= max(here, to):
            out.append(start + int(round(ticks * (at - here) / (to - here))))
        here = to
    on, off = out
    return on, off


# --- the stack ------------------------------------------------------------------------------------------
def _stack():
    """Spare sleepers in a crib, five courses crosswise, and north of it two lengths of rail on two
    bearers. The anchor in the middle of the crib, on the paving."""
    m = M.Model(PREFIX + "stack")
    rnd = random.Random(1889)
    for row in range(5):
        y = 3.2 * row
        for i, at in enumerate((-8.7, -2.9, 2.9, 8.7)):
            a, b = -11.0 + rnd.uniform(-0.6, 0.6), 11.0 + rnd.uniform(-0.6, 0.6)
            wood = WOOD if (row + i) % 3 else WOOD_L
            if row % 2:
                m.box((at - 2.1, y, a), (at + 2.1, y + 3.1, b), wood, grain="z", seed=10 + (row + i) % 4)
            else:
                m.box((a, y, at - 2.1), (b, y + 3.1, at + 2.1), wood, grain="x", seed=20 + (row + i) % 4)
    for x in (-9.0, 9.0):
        m.box((x - 1.5, 0.0, -18.5), (x + 1.5, 1.6, -13.0), WOOD, grain="z", seed=30)             # the bearers
    for z in (-17.2, -14.6):
        m.box((-22.0, 1.6, z - RAIL), (22.0, 1.6 + 2.0 * RAIL_UP, z + RAIL), IRON_D, faces={"u": HEAD}, grain="x", seed=31)
    return m


# --- the package ----------------------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _models():
    built = [_rail(PREFIX + "rail", LENGTH), _rail(PREFIX + "rail_short", 1), _rail(PREFIX + "rail_rope", LENGTH, rope=True),
             _stop(PREFIX + "stop"), _stop(PREFIX + "stop_sheave", sheave=True), _sheave(), _deck(), _pit(), _coal(),
             _scale(), _needle(), _stack()]
    built += _tub_models()
    return {m.name: m for m in built}


def models():
    return dict(_models())


def line_cells():
    """The cells (x, z) of the paving course the two lines lie in, and the table's seat."""
    tx, tz = TABLE
    bed = [(x, ROW) for x in range(A_WEST[0], A_WEST[1] + 1)] + [(x, ROW) for x in range(A_EAST[0], A_EAST[1] + 1)]
    bed += [(tx, z) for z in range(B_Z[0], B_Z[1] + 1)]
    seat = [(x, z) for x in range(tx - TABLE_HALF, tx + TABLE_HALF + 1) for z in range(tz - TABLE_HALF, tz + TABLE_HALF + 1)]
    return bed, seat


def kerb_cells():
    """The cells (x, z) beside the two lines and round the seat: where the kerb lies if the field's
    setts lie there."""
    bed, seat = line_cells()
    tx, tz = TABLE
    out = set()
    for x, z in bed:
        out.update([(x, z - 1), (x, z + 1)] if z == ROW and x != tx else [(x - 1, z), (x + 1, z)])
    reach = TABLE_HALF + 1
    out.update((x, z) for x in range(tx - reach, tx + reach + 1) for z in range(tz - reach, tz + reach + 1))
    return sorted(out - set(bed) - set(seat))


def _lengths(lo, hi):
    """The middles of the lengths of rail that cover the cells lo..hi of a line, and which model each
    is: whole lengths from the low end, single blocks for what is left."""
    out, at = [], float(lo)
    while at + LENGTH <= hi + 1:
        out.append((at + LENGTH / 2.0, "rail"))
        at += LENGTH
    while at < hi + 1:
        out.append((at + 0.5, "rail_short"))
        at += 1.0
    return out


def _run(leaves, there, back=0.0):
    """The moves of one run from `back` to `there` that sets off at tick `leaves`: a slow start, the
    haul, a slow stop. In the unit of there and back (blocks for the tubs)."""
    way = 1.0 if there > back else -1.0
    ease, ticks = EASE
    return [(leaves, back + way * ease, ticks), (leaves + ticks, there - way * ease, HAUL),
            (leaves + ticks + HAUL, there, ticks)]


def moves():
    """The rake's moves: (tick it sets off, blocks east of where it is placed, ticks it takes)."""
    return _run(LEAVES[0], -RUN) + _run(LEAVES[1], 0.0, -RUN)


def build(canvas, origin=(0, 0, 0)):
    """Lay the two lines and the table's seat into the paving, stand the models on them and set the
    tubs, the sheave and the table moving. Returns the number of display entities."""
    ox, oy, oz = origin
    kit = _models()
    first = len(canvas.entities)

    def put(name, x, y, z, yaw=0.0):
        view = M.FAR if PREFIX + name in FAR_MODELS else M.NEAR if PREFIX + name in NEAR_MODELS else VIEW
        canvas.add_entity(ox + x, oy + y, oz + z, M.display(kit[PREFIX + name], yaw=yaw, view=view))

    bed, seat = line_cells()
    for x, z in bed:
        canvas.set(ox + x, oy + PY, oz + z, BED)
    for x, z in seat:
        canvas.set(ox + x, oy + PY, oz + z, SEAT)
    if KERB:
        for x, z in kerb_cells():
            if canvas.name(ox + x, oy + PY, oz + z) == FIELD and canvas.get(ox + x, oy + FEET, oz + z) is None:
                canvas.set(ox + x, oy + PY, oz + z, CURB)

    mid = ROW + 0.5                                 # the middle of line A, and of the table
    tx = TABLE[0] + 0.5
    for x, name in _lengths(*A_WEST):
        put("rail_rope" if name == "rail" else name, x, FEET, mid)
    for x, name in _lengths(*A_EAST):
        put(name, x, FEET, mid)
    for z, name in _lengths(*B_Z):
        put(name, tx, FEET, z, yaw=90.0)

    put("stop_sheave", float(A_WEST[0]), FEET, mid)
    put("stop", A_EAST[1] + 1.0, FEET, mid, yaw=180.0)
    put("sheave", A_WEST[0] + SHEAVE_AT[0] * PX, FEET + SHEAVE_AT[1] * PX, mid)
    # the rope has gone round the sheave as far as the tubs have gone: west is the wheel's top going west
    degrees = math.degrees(1.0 / (SHEAVE * PX))
    MK.turn(canvas, "z", [(t, -d * degrees, n) for t, d, n in moves()], CYCLE, name=PREFIX + "sheave")

    head = FEET + RAIL_UP * PX                      # the rail heads: a tub's wheels stand on them
    put("rake", REST_X, head, mid)
    MK.slide(canvas, (1, 0, 0), moves(), CYCLE, name=PREFIX + "rake")

    put("pit", tx, FEET, mid)
    quarter = [(TABLE_TURNS[0], 90.0, QUARTER), (TABLE_TURNS[1], 0.0, QUARTER)]
    put("deck", tx, FEET, mid)
    MK.turn(canvas, "y", quarter, TABLE_CYCLE, name=PREFIX + "deck")
    put("tub", tx, head, mid)
    MK.turn(canvas, "y", quarter, TABLE_CYCLE, name=PREFIX + "deck_tub")
    canvas.set(ox + TABLE[0], oy + FEET, oz + TABLE[1], B.BARRIER)

    parked = A_EAST[0] + 1                          # the empty tub on the stub: the middle of its second cell
    put("tub_empty", parked + 0.5, head, mid)
    canvas.set(ox + parked, oy + FEET, oz + ROW, B.BARRIER)

    put("coal", HEAP[0] + 0.5, FEET, HEAP[1] + 0.5)
    canvas.set(ox + HEAP[0], oy + FEET, oz + HEAP[1], B.BARRIER)

    put("scale", SCALE_X, FEET, mid)
    put("needle", SCALE_X + (DIAL[0] + 0.45) * PX, FEET + DIAL[1] * PX, mid + PILLAR * PX)
    on, off = weighing()
    swing, weight, past = WEIGHT                    # clockwise for who reads the dial, from the east
    MK.turn(canvas, (1, 0, 0), [(on, -swing, 10), (on + 10, -weight, 8), (off, -past, 10), (off + 10, 0.0, 6)], CYCLE,
            name=PREFIX + "needle")
    canvas.set(ox + int(math.floor(SCALE_X)), oy + FEET, oz + ROW + 1, B.BARRIER)

    put("stack", STACK[0] + 0.5, FEET, STACK[1] + 0.5)
    canvas.set(ox + STACK[0], oy + FEET, oz + STACK[1], B.BARRIER)

    # the table's number, flat on the seat's south-east corner, read from the south
    nameplates.plate(canvas, NUMBER, (tx + 1.05, FEET + 0.01, mid + 1.25), origin=origin, turns=(("x", -90),))
    return len(canvas.entities) - first
