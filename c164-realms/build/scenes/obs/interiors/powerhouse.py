"""Work package interiors/powerhouse: the inside of the power house (plan ART-PLAN 8, the room behind
view V6). Card: plan/packages/interiors/powerhouse.md.

The room is the shell site/powerhouse.py leaves: 19 by 19 (x 69..87, z 22..40), the feet at -6, the
walls brick with six rows of cold glass, the saw-tooth roof on iron girders along z on the pier
lines (x 72, 76, 80, 84), dark overhead. The chimney's foot fills the north-east corner. One comes
in by the wicket of the north door (x 74) and looks south.

The machines are not this package's: the engine, its flywheel, the belt and the dynamo are
machines/engine.py, the two boilers and the switchboard machines/boiler.py and board.py. The room
is laid out round them and reads where they stand from their modules (ENGINE, BOILER, BOARD), or,
while those are not in the tree, from the figures agreed with their makers.

What stands where (plan cells; north is -z, the door is in the north wall):

  straight ahead    the engine's line along the south half (z 35), the flywheel full face behind the
                    crank: the star piece. Four drop lights hang in a row over its near edge, one
                    under each girder; nothing else in the room is lit like it.
  left hand         the two boilers, their fire doors to the west: the fire is the one orange thing.
                    Before them the firing floor of pale brick, the coal in its bin against the
                    north wall, a drop light over the stoker's place.
  right hand        the switchboard before the west wall, its face to the room: a wooden mat to
                    stand on, two drop lights before it. North of it, in the corner between two
                    windows, the engineer's desk.
  the walk          a band of polished stone three cells wide from the door to the gangway: the
                    band the lower platform lays up to the door goes on indoors.
  the gangway       two rows of open grating across the room at the foot of the engine (z 32..33),
                    over a pipe trench: the exhaust main lies in it under the south row, the north
                    row looks down on the trench's brick bottom and a caged lamp here and there. A
                    railing stands on its south row along the engine, turns south at the walk and
                    closes off the belt.
  the steam main    the main of the pipe bridge, in whole blocks like it, comes in through the west
                    wall under the eaves (site/powerhouse.PIPE_IN) and runs east over the gangway,
                    hung from every girder. A header leaves it north over the boilers, with a riser
                    down to the flange on each steam dome; east of the header it goes on to the
                    cylinder's end and a small pipe drops from it to the engine's inlet, a stop valve
                    with the red handwheel on it. No line ends in the air.
  the cables        from the two terminals on the dynamo up to a pair of insulators on the west
                    wall, along the wall before the window to the next pier, and down to the two
                    lead-in insulators at the switchboard's south end.

Light. The room is dark and is lit where somebody works. Every lamp is a shaded one (props/lamps'
version B) and hangs low; a shade throws its light down, so a lamp's source is offered not at its
bulb but at what it lights. The engine takes its light from four cells (machines/engine.LIT_BY: a
display entity is lit by the cell its anchor is in), and those four get the same level, so the set
is one machine. The fire doors' glow is the boilers' own; the windows stay cold. Nothing lights the
roof: the glazed sides of the saw teeth are a dark band from the court. Inside the wicket the walk
and the firing floor are pale stone under a lamp, and that is what V6 sees through the open wicket.

No block of the room stands in the first cell behind the glass of a fire window (clear_cells()):
the light line puts its source there.

build() is what the master scene calls (MOVED_IN). What joins a machine waits for the machine: the
risers, the engine's steam pipe and the cables are placed once the machine's module is in the tree.
The test scene, build/scenes/obs_int_powerhouse, shows the room with stand-ins for the machines
that are not.
"""
import functools
import importlib
import math
import random

from artkit import models as M
from artkit.blocks import st

from ..common import blocks as B
from ..common import palette as P
from ..props import _kit as K
from ..props import lamps
from ..site import powerhouse as SH

MOVED_IN = True
NAME = "interiors/powerhouse"
PREFIX = "int_power_"
PX = 1 / 16.0


# ---- the other lines' packages ------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def theirs(line, package):
    """The package scenes.obs.<line>.<package>, or None while it is not in the tree."""
    full = f"{__package__.rsplit('.', 1)[0]}.{line}.{package}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as missing:
        if missing.name != full:
            raise
        return None


def _told(module, name, default):
    """What a machine's module says, or the figure agreed with its maker while it is not in the tree."""
    return default if module is None else getattr(module, name, default)


ENGINE = theirs("machines", "engine")
BOILER = theirs("machines", "boiler")
BOARD = theirs("machines", "board")
MACHINES = ("engine", "boiler", "board")


def standing():
    """The machines whose module is in the tree."""
    return tuple(name for name, module in zip(MACHINES, (ENGINE, BOILER, BOARD)) if module is not None)


# ---- the room (site/powerhouse) ------------------------------------------------------------------------
X0, Z0, X1, Z1 = SH.ROOM                            # 69, 22, 87, 40
FEET = SH.ROOM_Y[0]                                 # -6
FLOOR_Y = FEET - 1                                  # -7: the floor block
EAVES = SH.ROOM_Y[1]                                # 3: the last clear row under the girders
GIRDER_Y = EAVES + 1                                # 4: the girders' row; their underside is the room's ceiling
GIRDER_X = tuple(range(SH.X0 + SH.CORNER + SH.BAY - 1, X1, SH.BAY))     # 72, 76, 80, 84: the pier lines
NORTH, SOUTH, WEST, EAST = float(Z0), Z1 + 1.0, float(X0), X1 + 1.0     # the four wall faces: 22, 41, 69, 88
FOOT = (SH.TOWER[0], SH.TOWER[3])                   # the chimney's foot is x >= 84, z <= 25: solid
DOOR_X = SH.DOOR_AT["cell"][0]                      # 74: the wicket
MAIN_Y, MAIN_Z = SH.PIPE_Y, SH.PIPE_Z               # 2, 33: the steam main's row and line

# ---- the engine and the dynamo (machines/engine, c326) ---------------------------------------------------
PIT = dict(_told(ENGINE, "PIT", {(x, 36): (2 if 76 <= x <= 78 else 1) for x in range(72, 80)}))
BASE = set(_told(ENGINE, "BASE", sorted(({(x, z) for x in range(76, 87) for z in range(34, 38)}
                                         | {(x, z) for x in range(70, 74) for z in range(36, 39)}) - set(PIT))))
STEAM_IN = tuple(_told(ENGINE, "STEAM_IN", (85.4, -3.6875, 35.875)))        # the inlet flange, which looks up
POWER_OUT = tuple(_told(ENGINE, "POWER_OUT", ((71.40625, -2.9375, 37.75), (72.59375, -2.9375, 37.75))))
ENGINE_CELLS = tuple(sorted(_told(ENGINE, "LIT_BY", ((72, -5, 37), (77, -5, 36), (82, -5, 35), (84, -5, 35)))))
LINE_Z = _told(ENGINE, "LINE_Z", 35.0)              # the engine's line

# ---- the boilers and the switchboard (machines/boiler, machines/board, c346) -----------------------------
STEAM_OUT = tuple(_told(BOILER, "STEAM_OUT", ((81.5, -1.0, 24.5), (81.5, -1.0, 28.5))))    # the flanges on the steam domes
FIRE_X = _told(BOILER, "FRONT_X", 79.0)             # the plane of the fire doors, which look west
FIRE_Z = tuple(_told(BOILER, "AXES_Z", (24.5, 28.5)))
BOARD_X = _told(BOARD, "X", 70)                     # the board's column; its face looks east
BOARD_Z = tuple(_told(BOARD, "Z", (26, 32)))
LEAD_IN = tuple(_told(BOARD, "LEAD_IN", ((70.5, -1.5, 32.25), (70.5, -1.5, 32.75))))       # the tops of its lead-in insulators

# ---- the floor --------------------------------------------------------------------------------------------
DECK_Z = (MAIN_Z - 1, MAIN_Z)                       # 32..33: the gangway, under the steam main
WALK_X = (DOOR_X - 1, DOOR_X + 1)                   # 73..75: the band from the door
DECK_X = (WALK_X[0], X1)                            # 73..87: the gangway starts where the walk meets it
HEARTH_X = WALK_X[1] + 1                            # 76: from here east the north half is the boiler house: brick
MAT_X = BOARD_X + 1                                 # 71: the wooden mat before the switchboard
TRENCH_Y = FLOOR_Y - 1                              # -8: the trench is one cell deep
EXHAUST_Z = DECK_Z[1]                               # 33: the exhaust main's row in the trench
TRENCH_LAMPS = tuple(range(DECK_X[0] + 2, DECK_X[1] + 1, 4))        # 75, 79, 83, 87: caged lamps in the trench's bottom
JOINT_STEP = 3                                      # a riveted collar every third cell, as on the pipe bridge

# ---- the railing ------------------------------------------------------------------------------------------
RAIL_TURN = WALK_X[1]                               # 75: where it turns south
RAIL_SOUTH = int(math.floor(LINE_Z))                # 35: the row north of the belt
RAIL_END = 72                                       # the last cell west: the way to the dynamo's west side stays open
RAIL = ([(x, DECK_Z[1]) for x in range(RAIL_TURN, X1)]                      # along the engine; the cell at the east wall is the way round
        + [(RAIL_TURN, z) for z in range(DECK_Z[1] + 1, RAIL_SOUTH + 1)]
        + [(x, RAIL_SOUTH) for x in range(RAIL_END, RAIL_TURN)])

# ---- the steam main ---------------------------------------------------------------------------------------
HEADER_X = int(math.floor(STEAM_OUT[0][0]))         # 81: the header's column, over the steam domes
RISERS = tuple(int(math.floor(p[2])) for p in STEAM_OUT)                    # 24, 28: the risers' rows
RISER_FOOT = int(math.floor(min(p[1] for p in STEAM_OUT)))                  # -1: the lowest block of a riser sits on the flange
DROP_CELL = (int(math.floor(STEAM_IN[0])), int(math.floor(STEAM_IN[2])))    # (85, 35): the block the engine's pipe drops from
VALVE_Y = -2.0                                      # the stop valve on the drop: over the governor, its wheel to the door
GAUGE_Y = -0.75                                     # the pressure gauge's tapping, over the valve
DROP_R = 3.0                                        # px: the drop is 6 px across (props/pipes' large bore)

# ---- the cables -------------------------------------------------------------------------------------------
RACK_Y = (-1.5, -1.0)                               # the two insulators of a rack, one above the other
RACK_Z = tuple(z + 0.5 for z in (37, 33))           # the racks: on the west wall's piers by the dynamo and by the main
SEAT = 4 * PX                                       # a cable in its insulator runs this far off the wall

# ---- the coal ---------------------------------------------------------------------------------------------
COAL_AT = (77.0, NORTH)                             # the bin's north-west corner, inside: against the north wall, east of the door
COAL = (24.0, 20.0, 15.0)                           # px: the heap east-west, north-south, and its height at the wall

# ---- the desk ---------------------------------------------------------------------------------------------
DESK_Z = (Z0, Z0 + 1)                               # 22..23: under the west wall's first window
DESK_TOP = 1.0                                      # blocks: the top of the board that stands in for a desk

# ---- light: what the room asks of the light line (level, rank); the lamps are props/lamps' models ---------
LAMPS = "b"                 # the shaded lamps: a shade keeps a lamp's glow to what is under it
HANG = -0.5                 # where every drop light's cord ends and its lamp hangs: the shades end at -1.44, four
#                             and a half blocks over the floor, over the flywheel's top and over the eye
LAMP_ROW = LINE_Z - 0.5     # 34.5: the engine's lamps hang over its near edge, one under each girder
ENGINE_LAMP = (12, 2)       # the engine's four cells: the top of the second rank, all alike
BOARD_LAMP = (10, 2)        # before the switchboard, at the height of the hand (agreed with c346)
BOARD_LIGHT = ((MAT_X, -4, 28), (MAT_X, -4, 31))
FIRING_LAMP = (11, 2)       # over the stoker's place between the two fire doors
FIRING_LIGHT = (HEARTH_X + 1, FEET, 27)             # (77, -6, 27): on the floor V6 sees through the wicket
DOOR_LAMP = (11, 2)         # the bracket lamp inside the door, on the pier east of it
DOOR_LIGHT = (WALK_X[1], FEET, Z0 + 1)              # (75, -6, 23): on the walk, a cell inside the door
DOOR_LAMP_Y = -2.5
DESK_LAMP = (6, 3)          # the green lamp on the desk

# ---- materials (the palette's, and nothing else) ------------------------------------------------------------
RED = P.mat("signal")
PORCELAIN = P.mat("porcelain")
WOOD = P.mat("dark_wood")
WOOD_L = P.mat("dark_wood", base=3)
COAL_CORE = K.flat("slate", 0)
COAL_LUMP = (P.mat("slate", base=0, noise=0.5), P.mat("slate", base=1, noise=0.5), P.mat("iron", base=1, noise=0.4))
CABLE = K.flat("old_copper", 1)
PIPE = K.flat("iron", 2)


def in_room(x, z):
    """Is the cell on the room's clear floor?"""
    return X0 <= x <= X1 and Z0 <= z <= Z1 and not (x >= FOOT[0] and z <= FOOT[1])


def on_deck(x, z):
    return DECK_X[0] <= x <= DECK_X[1] and DECK_Z[0] <= z <= DECK_Z[1]


def floor_role(x, z, roles=B):
    """The block of the floor course in a cell of the room; None where the machines lay their own."""
    if (x, z) in PIT or (x, z) in BASE:
        return None
    if on_deck(x, z):
        return roles.IRON_GRATE
    if WALK_X[0] <= x <= WALK_X[1] and z < DECK_Z[0]:
        return roles.TUFF_SMOOTH.block
    if x >= HEARTH_X and z < DECK_Z[0]:
        return roles.TUFF_BRICK.block
    if x == MAT_X and BOARD_Z[0] <= z <= BOARD_Z[1]:
        return roles.FLOOR_WOOD.block
    return roles.SLATE_TILE.block


def main_cells(risers=True):
    """The steam main in the room, in whole blocks: {(x, y, z): is it a riveted piece (a collar, a
    bend, a tee, a foot)}. From the sleeve in the west wall east over the gangway to the cell the
    engine's pipe drops from; the header north over the boilers, and a riser to each steam dome
    (left out while no boiler stands under it)."""
    out = {}

    def lay(cell, riveted):
        out[cell] = out.get(cell, False) or riveted

    x_in = SH.PIPE_IN[0]
    for x in range(x_in, DROP_CELL[0] + 1):                         # the run over the gangway
        lay((x, MAIN_Y, MAIN_Z), (SH.X0 - x) % JOINT_STEP == 0)
    lay((HEADER_X, MAIN_Y, MAIN_Z), True)                           # the tee
    lay((DROP_CELL[0], MAIN_Y, MAIN_Z), True)                       # the bend to the engine
    for z in range(MAIN_Z + 1, DROP_CELL[1] + 1):
        lay((DROP_CELL[0], MAIN_Y, z), z == DROP_CELL[1])           # ... and the head of the drop
    north = min(RISERS)
    for z in range(north, MAIN_Z):                                  # the header
        lay((HEADER_X, MAIN_Y, z), z in RISERS or (MAIN_Z - z) % JOINT_STEP == 0)
    for z in RISERS if risers else ():                              # the risers
        for y in range(RISER_FOOT, MAIN_Y):
            lay((HEADER_X, y, z), y == RISER_FOOT)
    return out


def hangers():
    """Where the main hangs from the girders: the cells between its top and a girder's underside."""
    return [(x, MAIN_Y + 1, MAIN_Z) for x in GIRDER_X if SH.PIPE_IN[0] <= x <= DROP_CELL[0]]


def clear_cells():
    """The cells no block of the room stands in, [(x, y, z)]: the first cell behind the glass of the
    two fire windows (the light line's sources stand there), and the two cells inside the wicket."""
    rows = range(SH.FURNACE_Y[0], SH.FURNACE_Y[1] + 1)
    out = [(x, y, Z0) for x in range(HEADER_X, HEADER_X + 3) for y in rows]
    out += [(X1, y, z) for z in range(FOOT[1] + 1, FOOT[1] + 4) for y in rows]
    out += [(DOOR_X, y, Z0) for y in (FEET, FEET + 1)]
    return out


# ---- the room's own models ---------------------------------------------------------------------------------
def _coal():
    """The coal in its bin: a heap against the wall, a plank side and a low plank kerb, the shovel in
    it. Anchor: the bin's inner corner at the floor; +x along the wall to the heap's open end, +z out
    from the wall."""
    wide, deep, high = COAL
    m = M.Model(PREFIX + "coal")
    # the heap's body, in steps, the darkest tone: what shows between the lumps
    for i, (z0, z1, h) in enumerate(((0.0, 6.0, high - 3.0), (6.0, 11.0, high - 7.0), (11.0, 15.5, high - 11.0))):
        m.box((0.0, 0.0, z0), (wide - 2.0 - 2.0 * i, h, z1), COAL_CORE, skip="d")
    rnd = random.Random(1890)
    for j, z in enumerate((1.5, 4.5, 7.5, 10.5, 13.5, 16.5)):
        top = high * (1.0 - (z / (deep - 1.0)) ** 1.3)
        for i in range(7):
            x = 1.5 + i * 3.3 + rnd.uniform(-0.6, 0.6)
            fall = 1.0 if x < wide - 6.0 else max(0.0, (wide - x) / 6.0)       # the open end slopes down
            size = rnd.choice((2.0, 2.5, 3.0, 3.0, 3.5))
            y = max(0.0, top * fall - size * 0.6 + rnd.uniform(-0.8, 0.8))
            if x + size / 2.0 > wide or y + size < 1.0 and rnd.random() < 0.3:
                continue
            c = (x, y + size / 2.0, z + rnd.uniform(-0.5, 0.5))
            m.box((c[0] - size / 2.0, c[1] - size / 2.0, c[2] - size / 2.0),
                  (c[0] + size / 2.0, c[1] + size / 2.0, c[2] + size / 2.0), COAL_LUMP[(i + j) % len(COAL_LUMP)],
                  rot=("xyz", (rnd.uniform(-25, 25), rnd.uniform(0, 90), rnd.uniform(-25, 25)), c), seed=7 * i + j)
    m.box((-1.5, 0.0, 0.0), (0.0, 13.0, deep + 1.5), WOOD, grain="z")                    # the plank side, towards the door
    m.box((0.0, 0.0, deep), (wide, 5.0, deep + 1.5), WOOD, grain="x")                    # the kerb
    for z in (1.0, deep - 1.0):
        m.box((-2.5, 0.0, z), (-1.5, 14.0, z + 1.5), K.IRON_D, grain="y")                # the side's two iron stakes
    # the shovel: its blade in the coal at the open end, the handle leaning on the wall
    a, b = (wide - 5.0, 4.0, 9.0), (wide - 2.5, 21.0, 0.8)
    m.beam(a, b, 1.0, 1.0, WOOD_L)
    m.box((a[0] - 2.5, 0.5, a[2] - 0.5), (a[0] + 2.5, 5.5, a[2] + 0.5), K.IRON, rot=("x", -18.0, a))
    m.box((b[0] - 1.5, b[1] - 0.5, b[2] - 0.5), (b[0] + 1.5, b[1] + 0.5, b[2] + 0.5), WOOD_L)       # the grip
    return m


def _cable():
    """A power cable: runs along +z from the anchor, 48 long, and is stretched between two points.
    One flat tone, so stretching smears nothing."""
    m = M.Model(PREFIX + "cable")
    m.box((-0.75, -0.75, 0), (0.75, 0.75, 48), CABLE, grain="z")
    return m


def _rack():
    """Two porcelain insulators on a wall strap, one above the other: the spools of a cable rack.
    A cable lies in the waist of each. Anchor: on the wall, level with the lower spool; the upper
    one is RACK_Y[1] - RACK_Y[0] higher; both stand SEAT off the wall."""
    rise = (RACK_Y[1] - RACK_Y[0]) * 16.0
    off = SEAT * 16.0
    m = M.Model(PREFIX + "rack")
    m.box((-1.0, -4.0, 0.0), (1.0, rise + 4.0, 1.0), K.IRON, grain="y")
    for y in (-3.0, rise + 3.0):
        K.rivet(m, (0.0, y, 1.0))
    for y in (0.0, rise):
        for dy in (-2.5, 1.5):
            m.box((-0.5, y + dy, 1.0), (0.5, y + dy + 1.0, off + 1.5), K.IRON_D, grain="z")      # the strap's two arms
        m.tube("y", (0.0, off), y - 1.5, y - 0.5, 1.75, PORCELAIN, sides=8)
        m.tube("y", (0.0, off), y - 0.5, y + 0.5, 1.0, PORCELAIN, sides=8)                   # the waist
        m.tube("y", (0.0, off), y + 0.5, y + 1.5, 1.75, PORCELAIN, sides=8)
    return m


def _drop():
    """The engine's steam pipe while props/pipes is not in the tree: a plain iron pipe along +z, 48
    long, stretched between two points."""
    m = M.Model(PREFIX + "drop")
    m.tube("z", (0, 0), 0.0, 48.0, DROP_R, PIPE, sides=8)
    return m


def _flange():
    """A pair of bolted flanges on that pipe. Anchor: on the axis (z), between the two."""
    m = M.Model(PREFIX + "flange")
    m.tube("z", (0, 0), -1.5, -0.25, DROP_R + 2.0, K.IRON, sides=8)
    m.tube("z", (0, 0), 0.25, 1.5, DROP_R + 2.0, K.IRON, sides=8)
    m.tube("z", (0, 0), -0.25, 0.25, DROP_R + 1.0, K.IRON_D, sides=8)
    return m


def _valve():
    """The stop valve on that pipe: a globe body between two flanges on the axis z, the bonnet, the
    brass stem and the red handwheel out along +y. Anchor: the middle of the globe."""
    m = M.Model(PREFIX + "valve")
    body = DROP_R + 1.5
    m.ball((0.0, 0.0, 0.0), body, K.IRON_D, sides=8, layers=3)
    for z0, z1 in ((-body - 1.5, -body + 0.5), (body - 0.5, body + 1.5)):
        m.tube("z", (0, 0), z0, z1, DROP_R + 2.0, K.IRON, sides=8)
    m.tube("y", (0, 0), body - 1.0, body + 2.0, 2.0, K.IRON_D, sides=8)                     # the bonnet
    m.tube("y", (0, 0), body + 2.0, body + 6.5, 0.5, K.BRASS, sides=4)                      # the stem
    wheel = body + 5.5
    m.ring("y", (0.0, wheel, 0.0), 4.0, 1.0, 1.0, RED, sides=12)
    m.box((-3.5, wheel - 0.5, -0.5), (3.5, wheel + 0.5, 0.5), RED)
    m.box((-0.5, wheel - 0.5, -3.5), (0.5, wheel + 0.5, 3.5), RED)
    return m


def _gauge():
    """The pressure gauge on that pipe: a boss, a turn of small pipe, a brass case, the cream dial with
    three luminous marks and the needle. Anchor: the tapping, on the pipe's skin; the stalk stands out
    along +y, the dial looks along +z."""
    m = M.Model(PREFIX + "gauge")
    m.tube("y", (0, 0), -0.5, 1.5, 1.0, K.IRON_D, sides=8)
    m.tube("y", (0, 0), 1.5, 4.0, 0.5, K.BRASS_D, sides=4)
    yc = 6.5
    m.tube("z", (0, yc), -1.0, 1.0, 3.0, K.BRASS, sides=12)
    m.tube("z", (0, yc), 1.0, 1.25, 2.25, K.flat("cream", 3), sides=12, cap=K.flat("cream", 3))
    m.box((-0.5, yc - 0.5, 1.25), (0.5, yc + 2.0, 1.5), K.flat("iron", 0), rot=("z", 40.0, (0.0, yc, 1.25)))
    for x, y in ((0.0, yc + 1.5), (1.5, yc), (-1.5, yc)):
        m.box((x - 0.5, y - 0.5, 1.25), (x + 0.5, y + 0.5, 1.4), K.flat("phosphor", 2), emit=10, shade=False)
    return m


def _toolboard():
    """A board of tools on the wall by the door: three spanners and a hammer on their pegs, a shelf
    under them with the oil can and a wad of cotton waste. Anchor: on the wall, the middle of the
    board."""
    m = M.Model(PREFIX + "toolboard")
    m.box((-8.0, -6.0, 0.0), (8.0, 7.0, 1.0), WOOD, skip="n", grain="x")
    m.box((-8.0, -7.0, 0.0), (8.0, -6.0, 4.0), WOOD_L, grain="x")                          # the shelf
    for x, length in ((-6.0, 9.0), (-3.5, 7.5), (-1.0, 6.0)):                               # spanners, the longest first
        m.box((x - 0.5, 4.5 - length, 1.0), (x + 0.5, 4.5, 1.5), K.IRON, grain="y")
        m.box((x - 1.0, 4.0, 1.0), (x + 1.0, 5.5, 1.5), K.IRON)                             # the jaw, on its peg
        m.box((x - 1.0, 3.5 - length, 1.0), (x + 1.0, 4.5 - length, 1.5), K.IRON)
    m.box((2.5, -3.0, 1.0), (3.5, 4.0, 2.0), WOOD_L, grain="y")                             # the hammer's shaft
    m.box((1.5, 4.0, 1.0), (4.5, 5.5, 2.5), K.IRON_D)
    m.tube("y", (6.0, 2.0), -6.0, -3.5, 1.5, K.BRASS, sides=8)                              # the oil can
    m.taper("y", (6.0, 2.0), -3.5, -2.0, 1.5, 0.5, K.BRASS, sides=8)
    m.beam((6.0, -2.25, 2.0), (3.5, -0.5, 2.0), 0.5, 0.5, K.BRASS_D)                        # its spout
    m.box((-5.0, -6.0, 1.5), (-2.0, -4.75, 3.5), K.flat("cream", 1))                        # cotton waste
    return m


def _oilcan():
    """The oiler's can by the engine: a brass can with a long spout and a handle, on a drip tray.
    Anchor: the middle of the tray's foot; the spout points along +x."""
    m = M.Model(PREFIX + "oilcan")
    m.box((-4.0, 0.0, -3.0), (4.0, 0.5, 3.0), K.IRON_D)
    m.tube("y", (-1.0, 0.0), 0.5, 4.0, 2.25, K.BRASS, sides=8)
    m.taper("y", (-1.0, 0.0), 4.0, 6.0, 2.25, 0.75, K.BRASS, sides=8)
    m.beam((-1.0, 6.0, 0.0), (5.0, 9.5, 0.0), 0.5, 0.5, K.BRASS_D)
    m.ring("z", (-3.25, 3.0, 0.0), 1.5, 0.5, 0.75, K.BRASS_D, sides=8, arc=(90.0, 270.0))
    return m


@functools.lru_cache(maxsize=None)
def _models():
    built = [_coal(), _cable(), _rack(), _drop(), _flange(), _valve(), _gauge(), _toolboard(), _oilcan()]
    return {m.name: m for m in built}


def models():
    """The room's own models: the coal in its bin, the power cable and the insulator rack, the tool
    board and the oil can, and what stands in for props/pipes on the engine's steam pipe (the pipe,
    its flanges, the stop valve, the gauge). The lamps are props/lamps', the machines the machines
    line's."""
    return dict(_models())


def their_models():
    """The models of the other props packages' pieces the room places: what a test scene packs
    besides the lamps and the room's own (the master scene collects every package's itself)."""
    out = {}
    for package in ("furniture", "paper", "pipes"):
        module = theirs("props", package)
        if module is not None:
            out.update(module.models())
    return out


def _pipes():
    """props/pipes, when it is in the tree and has the pieces the steam pipe is made of."""
    pipes = theirs("props", "pipes")
    spec = getattr(pipes, "SPEC", {})
    if pipes is None or not all(hasattr(pipes, f) for f in ("run", "place")):
        return None
    if not all(kind in spec for kind in ("main_l", "flange_l", "valve_l", "gauge")):
        return None
    return pipes


# ---- the room ----------------------------------------------------------------------------------------------
def build_powerhouse(c, origin=(0, 0, 0), roles=B, machines=None):
    """Dress the room standing at `origin`. Returns dict(entities=<display entities placed>,
    lights=[((x, y, z), level, why)]): the light sources it has offered to the light line.

    machines  which of MACHINES stand in the room; left out, those whose module is in the tree. What
              joins a machine is left out while the machine is: the risers to the boilers, the
              engine's steam pipe, the cables from the dynamo to the switchboard."""
    ox, oy, oz = origin
    lights, n = [], 0
    own = _models()
    there = set(standing() if machines is None else machines)

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    def at(p):
        return (ox + p[0], oy + p[1], oz + p[2])

    def offer(cell, ask, why):
        level, rank = ask
        cell = (ox + cell[0], oy + cell[1], oz + cell[2])
        lights.append((cell, level, f"{NAME}:{why}"))
        _offer(c, cell, level, f"{NAME}:{why}", rank)

    def span(model, a, b, thick=1.0):
        """One model drawn out from a to b (scene coordinates); it stands, and is lit, at a."""
        a, b = at(a), at(b)
        c.add_entity(a[0], a[1], a[2], M.between(model, a, b, thick=thick))
        return 1

    def drop_light(x, z, why, cell, ask):
        """A drop light: a cord from the girder's underside down to HANG, a shaded lamp on its end;
        its light is offered in `cell`."""
        offer(cell, ask, why)
        cord = lamps.models()[lamps.PREFIX + "wire"]
        return (span(cord, (x, GIRDER_Y - K.NUDGE, z), (x, HANG, z))
                + lamps.place(c, "pendant", (x, HANG, z), origin=origin, light=False, version=LAMPS))

    # ---- the floor: the room's own, in place of the platform's paving; the machines' base plates and
    # the flywheel's pit are theirs
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            role = floor_role(x, z, roles) if in_room(x, z) else None
            if role is not None:
                put(x, FLOOR_Y, z, role)

    # ---- the pipe trench under the gangway: a brick trough (the platform is hollow under its paving),
    # the exhaust main in its south row, caged lamps in the bottom of the north row
    for x in range(DECK_X[0] - 1, DECK_X[1] + 2):
        for z in range(DECK_Z[0] - 1, DECK_Z[1] + 2):
            if not on_deck(x, z):
                put(x, TRENCH_Y, z, roles.TUFF_BRICK.block)                 # the sides
                continue
            lamp = z != EXHAUST_Z and x in TRENCH_LAMPS
            put(x, TRENCH_Y - 1, z, st(roles.IRON_BULB, lit="true", powered="false") if lamp else roles.TUFF_BRICK.block)
            if z == EXHAUST_Z:
                put(x, TRENCH_Y, z, roles.IRON_RIVETED.block if (SH.X0 - x) % JOINT_STEP == 0 else roles.IRON_PLATE)
            else:
                c.clear(ox + x, oy + TRENCH_Y, oz + z)

    # ---- the railing
    for x, z in RAIL:
        put(x, FEET, z, roles.IRON_BARS)

    # ---- the steam main, its hangers
    for (x, y, z), riveted in main_cells(risers="boiler" in there).items():
        put(x, y, z, roles.IRON_RIVETED.block if riveted else roles.IRON_PLATE)
    for x, y, z in hangers():
        put(x, y, z, st(roles.IRON_PIPE, axis="y"))

    # ---- the engine's steam pipe: from under the main's last block down to the inlet flange, the stop
    # valve over the governor with its wheel to the door, the gauge over it. props/pipes' pieces when
    # that package is in the tree, the room's own until then
    top = (STEAM_IN[0], float(MAIN_Y), STEAM_IN[2])
    valve, gauge = (STEAM_IN[0], VALVE_Y, STEAM_IN[2]), (STEAM_IN[0], GAUGE_Y, STEAM_IN[2] - DROP_R * PX)
    pipes = _pipes()
    if "engine" not in there:
        pass
    elif pipes is not None:
        n += pipes.run(c, top, STEAM_IN, "main_l", origin=origin)
        n += pipes.place(c, "flange_l", (top[0], top[1] - 2 * PX, top[2]), along="down", out="north", origin=origin)
        n += pipes.place(c, "flange_l", (STEAM_IN[0], STEAM_IN[1] + PX, STEAM_IN[2]), along="down", out="north", origin=origin)
        n += pipes.place(c, "valve_l", valve, along="down", out="north", origin=origin)
        n += pipes.place(c, "gauge", gauge, along="east", out="north", origin=origin)
    else:
        n += span(own[PREFIX + "drop"], top, STEAM_IN)
        upright = (("x", -90.0),)                   # the model's z up, its y to the north
        for y in (top[1] - 2 * PX, STEAM_IN[1] + 1.5 * PX):
            n += K.put(c, own[PREFIX + "flange"], (top[0], y, top[2]), yaw=0.0, turns=upright, origin=origin)
        n += K.put(c, own[PREFIX + "valve"], valve, yaw=0.0, turns=upright, origin=origin)
        n += K.put(c, own[PREFIX + "gauge"], gauge, yaw=0.0, turns=(("x", -90.0), ("y", 180.0)), origin=origin)

    # ---- the cables: dynamo, rack by the dynamo, rack by the main, the board's lead-ins. The west
    # terminal takes the lower insulator, so the two never cross
    cable = own[PREFIX + "cable"]
    seat_x = WEST + SEAT
    for z in RACK_Z:
        n += K.put(c, own[PREFIX + "rack"], (WEST, RACK_Y[0], z), mount="wall", facing="east", origin=origin)
    low, high = sorted(POWER_OUT), sorted(LEAD_IN, key=lambda p: -p[2])
    for terminal, y, lead in zip(low, RACK_Y, high) if {"engine", "board"} <= there else ():
        way = [terminal] + [(seat_x, y, z) for z in RACK_Z] + [lead]
        for a, b in zip(way, way[1:]):
            n += span(cable, a, b)

    # ---- the coal, the tools, the oil can
    n += K.put(c, own[PREFIX + "coal"], (COAL_AT[0], FEET, COAL_AT[1]), yaw=0.0, origin=origin)
    n += K.put(c, own[PREFIX + "toolboard"], (GIRDER_X[0] + 0.5, FEET + 1.75, NORTH), mount="wall", facing="south", origin=origin)
    n += K.put(c, own[PREFIX + "oilcan"], (RAIL_TURN - 0.6, FEET, DECK_Z[1] + 1.4), yaw=160.0, origin=origin)

    # ---- the knees under the girders' ends, on the piers of the two end walls
    for x in GIRDER_X:
        north = Z0 if x < FOOT[0] else FOOT[1] + 1                  # the fourth girder starts at the chimney's foot
        put(x, EAVES, north, st(roles.IRON_RIVETED.stairs, facing="north", half="top"))
        put(x, EAVES, Z1, st(roles.IRON_RIVETED.stairs, facing="south", half="top"))

    # ---- the engineer's desk in the north-west corner: props/furniture's, or a board until it is in
    # the tree; the green lamp on it
    furniture, paper = theirs("props", "furniture"), theirs("props", "paper")
    desk_x, desk_z = WEST + 0.4375, DESK_Z[1] + 0.0
    if furniture is not None and hasattr(furniture, "place"):
        n += furniture.place(c, "writing_desk", (desk_x, FEET, desk_z), facing="east", origin=origin)
        n += furniture.place(c, "swivel_chair", (desk_x + 1.075, FEET, desk_z), yaw=K.FACING["west"] + 20.0, origin=origin)
        desk_top = FEET + furniture.TOP["writing_desk"]
    else:
        for z in range(DESK_Z[0], DESK_Z[1] + 1):
            put(X0, FEET, z, st(roles.DARK_WOOD.slab, type="top"))
        desk_top = FEET + DESK_TOP
    if paper is not None and hasattr(paper, "place") and furniture is not None:
        n += paper.place(c, "logbook", (desk_x + 0.1, desk_top, desk_z + 0.25), yaw=K.FACING["east"] + 8.0, origin=origin)
    offer((X0, FEET + 1, DESK_Z[0]), DESK_LAMP, "desk lamp")
    n += lamps.place(c, "desk_green", (X0 + 0.45, desk_top, DESK_Z[0] + 0.5), facing="east", origin=origin, light=False)

    # ---- the lamps. Over the engine: one under each girder, in a row; each of the engine's cells gets
    # the same light, offered in the cell itself
    cells = sorted(ENGINE_CELLS)
    for x in GIRDER_X:
        near = min(cells, key=lambda cell: abs(cell[0] + 0.5 - (x + 0.5)))
        n += drop_light(x + 0.5, LAMP_ROW, f"engine lamp x {x}", near, ENGINE_LAMP)
        cells = [cell for cell in cells if cell != near] or cells
    for cell in cells if len(ENGINE_CELLS) > len(GIRDER_X) else ():
        offer(cell, ENGINE_LAMP, "engine lamp")
    # before the switchboard, from the first girder
    for cell in BOARD_LIGHT:
        n += drop_light(GIRDER_X[0] + 0.5, float(cell[2]), f"switchboard lamp z {cell[2]}", cell, BOARD_LAMP)
    # over the stoker's place, from the second girder
    n += drop_light(GIRDER_X[1] + 0.5, FIRING_LIGHT[2] + 0.0, "firing floor lamp", FIRING_LIGHT, FIRING_LAMP)
    # inside the door, on the pier east of it
    offer(DOOR_LIGHT, DOOR_LAMP, "door lamp")
    n += lamps.place(c, "bracket", (GIRDER_X[1] + 0.5, DOOR_LAMP_Y, NORTH), facing="south", origin=origin,
                     light=False, version=LAMPS)
    return {"entities": n, "lights": lights}


def _offer(canvas, cell, level, why, rank):
    """Register a light source with the light line (sky/_lightkit). While that kit is not in the
    tree the block is put down here, never over a block that is there, so a test scene is lit."""
    try:
        from ..sky import _lightkit
    except ImportError:
        canvas.set(*cell, st(B.LIGHT, level=level), keep=True)
    else:
        _lightkit.suggest(canvas, cell, level, why, rank=rank)


def build(canvas, origin=(0, 0, 0)):
    """The master scene's call: nothing until the room has moved in."""
    if not MOVED_IN:
        return 0
    return build_powerhouse(canvas, origin)["entities"]
