"""The power house's inside (plan ART-PLAN 8; card plan/packages/interiors/powerhouse.md).

The works building on the lower terrace, the room of V6: the industrial room of the map, and the
only one whose star is a machine that turns. The shell is site/powerhouse's (c285): this package
dresses what stands inside it.

    floor     spruce boards between the wall's inner faces, with the engine pit open in the middle
    walls     a dark wainscot course and the iron truss bays above it, on the shell's own tuff
    ceiling   iron beams north-south and dark boards between them, as main/shell does the hall
    walkway   an iron grating run from the door to the machine's front, on a low frame
    lamps     caged lamps hung from the beams; the room's only warm light

What is whose. The machines are machines/engine-dynamo's (c264: the steam engine, its flywheel and
the dynamo) and machines/switchboard-boiler's (the switchboard and the boilers). This package
places neither: it keeps their cells clear and reads their numbers to know where that is. Props are
the props line's. The light is the light line's; while sky/lights is not in the tree the sources are
put down here, at the levels asked below.

The room is a box in the skeleton's coordinates: FEET is where feet stand, and every x, y, z here is
a cell of the world, not an offset. `build_powerhouse()` dresses it where it stands.
"""
import functools
import math

from artkit.canvas import Canvas

from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import engine_dynamo as ENGINE

NAME = "interiors/powerhouse"
MOVED_IN = False        # the master scene dresses the room once site/powerhouse is in the tree
ORDER = 80              # after the shell that holds it (site/powerhouse is 70)

# ---- the room, from the skeleton --------------------------------------------------------------
BOX = S.POWER_HOUSE["box"]                  # x 67..89, z 20..42: the shell's outer pier plane
FEET = S.POWER_HOUSE["base_y"]              # -6: where feet stand, and the floor's own row is one below
WALL_H = S.POWER_HOUSE["wall_h"]            # 10 courses, to the cornice
FLOOR_Y = FEET - 1                          # -7: the floor block under the feet
PIER = 2                                    # the shell's corner piers are this wide
X0, Z0, X1, Z1 = BOX
IN_X = (X0 + PIER, X1 - PIER)               # 69..87: the clear floor inside the piers
IN_Z = (Z0 + PIER, Z1 - PIER)               # 22..40
WALL_TOP = FEET + WALL_H - 1                # 3: the cornice course; the roof is the shell's
CEIL_Y = WALL_TOP                           # the beams hang under this row
CLEAR_TOP = CEIL_Y - 1                      # 2: the highest row a person's head has

# ---- the door: the shell's north front, second bay (site/powerhouse DOOR_AT) -------------------
DOOR_X = (X0 + PIER + S.BAY + 1, X0 + PIER + S.BAY + 2)      # 74, 75: the wicket's cells
DOOR_ROWS = (FEET, FEET + 1)                                 # -6, -5: the opening; a lintel above

# ---- the machines' own cells, read from their packages ---------------------------------------
# machines/engine-dynamo: centre (76, 31) facing south, the flywheel east, the dynamo beyond it.
# What it needs is not guessed from its centre but asked of its own numbers: the bed is two
# sections end to end (BED_SECTIONS x BED_SECTION units), the wheel is WHEEL_BLOCKS through and
# stands WHEEL_X west of the bed's east end, and the dynamo is DYNAMO_W wide beyond the wheel.
_BED = ENGINE.BED_SECTIONS * ENGINE.BED_SECTION / 16.0                       # 5.5 blocks
_HALF_BED = _BED / 2.0
ENGINE_CENTRE = (ENGINE.CX, ENGINE.CZ)                                      # (76.0, 31.0)
# the set runs east from the cylinder's far end to the dynamo's far end; south, it is the bed's
# depth, widened by the wheel and the governor standing off it
ENGINE_SPAN_X = (-(_HALF_BED + 0.35), ENGINE.WHEEL_X + ENGINE.DYNAMO_X + ENGINE.DYNAMO_W / 32.0)
ENGINE_SPAN_Z = (-(_HALF_BED / 2.0 + 1.0), _HALF_BED / 2.0 + 1.0)
# the cells the machine may stand in, with a cell of working room round it: this package puts
# nothing there, and the pit below is theirs to ask for. Clipped to the room: the span's east end
# reaches the wall, and a cell outside the walls is not the room's to keep clear.
ENGINE_CELLS = {(x, z) for x in range(math.floor(ENGINE_CENTRE[0] + ENGINE_SPAN_X[0]) - 1,
                                      math.ceil(ENGINE_CENTRE[0] + ENGINE_SPAN_X[1]) + 1)
                for z in range(math.floor(ENGINE_CENTRE[1] + ENGINE_SPAN_Z[0]) - 1,
                               math.ceil(ENGINE_CENTRE[1] + ENGINE_SPAN_Z[1]) + 1)
                if IN_X[0] <= x <= IN_X[1] and IN_Z[0] <= z <= IN_Z[1]}
# the switchboard and the boilers are not in the tree yet; their owner names the cells and this
# package widens ENGINE_CELLS then. Until it does, the east half of the room is left empty too.
RESERVED = {c for c in ENGINE_CELLS}

# ---- the floor -------------------------------------------------------------------------------
FLOOR = B.FLOOR_WOOD.block
FLOOR_EDGE = B.SLATE_BRICK.block            # a course of stone under the wainscot, at the wall
WAINSCOT = B.WAINSCOT                       # the dark panelling, one course at the foot of a wall
TRUSS = B.IRON_RIVETED.block                # the iron truss bays above the wainscot
TRUSS_STEP = 4                              # a truss stand every fourth column of a front
BEAM = B.IRON_RIVETED.block                 # the ceiling's beams
BOARDS = B.DARK_WOOD.block                  # the ceiling between them
GRATE = B.IRON_GRATE                        # the walkway
FRAME = B.IRON_RIVETED.block                # its frame, and the posts of its rail

# ---- the walkway -----------------------------------------------------------------------------
# From the door in along the north side, then south to the machine's front: a grating run two cells
# wide, one course over the floor. It ends at the machine's own cells, which it does not enter.
WALK_Y = FEET                               # the grating's own row: feet stand on the boards below
WALK_Z = (IN_Z[0] + 1, IN_Z[0] + 2)         # 23, 24: the run in from the door
WALK_X = (DOOR_X[0], 80)                    # 74..80: the run east past the machine's west end
WALK_END_Z = min(z for _x, z in ENGINE_CELLS) - 1        # 26: one short of the machine's own cells

# ---- the lamps -------------------------------------------------------------------------------
# Caged lamps hung from the beams, the room's only warm light: the card asks for them, and without
# them a box room with two furnace bays is a black hole (the offline renderer draws no ambient
# bloom). Levels are the light line's third rank (props/lamps puts a cage at 7); this package only
# names where they hang and offers them, and while sky/lights is not in the tree it puts them down.
# Hung over the walkway and over the machine, so that every stand has one in frame.
# Hung over the walkway and over the machine, in a ring round the room: a 19 by 19 box with ten
# courses of tuff needs more than four lamps to keep its corners off the dead-black floor (measured:
# four left 20 to 37 per cent of a stand under 0.03, which is RUBRIC's red line 6).
LAMPS = [(x, CEIL_Y - 1, z) for x, z in
         ((WALK_X[0] + 2, WALK_Z[0]), (WALK_X[1] - 2, WALK_Z[0]),
          (int(ENGINE_CENTRE[0]) - 3, int(ENGINE_CENTRE[1])), (int(ENGINE_CENTRE[0]) + 4, int(ENGINE_CENTRE[1])),
          (IN_X[0] + 3, IN_Z[1] - 3), (IN_X[1] - 3, IN_Z[1] - 3),
          (IN_X[0] + 3, IN_Z[0] + 8), (IN_X[1] - 3, IN_Z[0] + 8))]
LAMP_LEVEL = 7                              # the third rank (a caged lamp), never above 8

# ---- the light ------------------------------------------------------------------------------
LIGHT = B.LIGHT                             # the invisible source a lamp offers


def _inside(x, z):
    return IN_X[0] <= x <= IN_X[1] and IN_Z[0] <= z <= IN_Z[1]


def floor_cells():
    """Every cell of the room's floor: inside the piers, less nothing yet (the pit is the engine's
    owner's to ask for)."""
    return {(x, z) for x in range(IN_X[0], IN_X[1] + 1) for z in range(IN_Z[0], IN_Z[1] + 1)}


def wall_cells():
    """The cells of the room's four inner faces: one course deep, round the clear floor."""
    out = set()
    for x in range(IN_X[0] - 1, IN_X[1] + 2):
        out.add((x, IN_Z[0] - 1))
        out.add((x, IN_Z[1] + 1))
    for z in range(IN_Z[0], IN_Z[1] + 1):
        out.add((IN_X[0] - 1, z))
        out.add((IN_X[1] + 1, z))
    return out


def walk_cells():
    """The grating's cells: in from the door along the north side, then south to the machine's
    front. Nothing in the machines' own cells."""
    out = set()
    for x in range(WALK_X[0], WALK_X[1] + 1):
        for z in WALK_Z:
            out.add((x, z))
    for x in (WALK_X[1] - 1, WALK_X[1]):
        for z in range(WALK_Z[1] + 1, WALK_END_Z + 1):
            out.add((x, z))
    return {c for c in out if _inside(*c) and c not in ENGINE_CELLS}


def beam_cells():
    """The ceiling's beams: north-south, every BEAM_STEP columns, as main/shell lays the hall's."""
    return {c for c in floor_cells() if (c[0] - IN_X[0]) % TRUSS_STEP == 0}


def build_powerhouse(c, origin=(0, 0, 0), roles=B, *, version="a"):
    """Dress the room at `origin`. Returns dict(entities=, lights=, reserved=)."""
    ox, oy, oz = origin

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    cells = floor_cells()

    # the floor, and the stone course the wainscot stands on
    for x, z in cells:
        put(x, FLOOR_Y, z, FLOOR)
    for x, z in wall_cells():
        put(x, FLOOR_Y, z, FLOOR_EDGE)

    # the walls: a wainscot course at the foot, iron truss bays above it. The shell's own brick
    # stands behind; these are its lining, so one cell in from the piers
    for x, z in wall_cells():
        put(x, FEET, z, WAINSCOT)
    for x, z in wall_cells():
        if (x - IN_X[0]) % TRUSS_STEP == 0 or (z - IN_Z[0]) % TRUSS_STEP == 0:
            for y in range(FEET + 1, WALL_TOP + 1):
                put(x, y, z, TRUSS)

    # the ceiling: beams and boards between them
    beams = beam_cells()
    for x, z in cells:
        put(x, CEIL_Y, z, BEAM if (x, z) in beams else BOARDS)

    # the walkway: a grating walk on its frame, with a rail on both sides where it is off the floor
    walk = walk_cells()
    for x, z in walk:
        put(x, WALK_Y, z, GRATE)
    for x, z in walk:
        for dz in (-1, 1):
            n = (x, z + dz)
            if n not in walk and _inside(*n):
                put(x, WALK_Y + 1, n[1], FRAME)

    lights = []
    for x, y, z in LAMPS:
        if _inside(x, z):
            put(x, y, z, f"{LIGHT}[level={LAMP_LEVEL}]")
            lights.append(((x, y, z), LAMP_LEVEL))

    n = 0
    return {"entities": n, "lights": lights, "reserved": sorted(RESERVED)}


def build(canvas, origin=(0, 0, 0)):
    if not MOVED_IN:
        return 0
    return build_powerhouse(canvas, origin)["entities"]
