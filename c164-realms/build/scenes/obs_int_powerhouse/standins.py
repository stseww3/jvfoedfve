"""Stand-ins for the machines of the power house: for this test scene only, and only for a machine
whose module is not in the tree yet (machines/engine: the engine, flywheel, belt and dynamo;
machines/boiler: the two boilers; machines/board: the switchboard).

They are plain volumes of the right size at the right place, so that the room can be judged round
them: what a lamp lights, what a pipe or a cable ends on, what the eye meets from the door. They
are nobody's design. Each is anchored in the cell the real machine is lit from.
"""
import functools
import math

from artkit import models as M

from scenes.obs.common import blocks as B
from scenes.obs.common import palette as P
from scenes.obs.interiors import powerhouse as room
from scenes.obs.props import _kit as K

PREFIX = "int_power_standin_"
ALL = room.MACHINES

FLOOR = float(room.FEET)
SHAFT = (77.5, FLOOR + 1.375, 36.5)         # the flywheel's centre (machines/engine: SHAFT_X, H, WHEEL_Z)
WHEEL_R = 2.5
AXIS = (84.25, FLOOR + 1.375, room.LINE_Z)  # a point on the cylinder's axis
DYNAMO = (72.0, FLOOR + 1.1, 37.75)         # the armature's centre
PULLEY_R = 0.45
DRUM_R, DRUM_LEN, DRUM_H = 1.5, 4.0, 2.0    # a boiler: radius, length, the axis over the floor
SLABS = ((26.0, 28.0), (28.0, 31.0), (31.0, 33.0))      # the switchboard's three slabs along z
SLAB_Y = (FLOOR + 1.0, FLOOR + 5.0)
FACE_X = room.BOARD_X + 0.875

WOOD = P.mat("dark_wood")
SLATE = P.mat("slate", base=2)
LEATHER = K.flat("dark_wood", 1)
FIRE = K.flat("glow", 1)


def _wheel(u):
    """u model units to the block."""
    m = M.Model(PREFIX + "wheel")
    r = WHEEL_R * u
    m.ring("z", (0.0, 0.0, 0.0), r - 0.2 * u, 0.4 * u, 0.5 * u, K.IRON, sides=24)
    m.tube("z", (0.0, 0.0), -0.35 * u, 0.35 * u, 0.45 * u, K.IRON_D, sides=12)
    for i in range(6):
        a = math.radians(30.0 + 60.0 * i)
        m.beam((0.3 * u * math.cos(a), 0.3 * u * math.sin(a), 0.0), ((r - 0.3 * u) * math.cos(a), (r - 0.3 * u) * math.sin(a), 0.0),
               0.3 * u, 0.3 * u, K.IRON)
    # the shaft, the crank and its two bearings (z towards the engine's line is negative)
    m.tube("z", (0.0, 0.0), -1.9 * u, 0.9 * u, 0.18 * u, K.flat("iron", 5), sides=8)
    m.tube("z", (0.0, 0.0), -1.45 * u, -1.2 * u, 0.7 * u, K.IRON_D, sides=12)
    for z0, z1 in ((-1.9, -1.55), (0.55, 0.9)):
        m.box((-0.4 * u, -1.375 * u, z0 * u), (0.4 * u, 0.25 * u, z1 * u), K.IRON_D)
    return m


def _engine(u):
    """Bed, slide bars, cylinder, valve chest with the inlet flange. Origin: AXIS."""
    m = M.Model(PREFIX + "engine")

    def at(x, y, z):
        return ((x - AXIS[0]) * u, (y - AXIS[1]) * u, (z - AXIS[2]) * u)

    m.box(at(80.3, FLOOR, 34.3), at(86.3, FLOOR + 0.75, 35.9), K.IRON_D)                            # the bed
    m.tube("x", ((0.0), 0.0), (83.1 - AXIS[0]) * u, (85.7 - AXIS[0]) * u, 0.6 * u, WOOD, sides=12)    # the lagged cylinder
    for x in (83.1, 84.4, 85.7):
        m.tube("x", (0.0, 0.0), (x - 0.08 - AXIS[0]) * u, (x + 0.08 - AXIS[0]) * u, 0.66 * u, K.BRASS, sides=12)
    m.box(at(80.5, AXIS[1] - 0.3, 34.75), at(83.1, AXIS[1] - 0.18, 35.25), K.IRON)                  # the slide bars
    m.box(at(80.5, AXIS[1] + 0.18, 34.75), at(83.1, AXIS[1] + 0.3, 35.25), K.IRON)
    m.box(at(81.3, AXIS[1] - 0.18, 34.8), at(81.8, AXIS[1] + 0.18, 35.2), K.flat("iron", 5))        # the crosshead
    m.tube("x", (0.0, 0.0), (81.8 - AXIS[0]) * u, (83.1 - AXIS[0]) * u, 0.07 * u, K.flat("iron", 5), sides=8)
    m.beam(at(81.5, AXIS[1], 35.0), at(78.05, AXIS[1] + 0.35, 35.0), 0.14 * u, 0.2 * u, K.flat("iron", 5))   # the connecting rod
    top = room.STEAM_IN
    m.box(at(84.5, AXIS[1] - 0.35, 35.45), at(86.2, top[1] - 0.0625, 36.25), K.IRON)                # the valve chest
    cx, cz = at(top[0], 0.0, top[2])[0], at(top[0], 0.0, top[2])[2]
    m.tube("y", (cx, cz), (top[1] - 0.0625 - AXIS[1]) * u, (top[1] - AXIS[1]) * u, 0.3 * u, K.IRON_D, sides=8)
    return m


def _band():
    """A strand of the belt: along +z, 48 long, 7 px wide (x)."""
    m = M.Model(PREFIX + "band")
    m.box((-3.5, -0.4, 0.0), (3.5, 0.4, 48.0), LEATHER, grain="z")
    return m


def _dynamo(u):
    """Bed, two field coils under a yoke, the armature and commutator, the pulley, two terminals.
    Origin: DYNAMO."""
    m = M.Model(PREFIX + "dynamo")

    def at(x, y, z):
        return ((x - DYNAMO[0]) * u, (y - DYNAMO[1]) * u, (z - DYNAMO[2]) * u)

    m.box(at(70.7, FLOOR, 36.9), at(73.3, FLOOR + 0.35, 38.9), K.IRON_D)
    for x in (71.05, 72.95):
        m.box(at(x - 0.3, FLOOR + 0.35, 37.3), at(x + 0.3, FLOOR + 2.0, 38.5), K.IRON)              # the pole pieces
        cx, cz = at(x, 0, 37.9)[0], at(x, 0, 37.9)[2]
        m.tube("y", (cx, cz), (FLOOR + 0.6 - DYNAMO[1]) * u, (FLOOR + 1.75 - DYNAMO[1]) * u, 0.42 * u, K.COPPER, sides=12)
    m.box(at(70.75, FLOOR + 2.0, 37.3), at(73.25, FLOOR + 2.4, 38.5), K.IRON)                       # the yoke
    m.tube("z", (0.0, 0.0), (37.25 - DYNAMO[2]) * u, (38.55 - DYNAMO[2]) * u, 0.5 * u, K.IRON_D, sides=12)       # the armature
    m.tube("z", (0.0, 0.0), (38.55 - DYNAMO[2]) * u, (38.85 - DYNAMO[2]) * u, 0.28 * u, K.COPPER, sides=12)      # the commutator
    m.tube("z", (0.0, 0.0), (36.2 - DYNAMO[2]) * u, (38.95 - DYNAMO[2]) * u, 0.1 * u, K.flat("iron", 5), sides=8)
    m.tube("z", (0.0, 0.0), (36.25 - DYNAMO[2]) * u, (36.75 - DYNAMO[2]) * u, PULLEY_R * u, K.IRON, sides=12)    # the pulley
    for p in room.POWER_OUT:                                                                        # the terminals
        cx, cz = at(p[0], 0, p[2])[0], at(p[0], 0, p[2])[2]
        m.tube("y", (cx, cz), (FLOOR + 2.4 - DYNAMO[1]) * u, (p[1] - 0.2 - DYNAMO[1]) * u, 0.14 * u, P.mat("porcelain"), sides=8)
        m.tube("y", (cx, cz), (p[1] - 0.2 - DYNAMO[1]) * u, (p[1] - DYNAMO[1]) * u, 0.06 * u, K.BRASS, sides=4)
    return m


def _boiler(u):
    """A drum on two saddles, its front plate to -x with the fire door and the ash door, the steam
    dome with its flange. Origin: the middle of the front plate's foot line, one block under the axis."""
    m = M.Model(PREFIX + "boiler")
    ax = 1.0 * u                                    # the axis over the origin
    m.tube("x", (ax, 0.0), 0.12 * u, DRUM_LEN * u, DRUM_R * u, K.IRON, sides=16)
    m.tube("x", (ax, 0.0), 0.0, 0.12 * u, (DRUM_R + 0.06) * u, K.IRON_D, sides=16, cap=K.IRON_D)
    for x in (1.3, 2.6, 3.9):
        m.tube("x", (ax, 0.0), (x - 0.06) * u, (x + 0.06) * u, (DRUM_R + 0.04) * u, K.IRON_D, sides=16)
    for x in (0.7, 3.2):                                                                            # the saddles
        m.box((x * u, -(DRUM_H - 1.0) * u, -1.1 * u), ((x + 0.5) * u, ax - 1.2 * u, 1.1 * u), K.IRON_D)
    m.box((-0.06 * u, ax - 1.05 * u, -0.5 * u), (0.0, ax - 0.35 * u, 0.5 * u), K.IRON_D)            # the fire door
    m.box((-0.08 * u, ax - 0.85 * u, -0.34 * u), (-0.06 * u, ax - 0.55 * u, 0.34 * u), FIRE, emit=15, shade=False)
    m.box((-0.06 * u, ax - 1.38 * u, -0.3 * u), (0.0, ax - 1.15 * u, 0.3 * u), K.IRON_D)            # the ash door
    m.tube("x", (ax + 0.75 * u, 0.0), -0.08 * u, 0.0, 0.2 * u, K.BRASS, sides=12, cap=K.flat("cream", 3))     # the gauge
    dome = (room.STEAM_OUT[0][0] - room.FIRE_X) * u
    top = (room.STEAM_OUT[0][1] - (FLOOR + DRUM_H)) * u + ax
    m.tube("y", (dome, 0.0), ax + (DRUM_R - 0.15) * u, top - 0.1 * u, 0.45 * u, K.IRON, sides=12)
    m.tube("y", (dome, 0.0), top - 0.1 * u, top, 0.55 * u, K.IRON_D, sides=12)
    return m


def _slab(name, wide, u):
    """A slab of the switchboard in its iron frame, `wide` blocks, on a base course. The face looks
    along +x; origin: the middle of the face's foot line at the floor."""
    m = M.Model(PREFIX + name)
    h0, h1 = (SLAB_Y[0] - FLOOR) * u, (SLAB_Y[1] - FLOOR) * u
    half = wide * u / 2.0
    m.box((-0.3 * u, 0.0, -half), (-0.02 * u, h0, half), K.IRON_D)                                  # the base course
    m.box((-0.14 * u, h0, -half + 0.06 * u), (0.0, h1 - 0.06 * u, half - 0.06 * u), SLATE)
    for z0, z1 in ((-half, -half + 0.06 * u), (half - 0.06 * u, half)):
        m.box((-0.2 * u, h0, z0), (0.02 * u, h1, z1), K.IRON)
    m.box((-0.2 * u, h1 - 0.06 * u, -half), (0.02 * u, h1, half), K.IRON)
    count = int(wide)
    for i in range(count):
        z = -half + (i + 0.5) * wide * u / count
        m.tube("x", (h0 + 2.25 * u, z), 0.0, 0.07 * u, 0.3 * u, K.BRASS, sides=12, cap=K.flat("cream", 3))   # a meter
        m.box((0.0, h0 + 0.9 * u, z - 0.05 * u), (0.1 * u, h0 + 1.5 * u, z + 0.05 * u), K.COPPER)             # a knife switch
        m.box((0.0, h0 + 0.82 * u, z - 0.12 * u), (0.06 * u, h0 + 0.9 * u, z + 0.12 * u), P.mat("porcelain"))
    return m


def _leadin(u):
    """The board's two lead-in insulators on a bracket behind its south end. Origin: the top of the
    northern one."""
    m = M.Model(PREFIX + "leadin")
    gap = (room.LEAD_IN[1][2] - room.LEAD_IN[0][2]) * u
    for z in (0.0, gap):
        m.tube("y", (0.0, z), -0.3 * u, 0.0, 0.09 * u, P.mat("porcelain"), sides=8)
        m.tube("y", (0.0, z), -0.36 * u, -0.3 * u, 0.05 * u, K.BRASS_D, sides=4)
    m.box((-0.05 * u, -0.42 * u, -0.1 * u), (0.3 * u, -0.36 * u, gap + 0.1 * u), K.IRON_D)
    return m


U = {"wheel": 16 / 3.0, "engine": 16 / 3.0, "dynamo": 8.0, "boiler": 8.0, "slab": 8.0, "leadin": 16.0}


def missing():
    return tuple(name for name in ALL if name not in room.standing())


@functools.lru_cache(maxsize=None)
def _models():
    """The stand-ins of the machines that are missing: none once all three are in the tree."""
    out, built = missing(), []
    if "engine" in out:
        built += [_wheel(U["wheel"]), _engine(U["engine"]), _band(), _dynamo(U["dynamo"])]
    if "boiler" in out:
        built += [_boiler(U["boiler"])]
    if "board" in out:
        built += [_leadin(U["leadin"])] + [_slab(f"slab_{int(z1 - z0)}", z1 - z0, U["slab"]) for z0, z1 in SLABS[:2]]
    return {m.name: m for m in built}


def models():
    return dict(_models())


def build(c, origin=(0, 0, 0)):
    """Stand a volume in for every machine that is not in the tree; returns the names stood in."""
    ox, oy, oz = origin
    own = _models()

    def put(name, pos, unit):
        return K.put(c, own[PREFIX + name], pos, yaw=0.0, scale=16.0 / unit, origin=origin)

    out = missing()
    if "engine" in out:
        for (x, z) in room.BASE:                                    # the base plates and the flywheel's pit
            c.set(ox + x, oy + room.FLOOR_Y, oz + z, B.IRON_RIVETED.block)
        for (x, z), depth in room.PIT.items():
            for d in range(depth):
                c.clear(ox + x, oy + room.FLOOR_Y - d, oz + z)
            c.set(ox + x, oy + room.FLOOR_Y - depth, oz + z, B.TUFF_BRICK.block)
            for dz in (-1, 1):
                for d in range(1, depth):
                    c.set(ox + x, oy + room.FLOOR_Y - d, oz + z + dz, B.TUFF_BRICK.block, keep=True)
        for x in (min(room.PIT)[0] - 1, max(room.PIT)[0] + 1):
            c.set(ox + x, oy + room.FLOOR_Y - 1, oz + 36, B.TUFF_BRICK.block, keep=True)
        put("wheel", SHAFT, U["wheel"])
        put("engine", AXIS, U["engine"])
        put("dynamo", DYNAMO, U["dynamo"])
        band = own[PREFIX + "band"]
        for side in (1.0, -1.0):                                    # the belt's two strands, from the pulley
            a = (DYNAMO[0] + ox, DYNAMO[1] + side * PULLEY_R + oy, SHAFT[2] + oz)
            b = (SHAFT[0] + ox, SHAFT[1] + side * WHEEL_R + oy, SHAFT[2] + oz)
            c.add_entity(a[0], a[1], a[2], M.between(band, a, b))
        K.offer_lights(c, [((72 + ox, -3 + oy, 37 + oz), 6)], "stand-in: the dynamo's pilot lamp")
    if "boiler" in out:
        for z in room.FIRE_Z:
            put("boiler", (room.FIRE_X - K.NUDGE, FLOOR + DRUM_H - 1.0, z), U["boiler"])
            K.offer_lights(c, [((int(room.FIRE_X) - 2 + ox, int(FLOOR) + 1 + oy, int(z) + oz), 10)], "stand-in: a fire door")
    if "board" in out:
        for z0, z1 in SLABS:
            put(f"slab_{int(z1 - z0)}", (FACE_X + 0.13, FLOOR, (z0 + z1) / 2.0), U["slab"])
        first = min(room.LEAD_IN, key=lambda p: p[2])
        put("leadin", first, U["leadin"])
    return out
