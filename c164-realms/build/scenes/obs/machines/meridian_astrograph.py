"""machines/meridian_astrograph -- the meridian circle in its hut and the astrograph under the small dome.

Card plan/packages/machines/meridian-astrograph.md; detail plan/parts/A5-machines.md 2.9; ART-PLAN 7.2.

Two instruments that share one idea: a brass tube on an axis that is held to ONE plane or one rate.
They are the observatory's measuring instruments, so they are drawn as instruments -- turned brass,
graduated rings, a reading microscope -- and not as furniture.

  the meridian circle, in the hut at (35, -30) with a slit in its roof running north-south
    mach_meridian_tube    the telescope, a slim iron and brass tube, on a horizontal EAST-WEST axis:
                          it swings only in the north-south meridian plane, which is what makes the
                          instrument a meridian circle rather than a telescope (A8 turns it)
    mach_meridian_circle  the great vertical graduated ring, three blocks through, that reads the
                          zenith distance, with its reading microscope on the pier beside it
    mach_meridian_pier    the two masonry piers that carry the axis, one east and one west

  the astrograph, under the small dome at (12, 30) with its shutter facing the slit
    mach_astro_tube       the photographic tube: shorter and fatter than the great refractor, a
                          riveted iron barrel with brass hoops (it photographs, so it is a
                          refractor's tube with a camera at the back instead of an eyepiece)
    mach_astro_back       the camera back: a dark-wood plate holder with its brass slide
    mach_astro_mount      the small equatorial mount: a polar axis tilted to the station's latitude,
                          a declination cradle and two setting circles

The two tubes are built from the same vocabulary as machines/refractor (brass end hoops, riveted
barrel, a graduated ring at each axis), so they read as one family with the big instrument upstairs.

AXES FOR A8. Everything is still (A0 #505). Each tube is anchored on the axis it turns about.

Sizes, the card's: the meridian tube 0.8 through by 4 long; its ring 3 through; the astrograph tube
1.2 through by 6 long. Models are drawn inside the 48-unit span a model may have and shown at the
scale that gives them their real size, with px equal to that scale (A5 1.2), so every picture is 16
pixels to the block.

    from scenes.obs.machines import meridian_astrograph as MA
    n = MA.build(canvas, origin)      # both instruments where the skeleton puts them
"""
import functools
import math

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S

PREFIX = "mach_meridian_"
APREFIX = "mach_astro_"
NAME = "machines/meridian-astrograph"

FACING = {"south": 0.0, "west": 90.0, "north": 180.0, "east": -90.0}

# --- where they stand (the skeleton's numbers) ----------------------------------------------------
HUT_CX, HUT_CZ = S.MERIDIAN_HUT["centre"]          # (35, -30)
HUT_SIZE = S.MERIDIAN_HUT["size"]                  # 9: the hut's plan is 9 x 9
HUT_FEET = S.GROUND                                # the terrace's top: 0
MERIDIAN_X = S.MERIDIAN_X                          # 35, the north-south line the hut straddles

DOMEX0, DOMEX1 = S.SMALL_DOME_X                    # 8..16
DOMEZ0, DOMEZ1 = S.SMALL_DOME_Z                    # 26..34
DOME_CX = (DOMEX0 + DOMEX1 + 1) / 2.0              # 12.5
DOME_CZ = (DOMEZ0 + DOMEZ1 + 1) / 2.0              # 30.5
DOME_FLOOR = S.SMALL_DRUM_BASE                     # 18, the drum's floor the instrument stands on

# --- sizes in model units (16 to the block), each drawn inside the 48-unit span --------------------
TUBE_R = 6.4                        # the meridian tube: 0.8 blocks through
TUBE_LEN = 36.0                     # drawn length; shown at 4 blocks by TUBE_SCALE
TUBE_SCALE = 4.0 * 16.0 / TUBE_LEN  # 1.78
RING_R = 22.0                       # the graduated ring: 3 blocks through when scaled
RING_SCALE = 3.0 * 16.0 / (2.0 * RING_R)          # 1.09
ASTRO_R = 9.6                       # the astrograph tube: 1.2 blocks through
ASTRO_LEN = 36.0                    # drawn length, shown at 6 blocks
ASTRO_SCALE = 6.0 * 16.0 / ASTRO_LEN              # 2.67

# the reading microscope's small lamp (offered to A2 when it is on)
LAMP = True
LAMP_LEVEL = 6

# --- materials (palette only) ---------------------------------------------------------------------
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
IRON_F = P.mat("iron", kind="flat", bevel=0)
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")
BRASS_F = P.mat("brass", kind="flat", bevel=0)
COPPER = P.mat("old_copper")
PORCELAIN = P.mat("porcelain")
WOOD = P.mat("dark_wood")
WOOD_D = P.mat("dark_wood", base=1)
CREAM = P.mat("cream", kind="flat", bevel=0)
PHOSPHOR = P.mat("phosphor")
STONE = P.mat("slate")


# ==================================================================================================
# the graduated ring, shared by both instruments
# ==================================================================================================
def _grad_ring(m, axis, centre, radius, ticks, mat=BRASS, tick_mat=PHOSPHOR, width=1.4):
    """A graduated ring: the brass ring itself, then `ticks` short marks standing out of its face.
    The marks are what make a ring read as a scale rather than a hoop."""
    m.ring(axis, centre, radius - 0.9, 1.8, width, mat, sides=24)
    k = {"x": 0, "y": 1, "z": 2}[axis]
    o1, o2 = [i for i in range(3) if i != k]
    for i in range(ticks):
        a = 2.0 * math.pi * i / ticks
        c = [centre[0], centre[1], centre[2]]
        c[o1] += math.cos(a) * (radius - 0.9)
        c[o2] += math.sin(a) * (radius - 0.9)
        long_mark = (i % 6 == 0)
        half = 1.1 if long_mark else 0.55
        lo = list(c); hi = list(c)
        for d in (o1, o2):
            lo[d] = c[d] - half
            hi[d] = c[d] + half
        lo[k] = centre[k] + width / 2.0
        hi[k] = centre[k] + width / 2.0 + 0.35
        m.box(lo, hi, BRASS if long_mark else tick_mat, skip="d")


# ==================================================================================================
# the meridian circle
# ==================================================================================================
def _pier():
    """The two masonry piers that carry the meridian circle's axis, one east and one west, with their
    iron bearing blocks. Anchor: the middle of the instrument's foot, between them."""
    m = M.Model(PREFIX + "pier", px=1.0, anchor=(0.0, 0.0, 0.0))
    for sx in (-1, 1):
        x = sx * 17.5
        m.box((x - 4.5, 0.0, -4.5), (x + 4.5, 22.0, 4.5), STONE, skip="d")          # the pier
        m.box((x - 5.2, 22.0, -5.2), (x + 5.2, 24.0, 5.2), STONE, skip="d")         # its cap stone
        m.box((x - 3.0, 24.0, -3.0), (x + 3.0, 27.0, 3.0), IRON_D, skip="d")        # the bearing block
        m.tube("x", (0.0, 24.0), x - 3.0, x + 3.0, 1.0, BRASS_D, sides=8)           # the axis journal
    return m


def _meridian_tube():
    """The meridian telescope: a slim riveted tube with brass end hoops and the objective's dew cap.
    Anchor: the middle of the tube, on its east-west axis -- a turn about x swings it in the
    north-south meridian plane, which is the whole point of the instrument."""
    m = M.Model(PREFIX + "tube", px=TUBE_SCALE, anchor=(0.0, 0.0, 0.0))
    r = TUBE_R
    half = TUBE_LEN / 2.0
    m.tube("y", (0.0, 0.0), -half, half, r, IRON, sides=14)                       # the barrel
    for i in range(5):                                                             # its rivet rows
        yy = -half + TUBE_LEN * (i + 0.5) / 5.0
        m.ring("y", (0.0, yy, 0.0), r - 0.8, 1.4, 1.0, IRON_D, sides=14)
    m.tube("y", (0.0, 0.0), half, half + 3.4, r * 1.15, BRASS, sides=14,
           cap=P.mat("brass", kind="flat", base=3, bevel=0))                       # the objective hoop
    m.tube("y", (0.0, 0.0), half + 3.4, half + 5.2, r * 0.95, BRASS_D, sides=14)   # the dew cap
    m.tube("y", (0.0, 0.0), -half - 2.4, -half, r * 1.1, BRASS, sides=14)          # the eyepiece end
    m.tube("y", (0.0, 0.0), -half - 4.0, -half - 2.4, r * 0.6, BRASS_D, sides=10)  # the eyepiece
    # the finder, a small tube alongside the big one on two brass saddles
    m.tube("y", (r + 2.4, 0.0), -half * 0.45, half * 0.45, 1.6, BRASS_F, sides=10)
    for yy in (-half * 0.3, half * 0.3):
        m.box((r - 0.6, yy - 0.7, -1.6), (r + 2.4, yy + 0.7, 1.6), BRASS_D, skip="d")
    return m


def _meridian_circle():
    """The great graduated ring on the tube's east side: the vertical circle that reads the zenith
    distance, with the reading microscope on its rim. Anchor: its centre, on the tube's axis."""
    m = M.Model(PREFIX + "circle", px=RING_SCALE, anchor=(0.0, 0.0, 0.0))
    _grad_ring(m, "x", (0.0, 0.0, 0.0), RING_R - 1.2, 72, width=1.4)
    m.tube("x", (0.0, 0.0), -1.2, 1.2, 3.2, BRASS_D, sides=12)                    # the hub
    for i in range(6):                                                            # the spokes
        a = math.pi * i / 3.0
        m.beam((math.cos(a) * 2.6, math.sin(a) * 2.6, 0.0),
               (math.cos(a) * (RING_R - 2.6), math.sin(a) * (RING_R - 2.6), 0.0), 0.7, 0.6, BRASS)
    return m


def _microscope():
    """The reading microscope that rides the ring's rim: a small brass tube on a bracket with a
    porcelain scale and its little lamp. Anchor: its bracket's foot on the pier's cap."""
    m = M.Model(PREFIX + "micro", px=1.0, anchor=(0.0, 0.0, 0.0))
    m.box((-2.0, 0.0, -2.0), (2.0, 2.0, 2.0), BRASS_D, skip="d")                  # the foot
    m.tube("y", (0.0, 0.0), 2.0, 10.0, 1.2, BRASS, sides=8)                       # the stem
    m.box((-2.6, 10.0, -1.6), (2.6, 12.4, 1.6), BRASS, skip="d")                  # the head
    m.box((-2.0, 9.0, 1.6), (2.0, 10.4, 1.9), PORCELAIN, skip="d")                # the scale
    m.tube("x", (0.0, 8.0), -2.2, 2.2, 1.0, BRASS_D, sides=8)                     # the draw tube
    return m


# ==================================================================================================
# the astrograph
# ==================================================================================================
def _astro_tube():
    """The photographic tube: a short, fat riveted barrel on brass hoops, with the objective cell at
    the sky end and a brass collar where the camera back fits. Anchor: the middle of the tube on its
    axis (a turn about x elevates it)."""
    m = M.Model(APREFIX + "tube", px=ASTRO_SCALE, anchor=(0.0, 0.0, 0.0))
    r = ASTRO_R
    half = ASTRO_LEN / 2.0
    m.tube("y", (0.0, 0.0), -half, half, r, IRON, sides=16)
    for i in range(3):                                                            # three wide hoops
        yy = -half + ASTRO_LEN * (i + 0.5) / 3.0
        m.ring("y", (0.0, yy, 0.0), r - 1.2, 2.2, 2.0, BRASS, sides=16)
    m.tube("y", (0.0, 0.0), half, half + 4.0, r * 1.08, BRASS, sides=16)          # the objective cell
    m.tube("y", (0.0, 0.0), -half - 3.0, -half, r * 1.05, BRASS_D, sides=16)      # the back collar
    for i in range(10):                                                           # a rivet ring
        a = 2.0 * math.pi * i / 10.0
        m.box((math.cos(a) * (r - 0.6) - 0.4, -half + 2.0, math.sin(a) * (r - 0.6) - 0.4),
              (math.cos(a) * (r - 0.6) + 0.4, -half + 3.4, math.sin(a) * (r - 0.6) + 0.4),
              IRON_D, skip="d")
    return m


def _astro_back():
    """The camera back: a dark-wood plate holder with a brass slide, the focusing rack and the
    counterweight arm. Anchor: the middle of the plate frame."""
    m = M.Model(APREFIX + "back", px=1.0, anchor=(0.0, 0.0, 0.0))
    m.box((-7.0, -7.0, 0.0), (7.0, 7.0, 2.6), WOOD_D, skip="d")                   # the holder
    m.box((-5.4, -5.4, 2.6), (5.4, 5.4, 3.4), BRASS_D, skip="d")                  # the brass slide
    m.box((-5.0, -5.0, 3.4), (5.0, 5.0, 3.8), CREAM, skip="d")                    # the plate, edge-on
    m.box((5.4, -1.2, 2.4), (9.0, 1.2, 3.6), BRASS, skip="d")                     # the slide's handle
    for sy in (-1, 1):                                                            # the focusing racks
        m.box((-1.2, sy * 7.0 - 0.8, 0.0), (1.2, sy * 7.0 + 0.8, 3.2), BRASS_D, skip="d")
    return m


def _astro_mount():
    """The small equatorial mount: a polar axis set to the station's latitude, the declination
    cradle, two brass setting circles and the pillar. Anchor: the middle of its foot."""
    m = M.Model(APREFIX + "mount", px=1.0, anchor=(0.0, 0.0, 0.0))
    m.box((-6.0, 0.0, -6.0), (6.0, 3.0, 6.0), IRON_D, skip="d")                   # the pillar foot
    m.tube("y", (0.0, 0.0), 3.0, 20.0, 2.4, IRON, sides=10)                       # the pillar
    # the polar axis: tipped to the latitude, pointing north and up
    with m.aimed((0.0, 20.0, 0.0), (0.0, 34.0, -9.0), axis="y") as reach:
        m.tube("y", (0.0, 0.0), 0.0, reach, 1.6, BRASS_D, sides=10)               # the polar axle
        _grad_ring(m, "y", (0.0, reach * 0.55, 0.0), 6.4, 24, width=1.0)           # the polar circle
    m.box((-3.0, 30.0, -6.0), (3.0, 34.0, 2.0), IRON, skip="d")                   # the declination cradle
    _grad_ring(m, "x", (0.0, 32.0, 2.2), 5.4, 18, width=1.0)                      # the declination circle
    return m


# ==================================================================================================
# the registry
# ==================================================================================================
@functools.lru_cache(maxsize=None)
def _models():
    return {
        PREFIX + "pier": _pier(),
        PREFIX + "tube": _meridian_tube(),
        PREFIX + "circle": _meridian_circle(),
        PREFIX + "micro": _microscope(),
        APREFIX + "tube": _astro_tube(),
        APREFIX + "back": _astro_back(),
        APREFIX + "mount": _astro_mount(),
    }


def models():
    return dict(_models())


# ==================================================================================================
# placing
# ==================================================================================================
def _place(canvas, model, pos, origin, yaw, scale=1.0):
    x, y, z = (pos[i] + origin[i] for i in range(3))
    canvas.add_entity(x, y, z, M.display(model, yaw=yaw, scale=scale, view=6.0))
    return 1


def _offer_lights(canvas, lights, why):
    lights = [((int(x), int(y), int(z)), int(level)) for (x, y, z), level in lights]
    if not lights:
        return
    try:
        from ..sky import _lightkit
        take = getattr(_lightkit, "take", None)
    except ImportError:
        take = None
    if take is not None:
        take(canvas, lights, why)
        return
    for (x, y, z), level in lights:
        canvas.set(x, y, z, f"{B.LIGHT}[level={level}]", keep=True)


def _turn(yaw, v):
    r = math.radians(yaw)
    c, s = math.cos(r), math.sin(r)
    return (v[0] * c - v[2] * s, v[1], v[0] * s + v[2] * c)


# the tube's axis height above the floor (the piers carry it at 24 units = 1.5 blocks)
MERIDIAN_AXIS_Y = 1.55


def meridian(canvas, origin=(0, 0, 0), centre=None):
    """Place the meridian circle in its hut: the two piers, the tube on their axis and the graduated
    ring beside it. Returns (entities, lights)."""
    cx, cz = centre if centre else (float(HUT_CX), float(HUT_CZ))
    n, lights = 0, []
    n += _place(canvas, _models()[PREFIX + "pier"], (cx, HUT_FEET, cz), origin, FACING["south"])
    # the tube lies on the east-west axis, so it is turned a quarter turn: its own +y (its length)
    # points along x, and a turn about the world x swings it in the north-south plane
    n += _place(canvas, _models()[PREFIX + "tube"], (cx, HUT_FEET + MERIDIAN_AXIS_Y, cz), origin,
                FACING["west"], TUBE_SCALE)
    # the graduated ring on the tube's east side, in the same plane as the tube's swing
    n += _place(canvas, _models()[PREFIX + "circle"],
                (cx + 1.15, HUT_FEET + MERIDIAN_AXIS_Y, cz), origin, FACING["south"], RING_SCALE)
    # the reading microscope on the east pier's cap
    n += _place(canvas, _models()[PREFIX + "micro"], (cx + 1.9, HUT_FEET + 1.6, cz + 0.5), origin,
                FACING["south"])
    if LAMP:
        lights.append(((int(cx) + 2, int(HUT_FEET) + 2, int(cz)), LAMP_LEVEL))
    return n, lights


def astrograph(canvas, origin=(0, 0, 0), centre=None, facing="south"):
    """Place the astrograph under the small dome: the mount, the tube on it and the camera back.
    Returns (entities, lights)."""
    cx, cz = centre if centre else (DOME_CX, DOME_CZ)
    yaw = FACING[facing]
    n = 0
    n += _place(canvas, _models()[APREFIX + "mount"], (cx, DOME_FLOOR, cz), origin, yaw)
    # the tube sits in the mount's cradle, tilted up towards the slit
    tube_y = DOME_FLOOR + 2.05
    n += _place(canvas, _models()[APREFIX + "tube"], (cx, tube_y, cz - 0.3), origin, yaw,
                ASTRO_SCALE, )
    # the camera back at the tube's foot (the eyepiece end faces south, down the tube)
    n += _place(canvas, _models()[APREFIX + "back"], (cx, tube_y, cz + 1.55), origin, yaw)
    return n, []


def build(canvas, origin=(0, 0, 0)):
    """Place both instruments where the skeleton puts them; offer A2 the microscope's lamp. Returns
    the display-entity count."""
    n, lights = meridian(canvas, origin)
    got, ls = astrograph(canvas, origin)
    n += got
    lights += ls
    _offer_lights(canvas, lights, NAME)
    return n
