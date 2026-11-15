"""machines/switchboard_boiler -- the marble switchboard and the boiler of the power house.

Card plan/packages/machines/switchboard-boiler.md; detail plan/parts/A5-machines.md 2.6; ART-PLAN 7.2.

Two families in one card, and one thing in common: they face each other across the room, and the
boiler's fire is what V6 sees glowing through the house's fire windows.

  mach_board_frame     the marble switchboard: a slate slab on two brackets, with a riveted brass
                       cornice and a slate kerb at its foot. The dials, knife switches and bells on
                       its face are the panel blocks (materials/panels, B.PANELS); this package makes
                       only what stands out of the slab.
  mach_board_knife     a bank of three big knife switches: brass blades on porcelain bases, each with
                       its own porcelain handle, on a brass bus bar
  mach_board_meter     the big round meter: a brass ring, a cream face, phosphor graduations and a
                       still pointer (A8 turns it)
  mach_board_leads     the porcelain insulators and the brass bus where the dynamo's cables come in

  mach_boiler_body     the boiler: a riveted iron drum four blocks tall, banded with three iron
                       hoops, on a firebrick plinth
  mach_boiler_door     the fire door: an iron door with its hinge strap, the draught slots and the
                       glowing fire mouth inside (emit, kept to the mouth only)
  mach_boiler_gauge    the safety valve and the two big gauges on their brass stand pipes

WHERE THE FIRE FACES. The house's own window table says which bays glow: north bay 4 at x 81..83 and
east bay 2 at z 26..28, both at y -3..-1. So the boiler stands with its fire door towards the north
wall, its mouth on the axis of that window, and the fire light is offered to A2 one cell inside the
mouth. `FIRE_AXIS` below is read from site/powerhouse.windows() rather than guessed.

AXES FOR A8. Everything is still (A0 #505). The knife blades and the two pointers are separate models
anchored where they turn.

Sizes: the boiler is three blocks through and four tall (the card); the switchboard is 3 x 0.5 x 3.
Models are drawn inside 48 units and shown at the scale that gives them their real size, with px
equal to that scale, so every picture is 16 pixels to the block (A5 1.2).

    from scenes.obs.machines import switchboard_boiler as SB
    n = SB.build(canvas, origin)          # both families in the power house
"""
import functools
import math

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S

PREFIX = "mach_board_"
BPREFIX = "mach_boiler_"
NAME = "machines/switchboard-boiler"

FACING = {"south": 0.0, "west": 90.0, "north": 180.0, "east": -90.0}

# --- the power house (skeleton), and the bays its window table says glow
PH = S.POWER_HOUSE
X0, Z0, X1, Z1 = PH["box"]          # 67, 20, 89, 42
FEET = PH["base_y"]                 # -6
WALL_H = PH["wall_h"]               # 10
EAVES = FEET + WALL_H - 1           # 3

# site/powerhouse.windows() storey "furnace": north bay 4 at x 81..83, east bay 2 at z 26..28, y -3..-1
FIRE_AXIS = dict(front="north", x=(81, 83), z=Z0, y=(-3, -1))
FIRE_MID_X = (FIRE_AXIS["x"][0] + FIRE_AXIS["x"][1] + 1) / 2.0     # 82.5, the window's centre

# where the boiler stands: its fire door on the window's axis, the drum back from the north wall so
# the mouth looks straight at the glass
BOILER_R = 21.0                     # drawn radius: an 18-sided tube spans a little over 2r
BOILER_SCALE = 3.0 * 16.0 / (2.0 * BOILER_R)      # 1.09: 44 units draw 3 blocks
BOILER_H = 4.0                      # the drum's height, blocks (the card)
BOILER_LOWER = 2.2                  # the lower section's height in blocks; the rest is the upper one
BOILER_C = (FIRE_MID_X, FEET, Z0 + 3.2)           # its centre: 3.2 blocks into the room from the wall

# where the switchboard stands: on the west wall, its face looking east into the room
BOARD_W, BOARD_T, BOARD_H = 3.0, 0.5, 2.75        # the card says 3; 2.75 leaves the cornice inside 48 units
BOARD_HALF = BOARD_W / 2.0                         # each half of the slab: 1.5 blocks (a model may span 3)
BOARD_AT = (X0 + 1.2, FEET, Z0 + 9.0)             # against the west wall, mid-room

# --- lights (offered to A2)
FIRE_LEVEL = 9                      # the fire mouth: second rank
METER_LEVEL = 6                     # the meter's phosphor: third rank
LIGHTS_ON = True

# the scales the fittings are shown at; px equals each, so the picture is 16 pixels to the block
KNIFE_SCALE = 1.1
GAUGE_SCALE = 1.4

# --- materials (palette only)
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
IRON_F = P.mat("iron", kind="flat", bevel=0)
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")
COPPER = P.mat("old_copper")
PORCELAIN = P.mat("porcelain")
SLATE = P.mat("slate")
SLATE_D = P.mat("slate", base=1)
CREAM = P.mat("cream", kind="flat", bevel=0)
PHOSPHOR = P.mat("phosphor")
SIGNAL = P.mat("signal")
GLOW = [P.mat("glow", kind="flat", base=i, bevel=0) for i in range(len(P.RAMPS["glow"]))]


# ==================================================================================================
# the switchboard
# ==================================================================================================
def _frame():
    """ONE SECTION of the marble switchboard: a slate slab with the brass cornice over it and the slate
    kerb at its foot, with its iron bracket. Anchor: the middle of the section's bottom edge; sections
    stand side by side, so `build()` places two and the face reads as one 3-block board."""
    m = M.Model(PREFIX + "frame", px=1.0, anchor=(0.0, 0.0, 0.0))
    hw, hd = BOARD_HALF * 16.0 / 2.0, BOARD_T * 16.0 / 2.0
    top = BOARD_H * 16.0
    m.box((-hw, 1.6, -hd), (hw, top, hd * 0.4), SLATE, skip="d")             # the slab
    m.box((-hw, 1.6, -hd), (hw, 3.6, hd * 0.6), SLATE_D, skip="d")          # the kerb
    m.box((-hw, top, -hd), (hw, top + 3.0, hd * 0.8), BRASS, skip="d")       # the cornice
    for x in (-hw + 3.0, hw - 3.0):                                          # the cornice's rivets
        m.box((x - 0.6, top + 1.0, hd * 0.8), (x + 0.6, top + 2.2, hd * 0.8 + 0.5), BRASS_D, skip="d")
    m.box((-1.2, 1.6, -hd - 2.0), (1.2, 4.0, -hd), IRON, skip="d")          # the bracket
    return m


def _knife():
    """A bank of three knife switches: porcelain bases, brass blades with porcelain handles, and the
    brass bus bar they hang from. Anchor: the middle of the bus bar, on the board's face."""
    m = M.Model(PREFIX + "knife", px=KNIFE_SCALE, anchor=(0.0, 0.0, 0.0))
    m.box((-14.0, -1.2, 0.0), (14.0, 1.2, 1.6), BRASS_D, skip="d")            # the bus bar
    for i, x in enumerate((-9.0, 0.0, 9.0)):
        m.box((x - 3.0, -3.0, 0.0), (x + 3.0, 3.0, 2.6), PORCELAIN, skip="d")   # the base
        m.box((x - 1.0, -11.0, 2.6), (x + 1.0, 6.0, 3.8), BRASS, skip="d")      # the blade
        m.box((x - 1.6, 6.0, 1.2), (x + 1.6, 9.0, 4.2), PORCELAIN, skip="d")    # its handle
        m.box((x - 2.2, -12.0, 1.6), (x + 2.2, -10.0, 3.0), BRASS_D, skip="d")  # the jaw
    return m


def _meter():
    """The big round meter: a brass ring, a cream face, phosphor graduations and a still pointer.
    Anchor: the middle of its face, on the board."""
    m = M.Model(PREFIX + "meter", px=1.0, anchor=(0.0, 0.0, 0.0))
    r = 7.5
    m.ring("z", (0.0, 0.0, 0.8), r, 2.2, 1.6, BRASS, sides=20)                # the bezel
    m.tube("z", (0.0, 0.0), 0.0, 0.8, r, CREAM, sides=20)                     # the face
    for i in range(9):                                                        # the graduations
        a = math.radians(150.0 + i * 30.0)
        px_, py_ = math.cos(a) * (r - 2.0), math.sin(a) * (r - 2.0)
        m.box((px_ - 0.4, py_ - 0.4, 0.8), (px_ + 0.4, py_ + 0.4, 0.9), PHOSPHOR, skip="d")
    m.box((-0.3, 0.0, 0.8), (0.3, r - 2.6, 0.9), IRON_D, skip="d")             # the pointer, up
    m.tube("z", (0.0, 0.0), 0.8, 1.1, 0.9, IRON_D, sides=8)                    # the hub
    return m


def _leads():
    """The porcelain insulators and the brass bus where the dynamo's cables land. Anchor: the middle
    of the bus, on the board's lower face."""
    m = M.Model(PREFIX + "leads", px=1.0, anchor=(0.0, 0.0, 0.0))
    m.box((-12.0, -0.8, 0.0), (12.0, 0.8, 1.4), BRASS, skip="d")
    for x in (-8.0, -3.0, 3.0, 8.0):
        m.tube("y", (x, 0.0), 0.8, 4.4, 1.5, PORCELAIN, sides=8)               # the insulators
        m.tube("y", (x, 0.0), 4.4, 5.0, 0.9, BRASS_D, sides=8)                 # their caps
    return m


# ==================================================================================================
# the boiler
# ==================================================================================================
def _body():
    """The boiler drum, LOWER section: the firebrick plinth, the barrel from the plinth to the lower
    band, two hoops and the rivet ring round the foot. Anchor: the middle of its foot, on the floor.

    The drum is four blocks tall and a model may span three, so the upper section (`_body_top`) is a
    second entity stacked on this one -- the same split as the bed plate and the pneumatic pipe."""
    m = M.Model(BPREFIX + "body", px=BOILER_SCALE, anchor=(0.0, 0.0, 0.0))
    r = BOILER_R
    top = BOILER_LOWER * 16.0 / BOILER_SCALE
    m.tube("y", (0.0, 0.0), 4.0, top, r, IRON, sides=18)                     # the barrel
    m.tube("y", (0.0, 0.0), 0.0, 4.0, r * 1.04, IRON_D, sides=18)            # the plinth
    for yy in (top * 0.45, top - 1.2):                                        # two hoops
        m.ring("y", (0.0, yy, 0.0), r - 0.6, 2.0, 2.2, IRON_D, sides=18)
    for i in range(12):                                                       # the rivet ring
        a = 2.0 * math.pi * i / 12.0
        m.box((math.cos(a) * (r - 1.0) - 0.5, 5.0, math.sin(a) * (r - 1.0) - 0.5),
              (math.cos(a) * (r - 1.0) + 0.5, 6.4, math.sin(a) * (r - 1.0) + 0.5), IRON_D, skip="d")
    return m


def _body_top():
    """The boiler drum, UPPER section: the top band of the barrel with its third hoop, the domed head
    and the steam stub. Anchor: its own foot, which sits on the lower section's top."""
    m = M.Model(BPREFIX + "body_top", px=BOILER_SCALE, anchor=(0.0, 0.0, 0.0))
    r = BOILER_R
    h = (BOILER_H - BOILER_LOWER) * 16.0 / BOILER_SCALE
    m.tube("y", (0.0, 0.0), 0.0, h, r, IRON, sides=18)                       # the top band
    m.ring("y", (0.0, h - 1.4, 0.0), r - 0.6, 2.0, 2.2, IRON_D, sides=18)    # the third hoop
    m.taper("y", (0.0, 0.0), h, h + 5.0, r, r * 0.75, IRON, sides=18, steps=3)   # the dome
    m.tube("y", (0.0, 0.0), h + 5.0, h + 9.0, 2.4, IRON_D, sides=10)         # the steam stub
    return m


def _door():
    """The fire door: an iron door with its hinge strap, the draught slots under it and the glowing
    fire mouth behind. Anchor: the middle of the door, on the drum's face; the mouth faces -z."""
    m = M.Model(BPREFIX + "door", px=BOILER_SCALE, anchor=(0.0, 0.0, 0.0))
    w, h = 12.0, 14.0
    m.box((-w / 2.0, -h / 2.0, 0.0), (w / 2.0, h / 2.0, 1.6), IRON, skip="d")     # the door
    m.box((-w / 2.0 - 1.0, -h / 2.0 - 1.0, 0.0), (w / 2.0 + 1.0, -h / 2.0, 2.0), IRON_D, skip="d")
    m.box((-w / 2.0, h / 2.0, 0.0), (w / 2.0, h / 2.0 + 1.6, 2.0), IRON_D, skip="d")   # the lintel
    m.box((-3.0, 2.0, 1.6), (3.0, 8.0, 1.8), GLOW[2], skip="d")                    # the fire mouth
    for i in range(3):                                                            # the draught slots
        m.box((-3.4, -5.4 + i * 1.6, 1.6), (3.4, -4.6 + i * 1.6, 1.8), GLOW[1], skip="d")
    m.box((w / 2.0 - 3.0, -1.0, 1.6), (w / 2.0 - 1.4, 1.0, 2.6), BRASS_D, skip="d")   # the latch
    m.box((-w / 2.0, 1.0, 1.6), (-w / 2.0 + 7.0, 2.2, 2.0), BRASS_D, skip="d")        # the hinge strap
    return m


def _gauge():
    """The safety valve and the two big gauges on their brass stand pipes. Anchor: the middle of the
    valve's foot."""
    m = M.Model(BPREFIX + "gauge", px=GAUGE_SCALE, anchor=(0.0, 0.0, 0.0))
    m.box((-1.6, 0.0, -1.6), (1.6, 2.0, 1.6), BRASS_D, skip="d")                  # the foot
    m.tube("y", (0.0, 0.0), 2.0, 12.0, 1.2, BRASS, sides=8)                        # the stand pipe
    m.tube("y", (0.0, 0.0), 12.0, 14.0, 2.4, BRASS_D, sides=10)                    # the valve body
    m.box((-0.5, 14.0, -0.5), (0.5, 17.0, 0.5), SIGNAL, skip="d")                  # the lever, red
    m.ball((0.0, 17.4, 0.0), 1.4, SIGNAL, sides=8, layers=4)                       # its weight
    for sx in (-1, 1):                                                            # the two gauges
        m.tube("x", (sx * 4.0, 10.0), 0.0, sx * 4.0, 0.9, BRASS_D, sides=8)
        m.tube("z", (sx * 4.0, 10.0), 0.0, 1.2, 3.2, BRASS, sides=12)
        m.tube("z", (sx * 4.0, 10.0), 1.2, 1.6, 2.6, CREAM, sides=12)
        m.box((sx * 4.0 - 0.3, 10.0, 1.6), (sx * 4.0 + 0.3, 12.2, 1.7), IRON_D, skip="d")
    return m


# ==================================================================================================
# the registry
# ==================================================================================================
@functools.lru_cache(maxsize=None)
def _models():
    return {
        PREFIX + "frame": _frame(),
        PREFIX + "knife": _knife(),
        PREFIX + "meter": _meter(),
        PREFIX + "leads": _leads(),
        BPREFIX + "body": _body(),
        BPREFIX + "body_top": _body_top(),
        BPREFIX + "door": _door(),
        BPREFIX + "gauge": _gauge(),
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


def boiler(canvas, origin=(0, 0, 0), centre=None):
    """Place the boiler with its fire door towards the north window. `centre` is (x, z) of the drum's
    axis; the default puts the mouth on the window's axis. Returns (entities, lights)."""
    cx, cz = centre if centre else (BOILER_C[0], BOILER_C[2])
    n, lights = 0, []
    yaw = FACING["north"]                     # the door looks north (the model's +z turned to -z)
    n += _place(canvas, _models()[BPREFIX + "body"], (cx, FEET, cz), origin, yaw, BOILER_SCALE)
    n += _place(canvas, _models()[BPREFIX + "body_top"], (cx, FEET + BOILER_LOWER, cz), origin, yaw,
                BOILER_SCALE)
    # the door on the drum's north face
    door_far = cz - BOILER_R / 16.0 * BOILER_SCALE
    n += _place(canvas, _models()[BPREFIX + "door"], (cx, FEET + 1.7, door_far), origin, yaw,
                BOILER_SCALE)
    # the valve and gauges on the drum's west side, clear of the door
    n += _place(canvas, _models()[BPREFIX + "gauge"],
                (cx - BOILER_R / 16.0 * BOILER_SCALE - 0.2, FEET, cz), origin, FACING["west"],
                GAUGE_SCALE)
    # the fire light: one cell inside the mouth, at the middle of the mouth's height
    if LIGHTS_ON:
        lights.append(((int(cx), int(FEET + 1.7), int(door_far) - 1), FIRE_LEVEL))
    return n, lights


def board(canvas, origin=(0, 0, 0), at=None, facing="east"):
    """Place the switchboard against a wall. `at` is the point on the floor at the middle of its
    foot; facing is the way its face looks. Returns (entities, lights)."""
    x, y, z = at if at else BOARD_AT
    yaw = FACING[facing]
    n, lights = 0, []
    # two half sections side by side make the 3-block board
    side = _turn(yaw, (BOARD_HALF, 0.0, 0.0))
    for sgn in (-1, 1):
        n += _place(canvas, _models()[PREFIX + "frame"],
                    (x + sgn * side[0] / 2.0, y, z + sgn * side[2] / 2.0), origin, yaw)
    # the three fittings stand on the slab's face, a hand apart
    face = 0.34                                  # blocks out from the anchor to the face
    d = _turn(yaw, (0.0, 0.0, face))
    n += _place(canvas, _models()[PREFIX + "knife"], (x + d[0], y + 2.15, z + d[2]), origin, yaw,
                KNIFE_SCALE)
    n += _place(canvas, _models()[PREFIX + "meter"], (x + d[0], y + 1.45, z + d[2] - 0.9), origin, yaw)
    n += _place(canvas, _models()[PREFIX + "leads"], (x + d[0], y + 0.55, z + d[2]), origin, yaw)
    if LIGHTS_ON:
        d2 = _turn(yaw, (0.0, 0.0, 0.45))
        lights.append(((int(x + d2[0]), int(y + 1.45), int(z + d2[2])), METER_LEVEL))
    return n, lights


def build(canvas, origin=(0, 0, 0)):
    """Place the boiler and the switchboard in the power house; offer A2 the fire and the meter.
    Returns the display-entity count."""
    n, lights = 0, []
    got, ls = boiler(canvas, origin)
    n += got
    lights += ls
    got, ls = board(canvas, origin)
    n += got
    lights += ls
    _offer_lights(canvas, lights, NAME)
    return n
