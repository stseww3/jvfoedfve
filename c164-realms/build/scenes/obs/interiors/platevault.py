"""The plate vault and its darkroom (card plan/packages/interiors/platevault.md): the ground floor of
the south wing, right under the chart room. The glass plates the astrograph of the small dome takes
every night are developed, dried and numbered here, shelved, and sent up to the light table of the
chart room by a hand lift.

The room is 12 wide (x 2..13), 19 long (z 7..25) and 6 high (feet at 0, the ceiling block on 6 is
the chart room's floor). The door from the star hall is one cell wide, in the cross wall on z 6 at
x 7 (hall, c348: the piers of the gallery stand before x 8, 11 and 14), so the room's axis is the
middle of that cell, x 7.5. From north to south:

  entry (z 7..8)       the hand lift in the north-west corner (2, 7), under the cased riser of the
                       chart room (chart, c350); the door; iron shutters on the east window
  the stacks (z 9..20) a nave three wide on the axis (x 6..8) between two island stacks (x 5 and
                       x 9), a side aisle beyond each, and a stack on either long wall (x 2 and
                       x 13) which stands before the windows of the base storey. The stacks rise to
                       the iron beams (y 0..4); the beams cross the room on the pilaster rows
  cross aisle (z 21)   joins the aisles before the darkroom wall
  darkroom (z 23..25)  the last bay, behind a masonry wall on the pilaster row z 22 with an arch
                       three wide on the axis. Its one light is the red lamp over the sink on the
                       south wall: the point the nave ends on, seen from the door of the hall

Light: the vault is dark and is lit where somebody works. Nothing lights a window of the base
storey: every one of them has an iron shutter inside, and no source stands within reach of one.

Coordinates are the skeleton's. build_platevault() dresses the room where it stands in the building;
the box test scene (build/scenes/obs_int_platevault) stands a stand-in of the shell around it.
build() is what the master scene calls; it places nothing while MOVED_IN is off.

This is the rough model: the stacks and the darkroom's pieces are plain volumes still.
"""
from artkit.blocks import st

from ..common import blocks as B
from ..common import skeleton as S
from ..main import _plan as MP
from ..main import shell
from ..props import _kit as K
from ..props import lamps

ORDER = 80              # a room that moves into the shell (INTERFACE 3)
MOVED_IN = False        # the master scene dresses the room; turned on with the delivery
NAME = "interiors/platevault"
PREFIX = "int_vault_"

# ---- the room (cells) ---------------------------------------------------------------------------
_ABOVE = shell.ROOMS["chart room"]
X0, Z0, X1, Z1 = _ABOVE["box"]      # 2, 7, 13, 25: the clear inside, the same columns as the chart room above
FEET = S.GROUND                     # 0
FLOOR_Y = FEET - 1                  # -1: the floor block
CEIL_Y = _ABOVE["feet"] - 1         # 6: the chart room's floor block is this room's ceiling
TOP = CEIL_Y - 1                    # 5: the highest clear row, and the row of the beams
HALL_DOOR = (7, Z0 - 1)             # (7, 6): the wall cell of the door to the star hall (hall reads this name)
DOOR_Y = (FEET, FEET + 2)           # the doorway's rows
AXIS_X = S.mid(HALL_DOOR[0])        # 7.5: the room's axis runs through the door
LIFT = (X0, Z0)                     # (2, 7): the hand lift's shaft, under the chart room's cased riser
PIER_Z = tuple(z for z in range(Z0, Z1 + 1) if MP.on_pilaster(z))      # 10, 14, 18, 22: the beams' rows
EAST_BAYS = tuple(b for b in range(1, S.N_BAYS + 1)
                  if set(MP.window_rows(b)) <= set(range(Z0, Z1 + 1)))                # 11..15
WEST_BAYS = tuple(b for b in EAST_BAYS
                  if all(abs(z - S.DOME_CENTRE[1]) > MP.WEST_BLIND_Z for z in MP.window_rows(b)))   # 13..15
WINDOW_Y = MP.BASE_WINDOW           # (3, 4): the small windows of the base storey

# ---- the plan (cells) ---------------------------------------------------------------------------
WALL_Z = PIER_Z[-1]                 # 22: the darkroom's wall, on the last pilaster row
DARK_Z = (WALL_Z + 1, Z1)           # 23..25: the darkroom, the last bay
ARCH_X = (HALL_DOOR[0] - 1, HALL_DOOR[0] + 1)      # 6..8: the arch in the darkroom's wall
ARCH_Y = FEET + 2                   # the row of the arch's head
NAVE_X = ARCH_X                     # 6..8: the nave, as wide as the arch
ISLAND_X = (NAVE_X[0] - 1, NAVE_X[1] + 1)           # 5 and 9: the two island stacks
STACK_Z = (Z0 + 2, WALL_Z - 2)      # 9..20: the stacks' run
STACK_TOP = TOP - 1                 # 4: the stacks' last row; the beams pass over them
CHEST_X = X1 - 1                    # 12: the low plan chests before the east wall stack
TABLE = (HALL_DOOR[0], STACK_Z[1] - 2, STACK_Z[1] - 1)      # x 7, z 18..19: the checking table, in the nave
SINK_X = ARCH_X                     # 6..8: the stone sink on the south wall, on the axis

# ---- light: what the room asks of the light line (level); the lamps are props/lamps models ------
LAMPS = "b"                 # the shaded lamp of props/lamps: its glow stays under it
ASK_NAVE = 8                # a pendant over the nave
ASK_DARK = 5                # the red lamp: the lowest step of the third rank (the card)
NAVE_LAMP_Z = PIER_Z[:2]    # the pendants hang from the first two beams

FLOOR = B.FLOOR_WOOD.block
WET_FLOOR = B.SLATE_SMOOTH.block
SILL = B.SLATE_BRICK.block
BEAM = B.IRON_RIVETED.block
WOOD = B.DARK_WOOD.block


def bay_rows(bay):
    return MP.window_rows(bay)


def shutters():
    """The iron shutters inside the windows of the base storey: [((x, y, z), side)], an iron hatch
    on edge in the first cell behind the glass, standing on the glass's side of it."""
    out = []
    for bays, x, side in ((EAST_BAYS, X1, "east"), (WEST_BAYS, X0, "west")):
        for bay in bays:
            for z in bay_rows(bay):
                for y in range(WINDOW_Y[0], WINDOW_Y[1] + 1):
                    out.append(((x, y, z), side))
    return out


def build_platevault(canvas, origin=(0, 0, 0)):
    """Dress the room; returns the number of display entities placed."""
    ox, oy, oz = origin
    n = 0

    def put(x, y, z, state, keep=False):
        canvas.set(ox + x, oy + y, oz + z, state, keep)

    def cut(x, y, z):
        canvas.clear(ox + x, oy + y, oz + z)

    # the floor: boards in the vault, stone in the darkroom, the plinth's stone under the wall
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            put(x, FLOOR_Y, z, SILL if z == WALL_Z else WET_FLOOR if z > WALL_Z else FLOOR)
    put(HALL_DOOR[0], FLOOR_Y, DARK_Z[1] - 1, B.IRON_GRATE)                     # the drain before the sink

    # the beams, on the pilaster rows; the last one lies on the darkroom's wall
    for z in PIER_Z:
        for x in range(X0, X1 + 1):
            put(x, TOP, z, BEAM)

    # the darkroom's wall, in the courses of the building's inside walls, and its arch
    for x in range(X0, X1 + 1):
        for y in range(FEET, TOP):
            put(x, y, WALL_Z, shell.wall_block(y))
    for x in range(ARCH_X[0], ARCH_X[1] + 1):
        for y in range(FEET, ARCH_Y + 1):
            cut(x, y, WALL_Z)
    put(ARCH_X[0], ARCH_Y, WALL_Z, st(B.ASHLAR_ROUGH.stairs, facing="west", half="top"))
    put(ARCH_X[1], ARCH_Y, WALL_Z, st(B.ASHLAR_ROUGH.stairs, facing="east", half="top"))
    for x in range(ARCH_X[0] + 1, ARCH_X[1]):
        put(x, ARCH_Y, WALL_Z, st(B.ASHLAR_ROUGH.slab, type="top"))

    # the stacks, as volumes: two islands and one on either long wall
    for x in ISLAND_X + (X0, X1):
        for z in range(STACK_Z[0], STACK_Z[1] + 1):
            for y in range(FEET, STACK_TOP + 1):
                put(x, y, z, WOOD)
    for z in range(STACK_Z[0] + 1, STACK_Z[1]):
        put(CHEST_X, FEET, z, WOOD)

    # iron shutters inside every window that no stack stands before
    for (x, y, z), side in shutters():
        if not canvas.has(ox + x, oy + y, oz + z):
            put(x, y, z, shell.panel(side))

    # the lift's shaft through the chart room's floor
    cut(LIFT[0], CEIL_Y, LIFT[1])
    put(LIFT[0], FEET, LIFT[1], B.IRON_CAST)

    # the checking table, the sink, the bench of the trays, the drying rack: volumes
    for z in TABLE[1:]:
        put(TABLE[0], FEET, z, st(B.DARK_WOOD.slab, type="top"))
    for x in range(SINK_X[0], SINK_X[1] + 1):
        put(x, FEET, DARK_Z[1], st(B.ASHLAR_FINE.slab, type="top"))
    for x in range(SINK_X[1] + 1, X1):
        put(x, FEET, DARK_Z[1], st(B.DARK_WOOD.slab, type="top"))
    for x in range(X0 + 1, SINK_X[0]):
        put(x, FEET, DARK_Z[1], st(B.DARK_WOOD.slab, type="top"))

    # light: two pendants over the nave, the red lamp over the sink
    for z in NAVE_LAMP_Z:
        n += lamps.place(canvas, "pendant", (AXIS_X, float(TOP), S.mid(z)), origin=origin, version=LAMPS,
                         level=ASK_NAVE)
    red = (AXIS_X, FEET + 2.5, float(Z1 + 1))
    n += lamps.place(canvas, "signal", red, facing="north", origin=origin, light=False)
    K.offer_lights(canvas, [((ox + HALL_DOOR[0], oy + FEET + 2, oz + Z1), ASK_DARK)], f"{NAME}:red")
    return n


def models():
    return {}


def build(canvas, origin=(0, 0, 0)):
    """What the master scene calls: the room, once it has moved in."""
    if not MOVED_IN:
        return 0
    return build_platevault(canvas, origin)
