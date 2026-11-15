"""machines/engine -- the horizontal steam engine and the dynamo it drives, in the power house.

Card plan/packages/machines/engine-dynamo.md; detail plan/parts/A5-machines.md 2.5; ART-PLAN 7.2.

The set, laid out along one bed plate (the card's default: a single horizontal cylinder, the flywheel
on the east, the dynamo on the belt, the governor standing at the cylinder's side):

  mach_engine_base      the shared cast-iron bed plate the machine stands on
  mach_engine_flywheel  the big flywheel, five blocks through: the one moving thing V6 sees through
                        the windows. A separate entity, anchored on its main shaft.
  mach_engine_cylinder  the cylinder, piston rod, slide bars and crosshead, with its two brass heads
  mach_engine_rod       the connecting rod from the crosshead to the crank pin (turns with the wheel)
  mach_engine_governor  the centrifugal governor: a vertical spindle with two arms and balls, at the
                        cylinder's side (spins, A8)
  mach_engine_belt      the belt from the flywheel to the dynamo's pulley
  mach_engine_dynamo    the dynamo: yoke frame, field poles, the armature on its own shaft, the
                        commutator and the porcelain terminals the cables leave from

AXES FOR A8. Everything is still this round (A0 #505). The pieces are cut and anchored where they
turn, so switching them on is a change of the entity's transform, not a redraw:

  mach_engine_flywheel  anchor = the middle of the wheel, on its axle; the axle lies along z, so a
                        turn about z spins the wheel and the crank pin with it.
  mach_engine_rod       anchor = the crank pin (the wheel's rim), so it follows the wheel.
  mach_engine_governor  anchor = the base of its spindle; a turn about y spins the balls.
  mach_engine_dynamo_armature  anchor = the armature shaft, along z.

Nothing here emits light (the furnace is the boiler card's); the dynamo's small indicator lamp is
offered to A2 when `LAMP` is on.

Sizes come from the card: the flywheel is five blocks through, the machine body about four wide by
two deep, the dynamo three by two. Models are drawn in model units (16 to the block) with px = 1, so
every picture is 16 pixels to the block (A5 1.2).

    from scenes.obs.machines import engine
    n = engine.build(canvas, origin)        # the whole set on one bed plate, in scene coordinates
"""
import functools
import math

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S

PREFIX = "mach_engine_"
NAME = "machines/engine-dynamo"

# the way the set faces -> the yaw that points its +z that way (same table as props/_kit)
FACING = {"south": 0.0, "west": 90.0, "north": 180.0, "east": -90.0}

# --- the power house, from the skeleton (x 67..89, z 20..42, feet at y -6, walls 10 high)
PH = S.POWER_HOUSE
X0, Z0, X1, Z1 = PH["box"]
FEET = PH["base_y"]                 # -6, the floor the machine stands on
WALL_H = PH["wall_h"]               # 10: the walls rise to y 4

# where the set stands: the machine's own centre, on the room's long axis, a little west of centre so
# the dynamo and its belt have room to the east and the way in from the door stays clear
CX = X0 + 9.0                       # 76.0
CZ = Z0 + 11.0                      # 31.0
FACING_ROOM = "south"               # the machine's front (the cylinders' side) looks at the door

# --- sizes, in model units (16 to the block)
WHEEL_BLOCKS = 5.0                  # the flywheel is five blocks through (the card)
WHEEL_R = 22.0                      # its drawn radius in units: span 44, inside the 48 a model may have
WHEEL_SCALE = WHEEL_BLOCKS * 16.0 / (2.0 * WHEEL_R)   # 1.818: drawing * scale = 5 blocks, px = scale
WHEEL_W = 9.0                       # the rim's width across the wheel
WHEEL_SPOKES = 8
BED_W, BED_D, BED_T = 88.0, 40.0, 3.0   # the bed plate: 5.5 x 2.5 blocks, three units thick
BED_SECTION = 44.0                      # one section of it: 2.75 blocks (a model may span 3)
BED_SECTIONS = 2                        # laid end to end, they make the whole 5.5 blocks
CYL_SCALE = 1.05                    # drawing * scale = 2.9 blocks; px = scale
BODY_R = 6.9                        # the cylinder's drawn radius (0.69 blocks at its scale)
BODY_L = 28.8                       # its drawn length: 1.8 blocks at its scale (2.9 real)
DYNAMO_W, DYNAMO_D, DYNAMO_H = 40.0, 30.0, 34.0   # the dynamo: 2.5 x 1.9 x 2.1 blocks

# the layout along the bed plate, in blocks from its west end (the wheel is at the east end)
WHEEL_X = 4.3                       # the flywheel's plane, measured west from the bed's east end
CYL_X = -2.6                        # the cylinder's centre, west of the wheel's plane
GOV_X = -3.0                        # the governor's spindle, beside the cylinder
DYNAMO_X = 6.4                      # the dynamo's centre, east of the wheel (it is belted)

LAMP = False                        # the dynamo's indicator lamp: off until A2 says where light goes
LAMP_LEVEL = 6

# --- materials (palette only)
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
IRON_F = P.mat("iron", kind="flat", bevel=0)
IRON_FLAT = P.mat("iron_flat")
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")
COPPER = P.mat("old_copper")
PORCELAIN = P.mat("porcelain")
SIGNAL = P.mat("signal")
WOOD_D = P.mat("dark_wood", base=1)


# ==================================================================================================
# the flywheel
# ==================================================================================================
def _flywheel():
    """The big flywheel: a heavy rim, eight spokes and a hub, with the crank pin standing out of the
    rim's west face. Anchor: the middle of the wheel, on its axle (the axle runs along z)."""
    m = M.Model(PREFIX + "flywheel", px=WHEEL_SCALE, anchor=(0.0, 0.0, 0.0))
    rim_t = 3.8                                  # the rim's thickness, radially
    hub_r = 3.9
    # the rim, then a second, narrower flange at its west edge (a flywheel reads by its weight)
    m.ring("z", (0.0, 0.0, 0.0), WHEEL_R - rim_t / 2.0 - 0.6, rim_t, WHEEL_W, IRON, sides=24)
    m.ring("z", (0.0, 0.0, WHEEL_W / 2.0 - 0.4), WHEEL_R - rim_t / 2.0 - 0.6, rim_t * 1.35, 1.0, IRON_D, sides=24)
    # the hub and the spokes
    m.tube("z", (0.0, 0.0), -WHEEL_W / 2.0 - 0.8, WHEEL_W / 2.0 + 0.8, hub_r, IRON_D, sides=12)
    for i in range(WHEEL_SPOKES):
        a = 2.0 * math.pi * i / WHEEL_SPOKES
        tip = (math.cos(a) * (WHEEL_R - rim_t), math.sin(a) * (WHEEL_R - rim_t))
        root = (math.cos(a) * hub_r, math.sin(a) * hub_r)
        m.beam((root[0], root[1], 0.0), (tip[0], tip[1], 0.0), 1.6, 1.4, IRON)
    # the crank pin: a brass boss standing out of the rim on the west face, off centre
    pin_a = math.radians(214.0)
    px, py = math.cos(pin_a) * (WHEEL_R - rim_t * 1.4), math.sin(pin_a) * (WHEEL_R - rim_t * 1.4)
    m.tube("z", (px, py), -WHEEL_W / 2.0 - 2.0, -WHEEL_W / 2.0 + 0.6, 1.3, BRASS_D, sides=8)
    return m


# ==================================================================================================
# the cylinder and its motion
# ==================================================================================================
def _cylinder():
    """The horizontal cylinder: the barrel, its two brass heads, the piston rod going east out of
    the front head, the slide bars and the crosshead. Anchor: the middle of the barrel."""
    m = M.Model(PREFIX + "cylinder", px=CYL_SCALE, anchor=(0.0, 0.0, 0.0))
    half = BODY_L / 2.0
    # the barrel, flitched with two iron hoops
    m.tube("x", (0.0, 0.0), -half, half, BODY_R, IRON, sides=14)
    for hx in (-half * 0.45, half * 0.45):
        m.ring("x", (hx, 0.0, 0.0), BODY_R - 1.0, 2.2, 2.0, IRON_D, sides=14)
    # the two brass heads
    m.tube("x", (0.0, 0.0), -half - 3.0, -half, BODY_R * 1.06, BRASS, sides=14,
           cap=P.mat("brass", kind="flat", base=2, bevel=0))
    m.tube("x", (0.0, 0.0), half, half + 3.0, BODY_R * 1.06, BRASS, sides=14)
    # the piston rod out of the front head, the slide bars under it, and the crosshead
    m.tube("x", (0.0, 0.0), half + 3.0, half + 11.0, 1.4, IRON_D, sides=8)
    for sz in (-4.4, 4.4):
        m.box((half + 3.0, -4.6, sz - 0.7), (half + 11.0, -3.2, sz + 0.7), IRON, skip="d")
    m.box((half + 9.0, -3.6, -4.8), (half + 13.0, 3.6, 4.8), IRON_D, skip="d")
    # the steam chest on top of the barrel, with its two brass gland nuts
    m.box((-half * 0.55, BODY_R - 0.8, -4.4), (half * 0.35, BODY_R + 4.4, 4.4), IRON, skip="d")
    for hx in (-half * 0.35, half * 0.15):
        m.tube("y", (hx, 0.0), BODY_R + 4.4, BODY_R + 6.6, 1.6, BRASS, sides=8)
    return m


def _rod():
    """The connecting rod, from the crosshead to the crank pin. Anchor: the crank-pin end, so a turn
    about the wheel's axle (z) carries it round with the wheel."""
    m = M.Model(PREFIX + "rod", px=WHEEL_SCALE, anchor=(0.0, 0.0, 0.0))
    # it runs west from the anchor, 2.2 blocks, and ends in the crosshead's eye
    m.box((-22.0, -1.4, -1.1), (0.0, 1.4, 1.1), IRON_D, skip="d")
    m.tube("z", (0.0, 0.0), -1.6, 1.6, 2.1, BRASS_D, sides=10)      # the big end
    m.tube("z", (-19.4, 0.0), -1.4, 1.4, 1.6, BRASS_D, sides=10)    # the small end
    return m


GOV_SCALE = 1.1                     # drawing * scale = 2.0 blocks tall; px = scale


def _governor():
    """The centrifugal governor: a spindle on a small pedestal, a yoke at the top, two arms and two
    balls painted red. Anchor: the foot of the spindle; a turn about y spins it (A8)."""
    m = M.Model(PREFIX + "governor", px=GOV_SCALE, anchor=(0.0, 0.0, 0.0))
    m.tube("y", (0.0, 0.0), -2.0, 2.0, 4.6, IRON_D, sides=10)        # the pedestal
    m.tube("y", (0.0, 0.0), 2.0, 26.0, 1.5, IRON, sides=8)           # the spindle
    for sy in (21.0, 24.5):
        m.ring("y", (0.0, sy, 0.0), 6.0, 1.4, 1.2, BRASS_D, sides=12)     # the yoke collars
    for sx in (-1, 1):
        m.beam((0.0, 24.0, 0.0), (sx * 9.0, 17.0, 0.0), 1.4, 1.4, BRASS)   # the arms
        m.ball((sx * 9.0, 15.0, 0.0), 3.6, SIGNAL, sides=10, layers=5)              # the balls
    m.tube("y", (0.0, 0.0), 26.0, 28.0, 2.4, BRASS, sides=10)        # the top nut
    return m


# ==================================================================================================
# the dynamo
# ==================================================================================================
def _dynamo():
    """The dynamo: a cast-iron yoke on a plinth, two field poles with old-copper windings, the
    armature between them, the commutator and two porcelain terminals on the crown. Anchor: the
    middle of its plinth."""
    m = M.Model(PREFIX + "dynamo", px=1.0, anchor=(0.0, 0.0, 0.0))
    hw, hd = DYNAMO_W / 2.0, DYNAMO_D / 2.0
    m.box((-hw, 0.0, -hd), (hw, 4.0, hd), IRON_D, skip="d")                  # the plinth
    # the two field poles, west and east of the armature, wound with old copper
    for sx in (-1, 1):
        x = sx * 9.0
        m.box((x - 5.0, 4.0, -hd * 0.72), (x + 5.0, DYNAMO_H, hd * 0.72), IRON, skip="d")
        m.ring("z", (x, DYNAMO_H * 0.55, 0.0), 4.2, 2.4, 2.6, COPPER, sides=12)
    # the yoke over the top, tying the poles
    m.box((-hw * 0.82, DYNAMO_H - 3.0, -hd * 0.78), (hw * 0.82, DYNAMO_H, hd * 0.78), IRON, skip="d")
    # the two porcelain terminals on the crown, where the cables leave
    for sz in (-1, 1):
        m.tube("y", (hw * 0.55, sz * 4.0), DYNAMO_H, DYNAMO_H + 4.0, 2.0, PORCELAIN, sides=8)
    # the armature shaft's bearings, so the shaft has something to turn in
    for sx in (-1, 1):
        m.box((sx * 13.0 - 2.0, DYNAMO_H * 0.34, -2.6), (sx * 13.0 + 2.0, DYNAMO_H * 0.66, 2.6),
              IRON_D, skip="d")
    return m


def _armature():
    """The armature: the laminated core and the coil ends on its shaft, with the pulley at the west
    end where the belt runs. Anchor: the middle of the shaft; a turn about z spins it (A8)."""
    m = M.Model(PREFIX + "armature", px=1.0, anchor=(0.0, 0.0, 0.0))
    m.tube("z", (0.0, 0.0), -9.0, 9.0, 1.6, IRON_D, sides=8)                  # the shaft
    m.tube("z", (0.0, 0.0), -5.4, 5.4, 5.0, IRON, sides=12)                   # the core
    for zz in (-5.4, 5.4):
        m.ring("z", (0.0, 0.0, zz), 3.4, 2.4, 1.6, COPPER, sides=12)              # the coil ends
    m.tube("z", (0.0, 0.0), -9.0, -7.2, 4.2, IRON_D, sides=10)                # the pulley
    m.tube("z", (0.0, 0.0), 7.6, 9.0, 2.4, BRASS_D, sides=10)                 # the commutator
    return m


# ==================================================================================================
# the bed plate
# ==================================================================================================
def _base():
    """One section of the shared bed plate: a cast-iron slab with a moulded edge, two bolts and a
    joint flange at its east end. Anchor: the middle of its top face at its west end, so sections
    laid end to end share a joint. `build()` places two of them side by side."""
    m = M.Model(PREFIX + "base", px=1.0, anchor=(0.0, 0.0, 0.0))
    hd = BED_D / 2.0
    m.box((0.0, -BED_T, -hd), (BED_SECTION, 0.0, hd), IRON, skip="d")
    m.box((-0.8, -BED_T - 1.4, -hd - 0.8), (BED_SECTION + 0.8, -BED_T + 0.6, hd + 0.8), IRON_D, skip="d")
    for sx in (4.0, BED_SECTION - 4.0):
        for sz in (-1, 1):
            m.tube("y", (sx, sz * (hd - 4.0)), -BED_T - 1.4, BED_T * 0.2, 1.6, IRON_D, sides=8)
    # the joint flange at the east end, where the next section bolts on
    m.box((BED_SECTION - 0.2, -BED_T - 0.6, -hd - 1.2), (BED_SECTION + 1.6, -BED_T + 0.8, hd + 1.2),
          IRON_D, skip="d")
    return m


# ==================================================================================================
# the registry
# ==================================================================================================
@functools.lru_cache(maxsize=None)
def _models():
    return {
        PREFIX + "base": _base(),
        PREFIX + "flywheel": _flywheel(),
        PREFIX + "cylinder": _cylinder(),
        PREFIX + "rod": _rod(),
        PREFIX + "governor": _governor(),
        PREFIX + "dynamo": _dynamo(),
        PREFIX + "armature": _armature(),
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


def build(canvas, origin=(0, 0, 0), facing=FACING_ROOM, centre=None):
    """Place the whole set on its bed plate in the power house. `centre` is (x, z) of the machine's
    own centre; the default is the card's place in the room. Returns the display-entity count.

    The pieces are laid out along the bed plate's x axis in the model's frame: the flywheel east, the
    cylinder west of it, the governor beside the cylinder, the dynamo beyond the wheel on its belt.
    """
    yaw = FACING[facing]
    cx, cz = centre if centre else (CX, CZ)
    n = 0

    # the bed plate, standing on the floor: two sections end to end, centred on the machine
    west = -BED_SECTIONS * BED_SECTION / 2.0
    for i in range(BED_SECTIONS):
        d = _turn(yaw, (west + i * BED_SECTION, 0.0, 0.0))
        n += _place(canvas, _models()[PREFIX + "base"], (cx + d[0], FEET, cz + d[2]), origin, yaw)

    def at(dx, dz, y):
        """A point `dx` east and `dz` south of the machine's centre, `y` above the floor, in the
        machine's own frame turned by its facing."""
        d = _turn(yaw, (dx, 0.0, dz))
        return (cx + d[0], FEET + y, cz + d[2])

    # the flywheel: its plane stands across the machine, so it is turned a quarter turn about y
    n += _place(canvas, _models()[PREFIX + "flywheel"],
                at(WHEEL_X, 0.0, WHEEL_BLOCKS / 2.0), origin, yaw + 90.0, WHEEL_SCALE)
    # the cylinder: its barrel runs along the machine's x
    n += _place(canvas, _models()[PREFIX + "cylinder"], at(CYL_X, 0.0, BODY_R * CYL_SCALE / 16.0 + 0.35),
                origin, yaw + 90.0, CYL_SCALE)
    # the connecting rod, anchored on the crank pin
    n += _place(canvas, _models()[PREFIX + "rod"],
                at(WHEEL_X - 0.35, -0.55, WHEEL_BLOCKS / 2.0 + 0.62), origin, yaw + 90.0,
                WHEEL_SCALE)
    # the governor, standing at the cylinder's side
    n += _place(canvas, _models()[PREFIX + "governor"], at(GOV_X, 0.95, 0.3), origin, yaw, GOV_SCALE)
    # the dynamo, east of the wheel, and the armature inside it
    n += _place(canvas, _models()[PREFIX + "dynamo"], at(DYNAMO_X, 0.0, 0.0), origin, yaw)
    n += _place(canvas, _models()[PREFIX + "armature"], at(DYNAMO_X, 0.0, DYNAMO_H / 16.0 * 0.55),
                origin, yaw + 90.0)

    lights = []
    if LAMP:
        lights.append((tuple(int(math.floor(v)) for v in at(DYNAMO_X, 0.0, DYNAMO_H / 16.0 + 0.6)),
                       LAMP_LEVEL))
    _offer_lights(canvas, lights, NAME)
    return n
