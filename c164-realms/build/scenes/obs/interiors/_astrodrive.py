"""A part of interiors/astroroom: the driving clock of the astrograph, on the south wall of the
small dome room (card plan/packages/interiors/astroroom.md: "at least one thing that moves: the
weight or the governor of the driving clock"; the room is c336's, this file c356's, 11-16).

The astrograph follows the comet all night, and what turns it is a clock driven by a weight. Its
works hang on the wall west of the plate desk, where the door looks at them:

  the works      a brass case on two iron brackets, a glazed opening in its front with the wheels
                 behind it, the winding drum on its west side
  the governor   on the case's top: a spindle with two brass balls, turning for ever. It is a model
                 of its own and is registered with the motion line (MK.spin, once in
                 MK.SCOPE_GOVERNOR_REV, as the great refractor's)
  the weight     three cast discs on a wire that runs from the drum up over a pulley under the
                 wall's head and down again, in the corner. It stands still: what a weight falls in
                 a night no eye sees (plan/parts/motion.md 2)

Two display entities. Nothing gives light. Both are shown in the astrograph's own light
(machines/astro.BRIGHTNESS), so the brass of the works is the brass of the instrument beside it in
a room kept dark.

    place(canvas, origin=(0, 0, 0)) -> the display entities placed
    models() -> {name: Model}

Where (scene coordinates): the wall face z 33.0 between x 11.0 and 12.0, from the floor (y 18) to
the head of the wall (y 20). Nothing reaches more than 6 pixels off the wall, east of x 12.0 or
west of the wall on x 11.0.
"""
import functools

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from ..props import _kit as K

try:
    from ..motion import _kit as MK
except ImportError:                     # the motion line is not in the tree: the governor stands still
    MK = None
try:
    from ..machines.astro import BRIGHTNESS
except ImportError:
    BRIGHTNESS = (10, 7)

PREFIX = "int_astroroom_"
PX = 1 / 16.0

AT = (11.5, 18.0, 33.0)                 # the point of the wall face on the floor, in the middle of the stretch
FACING = "north"                        # the way that face looks

BRASS, BRASS_D = K.BRASS, K.BRASS_D
IRON, IRON_D = K.IRON, K.IRON_D
STEEL = P.mat("iron", base=5)
COPPER = K.COPPER
WIRE = K.flat("iron", 1)

# pixels; x along the wall (the model's +x is the west of the room: the wall looks north), y from
# the floor, z out of the wall
CASE = (-5.5, 1.5, 15.0, 21.0, 0.75, 5.0)       # the case: x from, to; y from, to; z from, to
LID = 0.5                                       # the plate on its top
SPINDLE = (-2.0, 3.0)                           # the governor's spindle: x, z
REACH = 2.0                                     # the balls from the spindle
BALL = 0.8
DRUM = (18.0, 2.9, 1.5)                         # the winding drum on the case's side: its axis (y, z), its radius
PULLEY = (4.15, 30.0, 1.75)                     # the pulley under the head of the wall: x, y, radius
LINE_Z = 2.0                                    # the plane the wire runs in
WEIGHT = (7.0, 2.5, 1.5)                        # the weight: its foot, the height of one disc, its radius
WINDOW = (                                      # the glazed opening in the case's front: a wheel of the train behind the glass
    "kgggk",
    "gkgkg",
    "ggsgg",
    "gkgkg",
    "kgggk",
)
WINDOW_COLOURS = dict(k=P.RAMPS["iron"][0], g=P.RAMPS["brass"][2], s=P.RAMPS["iron"][5])


def _works():
    """What stands still. Anchor: the point of the wall on the floor under the middle of the
    stretch; the wall is the plane z = 0."""
    name = PREFIX + "drive"
    m = M.Model(name)
    x0, x1, y0, y1, z0, z1 = CASE
    m.box((x0 - 0.5, y0 - 2.0, 0.0), (x1 + 0.5, y1 + 1.0, z0), IRON_D, skip="n")                # the plate on the wall
    for x in (x0 + 0.5, x1 - 1.5):
        m.box((x, y0 - 2.0, z0), (x + 1.0, y0, z1 - 0.5), IRON, grain="z")                      # the two brackets
    m.box((x0, y0, z0), (x1, y1, z1), BRASS, faces={"s": Sprite(name + "_window", list(WINDOW), WINDOW_COLOURS, back=BRASS)})
    m.box((x0 - 0.25, y1, z0 - 0.25), (x1 + 0.25, y1 + LID, z1 + 0.25), BRASS_D)
    dy, dz, dr = DRUM
    m.tube("x", (dy, dz), x1, x1 + 1.75, dr, BRASS_D, sides=8)                                  # the winding drum
    m.tube("x", (dy, dz), x1 + 1.75, x1 + 2.25, dr + 0.5, BRASS, sides=8)
    m.tube("x", (dy, dz), x1 + 2.25, x1 + 3.0, 0.5, STEEL, sides=4)                             # the square the key goes on
    px, py, pr = PULLEY
    m.box((px - 1.25, py - 1.5, 0.0), (px + 1.25, py + 1.5, 0.5), IRON_D, skip="n")             # the pulley's plate and stud
    m.tube("z", (px, py), 0.5, LINE_Z + 1.0, 0.4, STEEL, sides=4)
    m.tube("z", (px, py), LINE_Z - 0.5, LINE_Z + 0.5, pr, BRASS, sides=12)
    up, down = px - pr, px + pr                                                                 # the two runs of the wire
    m.box((up - 0.2, dy + dr, LINE_Z - 0.2), (up + 0.2, py, LINE_Z + 0.2), WIRE)
    foot, high, wr = WEIGHT
    top = foot + 3.0 * high + 0.5
    m.box((down - 0.2, top + 1.0, LINE_Z - 0.2), (down + 0.2, py, LINE_Z + 0.2), WIRE)
    m.tube("y", (down, LINE_Z), top, top + 1.0, 0.5, STEEL, sides=4)                            # the weight's eye
    m.tube("y", (down, LINE_Z), foot, top, wr - 0.5, IRON_D, sides=8)                           # its rod, and three discs on it
    for i in range(3):
        m.tube("y", (down, LINE_Z), foot + i * (high + 0.25), foot + i * (high + 0.25) + high, wr, IRON, sides=8)
    return m


def _governor():
    """The fly-ball governor: what turns. Anchor: the foot of its spindle; it spins about y, and
    the middle of its box is on the spindle (plan/parts/motion.md, rule 4)."""
    m = M.Model(PREFIX + "governor")
    m.tube("y", (0.0, 0.0), 0.0, 0.75, 1.25, BRASS_D, sides=8)
    m.tube("y", (0.0, 0.0), 0.75, 6.0, 0.4, STEEL, sides=4)
    m.tube("y", (0.0, 0.0), 2.25, 3.0, 0.8, COPPER, sides=8)                                    # the sleeve the arms lift
    m.tube("y", (0.0, 0.0), 5.75, 6.5, 0.8, BRASS_D, sides=8)
    for side in (-1.0, 1.0):
        m.rod((0.0, 6.0, 0.0), (side * REACH, 3.5, 0.0), 0.25, BRASS_D, sides=4)
        m.rod((0.0, 2.6, 0.0), (side * REACH, 3.5, 0.0), 0.25, BRASS_D, sides=4)
        m.ball((side * REACH, 3.25, 0.0), BALL, BRASS, sides=8, layers=3)
    return m


@functools.lru_cache(maxsize=None)
def _models():
    made = (_works(), _governor())
    return {m.name: m for m in made}


def models():
    return dict(_models())


def place(canvas, origin=(0, 0, 0), at=AT, facing=FACING):
    """Hang the driving clock on the wall; returns the number of display entities (2).

    at is the point of the wall face on the floor under the middle of the works, facing the way
    that face looks. The governor is registered with the motion line as it is placed.
    """
    own = _models()
    yaw = K.FACING[facing]
    n = K.put(canvas, own[PREFIX + "drive"], at, mount="wall", facing=facing, origin=origin, brightness=BRIGHTNESS)
    off = K.turn(yaw, (SPINDLE[0] * PX, (CASE[3] + LID) * PX, SPINDLE[1] * PX))
    n += K.put(canvas, own[PREFIX + "governor"], tuple(at[i] + off[i] for i in range(3)), yaw=yaw, origin=origin,
               brightness=BRIGHTNESS)
    if MK is not None:
        MK.spin(canvas, "y", MK.SCOPE_GOVERNOR_REV)
    return n
