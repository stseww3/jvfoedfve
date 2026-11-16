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
                    north wall, a drop light over the stoker's place, and behind it, at the
                    hearth's edge, his hand lamp burning on an upturned coal box.
  right hand        the switchboard before the west wall, its face to the room: a wooden mat to
                    stand on, two drop lights before it. North of it, in the corner between two
                    windows, the engineer's desk; on the pier between them the telephone to the
                    observatory and its bell.
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
                    cylinder's end and a small pipe (props/pipes) drops from it to the engine's
                    inlet, on it a stop valve with the red handwheel and a pressure gauge, both
                    turned to the door. No line ends in the air.
  the cables        from the two terminals on the dynamo up to the west wall, along the wall before
                    the window from pier to pier on pin insulators (props/electrics), one line over
                    the other, and down to the two lead-in insulators at the switchboard's south end.

Light. The room is dark and is lit where somebody works. Every lamp is a shaded one (props/lamps'
version B) and hangs low; a shade throws its light down, so a lamp's source is offered not at its
bulb but at what it lights. The engine takes its light from four cells (machines/engine.LIT_BY: a
display entity is lit by the cell its anchor is in), and those four get the same level, so the set
is one machine. The fire doors' glow is the boilers' own; the windows stay cold. Nothing lights the
roof: the glazed sides of the saw teeth are a dark band from the court. Inside the wicket the walk
and the firing floor are pale stone under a lamp, and the stoker's lantern stands in the line of the
open wicket: a lit floor and a flame are what V6 sees through it. Where nobody works but anybody
can walk, a lamp keeps the floor from being black: a bracket lamp on the east wall behind the
boilers, a caged one at the blind end of the alley north of No. 1.

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
from artkit.pixelart import Frames

from ..common import blocks as B
from ..common import palette as P
from ..props import _kit as K
from ..props import electrics, furniture, lamps, paper, pipes
from ..site import powerhouse as SH

MOVED_IN = True
NAME = "interiors/powerhouse"
PREFIX = "int_power_"
PX = 1 / 16.0
VIEW = M.NEAR       # the room's display entities are drawn up to 32 blocks off: the game draws them through
#                     walls, and nothing in here is to be seen from farther (the assembly applies it)


# ---- the other lines' packages ------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def theirs(package):
    """The machine's module scenes.obs.machines.<package>, or None while it is not in the tree."""
    full = f"{__package__.rsplit('.', 1)[0]}.machines.{package}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as missing:
        if missing.name != full:
            raise
        return None


def _told(module, name, default):
    """What a machine's module says, or the figure agreed with its maker while it is not in the tree."""
    return default if module is None else getattr(module, name, default)


ENGINE = theirs("engine")
BOILER = theirs("boiler")
BOARD = theirs("board")
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
DROP = "l"                                          # the drop is props/pipes' large bore, 6 px across

# ---- the cables -------------------------------------------------------------------------------------------
WIRE_Y = (-1.5, -0.75)                              # the two cables on the wall, one above the other
WIRE_Z = tuple(z + 0.5 for z in (37, 33))           # they are held on the west wall's piers by the dynamo and by the main
WIRE = 1.5                                          # a power cable is this many times the bell wire of props/electrics

# ---- the coal ---------------------------------------------------------------------------------------------
COAL_AT = (77.0, NORTH)                             # the bin's north-west corner, inside: against the north wall, east of the door
COAL = (24.0, 20.0, 15.0)                           # px: the heap east-west, north-south, and its height at the wall

# ---- the desk ---------------------------------------------------------------------------------------------
DESK_Z = (Z0, Z0 + 1)                               # 22..23: under the west wall's first window
PHONE_Z = SH.Z0 + SH.CORNER + SH.BAY - 0.5          # 25.5: the west wall's first pier, between the desk and the board
PHONE_Y = FEET + 0.875                              # the telephone's foot: its mouthpiece at the height of the mouth

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
DOOR_LAMP = (12, 2)         # the bracket lamp inside the door, on the pier east of it: the way in is lit as the
#                             engine is (review cr2 #74016: the door is where one goes in, and it was the dark place)
DOOR_LIGHT = (WALK_X[1], FEET, Z0 + 1)              # (75, -6, 23): on the walk, a cell inside the door
DOOR_LAMP_Y = -2.5
# The stoker's lantern. V6 looks into the room through the open wicket: a slot a third of a cell
# wide between the west jamb and the leaf, which lies open against the east jamb, and under the
# lintel no higher than a block and a quarter over the floor here. The lamps hang over that, so the
# slot showed a lit floor and nothing that burns (0.36 at its brightest). The lantern stands in the
# slot's line, on the hearth's first column behind the stoker's place: (76.33..76.69, 25.5) is seen.
LANTERN_AT = (HEARTH_X + 0.5, Z0 + 3.5)             # (76.5, 25.5)
LANTERN_BOX = 7.0                                   # px: the box it stands on, so the glass is clear of the floor
LANTERN = (8, 3)            # its own light: the top of the third rank, a hand lamp
DESK_LAMP = (7, 3)          # the green lamp on the desk, offered over the logbook: five is left of it on the
#                             floor before the telephone, two cells south
DESK_LIGHT = (X0, FEET + 1, Z0 + 1)                 # (69, -5, 23)
# Light where nobody works but anybody can walk (the director's closing list, 3: no dark floor
# where one can get to; the cells are sound's, dark.md). The corner behind the boilers, which the low railing only
# asks one to keep out of, and the passage south of it along the east wall take one bracket lamp on
# the east wall's pier south of the fire window, over the railing's end: ten in the cell before it
# is five on the farthest floor of both. The blind end of the alley north of No. 1 takes a caged
# lamp on the chimney's foot.
BACK_LAMP = (10, 2)
BACK_AT = (EAST, -2.5, SH.Z0 + SH.CORNER + 2 * SH.BAY - 0.5)        # (88.0, -2.5, 29.5): on the wall's second pier
BACK_LIGHT = (X1 - 1, FEET + 2, Z0 + 6)             # (86, -4, 28)
ALLEY_LAMP = (7, 3)
ALLEY_AT = (float(FOOT[0]), -3.5, Z0 + 0.5)         # (84.0, -3.5, 22.5): on the west face of the chimney's foot
ALLEY_LIGHT = (FOOT[0] - 1, FEET + 2, Z0)           # (83, -4, 22)

# ---- materials (the palette's, and nothing else) ------------------------------------------------------------
WOOD = P.mat("dark_wood")
WOOD_L = P.mat("dark_wood", base=3)
COAL_CORE = K.flat("slate", 0)
COAL_LUMP = (P.mat("slate", base=0, noise=0.5), P.mat("slate", base=1, noise=0.5), P.mat("iron", base=1, noise=0.4))


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


def _lantern():
    """The stoker's hand lamp, lit, on an upturned coal box: a brass font on an iron foot, the glass
    between two side tubes that carry the cap, a wire bail over it. The glass is as wide as what the
    open wicket shows of the room, so from the yard it is a flame in the door. Anchor: the middle of
    the box's foot; the side tubes stand along x."""
    m = M.Model(PREFIX + "lantern")
    top = LANTERN_BOX
    m.box((-5.0, 0.0, -4.0), (5.0, top - 1.0, 4.0), WOOD, grain="x")                        # the box, bottom up
    m.box((-5.5, top - 1.0, -4.5), (5.5, top, 4.5), WOOD_L, grain="x")                      # its bottom boards
    for x in (-4.5, 3.5):
        for z in (-4.5, 4.0):
            m.box((x, 0.0, z), (x + 1.0, top - 1.0, z + 0.5), WOOD_L, grain="y")            # the battens
    m.tube("y", (0.0, 0.0), top, top + 1.0, 3.5, K.IRON_D, sides=8)                         # the foot
    m.tube("y", (0.0, 0.0), top + 1.0, top + 3.0, 3.0, K.BRASS, sides=8)                    # the font
    m.tube("y", (0.0, 0.0), top + 3.0, top + 4.0, 2.0, K.BRASS_D, sides=8)                  # the burner
    # the glass: amber at the burner, the flame's white over it, as in the street lamps' globes (a
    # step darker throughout, too little of it passes 0.5 in V6)
    # The flame moves: the two upper bands of the glass are frames (plan/parts/materials.md 2 D), eight
    # of two ticks; now and then the flame's white dips a step and its tip another. The game runs them
    # by itself, no command and no entity. The first frame is the lamp as it was, the one a still shows.
    flame = Frames(PREFIX + "lantern_flame", [K.flat("glow", t) for t in (4, 4, 3, 4, 4, 4, 3, 4)], frametime=2)
    tip = Frames(PREFIX + "lantern_tip", [K.flat("glow", t) for t in (3, 3, 3, 2, 3, 3, 2, 3)], frametime=2)
    for y0, y1, glass in ((4.0, 5.5, K.flat("glow", 2)), (5.5, 8.5, flame), (8.5, 10.0, tip)):
        K.glass_prism(m, "y", (0.0, 0.0), top + y0, top + y1, 2.5, glass)
    for x in (-4.0, 3.0):
        m.box((x, top + 1.0, -0.5), (x + 1.0, top + 11.0, 0.5), K.IRON, grain="y")          # the side tubes
    m.box((-4.0, top + 10.0, -1.0), (4.0, top + 11.0, 1.0), K.IRON_D, grain="x")            # the yoke
    m.tube("y", (0.0, 0.0), top + 10.0, top + 12.0, 2.5, K.IRON_D, sides=8)                 # the cap
    m.tube("y", (0.0, 0.0), top + 12.0, top + 13.0, 1.5, K.IRON, sides=8)
    m.ring("z", (0.0, top + 11.0, 0.0), 4.0, 0.5, 0.75, K.IRON_D, sides=12, arc=(0.0, 180.0))       # the bail
    return m


@functools.lru_cache(maxsize=None)
def _models():
    settle = getattr(K, "settle", lambda m: m)      # the round pieces' flats lit alike in every copy (a6, g2 #75958)
    built = [_coal(), settle(_toolboard()), settle(_oilcan()), settle(_lantern())]
    return {m.name: m for m in built}


def models():
    """The room's own models: the coal in its bin, the tool board, the oil can, the stoker's
    lantern. The lamps, the pipe fittings, the insulators and the cable, the desk and the telephone
    are the props line's, the machines the machines line's."""
    return dict(_models())


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

    # ---- the engine's steam pipe (props/pipes): from the inlet flange up into the main's last block,
    # the stop valve over the governor with its wheel to the door, the gauge over it with its dial
    # to the door. The pipe stands, and is lit, at the engine's end
    if "engine" in there:
        top = (STEAM_IN[0], float(MAIN_Y), STEAM_IN[2])
        skin = pipes.BORE[DROP] * PX
        n += pipes.run(c, STEAM_IN, top, "main_" + DROP, origin=origin)
        for y in (STEAM_IN[1] + 2 * PX, top[1] - 2 * PX):
            n += pipes.place(c, "flange_" + DROP, (top[0], y, top[2]), along="up", out="north", origin=origin)
        n += pipes.place(c, "valve_" + DROP, (top[0], VALVE_Y, top[2]), along="up", out="north", origin=origin)
        n += pipes.place(c, "gauge", (top[0] - skin, GAUGE_Y, top[2]), along="up", out="west", origin=origin)

    # ---- the cables (props/electrics): dynamo, the pier by the dynamo, the pier by the main, the
    # board's lead-ins; a pin insulator under each cable on each pier. The west terminal takes the
    # lower line, so the two never cross
    if {"engine", "board"} <= there:
        cable = electrics.models()[electrics.PREFIX + "cable"]
        wire_x = WEST + electrics.WIRE_OUT
        low, high = sorted(POWER_OUT), sorted(LEAD_IN, key=lambda p: -p[2])
        for terminal, y, lead in zip(low, WIRE_Y, high):
            for z in WIRE_Z:
                n += electrics.place(c, "insulator", (WEST, y - electrics.WIRE_UP, z), facing="east", origin=origin)
            way = [terminal] + [(wire_x, y, z) for z in WIRE_Z] + [lead]
            for a, b in zip(way, way[1:]):
                n += span(cable, a, b, thick=WIRE)

    # ---- the coal, the tools, the oil can
    n += K.put(c, own[PREFIX + "coal"], (COAL_AT[0], FEET, COAL_AT[1]), yaw=0.0, origin=origin)
    n += K.put(c, own[PREFIX + "toolboard"], (GIRDER_X[0] + 0.5, FEET + 1.75, NORTH), mount="wall", facing="south", origin=origin)
    n += K.put(c, own[PREFIX + "oilcan"], (RAIL_TURN - 0.6, FEET, DECK_Z[1] + 1.4), yaw=160.0, origin=origin)

    # ---- the knees under the girders' ends, on the piers of the two end walls
    for x in GIRDER_X:
        north = Z0 if x < FOOT[0] else FOOT[1] + 1                  # the fourth girder starts at the chimney's foot
        put(x, EAVES, north, st(roles.IRON_RIVETED.stairs, facing="north", half="top"))
        put(x, EAVES, Z1, st(roles.IRON_RIVETED.stairs, facing="south", half="top"))

    # ---- the engineer's desk in the north-west corner (props/furniture, props/paper), the green lamp on it
    desk_x, desk_z = WEST + 0.4375, DESK_Z[1] + 0.0
    desk_top = FEET + furniture.TOP["writing_desk"]
    n += furniture.place(c, "writing_desk", (desk_x, FEET, desk_z), facing="east", origin=origin)
    n += furniture.place(c, "swivel_chair", (desk_x + 1.075, FEET, desk_z), yaw=K.FACING["west"] + 20.0, origin=origin)
    n += paper.place(c, "logbook", (desk_x + 0.1, desk_top, desk_z + 0.25), yaw=K.FACING["east"] + 8.0, origin=origin)
    offer(DESK_LIGHT, DESK_LAMP, "desk lamp")
    n += lamps.place(c, "desk_green", (X0 + 0.45, desk_top, DESK_Z[0] + 0.5), facing="east", origin=origin, light=False)
    # the telephone to the observatory and the bell over it, on the pier between the desk and the board
    n += electrics.place(c, "wall_phone", (WEST, PHONE_Y, PHONE_Z), facing="east", origin=origin)
    n += electrics.place(c, "bell", (WEST, PHONE_Y + 2.25, PHONE_Z), facing="east", origin=origin)

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
    # the stoker's lantern on its box, in the line of the open wicket
    offer((int(math.floor(LANTERN_AT[0])), FEET, int(math.floor(LANTERN_AT[1]))), LANTERN, "stoker's lantern")
    n += K.put(c, own[PREFIX + "lantern"], (LANTERN_AT[0], FEET, LANTERN_AT[1]), yaw=0.0, origin=origin)
    # behind the boilers, on the east wall; at the blind end of the alley north of No. 1, on the chimney's foot
    offer(BACK_LIGHT, BACK_LAMP, "boiler back lamp")
    n += lamps.place(c, "bracket", BACK_AT, facing="west", origin=origin, light=False, version=LAMPS)
    offer(ALLEY_LIGHT, ALLEY_LAMP, "alley lamp")
    n += lamps.place(c, "cage", ALLEY_AT, facing="west", origin=origin, light=False, version=LAMPS)
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
