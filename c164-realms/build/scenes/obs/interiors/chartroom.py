"""The chart room (plan ART-PLAN 8; card plan/packages/interiors/chartroom.md): the south wing of the
main floor, the room of V9. It is the time room of the north wing (interiors/timeroom, m2) mirrored
about the axis: the same panelling, floor, beams and lamps, another star.

The room is 12 wide (x 2..13), 19 long (z 7..25) and 7 high (feet at 7, the ceiling block on 14):
main/shell.ROOMS["chart room"]. The door is in the north wall on the room's long axis (x 7..8), and
V9 stands in it and looks south. On that axis, one behind the other:

  light table     the star: a long table of lit opal glass, four panes in a brass frame on a lamp
                  box and iron trestles, its north end three and a half blocks from the door. The
                  plates of the night lie on its first pane, a measuring bridge with its microscope
                  stands over the second, and at the far end the plate viewer stands up with the
                  newest plate, the comet, facing the door. From the door the glass is a lit lane
                  that runs to the viewer and to the books behind it.
  bookcase        the whole south wall, floor to ceiling, the library ladder on its rail.

and along the long walls, each thing at a window or on the blind stretch of the west wall (the
rotunda is behind it, z 7..13):

  east            the writing desk under the second window (bay 12), with the green lamp, the hand
                  calculator and the log; a small telescope on its tripod at the third; a bench
                  under a drop light at the fourth; the plate trunk by the bookcase
  west            on the blind stretch the blackboard under its lamp, at the door's end, and the
                  card cabinets with the moon map over them; the drafting table under a drop light
                  at the first window (bay 13); the celestial globe at the second
  north           the door in its case, its two leaves standing open into the room (_doorcase,
                  shell's: the pair of the time room's); the pair of great sky maps, one on each
                  side of it, a lamp over each

The room's envelope is the time room's: dark panels on every solid stretch of wall from the floor
to the ceiling (the piers, the blind stretch, the wall round the door; under a window the one
course below its sill), the floor relaid in dark boards, riveted beams on the pilaster rows with an
iron shoe at the head of each pier. The north-west corner cell holds one panel and two walls want
one: it is a cased riser. No block of the room stands in the first cell behind the glass of a
window (clear_cells()); the one that does is the last panel of the north wall, edge on to the glass
of east bay 11, which no look lights.

Light. The room is dark and is lit where somebody works, and by nothing else: what is to sink is
made dark, what is to be seen is light and then lit. The light table is the brightest thing in it:
its glass glows (emission), four sources in the row over the panes give the pool round it, and
four at its feet, where the vents of the lamp box open, lay that pool on the floor it stands on.
Every lamp is the shaded one of props/lamps (LAMPS) and hangs low over what it is for; its source
is not offered at its bulb but under its shade, at the height of what it lights. A window is not a
light of the room: the ones the light line lights (east 12 and 14, west 14: sky/lights' table) are
lined on the room side by materials/windows, with its deep lining, level with the panelling. The
green desk lamp is the room's one green; the desk and what stands on it under that lamp are shown
in its light (DESK_LIT, DESK_POOL), since a model takes the light of one cell and the lamp's rank
leaves that cell dim.
Every source is offered to the light line (sky/_lightkit); nothing is placed for good here.

What is whose. The room's own models (names "int_chart_..."): the light table here; its two
engines, the measuring bridge and the plate viewer, in _chartengine.py (m5); the bookcase wall in
_chartshelves.py (snow). Everything else comes from the props line and is placed through its place()
functions: lamps (props/lamps), furniture (props/furniture, a6), paper (props/paper, snow),
instruments (props/instruments, m1). A module that is not in the tree yet is left out, or stood in
for (the loose plates on the light table, a calculator, a board for the desk the green lamp stands
on); what was left out or stood in for is in the returned record.

Coordinates are the skeleton's: build_chartroom() dresses the room where it stands in the building,
the box test scene (build/scenes/obs_int_chartroom) stands a stand-in of the shell around it.
build() is what the master scene calls; it places nothing while MOVED_IN is off.
"""
import functools
import importlib
import math

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
from . import _chartengine
from . import _chartshelves
from . import _doorcase

try:
    from ..motion import _kit as MK
except ImportError:                     # the motion line is not in the tree: the room stands still
    MK = None

MOVED_IN = True         # the master scene dresses the room (A0, g2 #67123: a card's switch is turned on with its delivery)
NAME = "interiors/chartroom"
PREFIX = "int_chart_"
PX = 1 / 16.0

# ---- the room (cells): the clear inside the shell leaves (main/shell) ---------------------------
ROOM = shell.ROOMS["chart room"]
X0, Z0, X1, Z1 = ROOM["box"]        # 2, 7, 13, 25: clear, between the glass planes, the cross wall and the pavilion
FEET = ROOM["feet"]                 # 7
FLOOR_Y = FEET - 1                  # 6: the floor block
CEIL_Y = ROOM["ceiling"]            # 14: the ceiling block
TOP = CEIL_Y - 1                    # 13: the highest clear row
SILL = S.WINDOW[0]                  # 8: the first row of glass
_DOOR = next(d for d in shell.doors() if d["room"] == "chart room")
DOOR_X = (min(x for x, _ in _DOOR["cells"]), max(x for x, _ in _DOOR["cells"]))     # (7, 8): in the cross wall on z 6
DOOR_TOP = _DOOR["y"][1]            # 9: the last row of the doorway
PIER_Z = tuple(z for z in range(Z0, Z1 + 1) if MP.on_pilaster(z))                   # 10, 14, 18, 22
EAST_BAYS = tuple(b for b in range(1, S.N_BAYS + 1)
                  if set(MP.window_rows(b)) <= set(range(Z0, Z1 + 1)))                # 11..15
WEST_BAYS = tuple(b for b in EAST_BAYS
                  if all(abs(z - S.DOME_CENTRE[1]) > MP.WEST_BLIND_Z for z in MP.window_rows(b)))   # 13..15
BLIND_Z = (Z0, S.pilaster_z(min(WEST_BAYS) - 1) - 1)     # 7..13: the west wall with the rotunda behind it

# ---- the room (points) --------------------------------------------------------------------------
WEST, EAST = float(X0), float(X1 + 1)           # 2.0, 14.0: the inner faces of the long walls
NORTH, SOUTH = float(Z0), float(Z1 + 1)         # 7.0, 26.0: of the cross wall and the pavilion wall
AXIS_X = S.mid(*DOOR_X)                         # 8.0: the long axis of the room runs through the door
WAINSCOT_T = 3 * PX                             # a panel of the wainscot, off its wall
PANEL_W, PANEL_E, PANEL_N = WEST + WAINSCOT_T, EAST - WAINSCOT_T, NORTH + WAINSCOT_T    # the faces of the panelling:
#                                                 what hangs on a panelled wall or stands against it does so on these
RISER = (X0, Z0)                                # the north-west corner cell: the cased riser
CORNER = (X1, Z0)                               # the north-east corner cell: the north wall's panel, not the east wall's


def bay_z(bay):
    """The middle of a window bay along the room."""
    rows = MP.window_rows(bay)
    return S.mid(rows[0], rows[-1])


# ---- where the pieces stand ---------------------------------------------------------------------
TABLE_AT = (AXIS_X, float(FEET), S.mid(PIER_Z[1], PIER_Z[1]))    # (8, 7, 14.5): the middle of the light table's foot,
#                                                 on the axis, under the beam of the second pilaster row
DESK_BAY = 12                                   # the writing desk stands under this window of the east wall
SCOPE_BAY = 13                                  # the small telescope at this one
BENCH_BAY = 14                                  # the bench under this one
DRAFT_BAY = 13                                  # the drafting table under this window of the west wall
GLOBE_BAY = 14                                  # the celestial globe at this one
CABINET_PITCH = 15 * PX                         # the card cabinets of props/furniture are 15 wide and stand side by side
# The blind stretch, as the board's V9 sees it (cr4 #76387): that picture's right edge crosses the west wall at z 9.3.
# What is light and is to be read hangs whole inside it; what is dark may be cut by it.
BOARD_Z = Z0 + 2.0                              # 9.0: the middle of the blackboard, from the cased riser to z 10: the
#                                                 edge of V9 runs through it
BOARD_LAMP_Z = BOARD_Z - 0.3                    # its lamp, a hand towards the door from its middle: the shade is whole
#                                                 outside that picture, not a lit sliver on its edge
CABINET_Z = tuple(BOARD_Z + 2.5 + i * CABINET_PITCH for i in range(3))      # 11.5, 12.44, 13.38: the card cabinets, the
#                                                 moon map over the middle one, two blocks inside the picture
MAP_X = (DOOR_X[0] - 2.5, DOOR_X[1] + 3.5)      # 4.5 and 11.5: the middles of the two sky maps on the north wall
MAP_Y = FEET + 3.5                              # their middle above the floor: the head of the door is their foot line

# ---- light: what the room asks of the light line (level, rank); the lamps are props/lamps models
LAMPS = "b"                 # every lamp of the room is the shaded one (props/lamps' version B, the enamel cone): a shade
#                             keeps a lamp's glow to what is under it, and the opal globe of version A is itself the
#                             lightest thing in a dark room
CORD = lamps.PREFIX + "wire"            # the cord of a drop light: props/lamps' cable, stretched from the ceiling
# A source of 8 leaves what stands under its lamp at a fifth of its colour, one of 12 at half (the game's light
# map): at 8 a shade glowed over a desk that stayed black. A lamp somebody works under asks for the top of its
# rank; the walls ask for less, and the green lamp is of the third rank (sky/_lightkit.KIND_RANK).
ASK_TABLE = (12, 2)         # the four sources over the panes of the light table: the room's main light
ASK_FEET = (12, 2)          # the four at the table's feet (cr4 #76387: the glass shone and the floor beside it did not)
ASK_SHELF = (11, 2)         # the bracket lamps on the two outer piers of the bookcase
ASK_DROP = (12, 2)          # a drop light over a desk or a bench
ASK_DESK = (8, 3)           # the green desk lamp
DESK_LIT = (0, 10)          # (sky, block): the light the writing desk is shown in, under the green lamp, and
DESK_POOL = (0, 12)         # what stands on it: a model takes the light of the one cell it is held in, and a
#                             source of the third rank leaves that cell at 7 (cr4 #76387: the desk was one dark heap)
ASK_WALL = (10, 2)          # a bracket lamp over what hangs on a wall
OVER = 20 * PX              # a bracket's arm above the top of what it hangs over: the shade ends half a block over it
DESK_HANG = FEET + 3.25     # 10.25: where a desk's drop light ends and its lamp hangs; the shade ends at 9.2, over the eye
DRAFT_HANG = FEET + 3.75    # the same over the drafting table, whose board stands higher

# ---- materials ----------------------------------------------------------------------------------
WOOD = P.mat("dark_wood")
BRASS, BRASS_D, IRON, IRON_D = K.BRASS, K.BRASS_D, K.IRON, K.IRON_D
LABEL = K.flat("cream", 3)
LIT_GLASS = K.flat("opal", 3)                   # lit opal glass, a step under the ramp's white: the plates of
#                                                 props/paper are drawn a step under their pane, and on white they sank
LIT = dict(emit=15, shade=False)
VENT = K.flat("glow", 1)                        # the lamps seen through a vent slot
OP, IR, CR, BR = (P.RAMPS[k] for k in ("opal", "iron", "cream", "brass"))

# A glass negative with the light behind it, as props/paper draws the plates that lie on the table
# (snow #63583): the glass a step denser than the lit pane, its edge light on the two sides towards
# the light of the picture and dark on the other two; a star is black, the faintest are grey.
PLATE_SIDE = K.flat("opal", 0)
PLATE_COLOURS = {"c": OP[1], "t": OP[2], "d": OP[0], "1": IR[1], "2": IR[3], "3": IR[5], "4": CR[0]}


def _plate_picture(name, w, h, marks):
    """The face of a plate w by h: `marks` is {(x, y): tone}, y from the top."""
    rows = [["c"] * w for _ in range(h)]
    for x in range(w - 1):
        rows[0][x] = "t"
    for y in range(h - 1):
        rows[y][0] = "t"
    for x in range(w):
        rows[h - 1][x] = "d"
    for y in range(h):
        rows[y][w - 1] = "d"
    for (x, y), tone in marks.items():
        rows[y][x] = tone
    return Sprite(name, ["".join(row) for row in rows], PLATE_COLOURS)


def _comet():
    """The plate on the viewer, 18 by 18: the comet, its head low on the left, the tail fanning out
    up and away from it and thinning as it goes, a handful of field stars. No star is a cross."""
    marks = {}
    for x, y in ((5, 10), (6, 10), (4, 11), (7, 11), (4, 12), (7, 12), (5, 13), (6, 13)):
        marks[(x, y)] = "2"                                     # the coma
    for x, y in ((5, 11), (6, 11), (5, 12), (6, 12)):
        marks[(x, y)] = "1"                                     # the head
    for i in range(9):                                          # the tail: its middle, and a side on each hand
        marks[(7 + i, 10 - i)] = "2" if i < 2 else "3" if i < 5 else "4"
        if i < 8:
            marks[(8 + i, 10 - i)] = "3" if i < 3 else "4"
        if i < 7:
            marks[(7 + i, 9 - i)] = "3" if i < 3 else "4"
    marks.update({(3, 3): "1", (13, 13): "2", (2, 8): "2", (15, 9): "3", (9, 14): "3", (6, 5): "3",
                  (11, 11): "3", (3, 15): "3", (14, 15): "4", (8, 3): "4", (2, 13): "4"})
    return _plate_picture("chart_plate_comet", 18, 18, marks)


COMET = _comet()
# the plates of the stand-in for props/paper: the comet small, a star field, a spectrum
PLATE_SMALL = _plate_picture("chart_plate_small", 8, 8, {(2, 4): "1", (3, 4): "1", (2, 5): "1", (3, 5): "1", (4, 3): "2",
                                                         (5, 2): "3", (6, 1): "4", (1, 2): "2", (5, 5): "2", (6, 6): "3"})
PLATE_FIELD = _plate_picture("chart_plate_field", 8, 8, {(4, 2): "1", (5, 2): "1", (4, 3): "1", (5, 3): "1", (2, 5): "1",
                                                         (1, 1): "2", (6, 4): "2", (6, 1): "3", (2, 3): "3", (4, 6): "3"})
PLATE_STRIP = _plate_picture("chart_plate_strip", 8, 4, {(1, 1): "3", (1, 2): "3", (2, 1): "2", (2, 2): "2", (3, 1): "1",
                                                         (3, 2): "1", (5, 1): "1", (5, 2): "1", (6, 1): "2", (6, 2): "2"})
# the maker's plate on the north end of the light table: a line of engraving on brass
MAKER = Sprite("chart_maker", ["ffffffffff", "fkkfkkkfkf", "eeeeeeeeee"], {"f": BR[3], "k": BR[0], "e": BR[1]})


# ---- the room's own models: the light table ------------------------------------------------------
# Long along the room's axis: four square panes of opal glass in a brass frame, on a lamp box of
# dark wood that stands on five iron trestles. It is drawn in the table's own frame, texels from the
# middle of its foot: x to the east, z to the south (the north end is the one the door sees).
TABLE_L, TABLE_W = 114.0, 30.0      # along the room, across it
PANES = 4
PANE = 26.0                         # a pane, square
BAR = 2.0                           # the frame round the panes and the bars between them
BOX_Y = (9.0, 14.0)                 # the lamp box: its underside, and the rebate the glass lies in
FRAME_TOP = 15.0                    # the top of the brass frame above the floor
GLASS = 14.75                       # the top of the glass: a quarter of a texel under the frame
LIFT = 2.0                          # what stands on the table is held this far above its foot, the table itself this far
#                                     above its frame: in the row over the glass, where the table's sources are
HELD = (0.0, FRAME_TOP + LIFT, 0.0)     # where every length of the table is held: one cell lights the whole table
BRIDGE_Z = -14.0                    # the measuring bridge (_chartengine.bridge): over the middle of the second pane
VIEWER_Z = 38.0                     # the foot of the plate viewer's face (_chartengine.viewer), on the fourth pane
# the microscope of the bridge looks down at this point of the glass, towards the west edge, where the observer's stool
# stands; the plate that is being measured lies under it, as far east as leaves it whole on the glass
NOSE = (_chartengine.NOSE[0], BRIDGE_Z + _chartengine.NOSE[1])
# the loose plates on the glass: (kind of props/paper, (x, z) of its middle, degrees it is turned)
PLATES = (
    ("photo_plate", (-6.0, -47.0), 8.0), ("photo_plate_b", (5.0, -40.0), -14.0), ("photo_plate_c", (-5.0, -34.0), 4.0),
    ("photo_plate_b", (max(NOSE[0], -8.5), NOSE[1]), 0.0),              # under the microscope
    ("photo_plate", (6.0, 9.0), -6.0), ("photo_plate_c", (-6.0, 17.0), 10.0),
)
STAND_IN = 4                        # how many of them the room's own stand-in shows while props/paper is not in the tree
TABLE_LIGHTS = tuple((x, SILL, z) for z in (12, 16) for x in (7, 8))     # the cells of the table's four sources: the row
#                                     over the glass, two on each side of the middle, one in each of the two columns the
#                                     table stands in, so that the pool is the same on both hands and towards both ends
TABLE_FEET = tuple((x, FEET, z) for z in (12, 16) for x in (6, 9))      # and of the four at its feet: on the floor beside
#                                     it, abreast of those, where the vents of the lamp box open
DOOR_FACE = WAINSCOT_T / PX         # 3: how far the room's lining stands off the door's wall, in sixteenths
DOOR_SWING = 100.0                  # how far the two leaves stand open, as the time room's

# ---- what moves (motion/_kit; A0, g2 #85347: the measuring engine's carriage goes to and fro) ------
# The engine measures by itself: the screw turns, the carriage with the microscope creeps along the
# bed to the far end of its travel and comes back. Carriage and screw go through the same poses on
# the same ticks, the carriage a quarter of the cycle ahead, so that the carriage moves exactly as
# fast as the screw's turning draws it (a turn to 4 texels) and both stand for a moment where the
# way turns round. Twelve seconds there and back: at its quickest two texels a second.
MEASURE = 240                       # ticks, there and back
MEASURE_KEYS = 24                   # poses in that: one every half second
CLOCK_FOOT = _chartshelves.CLOCK_AT[1] - 1.0    # the regulator clock is two blocks tall and hangs in the middle of
#                                     the board the bookcase keeps for it, on the room's axis


def _measure_moves():
    """The carriage's way as motion's slide() takes it: (tick it sets off, blocks from where it
    was placed, ticks it takes), from pose to pose of the screw's swing."""
    half = _chartengine.TRAVEL / 2.0 * PX
    ticks = [k * MEASURE // MEASURE_KEYS for k in range(MEASURE_KEYS + 1)]
    ends = [half * (1.0 - math.cos(2.0 * math.pi * k / MEASURE_KEYS)) for k in range(1, MEASURE_KEYS)] + [0.0]
    return [(ticks[k], ends[k], ticks[k + 1] - ticks[k]) for k in range(MEASURE_KEYS)]


def _table_cells():
    """The cells the table fills: the two columns it stands in, every row wholly within its length."""
    z0, z1 = TABLE_AT[2] - TABLE_L / 2.0 * PX, TABLE_AT[2] + TABLE_L / 2.0 * PX      # 10.94 .. 18.06
    xs = range(int(TABLE_AT[0] - TABLE_W / 2.0 * PX), int(TABLE_AT[0] + TABLE_W / 2.0 * PX) + 1)     # 7, 8
    return tuple((x, FEET, z) for x in xs for z in range(-int(-z0 // 1), int(z1 // 1)))


TABLE_CELLS = _table_cells()        # (7|8, 7, 11..17): 14 cells


def pane_z(k):
    """Pane k of the table, counted from the north end: where it begins and ends."""
    a = -TABLE_L / 2.0 + BAR + k * (PANE + BAR)
    return a, a + PANE


def part_z(k):
    """The length of the table that carries pane k: the pane and the bar south of it, the north end
    of the frame as well for the first."""
    a, b = pane_z(k)
    return (a - BAR if k == 0 else a), b + BAR


def part_name(k):
    return f"{PREFIX}table_{k}"


def _trestle(m, z, braced=False):
    """One trestle of the table, across it at z: two iron legs on brass feet and a rail between
    them; the two at the ends have a knee brace under the lamp box."""
    for s in (-1.0, 1.0):
        x = s * (TABLE_W / 2.0 - 2.0)
        m.box((x - 1, 1, z - 1), (x + 1, BOX_Y[0], z + 1), IRON, grain="y")
        m.box((x - 1.5, 0, z - 1.5), (x + 1.5, 1, z + 1.5), BRASS_D)
        if braced:
            m.beam((x - s, 5.0, z), (x - s * 5.0, BOX_Y[0], z), 1.0, 1.0, IRON_D)
    m.box((-12, 3, z - 0.5), (12, 4, z + 0.5), IRON_D, grain="x")


def _table(k):
    """One length of the light table: the one that carries pane k. All of them are held at the same
    point over the middle of the table (HELD), so that one cell lights them all."""
    m = M.Model(part_name(k), anchor=HELD)
    hw = TABLE_W / 2.0
    a, b = part_z(k)
    p0, p1 = pane_z(k)
    first, last = k == 0, k == PANES - 1
    # the lamp box and the long rail between the trestles
    m.box((-hw, BOX_Y[0], a), (hw, BOX_Y[1], b), WOOD, grain="z", skip="u" + ("" if first else "n") + ("" if last else "s"))
    m.box((-0.5, 3, a), (0.5, 4, b), IRON_D, grain="z", skip=("" if first else "n") + ("" if last else "s"))
    # the brass frame: the two long sides, the bar south of the pane, the north end of the frame
    for x in (-hw, hw - BAR):
        m.box((x, BOX_Y[1], a), (x + BAR, FRAME_TOP, b), BRASS_D, grain="z", skip="d" + ("" if first else "n") + ("" if last else "s"))
    m.box((-hw + BAR, BOX_Y[1], p1), (hw - BAR, FRAME_TOP, p1 + BAR), BRASS_D, grain="x", skip="dew")
    if first:
        m.box((-hw + BAR, BOX_Y[1], a), (hw - BAR, FRAME_TOP, a + BAR), BRASS_D, grain="x", skip="dew")
    # the glass
    m.box((-hw + BAR, BOX_Y[1], p0), (hw - BAR, GLASS, p1), LIT_GLASS, skip="dnsew", **LIT)
    # the lamps through the vent slots of the long sides
    middle = (p0 + p1) / 2.0
    for z in (middle - 8.0, middle + 4.0):
        m.box((hw, 11, z), (hw + 0.25, 12, z + 4.0), VENT, skip="w", **LIT)
        m.box((-hw - 0.25, 11, z), (-hw, 12, z + 4.0), VENT, skip="e", **LIT)
    # the trestles: one under the bar south of the pane, one under the north end
    _trestle(m, p1 + BAR / 2.0, braced=last)
    if first:
        _trestle(m, a + BAR / 2.0, braced=True)
        # the north end, which the door sees: the maker's plate, a louvre, the switch, the conduit
        # that comes up out of the floor beside a leg
        m.box((-5, 10.5, a - 0.5), (5, 13.5, a), BRASS_D, skip="s", faces={"n": MAKER})
        for y in (10.0, 12.0):
            m.box((-12.5, y, a - 0.25), (-8.5, y + 1, a), VENT, skip="s", **LIT)
        m.tube("z", (10.5, 11.5), a - 1.0, a, 1.5, BRASS_D)
        m.tube("z", (10.5, 11.5), a - 1.75, a - 1.0, 0.5, BRASS_D, sides=4)
        m.box((9.0, 11.0, a - 2.5), (12.0, 12.0, a - 1.75), BRASS, rot=("z", 35.0, (10.5, 11.5, a - 2.0)))
        m.tube("y", (10.0, a + 1.0), 0.5, BOX_Y[0], 0.75, IRON_D)
        m.tube("y", (10.0, a + 1.0), 0.0, 0.5, 1.75, IRON)
    if last:
        for x in (-12.5, 8.5):
            for y in (10.0, 12.0):
                m.box((x, y, b), (x + 4.0, y + 1, b + 0.25), VENT, skip="n", **LIT)
    return m


def _plates():
    """The loose plates on the first two panes: the stand-in for the plates of props/paper while
    that module is not in the tree. Drawn in the table's frame; anchor: on the glass, in the middle
    of the plates it shows."""
    shown = PLATES[:STAND_IN]
    zs = [z for _, (_, z), _ in shown]
    m = M.Model(PREFIX + "plates", anchor=(0.0, 0.0, (min(zs) + max(zs)) / 2.0))
    pictures = {"photo_plate": PLATE_SMALL, "photo_plate_b": PLATE_FIELD, "photo_plate_c": PLATE_STRIP}
    for kind, (x, z), turn in shown:
        d = 2.0 if kind == "photo_plate_c" else 4.0
        m.box((x - 4, 0, z - d), (x + 4, 0.5, z + d), PLATE_SIDE, skip="d",
              rot=("y", turn, (x, 0.0, z)), faces={"u": pictures[kind]}, **LIT)
    return m


def _calculator():
    """The hand calculator: a pinwheel machine, black with brass setting levers, a carriage with
    the result windows in front and the crank on its right. The stand-in for the calc_machine of
    props/instruments while that is not in the tree. Anchor: the middle of its foot; the front (+z)
    is the side one sits at."""
    m = M.Model(PREFIX + "calculator")
    m.box((-5, 0, -3), (5, 1, 3), IRON_D, grain="x")
    m.box((-4.5, 1, -2.5), (4.5, 3, 1.5), IRON, grain="x")
    m.tube("x", (3.5, -0.5), -4.0, 4.0, 2.25, IRON, sides=8)                    # the drum of pinwheels
    for i in range(6):
        x = -3.25 + 1.3 * i
        m.box((x - 0.25, 5.25, -1.0 + 0.25 * (i % 3)), (x + 0.25, 6.25, -0.5 + 0.25 * (i % 3)), BRASS)
    m.box((-5.5, 1, 1.5), (4.0, 2.5, 3.5), IRON_D, grain="x")                   # the carriage
    m.box((-4.5, 2.5, 2.0), (3.0, 2.75, 3.0), LABEL, skip="d")                  # the result windows
    m.box((4.5, 2.5, -1.0), (5.25, 6.5, 0.0), BRASS_D, grain="y")               # the crank
    m.box((5.25, 5.5, -1.0), (7.25, 6.5, 0.0), WOOD, grain="x")
    return m


@functools.lru_cache(maxsize=None)
def _models():
    out = dict(_chartshelves.models())
    out.update(_doorcase.models(PREFIX, _DOOR, DOOR_FACE, DOOR_SWING))
    engines = _chartengine.bridge_models() + [_chartengine.viewer(COMET)]
    for m in [_table(k) for k in range(PANES)] + engines + [_plates(), _calculator()]:
        out[m.name] = m
    return out


def models():
    return dict(_models())


# ---- the other lines' pieces ----------------------------------------------------------------------
def _peer(name):
    """A module of the props line, or None while it is not in the tree."""
    full = f"{__package__.rsplit('.', 1)[0]}.props.{name}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as e:
        if e.name != full:
            raise               # the module is there and fails to import something: say so
        return None


def clear_cells():
    """The cells no block of the room stands in: the first cell behind the glass of every window of
    the long walls, [(x, y, z)]. The lining of a lit one lies on its glass there."""
    out = []
    for bays, x in ((EAST_BAYS, X1), (WEST_BAYS, X0)):
        for bay in bays:
            out += [(x, y, z) for z in MP.window_rows(bay) for y in range(S.WINDOW[0], S.WINDOW[1] + 1)]
    return out


def panel(side):
    """A panel of the wainscot standing on that side of its cell."""
    back = {"north": "south", "south": "north", "west": "east", "east": "west"}[side]
    return st(B.WAINSCOT, facing=back, half="bottom", open="true")      # it stands on the side it turns its back to


# ---- building -----------------------------------------------------------------------------------
def build_chartroom(c, origin=(0, 0, 0), roles=B):
    """Dress the room standing at `origin`. Returns dict(entities=<display entities placed>,
    lights=[(cell, level, why)] offered to the light line, missing=[what was left out or stood in
    for because its module is not in the tree])."""
    ox, oy, oz = origin
    own = _models()
    furniture, paper, instruments = _peer("furniture"), _peer("paper"), _peer("instruments")
    lights, missing = [], []
    n = 0

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    def free(x, y, z):
        return not c.has(ox + x, oy + y, oz + z)

    def offer(at, ask, why):
        """One light source, offered in the cell `at` (the room's own cells)."""
        level, rank = ask
        cell = (ox + at[0], oy + at[1], oz + at[2])
        lights.append((cell, level, f"{NAME}:{why}"))
        _offer(c, cell, level, f"{NAME}:{why}", rank)

    def lamp(kind, pos, ask, why, at, **how):
        """A lamp of props/lamps. Its light is offered in the cell `at`: under its shade, not at
        its bulb."""
        offer(at, ask, why)
        return lamps.place(c, kind, pos, origin=origin, light=False, version=LAMPS, **how)

    def drop(x, z, hang, ask, why, at):
        """A drop light: a cord from the ceiling down to `hang`, and a pendant on its end."""
        a, b = (ox + x, oy + CEIL_Y - K.NUDGE, oz + z), (ox + x, oy + hang, oz + z)
        c.add_entity(*a, M.between(lamps.models()[CORD], a, b))
        return 1 + lamp("pendant", (x, hang, z), ask, why, at)

    def has(module, kind):
        return module is not None and kind in getattr(module, "SPEC", (kind,))

    def piece(module, label, kind, pos, **how):
        if not has(module, kind):
            missing.append(f"{label}:{kind}")
            return 0
        return module.place(c, kind, pos, origin=origin, **how)

    # ---- the floor: dark boards over the pale ones of the shell (in those the floor is the lightest
    # large thing of the room, lit or not: the time room's review, cr3-P4)
    # The cell under the cased riser is not relaid: the plate lift of the vault below comes up through
    # it into the casing (interiors/platevault, c358), and the floor block there is that room's to open.
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            if (x, z) != RISER:
                put(x, FLOOR_Y, z, roles.DARK_WOOD.block)

    # ---- beams on the pilaster rows, each end in a shoe at the head of its pier
    for z in PIER_Z:
        for x in range(X0 + 1, X1):
            put(x, TOP, z, st(roles.IRON_RIVETED.slab, type="top"))
        put(X0, TOP, z, st(roles.IRON_RIVETED.stairs, facing="west", half="top"))
        put(X1, TOP, z, st(roles.IRON_RIVETED.stairs, facing="east", half="top"))

    # ---- the bookcase wall (snow's, _chartshelves), the ladder on its rail, a bracket lamp on each of
    # its outer piers, where the pier's face is bare
    n += _chartshelves.place(c, origin)
    front = _chartshelves.FRONT_Z
    if furniture is not None:
        n += furniture.rail(c, (X1 + 0.5, FEET, front), X1 - X0 + 1, facing="north", origin=origin)
    n += piece(furniture, "furniture", "library_ladder", (AXIS_X + 2.25, FEET, front), facing="north")
    for x in (_chartshelves.PIER_X[0], _chartshelves.PIER_X[-1]):
        n += lamp("bracket", (x, _chartshelves.LAMP_Y[0] + 11 * PX, _chartshelves.PIER_FACE_Z), ASK_SHELF,
                  "bracket lamp on a pier of the bookcase", (int(x), FEET + 3, Z1 - 1), facing="north")
    # the room's clock on the board the bookcase keeps for it, on the axis: the regulator of
    # props/instruments, and its pendulum swings as that module says it does (the motion line's
    # sound ticks at every such pendulum on the canvas)
    if has(instruments, "regulator_clock"):
        n += instruments.place(c, "regulator_clock", (_chartshelves.CLOCK_AT[0], CLOCK_FOOT, _chartshelves.CLOCK_AT[2]),
                               facing="north", origin=origin)
        beat = instruments.PENDULUM
        if MK is not None and not any(tag.startswith("m.") for tag in c.entities[-1][3].get("Tags", ())):
            MK.swing(c, beat["axis"], beat["swing"], beat["period_ticks"])
    else:
        missing.append("instruments:regulator_clock")

    # ---- the light table: its four lengths, the bridge, the viewer, the plates; the sources of its glass
    held = tuple(TABLE_AT[i] + HELD[i] * PX for i in range(3))
    for k in range(PANES):
        n += K.put(c, own[part_name(k)], held, origin=origin)
    # The table is a model and has no collision: a barrier in every cell that lies wholly within its
    # length, one high, in the two columns it stands in, so that nobody walks through it (A0's second
    # use of the barrier, INTERFACE.md: inside a solid model that is seen, never beyond its outline)
    for x, y, z in TABLE_CELLS:
        put(x, y, z, roles.BARRIER)

    def on_table(x, z, up=GLASS):
        """A point over the table: texels from the middle of its foot."""
        return (TABLE_AT[0] + x * PX, TABLE_AT[1] + up * PX, TABLE_AT[2] + z * PX)

    # the measuring engine: what stands still, the screw on its own axis, the carriage; the last two move
    n += K.put(c, own[PREFIX + "bridge"], on_table(0.0, BRIDGE_Z, FRAME_TOP + LIFT), origin=origin)
    n += K.put(c, own[PREFIX + "bridge_screw"],
               on_table(0.0, BRIDGE_Z + _chartengine.SCREW[1], FRAME_TOP + _chartengine.SCREW[0]), origin=origin)
    if MK is not None:
        MK.swing(c, "x", 180.0 * _chartengine.SCREW_TURNS, MEASURE, keys=MEASURE_KEYS, phase=MEASURE // 4)
    n += K.put(c, own[PREFIX + "bridge_carriage"], on_table(0.0, BRIDGE_Z, FRAME_TOP + LIFT), origin=origin)
    if MK is not None:
        MK.slide(c, "x", _measure_moves(), MEASURE)
    n += K.put(c, own[PREFIX + "viewer"], on_table(0.0, VIEWER_Z, GLASS + LIFT), facing="north", origin=origin)
    if all(has(paper, kind) for kind, _, _ in PLATES):
        for kind, (x, z), turn in PLATES:
            n += paper.place(c, kind, on_table(x, z), yaw=turn, origin=origin)
    else:
        missing.append("paper:photo_plate")
        stand_in = own[PREFIX + "plates"]
        n += K.put(c, stand_in, on_table(0.0, stand_in.anchor[2]), origin=origin)
    for i, at in enumerate(TABLE_LIGHTS):
        offer(at, ASK_TABLE, f"the light table {i + 1}")
    for i, at in enumerate(TABLE_FEET):
        offer(at, ASK_FEET, f"the light table's foot {i + 1}")
    n += piece(furniture, "furniture", "stool", (TABLE_AT[0] - TABLE_W / 2.0 * PX - 0.55, FEET, TABLE_AT[2] + BRIDGE_Z * PX),
               facing="east")

    # ---- the west wall. On the blind stretch: at the door's end the blackboard, hung where one writes
    # on it (its middle 1.75 above the floor), a lamp over it; south of it three card cabinets side by
    # side, a small globe on the first, the moon map over the middle one
    cabinet_x = PANEL_W + 6.5 * PX
    cabinet_top = FEET + (furniture.TOP["card_cabinet"] if furniture is not None else 1.875)
    for z in CABINET_Z:
        n += piece(furniture, "furniture", "card_cabinet", (cabinet_x, FEET, z), facing="east")
    if furniture is not None:
        n += piece(instruments, "instruments", "globe", (cabinet_x, cabinet_top, CABINET_Z[0]), facing="east")
    n += piece(paper, "paper", "moon_map", (PANEL_W, cabinet_top + 1.0, CABINET_Z[1]), facing="east")
    n += piece(paper, "paper", "blackboard", (PANEL_W, FEET + 1.75, BOARD_Z), facing="east")
    n += lamp("bracket", (PANEL_W, FEET + 2.5 + OVER, BOARD_LAMP_Z), ASK_WALL, "blackboard",
              (X0 + 1, FEET + 1, int(BOARD_Z)), facing="east")
    # at its first window the drafting table, a drop light over the drafter's left hand; at the next
    # the celestial globe
    z = bay_z(DRAFT_BAY)
    n += piece(furniture, "furniture", "drafting_table", (PANEL_W + 8 * PX, FEET, z), facing="east")
    n += piece(furniture, "furniture", "stool", (PANEL_W + 8 * PX + 1.1, FEET, z), facing="west")
    n += drop(PANEL_W + 0.75, z + 0.5, DRAFT_HANG, ASK_DROP, "drafting table", (X0 + 1, FEET, int(z)))
    n += piece(instruments, "instruments", "celestial_globe", (WEST + 1.6, FEET, bay_z(GLOBE_BAY)), facing="east")

    # ---- the north wall: the door case and its two open leaves, which stand over no cell one walks in
    # (_doorcase.swept()); the pair of great sky maps, one on each side of the door, a lamp over each
    n += _doorcase.place(c, PREFIX, _DOOR, DOOR_FACE, DOOR_SWING, origin)
    for x, kind in zip(MAP_X, ("sky_map", "sky_map_b")):
        n += piece(paper, "paper", kind, (x, MAP_Y, PANEL_N), facing="south")
        n += lamp("bracket", (x, MAP_Y + 1.0 + OVER, PANEL_N), ASK_WALL, f"{kind}", (int(x), FEET + 3, Z0 + 1), facing="south")
    n += piece(furniture, "furniture", "coat_stand", (EAST - 1.1, FEET, NORTH + 0.9))

    # ---- the east wall. Under its second window the writing desk (props/furniture's is 30 by 14, its
    # front the side one sits at; at its back an upstand between two stationery drawers): the
    # calculator in the middle against the upstand, before the sitter; the green lamp at his right, at
    # the far end as the door sees the desk, before the drawer there and not in it, its long hood
    # square to the desk so that it lights along it; the closed log at his left. The board's V9 looks
    # along the desk from the door's end, so the low thing lies nearest to it and the tall one stands
    # last, the hood broadside. The 30 of the desk are full: the log 6, the calculator 13 and the
    # sweep of its crank 2.5, the hood's half 3.5 and the foot's half 3, a hand between them. The desk
    # and what stands on it are shown in the lamp's light (DESK_LIT, DESK_POOL)
    desk = (PANEL_E - 7 * PX, float(FEET), bay_z(DESK_BAY))
    desk_yaw = K.FACING["west"]
    if furniture is None:
        desk_top = 1.0
        for z in MP.window_rows(DESK_BAY):
            put(X1, FEET, z, st(roles.DARK_WOOD.slab, type="top"))      # a board stands in for the desk
    else:
        desk_top = furniture.TOP["writing_desk"]

    def on_desk(x, z):
        """A point on the desk top: texels from the desk's middle, in the desk's own frame."""
        dx, _, dz = K.turn(desk_yaw, (x * PX, 0.0, z * PX))
        return (desk[0] + dx, desk[1] + desk_top, desk[2] + dz)

    n += piece(furniture, "furniture", "writing_desk", desk, facing="west", brightness=DESK_LIT)
    n += piece(furniture, "furniture", "swivel_chair", (desk[0] - 1.0, FEET, desk[2] - 0.1), facing="east")
    n += lamp("desk_green", on_desk(12.0, 0.5), ASK_DESK, "the green desk lamp", (X1 - 1, FEET, int(desk[2])),
              yaw=desk_yaw - 90.0, brightness=DESK_POOL)
    if has(instruments, "calc_machine"):
        n += instruments.place(c, "calc_machine", on_desk(-1.5, -0.75), facing="west", origin=origin,
                               brightness=DESK_POOL)
    else:
        missing.append("instruments:calc_machine")
        n += K.put(c, own[PREFIX + "calculator"], on_desk(-1.5, -0.75), yaw=desk_yaw, origin=origin,
                   brightness=DESK_POOL)
    n += piece(paper, "paper", "logbook_shut", on_desk(-12.0, 3.0), yaw=desk_yaw, brightness=DESK_POOL)
    # at the third window the small telescope; under the fourth a bench and a drop light to read by;
    # by the bookcase the trunk the plates come down from the dome in
    n += piece(instruments, "instruments", "tripod_scope_comet", (EAST - 1.7, FEET, bay_z(SCOPE_BAY)), facing="east")
    z = bay_z(BENCH_BAY)
    n += piece(furniture, "furniture", "bench", (PANEL_E - 7.25 * PX, FEET, z), facing="west")
    n += drop(PANEL_E - 0.75, z - 0.5, DESK_HANG, ASK_DROP, "bench", (X1 - 1, FEET, int(z)))
    n += piece(furniture, "furniture", "trunk", (EAST - 1.0, FEET, Z1 - 1.4), facing="west")

    # ---- the panelling: every solid stretch of wall where no block of the room stands, from the floor
    # to the ceiling; before a window only the course under its sill. The bookcase stands before
    # the south wall
    clear = set(clear_cells())
    for y in range(FEET, TOP + 1):
        put(RISER[0], y, RISER[1], roles.DARK_WOOD.block)
        for z in range(Z0, Z1 + 1):
            for x, side in ((X1, "east"), (X0, "west")):
                if (x, z) != CORNER and (x, y, z) not in clear and free(x, y, z):
                    put(x, y, z, panel(side))
        for x in range(X0 + 1, X1 + 1):
            if not (DOOR_X[0] <= x <= DOOR_X[1] and y <= DOOR_TOP) and free(x, y, Z0):
                put(x, y, Z0, panel("north"))

    return {"entities": n, "lights": lights, "missing": missing}


def _offer(canvas, cell, level, why, rank):
    """Hand one light source to the light line; while it is not in the tree, put the source down,
    never over a block that is there."""
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
    return build_chartroom(canvas, origin)["entities"]
