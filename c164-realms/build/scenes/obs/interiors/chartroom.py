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
  west            the card cabinets with the moon map over them, and the blackboard under its lamp,
                  on the blind stretch; the drafting table under a drop light at the first window
                  (bay 13); the celestial globe at the second
  north           the pair of great sky maps, one on each side of the door, a lamp over each

The room's envelope is the time room's: dark panels on every solid stretch of wall from the floor
to the ceiling (the piers, the blind stretch, the wall round the door; under a window the one
course below its sill), the floor relaid in dark boards, riveted beams on the pilaster rows with an
iron shoe at the head of each pier. The north-west corner cell holds one panel and two walls want
one: it is a cased riser. No block of the room stands in the first cell behind the glass of a
window (clear_cells()); the one that does is the last panel of the north wall, edge on to the glass
of east bay 11, which no look lights.

Light. The room is dark and is lit where somebody works, and by nothing else: what is to sink is
made dark, what is to be seen is light and then lit. The light table is the brightest thing in it:
its glass glows (emission), and four sources in the row over the panes give the pool round it.
Every lamp is the shaded one of props/lamps (LAMPS) and hangs low over what it is for; its source
is not offered at its bulb but under its shade, at the height of what it lights. A window is not a
light of the room: the ones the light line lights (east 12 and 14, west 13 and 15 under the blue
look) are lined on the room side by materials/windows, and each has a lamp of the room within two
cells. The green desk lamp is the room's one green. Every source is offered to the light line
(sky/_lightkit); nothing is placed for good here.

What is whose. The room's own models (names "int_chart_..."): the light table, its bridge and its
viewer, the bookcases. Everything else comes from the props line and is placed through its place()
functions: lamps (props/lamps), furniture (props/furniture, a6), paper (props/paper, snow),
instruments (props/instruments, m1). A module that is not in the tree yet is left out, or stood in
for (the loose plates on the light table, a calculator, a board for the desk the green lamp stands
on); what was left out or stood in for is in the returned record.

Coordinates are the skeleton's: build_chartroom() dresses the room where it stands in the building,
the box test scene (build/scenes/obs_int_chartroom) stands a stand-in of the shell around it.
build() is what the master scene calls; it places nothing until MOVED_IN is set.
"""
import functools
import importlib
import random

import numpy as np

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
from . import _chartshelves

MOVED_IN = False        # the master scene dresses the room once it is past review
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
CABINET_Z = tuple(Z0 + 1.5 + i * CABINET_PITCH for i in range(3))       # 8.5, 9.44, 10.38: on the blind stretch
BOARD_Z = BLIND_Z[1] - 0.2                      # 12.8: the middle of the blackboard, whole inside the picture of V9
MAP_X = (DOOR_X[0] - 2.5, DOOR_X[1] + 3.5)      # 4.5 and 11.5: the middles of the two sky maps on the north wall
MAP_Y = FEET + 3.5                              # their middle above the floor: the head of the door is their foot line

# ---- light: what the room asks of the light line (level, rank); the lamps are props/lamps models
LAMPS = "b"                 # every lamp of the room is the shaded one (props/lamps' version B, the enamel cone): a shade
#                             keeps a lamp's glow to what is under it, and the opal globe of version A is itself the
#                             lightest thing in a dark room
CORD = lamps.PREFIX + "wire"            # the cord of a drop light: props/lamps' cable, stretched from the ceiling
ASK_TABLE = (10, 2)         # the four sources over the panes of the light table: the room's main light
ASK_SHELF = (9, 2)          # the drop lights before the bookcase
ASK_DESK = (8, 3)           # a drop light over a desk, and the green desk lamp
ASK_WALL = (8, 3)           # a bracket lamp over what hangs on a wall
OVER = 20 * PX              # a bracket's arm above the top of what it hangs over: the shade ends half a block over it
DESK_HANG = FEET + 3.25     # 10.25: where a desk's drop light ends and its lamp hangs; the shade ends at 9.2, over the eye
DRAFT_HANG = FEET + 3.75    # the same over the drafting table, whose board stands higher
SHELF_HANG = FEET + 5.0     # and before the bookcase

# ---- materials ----------------------------------------------------------------------------------
WOOD = P.mat("dark_wood")
WOOD_L = P.mat("dark_wood", base=3)
WOOD_D = P.mat("dark_wood", base=1)
SHADOW = K.flat("dark_wood", 0)                 # the inside of a bookcase
BRASS, BRASS_D, IRON, IRON_D = K.BRASS, K.BRASS_D, K.IRON, K.IRON_D
CARD = P.mat("cream", base=1, bevel=1)          # pasteboard boxes
LABEL = K.flat("cream", 3)
LIT_GLASS = P.mat("opal")                       # lit opal glass: brighter towards its middle
LIT = dict(emit=15, shade=False)
VENT = K.flat("glow", 1)                        # the lamps seen through a vent slot
OP, IR, CR, BR = (P.RAMPS[k] for k in ("opal", "iron", "cream", "brass"))

ROLL_END = Sprite("chart_roll_end", ["aba", "bcb", "aba"],
                  {"a": P.RAMPS["cream"][1], "b": P.RAMPS["cream"][2], "c": P.RAMPS["dark_wood"][0]})

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


class _Scale:
    """The divided scale on the beam of the measuring bridge, seen from the side: a division on
    every other texel, every fifth of them a long one. It stands in for a material on one face
    (artkit.models asks a material only for its name and paint())."""

    name = "chart_scale"

    def paint(self, w, h, grain="u", seed=0):
        out = np.empty((h, w, 4), dtype=np.uint8)
        out[..., :3] = P.colour("brass", 1)
        out[..., 3] = 255
        out[0, :, :3] = P.colour("brass", 2)
        for x in range(1, w - 1, 2):
            long = x % 10 == 1
            out[h - 1, x, :3] = P.colour("brass", 4)
            if long:
                out[:, x, :3] = P.colour("brass", 4)
        return out


SCALE = _Scale()


class _Spines:
    """The picture of a row of books seen from the front: spines of uneven width and height in the
    quiet colours of the palette, the dark of the case behind them. It stands in for a material on
    the front of one box."""

    # (ramp, steps to choose from); a ramp named twice is chosen twice as often
    TONES = (("enamel", (0, 1, 2)), ("enamel", (1, 2)), ("old_copper", (0, 1, 2)), ("old_copper", (1, 2)),
             ("dark_wood", (3, 4)), ("cream", (0, 1)), ("iron", (3, 4)))

    def __init__(self, name, full=0.92):
        self.name = name
        self.full = full            # the share of the row that holds a book

    def paint(self, w, h, grain="u", seed=0):
        rnd = random.Random(f"{self.name}:{w}:{h}:{seed}")
        out = np.empty((h, w, 4), dtype=np.uint8)
        out[..., :3] = P.colour("dark_wood", 0)
        out[..., 3] = 255
        x = 0
        while x < w:
            width = min(rnd.choice((1, 2, 2, 2, 3)), w - x)
            if rnd.random() > self.full:
                x += width
                continue
            ramp, steps = rnd.choice(self.TONES)
            step = rnd.choice(steps)
            top = rnd.choice((0, 0, 1, 1, 2)) if h > 5 else 0
            out[top:, x:x + width, :3] = P.colour(ramp, step)
            if width >= 2:
                out[top:, x + width - 1, :3] = P.colour(ramp, max(0, step - 1))
            if h - top >= 7 and rnd.random() < 0.45:
                band = P.colour("iron", 2) if ramp == "cream" else P.colour("brass", 3)
                out[top + 2, x:x + width, :3] = band
            x += width
        return out


# ---- the room's own models: the bookcase ---------------------------------------------------------
# The bookcase wall is three tiers of bays three blocks wide: a tier on the floor and one on top of
# it, each three blocks high, and a tier of one block under the ceiling. Its lines are those of the
# cabinets of props/furniture, so that the wall and the card cabinets are one family: the plinth
# ends at y 4, the first tier ends in a cornice of two texels (y 46..48) over the board that carries
# the ladder rail (the rail's middle is 44.5 above the floor, one texel off the front), the case is
# six texels deep, the wood is dark_wood 1, 2 and 3.
SHELF_W, SHELF_H, SHELF_D = 48.0, 48.0, 6.0     # one bay: three blocks wide and high, six texels deep
SHELF_TOP_H = 16.0                              # the tier under the ceiling: one block
PLINTH = 4.0                                    # the top of the plinth
CORNICE = 2.0                                   # a cornice, one texel proud of the front
RAIL_BOARD = 3.0                                # the board under the first tier's cornice


def _carcass(m, height, foot, head, boards, crown=0.0):
    """The case of a bookcase bay: a back, two cheeks, an upright in the middle, a foot (a plinth or
    a bottom board, `foot` high), the shelves (`boards`: their undersides) and whatever closes the
    top (`head` high; the caller draws it, and what spans the whole bay, `crown` high). Returns the
    compartments [(x0, x1, y0, y1)], bottom row first."""
    half = SHELF_W / 2.0
    m.box((-half, 0, 0), (half, height - crown, 1), SHADOW, skip="n", grain="y")
    for x in (-half, half - 1.0):
        m.box((x, 0, 1), (x + 1.0, height - crown, SHELF_D), WOOD, grain="y")
    m.box((-1, foot, 1), (1, height - head, SHELF_D - 0.5), WOOD, grain="y")
    m.box((-half + 1, 0, 1), (half - 1, foot, SHELF_D), WOOD_D, grain="x")
    for y in boards:
        m.box((-half + 1, y, 1), (-1, y + 1, SHELF_D - 0.5), WOOD, grain="x")
        m.box((1, y, 1), (half - 1, y + 1, SHELF_D - 0.5), WOOD, grain="x")
    floors = (foot,) + tuple(y + 1 for y in boards)
    ceilings = tuple(boards) + (height - head,)
    return [(x0, x1, y0, y1) for y0, y1 in zip(floors, ceilings) for x0, x1 in ((-half + 1, -1.0), (1.0, half - 1))]


def _stock(m, name, seed, cells, plan):
    """Fill the compartments: `plan` says what each holds, bottom row first: b books, x plate
    boxes, r rolled charts, . nothing."""
    spines = _Spines(f"chart_spines_{name}")
    rnd = random.Random(seed)
    for i, (cell, what) in enumerate(zip(cells, plan)):
        if what == "b":
            _books(m, spines, cell, rnd, 1000 + i)
        elif what == "x":
            _boxes(m, cell, rnd)
        elif what == "r":
            _rolls(m, cell, rnd)


def _books(m, spines, cell, rnd, seed):
    """A row of books in a compartment; now and then the row stops short of the end."""
    x0, x1, y0, y1 = cell
    height = (y1 - y0) - rnd.choice((1, 1, 2))
    run = (x1 - x0) if rnd.random() < 0.7 else float(rnd.choice((12, 15, 18)))
    if rnd.random() < 0.5:
        a, b = x0, x0 + run
    else:
        a, b = x1 - run, x1
    m.box((a, y0, 1), (b, y0 + height, 4.5), SHADOW, skip="nd", faces={"s": spines}, seed=seed)


def _boxes(m, cell, rnd):
    """Pasteboard plate boxes standing side by side, a label on each."""
    x0, x1, y0, y1 = cell
    x = x0 + rnd.choice((0, 1))
    while x + 6 <= x1:
        height = min(y1 - y0 - 1, rnd.choice((7, 8, 8, 9)))
        m.box((x, y0, 1), (x + 6, y0 + height, 5), CARD, skip="nd", grain="y")
        m.box((x + 1.5, y0 + height - 4, 5), (x + 4.5, y0 + height - 2, 5.25), LABEL, skip="n")
        x += 6 + rnd.choice((0, 1, 1))


def _rolls(m, cell, rnd):
    """Rolled charts lying end-on in two layers."""
    x0, x1, y0, y1 = cell
    for layer in range(2):
        x = x0 + (1.5 if layer else 0.0) + rnd.choice((0, 1))
        while x + 3 <= x1 and y0 + 3 * layer + 3 <= y1:
            if rnd.random() < 0.85:
                m.box((x, y0 + 3 * layer, 1), (x + 3, y0 + 3 * layer + 3, 5.5), CARD, skip="n",
                      grain="z", faces={"s": ROLL_END})
            x += 3
    return m


def _shelf(name, seed, plan):
    """A bay of the first tier, on the floor: a plinth, four rows of compartments, the board that
    carries the ladder rail and a cornice. Anchor: on the wall, the middle of its foot."""
    m = M.Model(PREFIX + name)
    half, top = SHELF_W / 2.0, SHELF_H - CORNICE
    cells = _carcass(m, SHELF_H, PLINTH, CORNICE + RAIL_BOARD, (13.0, 23.0, 33.0), crown=CORNICE)
    _stock(m, name, seed, cells, plan)
    m.box((-half + 1, top - RAIL_BOARD, 1), (half - 1, top, SHELF_D), WOOD, grain="x")
    m.box((-half, top, 0), (half, SHELF_H, SHELF_D + 1), WOOD_D, skip="n", grain="x")
    return m


def _shelf_up(name, seed, plan):
    """A bay of the second tier, standing on the cornice of the first: a bottom board, four rows of
    compartments, a top board. Anchor: on the wall, the middle of its foot."""
    m = M.Model(PREFIX + name)
    half = SHELF_W / 2.0
    cells = _carcass(m, SHELF_H, 1.0, 1.0, (12.0, 24.0, 36.0))
    _stock(m, name, seed, cells, plan)
    m.box((-half + 1, SHELF_H - 1, 1), (half - 1, SHELF_H, SHELF_D), WOOD_D, grain="x")
    return m


def _shelf_top(name, seed, plan):
    """A bay of the tier under the ceiling, one block high: one row of compartments, a frieze board
    and the cornice that meets the ceiling. Anchor: on the wall, the middle of its foot."""
    m = M.Model(PREFIX + name)
    half, top = SHELF_W / 2.0, SHELF_TOP_H - CORNICE
    cells = _carcass(m, SHELF_TOP_H, 1.0, CORNICE + 2.0, (), crown=CORNICE)
    _stock(m, name, seed, cells, plan)
    m.box((-half + 1, top - 2.0, 1), (half - 1, top, SHELF_D), WOOD, grain="x")
    m.box((-half, top, 0), (half, SHELF_TOP_H, SHELF_D + 1), WOOD_D, skip="nu", grain="x")
    return m


# name -> (how it is built, the seed of its books, what its compartments hold: bottom row first, in
# a row the left one first as one looks at the wall)
SHELVES = {
    "shelf_a": (_shelf, 11, "xbbbbbbb"),
    "shelf_b": (_shelf, 23, "bbbbbbrb"),
    "shelf_up_a": (_shelf_up, 37, "bbbbbbb."),
    "shelf_up_b": (_shelf_up, 41, "bbbxbbbb"),
    "shelf_top_a": (_shelf_top, 53, "rb"),
    "shelf_top_b": (_shelf_top, 67, "xr"),
}
# the wall, bay by bay from the west: (first tier, second tier, the tier under the ceiling)
SHELF_WALL = (("shelf_b", "shelf_up_a", "shelf_top_a"), ("shelf_a", "shelf_up_b", "shelf_top_b"),
              ("shelf_b", "shelf_up_b", "shelf_top_a"), ("shelf_a", "shelf_up_a", "shelf_top_b"))


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
BRIDGE_Z = -14.0                    # the measuring bridge: over the middle of the second pane
SCOPE_X = -8.0                      # its microscope: towards the west edge, where the observer's stool stands
VIEWER_Z = 38.0                     # the foot of the plate viewer's face, on the fourth pane
VIEW_W, VIEW_H = 26.0, 24.0         # the plate viewer, across and high
VIEW_TILT = -20.0                   # it leans back by this
# the loose plates on the glass: (kind of props/paper, (x, z) of its middle, degrees it is turned)
PLATES = (
    ("photo_plate", (-6.0, -47.0), 8.0), ("photo_plate_b", (5.0, -40.0), -14.0), ("photo_plate_c", (-5.0, -34.0), 4.0),
    ("photo_plate_b", (SCOPE_X, BRIDGE_Z), 0.0),                        # under the microscope
    ("photo_plate", (6.0, 9.0), -6.0), ("photo_plate_c", (-6.0, 17.0), 10.0),
)
STAND_IN = 4                        # how many of them the room's own stand-in shows while props/paper is not in the tree
TABLE_LIGHTS = tuple((x, SILL, z) for z in (12, 16) for x in (7, 8))     # the cells of the table's four sources: the row
#                                     over the glass, two on each side of the middle, one in each of the two columns the
#                                     table stands in, so that the pool is the same on both hands and towards both ends


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


def _bridge():
    """The measuring bridge: a brass beam across the table that rides on the two long sides of its
    frame, the microscope on its carriage, the micrometer drum at one end. Low: from the door it
    lies across the lit lane and leaves the viewer behind it free. Anchor: LIFT over the middle of
    its foot on the frame; x runs across the table."""
    m = M.Model(PREFIX + "bridge", anchor=(0.0, LIFT, 0.0))
    hw = TABLE_W / 2.0
    for s in (-1.0, 1.0):
        x0, x1 = sorted((s * (hw - 2.5), s * (hw + 0.5)))
        m.box((x0, 0, -2), (x1, 2.5, 2), BRASS_D, grain="z")                    # the trucks on the frame
    m.box((-hw + 2.5, 1, -1), (hw - 2.5, 3, 1), BRASS_D, grain="x", faces={"n": SCALE, "s": SCALE}, skip="ew")   # the beam
    x = SCOPE_X
    m.box((x - 2.5, 0.5, -2.5), (x + 2.5, 3.5, 2.5), IRON_D, grain="x")         # the carriage
    m.tube("y", (x, 0.0), 0.25, 1.0, 0.75, IRON_D)                              # the objective, just over the plate
    m.tube("y", (x, 0.0), 3.5, 7.5, 1.0, BRASS)                                 # the tube
    m.tube("y", (x, 0.0), 7.5, 8.75, 0.75, IRON_D)                              # the eyepiece
    m.tube("x", (5.5, 0.0), x + 1.0, x + 2.75, 0.75, BRASS)                     # the focusing head
    m.tube("x", (1.75, 0.0), hw + 0.5, hw + 3.0, 1.5, BRASS)                    # the micrometer drum
    m.tube("x", (1.75, 0.0), hw + 3.0, hw + 3.75, 0.5, IRON_D, sides=4)
    return m


def _viewer():
    """The plate viewer: a lamp house behind a screen of opal glass in a wooden frame, leaning back
    on two stays, the newest plate standing on its ledge with the light behind it. Anchor: LIFT over
    the middle of the foot of its face; the face looks along +z."""
    m = M.Model(PREFIX + "viewer", anchor=(0.0, LIFT, 0.0))
    hw = VIEW_W / 2.0
    with m.turned(("x", VIEW_TILT), about=(0.0, 0.0, -2.0)):                    # it rests on the back edge of its frame
        for x in (-hw, hw - 2.0):
            m.box((x, 0, -2), (x + 2, VIEW_H, 0), WOOD, grain="y")              # the frame
        m.box((-hw + 2, 0, -2), (hw - 2, 2, 0), WOOD, grain="x")
        m.box((-hw + 2, VIEW_H - 2, -2), (hw - 2, VIEW_H, 0), WOOD, grain="x")
        m.box((-hw + 1, 3, -5), (hw - 1, VIEW_H - 1, -2), WOOD_D, grain="x", skip="s")      # the lamp house
        m.box((-hw + 2, 2, -1.5), (hw - 2, VIEW_H - 2, -1), LIT_GLASS, skip="nudew", **LIT)  # the screen
        m.box((-9, 3, -1), (9, 21, -0.5), PLATE_SIDE, skip="n", faces={"s": COMET}, **LIT)   # the plate
        m.box((-10, 2, -1), (10, 3, 0.5), BRASS_D, grain="x")                   # the ledge it stands on
        for x in (-6.0, 6.0):
            m.box((x - 0.5, 20.5, -1), (x + 0.5, 22, -0.25), BRASS_D)           # the two clips that hold its head
        for x in (-6.0, 0.0, 6.0):
            m.box((x - 1.5, 17, -5.25), (x + 1.5, 18, -5), VENT, skip="s", **LIT)   # the lamps through the vents of the back
    for x in (-10.0, 10.0):                                                     # the stays, and their feet on the frame
        m.rod((x, 17.5, -11.5), (x, 0.25, -17.0), 0.5, BRASS_D, sides=4)
        m.box((x - 1, 0, -18), (x + 1, 0.5, -16), BRASS_D)
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
    for m in [_table(k) for k in range(PANES)] + [_bridge(), _viewer(), _plates(), _calculator()]:
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
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            put(x, FLOOR_Y, z, roles.DARK_WOOD.block)

    # ---- beams on the pilaster rows, each end in a shoe at the head of its pier
    for z in PIER_Z:
        for x in range(X0 + 1, X1):
            put(x, TOP, z, st(roles.IRON_RIVETED.slab, type="top"))
        put(X0, TOP, z, st(roles.IRON_RIVETED.stairs, facing="west", half="top"))
        put(X1, TOP, z, st(roles.IRON_RIVETED.stairs, facing="east", half="top"))

    # ---- the bookcase wall, the ladder on its rail, two drop lights before it
    n += _chartshelves.place(c, origin)
    front = _chartshelves.FRONT_Z
    if furniture is not None:
        n += furniture.rail(c, (X1 + 0.5, FEET, front), X1 - X0 + 1, facing="north", origin=origin)
    n += piece(furniture, "furniture", "library_ladder", (AXIS_X + 2.25, FEET, front), facing="north")
    for x in (_chartshelves.PIER_X[0], _chartshelves.PIER_X[-1]):      # a bracket lamp on each outer pier
        n += lamp("bracket", (x, _chartshelves.LAMP_Y[0] + 11 * PX, _chartshelves.PIER_FACE_Z), ASK_SHELF,
                  "bracket lamp on a pier of the bookcase", (int(x), FEET + 3, Z1 - 1), facing="north")

    # ---- the light table: its four lengths, the bridge, the viewer, the plates; the sources of its glass
    held = tuple(TABLE_AT[i] + HELD[i] * PX for i in range(3))
    for k in range(PANES):
        n += K.put(c, own[part_name(k)], held, origin=origin)

    def on_table(x, z, up=GLASS):
        """A point over the table: texels from the middle of its foot."""
        return (TABLE_AT[0] + x * PX, TABLE_AT[1] + up * PX, TABLE_AT[2] + z * PX)

    n += K.put(c, own[PREFIX + "bridge"], on_table(0.0, BRIDGE_Z, FRAME_TOP + LIFT), origin=origin)
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
    n += piece(furniture, "furniture", "stool", (TABLE_AT[0] - TABLE_W / 2.0 * PX - 0.55, FEET, TABLE_AT[2] + BRIDGE_Z * PX),
               facing="east")

    # ---- the west wall. On the blind stretch: three card cabinets side by side, a small globe on the
    # first, the moon map over them; south of them the blackboard, hung where one writes on it (its
    # middle 1.75 above the floor), a lamp over it
    cabinet_x = PANEL_W + 6.5 * PX
    cabinet_top = FEET + (furniture.TOP["card_cabinet"] if furniture is not None else 1.875)
    for z in CABINET_Z:
        n += piece(furniture, "furniture", "card_cabinet", (cabinet_x, FEET, z), facing="east")
    if furniture is not None:
        n += piece(instruments, "instruments", "globe", (cabinet_x, cabinet_top, CABINET_Z[0]), facing="east")
    n += piece(paper, "paper", "moon_map", (PANEL_W, cabinet_top + 1.0, CABINET_Z[1]), facing="east")
    n += piece(paper, "paper", "blackboard", (PANEL_W, FEET + 1.75, BOARD_Z), facing="east")
    n += lamp("bracket", (PANEL_W, FEET + 2.5 + OVER, BOARD_Z), ASK_WALL, "blackboard",
              (X0 + 1, FEET + 1, int(BOARD_Z)), facing="east")
    # at its first window the drafting table, a drop light over the drafter's left hand; at the next
    # the celestial globe
    z = bay_z(DRAFT_BAY)
    n += piece(furniture, "furniture", "drafting_table", (PANEL_W + 8 * PX, FEET, z), facing="east")
    n += piece(furniture, "furniture", "stool", (PANEL_W + 8 * PX + 1.1, FEET, z), facing="west")
    n += drop(PANEL_W + 0.75, z + 0.5, DRAFT_HANG, ASK_DESK, "drafting table", (X0 + 1, FEET, int(z)))
    n += piece(instruments, "instruments", "celestial_globe", (WEST + 1.6, FEET, bay_z(GLOBE_BAY)), facing="east")

    # ---- the north wall: the pair of great sky maps, one on each side of the door, a lamp over each
    for x, kind in zip(MAP_X, ("sky_map", "sky_map_b")):
        n += piece(paper, "paper", kind, (x, MAP_Y, PANEL_N), facing="south")
        n += lamp("bracket", (x, MAP_Y + 1.0 + OVER, PANEL_N), ASK_WALL, f"{kind}", (int(x), FEET + 3, Z0 + 1), facing="south")
    n += piece(furniture, "furniture", "coat_stand", (EAST - 1.1, FEET, NORTH + 0.9))

    # ---- the east wall. Under its second window the writing desk (props/furniture's is 30 by 14, its
    # front the side one sits at; at its back an upstand between two stationery drawers): the
    # calculator in the middle against the upstand, the green lamp on the far corner as the door sees
    # the desk, turned a little towards the sitter, the closed log before the sitter's left hand
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

    n += piece(furniture, "furniture", "writing_desk", desk, facing="west")
    n += piece(furniture, "furniture", "swivel_chair", (desk[0] - 1.0, FEET, desk[2] - 0.1), facing="east")
    n += lamp("desk_green", on_desk(11.5, -3.0), ASK_DESK, "the green desk lamp", (X1 - 1, FEET, int(desk[2])),
              yaw=desk_yaw + 35.0)
    if has(instruments, "calc_machine"):
        n += instruments.place(c, "calc_machine", on_desk(0.5, -0.75), facing="west", origin=origin)
    else:
        missing.append("instruments:calc_machine")
        n += K.put(c, own[PREFIX + "calculator"], on_desk(0.5, -0.75), yaw=desk_yaw, origin=origin)
    n += piece(paper, "paper", "logbook_shut", on_desk(-10.5, 2.5), yaw=desk_yaw - 12.0)
    # at the third window the small telescope; under the fourth a bench and a drop light to read by;
    # by the bookcase the trunk the plates come down from the dome in
    n += piece(instruments, "instruments", "tripod_scope_comet", (EAST - 1.7, FEET, bay_z(SCOPE_BAY)), facing="east")
    z = bay_z(BENCH_BAY)
    n += piece(furniture, "furniture", "bench", (PANEL_E - 7.25 * PX, FEET, z), facing="west")
    n += drop(PANEL_E - 0.75, z - 0.5, DESK_HANG, ASK_DESK, "bench", (X1 - 1, FEET, int(z)))
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
