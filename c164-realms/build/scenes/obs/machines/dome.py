"""machines/dome: the gear of the great dome (plan ART-PLAN 5.2 and 7.2; parts/A5-machines.md 2.2;
card packages/machines/domegear.md). What turns the dome and what opens its slit, seen from the
dome room (view V8, in one picture with the great refractor).

ROUGH MASSING: sizes and places only, the detail comes in the next commits.

Two trains, each to be read from the hand to the load:

  turning the dome   a ring rail on the ledge of the drum's top course; under every rib foot a truck
                     with a flanged wheel on the rail; a hand gear on the floor whose shaft climbs
                     the wall to a pinion in the toothed ring of the dome's foot
  opening the slit   a cross shaft at the foot of the slit with a chain wheel on either side; the
                     shutter's two chains run over them, up the edges of the slit and down to a
                     counterweight each

The shell, its ribs and the edge beams of the slit are main's and interiors'; this package only
places the moving gear. Moving pieces are models of their own with a marked axis (plan 7.1), for
the motion category: the counterweights rise and fall (WEIGHT_TRAVEL), the hand wheel spins about
its shaft, the travelling ring turns about TURN_AXIS.
"""
import functools
import math

from artkit import models as M

from ..common import palette as P
from ..common import skeleton as S

PREFIX = "mach_dome_"
MOVED_IN = False                    # the master scene gets the gear once the shell and the room are in the assembly

IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
COPPER = P.mat("old_copper")
BRASS = P.mat("brass")

# ---- where things are: all from the skeleton ----------------------------------------------------
AX, AZ = S.DOME_AXIS                # the point the dome turns about
TURN_AXIS = (AX, AZ)                # vertical, through this point
FLOOR_Y = float(S.ROOF_STAND)       # 18.0: feet on the dome-room floor
SEAT_Y = float(S.DOME_SPRING)       # 24.0: the top of the drum's last course, the ledge the rail lies on
ROOM_R = S.DOME_ROOM_DIAM / 2.0 + 0.5   # 11.5: the drum's inner face on the axes
RAIL_R = ROOM_R + 0.3               # the rail's centre line: on the ledge, clear of the dome's foot ring
GORES = 20                          # main/_dome.GORES: a truck under every seam between two gores
CHAIN_Z = S.SLIT_W / 2.0 - 0.2      # 2.3: the chains run on the slit's side of its edge beams (interiors')
SHAFT_X = -(ROOM_R - 0.9)           # the cross shaft, from the dome's axis (the slit looks west)
SHAFT_Y = SEAT_Y + 0.45
WEIGHT_Y = FLOOR_Y + 1.2            # the counterweights' underside with the slit open
WEIGHT_TRAVEL = 3.0                 # they rise this far when the slit is shut
GEAR_DEG = 243.0                    # the hand gear stands at this seam (north-west), 0 = east, 90 = south

SEG_SCALE = 2
U = 16.0 / SEG_SCALE                # model units to a block in the pieces drawn at scale 2


def seam_angles():
    return [(k + 0.5) * 360.0 / GORES for k in range(GORES)]


def _arc(m, r, y0, y1, thick, mat, span, n=3, **kw):
    """A stretch of ring about the dome's axis, `span` degrees wide and centred on the model's +x,
    drawn as n straight pieces. r, thick, y0, y1 in model units; the model's origin lies on the
    ring's radius r0 = RAIL_R."""
    r0 = RAIL_R * 16.0 / m.px
    step = span / n
    half = (r + thick / 2.0) * math.tan(math.radians(step / 2.0))
    for i in range(n):
        a = math.radians(-span / 2.0 + step * (i + 0.5))
        cx, cz = r * math.cos(a) - r0, r * math.sin(a)
        m.box((cx - thick / 2.0, y0, cz - half), (cx + thick / 2.0, y1, cz + half), mat,
              rot=("y", -math.degrees(a), (cx, (y0 + y1) / 2.0, cz)), grain="z", **kw)


def _segment():
    """One gore's share of the ring: the rail on its sole plates and the truck under the rib foot.
    Radially outwards is +x; the anchor is on the ledge under the wheel."""
    m = M.Model(PREFIX + "seg", px=SEG_SCALE)
    span = 360.0 / GORES
    r = RAIL_R * U
    _arc(m, r, 0.0, 0.5, 3.0, IRON_D, span, seed=11)        # foot
    _arc(m, r, 0.5, 1.5, 1.0, IRON, span, seed=12)          # web
    _arc(m, r, 1.5, 2.0, 2.0, IRON, span, seed=13)          # head
    m.tube("x", (5.0, 0.0), -0.75, 0.75, 3.0, IRON, sides=12)           # the wheel's tread
    m.tube("x", (5.0, 0.0), -1.25, -0.75, 3.5, IRON_D, sides=12)        # its flange, on the room's side
    m.tube("x", (5.0, 0.0), -2.0, 2.0, 0.6, IRON_D, sides=8)            # the axle
    for x0, x1 in ((-2.0, -1.5), (1.5, 2.0)):                           # the truck's two cheeks
        m.box((x0, 4.0, -2.5), (x1, 8.0, 2.5), IRON_D)
    m.box((-2.0, 7.5, -3.0), (5.0, 8.0, 3.0), IRON)                     # its top plate, out to the dome's foot
    return m


def _shaft():
    """The cross shaft at the slit's foot with its two chain wheels and bearings. Runs along z;
    the anchor is its middle."""
    m = M.Model(PREFIX + "shaft", px=3)
    u = 16.0 / 3
    half = (CHAIN_Z + 0.6) * u
    m.tube("z", (0.0, 0.0), -half, half, 0.4, IRON, sides=8)
    for s in (-1, 1):
        z = s * CHAIN_Z * u
        m.tube("z", (0.0, 0.0), z - 0.5, z + 0.5, 1.6, IRON_D, sides=12)        # chain wheel
        zb = s * (CHAIN_Z + 0.45) * u
        m.box((-0.8, -2.4, zb - 0.4), (0.8, 0.6, zb + 0.4), IRON_D)             # bearing bracket
    return m


def _chain(name, blocks, scale):
    """A run of chain `blocks` long along +z from the anchor, drawn at `scale`."""
    m = M.Model(PREFIX + name, px=scale)
    u = 16.0 / scale
    n = max(1, int(round(blocks * 16.0 / 5.0)))
    link = blocks * u / n
    for i in range(n):
        z0 = i * link
        size = (0.5 / scale, 1.5 / scale) if i % 2 else (1.5 / scale, 0.5 / scale)
        m.box((-size[0], -size[1], z0), (size[0], size[1], z0 + link), IRON, seed=21 + i % 2, grain="z")
    return m


def _weight():
    """A counterweight: a stack of old-copper slabs on an iron hanger. The anchor is the eye on top."""
    m = M.Model(PREFIX + "weight", px=1)
    m.box((-0.75, -4.0, -0.75), (0.75, 0.0, 0.75), IRON_D)
    for i in range(4):
        m.box((-5.0, -8.0 - 4.0 * i, -3.5), (5.0, -4.5 - 4.0 * i, 3.5), COPPER, seed=31)
    m.box((-5.5, -21.0, -4.0), (5.5, -20.0, 4.0), IRON_D)
    return m


def _gear():
    """The hand gear: a cast pedestal on the floor, its back to the wall (+x), and the shaft's foot.
    The anchor is on the floor under the shaft."""
    m = M.Model(PREFIX + "gear", px=1)
    m.box((-5.0, 0.0, -4.0), (3.0, 1.5, 4.0), IRON_D)
    m.box((-3.5, 1.5, -2.5), (2.0, 15.0, 2.5), IRON)
    m.tube("y", (0.0, 0.0), 15.0, 22.0, 1.0, IRON_D, sides=8)
    m.tube("x", (18.0, 0.0), -7.0, -3.5, 0.8, IRON_D, sides=8)
    return m


def _handwheel():
    """The hand wheel: spins about its shaft (the model's x axis through the anchor)."""
    m = M.Model(PREFIX + "handwheel", px=1)
    m.ring("x", (0.0, 0.0, 0.0), 6.0, 1.0, 1.0, BRASS, sides=16)
    for i in range(3):
        m.box((-0.4, -6.0, -0.5), (0.4, 6.0, 0.5), IRON, rot=("x", 60.0 * i, (0.0, 0.0, 0.0)), seed=41)
    m.tube("x", (0.0, 0.0), -1.0, 1.0, 1.2, IRON_D, sides=8)
    return m


def _riser():
    """The shaft from the hand gear up the wall to the pinion in the toothed ring. Runs up from the anchor."""
    m = M.Model(PREFIX + "riser", px=2)
    top = (SEAT_Y + 0.5 - FLOOR_Y - 1.3) * U
    m.tube("y", (0.0, 0.0), 0.0, top, 0.5, IRON, sides=8)
    m.tube("y", (0.0, 0.0), top - 1.0, top, 2.5, IRON_D, sides=12)      # the pinion
    return m


FALL = SHAFT_Y - 0.3 - (WEIGHT_Y + 1.3)     # the hanging run of chain, shaft to counterweight
RISE = 14.0                                  # the run up the slit's edge (rough: one straight stretch)


@functools.lru_cache(maxsize=None)
def _models():
    return {m.name: m for m in (_segment(), _shaft(), _chain("fall", FALL, 2), _chain("rise", RISE, 5), _weight(),
                                _gear(), _handwheel(), _riser())}


def models():
    return dict(_models())


def _put(canvas, name, pos, scale, yaw=0.0, turns=()):
    canvas.add_entity(pos[0], pos[1], pos[2], M.display(_models()[PREFIX + name], yaw=yaw, scale=scale, turns=turns))
    return 1


def _run(canvas, name, a, b, scale):
    m = _models()[PREFIX + name]
    length = math.dist(a, b) * 16.0 / scale
    canvas.add_entity(a[0], a[1], a[2], M.between(m, a, b, thick=scale, length=length))
    return 1


def place(canvas, origin=(0, 0, 0)):
    """The whole gear round DOME_AXIS. Returns the number of display entities."""
    ox, oy, oz = origin
    x0, z0 = ox + AX, oz + AZ
    n = 0
    for a in seam_angles():
        r = math.radians(a)
        n += _put(canvas, "seg", (x0 + RAIL_R * math.cos(r), oy + SEAT_Y, z0 + RAIL_R * math.sin(r)), SEG_SCALE, yaw=a)
    n += _put(canvas, "shaft", (x0 + SHAFT_X, oy + SHAFT_Y, z0), 3)
    for s in (-1, 1):
        z = z0 + s * CHAIN_Z
        top = (x0 + SHAFT_X + 0.3, oy + SHAFT_Y, z)
        eye = (top[0], oy + WEIGHT_Y + 1.3, z)
        n += _run(canvas, "fall", top, eye, 2)
        n += _put(canvas, "weight", eye, 1)
        foot = (x0 + SHAFT_X - 0.3, oy + SHAFT_Y, z)
        k = RISE / math.hypot(11.0, 11.3)
        n += _run(canvas, "rise", foot, (foot[0] + 11.0 * k, foot[1] + 11.3 * k, z), 5)
    r = math.radians(GEAR_DEG)
    ux, uz = math.cos(r), math.sin(r)
    at = ROOM_R - 0.6
    foot = (x0 + at * ux, oy + FLOOR_Y, z0 + at * uz)
    n += _put(canvas, "gear", foot, 1, yaw=GEAR_DEG)
    n += _put(canvas, "handwheel", (foot[0] - 0.45 * ux, foot[1] + 1.1, foot[2] - 0.45 * uz), 1, yaw=GEAR_DEG)
    n += _put(canvas, "riser", (foot[0], foot[1] + 1.3, foot[2]), SEG_SCALE, yaw=GEAR_DEG)
    return n


def build(canvas, origin=(0, 0, 0)):
    return place(canvas, origin) if MOVED_IN else 0
