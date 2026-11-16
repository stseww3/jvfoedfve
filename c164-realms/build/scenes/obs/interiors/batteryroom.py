"""Work package interiors/batteryroom: the accumulator room under the time room.
Card: plan/packages/interiors/batteryroom.md.

The time service may not stop when the engine does. So the ground floor of the north wing, right
under the time room, is a room full of accumulators: the power house charges them, and they feed
the clocks, the telegraph and the time ball upstairs, evenly, whatever the engine does.

The room is the closed cavity main/shell leaves under the time room: 12 wide (x 2..13), 19 long
(z -25..-7), six rows high (feet at 0, the last clear row 5; the block over it is the time room's
floor). Its door is one cell in the south wall, (7, 0..1, -6), from under the star hall's north
gallery (HALL_DOOR; main/shell cuts it when the room has passed its review, not before).

What stands where (plan cells; north is -z, one comes in at the south end and looks north):

  aisle             two cells wide on the room's long axis (x 7..8), from the door to the board
  the battery       the star piece. Two banks, one either side of the aisle (x 5..6 and x 9..10),
                    each two rows of cells back to back, thirteen blocks long (z -22..-10: from
                    the first beam to the last). A cell is an open glass jar: one sees its bright
                    rim and corners, the level of the acid, and through the glass the plates,
                    edge on to the aisle, grey and brown by turns. The jars stand on a timber
                    stand of two tiers on porcelain feet, two jars to a block of a row and tier,
                    and lead straps join each to the next: 208 jars. One model to a block of a
                    row (CELLS), placed 52 times
  gantries          under each of the four beams a timber frame over each bank, its posts the
                    stand's own; on its lintel porcelain insulators carry the bus bars
  bus bars          a pair of copper bars over each bank at 2.5 blocks, from the last jar at the
                    south end north to the board (machines-side piece; a plain bar stands in here
                    until it is in the tree)
  switchboard       on the north wall at the end of the aisle, three slabs of slate standing off
                    the wall, the middle one as wide as the aisle with the voltmeter and the
                    ammeter on it (a stand-in here: the board is c346's piece)
  window cases      the base storey's windows are dark, barred ones and may not show a light
                    outside. A whole block of iron louvre stands inside every window cell (the
                    first cell behind the glass, y 3..4): no light of the room reaches the glass
  floor             slate, which acid does not eat; under each bank a tray of lead-coloured plate;
                    a drain grating across the aisle
  ceiling           four riveted beams on the pilaster rows (y 5); between them the time room's
                    floor is seen from below, with the iron bed of its cable trough along the
                    north wall (z -24), where the two feeders go up at x 6 and x 9

Light: cold ground, warm points. Three caged lamps and nothing else: two over the aisle on the
south faces of the first and the third beam, one on the north wall over the board. A caged lamp
throws its light down, so its source is offered under it, in the aisle at the height of the jars
(LAMPS). The models of the room are held at the height of the upper tier (HELD), so that a jar
takes the light of the row its glass stands in and not that of the floor.

build() is what the master scene calls: nothing while MOVED_IN is off. The box test scene,
build/scenes/obs_int_batteryroom, dresses a slice of the real building cut out round the cavity.
"""
import functools

from artkit import models as M
from artkit.blocks import st
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..main import _plan as MP
from ..main import shell
from ..props import _kit as K
from ..props import lamps

MOVED_IN = False
NAME = "interiors/batteryroom"
PREFIX = "int_batteryroom_"
PX = 1 / 16.0

# ---- the room: the cavity under the time room (main/shell.ROOMS["time room"]), a storey lower
X0, Z0, X1, Z1 = shell.ROOMS["time room"]["box"]    # 2, -25, 13, -7
FEET = S.GROUND                                     # 0
FLOOR_Y = FEET - 1                                  # -1: the floor block, in the row of the terrace's paving
TOP = S.STRING - 1                                  # 5: the last clear row; the block over it is the time room's floor
AXIS_X = S.mid(X0, X1)                              # 8.0: the long axis, between two cells
NORTH, SOUTH, WEST, EAST = float(Z0), Z1 + 1.0, float(X0), X1 + 1.0     # the four wall faces: -25, -6, 2, 14
HALL_DOOR = (7, Z1 + 1)                             # (7, -6): the cell of the south wall the door stands in. The star
#                                                     hall reads this name (aisle_doors); x 8 is a pilaster of the hall
DOOR_Y = (FEET, FEET + 1)                           # the doorway is two rows high
BEAM_Z = tuple(z for z in range(Z0, Z1 + 1) if MP.on_pilaster(z))               # -22, -18, -14, -10
EAST_BAYS = tuple(b for b in range(1, S.N_BAYS + 1) if set(MP.window_rows(b)) <= set(range(Z0, Z1 + 1)))
WEST_BAYS = tuple(b for b in EAST_BAYS if all(abs(z - S.DOME_CENTRE[1]) > MP.WEST_BLIND_Z for z in MP.window_rows(b)))
WINDOW_Y = MP.BASE_WINDOW                           # 3..4: the base storey's small windows

# ---- the battery
AISLE = (7, 8)
BANKS = ((5, 6), (9, 10))                           # a bank: two rows of cells back to back
BANK_Z = (BEAM_Z[0], BEAM_Z[-1])                    # -22..-10: thirteen blocks, from the first beam to the last
JAR = (6.0, 9.0, 10.0)                              # px: a jar along its row, high, across the row
JAR_AT = (-4.0, 4.0)                                # px along the row from the middle of a block: the middles of its two jars
TIERS = (4.0, 19.0)                                 # px above the floor: where the jars of the two tiers stand
LEVEL = 6.0                                         # px above a jar's foot: the level of its acid
HELD = 1.0                                          # blocks above the floor: where the models of the battery are held
#                                                     from. A display takes the light of the cell it is held in
POST = (6.0, 8.0)                                   # px from the middle of a row: a post of the stand, at the row's two faces
GANTRY_TOP = 37.0                                   # px above the floor: the top of a gantry's lintel
BAR_Y = (40.0, 44.0)                                # px above the floor: a bus bar, on three pixels of porcelain
BAR_OFF = 4.0                                       # px either side of the middle of a bank: its two bars
BAR_Z = (NORTH + 6 * PX, BANK_Z[1] + 1 - 1 * PX)    # from the face of the board to over the last jar

# ---- the switchboard (a stand-in: the board is the machines line's)
BOARD = ((5.5, 7.0), (7.0, 9.0), (9.0, 10.5))       # blocks along the north wall: its three slabs
BOARD_Y = (0.75, 3.0)                               # blocks above the floor: the foot and the head of a slab
BOARD_OFF = (4.0, 6.0)                              # px off the wall: the back and the face of a slab
FEEDS = (6, 9)                                      # the columns the two feeders go up in: under the time room's two risers

# ---- light: what the room asks of the light line. Caged lamps are third rank (5..8)
LAMP_VERSION = "a"
LAMPS = (
    # where the lamp is fixed and the way that face looks; the cells its light is offered in; the level
    ((AXIS_X, TOP + 0.5, BEAM_Z[-1] + 1.0), "south", ((AISLE[0], FEET + 2, BEAM_Z[-1] + 1), (AISLE[1], FEET + 2, BEAM_Z[-1] + 1)), 8,
     "aisle south"),
    ((AXIS_X, TOP + 0.5, BEAM_Z[1] + 1.0), "south", ((AISLE[0], FEET + 2, BEAM_Z[1] + 1), (AISLE[1], FEET + 2, BEAM_Z[1] + 1)), 7,
     "aisle north"),
    ((AXIS_X, FEET + 4.0, NORTH), "south", ((AISLE[0], FEET + 3, Z0), (AISLE[1], FEET + 3, Z0)), 8, "board"),
)
CAGE_RANK = 3

# ---- the colours of a jar, seen through its glass
GLASS = dict(
    g=K.SHEEN,                          # the rim and the corners: clear glass holds a little of the sky
    l=P.RAMPS["night_glass"][3],        # the level of the acid
    a=P.RAMPS["night_glass"][0],        # acid in the shade
    d=P.RAMPS["night_glass"][1],        # the thick foot of the jar
    n=P.RAMPS["iron"][5],               # a negative plate: lead grey
    m=P.RAMPS["iron"][4],               # the grid of its paste
    p=P.RAMPS["old_copper"][0],         # a positive plate: brown
)
JAR_SIDE = (                            # the face a jar turns to the aisle: its plates edge on
    "gggggg",
    "g....g",
    "g....g",
    "llllll",
    "gnpnpg",
    "gnpnpg",
    "gnpnpg",
    "gnpnpg",
    "dddddd",
)
JAR_END = (                             # the face at the end of a row: the last plate flat on
    "gggggggggg",
    "g........g",
    "g........g",
    "llllllllll",
    "gnnnnnnnng",
    "gnmnmnmnng",
    "gnnnnnnnng",
    "gnmnmnmnng",
    "dddddddddd",
)
JAR_TOP = (                             # looked into from above: the acid and the heads of the plates
    "llllllllll",
    "lnnnnnnnnl",
    "lppppppppl",
    "lnnnnnnnnl",
    "lppppppppl",
    "llllllllll",
)
assert (len(JAR_SIDE[0]), len(JAR_SIDE), len(JAR_END[0])) == JAR, "the faces of a jar are drawn pixel for pixel"
LEAD = K.flat("iron", 5)
WOOD = P.mat("dark_wood", base=3)
WOOD_D = P.mat("dark_wood", base=1)
CHINA = P.mat("porcelain")


def _jar(m, name, foot, along):
    """One cell: a glass jar with its foot at `foot` px above the floor, its middle `along` px along
    the row from the middle of the block. The glass is one box whose faces are drawn; the acid's
    surface lies inside it."""
    wide, high, deep = JAR
    lo, hi = (-deep / 2.0, foot, along - wide / 2.0), (deep / 2.0, foot + high, along + wide / 2.0)
    side, end = Sprite(name + "_side", JAR_SIDE, GLASS), Sprite(name + "_end", JAR_END, GLASS)
    m.box(lo, hi, K.flat("night_glass", 1), skip="ud", faces={"e": side, "w": side, "n": end, "s": end})
    m.box((lo[0], foot + LEVEL - 0.5, lo[2]), (hi[0], foot + LEVEL, hi[2]), K.flat("night_glass", 1), skip="nsewd",
          faces={"u": Sprite(name + "_top", JAR_TOP, GLASS)})


def _cells():
    """One block of a row of the battery: four jars, two to a tier, on the timber stand. The sole
    plates stand on porcelain feet; the bearers run on from block to block; a post stands at each
    face of the row before the gap between the two jars; lead straps join jar to jar along the
    row. Held HELD above the middle of the block's floor; the row runs along z."""
    name = PREFIX + "cells"
    m = M.Model(name, anchor=(0.0, HELD * 16.0, 0.0))
    for x in (-4.0, 4.0):
        for z in (-6.0, 6.0):
            m.box((x - 1.0, 0.0, z - 1.0), (x + 1.0, 2.0, z + 1.0), CHINA)                          # the feet
        m.box((x - 1.0, 2.0, -8.0), (x + 1.0, TIERS[0], 8.0), WOOD, skip="ns", grain="z")           # the sole plates
        m.box((x - 1.0, TIERS[1] - 2.0, -8.0), (x + 1.0, TIERS[1], 8.0), WOOD, skip="ns", grain="z")    # the bearers of the upper tier
    for side in (-1.0, 1.0):
        a, b = sorted((side * POST[0], side * POST[1]))
        m.box((a, 0.0, -1.0), (b, TIERS[1], 1.0), WOOD_D, grain="y")                                # the posts
    m.box((-POST[0], TIERS[1] - 4.0, -1.0), (POST[0], TIERS[1] - 2.0, 1.0), WOOD_D, grain="x")      # the tie under the upper tier
    for foot in TIERS:
        for along in JAR_AT:
            _jar(m, name, foot, along)
        top = foot + JAR[1]
        m.box((-1.0, top, JAR_AT[0] + 1.0), (1.0, top + 1.0, JAR_AT[1] - 1.0), LEAD)                # the strap between the block's two jars
        for z0, z1 in ((-8.0, JAR_AT[0] - 1.0), (JAR_AT[1] + 1.0, 8.0)):
            m.box((-1.0, top, z0), (1.0, top + 1.0, z1), LEAD)                                      # ... and on to the next block's
    return m


def _gantry():
    """The frame over a bank under a beam: the posts of the stand at the bank's two faces carried
    up, a lintel across them, and on the lintel the porcelain the two bus bars lie on. Held HELD
    above the floor on the middle line of the bank; the bank runs along z."""
    m = M.Model(PREFIX + "gantry", anchor=(0.0, HELD * 16.0, 0.0))
    reach = 8.0 + POST[1]                                                                           # 16: the bank's face
    for side in (-1.0, 1.0):
        a, b = sorted((side * (reach - 2.0), side * reach))
        m.box((a, TIERS[1], -1.0), (b, GANTRY_TOP - 2.0, 1.0), WOOD_D, grain="y")
        m.box((side * BAR_OFF - 1.0, GANTRY_TOP, -1.0), (side * BAR_OFF + 1.0, BAR_Y[0], 1.0), CHINA)
    m.box((-reach, GANTRY_TOP - 2.0, -1.0), (reach, GANTRY_TOP, 1.0), WOOD_D, grain="x")
    return m


def _bar():
    """A bus bar: a flat copper bar on edge, 48 long along +z from its anchor, to be stretched from
    the board to the last jar (artkit.models.between). One flat tone, so stretching smears nothing."""
    m = M.Model(PREFIX + "bar")
    m.box((-0.5, 0.0, 0.0), (0.5, BAR_Y[1] - BAR_Y[0], 48.0), K.flat("old_copper", 3))
    return m


def board_name(i):
    return f"{PREFIX}board_{i}"


def _board(i):
    """A slab of the switchboard, a stand-in: slate standing off the wall on two iron uprights; on
    the middle one the two meters, cream dials in brass rims. Anchor: the point on the wall behind
    the middle of the slab's foot."""
    x0, x1 = BOARD[i]
    half = (x1 - x0) * 8.0
    high = (BOARD_Y[1] - BOARD_Y[0]) * 16.0
    m = M.Model(board_name(i))
    m.box((-half, 0.0, BOARD_OFF[0]), (half, high, BOARD_OFF[1]), P.mat("slate"))
    for x in (-half + 2.0, half - 4.0):
        m.box((x, -BOARD_Y[0] * 16.0, 0.0), (x + 2.0, high - 2.0, BOARD_OFF[0]), K.IRON_D, grain="y")
    if i == 1:
        for x in (-8.0, 8.0):
            m.tube("z", (x, high - 9.0), BOARD_OFF[1], BOARD_OFF[1] + 1.5, 4.5, K.BRASS, sides=12, cap=K.flat("cream", 3))
    return m


@functools.lru_cache(maxsize=None)
def _models():
    out = {PREFIX + "cells": _cells(), PREFIX + "gantry": _gantry(), PREFIX + "bar": _bar()}
    out.update({board_name(i): _board(i) for i in range(len(BOARD))})
    return out


def models():
    """The room's own models: a block of the battery, the gantry over a bank, and the stand-ins of
    the bus bars and of the switchboard. Its lamps are props/lamps'."""
    return dict(_models())


def their_models():
    """The models of the pieces of other packages the room places: what a test scene packs besides
    the room's own."""
    return dict(lamps.models())


def window_cells():
    """The first cell behind the glass of every window of the room: [((x, y, z), the way the room
    lies from it)]."""
    out = []
    for bays, x, inward in ((EAST_BAYS, X1, "west"), (WEST_BAYS, X0, "east")):
        for bay in bays:
            out += [((x, y, z), inward) for z in MP.window_rows(bay) for y in range(WINDOW_Y[0], WINDOW_Y[1] + 1)]
    return out


def in_bank(x, z):
    return any(a <= x <= b for a, b in BANKS) and BANK_Z[0] <= z <= BANK_Z[1]


def build_batteryroom(c, origin=(0, 0, 0), roles=B):
    """Dress the room standing at `origin`. Returns dict(entities=<display entities placed>,
    lights=[((x, y, z), level, why)]): the light sources it has offered to the light line."""
    ox, oy, oz = origin
    lights, n = [], 0
    own = _models()

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    # ---- the floor: slate; a tray of lead-coloured plate under each bank; a drain across the aisle
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            put(x, FLOOR_Y, z, roles.IRON_PLATE if in_bank(x, z) else roles.SLATE_SMOOTH.block)
    for x in AISLE:
        put(x, FLOOR_Y, BEAM_Z[2] - 2, roles.IRON_GRATE)
        put(x, FLOOR_Y - 1, BEAM_Z[2] - 2, roles.IRON_PLATE)

    # ---- the ceiling: riveted beams on the pilaster rows
    for z in BEAM_Z:
        for x in range(X0, X1 + 1):
            put(x, TOP, z, roles.IRON_RIVETED.block)

    # ---- the window cases: a block of iron louvre in every cell behind the glass
    for (x, y, z), inward in window_cells():
        put(x, y, z, st(roles.PANELS["louvre"], facing=inward))

    # ---- the battery: the stand and its jars, block by block; a gantry over each bank under each beam
    for a, b in BANKS:
        for x in (a, b):
            for z in range(BANK_Z[0], BANK_Z[1] + 1):
                n += K.put(c, own[PREFIX + "cells"], (S.mid(x), FEET + HELD, S.mid(z)), origin=origin)
        for z in BEAM_Z:
            n += K.put(c, own[PREFIX + "gantry"], (b + K.NUDGE, FEET + HELD, S.mid(z)), origin=origin)
        for off in (-BAR_OFF, BAR_OFF):                                 # the bus bars (a stand-in)
            p = (ox + b + off * PX, oy + FEET + BAR_Y[0] * PX, oz + BAR_Z[0])
            q = (p[0], p[1], oz + BAR_Z[1])
            c.add_entity(*p, M.between(own[PREFIX + "bar"], p, q))
            n += 1

    # ---- the switchboard on the north wall (a stand-in)
    for i, (x0, x1) in enumerate(BOARD):
        n += K.put(c, own[board_name(i)], ((x0 + x1) / 2.0, FEET + BOARD_Y[0], NORTH), mount="wall", facing="south", origin=origin)

    # ---- the caged lamps; the light of each is offered under it, at the height of the jars
    for pos, facing, cells, level, why in LAMPS:
        n += lamps.place(c, "cage", pos, facing=facing, origin=origin, light=False, version=LAMP_VERSION)
        for cell in cells:
            at = (ox + cell[0], oy + cell[1], oz + cell[2])
            lights.append((at, level, f"{NAME}:{why}"))
            _offer(c, at, level, f"{NAME}:{why}", CAGE_RANK)
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
    """The master scene's call: the room in the cavity main/shell leaves; nothing while MOVED_IN is
    off (the door is not cut before the room has passed its review). Returns the number of display
    entities placed."""
    if not MOVED_IN:
        return 0
    return build_batteryroom(canvas, origin)["entities"]
