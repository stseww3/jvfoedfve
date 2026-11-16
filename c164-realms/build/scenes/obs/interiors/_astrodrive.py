"""A part of interiors/astroroom: the driving clock of the astrograph, on the south wall of the
small dome room (card plan/packages/interiors/astroroom.md: "at least one thing that moves: the
weight or the governor of the driving clock"; the room is c336's, this file c356's, 11-16).

The astrograph follows the comet all night, and what turns it is a clock driven by a weight. Its
works hang on the wall west of the plate desk, where the door looks at them:

  the works      a brass case on two iron brackets, an opening in its front, the winding drum on
                 its west side
  the train      a wheel and its pinion in the opening, a model each: they turn, slowly, against
                 each other (the pinion 7 turns to the wheel's 4, as their sizes are)
  the governor   over the case, at the height of the eye: a fly, two brass balls on a cross arm
                 on an arbor that comes out of the wall, turning for ever in the plane of the
                 wall (MK.spin, once in MK.SCOPE_GOVERNOR_REV, as the great refractor's). It was a
                 fly-ball governor on a spindle on the case's top and stood 5.8 pixels off the
                 wall: who stood in the niche's west cell had his head in it (a4's walk, c336
                 #79466). A fly in the wall's plane sweeps no depth
  the weight     three cast discs on a wire that runs from the drum up over a pulley under the
                 wall's head and down again, in the corner. It stands still: what a weight falls in
                 a night no eye sees (plan/parts/motion.md 2)

Four display entities. Nothing gives light. All are shown in the astrograph's own light
(machines/astro.BRIGHTNESS), so the brass of the works is the brass of the instrument beside it in
a room kept dark.

    place(canvas, origin=(0, 0, 0)) -> the display entities placed
    models() -> {name: Model}

Where (scene coordinates): the wall face z 33.0 between x 11.0 and 12.0, from the floor (y 18) to
the head of the wall (y 20). Nothing reaches more than DEEP, 3 pixels, off the wall: a walker
pressed against it has his shoulders and his head 3.2 pixels from it and his eye 4.8. Nothing
reaches east of x 12.0 or west of the wall on x 11.0.
"""
import functools

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from ..props import _kit as K

try:
    from ..motion import _kit as MK
except ImportError:                     # the motion line is not in the tree: the clock stands still
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
BRASS_L = P.mat("brass", base=4)
IRON, IRON_D = K.IRON, K.IRON_D
STEEL = P.mat("iron", base=5)
WIRE = K.flat("iron", 1)

# pixels; x along the wall (the model's +x is the west of the room: the wall looks north), y from
# the floor, z out of the wall
DEEP = 3.0                                      # the furthest anything stands off the wall
CASE = (-5.5, 1.5, 15.0, 21.0, 0.5, 2.5)        # the case: x from, to; y from, to; z from, to
LID = 0.5                                       # the plate on its top
FLY = (-2.0, 25.5)                              # the fly's arbor: x, y. 1.59 blocks over the floor: the eye is at 1.62
REACH = 2.5                                     # its balls from the arbor
BALL = 0.75
DRUM = (18.0, 1.5, 1.25)                        # the winding drum on the case's side: its axis (y, z), its radius
PULLEY = (4.15, 30.0, 1.75)                     # the pulley under the head of the wall: x, y, radius
LINE_Z = 1.5                                    # the plane the wire runs in
WEIGHT = (7.0, 2.5, 1.5)                        # the weight: its foot, the height of one disc, its radius
OPENING = 5                                     # the opening in the case's front, square and dark inside
WHEEL_T = 0.4                                   # a wheel of the train is this thick, on the case's front
# the two wheels of the train that stand in the opening: name, x, y, radius, spokes, ticks a turn
# (the sign is the way round: two wheels in mesh turn against each other, 7 to 4 as their radii)
WHEELS = (("wheel", -2.75, 18.25, 1.75, 4, 280), ("pinion", -0.4, 16.6, 1.0, 2, -160))


def _works():
    """What stands still. Anchor: the point of the wall on the floor under the middle of the
    stretch; the wall is the plane z = 0."""
    name = PREFIX + "drive"
    m = M.Model(name)
    x0, x1, y0, y1, z0, z1 = CASE
    m.box((x0 - 0.5, y0 - 2.0, 0.0), (x1 + 0.5, y1 + 1.0, z0), IRON_D, skip="n")                # the plate on the wall
    for x in (x0 + 0.5, x1 - 1.5):
        m.box((x, y0 - 2.0, z0), (x + 1.0, y0, z1 - 0.5), IRON, grain="z")                      # the two brackets
    dark = Sprite(name + "_opening", ["k" * OPENING] * OPENING, dict(k=P.RAMPS["iron"][0]), back=BRASS)
    m.box((x0, y0, z0), (x1, y1, z1), BRASS, faces={"s": dark})
    m.box((x0 - 0.25, y1, z0 - 0.25), (x1 + 0.25, y1 + LID, z1 + 0.25), BRASS_D)
    fx, fy = FLY                                                                                # the cock the fly's arbor runs in
    m.box((fx - 1.25, y1 + 1.0, 0.0), (fx + 1.25, fy + 1.25, z0), IRON_D, skip="n")
    m.tube("z", (fx, fy), z0, z0 + 0.5, 1.0, BRASS_D, sides=8)
    dy, dz, dr = DRUM
    m.tube("x", (dy, dz), x1, x1 + 1.75, dr, BRASS_D, sides=8)                                  # the winding drum
    m.tube("x", (dy, dz), x1 + 1.75, x1 + 2.25, dr + 0.25, BRASS, sides=8)
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
    """The fly: what spins. Anchor: the point of the wall its arbor comes out of; the arbor is the
    model's z, and the middle of its box is on it (plan/parts/motion.md, rule 4)."""
    m = M.Model(PREFIX + "governor")
    z = (CASE[4] + 0.5 + DEEP) / 2.0                                                            # the plane the arm turns in
    m.tube("z", (0.0, 0.0), CASE[4] + 0.5, DEEP, 0.4, STEEL, sides=4)
    m.tube("z", (0.0, 0.0), z - 0.6, z + 0.6, 0.9, BRASS_D, sides=8)                            # the hub
    m.box((-REACH, -0.3, z - 0.3), (REACH, 0.3, z + 0.3), BRASS_D, grain="x")                   # the cross arm
    for side in (-1.0, 1.0):
        m.ball((side * REACH, 0.0, z), BALL, BRASS, sides=8, layers=3)
    return m


def _wheel(name, radius, spokes):
    """A wheel of the train: a rim, `spokes` bars across it and its arbor's end. Anchor: the point
    of the wall behind its middle; it turns about z, on the case's front."""
    m = M.Model(PREFIX + name)
    z0 = CASE[5]
    z = z0 + WHEEL_T / 2.0
    m.ring("z", (0.0, 0.0, z), radius - 0.25, 0.5, WHEEL_T, BRASS_L, sides=8)
    for k in range(spokes):
        angle = 180.0 * k / spokes
        m.box((-radius + 0.4, -0.2, z0), (radius - 0.4, 0.2, z0 + WHEEL_T), BRASS_L, grain="x",
              rot=("z", angle, (0.0, 0.0, z)) if angle else None)
    m.tube("z", (0.0, 0.0), z0, DEEP, 0.4, STEEL, sides=4)
    return m


@functools.lru_cache(maxsize=None)
def _models():
    settle = getattr(K, "settle", None) or (lambda m: m)    # the kit has it from the assembly's a9f92259 on
    made = [_works(), _governor()] + [_wheel(name, radius, spokes) for name, _x, _y, radius, spokes, _t in WHEELS]
    return {m.name: settle(m) for m in made}


def models():
    return dict(_models())


def place(canvas, origin=(0, 0, 0), at=AT, facing=FACING):
    """Hang the driving clock on the wall; returns the number of display entities (4).

    at is the point of the wall face on the floor under the middle of the works, facing the way
    that face looks. The fly and the two wheels are registered with the motion line as they are
    placed.
    """
    own = _models()
    yaw = K.FACING[facing]

    def on_wall(x, y):
        off = K.turn(yaw, (x * PX, y * PX, 0.0))
        return tuple(at[i] + off[i] for i in range(3))

    def hang(name, pos):
        return K.put(canvas, own[PREFIX + name], pos, mount="wall", facing=facing, origin=origin, brightness=BRIGHTNESS)

    n = hang("drive", at)
    n += hang("governor", on_wall(*FLY))
    if MK is not None:
        MK.spin(canvas, "z", MK.SCOPE_GOVERNOR_REV)
    for name, x, y, _radius, _spokes, ticks in WHEELS:
        n += hang(name, on_wall(x, y))
        if MK is not None:
            MK.spin(canvas, "z", ticks)
    return n
