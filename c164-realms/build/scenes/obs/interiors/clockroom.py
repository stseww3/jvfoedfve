"""Work package interiors/clockroom: the clock room of the time tower, behind the four dials
(card: plan/packages/interiors/clockroom.md).

The room is the upper part of the tower's well (main/tower: WELL_X/Z, 5 x 5 inside a wall one block
thick). Its floor is the row under ROOM_FLOOR (y 23, the top at 24.0), its ceiling the underside of
the lookout's floor (31.0). The iron plates behind the four dial recesses stand one block into the
well in the rows 26..28, so the room is a low gallery one block wide, two rows high, round a shaft
of 3 x 3 that is open to the ceiling. The movement stands in that shaft, and whoever walks the
gallery looks at it from all four sides.

The way up is the tower's (tower.way_up(), called from build()): the door of the roof walk stands
open, a ladder climbs the north-west corner of the well to the hatch in the floor. Nothing is
clicked on the way.

The star piece is the tower clock's movement, a flat bed: two cast-iron girders on two piers, three
trains side by side along x (strike, going, chime: barrel, great wheel, second wheel; a fly on each
of the outer two), the going train under an A-frame in the middle. Its front looks north, to the
side one arrives on: the setting dial (it shows the tower's time), the winding crank, and the small
electric winding motor with its worm, bolted on later. Its back looks south: the escape wheel, the
pallets over it, the crutch, and the long pendulum, which hangs behind the bed and goes down
through the floor; its bob swings under the ceiling of the tower's lobby. The floor under the bed
and where the pendulum goes through is whole iron plate: the slot is a model on it, above and
below, so no light gets down and nobody can fall. From the going
train an upright shaft rises to a nest of bevels on a beam at the height of the dials' centres, and
four leading-off rods run from there to the four dials: one movement, four dials.

The dials' backs are models on the iron plates (the plates stay iron: no light gets out by a dial):
a disc of opal glass, lit from behind, with the minute track, the hour marks and the two hands as
shadows, mirrored, the motion work on its middle. They are the room's main light. Three wire ropes
rise from the barrels to sheaves under the ceiling and drop through the floor in three corners;
their weights hang in the corners of the lobby. The time ball has a small braked drum on the bed's
east end and a rope that leaves through the ceiling.

What moves (motion/_kit): the pendulum and the pallets swing together, there and back in two beats
of the master clock's pendulum (a rod four times as long); the escape wheel turns one tooth for
every swing.

Light. Nothing here adds a colour. The sources are offered to the light line (sky/_lightkit):
one in front of each dial's back (rank 2), and one at each of three caged lamps (rank 3): on the
south wall behind the movement, over the hatch, and in the lobby beside the ladder's foot, so
that the way up has light all the way. The movement takes no source of its own: its pieces are shown as the dials light
them (MOVEMENT_LIGHT). No slit window may be brighter outside than without the room. The tops of
the slits' glass lie in the floor's row, under thin plates that light passes; over the two dark
slits (north and south) a cabinet stands on the plate instead, a whole block: the switchboard of
the winding motor, and a chest of drawers. Over the two lit slits the level stays under what
their glass has from the tower's own sources. The test scene counts both, the cells outside and
the light on the walk: python -m scenes.obs_int_clockroom.
"""
import functools
import math

import numpy as np

from artkit import models as M
from artkit.blocks import st
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..main import tower as T
from ..props import _kit as K
from ..props import lamps

MOVED_IN = True
NAME = "interiors/clockroom"
PREFIX = "int_clockroom_"
PX = 1 / 16.0
TIME = tuple(S.CLOCK)                               # (7, 55): what the setting dial and the shadows show

# ---- the room (main/tower) -----------------------------------------------------------------------------
CX, CZ = T.CX, T.CZ                                 # 13, -30: the middle column
AXIS = T.AXIS                                       # (13.5, -29.5): the tower's axis
WELL_X, WELL_Z = tuple(T.WELL_X), tuple(T.WELL_Z)   # 11 .. 15 and -32 .. -28
FLOOR_TOP = float(T.ROOM_FLOOR)                     # 24.0
FLOOR_Y = int(FLOOR_TOP) - 1                        # 23: the floor's row
FEET = int(FLOOR_TOP)                               # 24: the first clear row
CEILING = float(T.SHAFT_TOP)                        # 31.0: the underside of the lookout's floor
DIAL = T.DIAL_BACKS["east"][1]                      # 27.5: the height of the dials' centres
HATCH = tuple(T.LADDER_AT)                          # (11, -32): the corner the ladder comes up in
SLOT = (CX, CZ + 1)                                 # (13, -29): the pendulum's slot in the floor
PIERS = ((CX - 1, CZ), (CX + 1, CZ))                # the two piers the bed lies on
# the two cabinets over the tops of the dark slits: column, the panel it is (B.PANELS), the way it looks
CABINETS = (((CX, WELL_Z[0]), "knife_switch", "south"), ((CX, WELL_Z[1]), "drawers", "north"))
LOOKS = {"east": "west", "west": "east", "north": "south", "south": "north"}    # the way a dial's back looks

# ---- the movement, in pixels from the middle of the floor (x east, y up, z south) -------------------------
BED_TOP = 20.0                                      # the bed lies on the piers (16) and is four deep
BED_X, BED_Z = 22.0, 10.0                           # half its length and half its depth
TRAIN_X = {"strike": -13.0, "going": 0.0, "chime": 13.0}
ARBOR_Y = 25.0                                      # the three barrel arbors
BARREL_R, GREAT_R = 3.5, 5.0
CENTRE_Y = 31.0                                     # the second arbors; the going train's carries the setting dial
SECOND_OUT, FLY_OUT = 4.5, 5.25                     # a side train's second arbor (towards the middle) and fly (outwards)
FLY_Y = 36.0
ESCAPE = (0.0, 37.0, 6.0)                           # the escape wheel's middle, behind the upright shaft
ESCAPE_TEETH = 15
PALLETS = (0.0, 44.0, 6.0)                          # the pallet arbor, in the wheel's plane
PIVOT = (0.0, 44.0, 12.0)                           # the pendulum's suspension: level with the pallet arbor, behind the bed
BOB = 41.5                                          # from the pivot down to the bob's middle, in the pendulum's units (2 px)
SWING = 3.0                                         # degrees to either side
BEATS = 2                                           # the pendulum's swing in swings of the master clock's
NEST = (DIAL - FLOOR_TOP) / PX                      # 56.0: the nest of bevels, at the height of the dials' centres

# the weight lines: where the rope leaves its barrel (x, z in the movement's pixels), the corner it
# drops in, and the height of the weight's eye in the lobby (all three hang over the heads)
LINES = {
    "strike": dict(leave=(TRAIN_X["strike"] - BARREL_R, 2.25), corner=(WELL_X[0], WELL_Z[1]), eye=21.9),
    "going": dict(leave=(TRAIN_X["going"] + BARREL_R, -4.75), corner=(WELL_X[1], WELL_Z[0]), eye=21.4),
    "chime": dict(leave=(TRAIN_X["chime"] + BARREL_R, 2.25), corner=(WELL_X[1], WELL_Z[1]), eye=22.5),
}
SHEAVE_R, SHEAVE_DROP = 2.5, 4.5                    # a sheave's radius, and its middle under the ceiling
BALL_ROPE = (18.25, 24.75, 13.0)                    # where the time ball's rope leaves its drum

# ---- light: (level, rank) --------------------------------------------------------------------------------
# In front of each dial's back, as behind a lit window. Four rows over the plates on the tops of
# the lit slits: 6 arrives there, 5 in the glass under them, which is what the glass has already.
DIAL_GLOW = (10, 2)
CAGE_LAMP = (7, 3)              # at the caged lamp behind the movement
# The way up: a caged lamp over the hatch and one beside the ladder's foot, both at the top of the
# third rank. The ladder climbs three rows shut in between the backs of two slit fields: 8 at each
# end leaves 5 in the middle one. The lower lamp hangs five steps from the lobby's cell before the
# north slit's glass, which keeps its 3.
HATCH_LAMP = (8, 3)
LADDER_LAMP = (8, 3)
WALK_LIGHT = 5                  # the least a place to stand has, at the feet or at the head
# What the pieces are shown with, (sky, block): the movement as the four dials light it, whatever
# the cell its anchor stands in; the pendulum a little less; the weights so that they are seen
# under the lobby's ceiling.
MOVEMENT_LIGHT = (0, 12)
PENDULUM_LIGHT = (0, 10)
WEIGHT_LIGHT = (0, 7)
LAMP_AT = (CX + 1.6, FLOOR_TOP + 1.4, WELL_Z[1] + 1.0)     # the caged lamp, on the south wall
HATCH_LAMP_AT = (HATCH[0] + 0.5, FLOOR_TOP + 1.55, float(WELL_Z[0]))       # over the hatch, on the north wall
LADDER_LAMP_AT = (HATCH[0] + 1.5, T.FOOT + 1.45, float(WELL_Z[0]))         # beside the ladder's foot, on the north wall

# ---- materials ---------------------------------------------------------------------------------------------
TILT = 40.0                     # the tilted frame of a face that glows (props/_kit, props/ironwork)
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
IRON_L = P.mat("iron", base=4)
STEEL = P.mat("iron", base=5)
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")
BRASS_L = P.mat("brass", base=4)
COPPER = P.mat("old_copper")
WOOD = P.mat("dark_wood")
WOOD_L = P.mat("dark_wood", base=3)
RED = P.mat("signal")
CREAM = P.mat("cream")
WOUND = P.mat("iron", kind="rope", base=4, bevel=0)             # wire rope wound on a barrel
WIRE = K.flat("iron", 5)                                        # a wire rope in the air: one tone
TOOTH = (K.flat("brass", 5), K.flat("brass", 3))                # the rim of a wheel: tooth, gap
INK = K.flat("iron", 1)
OPAL = [P.colour("opal", i) for i in range(len(P.RAMPS["opal"]))]
SHADOW = P.colour("ashlar", 0)                                  # the marks, seen through the glass
SHADOW_DEEP = P.colour("old_copper", 0)                         # the hands, close behind it


class _Picture:
    """A face painted by hand: the pixels as they are, for the one face size they were drawn for."""

    def __init__(self, name, pixels):
        self.name = name
        self.pixels = pixels

    def paint(self, w, h, grain="u", seed=0):
        if (h, w) != self.pixels.shape[:2]:
            raise ValueError(f"{self.name} is drawn {self.pixels.shape[1]}x{self.pixels.shape[0]}, "
                             f"the face asks for {w}x{h}")
        return self.pixels.copy()


def hand_angles(hour, minute):
    """Degrees clockwise from twelve, seen from outside: (hour hand, minute hand)."""
    return ((hour % 12) + minute / 60.0) * 30.0, minute * 6.0


def spot(p):
    """A point of the movement (pixels from the middle of the floor) in scene coordinates."""
    return (AXIS[0] + p[0] * PX, FLOOR_TOP + p[1] * PX, AXIS[1] + p[2] * PX)


# ---- the floor -----------------------------------------------------------------------------------------------
def floor_role(x, z, roles=B):
    """The block this package lays in column (x, z) of the floor's row, over the tower's boards
    (tower.way_up()), or None where the tower's floor stays."""
    if (x, z) == HATCH:
        return None
    if x in WELL_X and z in WELL_Z:
        return roles.IRON_GRATE                     # the three other corners: a weight's rope drops through
    if (x, z) in PIERS or (x, z) in ((CX, CZ), SLOT):
        return roles.IRON_RIVETED.block             # under the bed and where the pendulum goes through: whole plate
    return None


def walk():
    """The columns one can stand in: the gallery but for the two cabinets, and the floor round the
    movement but for the piers and the bars between them. The hatch is one of them (the ladder's
    head)."""
    taken = {column for column, _, _ in CABINETS} | set(PIERS) | {(CX, CZ)}
    return [(x, z) for x in range(WELL_X[0], WELL_X[1] + 1) for z in range(WELL_Z[0], WELL_Z[1] + 1)
            if (x, z) not in taken]


def way():
    """The cells of the way up, from inside the door to the hatch: the head's row along the west
    wall of the lobby, then the ladder's own cells up to the room's floor."""
    x, z = HATCH
    door = T.FACE["west"].cell(T.MID, 1)[1]
    step = 1 if door > z else -1
    return [(x, T.FOOT + 1, k) for k in range(door, z, -step)] + [(x, y, z) for y in range(T.FOOT + 1, FEET + 1)]


# ---- models: wheels ----------------------------------------------------------------------------------------------
def _wheel(m, c, z0, z1, r, teeth, mat=BRASS, spokes=2, hub=1.25):
    """A spoked wheel across z, its middle at c = (x, y), `r` to the tips of its teeth. The teeth
    are drawn as the two tones of its rim, tooth and gap; inside them a rim, the spokes, the hub."""
    x, y = c
    zc, w, n = (z0 + z1) / 2.0, z1 - z0, 2 * teeth
    for k in range(n):
        m.ring("z", (x, y, zc), r - 0.5, 1.0, w, TOOTH[k % 2], sides=n, arc=(360.0 * k / n, 360.0 * (k + 1) / n),
               seed=900 + k % 2)
    m.ring("z", (x, y, zc), r - 1.5, 1.0, w, mat, sides=16)
    for k in range(spokes):
        turn = 180.0 * k / spokes
        m.box((x - r + 2.0, y - 0.5, z0 + 0.125), (x + r - 2.0, y + 0.5, z1 - 0.125), mat,
              rot=("z", turn, (x, y, zc)) if turn else None, seed=910)
    m.tube("z", (x, y), z0 - 0.25, z1 + 0.25, hub, BRASS_D, sides=8)


def _side(x):
    return 1.0 if x > 0 else -1.0


# ---- models: the movement ------------------------------------------------------------------------------------------
def _bed():
    """The bed and everything of cast iron that stands on it: two girders on the piers, the cross
    members, the pedestals of the barrel arbors, the going train's A-frames with the pendulum's
    cock on the back one, the posts of the outer trains."""
    m = M.Model(PREFIX + "bed", anchor=(0.0, BED_TOP, 0.0))
    for z0, z1 in ((-BED_Z, -BED_Z + 3.0), (BED_Z - 3.0, BED_Z)):
        m.box((-BED_X, 16.0, z0), (BED_X, 17.0, z1), IRON, grain="x")
        m.box((-BED_X, 17.0, z0 + 1.0), (BED_X, 19.0, z1 - 1.0), IRON_D, grain="x", skip="ud")
        m.box((-BED_X, 19.0, z0), (BED_X, BED_TOP, z1), IRON_L, grain="x")
        for x in TRAIN_X.values():
            m.box((x - 2.0, BED_TOP, z0), (x + 2.0, ARBOR_Y + 1.5, z1), IRON)
            m.tube("z", (x, ARBOR_Y), z0 - 0.5, z1 + 0.5, 1.25, BRASS_D, sides=8)
    for x0 in (-BED_X, -7.5, 5.5, BED_X - 2.0):
        m.box((x0, 16.5, -BED_Z + 3.0), (x0 + 2.0, 19.5, BED_Z - 3.0), IRON_D, grain="z", skip="ns")
    m.box((-4.0, 17.25, -BED_Z - 0.25), (4.0, 18.75, -BED_Z), BRASS_L, skip="s")        # the maker's plate
    # the going train's A-frames: the centre arbor in their ties, the pallet arbor in the back one's head
    for z in (-8.5, 8.5):
        for s in (-1.0, 1.0):
            m.beam((s * 5.5, BED_TOP, z), (s * 1.5, 45.0, z), 1.5, 1.5, IRON)
        m.box((-3.75, CENTRE_Y - 1.0, z - 0.75), (3.75, CENTRE_Y + 1.0, z + 0.75), IRON_D)
        m.box((-2.5, 43.0, z - 1.0), (2.5, 46.5, z + 1.0), IRON_D)
    m.box((-2.75, ESCAPE[1] - 1.0, 7.75), (2.75, ESCAPE[1] + 1.0, 9.25), IRON_D)        # the escape arbor's tie
    m.box((-1.5, 44.75, 9.5), (1.5, 46.5, 13.5), IRON)                                  # the pendulum's cock
    m.box((-1.0, 44.0, 11.25), (1.0, 44.75, 12.75), BRASS_D)                            # the chops the spring hangs in
    # the posts of the outer trains: the second arbor towards the middle, the fly's arbor outwards
    for name in ("strike", "chime"):
        x = TRAIN_X[name]
        xs, xf = x - _side(x) * SECOND_OUT, x + _side(x) * FLY_OUT
        for z0, z1 in ((-9.5, -8.0), (8.0, 9.5)):
            m.box((xs - 1.0, BED_TOP, z0), (xs + 1.0, CENTRE_Y + 1.5, z1), IRON)
            m.box((xf - 0.75, BED_TOP, z0), (xf + 0.75, FLY_Y + 1.5, z1), IRON)
    return m


def _trains():
    """What turns: the three barrels with their ropes and great wheels, the second wheels, the two
    flies, the going train's centre arbor with the bevel that drives the upright shaft, the
    setting dial on its front end, and the winding crank on the going barrel."""
    m = M.Model(PREFIX + "trains", anchor=(0.0, BED_TOP, 0.0))
    for name, x in TRAIN_X.items():
        m.tube("z", (x, ARBOR_Y), -5.5, 3.0, BARREL_R, WOUND, sides=12)
        for z0 in (-6.25, 3.0):
            m.tube("z", (x, ARBOR_Y), z0, z0 + 0.75, BARREL_R + 0.75, IRON_L, sides=12)
        m.tube("z", (x, ARBOR_Y), -11.0, 11.0, 0.75, STEEL, sides=8)
        _wheel(m, (x, ARBOR_Y), 4.25, 5.75, GREAT_R, 15)
        if name == "going":
            continue
        xs, xf = x - _side(x) * SECOND_OUT, x + _side(x) * FLY_OUT
        m.tube("z", (xs, CENTRE_Y), -10.0, 10.0, 0.6, STEEL, sides=8)
        m.tube("z", (xs, CENTRE_Y), 4.0, 6.0, 2.5, BRASS_L, sides=8)                    # its pinion, in the great wheel
        _wheel(m, (xs, CENTRE_Y), -3.0, -2.0, 4.0, 12)
        m.tube("z", (xf, FLY_Y), -13.25, 10.0, 0.6, STEEL, sides=8)
        m.tube("z", (xf, FLY_Y), -3.0, -2.0, 1.25, BRASS_L, sides=8)
        lean = 25.0 if name == "strike" else -40.0
        m.box((xf - 0.25, FLY_Y - 5.0, -13.0), (xf + 0.25, FLY_Y + 5.0, -10.5), IRON_L,
              rot=("z", lean, (xf, FLY_Y, -11.75)))
    # the going train
    m.tube("z", (0.0, CENTRE_Y), -11.0, 9.5, 0.6, STEEL, sides=8)
    m.tube("z", (0.0, CENTRE_Y), 4.0, 6.0, 1.0, BRASS_L, sides=8)                       # the pinion in the great wheel
    _wheel(m, (0.0, CENTRE_Y), 2.5, 3.5, 4.5, 14)
    m.taper("z", (0.0, CENTRE_Y), -3.25, -1.75, 1.5, 2.75, BRASS_L, sides=12)           # the bevel on the arbor
    m.tube("z", (ESCAPE[0], ESCAPE[1]), ESCAPE[2] - 1.5, 9.5, 0.6, STEEL, sides=8)      # the escape wheel's arbor
    # the setting dial: enamel in a brass bezel, two hands
    m.tube("z", (0.0, CENTRE_Y), -11.25, -10.75, 4.0, BRASS, sides=12)
    m.tube("z", (0.0, CENTRE_Y), -11.5, -11.25, 3.25, K.flat("cream", 2), sides=12, cap=K.flat("cream", 3))
    hour, minute = hand_angles(*TIME)
    m.box((-0.5, CENTRE_Y - 0.5, -11.75), (0.5, CENTRE_Y + 2.25, -11.5), INK, rot=("z", hour, (0.0, CENTRE_Y, -11.625)))
    m.box((-0.25, CENTRE_Y - 0.5, -12.0), (0.25, CENTRE_Y + 3.0, -11.75), INK,
          rot=("z", minute, (0.0, CENTRE_Y, -11.875)))
    # the winding crank on the going barrel's square
    m.box((-0.75, ARBOR_Y - 0.75, -12.75), (0.75, ARBOR_Y + 0.75, -11.0), IRON_L)
    m.beam((0.0, ARBOR_Y, -12.25), (-4.5, ARBOR_Y - 4.0, -12.25), 1.0, 1.0, IRON_L)
    m.tube("z", (-4.5, ARBOR_Y - 4.0), -15.75, -12.75, 0.75, WOOD_L, sides=8)
    return m


def _motor():
    """The winding motor, bolted on later: a bracket on the front girder's west end, the motor with
    its band of windings, a worm under a worm wheel on the strike barrel's arbor, the terminal box
    and the conduit down to the floor."""
    m = M.Model(PREFIX + "motor", anchor=(0.0, BED_TOP, 0.0))
    x, axis = TRAIN_X["strike"], (21.75, -13.25)
    m.box((-BED_X, 18.0, -16.5), (-15.0, 19.0, -BED_Z), IRON, grain="x")
    m.tube("x", axis, -21.0, -16.0, 2.75, IRON, sides=12)
    m.tube("x", axis, -19.5, -17.5, 2.9, COPPER, sides=12)
    for x0 in (-21.5, -16.0):
        m.tube("x", axis, x0, x0 + 0.5, 1.75, IRON_L, sides=8)
    m.tube("x", axis, -15.5, -9.5, 0.6, STEEL, sides=8)
    m.tube("x", axis, -15.0, -11.0, 1.1, BRASS_D, sides=8)
    m.tube("z", (x, ARBOR_Y), -14.0, -10.5, 0.75, STEEL, sides=8)
    m.tube("z", (x, ARBOR_Y), -13.75, -12.75, 2.25, BRASS_L, sides=12)
    m.box((-23.5, 20.5, -14.5), (-21.5, 23.0, -12.0), IRON_D)
    m.tube("y", (-22.5, -13.25), 0.5, 20.5, 0.6, IRON_L, sides=8)
    m.tube("y", (-22.5, -13.25), 0.0, 0.5, 1.25, IRON_D, sides=8)
    return m


def _winch():
    """The time ball's drum on the back girder's east end: a small rope drum between two cheeks, a
    brake drum with its band and a lever with a red grip. The rope leaves it upwards."""
    m = M.Model(PREFIX + "winch", anchor=(0.0, BED_TOP, 0.0))
    axis = (22.75, 13.0)
    m.box((15.5, 19.0, BED_Z), (BED_X, BED_TOP, 16.0), IRON, grain="x")
    for x0 in (16.0, 21.0):
        m.box((x0, BED_TOP, 11.0), (x0 + 0.5, 25.0, 15.0), IRON_D)
    m.tube("x", axis, 15.75, 21.75, 0.5, STEEL, sides=8)
    m.tube("x", axis, 16.5, 20.0, 2.0, WOUND, sides=12)
    m.tube("x", axis, 20.0, 21.0, 2.5, IRON_L, sides=12)
    m.ring("x", (20.5, axis[0], axis[1]), 2.75, 0.5, 0.75, IRON_D, sides=12)
    m.beam((20.5, 25.5, 13.0), (20.5, 28.5, 16.5), 0.75, 0.75, IRON_L)
    m.box((19.9, 28.0, 16.0), (21.1, 29.2, 17.2), RED)
    return m


def _escape():
    """The escape wheel, its middle on the anchor: fifteen teeth standing off a thin rim. Turned by
    the motion line about its z axis."""
    m = M.Model(PREFIX + "escape")
    m.ring("z", (0.0, 0.0, 0.0), 3.25, 0.75, 1.0, BRASS_L, sides=16)
    for k in range(ESCAPE_TEETH):
        m.box((3.5, -0.4, -0.5), (4.75, 0.4, 0.5), TOOTH[0],
              rot=("z", 360.0 * k / ESCAPE_TEETH, (0.0, 0.0, 0.0)) if k else None, seed=900)
    for k in range(3):
        m.box((-3.0, -0.4, -0.375), (3.0, 0.4, 0.375), BRASS, rot=("z", 60.0 * k, (0.0, 0.0, 0.0)) if k else None,
              seed=910)
    m.tube("z", (0.0, 0.0), -0.75, 0.75, 1.0, BRASS_D, sides=8)
    return m


def _pallets():
    """The pallets, their arbor and the crutch, as one piece that swings about the arbor (the
    anchor, in the escape wheel's plane): two arms that reach round the top of the wheel, the arbor
    back through the A-frame's head, the crutch down behind it with a fork for the pendulum's rod."""
    m = M.Model(PREFIX + "pallets")
    m.tube("z", (0.0, 0.0), -1.5, 5.25, 0.6, STEEL, sides=8)
    for s in (-1.0, 1.0):
        m.beam((0.0, 0.0, 0.0), (s * 4.6, -4.4, 0.0), 1.0, 1.0, STEEL)
        m.box((s * 4.1, -5.6, -0.5), (s * 5.1, -4.1, 0.5), IRON_L)
        m.box((s * 1.1, -14.0, 5.25), (s * 1.7, -13.0, 7.0), STEEL)
    m.tube("z", (0.0, 0.0), -0.75, 0.75, 1.25, IRON_L, sides=8)
    m.box((-0.4, -13.0, 4.75), (0.4, 0.0, 5.25), STEEL, grain="y")
    m.box((-1.7, -14.0, 4.75), (1.7, -13.0, 5.25), STEEL)
    return m


def _pendulum():
    """The pendulum, hanging from its anchor, in units of two pixels: the spring, a steel rod, the
    brass bob with its rim, the rating nut under it. A little over five blocks to the bob."""
    m = M.Model(PREFIX + "pendulum", px=2.0)
    m.box((-0.5, -2.0, -0.125), (0.5, 0.25, 0.125), STEEL, grain="y")
    m.box((-0.75, -3.0, -0.375), (0.75, -2.0, 0.375), IRON_D)
    m.box((-0.5, -BOB - 4.25, -0.25), (0.5, -3.0, 0.25), STEEL, grain="y")
    m.tube("z", (0.0, -BOB), -1.0, 1.0, 3.5, BRASS_L, sides=16)
    m.ring("z", (0.0, -BOB, 0.0), 3.5, 0.5, 2.25, BRASS_D, sides=16)
    m.box((-0.75, -BOB - 5.0, -0.5), (0.75, -BOB - 4.25, 0.5), BRASS_D)
    m.box((-0.25, -BOB - 5.75, -0.25), (0.25, -BOB - 5.0, 0.25), STEEL)
    return m


# ---- models: the leading-off work and the dials' backs -----------------------------------------------------------
def _leads():
    """The nest of bevels and what it turns, its middle on the anchor: the beam it hangs from (east
    to west, plate to plate), the cage, the crown wheel on the upright shaft that comes up from the
    going train, a pinion on each of the four rods, the rods out to the dials with a coupling half
    way."""
    m = M.Model(PREFIX + "leads")
    m.box((-24.0, 5.0, -1.5), (24.0, 6.0, 1.5), IRON, grain="x")
    m.box((-24.0, 6.0, -0.5), (24.0, 8.0, 0.5), IRON_D, grain="x", skip="ud")
    m.box((-24.0, 8.0, -1.5), (24.0, 9.0, 1.5), IRON_L, grain="x")
    for y0 in (-5.0, 4.0):
        m.box((-4.0, y0, -4.0), (4.0, y0 + 1.0, 4.0), IRON_D)
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            m.box((sx * 3.0, -4.0, sz * 3.0), (sx * 4.0, 4.0, sz * 4.0), IRON, grain="y", skip="ud")
    foot = CENTRE_Y + 2.0 - NEST                                    # just over the bevel on the centre arbor
    m.tube("y", (0.0, 0.0), foot, 4.0, 0.75, STEEL, sides=8)
    m.taper("y", (0.0, 0.0), foot, foot + 1.5, 2.75, 1.5, BRASS_L, sides=12)
    m.tube("y", (0.0, 0.0), -2.75, -1.5, 3.0, BRASS, sides=12)
    m.tube("y", (0.0, 0.0), -1.5, -1.0, 2.0, BRASS_D, sides=12)
    for axis in ("x", "z"):
        for s in (-1.0, 1.0):
            a0, a1 = sorted((s * 1.75, s * 3.0))
            m.tube(axis, (0.0, 0.0), a0, a1, 1.75, BRASS_L, sides=8)
            a0, a1 = sorted((s * 3.0, s * 23.75))
            m.tube(axis, (0.0, 0.0), a0, a1, 0.6, STEEL, sides=8)
            a0, a1 = sorted((s * 12.5, s * 14.5))
            m.tube(axis, (0.0, 0.0), a0, a1, 1.1, BRASS_D, sides=8)
    return m


def _back_picture():
    """The back of a dial, 44 pixels across: opal glass, lightest in the middle; on it the shadows
    of what is painted and what turns on the other side, mirrored: the minute track, a bar at each
    quarter and a short one at each of the other hours, the two hands and their boss."""
    size, c = 44, 22.0
    px = np.zeros((size, size, 4), dtype=np.uint8)
    hands = [(angle, length, half) for angle, (length, half) in zip(hand_angles(*TIME), ((13.0, 3.0), (19.0, 2.5)))]
    for j in range(size):
        for i in range(size):
            x, y = i + 0.5 - c, c - (j + 0.5)
            r = math.hypot(x, y)
            if r > 21.3:
                continue
            check = (i + j) % 2 == 0
            tone = OPAL[2] if r < 8.0 or (r < 10.0 and check) else OPAL[1] if r < 17.0 or (r < 19.0 and check) else OPAL[0]
            if 17.5 < r <= 18.5:
                tone = SHADOW
            for hour in range(12):
                a = math.radians(30.0 * hour)
                along, across = -x * math.sin(a) + y * math.cos(a), abs(x * math.cos(a) + y * math.sin(a))
                if (13.5 if hour % 3 == 0 else 15.5) <= along <= 17.5 and across < 1.0:
                    tone = SHADOW
            for angle, length, half in hands:
                a = math.radians(angle)
                along, across = -x * math.sin(a) + y * math.cos(a), abs(x * math.cos(a) + y * math.sin(a))
                if -3.0 <= along <= length and across < half - max(0.0, along - length + 4.0) / 2.0:
                    tone = SHADOW_DEEP
            if r < 3.5:
                tone = SHADOW_DEEP
            px[j, i, :3] = tone
            px[j, i, 3] = 255
    return _Picture("clockroom_dial_back", px)


def _dial():
    """The back of one dial, on the iron plate, in units of two pixels, drawn in the tilted frame so
    that all four are lit alike: the opal disc (it glows), its iron ring and two stays, the motion
    work on its middle, where the rod arrives."""
    m = M.Model(PREFIX + "dial", px=2.0)
    with m.turned(("x", TILT)):
        m.box((-11.0, -11.0, 0.0), (11.0, 11.0, 0.5), P.mat("opal"), skip="nweud", faces={"s": _back_picture()}, emit=15)
        m.ring("z", (0.0, 0.0, 0.75), 10.75, 1.0, 1.5, IRON, sides=24)
        for turn in (45.0, 135.0):
            m.box((-10.25, -0.25, 0.5), (10.25, 0.25, 0.75), K.flat("iron", 2), rot=("z", turn, (0.0, 0.0, 0.625)),
                  seed=920)
        m.tube("z", (0.0, 0.0), 0.5, 2.0, 1.75, IRON_D, sides=12)
        m.tube("z", (0.0, 0.0), 2.0, 2.75, 2.75, BRASS, sides=12)
        m.tube("z", (0.0, 0.0), 2.75, 3.5, 1.5, BRASS_L, sides=8)
    return m


# ---- models: ropes, weights, small pieces ----------------------------------------------------------------------------
def _slot(side):
    """The pendulum's slot in the floor plate, its middle on the anchor: an iron rim round a dark
    opening, long enough for the swing. side 1 lies on the floor, side -1 under the lobby's ceiling."""
    m = M.Model(PREFIX + ("slot" if side > 0 else "slot_under"))
    y0, y1 = sorted((0.0, side * 0.25))
    m.box((-7.0, y0, -2.5), (7.0, y1, 2.5), IRON_L)
    y0, y1 = sorted((side * 0.25, side * 0.3))
    m.box((-6.0, y0, -1.5), (6.0, y1, 1.5), K.flat("iron", 0), skip="d" if side > 0 else "u")
    return m


def _rope():
    """A wire rope: one pixel square, along +z from its anchor, 48 long (artkit.models.between)."""
    m = M.Model(PREFIX + "rope")
    m.box((-0.5, -0.5, 0.0), (0.5, 0.5, 48.0), WIRE, grain="z")
    return m


def _sheave():
    """A sheave under the ceiling; the anchor is where its hanger is fixed. The wheel turns in the
    plane of the model's y and z, its middle SHEAVE_DROP under the anchor."""
    m = M.Model(PREFIX + "sheave")
    m.box((-1.5, -0.5, -1.5), (1.5, 0.0, 1.5), IRON)
    for x0 in (-1.1, 0.6):
        m.box((x0, -SHEAVE_DROP - 1.0, -0.5), (x0 + 0.5, -0.5, 0.5), IRON_D, grain="y")
    m.tube("x", (-SHEAVE_DROP, 0.0), -0.5, 0.5, SHEAVE_R, IRON_L, sides=12)
    m.tube("x", (-SHEAVE_DROP, 0.0), -1.25, 1.25, 0.5, BRASS_D, sides=8)
    return m


def _weight():
    """A weight, hanging from its anchor (the eye): a rod through four cast-iron cheeses."""
    m = M.Model(PREFIX + "weight")
    m.ring("x", (0.0, -0.75, 0.0), 0.75, 0.5, 0.5, IRON_L, sides=8)
    m.box((-0.4, -3.0, -0.4), (0.4, -1.5, 0.4), IRON_L, grain="y")
    for k in range(4):
        y1 = -3.0 - 3.25 * k
        m.tube("y", (0.0, 0.0), y1 - 3.0, y1, 3.5, IRON if k % 2 else IRON_D, sides=12)
    return m


def _board():
    """The record of the clock's setting, on the wall: a ruled sheet under a brass clip on a board."""
    m = M.Model(PREFIX + "board")
    tones = {"3": P.RAMPS["cream"][3], "2": P.RAMPS["cream"][1], "1": P.RAMPS["enamel"][2]}
    sheet = Sprite("clockroom_sheet", ["33333333", "31111113", "33333333", "32222223", "33333333", "32222223",
                                       "33333333", "32223333", "33333333"], tones)
    m.box((-5.0, -6.5, 0.0), (5.0, 6.5, 0.75), WOOD, grain="y")
    m.box((-4.0, -5.5, 0.75), (4.0, 3.5, 1.0), CREAM, skip="n", faces={"s": sheet})
    m.box((-1.5, 3.0, 1.0), (1.5, 4.75, 1.5), BRASS)
    return m


def _oilcan():
    """The oil can on its drip tray; the spout points along +x."""
    m = M.Model(PREFIX + "oilcan")
    m.box((-3.5, 0.0, -2.5), (3.5, 0.5, 2.5), IRON_D)
    m.tube("y", (-0.75, 0.0), 0.5, 4.0, 2.0, BRASS, sides=8)
    m.taper("y", (-0.75, 0.0), 4.0, 6.0, 2.0, 0.75, BRASS, sides=8)
    m.beam((-0.75, 6.0, 0.0), (4.5, 9.0, 0.0), 0.5, 0.5, BRASS_D)
    return m


@functools.lru_cache(maxsize=None)
def _models():
    built = [_bed(), _trains(), _motor(), _winch(), _escape(), _pallets(), _pendulum(), _slot(1), _slot(-1),
             _leads(), _dial(), _rope(), _sheave(), _weight(), _board(), _oilcan()]
    return {m.name: m for m in built}


def models():
    """The room's own models. The caged lamp is props/lamps'."""
    return dict(_models())


def their_models():
    """The models of the other packages' pieces the room places: what a test scene packs besides."""
    return dict(lamps.models())


# ---- the room ----------------------------------------------------------------------------------------------------------
def _motion():
    """The motion line's kit, or None while it is not in the tree: everything then stands still."""
    try:
        from ..motion import _kit
    except ImportError:
        return None
    return _kit


def _offer(canvas, cell, level, why, rank):
    """Register a light source with the light line (sky/_lightkit). While that kit is not in the
    tree the block is put down here, never over a block that is there, so a test scene is lit."""
    try:
        from ..sky import _lightkit
    except ImportError:
        canvas.set(*cell, st(B.LIGHT, level=level), keep=True)
    else:
        _lightkit.suggest(canvas, cell, level, why, rank=rank)


def build_clockroom(c, origin=(0, 0, 0), roles=B):
    """Dress the room standing at `origin`. Returns dict(entities=<display entities placed>,
    lights=[((x, y, z), level, why)]): the light sources it has offered to the light line."""
    ox, oy, oz = origin
    lights, n = [], 0
    own = _models()
    kit = _motion()

    def put(x, y, z, state, keep=False):
        c.set(ox + x, oy + y, oz + z, state, keep=keep)

    def at(p):
        return (ox + p[0], oy + p[1], oz + p[2])

    def show(name, p, **opts):
        c.add_entity(*at(p), M.display(own[PREFIX + name], **opts))
        return 1

    def rope(a, b):
        c.add_entity(*at(a), M.between(own[PREFIX + "rope"], a, b))
        return 1

    def offer(cell, ask, why):
        level, rank = ask
        cell = tuple(int(math.floor(v)) for v in cell)
        _offer(c, at(cell), level, f"{NAME}:{why}", rank)
        lights.append((cell, level, why))

    # ---- the floor: the cells the movement needs, over the tower's boards
    for x in range(WELL_X[0], WELL_X[1] + 1):
        for z in range(WELL_Z[0], WELL_Z[1] + 1):
            role = floor_role(x, z, roles)
            if role is not None:
                put(x, FLOOR_Y, z, role)
    # the piers, and bars between them: nobody walks through under the bed
    for x, z in PIERS:
        put(x, FEET, z, roles.IRON_CAST)
    put(CX, FEET, CZ, roles.IRON_BARS)
    # the two cabinets, in place of the plate over a dark slit's glass: whole blocks, no light gets down
    for (x, z), panel, looks in CABINETS:
        put(x, FEET, z, st(roles.PANELS[panel], facing=looks))

    # ---- the movement
    bed = spot((0.0, BED_TOP, 0.0))
    for name in ("bed", "trains", "motor", "winch"):
        n += show(name, bed, brightness=MOVEMENT_LIGHT)
    n += show("escape", spot(ESCAPE), brightness=MOVEMENT_LIGHT)
    period = BEATS * kit.PENDULUM if kit else 0
    if kit:
        kit.spin(c, "z", ESCAPE_TEETH * period)
    n += show("pallets", spot(PALLETS), brightness=MOVEMENT_LIGHT)
    if kit:
        kit.swing(c, "z", SWING, period)
    n += show("pendulum", spot(PIVOT), scale=2.0, brightness=PENDULUM_LIGHT)
    if kit:
        kit.swing(c, "z", SWING, period)
    through = spot(PIVOT)
    n += K.put(c, own[PREFIX + "slot"], (through[0], FLOOR_TOP, through[2]), origin=origin)
    n += K.put(c, own[PREFIX + "slot_under"], (through[0], float(FLOOR_Y), through[2]), mount="ceiling", origin=origin)

    # ---- the leading-off work and the dials' backs
    n += show("leads", (AXIS[0], DIAL, AXIS[1]), brightness=MOVEMENT_LIGHT)
    for name, back in T.DIAL_BACKS.items():
        n += K.put(c, own[PREFIX + "dial"], back, mount="wall", facing=LOOKS[name], scale=2.0, origin=origin,
                   turns=(("x", -TILT),))
        d = K.turn(K.FACING[LOOKS[name]], (0.0, 0.0, 0.5))
        offer((back[0] + d[0], back[1], back[2] + d[2]), DIAL_GLOW, f"dial {name}")

    # ---- the weight lines: up from the barrel, over two sheaves under the ceiling, down a corner
    r = SHEAVE_R * PX
    hub = CEILING - SHEAVE_DROP * PX
    for name, line in LINES.items():
        a = spot((line["leave"][0], ARBOR_Y, line["leave"][1]))
        cx, cz = line["corner"][0] + 0.5, line["corner"][1] + 0.5
        run = math.hypot(cx - a[0], cz - a[2])
        ux, uz = (cx - a[0]) / run, (cz - a[2]) / run
        yaw = math.degrees(math.atan2(-ux, uz))
        first, last = (a[0] + ux * r, CEILING, a[2] + uz * r), (cx - ux * r, CEILING, cz - uz * r)
        for p in (first, last):
            n += K.put(c, own[PREFIX + "sheave"], p, mount="ceiling", yaw=yaw, origin=origin)
        n += rope(a, (a[0], hub, a[2]))
        n += rope((first[0], hub + r, first[2]), (last[0], hub + r, last[2]))
        eye = (cx, line["eye"], cz)
        n += rope((cx, hub, cz), eye)
        n += show("weight", eye, brightness=WEIGHT_LIGHT)
    # the time ball's rope: from its drum up through the ceiling
    a = spot(BALL_ROPE)
    n += rope(a, (a[0], CEILING - K.NUDGE, a[2]))

    # ---- the small pieces: the record over the switchboard, on the north wall; the oil can on the drawers
    n += K.put(c, own[PREFIX + "board"], (AXIS[0], FLOOR_TOP + 1.5, float(WELL_Z[0])), mount="wall",
               facing="south", origin=origin)
    n += K.put(c, own[PREFIX + "oilcan"], (AXIS[0] - 0.1, FLOOR_TOP + 1.0, WELL_Z[1] + 0.5), yaw=200.0, origin=origin)

    # ---- the light: the caged lamps behind the movement, over the hatch and beside the ladder's foot
    n += lamps.place(c, "cage", LAMP_AT, facing="north", origin=origin, light=False)
    offer((LAMP_AT[0], LAMP_AT[1], LAMP_AT[2] - 0.5), CAGE_LAMP, "caged lamp")
    for where, ask, why in ((HATCH_LAMP_AT, HATCH_LAMP, "hatch lamp"), (LADDER_LAMP_AT, LADDER_LAMP, "ladder lamp")):
        n += lamps.place(c, "cage", where, facing="south", origin=origin, light=False)
        offer((where[0], where[1], where[2] + 0.5), ask, why)
    return {"entities": n, "lights": lights}


def build(canvas, origin=(0, 0, 0)):
    """The master scene's call: the tower's way up (the door open, the ladder, the room's floor and
    the plates along its walls), then the room."""
    if not MOVED_IN:
        return 0
    T.way_up(canvas, origin)
    return build_clockroom(canvas, origin)["entities"]
