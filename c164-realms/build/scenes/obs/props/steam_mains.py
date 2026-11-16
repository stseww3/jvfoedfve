"""props/steam_mains -- the steam mains of the hill (plan/round2.md, card plan/packages/props/steam-mains.md).

The power house makes the steam and the observatory is heated by it. Until now one main showed: over
the pipe bridge, into the ground at the bridge head and up again at the foot of the south end
pavilion (props/pipes.inlet). This package lays the mains that are seen from there on: copper,
because a steam main of the 1890s that is to last is copper, with the pipework family's iron on it
(props/pipes: the bolted flanges, the plates where a main goes into stone, the brackets, the stop
valve with the red handwheel). Every main has a number and wears the ring of its medium, red for
steam (plan/parts/pipes.md).

A main is under steam and is seen to be: the gland of every stop valve weeps (pipes.weep), and at
every low point a steam trap stands beside the main and blows now and then (blow()).

A stretch of main is a few display entities, not one to a fitting: a model is a piece of the line
up to three blocks long with everything that sits on it -- joints, rings, brackets, the valve, the
trap -- so a board view that looks along a wall counts a handful of pieces (the views are held to
600 display entities each). The models are drawn in the frame of the wall they run along: +z along
the main, +x away from the wall, +y up; the anchor is a point of the main's axis, and a piece is
placed with its +z to the south. A main along a wall belongs to the outline of that wall: its
pieces keep the far band they are built with (plan/roles/INTERFACE.md, section 7).

    east_front(canvas)                the heating main of the south wing (S 3): along the foot of the
                                      east front, on the plinth's coping under the base windows
    blow(canvas, tap, out)            a steam trap's spout blows: the wisps, as the motion line's points
    dress(canvas)                     everything the package places in the master scene

The heating main of the south wing (east_front). It leaves the pilaster south of the stretch, lies
on the weathered coping of the plinth as close to the wall as its flanges let it, and goes north:
two bays from pilaster to pilaster (a plate on either face, a bolted joint half way, two brackets),
through a stop valve whose handwheel looks out at the court, past a steam trap that stands on the
plinth's lower step, round the last pilaster in an expansion bend of copper, and into the wall
before the corner of the middle pavilion, well clear of the rainwater pipe that stands in that
corner. It keeps out of the door's bays and crosses no window: the base windows begin a course
higher. Nothing of it comes down into the height of whoever walks along the foot of the wall: the
bend round the pilaster is the only part that stands over the paving, and its underside is 2.1
blocks up.

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

SIZE = "l"              # the bore: the big one of the family, 6 px across
R = pipes.BORE[SIZE]
WALL = pipes.STANDOFF[SIZE]     # texels from the main's axis to the wall it runs along and to the stone it lies over
OFF = WALL / 16.0
TONES = pipes.RAIN3             # old copper a step down the ramp, as all copper out of doors: a straight length
COPPER = K.COPPER_D             # and a bend
RING = K.flat("signal", 1)      # the ring of the medium: steam is red (plan/parts/pipes.md)
RING_W = 2.0                    # a ring's width; it stands half a texel proud of the pipe
BEND = 6.0                      # the radius of a copper bend, on the axis
BAY = 48.0                      # a piece from pilaster to pilaster: three blocks
PITCH = 16.0 * S.BAY            # from one pilaster to the next
JOINT = 1.75                    # a joint's bolts end this far either side of its plane


# ---- what a piece is drawn from ---------------------------------------------------------------------
def _length(m, z0, z1):
    """A straight length of the copper main along z."""
    pipes._even(m, "z", (0.0, 0.0), min(z0, z1), max(z0, z1), R, TONES)


def _ring(m, z, x=0.0):
    """The ring of the steam's colour round the main, from z on along +z."""
    m.tube("z", (x, 0.0), z, z + RING_W, R + 0.5, RING)


def _joint(m, z):
    """Two lengths bolted together: the family's pair of flanges about the plane z."""
    with m.moved((0.0, 0.0, z)):
        pipes._pair(m, SIZE, -1.0)


def _plate(m, z, stone):
    """Where the main goes into stone whose face is the plane z: the family's plate, a flange bolted
    on the face and the neck the pipe is brazed into. stone is 1 when the stone lies on the +z side
    of the face, -1 when on the -z side."""
    count, first = pipes.BOLTS[SIZE]
    face, back, neck = z - stone * 0.05, z - stone * 1.5, z - stone * pipes.PLATE_NECK
    m.tube("z", (0.0, 0.0), min(face, back), max(face, back), R + 2.0, K.IRON)
    m.tube("z", (0.0, 0.0), min(back, neck), max(back, neck), R + 0.5, K.IRON_D)
    pipes._bolts(m, R + 1.25, count, min(back, back - stone * 0.75), max(back, back - stone * 0.75), first)


def _bracket(m, z, wall=-WALL, x=0.0):
    """A bracket at z, as the family's clip: a plate riveted to the wall (the plane x = wall, the
    stone behind it), a stem, a strap round the main whose axis is at x."""
    m.box((wall + 0.05, -R - 2.0, z - 2.0), (wall + 0.75, R + 2.0, z + 2.0), K.IRON_D)
    for y in (-R - 1.0, R + 1.0):
        K.rivet(m, (wall + 0.75, y, z), out="x")
    m.box((wall + 0.75, -1.0, z - 0.75), (x - R, 1.0, z + 0.75), K.IRON)
    m.ring("z", (x, 0.0, z), R + 0.5, 1.0, 2.0, K.IRON_D, sides=8)


def _valve(m, z):
    """The stop valve at z, the family's (pipes._valve): its works out along +x, so the handwheel
    looks away from the wall, one spoke upright."""
    g = R + 1.5
    with m.moved((0.0, 0.0, z)):
        m.ball((0.0, 0.0, 0.0), g, K.IRON_D, sides=8, layers=3)
        pipes._port(m, SIZE, g - 1.0, pipes.VALVE[SIZE])
        with m.turned(("y", 180.0)):
            pipes._port(m, SIZE, g - 1.0, pipes.VALVE[SIZE])
        with m.turned(("z", -90.0)):
            pipes._works(m, SIZE, g - 1.0, top=180.0)


def _arc(cx, cz, a0, a1, rho=BEND, steps=3):
    """The axis of a quarter bend in the level plane: points round (cx, cz) from the angle a0 to a1,
    in degrees, 0 along +x and 90 along +z."""
    angles = [math.radians(a0 + (a1 - a0) * i / steps) for i in range(steps + 1)]
    return [(cx + rho * math.cos(a), 0.0, cz + rho * math.sin(a)) for a in angles]


# ---- the steam trap -----------------------------------------------------------------------------------
# A cast-iron pot with a bolted lid that stands beside the main, on the stone the main lies over; a
# nipple from the main's flank down into its lid; a brass cock and a spout low on the side away from
# the wall. In texels from the point of the main's axis it is tapped at:
TRAP_OUT = 6.5          # the pot's axis off the main's
TRAP_FOOT = -13.0       # the pot's foot under the main's axis: on the plinth's lower step when the main lies
#                         WALL over its upper one (half a block down)
TRAP_SPOUT = (10.25, -11.5)     # the spout's mouth: out (its lip is over the edge of the step), and under the main's axis
# A trap blows: the condensate goes, and a little steam with it. The wisps of one blow, in the BREATH
# of pipes.weep (motion/smoke's slow chain): the tick, the blocks a tick it leaves the spout with, and
# its way as (away from the wall, up, with the wind).
BLOW = ((90, 0.055, (0.9, 0.55, 0.35)), (94, 0.045, (0.8, 0.8, 0.45)), (99, 0.035, (0.6, 1.0, 0.5)))


def _trap(m, z):
    """The trap tapped at z."""
    out, foot = TRAP_OUT, TRAP_FOOT
    with m.moved((0.0, 0.0, z)):
        m.tube("x", (0.0, 0.0), R - 0.5, R + 1.0, 1.5, K.IRON_D)                # the boss on the main's flank
        m.tube("x", (0.0, 0.0), R + 1.0, out, 1.0, K.IRON)
        m.ball((out, 0.0, 0.0), 1.5, K.IRON_D, sides=8, layers=3)
        m.tube("y", (out, 0.0), -4.0, 0.0, 1.0, K.IRON)
        m.tube("y", (out, 0.0), -5.0, -4.0, 3.25, K.IRON_D, sides=8)            # the lid
        for i in range(4):
            m.box((out + 2.0, -4.0, -0.5), (out + 3.0, -3.5, 0.5), K.RIVET, rot=("y", 45.0 + 90.0 * i, (out, 0.0, 0.0)))
        m.tube("y", (out, 0.0), foot + 0.75, -5.0, 2.75, K.IRON, sides=8)       # the pot
        m.tube("y", (out, 0.0), foot, foot + 0.75, 3.25, K.IRON_D, sides=8)
        cock = TRAP_SPOUT[1] + 1.5
        m.tube("x", (cock, 0.0), out + 2.5, TRAP_SPOUT[0], 0.75, K.BRASS)       # the cock
        m.box((out + 3.0, cock + 0.5, -0.4), (out + 3.6, cock + 2.0, 0.4), K.BRASS_D)
        m.tube("y", (TRAP_SPOUT[0], 0.0), TRAP_SPOUT[1], cock + 0.75, 0.75, K.BRASS_D)     # the spout looks down


def blow(canvas, tap, out="east", origin=(0, 0, 0), phase=0):
    """The trap tapped at `tap`, a point of a main's axis, blows once in a BREATH (BLOW); `out` is the
    level way from the main to the pot. Nothing is placed: the wisps are points of the motion line.
    Returns 0."""
    d = pipes.DIRS[out]
    mouth = tuple(tap[i] + d[i] * (TRAP_SPOUT[0] / 16.0 + 0.03) + (TRAP_SPOUT[1] / 16.0 - 0.03 if i == 1 else 0.0)
                  for i in range(3))
    for tick, speed, (away, up, wind) in BLOW:
        way = tuple(d[i] * away + (up if i == 1 else 0.0) + MK.WIND[i] * wind for i in range(3))
        MK.puff(canvas, mouth, pipes.STEAM, pipes.BREATH, at=(tick,), count=0, spread=way, speed=speed,
                origin=origin, phase=phase)
    return 0


# ---- the heating main of the south wing: its pieces ---------------------------------------------------
# The stretch, in the skeleton's pilasters (pilaster k stands in row S.pilaster_z(k)): the main leaves
# FRONT_FROM northwards, a whole bay to each of FRONT_BAYS (the pilaster at the bay's north end), then
# the bay with the valve, round FRONT_ROUND, and into the wall.
FRONT_FROM = 14
FRONT_BAYS = (13, 12)
FRONT_ROUND = 11
VALVE_AT = 12.8         # the stop valve, texels north of the pilaster the main last comes out of
TRAP_AT = 17.0          # the steam trap, texels north of the valve
LOOP_LEG = 13.0         # the bend round the pilaster: its two legs, texels from the middle of the pilaster
LOOP_JOINT = 21.0       # the joints it is bolted into the line with, the same way
LOOP_OUT = 16.0         # its outer length, texels off the main's line
END_AT = 12.0           # where the main turns into the wall, texels north of the bend's north joint
VALVE_RUN = PITCH - 8.0 - LOOP_JOINT - VALVE_AT         # from the valve north to the bend's south joint


def _bay():
    """A bay of the main, from the face of one pilaster to the face of the next, the anchor half
    way: a plate on either face, the two lengths bolted together in the middle with the ring beside
    the joint, a bracket to each length."""
    m = M.Model(PREFIX + "bay")
    half = BAY / 2.0
    _length(m, -half + 1.0, half - 1.0)
    _plate(m, half, 1)
    _plate(m, -half, -1)
    _joint(m, 0.0)
    _ring(m, JOINT + 1.0)
    for z in (-half / 2.0, half / 2.0):
        _bracket(m, z)
    return m


def _valve_bay():
    """The bay with the stop valve; the anchor is the valve's middle. From the plate on the pilaster
    (at +z) through the valve, past the ring and the steam trap, to the joint of the bend round the
    next pilaster, which is that piece's."""
    m = M.Model(PREFIX + "valve")
    _plate(m, VALVE_AT, 1)
    _length(m, pipes.VALVE[SIZE] - 1.0, VALVE_AT - 1.0)
    _valve(m, 0.0)
    _length(m, -VALVE_RUN, -pipes.VALVE[SIZE] + 1.0)
    _ring(m, -pipes.VALVE[SIZE] - 1.75 - RING_W)
    _trap(m, -TRAP_AT)
    return m


def _loop():
    """The expansion bend round a pilaster; the anchor is the middle of its south joint, on the
    main's line. Copper all the way: out, past the pilaster's face, in again; a joint at either end
    bolts it into the line, a ring in the middle of the outer length says what is in it, and two
    brackets on the pilaster's face carry that length."""
    m = M.Model(PREFIX + "loop")
    mid = -LOOP_JOINT                                   # the middle of the pilaster
    s, n, out = mid + LOOP_LEG, mid - LOOP_LEG, LOOP_OUT
    path = [(0.0, 0.0, 0.0)]
    path += _arc(BEND, s + BEND, 180.0, 270.0)          # from the line out
    path += _arc(out - BEND, s - BEND, 90.0, 0.0)       # and north, along the pilaster's face
    path += _arc(out - BEND, n + BEND, 0.0, -90.0)      # in again
    path += _arc(BEND, n - BEND, 90.0, 180.0)           # and north along the line
    path += [(0.0, 0.0, 2.0 * mid)]
    m.hose(path, R, COPPER, lap=0.3)
    _joint(m, 0.0)
    _joint(m, 2.0 * mid)
    _ring(m, mid - RING_W / 2.0, x=out)
    face = -WALL + 16.0 * S.DEPTH_PILASTER              # the pilaster's face
    for z in (mid - 4.0, mid + 4.0):
        _bracket(m, z, wall=face, x=out)
    return m


def _end():
    """The end of the stretch; the anchor is the corner where the main turns into the wall. It comes
    from the bend's north joint (at +z), wears its ring, bends west and goes in through a plate."""
    m = M.Model(PREFIX + "end")
    count, first = pipes.BOLTS[SIZE]
    m.hose([(0.0, 0.0, END_AT)] + _arc(-WALL, WALL, 0.0, -90.0, rho=WALL), R, COPPER, lap=0.3)
    _ring(m, END_AT - JOINT - 1.0 - RING_W)
    m.tube("x", (0.0, 0.0), -WALL + 0.05, -WALL + 1.5, R + 2.0, K.IRON)
    m.tube("x", (0.0, 0.0), -WALL + 1.5, -WALL + 2.5, R + 0.5, K.IRON_D)
    with m.turned(("y", -90.0)):                        # the bolts of a plate that looks along +x
        pipes._bolts(m, R + 1.25, count, WALL - 2.25, WALL - 1.5, first)
    return m


SPEC = {"bay": _bay, "valve": _valve_bay, "loop": _loop, "end": _end}


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: K.settle(build()) for name, build in SPEC.items()}


def models():
    return dict(_models())


# ---- the heating main of the south wing: where it lies -------------------------------------------------
def front_line():
    """The axis of the heating main along the east front: (x, y)."""
    face = S.WALL_E + 1.0                               # the face of the wings' wall
    return face + OFF, S.PLINTH[1] + 1.0 + OFF


def front_places():
    """Where the pieces of the heating main stand: {piece: [z of its anchor, ...]}, and "trap" and
    "gland", the two places that are under steam."""
    last = float(S.pilaster_z(FRONT_BAYS[-1]))          # the north face of the pilaster before the valve
    turn = S.pilaster_z(FRONT_ROUND) + 0.5              # the middle of the pilaster the bend goes round
    valve = last - VALVE_AT / 16.0
    return {"bay": [S.pilaster_z(k) + 1.0 + BAY / 32.0 for k in FRONT_BAYS], "valve": [valve],
            "loop": [turn + LOOP_JOINT / 16.0], "end": [turn - (LOOP_JOINT + END_AT) / 16.0],
            "trap": [valve - TRAP_AT / 16.0], "gland": [valve]}


def east_front(canvas, origin=(0, 0, 0)):
    """The heating main of the south wing (see the top of the file). Nothing is placed unless the
    wall and the plinth of the stretch stand on the canvas and the main's own way is clear. Returns
    the number of display entities."""
    x, y = front_line()
    ox, oy, oz = origin
    wall, row = int(S.WALL_E), int(S.PLINTH[1]) + 1
    places = front_places()
    for z in (S.pilaster_z(FRONT_FROM) - 1, S.pilaster_z(FRONT_ROUND) + 1, int(math.floor(places["end"][0]))):
        if not pipes._stone(canvas, wall + ox, row + oy, z + oz):           # the wall the main runs along
            return 0
        if not pipes._stone(canvas, wall + 1 + ox, row - 1 + oy, z + oz):   # the plinth it lies over
            return 0
        if pipes._stone(canvas, wall + 1 + ox, row + oy, z + oz):           # and its own way, which is clear
            return 0
    n = 0
    for name in SPEC:
        for z in places[name]:
            n += K.put(canvas, _models()[PREFIX + name], (x, y, z), yaw=0.0, turns=pipes._turns("south", "up"),
                       origin=origin)
    for z in places["gland"]:
        pipes.weep(canvas, "valve_" + SIZE, (x, y, z), "east", origin=origin, phase=pipes.BREATH // 4)
    for z in places["trap"]:
        blow(canvas, (x, y, z), "east", origin=origin)
    return n


def dress(canvas, origin=(0, 0, 0)):
    """The mains in the master scene, on whatever the other lines have built there."""
    return east_front(canvas, origin)


def build(canvas, origin=(0, 0, 0)):
    """What this package places in the master scene: dress(), while DRESS is on."""
    return dress(canvas, origin) if DRESS else 0
