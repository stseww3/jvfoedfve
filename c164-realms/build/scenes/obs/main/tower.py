"""main/tower -- the clock tower on the north end pavilion (plan/ART-PLAN.md 5.3, plan/parts/main.md
6.2, card plan/packages/main/tower.md; the director's four points on the first version, group #265).

The pavilion's walls and parapet (y 0..17) are main/facade.py, its roof deck at y 17 is the roof
package's. This is what stands on the deck, on the skeleton's footprint CLOCK_SHAFT_X/Z and to its
heights CLOCK_SHAFT_TOP, CLOCK_TOP and CLOCK_BALL_MAST:

    y 18..30   the shaft: 7 x 7, hollow, flush on all four faces from foot to cornice (nothing
               stands proud of it: its relief is sunk). Three rows of rusticated base, dressed
               stone above them between rusticated quoins that run unbroken to the cornice, one
               column long and two by turns. Every face has two sunk squares of three by three,
               one above the other: the field of a slit window (the slit y 22..23) and the
               recess of a clock dial (y 26..28), backed with dark iron plate. A frieze of
               panels under the cornice; an iron door in the west face opens on the roof walk.
    y 31       the shaft's one cornice: the main order's moulding, in stone
    y 32..35   the lookout, as wide as the shaft and open on all four sides; its ceiling is y 36
    y 35..41   the verdigris top, the building's third green top beside the two domes. Copper
               begins with the eaves and nowhere below them: the eaves are the roof's own
               moulding and gutter, and from below it is their soffit that is seen
    y 42..53   the mast of the time ball, the cup anemometer and the wind vane at its head

The top is pointed, beside the two round domes (main's approver, 11-16, on the pictures of two
versions; the round one, an octagonal kiosk under a dome, is in the history at b01b871f): the
lookout has four arches of three columns between corner piers, a round head to each, under a
four-sided roof whose faces rise in an arc: eaves hung in the row of the arch heads, a kick on
them, an upright foot on the wall line, a shoulder, and 45 degrees to the finial.

There is no cross anywhere: the plan is a square, and the mast carries a pennant at its tip and
the cup wheel lower down on the other side.

Not here: the dials, their hands and the time ball are machines/clock, which finds the recesses and
the mast by itself (DIAL_CENTRES and MAST_MODEL say where they are); the light of the lit slits and
of the lookout's lamp is placed by sky/lights (windows(), and the kit's suggest()). The radio mast
hangs no wire to the tower (the director, 11-16: the mast itself is the aerial), so the shaft
carries no bracket or hook for one: its four faces are flush alike. The clock room behind the
dials is interiors/clockroom; what it reads of the well is WELL_X/Z/Y, ROOM_FLOOR, backs() and
DIAL_BACKS, and way_up() opens the door and stands the ladder for it.

The mast is two display models, the only ones of the main line: bld_tower_mast, the pole with all
that is fixed to it, and bld_tower_cups, the cup wheel, a piece of its own so that the motion line
can turn it about its spindle. build() returns 2.

    python -m scenes.obs.main.tower            # as text: elevation, sections, plans, the way up
"""
import functools
import math
import sys

from artkit import models as M
from artkit.blocks import st
from artkit.canvas import Canvas

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..motion import _kit as MK
from . import _order as O

# --- the footprint (skeleton, LOCKED): 7 x 7, the east face flush with the pavilion's wall ----------
X0, X1 = S.CLOCK_SHAFT_X            # 10 .. 16
Z0, Z1 = S.CLOCK_SHAFT_Z            # -33 .. -27
CX, CZ = (X0 + X1) // 2, (Z0 + Z1) // 2         # 13, -30: the middle column
AXIS = (CX + 0.5, CZ + 0.5)         # (13.5, -29.5): the tower's axis, a point
BODY = O.box(X0, Z0, X1, Z1)        # the 49 columns of the shaft
INSIDE = O.shrink(BODY)             # the well, 5 x 5
WALLS = BODY - INSIDE               # the 24 columns of the wall
LAST = X1 - X0                      # 6: a face's seven columns are counted 0 .. 6
MID = LAST // 2                     # 3: the middle one
ARCH = (2, 3, 4)                    # the three columns of a sunk square and of a lookout arch

# --- the rows -----------------------------------------------------------------------------------------
FOOT = S.ROOF_STAND                 # 18: the first row on the pavilion's deck
BASE_TOP = 20                       # the last row of the rusticated base
SLIT_Y = (22, 23)                   # the slit windows
FIELD_Y = (SLIT_Y[0] - 1, SLIT_Y[1])            # 21 .. 23: the sunk field a slit stands in, its apron below
DIAL_Y = (26, 28)                   # the dial recesses
SHAFT_TOP = S.CLOCK_SHAFT_TOP       # 31: the cornice row, and the floor of the lookout
FRIEZE_Y = SHAFT_TOP - 1            # 30: the frieze under the cornice
LOOKOUT = (32, 35)                  # its open rows; the eaves hang in the last of them
HEAD = 36                           # its ceiling, and the foot of the roof
ROOF = (37, S.CLOCK_TOP)            # 37 .. 41: copper and nothing else
APEX = S.CLOCK_TOP                  # 41: the finial block

# --- the mast (points, in blocks) ---------------------------------------------------------------------
MAST_MODEL = "bld_tower_mast"       # machines/clock looks for a display of this model: the mast stands
CUPS_MODEL = "bld_tower_cups"       # the cup wheel: the motion line turns it (its tag is the kit's, m.<model>)
MAST_FOOT = APEX + 1.0              # 42.0: the top of the finial
MAST_STOP = S.CLOCK_BALL_MAST - 1.0  # 51.0: up to here the pole is plain and the ball's to travel on
MAST_TOP = S.CLOCK_BALL_MAST + 1.0  # 53.0: the tip, the top of the skeleton's last row
MAST_THICK = 7 / 16.0               # the pole between its boot and the stop collar
MAST_SCALE = 4.0                    # the model is shown at four times its size: 11 blocks are 44 units
MAST_HOLD = 0.5                     # the entity stands this far above the foot: in the air over the finial
WIND = (S.WIND[0], S.WIND[2])       # (0, 1): one step downwind along x and z; the vane's tail points there
CUPS_OUT = 0.875                    # the cup wheel's spindle stands this far upwind of the axis: north
CUPS_AT = (AXIS[0] - CUPS_OUT * WIND[0], MAST_STOP + 0.4375, AXIS[1] - CUPS_OUT * WIND[1])   # (13.5, 51.4375, -30.375): its hub
VANE_LONG = 2.0                     # the pennant of the wind vane: from the axis to the ends of its two tails,
VANE_TAIL = 0.75                    # how long the tails are,
VANE_HIGH = 0.75                    # and how high it is; its upper edge is the tip of the mast
FAR = 4.0                           # view_range, as machines/clock gives the dials and the ball

# --- light --------------------------------------------------------------------------------------------
FRONT, STOREY = "tower", "shaft"    # the slits' keys for the light line; the bay is the face's number
LIT_FACES = ("east", "west")        # the slits that are lit: opposite faces, never two neighbours
SLIT_LIGHT = 7                      # the stand-in source of a lit slit: what sky/lights places (9 - 2)
LAMP = True                         # a caged lamp let into the lookout's ceiling
LAMP_LEVEL = 7                      # the fill it asks the light line for (rank 3)

# --- materials: roles of the occupancy table ------------------------------------------------------------
WALL = B.ASHLAR_FINE
QUOIN = B.ASHLAR_ROUGH              # quoins and base
PANEL = B.ASHLAR_PANEL              # the field of the slits, the frieze
PLATE = B.IRON_PLATE                # the back of the dial recesses
BARS = B.IRON_BARS                  # the railing in the lookout's arches
CEILING = B.ASHLAR_PANEL            # pale, so that the lookout holds the glow of its lamp
DOOR, BULB = B.IRON_DOOR, B.IRON_BULB
COPPER = B.VERDIGRIS_CUT
FINIAL = B.VERDIGRIS_CAST


class Face:
    """One face of the shaft: the side it looks to, its seven wall columns in order (north to
    south, or west to east) and the names of the two directions along it."""

    def __init__(self, name, bay):
        self.name, self.bay = name, bay
        self.out = O.STEP[name]
        dx, dz = self.out
        if dx:
            x = X1 if dx > 0 else X0
            self.cells = [(x, z) for z in range(Z0, Z1 + 1)]
            self.low, self.high = "north", "south"
        else:
            z = Z1 if dz > 0 else Z0
            self.cells = [(x, z) for x in range(X0, X1 + 1)]
            self.low, self.high = "west", "east"

    @property
    def inward(self):
        return (-self.out[0], -self.out[1])

    def cell(self, i, depth=0):
        """Column i of the face; depth 1 is one block behind the wall, -1 one block in front."""
        x, z = self.cells[i]
        return (x - self.out[0] * depth, z - self.out[1] * depth)


FACES = (Face("east", 1), Face("south", 2), Face("west", 3), Face("north", 4))
FACE = {f.name: f for f in FACES}
LIT_TABLE = [(FRONT, f.bay, STOREY) for f in FACES if f.name in LIT_FACES]


def _mouth(face):
    """The middle of the mouth of a face's dial recess: a point in the plane of the wall face."""
    x, z = face.cell(MID)
    return (x + 0.5 + face.out[0] * 0.5, (DIAL_Y[0] + DIAL_Y[1] + 1) / 2.0, z + 0.5 + face.out[1] * 0.5)


# east (17.0, 27.5, -29.5), south (13.5, 27.5, -26.0), west (10.0, 27.5, -29.5), north (13.5, 27.5, -33.0)
DIAL_CENTRES = {f.name: _mouth(f) for f in FACES}

# --- the inside: the well of the shaft, and the way up to interiors/clockroom ---------------------------
WELL_X, WELL_Z = (X0 + 1, X1 - 1), (Z0 + 1, Z1 - 1)     # 11 .. 15 and -32 .. -28: the well, 5 x 5
WELL_Y = (FOOT, FRIEZE_Y)           # 18 .. 30: its rows, between the roof's deck (row 17, whole) and the
#                                     lookout's floor (row 31, whole); the walls round it are one block thick
ROOM_FLOOR = DIAL_Y[0] - 2.0        # 24.0: the top of the clock room's floor. The rows 24 and 25 are clear
#                                     from wall to wall: the room is walked under the backs of the dials
LADDER_AT = (X0 + 1, Z0 + 1)        # (11, -32): the well's north-west corner. Only the four corner columns
#                                     and the middle 3 x 3 run clear all the way from the deck to the room
LADDER_Y = (FOOT, int(ROOM_FLOOR) - 1)                  # 18 .. 23: the ladder's rows; the last one is the
#                                                         hatch in the room's floor
LADDER = "ladder"                   # the game's ladder: it is climbed by walking into it, without a click


def backs(face):
    """The cells the two sunk squares of a face ("east", ...) fill inside the well, without the
    origin: "field", the nine behind the slit (panelled; "glass" names the two of them that are the
    slit's glass), and "plate", the nine of iron plate behind the dial. In those six rows the well
    is its middle 3 x 3 and its four corner columns; in the others it is 5 x 5."""
    f = FACE[face]
    cells = [f.cell(i, 1) for i in ARCH]
    gx, gz = f.cell(MID, 1)
    return dict(field=[(x, y, z) for x, z in cells for y in range(FIELD_Y[0], FIELD_Y[1] + 1)],
                glass=[(gx, y, gz) for y in range(SLIT_Y[0], SLIT_Y[1] + 1)],
                plate=[(x, y, z) for x, z in cells for y in range(DIAL_Y[0], DIAL_Y[1] + 1)])


def _back(face):
    """The middle of the side a dial's plate turns to the room: a point in the well."""
    x, z = face.cell(MID, 1)
    return (x + 0.5 - face.out[0] * 0.5, (DIAL_Y[0] + DIAL_Y[1] + 1) / 2.0, z + 0.5 - face.out[1] * 0.5)


# east (15.0, 27.5, -29.5), south (13.5, 27.5, -28.0), west (12.0, 27.5, -29.5), north (13.5, 27.5, -31.0)
DIAL_BACKS = {f.name: _back(f) for f in FACES}


# --- small builders -------------------------------------------------------------------------------------
def _set(c, o, x, y, z, state):
    c.set(o[0] + x, o[1] + y, o[2] + z, state)


def _clear(c, o, x, y, z):
    c.clear(o[0] + x, o[1] + y, o[2] + z)


def _fill(c, o, cells, y, state):
    for x, z in cells:
        _set(c, o, x, y, z, state)


@functools.lru_cache(maxsize=None)
def _kit():
    """The light kit of the sky line, or None while it is not in the tree."""
    try:
        from ..sky import _lightkit
    except ImportError:
        return None
    return _lightkit


# --- the shaft --------------------------------------------------------------------------------------------
def _glass(face):
    """The glass of a face's slit. East and west are lit, and the kit says with what (a tower's
    windows are lit under every look): frosted glass while the kit is not in the tree. The other
    two are dark, so that no two neighbours are lit."""
    if face.name not in LIT_FACES:
        return B.WINDOW_DARK.block
    lit = getattr(_kit(), "window_lit", None)
    if lit is not None:
        role = lit(FRONT, face.bay, STOREY, table=LIT_TABLE)[1]
        if role in B.LIT_WINDOWS + B.DARK_WINDOWS:
            return role.block
    return B.WINDOW_FROSTED.block


def _stone(i, y):
    """The stone of column i (0 .. 6) of a face in row y: rusticated in the base and at the
    corners, where the quoin is two columns long in every other row; dressed between them."""
    edge = min(i, LAST - i)
    if y <= BASE_TOP or edge == 0 or (edge == 1 and (y - BASE_TOP) % 2 == 1):
        return QUOIN.block
    return WALL.block


def _shaft(c, o, s):
    """Base, quoins and wall; in every face the slit in its field and the dial's recess; the
    frieze and the cornice; the door to the roof walk."""
    for face in FACES:
        for i, (x, z) in enumerate(face.cells):
            for y in range(FOOT, SHAFT_TOP):
                _set(c, o, x, y, z, PANEL.block if y == FRIEZE_Y and 0 < i < LAST else _stone(i, y))
        glass = _glass(face)
        for i in ARCH:
            wx, wz = face.cell(i)
            bx, bz = face.cell(i, 1)
            # the slit's field: a square of three sunk the wall's thickness, panelled at the
            # back. The slit is its middle column (the cell in front of the glass is where the
            # light line's source stands), with an apron of one row below it
            for y in range(FIELD_Y[0], FIELD_Y[1] + 1):
                _clear(c, o, wx, y, wz)
                slit = i == MID and SLIT_Y[0] <= y <= SLIT_Y[1]
                _set(c, o, bx, y, bz, glass if slit else PANEL.block)
            # the dial's recess: a square mouth of three, the wall's thickness deep. The dial of
            # machines/clock is 2.75 blocks across and fills it; no glass and no light here
            for y in range(DIAL_Y[0], DIAL_Y[1] + 1):
                _clear(c, o, wx, y, wz)
                _set(c, o, bx, y, bz, PLATE)
    _fill(c, o, BODY, SHAFT_TOP, WALL.block)
    s.mould(BODY, SHAFT_TOP, WALL.stairs, "top")
    _door(c, o, False)


def _door(c, o, opened):
    """The door of the roof walk, in the middle of the west face. Shut, its leaf is on the inner
    side of the wall (a shut door facing west fills the east 3/16 of its cell); open, it stands
    against the south jamb, within the wall's thickness, and leaves 13/16 of the doorway."""
    x, z = FACE["west"].cell(MID)
    for y, half in ((FOOT, "lower"), (FOOT + 1, "upper")):
        _set(c, o, x, y, z, st(DOOR, facing="west", half=half, hinge="left", open="true" if opened else "false"))


def way_up(canvas, origin=(0, 0, 0)):
    """Let visitors into the tower: for interiors/clockroom, which calls this from its build().
    Until it does the tower is shut and its well empty. The door of the roof walk stands open, and
    a ladder climbs the north-west corner of the well, on the west wall, from the deck to the
    hatch in the clock room's floor (LADDER_AT, LADDER_Y). Nothing on the way is clicked: the
    map's reach is 0. Returns the ladder's cells, without the origin: the room keeps them clear."""
    _door(canvas, origin, True)
    x, z = LADDER_AT
    cells = [(x, y, z) for y in range(LADDER_Y[0], LADDER_Y[1] + 1)]
    for x, y, z in cells:
        _set(canvas, origin, x, y, z, st(LADDER, facing="east"))
    return cells


# --- the lookout and the top ------------------------------------------------------------------------------
# The roof above its eaves, ring by ring: (row, how far the ring stands from the middle column, what
# it is made of). Half-widths by the half row from y 36: 4.5 4.0 | 3.5 3.5 | 3.5 3.0 | 2.5 2.0 |
# 1.5 1.0 | 0.5 -- a kick on the eaves, an upright foot on the wall line, a shoulder, and 45 degrees
# to the finial: the four faces rise in an arc and close in a point
HELM = ((HEAD, 4, "stairs"), (HEAD + 1, 3, "block"), (HEAD + 2, 3, "stairs"), (HEAD + 3, 2, "stairs"),
        (HEAD + 4, 1, "stairs"))


def _square(reach):
    """The columns no further than `reach` from the middle column: a square of 2 * reach + 1."""
    return O.box(CX - reach, CZ - reach, CX + reach, CZ + reach)


def _top(c, o, s):
    """Square: corner piers two columns wide (the quoin and one of dressed stone) and between them
    an arch of three with a railing in its foot. The roof begins with its eaves, a copper moulding
    hung in the row of the arch heads: from the court and from the station it is the soffit that
    shows, so the green top starts where the stone ends. Returns the row of the ceiling."""
    y0, y1 = LOOKOUT
    for face in FACES:
        for i, (x, z) in enumerate(face.cells):
            for y in range(y0, y1 + 1):
                _set(c, o, x, y, z, _stone(i, y))
        for i in ARCH:
            x, z = face.cell(i)
            _set(c, o, x, y0, z, BARS)
            for y in range(y0 + 1, y1):
                _clear(c, o, x, y, z)
            # the round head, shut at the top: a slab between two stairs hung with their solid
            # quarter towards the jambs
            if i == ARCH[0]:
                head = st(WALL.stairs, facing=face.low, half="top")
            elif i == ARCH[-1]:
                head = st(WALL.stairs, facing=face.high, half="top")
            else:
                head = st(WALL.slab, type="top")
            _set(c, o, x, y1, z, head)
    # the eaves: the order's moulding over the piers, a thin shelf over the arches, so that the
    # hung stairs do not stand in front of the arch heads
    s.mould(BODY, y1, COPPER.stairs, "top")
    for face in FACES:
        for i in ARCH:
            s.put(face.cell(i, -1), y1, st(COPPER.slab, type="top"))
    _fill(c, o, INSIDE, HEAD, CEILING.block)
    for y, reach, kind in HELM:
        inner = _square(reach - 1)
        _fill(c, o, inner - INSIDE if y == HEAD else inner, y, COPPER.block)
        if kind == "block":
            _fill(c, o, _square(reach) - inner, y, COPPER.block)
        else:
            s.mould(inner, y, COPPER.stairs, "bottom")
    _set(c, o, CX, APEX, CZ, FINIAL)
    return HEAD


# --- the lamp and the light -------------------------------------------------------------------------------
def _lamp(c, o, head):
    """A caged lamp let into the middle of the lookout's ceiling, which lies in row `head`. The
    light it throws is the sky line's to place: asked for through the kit, a stand-in source while
    the kit is not in the tree."""
    if not LAMP:
        return
    _set(c, o, CX, head, CZ, st(BULB, lit="true"))
    below = (o[0] + CX, o[1] + head - 1, o[2] + CZ)
    suggest = getattr(_kit(), "suggest", None)
    if suggest is not None:
        suggest(c, below, LAMP_LEVEL, "main/tower:cage", rank=3)
    else:
        c.set(below[0], below[1], below[2], f"{B.LIGHT}[level={LAMP_LEVEL}]", keep=True)


def windows():
    """The four slit windows as main's table of windows lists a window, for the light line: front
    "tower", bay 1 east, 2 south, 3 west, 4 north, storey "shaft"; cells are the glass columns,
    inward the step from the glass into the well, y the glass's rows. Without the origin."""
    return [dict(front=FRONT, bay=f.bay, storey=STOREY, cells=[f.cell(MID, 1)], inward=f.inward, y=SLIT_Y)
            for f in FACES]


def _slit_lights(c, o):
    """Hand the slits to the light line, which puts a source into the recess of the lit ones.
    While its kit is not in the tree the same source is placed here, as a stand-in."""
    glazed = getattr(_kit(), "glazed", None)
    if glazed is not None:
        glazed(c, windows(), o, group=FRONT)
        return
    for face in FACES:
        if face.name in LIT_FACES:
            x, z = face.cell(MID)
            c.set(o[0] + x, o[1] + SLIT_Y[0], o[2] + z, f"{B.LIGHT}[level={SLIT_LIGHT}]", keep=True)


# --- the mast: display models ------------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _models():
    dark, iron = P.mat("iron_dark"), P.mat("iron")
    u = 16.0 / MAST_SCALE                               # model units to the block: 4, a quarter block each
    stop = (MAST_STOP - MAST_FOOT) * u                  # 36.0
    top = (MAST_TOP - MAST_FOOT) * u                    # 44.0
    out = CUPS_OUT * u                                  # 3.5
    on = (0.0, 0.0)                                     # the axis
    long, tail, high = VANE_LONG * u, VANE_TAIL * u, VANE_HIGH * u      # 8.0, 3.0, 3.0

    # Units from the foot upwards. Between the boot and the stop collar the pole is plain: the time
    # ball of machines/clock and its sleeves (6 px in radius) travel there.
    m = M.Model(MAST_MODEL, px=MAST_SCALE, anchor=(0.0, MAST_HOLD * u, 0.0))

    def plate(a0, a1, y0, y1):
        """An iron plate half a unit thick in the plane of the wind: from a0 to a1 downwind of the
        axis (upwind where negative), from y0 to y1."""
        wx, wz = WIND
        lo, hi = (a0, a1) if wx + wz > 0 else (-a1, -a0)
        if wx:
            m.box((lo, y0, -0.25), (hi, y1, 0.25), iron)
        else:
            m.box((-0.25, y0, lo), (0.25, y1, hi), iron)

    m.tube("y", on, 0.0, 0.5, 1.375, iron)                                  # the flange on the finial, 11 px across
    m.taper("y", on, 0.5, 2.5, 1.25, 0.875, dark, steps=2)                  # the boot
    m.tube("y", on, 2.5, stop, MAST_THICK * u / 2.0, dark)                  # the pole, 7 px
    m.tube("y", on, stop, stop + 0.75, 1.375, iron)                         # the stop collar
    m.taper("y", on, stop + 0.75, stop + 3.0, 0.875, 0.375, dark, steps=3)  # the neck
    m.tube("y", on, stop + 3.0, top, 0.375, dark, sides=4)                  # the rod, 3 px, to the tip
    # the cup wheel's bracket, upwind: an arm out of the stop collar, the spindle upright on its end
    plate(-out - 0.25, -1.0, stop + 0.125, stop + 0.625)
    plate(-out - 0.25, -out + 0.25, stop + 0.125, stop + 1.5)
    # the wind vane, downwind: a sleeve on the rod and a swallow-tailed pennant whose upper edge is
    # the mast's tip. Nothing stands above it, and the cups hang three quarters of a block below
    # it on the other side and reach less far: a flag on its pole from wherever it is seen, never
    # a cross
    m.tube("y", on, top - high - 0.25, top, 0.5, iron)
    plate(0.375, long - tail, top - high, top)
    plate(long - tail, long, top - 0.875, top)
    plate(long - tail, long, top - high, top - high + 0.875)

    # The cup wheel, in pixels about its hub: three arms, never four. It turns about y through the
    # anchor; the box round the three cups has its middle 1.5 px north of that axis.
    w = M.Model(CUPS_MODEL, px=1.0)
    w.tube("y", on, -1.5, 1.5, 1.5, dark)
    for k in range(3):
        a = math.radians(90.0 + 120.0 * k)
        ux, uz = math.cos(a), -math.sin(a)
        w.beam((ux, 0.0, uz), (5.0 * ux, 0.0, 5.0 * uz), 2.0, 2.0, iron)
        w.tube("y", (6.0 * ux, 6.0 * uz), -2.0, 2.0, 2.5, iron, sides=6)
    return {m.name: m, w.name: w}


def models():
    return dict(_models())


def _mast(c, o):
    """Stand the mast on the finial and the cup wheel on its spindle, and register the wheel with the
    motion line: it turns about its spindle. Returns the entities placed."""
    kit = _models()
    c.add_entity(o[0] + AXIS[0], o[1] + MAST_FOOT + MAST_HOLD, o[2] + AXIS[1],
                 M.display(kit[MAST_MODEL], scale=MAST_SCALE, view=FAR))
    c.add_entity(o[0] + CUPS_AT[0], o[1] + CUPS_AT[1], o[2] + CUPS_AT[2], M.display(kit[CUPS_MODEL], view=FAR))
    MK.spin(c, "y", MK.ANEMOMETER_REV)
    return 2


# --- the package ----------------------------------------------------------------------------------------------
def build(canvas, origin=(0, 0, 0)):
    """Place the clock tower on the north pavilion's deck: the shaft, the lookout under its
    four-sided roof, the mast. Returns the display entities placed: 2."""
    s = O.Laying(canvas, O.Plan(BODY), origin, None)
    _shaft(canvas, origin, s)
    head = _top(canvas, origin, s)
    _lamp(canvas, origin, head)
    _slit_lights(canvas, origin)
    return _mast(canvas, origin)


def _plan_row(c, y):
    """Row y as text, north up, with the letters of _order.mark()."""
    lines = []
    for z in range(Z0 - 2, Z1 + 3):
        row = "".join(" " if c.get(x, y, z) is None else O.mark(c.get(x, y, z)) for x in range(X0 - 2, X1 + 3))
        lines.append("z %4d  %s" % (z, row.rstrip()))
    return "\n".join(lines)


def _drawings():
    c = Canvas()
    n = build(c)
    print(f"\n=== clock tower: {len(c.b)} blocks, {n} display entities ===")
    print("\nEAST ELEVATION (seen from the court; south on the left):\n")
    print(O.elevation(c, "east", (Z0 - 2, Z1 + 2), (FOOT, APEX), X1 + 4, X0 - 1))
    print(f"\nSECTION through the middle (z = {CZ}; west on the left):\n")
    print(O.section(c, "z", CZ, (X0 - 2, X1 + 2), (FOOT, APEX)))
    for y in (LOOKOUT[0], LOOKOUT[0] + 1, LOOKOUT[1], HEAD, *range(ROOF[0], APEX)):
        print(f"\nPLAN of row y = {y} (north up):\n")
        print(_plan_row(c, y))
    way_up(c)
    print(f"\nSECTION through the ladder with the way up open (z = {LADDER_AT[1]}; west on the left):\n")
    print(O.section(c, "z", LADDER_AT[1], (X0 - 2, X1 + 2), (FOOT, SHAFT_TOP)))
    for y in (FOOT, SLIT_Y[0], int(ROOM_FLOOR), DIAL_Y[0]):
        print(f"\nPLAN of row y = {y} with the way up open (north up):\n")
        print(_plan_row(c, y))


if __name__ == "__main__":
    _drawings()
    sys.exit(0)
