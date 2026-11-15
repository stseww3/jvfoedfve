"""The chart room (plan ART-PLAN 8; card plan/packages/interiors/chartroom.md): the south wing of the
main floor, the room of V9. It mirrors the time room of the north wing about the axis.

The star of the room is the plate light table: glass negatives of the sky spread on a pane lit
from below, the newest one stood up on a tilted viewing frame. It stands in the middle of the room
on the long axis, so that the eye runs from the door over the lit glass to the wall of books that
closes the room in the south.

    north   the door from the gallery (x 7..8); the pair of great sky maps beside it
    middle  the light table across the axis, its viewing frame towards the door
    south   the whole wall is bookcase, floor to ceiling, with the library ladder on its rail
    west    the blind stretch behind the rotunda (z 7..13): the card cabinets in one row, the
            blackboard and the moon map over them; then a globe and the drafting table at the windows
    east    five great windows; the writing desk under the fourth, on it the green lamp and the
            hand calculator

What is whose. The room's own models (names "int_chart_..."): the light table, the bookcases, the
calculator. Everything else comes from the props line and is placed through its place() functions:
lamps (props/lamps), furniture (props/furniture, c179), paper (props/paper, c197), instruments
(props/instruments, c199). A module that is not in the tree yet is left out, or stood in for with
plain blocks where something has to carry a lamp; what was left out is in the returned record.

The light. A lit window does not light the room (A0 #32717: its inner face is lined, materials/
windows); the room is lit by its lamps. They are offered to the light line (sky/_lightkit.suggest);
while that is not in the tree the invisible sources are put down here. The light table is the
brightest thing in the room and the green desk lamp its one green.

Coordinates are the skeleton's: build_chartroom() dresses the room where it stands in the building,
the box test scene (build/scenes/obs_int_chartroom) stands a stand-in of the shell around it.
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
from ..props import _kit as K
from ..props import lamps

MOVED_IN = False        # the master scene dresses the room once main/shell is in the tree
NAME = "interiors/chartroom"
PREFIX = "int_chart_"

# ---- the room (cells) ---------------------------------------------------------------------------
X0, X1 = S.ROOM_X                   # 2..13: clear, between the glass planes
Z0, Z1 = MP.WING_S_Z                # 7..25: clear, between the cross wall and the end pavilion
FEET = S.STAND                      # 7
FLOOR_Y = FEET - 1                  # 6: the floor block
CEIL_Y = S.STAR_HALL_CEIL           # 14: the ceiling block
TOP = CEIL_Y - 1                    # 13: the highest clear row
DOOR_X = MP.ROOM_DOOR_X             # (7, 8): the door in the cross wall on z 6
PIER_Z = tuple(z for z in range(Z0, Z1 + 1) if MP.on_pilaster(z))                   # 10, 14, 18, 22
EAST_BAYS = tuple(b for b in range(1, S.N_BAYS + 1)
                  if set(MP.window_rows(b)) <= set(range(Z0, Z1 + 1)))                # 11..15
WEST_BAYS = tuple(b for b in EAST_BAYS
                  if all(abs(z - S.DOME_CENTRE[1]) > MP.WEST_BLIND_Z for z in MP.window_rows(b)))   # 13..15

# ---- the room (points) --------------------------------------------------------------------------
WEST, EAST = float(X0), float(X1 + 1)           # 2.0, 14.0: the inner faces of the long walls
NORTH, SOUTH = float(Z0), float(Z1 + 1)         # 7.0, 26.0: of the cross wall and the pavilion wall
AXIS_X = S.mid(*DOOR_X)                         # 8.0: the long axis of the room runs through the door
MID_Z = S.mid(Z0, Z1)                           # 16.5
SKIRT = 3.0 / 16.0                              # the wainscot's thickness: furniture stands off the wall by it

# ---- where the pieces stand -----------------------------------------------------------------------
TABLE_AT = (AXIS_X, float(FEET), MID_Z)         # the light table: the middle of its foot
TABLE_FACING = "north"                          # its viewing frame looks at the door
DESK_BAY = 14                                   # the writing desk stands under this window of the east wall
CABINET_Z = tuple(range(Z0 + 1, Z0 + 6))        # 8..12: the row of card cabinets on the west wall
LAMP_PIERS = {"east": (14, 18), "west": (18, 22)}    # the piers that carry a caged lamp, beside the lit windows

# the lamps: (level, rank) asked of the light line
ASK_TABLE = (11, 2)         # the light table: the room's main light
ASK_SHELF = (9, 3)          # two pendants before the bookcase
ASK_PIER = (7, 3)           # caged lamps on the piers
ASK_DESK = (6, 3)           # the green desk lamp

# ---- materials ----------------------------------------------------------------------------------
WOOD = P.mat("dark_wood")
WOOD_L = P.mat("dark_wood", base=3)
WOOD_D = P.mat("dark_wood", base=1)
SHADOW = K.flat("dark_wood", 0)                 # the inside of a bookcase
BRASS, BRASS_D, IRON, IRON_D = K.BRASS, K.BRASS_D, K.IRON, K.IRON_D
CARD = P.mat("cream", base=1, bevel=1)          # pasteboard boxes
LABEL = K.flat("cream", 3)
LIT_GLASS = P.mat("opal")                       # the lit pane: brighter towards its middle
LIT = dict(emit=15, shade=False)
VENT = K.flat("glow", 1)
PLATE_EDGE = K.flat("glow", 1)                  # the ground edge of a glass plate

ROLL_END = Sprite("chart_roll_end", ["aba", "bcb", "aba"],
                  {"a": P.RAMPS["cream"][1], "b": P.RAMPS["cream"][2], "c": P.RAMPS["dark_wood"][0]})

# A glass negative on the lit pane: the sky is clear glass, the stars are black. The tones are those
# of the plates of props/paper (c197): the glass glow 3 inside a rim of glow 1, the stars dark iron;
# the pane under them is lighter still, so a plate reads as a piece of tinted glass lying on it.
_g, _i = P.RAMPS["glow"], P.RAMPS["iron"]
PLATE_COMET = Sprite("chart_plate_comet", [     # the plate on the viewing frame: the comet, head down
    "eeeeeeeeeeeeee",
    "eaaaaaaaaaaaae",
    "eaasaaaaaagaae",
    "eaaaaaaaagaaae",
    "eaaaaaaagdaaae",
    "easaaaagdgaaae",
    "eaaaaagdgaaaae",
    "eaaaagdkgaasae",
    "eaaaagkdaaaaae",
    "eaaaaagaaaaaae",
    "eaasaaaaaaaaae",
    "eaaaaaaaasaaae",
    "eaaaaaaaaaaaae",
    "eeeeeeeeeeeeee",
], {"e": _g[1], "a": _g[3], "s": _i[1], "g": _g[2], "d": _i[5], "k": _i[2]})
PLATE_FIELD = Sprite("chart_plate_field", [
    "eeeeeeee",
    "easaaaae",
    "eaaaasae",
    "eaaaaaae",
    "esaasaae",
    "eaaaaaae",
    "eaaasaae",
    "eeeeeeee",
], {"e": _g[1], "a": _g[3], "s": _i[1]})
PLATE_STRIP = Sprite("chart_plate_strip", [
    "eeeeeeee",
    "eakakake",
    "eakakake",
    "eeeeeeee",
], {"e": _g[1], "a": _g[3], "k": _i[3]})          # a spectrum plate: a band of lines


class _Spines:
    """The picture of a row of books seen from the front: spines of uneven width and height in the
    quiet colours of the palette, the dark of the case behind them. It stands in for a material on
    the front of one box (artkit.models asks a material only for its name and paint())."""

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
            width = rnd.choice((1, 2, 2, 2, 3))
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


# ---- the room's own models ----------------------------------------------------------------------
SHELF_W, SHELF_H, SHELF_D = 48.0, 48.0, 6.0     # one bay of bookcase: three blocks wide and high
SHELF_TOP_H = 16.0                              # the top tier under the ceiling: one block
BOARDS = (13.0, 24.0, 35.0)                     # the undersides of the three loose shelves


def _carcass(m, height, boards):
    """The case of a bookcase bay: a back, two cheeks, an upright in the middle, a plinth, a top and
    the shelves. Returns the compartments [(x0, x1, y0, y1)], bottom row first."""
    half = SHELF_W / 2.0
    m.box((-half, 0, 0), (half, height, 1), SHADOW, skip="n", grain="y")
    for x in (-half, half - 1.0):
        m.box((x, 0, 1), (x + 1.0, height, SHELF_D), WOOD, grain="y")
    m.box((-1, 2, 1), (1, height - 1, SHELF_D - 0.5), WOOD, grain="y")
    m.box((-half + 1, 0, 1), (half - 1, 2, SHELF_D), WOOD_D, grain="x")
    m.box((-half + 1, height - 1, 1), (half - 1, height, SHELF_D), WOOD_D, grain="x")
    for y in boards:
        m.box((-half + 1, y, 1), (-1, y + 1, SHELF_D - 0.5), WOOD_L, grain="x")
        m.box((1, y, 1), (half - 1, y + 1, SHELF_D - 0.5), WOOD_L, grain="x")
    floors = (2.0,) + tuple(y + 1 for y in boards)
    ceilings = tuple(boards) + (height - 1,)
    return [(x0, x1, y0, y1) for y0, y1 in zip(floors, ceilings) for x0, x1 in ((-half + 1, -1.0), (1.0, half - 1))]


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
    """One bay of the bookcase wall, three blocks wide and three high. `plan` says what each of its
    eight compartments holds, bottom row first: b books, x plate boxes, r rolled charts, . nothing.
    Anchor: on the wall, the middle of its foot."""
    m = M.Model(PREFIX + name)
    spines = _Spines(f"chart_spines_{name}")
    rnd = random.Random(seed)
    for i, (cell, what) in enumerate(zip(_carcass(m, SHELF_H, BOARDS), plan)):
        if what == "b":
            _books(m, spines, cell, rnd, 1000 + i)
        elif what == "x":
            _boxes(m, cell, rnd)
        elif what == "r":
            _rolls(m, cell, rnd)
    return m


def _shelf_top(name, seed, plan):
    """The top tier of a bay, one block high: one row of compartments under the cornice that meets
    the ceiling. Anchor: on the wall, the middle of its foot."""
    m = M.Model(PREFIX + name)
    spines = _Spines(f"chart_spines_{name}")
    rnd = random.Random(seed)
    half = SHELF_W / 2.0
    for i, (cell, what) in enumerate(zip(_carcass(m, SHELF_TOP_H - 3.0, ()), plan)):
        if what == "b":
            _books(m, spines, cell, rnd, 1000 + i)
        elif what == "x":
            _boxes(m, cell, rnd)
        elif what == "r":
            _rolls(m, cell, rnd)
    m.box((-half, SHELF_TOP_H - 3, 0), (half, SHELF_TOP_H - 2, SHELF_D + 1), WOOD_L, skip="n", grain="x")
    m.box((-half, SHELF_TOP_H - 2, 0), (half, SHELF_TOP_H, SHELF_D + 2), WOOD_D, skip="nu", grain="x")
    return m


TABLE_L, TABLE_D = 44.0, 24.0       # the light table: long across the room, deep along it
TABLE_GLASS = 14.75                 # the top of its lit pane above the floor
TABLE_TOP = TABLE_GLASS / 16.0      # the same in blocks: where the plates lie
FRAME_TILT = -20.0                  # the viewing frame leans back by this
# where the loose plates lie on the pane, in the table's own frame (texels from its middle; +z is
# the side of the viewing frame's face), and how each is turned
PLATES = (("photo_plate", (-13.0, 4.0), 8.0), ("photo_plate_b", (-2.0, 5.0), -14.0), ("photo_plate_c", (9.0, 3.0), 4.0))


def _light_table():
    """The plate light table: a lamp box on four legs, a brass-framed pane of opal glass lit from
    below, and at its back a tilted viewing frame with the newest plate on it. The front (+z) is
    the side the viewing frame looks to. Anchor: the middle of its foot."""
    m = M.Model(PREFIX + "light_table")
    hl, hd = TABLE_L / 2.0, TABLE_D / 2.0
    for x in (-hl + 1, hl - 4):
        for z in (-hd + 1, hd - 4):
            m.box((x, 0, z), (x + 3, 11, z + 3), WOOD, grain="y")
    for x in (-hl + 1.5, hl - 3.5):
        m.box((x, 3, -hd + 4), (x + 2, 5, hd - 4), WOOD_D, grain="z")           # end stretchers
    m.box((-hl + 3.5, 3, -1), (hl - 3.5, 5, 1), WOOD_D, grain="x")              # the long stretcher
    m.box((-hl, 11, -hd), (hl, 14, hd), WOOD, grain="x")                        # the lamp box
    m.box((-14, 7, -8), (14, 11, 8), WOOD_D, grain="x")                         # its deeper middle: the lamps
    for x in (-9.0, -3.0, 3.0, 9.0):
        m.box((x - 1.5, 8.5, 8), (x + 1.5, 9.5, 8.25), VENT, skip="n", **LIT)   # vent slots, a little light
    m.box((-hl, 14, hd - 2), (hl, 15, hd), BRASS, grain="x")                    # the brass frame of the pane
    m.box((-hl, 14, -hd), (hl, 15, -hd + 2), BRASS, grain="x")
    m.box((-hl, 14, -hd + 2), (-hl + 2, 15, hd - 2), BRASS, grain="z")
    m.box((hl - 2, 14, -hd + 2), (hl, 15, hd - 2), BRASS, grain="z")
    m.box((-hl + 2, 14, -hd + 2), (hl - 2, TABLE_GLASS, hd - 2), LIT_GLASS, skip="d", grain="x", **LIT)
    m.tube("y", (15.0, 5.5), TABLE_GLASS, TABLE_GLASS + 3.0, 1.5, BRASS, sides=8)       # a loupe on the pane
    m.tube("y", (15.0, 5.5), TABLE_GLASS + 3.0, TABLE_GLASS + 3.5, 1.0, BRASS_D, sides=8)
    with m.turned(("x", FRAME_TILT), about=(0.0, 15.0, -8.0)):                  # hinged on its back foot
        m.box((-14, 15, -8), (-12, 35, -6), WOOD, grain="y")                    # the frame
        m.box((12, 15, -8), (14, 35, -6), WOOD, grain="y")
        m.box((-12, 15, -8), (12, 17, -6), WOOD, grain="x")
        m.box((-12, 33, -8), (12, 35, -6), WOOD, grain="x")
        m.box((-12, 17, -8), (12, 33, -7.5), WOOD_D, grain="x")                 # its back board
        m.box((-12, 17, -7.5), (12, 33, -6.5), LIT_GLASS, skip="n", grain="x", **LIT)
        m.box((-7, 18, -6.5), (7, 32, -6.25), PLATE_EDGE, skip="n", faces={"s": PLATE_COMET}, **LIT)
        m.box((-9, 17, -6.5), (9, 18, -5.5), BRASS_D, grain="x")                # the ledge the plate stands on
    for x in (-13.0, 13.0):
        m.box((x - 0.5, 15, -11.5), (x + 0.5, 16, -6.5), BRASS_D, grain="z")    # the feet of the frame's stays
    return m


def _plates():
    """Three loose plates lying on the pane: the stand-in for the plates of props/paper while that
    module is not in the tree. Drawn in the table's frame, so it is placed where the table is."""
    m = M.Model(PREFIX + "plates")
    pictures = (PLATE_FIELD, PLATE_FIELD.mirrored(), PLATE_STRIP)
    for (kind, (x, z), turn), picture in zip(PLATES, pictures):
        d = 2.0 if picture is PLATE_STRIP else 4.0
        m.box((x - 4, TABLE_GLASS, z - d), (x + 4, TABLE_GLASS + 0.25, z + d), PLATE_EDGE, skip="d",
              rot=("y", turn, (x, TABLE_GLASS, z)), faces={"u": picture}, **LIT)
    return m


def _calculator():
    """The hand calculator: a pinwheel machine, black with brass setting levers, a carriage with
    the result windows in front and the crank on its right. Anchor: the middle of its foot; the
    front (+z) is the side one sits at."""
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


# name -> what its compartments hold (bottom row first, west to east as one looks at the wall is
# right to left: the wall looks north)
SHELVES = {
    "shelf_a": (11, "bbbbbbbb"),
    "shelf_b": (23, "xbbbbbrb"),
    "shelf_c": (37, "bxbbbbbb"),
    "shelf_d": (41, "bbbxbbb."),
}
SHELF_TOPS = {
    "shelf_top_a": (53, "rb"),
    "shelf_top_b": (67, "xr"),
}
# the wall, bay by bay from the west: (lower tier, upper tier, top tier)
SHELF_WALL = (("shelf_b", "shelf_a", "shelf_top_a"), ("shelf_a", "shelf_d", "shelf_top_b"),
              ("shelf_c", "shelf_a", "shelf_top_a"), ("shelf_a", "shelf_b", "shelf_top_b"))


@functools.lru_cache(maxsize=None)
def _models():
    out = {PREFIX + name: _shelf(name, seed, plan) for name, (seed, plan) in SHELVES.items()}
    out.update({PREFIX + name: _shelf_top(name, seed, plan) for name, (seed, plan) in SHELF_TOPS.items()})
    for m in (_light_table(), _plates(), _calculator()):
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


def panel(side):
    """A panel of the wainscot standing on that side of its cell."""
    back = {"north": "south", "south": "north", "west": "east", "east": "west"}[side]
    return st(B.WAINSCOT, facing=back, half="bottom", open="true")


def desk_rows():
    return MP.window_rows(DESK_BAY)


# ---- building -----------------------------------------------------------------------------------
def build_chartroom(c, origin=(0, 0, 0), roles=B, *, version="a"):
    """Dress the room standing at `origin`. Returns dict(entities=<display entities placed>,
    lights=[(cell, level, why)] offered to the light line, missing=[what was left out or stood in
    for because its module is not in the tree])."""
    ox, oy, oz = origin
    own = _models()
    furniture, paper, instruments = _peer("furniture"), _peer("paper"), _peer("instruments")
    lights, missing = [], []
    n = 0

    def put(x, y, z, state, keep=False):
        c.set(ox + x, oy + y, oz + z, state, keep=keep)

    def offer(cell, ask, why):
        level, rank = ask
        lights.append((cell, level, f"{NAME}:{why}"))
        _offer(c, cell, level, f"{NAME}:{why}", rank)

    def lamp(kind, pos, ask, why, **how):
        name = f"{kind}_{lamps.VERSION}" if kind in lamps.VERSIONED else kind
        cell = K.light_cell(pos, K.FACING[how.get("facing", "south")], lamps.SPEC[name]["light"], origin)
        offer(cell, ask, why)
        return lamps.place(c, kind, pos, origin=origin, light=False, **how)

    def piece(module, label, kind, pos, **how):
        if module is None:
            missing.append(f"{label}:{kind}")
            return 0
        return module.place(c, kind, pos, origin=origin, **how)

    # the wainscot: one course at the foot of the long walls and of the cross wall; the bookcase
    # stands on the floor of the south wall
    for z in range(Z0, Z1 + 1):
        put(X0, FEET, z, panel("west"))
        put(X1, FEET, z, panel("east"))
    for x in range(X0, X1 + 1):
        if not DOOR_X[0] <= x <= DOOR_X[1]:
            put(x, FEET, Z0, panel("north"), keep=True)

    # the ceiling: riveted iron beams on the lines of the pilasters, under the boards
    for z in PIER_Z:
        for x in range(X0, X1 + 1):
            put(x, TOP, z, st(roles.IRON_RIVETED.slab, type="top"))

    # the bookcase wall, and the ladder on its rail
    for i, tiers in enumerate(SHELF_WALL):
        x = X0 + SHELF_W / 32.0 + i * SHELF_W / 16.0
        for name, y in zip(tiers, (FEET, FEET + 3, FEET + 6)):
            n += K.put(c, own[PREFIX + name], (x, y, SOUTH), mount="wall", facing="north", origin=origin)
    front = SOUTH - SHELF_D / 16.0
    if furniture is not None:
        n += furniture.rail(c, (X1 + 0.5, FEET, front), X1 - X0 + 1, facing="north", origin=origin)
    n += piece(furniture, "furniture", "library_ladder", (AXIS_X + 2.25, FEET, front), facing="north")
    for x in (AXIS_X - 3.0, AXIS_X + 3.0):
        n += lamp("pendant", (x, CEIL_Y, SOUTH - 1.5), ASK_SHELF, "pendant before the bookcase")

    # the light table
    yaw = K.FACING[TABLE_FACING]
    n += K.put(c, own[PREFIX + "light_table"], TABLE_AT, yaw=yaw, origin=origin)
    if paper is not None:
        for kind, (x, z), turn in PLATES:
            dx, _, dz = K.turn(yaw, (x / 16.0, 0.0, z / 16.0))
            n += paper.place(c, kind, (TABLE_AT[0] + dx, TABLE_AT[1] + TABLE_TOP, TABLE_AT[2] + dz),
                             yaw=yaw + turn, origin=origin)
    else:
        missing.append("paper:photo_plate")
        n += K.put(c, own[PREFIX + "plates"], TABLE_AT, yaw=yaw, origin=origin)
    offer(K.light_cell(TABLE_AT, yaw, (0.0, TABLE_TOP + 0.5, 0.0), origin), ASK_TABLE, "the light table")

    # the west wall: card cabinets in a row, the blackboard and the moon map over them
    cabinet_x = WEST + SKIRT + 6.5 / 16.0
    for z in CABINET_Z:
        if furniture is None:
            for y in (FEET, FEET + 1):
                put(X0, y, z, roles.DARK_WOOD.block)
        n += piece(furniture, "furniture", "card_cabinet", (cabinet_x, FEET, z + 0.5), facing="east")
    n += piece(paper, "paper", "blackboard", (WEST, FEET + 3.5, CABINET_Z[0] + 1.75), facing="east")
    n += piece(paper, "paper", "moon_map", (WEST, FEET + 3.5, CABINET_Z[-1] + 0.25), facing="east")
    # further on, at the windows: a globe and the drafting table
    n += piece(instruments, "instruments", "celestial_globe", (WEST + 1.6, FEET, PIER_Z[2] + 0.5), facing="east")
    n += piece(furniture, "furniture", "drafting_table", (WEST + SKIRT + 0.6, FEET, PIER_Z[3] + 1.0), facing="east")
    n += piece(furniture, "furniture", "stool", (WEST + SKIRT + 1.6, FEET, PIER_Z[3] + 1.0), facing="west")

    # the cross wall: the pair of great sky maps, one on each side of the door
    n += piece(paper, "paper", "sky_map", (DOOR_X[0] - 2.5, FEET + 3.5, NORTH), facing="south")
    n += piece(paper, "paper", "sky_map_b", (DOOR_X[1] + 3.5, FEET + 3.5, NORTH), facing="south")

    # the writing desk under a window of the east wall: the green lamp, the calculator, the log
    rows = desk_rows()
    desk_x, desk_z = EAST - SKIRT - 7.0 / 16.0, S.mid(rows[0], rows[-1])
    if furniture is None:
        desk_top = 1.0
        for z in rows:
            put(X1, FEET, z, st(roles.DARK_WOOD.slab, type="top"))
    else:
        desk_top = furniture.TOP["writing_desk"]
    n += piece(furniture, "furniture", "writing_desk", (desk_x, FEET, desk_z), facing="west")
    n += piece(furniture, "furniture", "swivel_chair", (desk_x - 1.0, FEET, desk_z + 0.1), facing="east")
    n += lamp("desk_green", (desk_x + 0.125, FEET + desk_top, desk_z - 0.55), ASK_DESK, "the green desk lamp",
              facing="west")
    n += K.put(c, own[PREFIX + "calculator"], (desk_x - 0.06, FEET + desk_top, desk_z + 0.5),
               yaw=K.FACING["west"], origin=origin)
    n += piece(paper, "paper", "logbook", (desk_x - 0.125, FEET + desk_top, desk_z - 0.05), yaw=K.FACING["west"])

    # caged lamps on the piers beside the lit windows
    for z in LAMP_PIERS["east"]:
        n += lamp("cage", (EAST, FEET + 3.5, z + 0.5), ASK_PIER, "caged lamp on a pier", facing="west")
    for z in LAMP_PIERS["west"]:
        n += lamp("cage", (WEST, FEET + 3.5, z + 0.5), ASK_PIER, "caged lamp on a pier", facing="east")

    return {"entities": n, "lights": lights, "missing": missing}


def _offer(canvas, cell, level, why, rank):
    """Hand one light source to the light line; while it is not in the tree, put the source down."""
    try:
        from ..sky import _lightkit
    except ImportError:
        canvas.set(*cell, st(B.LIGHT, level=level), keep=True)
    else:
        _lightkit.suggest(canvas, cell, level, why, rank=rank)


def build(canvas, origin=(0, 0, 0)):
    if not MOVED_IN:
        return 0
    return build_chartroom(canvas, origin)["entities"]
