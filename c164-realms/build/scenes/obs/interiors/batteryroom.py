"""Work package interiors/batteryroom: the accumulator room under the time room.
Card: plan/packages/interiors/batteryroom.md.

The time service may not stop when the engine does. So the ground floor of the north wing, right
under the time room, is a room full of accumulators: the power house charges them, and they feed
the clocks, the telegraph and the time ball upstairs, evenly, whatever the engine does.

The room is the closed cavity main/shell leaves under the time room: 12 wide (x 2..13), 19 long
(z -25..-7), six rows high (feet at 0, the last clear row 5; the block over it is the time room's
floor). Its door is one cell in the south wall, (7, 0..1, -6), from under the star hall's north
gallery (HALL_DOOR; main/shell cuts it once the room is in the master scene).

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
                    stand's own; on its lintel porcelain insulators carry the bus bars. At the
                    south end of a bank a lead bar rises from the last jar of each row to its bar
  bus bars          a pair of copper bars over each bank at 2.5 blocks, from the last jar at the
                    south end north to the board (machines/batteryboard lays them, in lengths
                    from gantry to gantry)
  switchboard       before the north wall at the end of the aisle, three slabs of slate on iron
                    legs, a wing before each bank: meters, knife switches, the change-over switch
                    for charging and discharging; the battery ammeter's pointer swings
                    (machines/batteryboard, c346)
  cable             from the power house: lead-sheathed, out of the south wall behind the star
                    hall's board, along the top of the dado on the south, west and north walls
                    on porcelain cleats and in behind the board's west wing. The two feeders to
                    the time room go up behind the board in conduits (the board's risers)
  small pieces      three carboys of distilled water in their crates by the west wall; the
                    hydrometer's shelf under the last east window; a rubber apron and gloves on
                    pegs and the record board on the south wall by the door; an enamel sign on
                    the second beam over the aisle: no naked flame, a figure and nothing written
  window cases      the base storey's windows are dark, barred ones and may not show a light
                    outside. A whole block of iron louvre stands inside every window cell (the
                    first cell behind the glass, y 3..4): no light of the room reaches the glass
  floor             slate, which acid does not eat; under each bank a tray of lead-coloured plate;
                    a drain grating across the aisle
  ceiling           four riveted beams on the pilaster rows (y 5); between them the time room's
                    floor is seen from below, with the iron bed of its cable trough along the
                    north wall (z -24), where the two feeders go up at x 6 and x 9

Light: cold ground, warm points. Three caged lamps and nothing else: two over the aisle on the
south faces of the first and the third beam, one over the board on the bed of the time room's
cable trough. A caged lamp throws its light down, so its light is offered under it, in the aisle
between the jars (LAMPS); half way between two lamps a fill of what both throw (FILLS). The models of the room are held at the height of the upper tier (HELD), so that a jar
takes the light of the row its glass stands in and not that of the floor.

build() is what the master scene calls; it places nothing while MOVED_IN is off. The box test scene,
build/scenes/obs_int_batteryroom, dresses a slice of the real building cut out round the cavity.
"""
import functools

from artkit import models as M
from artkit.blocks import st
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..machines import batteryboard as BB
from ..machines import board as PB
from ..main import _plan as MP
from ..main import shell
from ..props import _kit as K
from ..props import lamps

MOVED_IN = True            # the master scene dresses the room (a card's switch is turned on with its delivery); the
#                            doorway is main/shell's to cut (HALL_DOOR): until then the room stands closed
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
JAR = (6.0, 10.0, 10.0)                             # px: a jar along its row, high, across the row
JAR_AT = (-4.0, 4.0)                                # px along the row from the middle of a block: the middles of its two jars
TIERS = (4.0, 19.0)                                 # px above the floor: where the jars of the two tiers stand
LEVEL = 6.0                                         # px above a jar's foot: the top of the line of its acid's level
HELD = 1.0                                          # blocks above the floor: where the models of the battery are held
#                                                     from. A display takes the light of the cell it is held in
POST = (6.0, 8.0)                                   # px from the middle of a row: a post of the stand, at the row's two faces
GANTRY_TOP = 37.0                                   # px above the floor: the top of a gantry's lintel
BAR_Y = (40.0, 44.0)                                # px above the floor: a bus bar, on three pixels of porcelain
BAR_OFF = 4.0                                       # px either side of the middle of a bank: its two bars
BAR_SOUTH = BANK_Z[1] + 1 - 1 * PX                  # the bars end over the last jar

# ---- the switchboard and the bars: machines/batteryboard's (c346). It stands before the north wall, x 5..11,
# y 1..4, a wing before each bank; its pieces take the light of the one cell BB.STAND is in
BOARD_LIGHT = (8, FEET + 4, Z0 + 1)                 # (8, 4, -24): the cell over that one, where the board's lamp shines

# ---- light: what the room asks of the light line. Caged lamps are third rank (5..8)
LAMP_VERSION = "a"
TROUGH_Z = Z0 + 1                                   # -24: the time room's cable trough hangs in the last row along this line
LAMP_Y = TOP + 5 * PX                               # a caged lamp is as high as a beam: its foot on the beam's lower edge


def _pool(z):
    """What a lamp over the aisle throws down: under it, between the jars, as much as a source
    beside a machine may give (8); a row either way and at the height of the bars a step less."""
    return tuple(((x, FEET + y, z + dz), level) for x in AISLE for y, dz, level in ((1, 0, 8), (1, -1, 7), (1, 1, 7), (3, 0, 7)))


LAMPS = (
    # where the lamp is fixed and the way that face looks; the cells its light is offered in, each with its level
    ((AXIS_X, LAMP_Y, BEAM_Z[-1] + 1.0), "south", _pool(BEAM_Z[-1] + 1), "aisle south"),    # on the first beam, over the way in
    ((AXIS_X, LAMP_Y, BEAM_Z[1] + 1.0), "south", _pool(BEAM_Z[1] + 1), "aisle north"),      # on the third beam
    ((AXIS_X, LAMP_Y, TROUGH_Z + 1.0), "south",                                             # on the trough's bed, over the board:
     tuple(((x, BOARD_LIGHT[1], BOARD_LIGHT[2]), 8) for x in AISLE)                         # on the board's face
     + tuple(((x, FEET + 1, TROUGH_Z + 1), 7) for x in AISLE), "board"),                    # and where one stands before it
)
FILL = 7                                            # between two lamps the aisle is walked in what both throw: a fill
FILLS = tuple((x, FEET + 2, z + 1) for z in (BEAM_Z[2], BEAM_Z[0]) for x in AISLE)      # under the second and the fourth beam
CAGE_RANK = 3

# ---- the cable from the power house and the small pieces
CABLE_OUT = (BB.FEED_IN[2] - NORTH) * 16.0          # 3 px off the wall: the cable's middle line, as the board takes it in
CABLE_R = 1.5                                       # px: its radius, lead sheath and all
CABLE_Y = BB.FEED_IN[1]                             # 2.125: it runs along the top of the dado
CABLE_IN = (5.5, FEET + 1.5)                        # where it comes through the south wall, behind the star hall's board
CABLE_END = BB.FEED_IN[0] + 0.5                     # x: it ends behind the board's west wing, between slab and wall
SIGN_AT = (AXIS_X, TOP + 0.5, BEAM_Z[2] + 1.0)      # the enamel sign: on the second beam, over the aisle
CARBOYS = ((WEST + 0.55, Z1 + 0.45), (WEST + 0.55, Z1 - 0.5), (WEST + 0.55, Z1 - 1.45))   # along the blind west wall
SHELF_AT = (EAST, FEET + 1.5, Z1 - 0.5)             # the hydrometer's shelf: on the east wall, under the last window
APRON_AT = (EAST - 2.5, FEET + 2.5, SOUTH)          # the pegs with the apron and the gloves: south wall, east of the door
RECORD_AT = (HALL_DOOR[0] + 2.25, FEET + 1.75, SOUTH)   # the record board: beside the door, where one leaves

# ---- a jar, drawn pixel for pixel. Clear glass is left out (props/_kit.pane): over the acid one looks
# through the jar, and what says glass is its rim, one lit corner and the line of the acid's level
GLASS = dict(
    g=K.SHEEN,                          # the rim: clear glass holds a little of the sky
    h=P.RAMPS["night_glass"][3],        # the corner the light catches, and the level of the acid
    a=P.RAMPS["night_glass"][0],        # acid in the shade, beside the plates
    d=P.RAMPS["night_glass"][1],        # the thick foot of the jar
    n=P.RAMPS["iron"][5],               # a negative plate: lead grey
    q=P.RAMPS["iron"][3],               # a plate seen flat on, at the end of a row
    m=P.RAMPS["iron"][4],               # the grid of its paste
    p=P.RAMPS["old_copper"][1],         # a positive plate: brown
)
JAR_SIDE = (                            # the face a jar turns to the aisle: its plates edge on
    "gggggg",
    "h.....",
    "h.....",
    "h.....",
    "hhhhhh",
    "apnpna",
    "apnpna",
    "apnpna",
    "apnpna",
    "dddddd",
)
JAR_END = (                             # the face at the end of a row: the last plate flat on
    "gggggggggg",
    "h.........",
    "h.........",
    "h.........",
    "hhhhhhhhhh",
    "aqqqqqqqqa",
    "aqmqmqmqqa",
    "aqqqqqqqqa",
    "aqmqmqmqqa",
    "dddddddddd",
)
JAR_TOP = (                             # looked into from above: the acid and the heads of the plates
    "aaaaaaaaaa",
    "appppppppa",
    "annnnnnnna",
    "appppppppa",
    "annnnnnnna",
    "aaaaaaaaaa",
)
assert (len(JAR_SIDE[0]), len(JAR_SIDE), len(JAR_END[0])) == JAR, "the faces of a jar are drawn pixel for pixel"
assert len(JAR_SIDE) - JAR_SIDE.index("hhhhhh") == LEVEL, "the acid's surface lies at the line drawn on the glass"
LEAD = K.flat("iron", 5)
WOOD = P.mat("dark_wood", base=3)
WOOD_D = P.mat("dark_wood", base=1)
DEAL = P.mat("dark_wood", base=4)
CHINA = P.mat("porcelain")
CHINA_D = P.mat("porcelain", base=2)
SHEATH = K.flat("iron", 2)                          # the cable's lead sheath
RUBBER = K.flat("iron", 0)                          # the apron
RUBBER_R = K.flat("old_copper", 1)                  # the gloves: red rubber

INK = dict(c=P.RAMPS["cream"][3], s=P.RAMPS["cream"][1], b=P.RAMPS["enamel"][2], i=P.RAMPS["iron"][1],
           e=P.RAMPS["iron"][1], w=P.RAMPS["cream"][3], k=P.RAMPS["iron"][0], r=P.RAMPS["signal"][2])
RECORD = (                              # the sheet on the record board: a heading strip, rows of figures as strokes
    "cccccccc",
    "cbbbbbbc",
    "cccccccc",
    "ciiciiic",
    "cccccccc",
    "ciciicic",
    "cccccccc",
    "ciiicicc",
    "cccccccc",
    "cicciiic",
    "cccccccc",
    "ssssssss",
)
SIGN = (                                # no naked flame: a flame, struck out. A figure, nothing written
    "eeeeeeeeeeee",
    "ewwwwwwwwwre",
    "ewwwwkwwwrre",
    "ewwwwkkwrrwe",
    "ewwwkkkrrwwe",
    "ewwwkkrrkwwe",
    "ewwkkrrkkwwe",
    "ewwkrrkkkwwe",
    "ewwrrkkkkwwe",
    "ewrrwkkkwwwe",
    "errwwwwwwwwe",
    "eeeeeeeeeeee",
)


def _jar(m, name, foot, along):
    """One cell: a glass jar with its foot at `foot` px above the floor, its middle `along` px along
    the row from the middle of the block. The glass is one box whose faces are drawn; the acid's
    surface lies inside it."""
    wide, high, deep = JAR
    lo, hi = (-deep / 2.0, foot, along - wide / 2.0), (deep / 2.0, foot + high, along + wide / 2.0)
    side, end = Sprite(name + "_side", JAR_SIDE, GLASS), Sprite(name + "_end", JAR_END, GLASS)
    m.box(lo, hi, K.flat("night_glass", 1), skip="ud", faces={"e": side, "w": side, "n": end, "s": end})
    m.box((lo[0], foot + LEVEL - 1.0, lo[2]), (hi[0], foot + LEVEL - 0.5, hi[2]), K.flat("night_glass", 1), skip="nsewd",
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
        m.box((side * BAR_OFF - 1.0, GANTRY_TOP, -1.0), (side * BAR_OFF + 1.0, BAR_Y[0], 1.0), CHINA_D)
    m.box((-reach, GANTRY_TOP - 2.0, -1.0), (reach, GANTRY_TOP, 1.0), WOOD_D, grain="x")
    return m


def _taps():
    """Where a bank's battery ends: from the strap of the last jar of each row a lead bar across
    to under the bank's bus bar and up to it. For the last block of a bank; held as the gantry."""
    m = M.Model(PREFIX + "taps", anchor=(0.0, HELD * 16.0, 0.0))
    top = TIERS[1] + JAR[1]
    for side in (-1.0, 1.0):
        a, b = sorted((side * BAR_OFF - side * 0.5, side * 8.0))
        m.box((a, top, 5.0), (b, top + 1.0, 6.0), LEAD)
        a, b = sorted((side * BAR_OFF - side * 0.5, side * BAR_OFF + side * 0.5))
        m.box((a, top + 1.0, 5.0), (b, BAR_Y[0], 6.0), LEAD)
    return m


def _cable():
    """The cable from the power house: lead-sheathed, 48 long along +z from its anchor, to be
    stretched from point to point (artkit.models.between)."""
    m = M.Model(PREFIX + "cable")
    m.tube("z", (0.0, 0.0), 0.0, 48.0, CABLE_R, SHEATH, sides=8)
    return m


def _cleat():
    """A porcelain cleat that holds the cable to the wall. Anchor: the point of the wall behind
    the cable's middle line; +z out of the wall."""
    m = M.Model(PREFIX + "cleat")
    m.box((-2.0, -3.0, 0.0), (2.0, 3.0, 0.75), K.IRON_D)
    m.box((-1.5, -2.5, 0.75), (1.5, 2.5, CABLE_OUT + CABLE_R + 0.5), CHINA)
    m.box((-0.5, -0.5, CABLE_OUT + CABLE_R + 0.5), (0.5, 0.5, CABLE_OUT + CABLE_R + 1.0), K.BRASS)
    return m


def _entry():
    """Where the cable comes out of the wall: a flange and the gland it leaves by. Anchor: the
    point of the wall on its middle line."""
    m = M.Model(PREFIX + "entry")
    m.tube("z", (0.0, 0.0), 0.0, 1.0, CABLE_R + 2.0, K.IRON, sides=8)
    m.tube("z", (0.0, 0.0), 1.0, CABLE_OUT + CABLE_R, CABLE_R + 0.5, K.IRON_D, sides=8)
    return m


def _carboy():
    """A carboy of distilled water: a glass balloon in a crate of raw deal, a cork in its neck.
    Anchor: the middle of its foot."""
    m = M.Model(PREFIX + "carboy")
    for x in (-6.0, 5.0):
        for z in (-6.0, 5.0):
            m.box((x, 0.0, z), (x + 1.0, 9.0, z + 1.0), WOOD_D, grain="y")
    for y in (1.0, 5.0):
        m.box((-5.0, y, -6.0), (5.0, y + 3.0, -5.5), DEAL, grain="x")
        m.box((-5.0, y, 5.5), (5.0, y + 3.0, 6.0), DEAL, grain="x")
        m.box((-6.0, y, -5.0), (-5.5, y + 3.0, 5.0), DEAL, grain="z")
        m.box((5.5, y, -5.0), (6.0, y + 3.0, 5.0), DEAL, grain="z")
    m.box((-5.5, 0.0, -5.5), (5.5, 1.0, 5.5), DEAL, grain="x")
    K.glass_ball(m, (0.0, 7.0, 0.0), 5.0, [(-1.0, 0.3, 3, K.flat("night_glass", 1)), (0.3, 0.7, 1, K.flat("night_glass", 2)),
                                           (0.7, 1.0, 1, K.flat("night_glass", 3))], emit=0)
    m.tube("y", (0.0, 0.0), 11.5, 14.0, 1.25, K.flat("night_glass", 2), sides=8)
    m.tube("y", (0.0, 0.0), 14.0, 15.0, 1.0, DEAL, sides=8)
    return m


def _shelf():
    """The shelf of the hydrometer: its tall glass with the float standing in the acid, two
    measuring jugs, a stoneware bottle. Anchor: the point of the wall behind the middle of the
    board's top; +z out of the wall."""
    m = M.Model(PREFIX + "shelf")
    m.box((-10.0, -1.0, 0.0), (10.0, 0.0, 5.0), WOOD, grain="x")
    for x in (-8.0, 7.0):
        m.box((x, -5.0, 0.0), (x + 1.0, -1.0, 1.0), K.IRON_D, grain="y")
        m.box((x, -2.0, 1.0), (x + 1.0, -1.0, 4.0), K.IRON_D, grain="z")
    m.tube("y", (-6.0, 2.5), 0.0, 6.0, 1.5, K.flat("night_glass", 1), sides=8)
    m.tube("y", (-6.0, 2.5), 6.0, 8.0, 1.5, K.flat("night_glass", 3), sides=8, cap=K.flat("night_glass", 0))
    m.box((-6.5, 8.0, 2.0), (-5.5, 11.0, 3.0), K.flat("cream", 3))
    m.tube("y", (-1.0, 2.5), 0.0, 4.0, 1.5, CHINA, sides=8, cap=CHINA_D)
    m.tube("y", (3.0, 2.5), 0.0, 3.0, 1.25, CHINA, sides=8, cap=CHINA_D)
    m.tube("y", (7.0, 2.5), 0.0, 5.0, 1.5, K.flat("old_copper", 1), sides=8)
    m.tube("y", (7.0, 2.5), 5.0, 6.5, 0.75, K.flat("old_copper", 0), sides=8)
    return m


def _apron():
    """Three pegs on a rail: the rubber apron on two of them, the pair of gloves on the third.
    Anchor: the point of the wall behind the middle of the rail; +z out of the wall."""
    m = M.Model(PREFIX + "apron")
    m.box((-9.0, -1.0, 0.0), (9.0, 1.0, 1.0), WOOD_D, grain="x")
    for x in (-6.0, -1.0, 6.0):
        m.box((x - 0.5, -0.5, 1.0), (x + 0.5, 0.5, 2.75), K.BRASS)
    m.box((-6.5, -2.0, 1.0), (-5.5, 0.0, 1.75), RUBBER)                 # the neck band, over two pegs
    m.box((-1.5, -2.0, 1.0), (-0.5, 0.0, 1.75), RUBBER)
    m.box((-6.5, -8.0, 1.0), (-0.5, -2.0, 1.75), RUBBER)                # the bib
    m.box((-8.5, -24.0, 1.0), (1.5, -8.0, 2.0), RUBBER)                 # the skirt
    m.box((-8.5, -9.0, 2.0), (1.5, -8.0, 2.25), K.flat("iron", 2))      # the fold at the waist catches the light
    for x in (4.0, 6.5):                                                # the gloves, cuffs up
        m.box((x, -3.0, 1.0), (x + 2.0, -1.0, 2.0), K.flat("old_copper", 2))
        m.box((x, -10.0, 1.0), (x + 2.0, -3.0, 2.0), RUBBER_R)
    return m


def _record():
    """The record board: a sheet of readings under a brass clip, a pencil on a string. Anchor:
    the point of the wall behind the middle of the board; +z out of the wall."""
    m = M.Model(PREFIX + "record")
    w, h = len(RECORD[0]), len(RECORD)
    m.box((-5.0, -7.5, 0.0), (5.0, 7.5, 1.0), WOOD_D, grain="y")
    m.box((-w / 2.0, -h / 2.0 - 0.5, 1.0), (w / 2.0, h / 2.0 - 0.5, 1.25), K.flat("cream", 2), skip="n",
          faces={"s": Sprite(PREFIX + "record_sheet", RECORD, INK)})
    m.box((-2.0, 5.0, 1.0), (2.0, 6.5, 2.0), K.BRASS)
    m.box((5.25, -5.0, 0.0), (5.75, 4.0, 0.5), K.flat("cream", 1))      # the string
    m.box((5.0, -8.0, 0.0), (6.0, -5.0, 1.0), K.flat("old_copper", 2))  # the pencil
    return m


def _sign():
    """The enamel sign over the aisle: no naked flame. Anchor: the middle of its back."""
    m = M.Model(PREFIX + "sign")
    w, h = len(SIGN[0]), len(SIGN)
    m.box((-w / 2.0, -h / 2.0, 0.0), (w / 2.0, h / 2.0, 0.5), K.flat("cream", 1), skip="n",
          faces={"s": Sprite(PREFIX + "sign_face", SIGN, INK)})
    return m


@functools.lru_cache(maxsize=None)
def _models():
    built = (_cells(), _gantry(), _taps(), _cable(), _cleat(), _entry(), _carboy(), _shelf(), _apron(), _record(), _sign())
    return {m.name: m for m in built}


def models():
    """The room's own models: a block of the battery, the gantry over a bank, the cable and what
    holds it, the small pieces. The board and the bars are machines/batteryboard's, the lamps
    props/lamps'."""
    return dict(_models())


def their_models():
    """The models of the pieces of other packages the room places: what a test scene packs besides
    the room's own."""
    return {**lamps.models(), **PB.models(), **BB.models()}       # the board's pointers are the power house board's


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

    def hang(name, pos, facing):
        """One of the room's own pieces on a wall face that looks the way `facing` says."""
        return K.put(c, own[PREFIX + name], pos, mount="wall", facing=facing, origin=origin)

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

    # ---- the battery: the stand and its jars, block by block; a gantry over each bank under each beam,
    # held in the row next to the aisle, whose light it takes
    for a, b in BANKS:
        for x in (a, b):
            for z in range(BANK_Z[0], BANK_Z[1] + 1):
                n += K.put(c, own[PREFIX + "cells"], (S.mid(x), FEET + HELD, S.mid(z)), origin=origin)
        inner = b + (K.NUDGE if b < AXIS_X else -K.NUDGE)
        for z in BEAM_Z:
            n += K.put(c, own[PREFIX + "gantry"], (inner, FEET + HELD, S.mid(z)), origin=origin)
        n += K.put(c, own[PREFIX + "taps"], (inner, FEET + HELD, S.mid(BANK_Z[1])), origin=origin)

    # ---- the switchboard before the north wall, and a pair of bars from each of its wings over a bank to
    # the last jar, laid in lengths from gantry to gantry (machines/batteryboard)
    n += BB.place(c, origin)
    for side in ("west", "east"):
        n += BB.run(c, side, BAR_SOUTH, tuple(S.mid(z) for z in BEAM_Z), origin)

    # ---- the cable from the power house: out of the south wall, up to the top of the dado, along the south,
    # the west and the north wall and in behind the board's west wing
    out = CABLE_OUT * PX
    route = ((CABLE_IN[0], CABLE_IN[1], SOUTH - out), (CABLE_IN[0], CABLE_Y, SOUTH - out), (WEST + out, CABLE_Y, SOUTH - out),
             (WEST + out, CABLE_Y, NORTH + out), (CABLE_END, CABLE_Y, NORTH + out))
    for p, q in zip(route, route[1:]):
        p, q = ((v[0] + ox, v[1] + oy, v[2] + oz) for v in (p, q))
        c.add_entity(*p, M.between(own[PREFIX + "cable"], p, q))
        n += 1
    n += hang("entry", (CABLE_IN[0], CABLE_IN[1], SOUTH), "north")
    n += hang("cleat", (S.mid(X0 + 1), CABLE_Y, SOUTH), "north")
    n += hang("cleat", (S.mid(X0 + 1), CABLE_Y, NORTH), "south")
    for z in BEAM_Z:
        n += hang("cleat", (WEST, CABLE_Y, S.mid(z)), "east")

    # ---- the small pieces
    for x, z in CARBOYS:
        n += K.put(c, own[PREFIX + "carboy"], (x, FEET, z), origin=origin)
    n += hang("shelf", SHELF_AT, "west")
    n += hang("apron", APRON_AT, "north")
    n += hang("record", RECORD_AT, "north")
    n += hang("sign", SIGN_AT, "south")

    # ---- the caged lamps; the light of each is offered under it, between the jars
    for pos, facing, cells, why in LAMPS:
        n += lamps.place(c, "cage", pos, facing=facing, origin=origin, light=False, version=LAMP_VERSION)
        for cell, level in cells:
            at = (ox + cell[0], oy + cell[1], oz + cell[2])
            lights.append((at, level, f"{NAME}:{why}"))
            _offer(c, at, level, f"{NAME}:{why}", CAGE_RANK)
    for cell in FILLS:
        at = (ox + cell[0], oy + cell[1], oz + cell[2])
        lights.append((at, FILL, f"{NAME}:fill"))
        _offer(c, at, FILL, f"{NAME}:fill", CAGE_RANK)
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
