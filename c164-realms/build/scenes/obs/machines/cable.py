"""machines/cable: the cable car and winch at the cable station (plan ART-PLAN 7.2, 5.3;
parts/A5-machines.md 2.7; card packages/machines/cablecar-winch.md).

The station is the spawn and the arrival view V1 (skeleton S.V1). Four pieces, all east or north of
the V1 eye so none crosses its sight line to the building (S.V1 looks west-south-west and up):

  mach_cable_car     the car: a dark-wood body in an iron frame, lit windows, a door to the platform;
                     parked at the head of the track, hard against the station's east edge, so a
                     player who spawns on the platform turns round to "the thing I came up on".
  mach_cable_drum    the winch: a wide iron drum with a cable groove between two spoked wheels
                     (diameter 3), in the machine house behind the car, its big wheel seen from the
                     platform. Movable (A8): it turns about its own axis -- marked DRUM_AXIS below.
  mach_cable_sheave  a grooved guide wheel that turns the haul rope. Two of them: one leads the rope
                     from the drum down to the car, one at the track head turns it onto the descent.
                     Movable (A8): turns about its own axis (local z).
  mach_cable_rope    the steel haul rope: a thin flat-tone bar stretched with M.between, from the
                     drum over the car and down the trestle (site _kit K.cable_ridge) into the cloud.

Scale (A5 1.2, px = scale keeps 16 texels to the block): car 2, drum 2, sheave 1, rope stretched.
Budget (card): about 40 display entities; build() returns how many it placed.
"""
import functools
import math

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..site import _kit as SK        # read only: the ridge the trestle (and so the rope) runs down

PREFIX = "mach_cable_"

# --- materials (palette only) ---------------------------------------------------------------------
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
IRON_F = P.mat("iron_flat")
WOOD = P.mat("dark_wood")
BRASS = P.mat("brass")


def _flat(name, step):
    """One flat tone of a ramp (glass and smooth faces, shaded in the texture not by the engine)."""
    return P.mat(name, kind="flat", base=step, bevel=0)


GLOW_WIN = _flat("glow", 1)         # the warm amber of a lit window, kept dim so the lit area is small
GLOW_HOT = _flat("glow", 2)         # the one hotter tone, only the small panes behind the door

# --- where it all stands (from the skeleton and the site ridge; nothing written down twice) --------
# CABLE_STATION = (75, -40, 91, -26); its platform feet at STATION_GROUND; the track axis leaves the
# east edge in row z = -33 (A4-site 7, site/_kit K.cable_ridge, c221 group #198).
STATION = S.CABLE_STATION
DECK = float(S.STATION_GROUND)              # -4.0, where feet (and the car floor) stand on the platform
EAST = float(STATION[2])                    # 91.0, the east edge column
TRACK_Z = float(SK.CABLE_RIDGE_Z)           # -33.0, the track axis at the station

# The car at the head of the track, body x 89..91 so its west face is east of the V1 eye (x 88.5): it
# frames nothing of the forward view and is seen on turning round. Door and lit windows face the
# platform (west and south). Coordinate with c226 on the exact cell (group #247).
CAR = (90.0, DECK, TRACK_Z)                 # anchor: floor centre
GRIP_Y = DECK + 0.7                         # the haul rope grips the truck at axle height
CAR_GRIP_W = (CAR[0] - 1.0, GRIP_Y, TRACK_Z)   # west grip, up to the winch
CAR_GRIP_E = (CAR[0] + 1.0, GRIP_Y, TRACK_Z)   # east grip, down the trestle

# The winch in the machine house behind the car (north-east corner), its wheel seen from the platform.
DRUM = (85.5, -2.0, -37.0)                  # anchor: the axle centre
DRUM_AXIS = "z"                             # it turns about its own local z (A8)
DRUM_OFFTAKE = (86.9, -2.6, -36.4)          # where the rope leaves the barrel towards the car

SHEAVE_UP = (88.0, -3.1, -35.0)             # leads the rope from the drum down to the car
SHEAVE_HEAD = (EAST + 0.9, -3.9, TRACK_Z)   # at the track head, turns the rope onto the descent
SHEAVE_AXIS = "z"

# The descent down the trestle: points on the ridge raised to the track deck, into the cloud.
DECK_ABOVE_RIDGE = 2.5                      # the trestle deck runs about this far above the rock
CLOUD_TOP = -26                            # sky/terrain: the rope is lost in the cloud below this


def _ridge_point(x):
    """A rope point above the ridge in column x, or None past the end of the ridge."""
    zy = SK.cable_ridge(x)
    if zy is None:
        return None
    z, y = zy
    return (float(x) + 0.5, float(y) + DECK_ABOVE_RIDGE, float(z) + 0.5)


# three spans down the trestle; the last ends in the cloud (K.cable_ridge reaches the cloud top ~x120)
DESCENT = [p for p in (_ridge_point(100), _ridge_point(110), _ridge_point(120)) if p is not None]

ROPE_LEN = 48.0                            # the rope model is this long, along +z (M.between stretches it)
ROPE_THICK = 1.1


# --- the models -----------------------------------------------------------------------------------
def _car():
    """The cable car. Shown at scale 2 (units are eighths of a block, px = 2 keeps 16 texels to the
    block). Anchor: the floor centre. It is parked, so it carries no axis (A8 drives nothing)."""
    m = M.Model(PREFIX + "car", px=2.0)
    HX = HZ = 8.0                            # half footprint, 2 x 2 blocks
    EAVE = 16.0                              # the body is two blocks of wall
    ROOF = 20.0                              # and a roof, 2.5 blocks over all

    # truck under the body: an iron frame on two axles, the rope gripped at both ends
    m.box((-HX, -2.5, -HZ), (HX, 0.0, HZ), IRON, skip="u", grain="x")
    for ax in (-4.5, 4.5):
        m.tube("z", (ax, -1.6), -HZ + 0.6, HZ - 0.6, 0.7, IRON_D)
        for zz in (-HZ + 1.2, HZ - 1.2):
            m.tube("z", (ax, -1.6), zz - 0.8, zz + 0.8, 2.0, IRON)      # wheel
    for sx in (-1.0, 1.0):
        m.box((sx * HX, -2.1, -1.4), (sx * (HX + 2.0), -1.1, 1.4), IRON_D, grain="x")   # draw-gear
        m.tube("x", (-1.6, 0.0), sx * HX, sx * (HX + 2.4), 0.9, IRON)                   # rope socket

    # corner posts (iron), the dark-wood walls set back between them
    for cx in (-HX, HX):
        for cz in (-HZ, HZ):
            x0, x1 = (cx - 1.4, cx) if cx > 0 else (cx, cx + 1.4)
            z0, z1 = (cz - 1.4, cz) if cz > 0 else (cz, cz + 1.4)
            m.box((x0, 0.0, z0), (x1, EAVE, z1), IRON, grain="y")
    m.box((-HX, 0.0, -HZ + 1.3), (HX, 2.0, HZ - 1.3), IRON, grain="y")      # east/west sill
    m.box((-HX + 1.3, 0.0, -HZ), (HX - 1.3, 2.0, HZ), IRON, grain="y")      # north/south sill
    for cz in (-HZ, HZ):                                                    # south, north walls
        z0, z1 = (cz - 1.0, cz) if cz > 0 else (cz, cz + 1.0)
        m.box((-HX + 1.3, 1.5, z0), (HX - 1.3, EAVE, z1), WOOD, grain="y")
    for cx in (-HX, HX):                                                    # east, west walls
        x0, x1 = (cx - 1.0, cx) if cx > 0 else (cx, cx + 1.0)
        m.box((x0, 1.5, -HZ + 1.3), (x1, EAVE, HZ - 1.3), WOOD, grain="y")

    _band_z(m, HZ, 1.0, (-6.3, 6.3), (8.0, 13.0))       # lit windows, south (to the platform)
    _band_x(m, HX, 1.0, (-6.3, 6.3), (8.0, 13.0))       # and east (seen down the descent)
    _band_z(m, -HZ, -1.0, (-6.3, 6.3), (9.5, 13.0))     # a smaller one north (the machine-house side)
    _door(m, -HX, -1.0)                                 # the door, west, to the platform

    # roof: an iron deck with a small overhang and a ridge cap along the way of travel
    m.box((-HX - 1.2, EAVE, -HZ - 1.2), (HX + 1.2, EAVE + 1.5, HZ + 1.2), IRON, grain="x")
    m.box((-HX - 1.5, EAVE + 1.5, -1.3), (HX + 1.5, ROOF, 1.3), IRON_D, grain="x")
    for sx in (-1, 1):                                   # two roof ribs
        m.box((sx * (HX - 3.5) - 0.3, EAVE + 1.5, -HZ - 1.2), (sx * (HX - 3.5) + 0.3, EAVE + 2.6, HZ + 1.2),
              IRON_D, grain="z")
    return m


def _band_z(m, zface, sgn, span, height):
    """A row of lit panes in a wall whose outer face looks along +z (sgn +1) or -z (sgn -1), set in
    the outer skin with iron muntins and a sill and lintel a little proud."""
    x0, x1 = span
    y0, y1 = height
    g0, g1 = (zface - 0.4, zface) if sgn > 0 else (zface, zface + 0.4)
    o0, o1 = (zface, zface + 0.4) if sgn > 0 else (zface - 0.4, zface)
    m.box((x0, y0, g0), (x1, y1, g1), GLOW_WIN, emit=15, shade=False)
    m.box((x0 - 0.7, y0 - 1.0, o0), (x1 + 0.7, y0, o1), IRON_D, grain="x")          # sill
    m.box((x0 - 0.7, y1, o0), (x1 + 0.7, y1 + 1.0, o1), IRON_D, grain="x")          # lintel
    for mx in ((x0 + x1) / 2.0 - 2.1, (x0 + x1) / 2.0 + 2.1):
        m.box((mx - 0.25, y0, o0), (mx + 0.25, y1, o1), IRON_D, grain="y")          # muntins


def _band_x(m, xface, sgn, span, height):
    """As _band_z, for a wall whose outer face looks along x."""
    z0, z1 = span
    y0, y1 = height
    g0, g1 = (xface - 0.4, xface) if sgn > 0 else (xface, xface + 0.4)
    o0, o1 = (xface, xface + 0.4) if sgn > 0 else (xface - 0.4, xface)
    m.box((g0, y0, z0), (g1, y1, z1), GLOW_WIN, emit=15, shade=False)
    m.box((o0, y0 - 1.0, z0 - 0.7), (o1, y0, z1 + 0.7), IRON_D, grain="z")
    m.box((o0, y1, z0 - 0.7), (o1, y1 + 1.0, z1 + 0.7), IRON_D, grain="z")
    for mz in ((z0 + z1) / 2.0 - 2.1, (z0 + z1) / 2.0 + 2.1):
        m.box((o0, y0, mz - 0.25), (o1, y1, mz + 0.25), IRON_D, grain="y")


def _door(m, xface, sgn):
    """The door to the platform, on the west wall: an iron frame round a warm, dim opening (the car
    is lit within); the lit area is small, two narrow panes above a solid lower leaf."""
    o0, o1 = (xface, xface + 0.6) if sgn > 0 else (xface - 0.6, xface)
    g0, g1 = (xface - 0.3, xface) if sgn > 0 else (xface, xface + 0.3)
    m.box((o0, 1.5, -3.6), (o1, 13.0, -3.0), IRON_D, grain="y")                     # frame jambs
    m.box((o0, 1.5, 3.0), (o1, 13.0, 3.6), IRON_D, grain="y")
    m.box((o0, 12.4, -3.6), (o1, 13.0, 3.6), IRON_D, grain="z")                     # frame head
    m.box((g0, 7.5, -2.8), (g1, 12.2, 2.8), GLOW_HOT, emit=15, shade=False)         # lit upper lights
    m.box((xface - 0.2 if sgn > 0 else xface, 2.0, -0.2),
          (xface + 0.2 if sgn > 0 else xface + 0.4, 12.0, 0.2), IRON_D, grain="y")  # meeting stile
    m.box((g0, 2.0, -2.8), (g1, 7.5, 2.8), WOOD, grain="y")                         # lower leaf (solid)


def _drum():
    """The winch drum: a wide iron barrel with a helical cable groove between two spoked wheels
    (diameter 3), on bearing pedestals that stand on the platform. Shown at scale 2. Anchor: the
    axle centre. Movable (A8): it turns about its local z axis (DRUM_AXIS)."""
    m = M.Model(PREFIX + "drum", px=2.0)
    HW = 8.0                                 # half the barrel width (2 blocks between the wheels)
    R = 12.0                                 # the wheel radius (diameter 3)
    RB = 8.5                                 # the barrel radius

    m.tube("z", (0, 0), -HW - 4, HW + 4, 1.6, IRON_D)                       # axle
    m.tube("z", (0, 0), -HW, HW, RB, IRON, sides=12)                        # barrel
    for zz in (4.5, 1.5, -1.5):                                             # cable grooves (open half)
        m.ring("z", (0, 0, zz), RB + 0.3, 1.0, 1.1, IRON_D, sides=12)
    for zz in (-6.6, -5.6, -4.6):                                           # a few turns of wound rope
        m.ring("z", (0, 0, zz), RB + 0.9, 1.1, 0.9, IRON_F, sides=12)
    for zz in (-HW, HW):                                                    # the two wheels
        m.ring("z", (0, 0, zz), R - 1.2, 2.4, 1.6, IRON, sides=16)         # rim
        m.tube("z", (0, 0), zz - 1.0, zz + 1.0, 3.0, IRON_D)              # hub
        for a in range(0, 360, 60):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            m.beam((2.6 * ca, 2.6 * sa, zz), ((R - 2.2) * ca, (R - 2.2) * sa, zz), 1.4, 1.0, IRON_D)
    for zz in (-HW - 2.5, HW + 2.5):                                        # bearing pedestals, to the deck
        m.box((-3.4, -16.0, zz - 2.3), (3.4, -14.0, zz + 2.3), IRON_D, grain="x")   # base plate
        m.box((-2.4, -16.0, zz - 1.6), (2.4, -2.8, zz + 1.6), IRON, grain="y")
        m.tube("z", (0, 0), zz - 1.2, zz + 1.2, 2.6, IRON_D)                        # bearing cap
    return m


def _sheave():
    """A grooved guide wheel on a yoke, turning the haul rope (diameter about 1, scale 1). Anchor:
    the wheel centre. Movable (A8): it turns about its local z axis (SHEAVE_AXIS)."""
    m = M.Model(PREFIX + "sheave", px=1.0)
    R = 7.0
    m.tube("z", (0, 0), -2.2, 2.2, 1.1, IRON_D)                            # axle
    for zz in (-1.4, 1.4):                                                 # two rims, a groove between
        m.ring("z", (0, 0, zz), R - 1.0, 1.8, 1.4, IRON, sides=16)
    m.tube("z", (0, 0), -1.4, 1.4, R - 1.8, IRON_D)                        # groove bottom
    m.tube("z", (0, 0), -1.6, 1.6, 2.6, IRON)                             # hub
    for a in range(0, 360, 90):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        m.rod((2.4 * ca, 2.4 * sa, 0), ((R - 1.9) * ca, (R - 1.9) * sa, 0), 0.7, IRON_D)
    m.box((-1.0, -R - 3.5, -2.4), (1.0, -R + 1.0, 2.4), IRON, grain="y")   # yoke arm
    m.box((-2.2, -R - 4.5, -3.0), (2.2, -R - 3.5, 3.0), IRON_D, grain="x") # foot
    return m


def _rope():
    """The steel haul rope: a thin bar in one flat tone (so stretching smears nothing), along +z
    from the anchor, ROPE_LEN long; M.between stretches it between two points."""
    m = M.Model(PREFIX + "rope", px=1.0)
    m.box((-1.0, -1.0, 0.0), (1.0, 1.0, ROPE_LEN), IRON_F, grain="z")
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {m.name: m for m in (_car(), _drum(), _sheave(), _rope())}


def models():
    return dict(_models())


SCALE = {PREFIX + "car": 2.0, PREFIX + "drum": 2.0, PREFIX + "sheave": 1.0, PREFIX + "rope": 1.0}


# --- placing --------------------------------------------------------------------------------------
def _offer_lights(canvas, origin, lights):
    """Hand the car's warm window light to A2 (sky/_lightkit.take); until that tool is in the tree,
    put the invisible light blocks down here so a test scene is lit (never over a block already set)."""
    ox, oy, oz = origin
    cells = [((int(math.floor(x + ox)), int(math.floor(y + oy)), int(math.floor(z + oz))), int(level))
             for (x, y, z), level in lights]
    try:
        from ..sky import _lightkit
        take = getattr(_lightkit, "take", None)
    except ImportError:
        take = None
    if take is not None:
        take(canvas, cells, "machines/cable")
        return
    for (x, y, z), level in cells:
        canvas.set(x, y, z, f"{B.LIGHT}[level={level}]", keep=True)


def build(canvas, origin=(0, 0, 0)):
    """Place the cable car, the winch and the haul rope at the station. Returns the entity count."""
    built = _models()
    ox, oy, oz = origin
    n = 0

    def place(name, pos, yaw=0.0, **kw):
        nonlocal n
        canvas.add_entity(pos[0] + ox, pos[1] + oy, pos[2] + oz,
                          M.display(built[PREFIX + name], yaw=yaw, scale=SCALE[PREFIX + name], **kw))
        n += 1

    def rope(a, b, thick=ROPE_THICK):
        nonlocal n
        A = (a[0] + ox, a[1] + oy, a[2] + oz)
        Bp = (b[0] + ox, b[1] + oy, b[2] + oz)
        canvas.add_entity(A[0], A[1], A[2], M.between(built[PREFIX + "rope"], A, Bp, thick=thick))
        n += 1

    place("car", CAR)
    place("drum", DRUM)
    place("sheave", SHEAVE_UP)
    place("sheave", SHEAVE_HEAD)

    rope(DRUM_OFFTAKE, SHEAVE_UP)
    rope(SHEAVE_UP, CAR_GRIP_W)
    rope(CAR_GRIP_E, SHEAVE_HEAD)
    prev = SHEAVE_HEAD
    for pt in DESCENT:
        rope(prev, pt)
        prev = pt

    # the car is lit within: a second-rank warm light (A5 1.3) inside it and a spill at the door
    _offer_lights(canvas, origin, [((CAR[0], DECK + 2.0, TRACK_Z), 9),
                                   ((CAR[0] - 1.5, DECK + 1.0, TRACK_Z), 8)])
    return n
