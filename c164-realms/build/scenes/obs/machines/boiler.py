"""machines/switchboard-boiler, the boilers of the power house (plan/ART-PLAN.md 5.3, 7.2;
plan/parts/A5-machines.md 2.6; card plan/packages/machines/switchboard-boiler.md). The switchboard
is machines/board.py.

ROUGH SET: the volumes where they stand, so that the room can be laid out round them. Rivets,
fittings and the fire come with the next commits.

What it is. Two shell boilers of riveted iron plate, each three blocks across and four long, lying
side by side on cast saddles: one in steam, one behind it. The fire door is in the front plate,
under the middle; the smoke leaves at the back and goes into the chimney's foot. On each shell a
steam dome with the safety valve.

Where they stand. In the north-east of the room (site/powerhouse.ROOM), beside the chimney's foot
and behind the two bays whose windows glow: their axes east-west, their fronts to the west, so
that whoever comes in by the wicket has the two fire doors on the left hand and the flywheel
straight ahead. The north boiler's flue goes straight into the west face of the chimney's foot,
the south one's turns north into its south face.

    x  the front plates stand in the plane x = FRONT_X; the shells lie east of it
    y  the floor is S.LOWER_GROUND; the shells' axes lie AXIS_H above it
    z  the axes: AXES_Z

Every model is drawn in blocks in a boiler's own frame: x from the front plate towards the back,
y up from the floor, z from the axis.
"""
import functools

from ..common import palette as P
from ..common import skeleton as S
from . import _powerkit as K

PREFIX = "mach_boiler_"

# --- where they stand (scene coordinates) -------------------------------------------------------------
FLOOR = float(S.LOWER_GROUND)           # -6.0
FRONT_X = 79.5                          # the plane of the front plates
AXES_Z = (24.0, 28.0)                   # the north boiler (on the middle of the chimney foot's west face), the south one
CHIMNEY_WEST = 84.0                     # the west face of the chimney's foot (site/powerhouse.TOWER)
CHIMNEY_SOUTH = 26.0                    # ... and its south face

# --- a boiler (its own frame, blocks) -----------------------------------------------------------------
R = 1.5                                 # the shell: three blocks across (the card)
LEN = 4.0                               # ... and four long
AXIS_H = 2.0                            # its axis over the floor: half a block of saddle under it
HOOPS = (0.5, 1.5, 2.5, 3.5)            # the lap of two rings of plate, along x
HOOP = 0.125                            # a lap is 2 texels wide and 1 proud
SADDLES = (1.0, 3.0)
DOOR_Y = (0.75, 1.75)                   # the fire door: a block square, its middle a block and a quarter up
DOOR_HALF = 0.5
DOME_X = 2.5                            # the steam dome's axis
DOME_R = 0.5
DOME_H = 0.75                           # its barrel over the shell's top
FLUE_Y = AXIS_H + 0.625                 # the flue's axis, in the upper half of the back plate
FLUE_R = 0.5
FLUE_TURN = 1.5                         # the south boiler's flue runs this far east before it turns north

# --- for the others (scene coordinates) ---------------------------------------------------------------
# Where the fire doors throw their light: the cell before each door. The sky line sets the level.
LIGHTS = [((FRONT_X - 1.5, FLOOR + 1.5, z), 10) for z in AXES_Z]
# The stop valve on top of each steam dome: the steam pipes start here (props/pipes, interiors).
STEAM_OUT = [(FRONT_X + DOME_X, FLOOR + AXIS_H + R + DOME_H + 0.5, z) for z in AXES_Z]
# Boxes (x0, y0, z0, x1, y1, z1) in which something of the set stands: nothing else goes there.
KEEP_CLEAR = tuple((FRONT_X - 0.5, FLOOR, z - R - 0.25, CHIMNEY_WEST + 2.0, FLOOR + AXIS_H + R + 1.75, z + R + 0.25)
                   for z in AXES_Z)

# --- materials (the palette's, and nothing else) ------------------------------------------------------
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
BRASS = P.mat("brass")
RED = P.mat("signal")
FIRE = P.mat("glow")


def _body():
    d = K.Draw(PREFIX + "body", scale=2.0)
    d.tube("x", (AXIS_H, 0.0), 0.0, LEN, R, IRON_D, sides=16)
    for x in HOOPS:
        d.ring("x", (x, AXIS_H, 0.0), R, HOOP, HOOP, IRON, sides=16)
    for x in SADDLES:
        d.box((x - 0.125, 0.0, -1.25), (x + 0.125, 1.0, 1.25), IRON)
        d.box((x - 0.25, 0.0, -1.375), (x + 0.25, 0.125, 1.375), IRON)
    return d


def _front():
    d = K.Draw(PREFIX + "front", scale=2.0)
    d.tube("x", (AXIS_H, 0.0), -0.0625, 0.0, R + 0.0625, IRON, sides=16)
    d.box((-0.1875, DOOR_Y[0] - 0.125, -DOOR_HALF - 0.125), (-0.0625, DOOR_Y[1] + 0.125, DOOR_HALF + 0.125), IRON)
    d.box((-0.25, DOOR_Y[0], -DOOR_HALF), (-0.1875, DOOR_Y[1], DOOR_HALF), FIRE, emit=15, shade=False)
    d.box((-0.3125, DOOR_Y[0] + 0.125, -DOOR_HALF + 0.125), (-0.25, DOOR_Y[1] - 0.125, DOOR_HALF - 0.125), IRON_D)
    d.box((-0.125, 0.25, -0.375), (-0.0625, 0.5, 0.375), IRON_D)                    # the ash pit's damper
    return d


def _dome():
    d = K.Draw(PREFIX + "dome", scale=1.0)
    top = AXIS_H + R
    d.tube("y", (DOME_X, 0.0), top - 0.125, top + DOME_H, DOME_R, IRON_D, sides=12)
    d.ball((DOME_X, top + DOME_H, 0.0), DOME_R, IRON_D, sides=12, layers=3, squash=0.5, part=(0.0, 1.0))
    d.ring("y", (DOME_X, top + 0.0625, 0.0), DOME_R + 0.0625, 0.125, 0.125, BRASS, sides=12)
    d.tube("y", (DOME_X, 0.0), top + DOME_H + 0.2, top + DOME_H + 0.5, 0.125, BRASS, sides=8)
    d.box((DOME_X - 0.0625, top + DOME_H + 0.5, -0.5), (DOME_X + 0.0625, top + DOME_H + 0.5625, 0.125), IRON)
    d.box((DOME_X - 0.125, top + DOME_H + 0.3125, -0.5625), (DOME_X + 0.125, top + DOME_H + 0.5, -0.375), RED)
    return d


def _flue(name, turn):
    """The flue from the back plate: straight on to the chimney, or east by `turn` and then north."""
    d = K.Draw(PREFIX + name, scale=2.0)
    if not turn:
        d.tube("x", (FLUE_Y, 0.0), LEN, FRONT_X + LEN + 0.5 - FRONT_X, FLUE_R, IRON_D, sides=12)
        return d
    reach = AXES_Z[1] - CHIMNEY_SOUTH                                               # 2.0, to the south face
    d.tube("x", (FLUE_Y, 0.0), LEN, LEN + turn + FLUE_R, FLUE_R, IRON_D, sides=12)
    d.tube("z", (LEN + turn, FLUE_Y), -reach, FLUE_R, FLUE_R, IRON_D, sides=12)
    return d


@functools.lru_cache(maxsize=None)
def _drawn():
    built = [_body(), _front(), _dome(), _flue("flue", 0.0), _flue("flue_turn", FLUE_TURN)]
    return {d.m.name[len(PREFIX):]: d for d in built}


def models():
    return {d.m.name: d.m for d in _drawn().values()}


def build(canvas, origin=(0, 0, 0)):
    """Place the two boilers; returns the number of display entities."""
    drawn = _drawn()
    n = 0
    for i, z in enumerate(AXES_Z):
        at = (FRONT_X, FLOOR, z)
        for name in ("body", "front", "dome", "flue_turn" if i else "flue"):
            n += K.place(canvas, drawn[name], at, origin)
    return n
