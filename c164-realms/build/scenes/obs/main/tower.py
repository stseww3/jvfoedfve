"""main/tower -- the clock tower on the north end pavilion (plan/ART-PLAN.md 5.3, plan/parts/main.md
6.2, card plan/packages/main/tower.md; the director's four points on the first version, group #265).

The pavilion's walls and parapet (y 0..17) are main/facade.py, its roof deck at y 17 is the roof
package's. This is what stands on the deck, on the skeleton's footprint CLOCK_SHAFT_X/Z and to its
heights CLOCK_SHAFT_TOP, CLOCK_TOP and CLOCK_BALL_MAST:

    y 18..30   the shaft: 7 x 7, hollow, flush on all four faces from foot to cornice. Three rows
               of rusticated base, dressed stone above them between rusticated quoins that run
               unbroken to the cornice. Every face has a slit window (y 22..23) and the recess
               of a clock dial (y 26..28): three wide, three high, one deep, backed with dark
               iron plate. An iron door in the west face opens on the roof walk.
    y 31       the shaft's one cornice: the main order's moulding, in stone
    y 32..36   the lookout, as wide as the shaft and open on all four sides
    y 37..41   the verdigris top, the building's third green top beside the two domes
    y 42..53   the mast of the time ball, the cup anemometer and the wind vane at its head

The lookout and the top come in two versions (VERSION, or build(version=...)):

    a   four arches of three columns between corner piers, a round head to each, under a
        four-sided copper roof that starts upright and closes at 45 degrees to a point;
    b   an octagonal kiosk of eight free piers inside the square of the shaft, a stub pinnacle
        on each of the shaft's corners, under an octagonal copper dome with a flat crown.

Not here: the dials, their hands and the time ball are machines/clock, which finds the recesses and
the mast by itself (DIAL_CENTRES and MAST_MODEL say where they are); the antenna and its insulators
are machines/radiomast (ANTENNA_ANCHOR is the end of the bracket it hangs on); the light of the lit
slits and of the lookout's lamp is placed by sky/lights (windows(), and the kit's suggest()).

The mast is two display models, the only ones of the main line: bld_tower_mast, the pole with all
that is fixed to it, and bld_tower_cups, the cup wheel, a piece of its own so that the motion line
can turn it about its spindle. build() returns 2.

    python -m scenes.obs.main.tower            # both versions as text: elevation, section, plans
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
from . import _order as O

# --- the footprint (skeleton, LOCKED): 7 x 7, the east face flush with the pavilion's wall ----------
X0, X1 = S.CLOCK_SHAFT_X            # 10 .. 16
Z0, Z1 = S.CLOCK_SHAFT_Z            # -33 .. -27
CX, CZ = (X0 + X1) // 2, (Z0 + Z1) // 2         # 13, -30: the middle column
AXIS = (CX + 0.5, CZ + 0.5)         # (13.5, -29.5): the tower's axis, a point
BODY = O.box(X0, Z0, X1, Z1)        # the 49 columns of the shaft
INSIDE = O.shrink(BODY)             # the well, 5 x 5
WALLS = BODY - INSIDE               # the 24 columns of the wall
CORNERS = {(X0, Z0), (X1, Z0), (X0, Z1), (X1, Z1)}
MID = 3                             # the middle one of a face's seven columns, counted 0 .. 6
ARCH = (2, 3, 4)                    # the three columns of a dial recess and of a lookout arch

# --- the rows -----------------------------------------------------------------------------------------
FOOT = S.ROOF_STAND                 # 18: the first row on the pavilion's deck
BASE_TOP = 20                       # the last row of the rusticated base
SLIT_Y = (22, 23)                   # the slit windows
DIAL_Y = (26, 28)                   # the dial recesses
SHAFT_TOP = S.CLOCK_SHAFT_TOP       # 31: the cornice row, and the floor of the lookout
LOOKOUT = (32, 35)                  # its open rows
HEAD = 36                           # its ceiling
ROOF = (37, S.CLOCK_TOP)            # 37 .. 41 (version a starts its copper one row lower, on the eaves)
APEX = S.CLOCK_TOP                  # 41: the finial block

# --- the mast (points, in blocks) ---------------------------------------------------------------------
MAST_MODEL = "bld_tower_mast"       # machines/clock looks for a display of this model: the mast stands
CUPS_MODEL = "bld_tower_cups"
CUPS_TAG = "c164_tower_cups"        # the cup wheel's own tag, for the motion line
MAST_FOOT = APEX + 1.0              # 42.0: the top of the finial
MAST_STOP = S.CLOCK_BALL_MAST - 1.0  # 51.0: up to here the pole is plain and the ball's to travel on
MAST_TOP = S.CLOCK_BALL_MAST + 1.0  # 53.0: the tip, the top of the skeleton's last row
MAST_THICK = 7 / 16.0               # the pole between its boot and the stop collar
MAST_SCALE = 4.0                    # the model is shown at four times its size: 11 blocks are 44 units
MAST_HOLD = 0.5                     # the entity stands this far above the foot: in the air over the finial
CUPS_OUT = 0.875                    # the cup wheel's spindle stands this far north of the axis
CUPS_AT = (AXIS[0], MAST_STOP + 0.4375, AXIS[1] - CUPS_OUT)     # (13.5, 51.4375, -30.375): its hub
FAR = 4.0                           # view_range, as machines/clock gives the dials and the ball

# --- the antenna's bracket ----------------------------------------------------------------------------
HOOK_Y = SHAFT_TOP - 1              # 30: under the cornice
HOOK_REACH = 2                      # blocks of rod north of the north face, out of the north-east quoin
ANTENNA_ANCHOR = (X1 + 0.5, HOOK_Y + 0.5, float(Z0 - HOOK_REACH))       # (16.5, 30.5, -35.0): its end

# --- light --------------------------------------------------------------------------------------------
FRONT, STOREY = "tower", "shaft"    # the slits' keys for the light line; the bay is the face's number
LIT_FACES = ("east", "west")        # the slits that are lit: opposite faces, never two neighbours
SLIT_LIGHT = 7                      # the stand-in source of a lit slit: what sky/lights places (9 - 2)
LAMP = True                         # a caged lamp let into the lookout's ceiling
LAMP_LEVEL = 7                      # the fill it asks the light line for (rank 3)

# --- materials: roles of the occupancy table ------------------------------------------------------------
WALL = B.ASHLAR_FINE
QUOIN = B.ASHLAR_ROUGH              # quoins and base; the corner pinnacles of version b
PLATE = B.IRON_PLATE                # the back of the dial recesses
BARS = B.IRON_BARS                  # the railing in the arches of version a
CEILING = B.IRON_RIVETED
DOOR, ROD, BULB = B.IRON_DOOR, B.IRON_ROD, B.IRON_BULB
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


def _cut_square(reach, most):
    """The columns no further than `reach` from the middle column along x and along z, without
    those whose two distances add up to more than `most`: a square with its corners cut."""
    return {(CX + dx, CZ + dz) for dx in range(-reach, reach + 1) for dz in range(-reach, reach + 1)
            if abs(dx) + abs(dz) <= most}


# --- the plan of version b ------------------------------------------------------------------------------
OCT = _cut_square(3, 4)             # 37 columns: the kiosk, inside the square of the shaft
OCT_IN = _cut_square(2, 3)          # 21: its floor
OCT_WALL = OCT - OCT_IN             # 16: three to a side on the axes, one on each diagonal
OCT_PIERS = {(x, z) for x, z in OCT_WALL if sorted((abs(x - CX), abs(z - CZ))) == [1, 3]}       # 8
OCT_DIAG = {(x, z) for x, z in OCT_WALL if abs(x - CX) == abs(z - CZ)}                          # 4
CROWN = O.box(CX - 1, CZ - 1, CX + 1, CZ + 1)                                                   # 3 x 3


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


def _shaft(c, o, s):
    """Base, quoins and wall; in every face the slit and the dial's recess; the cornice; the door
    to the roof walk and the antenna's bracket."""
    for x, z in WALLS:
        quoin = (x, z) in CORNERS
        for y in range(FOOT, SHAFT_TOP):
            _set(c, o, x, y, z, (QUOIN if quoin or y <= BASE_TOP else WALL).block)
    for face in FACES:
        # the slit: the wall column is cut out (the recess the light line's source stands in), the
        # glass stands one block behind it
        glass = _glass(face)
        wx, wz = face.cell(MID)
        gx, gz = face.cell(MID, 1)
        for y in range(SLIT_Y[0], SLIT_Y[1] + 1):
            _clear(c, o, wx, y, wz)
            _set(c, o, gx, y, gz, glass)
        # the dial's recess: a square mouth of three, the wall's thickness deep. The dial of
        # machines/clock is 2.75 blocks across and fills it; no glass and no light here
        for i in ARCH:
            wx, wz = face.cell(i)
            bx, bz = face.cell(i, 1)
            for y in range(DIAL_Y[0], DIAL_Y[1] + 1):
                _clear(c, o, wx, y, wz)
                _set(c, o, bx, y, bz, PLATE)
    _fill(c, o, BODY, SHAFT_TOP, WALL.block)
    s.mould(BODY, SHAFT_TOP, WALL.stairs, "top")
    # the door of the roof walk, in the middle of the west face: shut, the leaf on the inner side
    # of the wall (a shut door facing west fills the east 3/16 of its cell)
    x, z = FACE["west"].cell(MID)
    for y, half in ((FOOT, "lower"), (FOOT + 1, "upper")):
        _set(c, o, x, y, z, st(DOOR, facing="west", half=half, hinge="left", open="false"))
    # the bracket of the antenna: an iron rod out of the north-east quoin, under the cornice
    north = FACE["north"]
    for n in range(1, HOOK_REACH + 1):
        x, z = north.cell(len(north.cells) - 1, -n)
        _set(c, o, x, HOOK_Y, z, st(ROD, facing="north"))


# --- the lookout and the top: version a ---------------------------------------------------------------------
def _top_a(c, o, s):
    """Square: corner piers two columns wide (the quoin and one of dressed stone) and between them
    an arch of three with a railing in its foot. The eaves hang in the row of the arch heads; over
    them an upright copper band and four slopes of 45 degrees to the finial."""
    y0, y1 = LOOKOUT
    for x, z in WALLS:
        stone = (QUOIN if (x, z) in CORNERS else WALL).block
        for y in range(y0, y1 + 1):
            _set(c, o, x, y, z, stone)
    for face in FACES:
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
    s.mould(BODY, y1, WALL.stairs, "top")
    for face in FACES:
        for i in ARCH:
            s.put(face.cell(i, -1), y1, st(WALL.slab, type="top"))
    _fill(c, o, WALLS, HEAD, WALL.block)
    _fill(c, o, INSIDE, HEAD, CEILING.block)
    _fill(c, o, O.ring(BODY), HEAD, COPPER.block)       # the upright band, on the eaves
    body = set(BODY)
    for y in range(ROOF[0], APEX):                      # 37 .. 40: a ring of stairs to the row, each ring one further in
        _fill(c, o, body, y, COPPER.block)
        s.mould(body, y, COPPER.stairs, "bottom")
        body = O.shrink(body)
    _set(c, o, CX, APEX, CZ, FINIAL)


# --- the lookout and the top: version b ---------------------------------------------------------------------
def _top_b(c, o, s):
    """Octagonal: a low parapet, eight free piers (the slots between them one column wide and three
    rows high, so the sky shows through the kiosk), on each corner of the shaft a pedestal with a
    stub of a pinnacle. The eaves follow the octagon; over them an upright copper band, two rings
    of stairs and a flat crown under the finial."""
    y0, y1 = LOOKOUT
    _fill(c, o, OCT_WALL, y0, WALL.block)
    for x, z in CORNERS:
        _set(c, o, x, y0, z, QUOIN.block)
        _set(c, o, x, y0 + 1, z, QUOIN.wall)
    for y in range(y0 + 1, y1 + 1):
        _fill(c, o, OCT_PIERS, y, WALL.block)
    _fill(c, o, OCT_WALL, HEAD, WALL.block)
    _fill(c, o, OCT_IN, HEAD, CEILING.block)
    s.mould(OCT, HEAD, WALL.stairs, "top")
    y = ROOF[0]
    _fill(c, o, OCT, y, COPPER.block)                   # 37: the upright band
    _fill(c, o, O.ring(OCT), y, COPPER.block)
    _fill(c, o, OCT, y + 1, COPPER.block)               # 38: the first slope, round the kiosk
    s.mould(OCT, y + 1, COPPER.stairs, "bottom")
    # 39: the second slope, on the kiosk's wall line. Its four diagonal columns are whole blocks:
    # a stair there would have to be an inner corner, and no state can ask for one
    _fill(c, o, OCT_IN | OCT_DIAG, y + 2, COPPER.block)
    for x, z in OCT_WALL - OCT_DIAG:
        dx, dz = x - CX, z - CZ
        if abs(dx) == 3:
            to = "west" if dx > 0 else "east"
        else:
            to = "north" if dz > 0 else "south"
        _set(c, o, x, y + 2, z, st(COPPER.stairs, facing=to, half="bottom"))
    _fill(c, o, OCT_IN - CROWN, y + 3, st(COPPER.slab, type="bottom"))     # 40: the dome flattens
    _fill(c, o, CROWN, y + 3, COPPER.block)
    _set(c, o, CX, APEX, CZ, FINIAL)


TOPS = {"a": _top_a, "b": _top_b}
VERSION = "a"                       # what the master scene shows until the director has picked one


# --- the lamp and the light -------------------------------------------------------------------------------
def _lamp(c, o):
    """A caged lamp let into the middle of the lookout's ceiling. The light it throws is the sky
    line's to place: asked for through the kit, a stand-in source while the kit is not in the tree."""
    if not LAMP:
        return
    _set(c, o, CX, HEAD, CZ, st(BULB, lit="true"))
    below = (o[0] + CX, o[1] + HEAD - 1, o[2] + CZ)
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

    # Units from the foot upwards. Between the boot and the stop collar the pole is plain: the time
    # ball of machines/clock and its sleeves (6 px in radius) travel there.
    m = M.Model(MAST_MODEL, px=MAST_SCALE, anchor=(0.0, MAST_HOLD * u, 0.0))
    m.tube("y", on, 0.0, 0.5, 1.375, iron)                                  # the flange on the finial, 11 px across
    m.taper("y", on, 0.5, 2.5, 1.25, 0.875, dark, steps=2)                  # the boot
    m.tube("y", on, 2.5, stop, MAST_THICK * u / 2.0, dark)                  # the pole, 7 px
    m.tube("y", on, stop, stop + 0.75, 1.375, iron)                         # the stop collar
    m.taper("y", on, stop + 0.75, stop + 3.0, 0.875, 0.375, dark, steps=3)  # the neck
    m.tube("y", on, stop + 3.0, stop + 6.0, 0.375, dark, sides=4)           # the rod, 3 px
    m.taper("y", on, stop + 6.0, top, 0.375, 0.25, dark, sides=4, steps=2)  # the tip, 2 px at the end
    # the cup wheel's bracket, north: an arm out of the stop collar, the spindle upright on its end
    m.box((-0.25, stop + 0.125, -out - 0.25), (0.25, stop + 0.625, -1.0), iron)
    m.box((-0.25, stop + 0.125, -out - 0.25), (0.25, stop + 1.5, -out + 0.25), iron)
    # the wind vane, south and three quarters of a block higher: a sleeve on the rod and a
    # swallow-tailed flag. Arm and flag stand on opposite sides at different heights: no cross
    m.tube("y", on, stop + 3.25, stop + 6.25, 0.5, iron)
    m.box((-0.25, stop + 3.5, 0.375), (0.25, stop + 6.0, 3.5), iron)
    m.box((-0.25, stop + 5.25, 3.5), (0.25, stop + 6.0, 5.5), iron)
    m.box((-0.25, stop + 3.5, 3.5), (0.25, stop + 4.25, 5.5), iron)

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
    """Stand the mast on the finial and the cup wheel on its spindle. Returns the entities placed."""
    kit = _models()
    c.add_entity(o[0] + AXIS[0], o[1] + MAST_FOOT + MAST_HOLD, o[2] + AXIS[1],
                 M.display(kit[MAST_MODEL], scale=MAST_SCALE, view=FAR))
    cups = M.display(kit[CUPS_MODEL], view=FAR)
    cups["Tags"].append(CUPS_TAG)
    c.add_entity(o[0] + CUPS_AT[0], o[1] + CUPS_AT[1], o[2] + CUPS_AT[2], cups)
    return 2


# --- the package ----------------------------------------------------------------------------------------------
def build(canvas, origin=(0, 0, 0), version=None):
    """Place the clock tower on the north pavilion's deck. `version` picks the lookout and the top
    (a: arches under a four-sided roof, b: an octagonal kiosk under a dome; VERSION when left out);
    the shaft and the mast are the same for both. Returns the display entities placed: 2."""
    s = O.Laying(canvas, O.Plan(BODY), origin, None)
    _shaft(canvas, origin, s)
    TOPS[version or VERSION](canvas, origin, s)
    _lamp(canvas, origin)
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
    for version in ("a", "b"):
        c = Canvas()
        n = build(c, version=version)
        print(f"\n=== clock tower, version {version}: {len(c.b)} blocks, {n} display entities ===")
        print("\nEAST ELEVATION (seen from the court; south on the left):\n")
        print(O.elevation(c, "east", (Z0 - 2, Z1 + 2), (FOOT, APEX), X1 + 4, X0 - 1))
        print(f"\nSECTION through the middle (z = {CZ}; west on the left):\n")
        print(O.section(c, "z", CZ, (X0 - 2, X1 + 2), (FOOT, APEX)))
        for y in (LOOKOUT[0], LOOKOUT[0] + 1, HEAD, ROOF[0], ROOF[0] + 1, ROOF[0] + 2, ROOF[0] + 3):
            print(f"\nPLAN of row y = {y} (north up):\n")
            print(_plan_row(c, y))


if __name__ == "__main__":
    _drawings()
    sys.exit(0)
