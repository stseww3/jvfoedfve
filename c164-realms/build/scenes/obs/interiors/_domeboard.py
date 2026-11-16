"""interiors/_domeboard -- the switchboard of the dome's drive, on the east wall of the dome room.
Part of the package interiors/domeroom (card plan/packages/interiors/domeroom.md); domeroom.py
calls it.

One display model on the lining of the east axis: a slab of slate in an angle-iron frame, three wide
and two high, no more than four pixels off the wall, so the floor in front of it stays free. On it,
from the top: a voltmeter and an ammeter in brass cases, between them three pilot lamps over the
maker's plate; under them three knife switches, the main one in the middle (two blades far apart,
the bar of its handle across them) and a smaller one either side, for the motor that turns the dome
and for the one that draws the slit's leaves. All three are shut: the slit stands open and the dome
follows the telescope.

The room is dark (sky light 6 to 9), so the board reads by what is light on dark: brass and two
white dials on slate. What glows is small and third in rank (plan 3.2; sky/lights): two of the three
pilot lamps, amber, their brightest pixel under the telescope's red lamp; and the luminous marks of
the two dials, the only green in the room. Nothing on it is red.

    models()                -> {name: Model}
    place(canvas, origin)   -> the number of display entities (one)
    GLOW                    -> the middle of each lit pilot lamp, scene coordinates in blocks (no origin)
"""
import functools
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..props import _kit as K

PREFIX = "int_domeroom_"
NAME = PREFIX + "board"

# where it hangs: the lining's face on the east axis, the three columns z -1..1, two rows from the floor
FACE_X = 15.0                                   # the plane of the lining's west face
SPAN_Z = (S.DOME_CENTRE[1] - 1.0, S.DOME_CENTRE[1] + 2.0)
SPAN_Y = (float(S.ROOF_STAND), S.ROOF_STAND + 2.0)
FACING = "west"
# the light the model is drawn in, (sky, block): the room's own level at its brightest, so that the
# board is seen as far as the lining round it is and no further
BRIGHTNESS = (9, 0)
LEVEL = 3                                       # the light the pilot lamps may give (sky/lights)

# the model's frame: x to the right of the one who looks at it, y up from the middle of the board,
# z out of the wall (0 on the lining)
HALF_W, HALF_H = 23.0, 15.0                     # the frame's outside: 46 x 30, a pixel of lining left round it
BAR = 2.0                                       # the angle iron's width
SLAB_Z, FRAME_Z = 1.5, 2.5                      # the slab's face, the frame's
METER = (13.5, 6.5)                             # |x| and y of the two meters' middles
LAMPS = (-5.0, 0.0, 5.0)                        # x of the three pilot lamps
LAMP_Y = 9.0
LIT = (True, False, True)                       # mains on, the dome's motor at rest, the slit drawn open

LINING = B.FLOOR_WOOD.block                     # the boards of the drum's lining (domeroom.DEAL)
SLATE = P.mat("slate", base=2, noise=0.16)
HANDLE = P.mat("dark_wood", base=3)             # the bar one pulls a knife switch by: turned wood, which
#                                                 shows on slate where ebonite would be a hole in it
POINTER = K.flat("iron", 0)                     # a meter's hand
BOLT = K.flat("iron", 5)
PLATE = K.flat("brass", 3)
INK = P.RAMPS["iron"][1]
FACE, FACE_D = P.RAMPS["porcelain"][3], P.RAMPS["porcelain"][2]
MARK = P.RAMPS["iron"][5]
LUME = P.RAMPS["phosphor"][2]
AMBER, AMBER_D = P.RAMPS["glow"][1], P.RAMPS["glow"][0]
OUT, OUT_D = P.RAMPS["brass"][1], P.RAMPS["brass"][0]
DIAL_COLOURS = dict(c=FACE, d=FACE_D, k=INK, m=MARK, h=P.RAMPS["iron"][0], b=P.RAMPS["brass"][3], g=LUME)

# a meter's dial, nine pixels across: the scale along the upper rim, three luminous marks. The hand is
# not painted: it is a strip one pixel wide in front of the dial, at its true angle, pivoted two
# pixels under the middle
DIAL = [
    "..mcgcm..",
    ".mcccccm.",
    "gcccccccg",
    "ccccccccc",
    "ccccccccc",
    "ccccccccc",
    "ccccccccc",
    ".dcccccd.",
    "..ddddd..",
]
PIVOT = -2.0                                    # the hand's pivot, under the dial's middle
# degrees from upright (to the right) and the length of each hand: the voltmeter's stands two thirds
# up its scale, the ammeter's lies near the foot of its own -- the motors are at rest
VOLTS, AMPS = (28.0, 5.6), (-52.0, 5.0)
# the maker's plate: two lines of engraving
MAKER = [
    "bbbbbbbbbb",
    "bkkbkkkbkb",
    "bbbbbbbbbb",
    "bbkkkkbkbb",
    "bbbbbbbbbb",
]


def _sprite(name, rows, **colours):
    return Sprite(PREFIX + "board_" + name, rows, colours)


def _meter(m, x, y, hand):
    """A round meter: a brass case on the slab, a bezel, the painted dial, in front of it a plate
    with only its luminous marks, which glows, and the hand."""
    z = SLAB_Z
    m.tube("z", (x, y), z, z + 1.25, 6.0, K.BRASS_D, sides=16, cap=K.flat("brass", 1))
    m.ring("z", (x, y, z + 1.75), 5.0, 1.5, 1.0, K.BRASS, sides=16)
    m.box((x - 4.5, y - 4.5, z + 1.5), (x + 4.5, y + 4.5, z + 1.75), K.flat("porcelain", 3), skip="nudew",
          faces={"s": _sprite("dial", DIAL, **DIAL_COLOURS)})
    m.box((x - 4.5, y - 4.5, z + 1.75), (x + 4.5, y + 4.5, z + 1.85), K.flat("phosphor", 2), skip="nudew",
          faces={"s": _sprite("dial_lume", ["".join(ch if ch == "g" else "." for ch in row) for row in DIAL],
                              g=LUME)}, emit=15, shade=False)
    lean, length = math.radians(hand[0]), hand[1]
    foot = (x, y + PIVOT, z + 2.0)
    m.beam(foot, (x + length * math.sin(lean), y + PIVOT + length * math.cos(lean), z + 2.0), 0.25, 1.0, POINTER)
    m.box((x - 0.5, y + PIVOT - 0.5, z + 1.85), (x + 0.5, y + PIVOT + 0.5, z + 2.25), K.flat("brass", 4))


def _lamp(m, x, y, lit):
    """A pilot lamp: a brass collar and a jewel two pixels across. Lit, the jewel is amber with one
    brighter pixel; out, it is a dark bead."""
    z = SLAB_Z
    m.tube("z", (x, y), z, z + 1.0, 2.0, K.BRASS, sides=8, cap=K.flat("brass", 2))
    a, b = (AMBER, AMBER_D) if lit else (OUT, OUT_D)
    jewel = _sprite("lamp_lit" if lit else "lamp_out", ["ab", "bb"], a=a, b=b)
    side = K.flat("glow", 0) if lit else K.flat("brass", 0)
    m.box((x - 1.0, y - 1.0, z + 1.0), (x + 1.0, y + 1.0, z + 1.5), side, skip="n", faces={"s": jewel},
          emit=15 if lit else 0, shade=not lit)


def _knife(m, x, foot, reach, tall):
    """A two-pole knife switch, shut: the hinge posts at the foot, the jaws under the top, the two
    blades standing edge-on through them and, across their free ends, the bar one pulls them by. x is
    its middle, `reach` the middle of a blade off it, `tall` its height."""
    z = SLAB_Z
    for s in (-1.0, 1.0):
        c = x + s * reach
        for y in (foot, foot + tall - 5.0):
            m.box((c - 1.5, y, z), (c + 1.5, y + 2.0, z + 1.5), K.BRASS_D)               # hinge post, jaw
        m.box((c - 0.5, foot + 1.0, z + 0.25), (c + 0.5, foot + tall - 1.0, z + 2.25), K.BRASS, grain="y",
              faces={"s": K.flat("brass", 4)})                                           # the blade's edge
    m.box((x - reach - 1.5, foot + tall - 2.0, z + 1.0), (x + reach + 1.5, foot + tall, z + 2.5), HANDLE,
          grain="x")


def _fuse(m, x, foot):
    """A porcelain fuse between two brass clips."""
    z = SLAB_Z
    m.box((x - 1.0, foot + 1.0, z), (x + 1.0, foot + 5.0, z + 1.5), K.flat("porcelain", 1), grain="y",
          faces={"s": K.flat("porcelain", 2)})
    for y in (foot, foot + 5.0):
        m.box((x - 1.0, y, z), (x + 1.0, y + 1.0, z + 1.5), K.BRASS_D, faces={"s": K.flat("brass", 3)})


def _board():
    """The switchboard. 46 px wide, 30 px tall, 4 px off the wall. Anchor: the point of the wall
    behind the middle of the board."""
    m = M.Model(NAME)
    w, h = HALF_W, HALF_H
    m.box((-w + BAR, -h + BAR, 0.0), (w - BAR, h - BAR, SLAB_Z), SLATE, skip="n")
    for y in (-h, h - BAR):
        m.box((-w, y, 0.0), (w, y + BAR, FRAME_Z), K.IRON, skip="n", grain="x")
    for x in (-w, w - BAR):
        m.box((x, -h + BAR, 0.0), (x + BAR, h - BAR, FRAME_Z), K.IRON, skip="nud", grain="y")
    for x in (-w + BAR + 1.5, w - BAR - 1.5):                                            # the slab's bolts
        for y in (-h + BAR + 1.5, h - BAR - 1.5):
            m.box((x - 0.5, y - 0.5, SLAB_Z), (x + 0.5, y + 0.5, SLAB_Z + 0.5), BOLT)
    _meter(m, -METER[0], METER[1], VOLTS)
    _meter(m, METER[0], METER[1], AMPS)
    for x, lit in zip(LAMPS, LIT):
        _lamp(m, x, LAMP_Y, lit)
    m.box((-5.0, 1.0, SLAB_Z), (5.0, 6.0, SLAB_Z + 0.5), PLATE, skip="n", faces={"s": _sprite(
        "maker", MAKER, b=P.RAMPS["brass"][3], k=P.RAMPS["brass"][0])})
    _knife(m, 0.0, -12.0, 3.5, 12.0)
    for x in (-METER[0], METER[0]):
        _knife(m, x, -12.0, 2.0, 10.0)
    for x in (-8.0, 8.0):
        _fuse(m, x, -11.0)
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {m.name: m for m in (_board(),)}


def models():
    """{name: Model} what the board is made of."""
    return dict(_models())


MIDDLE = (FACE_X, (SPAN_Y[0] + SPAN_Y[1]) / 2.0, (SPAN_Z[0] + SPAN_Z[1]) / 2.0)


def _scene(x, y, z):
    """A point of the model's frame in scene coordinates (blocks): the board looks west, so its x
    runs south and its z west."""
    return (MIDDLE[0] - z / 16.0, MIDDLE[1] + y / 16.0, MIDDLE[2] + x / 16.0)


GLOW = tuple(_scene(x, LAMP_Y, SLAB_Z + 1.5) for x, lit in zip(LAMPS, LIT) if lit)


def cells():
    """The cells of the lining the board hangs on: [(x, y, z)], scene coordinates."""
    x = int(FACE_X)
    return [(x, y, z) for y in range(int(SPAN_Y[0]), int(SPAN_Y[1])) for z in range(int(SPAN_Z[0]), int(SPAN_Z[1]))]


def place(canvas, origin=(0, 0, 0), brightness=BRIGHTNESS):
    """Board up the lining behind the board and hang it there. Returns the number of display
    entities."""
    for x, y, z in cells():
        canvas.set(origin[0] + x, origin[1] + y, origin[2] + z, LINING)
    return K.put(canvas, _models()[NAME], MIDDLE, mount="wall", facing=FACING, origin=origin,
                 brightness=brightness)
