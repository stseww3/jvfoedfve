"""props/steam -- the steam mains of the hill (plan/round2.md, card plan/packages/props/steam-mains.md).

The power house makes the steam and the observatory is heated by it. Until now one main showed: over
the pipe bridge, into the ground at the bridge head and up again at the foot of the south end
pavilion (props/pipes.inlet). This package lays the mains that are seen from there on: copper,
because a steam main of the 1890s that is to last is copper, in the pipework family's own fittings
(props/pipes: the iron flanges, bends, plates, brackets and stop valves with the red handwheel).

A main is under steam and is seen to be: the gland of every stop valve weeps (pipes.weep), and at
every low point a steam trap stands beside the main and blows now and then (trap()).

    lay(canvas, a, b)                 one straight length of the copper main (as pipes.run lays iron)
    trap(canvas, pos, out)            a steam trap beside the main, on the stone the main lies over
    east_front(canvas)                the heating main of the south wing: along the foot of the east
                                      front, on the plinth's coping under the base windows
    dress(canvas)                     everything the package places in the master scene

The heating main of the south wing (east_front). It leaves the pilaster south of the stretch, lies
on the weathered coping of the plinth as close to the wall as its flanges let it, and goes north:
through two pilasters (a plate on either face), past a bracket and a bolted joint, through a stop
valve whose handwheel looks out at the court, past a steam trap that stands on the plinth's lower
step, round the last pilaster in an expansion bend of four quarter bends, and into the wall before
the corner of the middle pavilion, well clear of the rainwater pipe that stands in that corner. It
keeps out of the door's bays and crosses no window: the base windows begin a course higher.
Nothing of it comes down into the height of whoever walks along the foot of the wall: the bend
round the pilaster is the only part that stands over the paving, and its underside is 2.1 blocks up.

All functions take scene coordinates plus `origin` and return the number of display entities.
"""
import functools
import math

from artkit import models as M

from ..common import skeleton as S
from ..motion import _kit as MK
from . import _kit as K
from . import pipes

PREFIX = "prop_steam_"
DRESS = True            # the mains in the master scene
# How far off the pieces are drawn (artkit.models' bands): the line -- lengths and bends -- from across
# the court, what is small on it only from near by.
VIEW_LINE = M.MID
VIEW_SMALL = M.NEAR

SIZE = "l"              # the bore: the big one of the family, 6 px across
R = pipes.BORE[SIZE]
OFF = pipes.STANDOFF[SIZE] / 16.0       # the axis off a wall the main runs along, and over the stone it lies on
NECK = (pipes.PLATE_NECK - 1.0) / 16.0  # a length starts this far inside a plate's neck,
PORT = (pipes.VALVE[SIZE] - 1.0) / 16.0     # stops this far from the middle of a valve
LEG = (pipes.ELBOW[SIZE] - 1.0) / 16.0      # and from the corner of a bend: inside their flanges

# ---- the steam trap ---------------------------------------------------------------------------------
# In the trap's own frame (texels; the origin on the main's axis, +z away from the wall, +y up):
TRAP_OUT = 6.5          # the pot's axis off the main's
TRAP_FOOT = -13.0       # the pot's foot under the main's axis: on the plinth's lower step when the main lies
#                         OFF over its upper one (half a block down)
TRAP_SPOUT = (10.5, -11.5)      # the spout's mouth: out, and under the main's axis
# A trap blows: the condensate goes, and a little steam with it. The wisps of one blow, in the BREATH
# of pipes.weep (motion/smoke's slow chain): the tick, the blocks a tick it leaves the spout with, and
# its way as (away from the wall, up, with the wind).
BLOW = ((90, 0.055, (0.9, 0.55, 0.35)), (94, 0.045, (0.8, 0.8, 0.45)), (99, 0.035, (0.6, 1.0, 0.5)))


def _main():
    """A length of the copper main: along +z from the anchor, pipes.RUN long, to be drawn out. The
    rainwater copper's tones, a step down the ramp as all copper out of doors is."""
    m = M.Model(PREFIX + "main")
    pipes._even(m, "z", (0, 0), 0.0, pipes.RUN, R, pipes.RAIN3)
    return m


def _trap():
    """The steam trap: a cast-iron pot with a bolted lid that stands beside the main, a nipple from
    the main's flank down into its lid, a brass cock and a spout low on the side away from the wall."""
    m = M.Model(PREFIX + "trap")
    out, foot = TRAP_OUT, TRAP_FOOT
    m.tube("z", (0, 0), R - 0.5, R + 1.0, 1.5, K.IRON_D)                    # the boss on the main's flank
    m.tube("z", (0, 0), R + 1.0, out, 1.0, K.IRON)
    m.ball((0.0, 0.0, out), 1.5, K.IRON_D, sides=8, layers=3)
    m.tube("y", (0, out), -4.0, 0.0, 1.0, K.IRON)
    m.tube("y", (0, out), -5.0, -4.0, 3.25, K.IRON_D, sides=8)             # the lid
    for i in range(4):
        m.box((2.0, -4.0, out - 0.5), (3.0, -3.5, out + 0.5), K.RIVET, rot=("y", 45.0 + 90.0 * i, (0.0, 0.0, out)))
    m.tube("y", (0, out), foot + 0.75, -5.0, 2.75, K.IRON, sides=8)        # the pot
    m.tube("y", (0, out), foot, foot + 0.75, 3.25, K.IRON_D, sides=8)
    cock = TRAP_SPOUT[1] + 1.5
    m.tube("z", (0, cock), out + 2.5, TRAP_SPOUT[0], 0.75, K.BRASS)         # the cock
    m.box((-0.4, cock + 0.5, out + 3.0), (0.4, cock + 2.0, out + 3.6), K.BRASS_D)
    m.tube("y", (0, TRAP_SPOUT[0]), TRAP_SPOUT[1], cock + 0.75, 0.75, K.BRASS_D)       # the spout looks down
    return m


SPEC = {"main": _main, "trap": _trap}


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: K.settle(build()) for name, build in SPEC.items()}


def models():
    return dict(_models())


# ---- placing ----------------------------------------------------------------------------------------
def lay(canvas, a, b, lit=None, origin=(0, 0, 0)):
    """One straight length of the copper main from a to b, two points of its axis, along one of the
    axes; returns 1. The entity stands at a, which must be in the air (it takes its light there); b
    may lie inside a fitting or a stone. lit: the side its light tone looks to (pipes.run)."""
    a = tuple(a[i] + origin[i] for i in range(3))
    b = tuple(b[i] + origin[i] for i in range(3))
    d = tuple(b[i] - a[i] for i in range(3))
    along = pipes._name(d)
    if along is None:
        raise ValueError(f"a length of the steam main runs along an axis, not from {a} to {b}")
    if lit is None:
        lit = "north" if along in ("up", "down") else "up"
    dist = math.sqrt(sum(v * v for v in d))
    canvas.add_entity(a[0], a[1], a[2], M.display(_models()[PREFIX + "main"], scale=(1.0, 1.0, dist * 16.0 / pipes.RUN),
                                                  turns=pipes._turns(along, lit), view=VIEW_LINE))
    return 1


def trap(canvas, pos, out="east", origin=(0, 0, 0), phase=0):
    """A steam trap beside the main: pos is the point of the main's axis it is tapped at, `out` the
    level way from there to the pot. It blows once in a BREATH (BLOW). Returns 1."""
    d = pipes.DIRS[out]
    n = K.put(canvas, _models()[PREFIX + "trap"], pos, yaw=0.0, turns=pipes._turns(out, "up"), origin=origin,
              view=VIEW_SMALL)
    mouth = tuple(pos[i] + d[i] * (TRAP_SPOUT[0] / 16.0 + 0.03) + (TRAP_SPOUT[1] / 16.0 - 0.03 if i == 1 else 0.0)
                  for i in range(3))
    for tick, speed, (away, up, wind) in BLOW:
        way = tuple(d[i] * away + (up if i == 1 else 0.0) + MK.WIND[i] * wind for i in range(3))
        MK.puff(canvas, mouth, pipes.STEAM, pipes.BREATH, at=(tick,), count=0, spread=way, speed=speed,
                origin=origin, phase=phase)
    return n


# ---- the heating main of the south wing ---------------------------------------------------------------
# The stretch: the pilasters of the south wing it meets, by number (pilaster k stands in row
# S.pilaster_z(k)). It leaves FRONT_FROM northwards, goes through those of FRONT_THROUGH and round
# FRONT_ROUND, and turns into the wall FRONT_END blocks north of that one.
FRONT_FROM = 14
FRONT_THROUGH = (13, 12)
FRONT_ROUND = 11
FRONT_END = 1.75
FRONT_CLEAR = 6.0       # texels between the stone of the pilaster and the axis of the bend that goes round it
FRONT_VALVE = 0.8       # the stop valve, blocks north of the last pilaster the main goes through
FRONT_JOINT = 1.55      # the bolted joint after it,
FRONT_TRAP = 1.95       # and the steam trap
FRONT_CLIPS = ((FRONT_FROM, 1.5), (13, 0.75), (13, 2.25))       # brackets: blocks north of the north face of a pilaster
FRONT_JOINTS = ((13, 1.5),)                                     # bolted joints in the plain lengths, the same way


def front_line():
    """The axis of the heating main along the east front: (x, y), and x of the bend round the pilaster."""
    face = S.WALL_E + 1.0                               # the face of the wings' wall
    return face + OFF, S.PLINTH[1] + 1.0 + OFF, face + OFF + 1.0


def east_front(canvas, origin=(0, 0, 0)):
    """The heating main of the south wing (see the top of the file). Nothing is placed unless the
    wall and the plinth of the stretch stand on the canvas. Returns the number of display entities."""
    x, y, bend = front_line()
    ox, oy, oz = origin
    wall, row = int(S.WALL_E), int(S.PLINTH[1]) + 1
    z_end = S.pilaster_z(FRONT_ROUND) - FRONT_END
    for z in (S.pilaster_z(FRONT_FROM) - 1, S.pilaster_z(FRONT_ROUND) + 1, int(math.floor(z_end))):
        if not pipes._stone(canvas, wall + ox, row + oy, z + oz):           # the wall the main runs along
            return 0
        if not pipes._stone(canvas, wall + 1 + ox, row - 1 + oy, z + oz):   # the plinth it lies over
            return 0
        if pipes._stone(canvas, wall + 1 + ox, row + oy, z + oz):           # and its own way, which is clear
            return 0

    def at(z):
        return (x, y, z)

    def plain(z0, z1):
        return lay(canvas, at(z0), at(z1), origin=origin)

    def fit(kind, pos, along, out="up"):
        return pipes.place(canvas, kind + "_" + SIZE, pos, along=along, out=out, origin=origin,
                           view=VIEW_LINE if kind == "elbow" else VIEW_SMALL)

    def fix(kind, pos, out):
        return pipes.mount(canvas, kind + "_" + SIZE, pos, out=out, origin=origin, view=VIEW_SMALL)

    n = 0
    z = float(S.pilaster_z(FRONT_FROM))                 # the north face of the pilaster the main leaves
    n += fix("plate", at(z), "north")
    for k in FRONT_THROUGH:                             # a bay, and through the pilaster north of it
        far = S.pilaster_z(k) + 1.0
        n += plain(z - NECK, far + NECK)
        n += fix("plate", at(far), "south")
        z = far - 1.0
        n += fix("plate", at(z), "north")
    for k, north in FRONT_CLIPS:
        n += fix("clip", (x - OFF, y, S.pilaster_z(k) - north), "east")
    for k, north in FRONT_JOINTS:
        n += fit("flange", at(S.pilaster_z(k) - north), "north")
    # the last bay before the bend: the stop valve, a bolted joint, the trap
    valve = z - FRONT_VALVE
    south = S.pilaster_z(FRONT_ROUND) + 1.0 + FRONT_CLEAR / 16.0        # the bend's two corners on the main's line
    north = S.pilaster_z(FRONT_ROUND) - FRONT_CLEAR / 16.0
    n += plain(z - NECK, valve + PORT)
    n += fit("valve", at(valve), "north", "east")
    pipes.weep(canvas, "valve_" + SIZE, at(valve), "east", origin=origin, phase=pipes.BREATH // 4)
    n += plain(valve - PORT, south + LEG)
    n += fit("flange", at(z - FRONT_JOINT), "north")
    n += trap(canvas, at(z - FRONT_TRAP), "east", origin=origin)
    # round the pilaster: out, past it, in again
    n += fit("elbow", at(south), "south", "east")
    n += lay(canvas, (x + LEG, y, south), (bend - LEG, y, south), origin=origin)
    n += fit("elbow", (bend, y, south), "west", "north")
    n += lay(canvas, (bend, y, south - LEG), (bend, y, north + LEG), origin=origin)
    n += fit("elbow", (bend, y, north), "south", "west")
    n += lay(canvas, (bend - LEG, y, north), (x + LEG, y, north), origin=origin)
    n += fit("elbow", at(north), "east", "north")
    # and into the wall
    n += plain(north - LEG, z_end + LEG)
    n += fit("elbow", at(z_end), "south", "west")
    n += fix("plate", (x - OFF, y, z_end), "east")
    return n


def dress(canvas, origin=(0, 0, 0)):
    """The mains in the master scene, on whatever the other lines have built there."""
    return east_front(canvas, origin)


def build(canvas, origin=(0, 0, 0)):
    """What this package places in the master scene: dress(), while DRESS is on."""
    return dress(canvas, origin) if DRESS else 0
