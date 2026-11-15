"""Work package interiors/starhall: the fitting-out of the star hall (plan ART-PLAN 8; card
plan/packages/interiors/starhall.md).

The star hall is the first room a visitor sees: the orrery overhead, the mother clock on the pier
straight ahead, the station's emblem underfoot. The room itself is main/shell's (c231: walls, floor
slab, galleries, stairs, ceiling beams, the pier), the orrery machines/orrery's (c236), the clock
machines/clock's (c238). This package fits the room out and builds none of it:

  floor     the emblem let into the stone under the orrery (A0 #30488, #30667): an eight-sided ring
            of thin brass seven across, the meridian through it from the north wall to the south
            wall, a brass stud for the star, turned as in the court (the star's place is read from
            site/court). Brass runs north-south only; the axis is marked in stone. The ring lies on a
            band of dark slate, the field inside it is pale;
  walls     a pilaster on each cross wall under the ceiling beams on x 8 and 14 (none on x 11: there
            the meridian meets the wall, under a brass plate), an iron bracket from its head to the
            gallery's girder; the emblem a second and last time, small, over the doorway inside;
  step      the mother clock's: one course of the pier's own stone on the three cells before the
            pier's east face (DAIS; A0 #30667);
  pieces    few, each with its use, all against the cross walls. North: the switchboard by the pier
            (the hall's lamps and the orrery's motor are switched here), the display table (what the
            station keeps to show) and the visitors' desk with its book. South: the star chart, two
            benches. On the gallery, over the meridian: the two great maps of the sky, the winter
            half on the north wall and the summer half on the south. The furniture is
            props/furniture's (c179), charts and books props/paper's (c197): they are placed from
            here, each where its package is in the tree, and left out where it is not;
  lamps     caged lamps (props/lamps, the third rank): three under each gallery, one over each door
            of the gallery, and the four of the stair hall (A0 #37954: the apse beyond the west
            arcade is lit from here, it has no other fitting-out), a pair under the crowns of the
            arcade's side arches and a pair either side of the west window.

Two versions for the director to choose between (the plan is fixed; they differ in dress):
  a  "academic"  black and white squares of two by two in the aisles, stone pilasters, a dark wood
                 wainscot, a short switchboard, two benches, lamps with round glasses;
  b  "workshop"  bands of tuff along the axis, riveted iron pilasters, bare walls, a longer
                 switchboard with a row of valves, one bench and a trunk come up with the last car,
                 a blueprint beside the chart, lamps behind flat bars.

Sight lines (c220 #38744). Seen from the court, the two side arches of the entrance look down the
aisles (rows z -5, -4 and 4, 5) through the west arcade onto the first steps of the grand stair.
So nothing stands in the inner row of an aisle, and what stands in the row along the wall is no
higher than a block, the switchboard alone excepted. Seen through the middle arch (V7), the walls
show only west of x 7: the switchboard on the right, the star chart on the left.

Light (A0 #30667, c220 #30403 and #38744; cells in the room's coordinates). The orrery's sun is the
hall's one warm core; everything of this package keeps to the third rank:
    sun          (11, 7, 0)                      12   machines/orrery offers it
    clock        (7, 3, 0)                       11   machines/clock offers it
    aisles       (9, 3, -5), (9, 3, 5)            8   on the first pilaster, looking east
                 (7, 3, -5), (7, 3, 5)            7   on the same, looking west
                 (13, 3, -5), (13, 3, 5)          7   on the corner pilaster, looking west
    doors        (8, 10, -5), (8, 10, 5)          6   over the doors of the wing rooms
    switchboard  (5, 2, -4)                       5   before the pilot lamps
    stair foot   (1, 4, -4), (1, 4, 4)            8   under the crowns of the arcade's side arches
    mezzanine    (-6, 9, -2), (-6, 9, 2)          7   either side of the west window
The sources go to the light line (sky/_lightkit; the lamps hand theirs over themselves). The two of
the machines are offered from here only where nobody has put or offered one, so the hall is not
left dark in a tree without them.

    from scenes.obs.interiors import starhall
    got = starhall.dress(canvas, origin, version="a")   # dict(entities, lights, missing)

build() is what the master scene calls. It places nothing until MOVED_IN is set; main/facade and
sky/lights read the same switch (the stand-in wall behind the entrance and its three sources go when
the hall moves in). Until then the hall is seen in its test scene, build/scenes/obs_int_starhall.
"""
import importlib
import math

from artkit import models as M
from artkit.blocks import st

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..main import shell
from ..props import _kit as K
from ..props import lamps
from . import _stubs as T

NAME = "interiors/starhall"
PREFIX = "int_starhall_"
MOVED_IN = False            # the director's switch: set once a version is chosen and the pictures have passed
VERSION = "a"               # the version build() places
VERSIONS = ("a", "b")
DAIS = True                 # the step under the mother clock (A0 #30667: a switch)

# --- where things are (cells unless said otherwise; the room's coordinates are the skeleton's) ------------
ROOM = shell.ROOMS["star hall"]
X0, Z0, X1, Z1 = ROOM["box"]                    # 2, -5, 15, 5: the clear inside
FEET = ROOM["feet"]                             # 0
FLOOR = FEET - 1                                # -1: the floor block
CX, CZ = (int(math.floor(v)) for v in S.ORRERY_CENTRE)      # (11, 0): the cell under the orrery
RING_R = 3                                      # the emblem's ring is seven across
BEAM_X = tuple(range(S.PIER_ENVELOPE[2] + 1, X1 + 1, shell.BEAM_STEP))      # 8, 11, 14: the ceiling's beams
PILASTER_X = tuple(x for x in BEAM_X if x != CX)                             # 8, 14: a pilaster under each but the middle one
WALL_Z = {"north": Z0, "south": Z1}             # the row of cells along each cross wall
FACE_Z = {"north": float(Z0), "south": float(Z1 + 1)}       # points: the faces of the cross walls, -5.0 and 6.0
LOOKS = {"north": "south", "south": "north"}    # the way each of those faces looks
SIDES = (("north", -1), ("south", 1))           # a cross wall, and the step from the axis towards it
PX = 1.0 / 16.0
SKIRT = 3.0 * PX                                # the wainscot's thickness: what stands against it stands off the wall by it

# --- stone and iron ------------------------------------------------------------------------------------
PALE, DARK = shell.FLOOR, shell.FLOOR_DARK      # the shell's white square and its black one
SEAT = B.SLATE_TILE.block                       # the darkest, under the brass: as under the court's emblem
BAND = B.TUFF_BRICK.block                       # version b: the bands along the axis
WALK = B.IRON_GRATE                             # version b: the iron walk on the axis
PILASTER = {                                    # foot (the plinth's two rows), shaft, head (the row under the gallery)
    "a": dict(foot=B.SLATE_BRICK.block, shaft=B.ASHLAR_FINE.block, head=B.ASHLAR_PANEL.block),
    "b": dict(foot=B.IRON_PLATE, shaft=B.IRON_RIVETED.block, head=B.IRON_PLATE),
}
# The switchboard: an iron base, the courses of instrument panels from the bottom, an iron cap. By
# materials/panels' rules for a wall of instruments: no kind beside or over itself, no lit panel
# beside a lit one, no pale one beside a pale one. No nameplate: it carries the emblem, and the
# hall has its two.
BOARD = {
    "a": (("knife_switch", "fuses", "knife_switch"),
          ("pilot_lamps", "dial", "pilot_lamps")),
    "b": (("knife_switch", "fuses", "bus_switch", "knife_switch"),
          ("pilot_lamps", "dial", "relays", "tubes")),
}
BOARD_END = PILASTER_X[0] - 2                   # 6: its east end; the cell between it and the pilaster is that one's lamp's
BRASS = P.mat("brass")                          # the ceiling's rose and the hearts' studs
BRASS_D = P.mat("brass_dark")
ENAMEL = P.mat("enamel")                        # the hearts' faces: the palette's enamel blue, nowhere else

# --- the ceiling --------------------------------------------------------------------------------------------
# The shell lays it (c231, A0 #491): iron beams north-south only, on x 8, 11 and 14 east of the stair's
# opening, the boards between them lying half a block higher (their lower face 14.5). The hall adds two
# things, both in the cells the shell left empty:
#   the rose   a flat brass drum of radius 1.5 about the hanging point, its side running up to the
#              boards' face at 14.5 and its own face at 13.96: the orrery's seat rests on it, and the
#              0.45 of the seat that reaches past the beam has something behind it (c231 #517, #531).
#              A model, not blocks: four cells are not a round.
#   the hearts  enamel-blue plates let into the boards between the beams, in the two bands (x 9..10 and
#              12..13) and their north and south crossings; the middle crossing is the rose's (c243 #531)
ROSE_R = 1.5                                    # blocks: the drum's radius
ROSE_FACE = 13.96                              # the face the orrery's seat rests on
BOARD_Y = shell.CEIL_Y + 0.5                    # 14.5: the boards' lower face, where the drum's side ends
BOARD_X = ((9, 10), (12, 13))                   # the two bands of boards between the beams
BOARD_Z = ((-5, -3), (-1, 1), (3, 5))           # their three crossings; the middle one is the rose's
HEART_Z = (BOARD_Z[0], BOARD_Z[2])              # the north and south crossings: the four hearts
HEART_WIDE, HEART_HIGH = 2.0, 3.0               # a heart covers its whole crossing: two by three blocks

# --- the pieces (points) -----------------------------------------------------------------------------------
BAY_X = (S.mid(CX) - 1.5, S.mid(CX) + 1.5)      # 10.0, 13.0: two pieces two blocks wide, either side of the meridian
CHART_X = (X0 + PILASTER_X[0] - 0.5) / 2.0      # 4.75: the middle of the wall between the arcade and the first lamp
CHART_Y = FEET + 3.5                            # the middle of a chart, level with the lamps
MAP_Y = S.STAND + 3.5                           # 10.5: the middle of a great map, clear of the gallery's railing from below
# texels from the middle of a piece's foot to its back (props/furniture's models; the bench's leaning back)
BACK = {"display_table": 7.0, "writing_desk": 7.0, "bench": 7.25, "trunk": 6.5}
# how high a piece carries what lies on it, where props/furniture does not say (its TOP)
TOP = {"display_table": 11.25 * PX, "writing_desk": 12.0 * PX, "trunk": 11.0 * PX}

# --- light: the level asked for, and the rank where the name of the source does not tell it ------------------
ASK_SUN = (12, 2)           # the orrery's sun (c220 #38744)
ASK_CLOCK = (11, 2)         # before the mother clock's dial (A0 #37312)
ASK_AISLE = (8, 7)          # on a pilaster: the lamp that looks east, a lamp that looks west
ASK_DOOR = 6                # over a door of the gallery
ASK_BOARD = (5, 3)          # the switchboard's pilot lamps
ASK_STAIR = 8               # under a side arch of the west arcade: 7 does not show the steps (c220 #38744)
ASK_MEZZANINE = 7           # beside the west window
SUN_CELL = (CX, int(math.floor(S.ORRERY_RING_Y)), CZ)                                       # (11, 7, 0)
CLOCK_CELL = (int(S.MOTHER_CLOCK["back_x"]) + 1, int(S.MOTHER_CLOCK["y"][0]) + 2, CZ)       # (7, 3, 0)
LAMP_Y = FEET + 3.5         # the middle of a lamp on a pilaster


# --- the emblem ----------------------------------------------------------------------------------------------
def emblem():
    """The station's emblem in the floor, in cells of the room: dict(disc, ring, star, line).

    disc   every cell the emblem covers: seven by seven without its four corners;
    ring   {cell: shape}: the disc's rim, one closed line, each cell with the two sides it joins (a
           rail's shape names, north is -z);
    star   the star's cell: up and to the right when north is up, as in the court (site/court's
           STAR, brought down from its ring to this one);
    line   the meridian's cells from wall to wall, without the two where it crosses the ring."""
    disc = {(CX + dx, CZ + dz) for dx in range(-RING_R, RING_R + 1) for dz in range(-RING_R, RING_R + 1)
            if abs(dx) + abs(dz) < 2 * RING_R}
    around = [(dx, dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1) if (dx, dz) != (0, 0)]
    rim = {c for c in disc if any((c[0] + dx, c[1] + dz) not in disc for dx, dz in around)}
    sides = (("north", 0, -1), ("south", 0, 1), ("east", 1, 0), ("west", -1, 0))
    ring = {(x, z): "_".join(name for name, dx, dz in sides if (x + dx, z + dz) in rim) for x, z in rim}
    try:
        from ..site import court
        reach, star = court.RING_R, court.STAR
    except (ImportError, AttributeError):
        reach, star = 7, (3, -3)
    star = (CX + int(round(star[0] * RING_R / reach)), CZ + int(round(star[1] * RING_R / reach)))
    line = [(CX, z) for z in range(Z0, Z1 + 1) if (CX, z) not in ring]
    return dict(disc=disc, ring=ring, star=star, line=line)


def _stone(version, x, z):
    """The stone of the floor in a cell outside the emblem, or None where the shell's own stays."""
    d = abs(z - CZ)
    if version == "a":
        # The shell has laid the axis: a pale band three wide, a line of slate either side. The
        # squares beyond are laid again, counted from the meridian instead of from the entrance
        # wall, so that the brass runs on pale stone to both walls and the squares mirror about it.
        if d <= shell.CHEEK_Z:
            return None
        k = abs(x - CX)
        if k == 0:
            return PALE
        band = 0 if d > shell.CHEEK_Z + 1 else 1
        return DARK if ((k - 1) // 2 + band) % 2 else PALE
    if d == 0:
        return WALK
    if d < shell.CHEEK_Z:
        return DARK
    return BAND if d <= shell.CHEEK_Z + 1 else PALE


def _floor(canvas, origin, version, L, mark):
    """The floor of the hall east of the arcade, without the pier's footing and the joint round it."""
    ox, oy, oz = origin
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            cell = (x, z)
            if cell not in L.hall or cell in L.shaft or cell in L.seat or cell in L.joint:
                continue
            if cell in mark["ring"] or cell == mark["star"]:
                stone = SEAT
            elif cell in mark["disc"]:
                stone = PALE
            else:
                stone = _stone(version, x, z)
            if stone is None:
                continue
            canvas.set(ox + x, oy + FLOOR, oz + z, stone)
            if stone == WALK:                   # a grating shows what is under it
                canvas.set(ox + x, oy + FLOOR - 1, oz + z, DARK, keep=True)


def _emblem(canvas, origin, mark):
    """The brass, in the cells over the floor: the ring, the meridian, the star."""
    ox, oy, oz = origin
    for (x, z), shape in mark["ring"].items():
        line = st(B.BRASS_CROSS, shape="north_south") if x == CX else st(B.BRASS_LINE, shape=shape)
        canvas.set(ox + x, oy + FEET, oz + z, line)
    for x, z in mark["line"]:
        canvas.set(ox + x, oy + FEET, oz + z, st(B.BRASS_LINE, shape="north_south"))
    x, z = mark["star"]
    canvas.set(ox + x, oy + FEET, oz + z, st(B.BRASS_BUTTON, face="floor", facing="north"))


# --- walls -----------------------------------------------------------------------------------------------------
def _pilasters(canvas, origin, version):
    """A pilaster one block proud of each cross wall under the beams that have one, from the floor
    to the gallery's deck, and an iron bracket from its head to the girder the railing stands on."""
    ox, oy, oz = origin
    made = PILASTER[version]
    head = shell.DECK_Y - 1
    for x in PILASTER_X:
        for wall, s in SIDES:
            z = WALL_Z[wall]
            for y in range(FEET, head + 1):
                block = made["foot"] if y <= S.PLINTH[1] else made["head"] if y == head else made["shaft"]
                canvas.set(ox + x, oy + y, oz + z, block)
            canvas.set(ox + x, oy + head, oz + z - s, st(B.IRON_RIVETED.stairs, facing=wall, half="top"), keep=True)


def _wainscot(canvas, origin):
    """Dark panelling over the plinth's two rows of both cross walls, from the arcade to the corner
    pilaster, wherever nothing stands in the cell. It stops for the pilasters and for the meridian."""
    ox, oy, oz = origin
    for wall, _s in SIDES:
        for x in range(X0, PILASTER_X[-1]):
            if x in PILASTER_X or x == CX:
                continue
            for y in range(FEET, S.PLINTH[1] + 1):
                canvas.set(ox + x, oy + y, oz + WALL_Z[wall], T.panel(B.WAINSCOT, wall), keep=True)


def _marks(canvas, origin):
    """Where the meridian meets a wall: a brass plate over its end. And the emblem's second place in
    the hall (A0 #30488), small: the stone of the wall's inner leaf over the middle of the doorway."""
    ox, oy, oz = origin
    for wall, _s in SIDES:
        canvas.set(ox + CX, oy + FEET + 1, oz + WALL_Z[wall], T.panel(B.BRASS_HATCH, wall))
    cell = (ox + S.east_wall_x(S.CENTRE_BAYS[1]) + S.DEPTH_GLASS, oy + S.STRING, oz + CZ)
    if canvas.has(*cell) and canvas.name(*cell) != B.LIGHT:
        canvas.set(cell[0], cell[1], cell[2], B.ASHLAR_EMBLEM)


# --- the ceiling ----------------------------------------------------------------------------------------------
def _rose_model():
    """The rose at the hanging point (A0 #491, c243 #531): a flat brass drum of radius ROSE_R whose
    side runs up from ROSE_FACE to the boards' face, so nothing hangs in the air; its own face is a
    ring of moulding round a plain field, with a rivet head on every other side of the ring.
    Anchor: the middle of its face, where the orrery's seat rests. Units are texels (16 to the block),
    and the model is drawn downwards from the anchor, as a thing fixed under a ceiling."""
    m = M.Model(PREFIX + "rose")
    r = ROSE_R * 16.0                               # 24 texels: radius 1.5 blocks
    rise = (BOARD_Y - ROSE_FACE) * 16.0             # 8.6 texels: up to the boards' face
    m.tube("y", (0.0, 0.0), 0.0, rise, r - 3.0, BRASS_D, sides=16)          # the drum, to the boards
    m.tube("y", (0.0, 0.0), -2.6, 0.0, r, BRASS_D, sides=16)                # the ring, proud of the field
    m.tube("y", (0.0, 0.0), -2.2, -2.6, r - 2.0, BRASS, sides=16)           # the field, sunk behind it
    for i in range(8):                              # a rivet head, one every 45 degrees
        a = math.radians(22.5 + 45.0 * i)
        x, z = math.cos(a) * (r - 4.2), math.sin(a) * (r - 4.2)
        m.box((x - 0.9, -3.4, z - 0.9), (x + 0.9, -2.6, z + 0.9), BRASS)
    return m


def _heart_model():
    """One of the enamel-blue hearts let into the boards between the beams (c243 #493, #531): a plate
    exactly the size of its crossing, a moulding round its edge, a brass stud at each corner. Anchor:
    its middle, on the boards' face. Units are texels (16 to the block); the model is 2 by 3 blocks,
    which is the limit of 48 units a model may have in any direction, so the moulding turns in."""
    m = M.Model(PREFIX + "heart")
    w, h = HEART_WIDE * 8.0, HEART_HIGH * 8.0       # 16.0, 24.0: half the plate's width and depth
    m.box((-w, -1.0, -h), (w, 0.0, h), BRASS_D)                             # the moulding, the whole crossing
    m.box((-w + 1.5, -1.5, -h + 1.5), (w - 1.5, -1.0, h - 1.5), ENAMEL)     # the plate in it, proud
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.box((sx * (w - 2.4), -1.7, sz * (h - 2.4)),
                  (sx * (w - 0.4), -1.0, sz * (h - 0.4)), BRASS)
    return m


def _ceiling(canvas, origin, asked):
    """The hall's half of the ceiling: the rose at the hanging point, and the four enamel-blue hearts
    in the boards between the beams. The beams and the boards are the shell's (A0 #491); the hall
    lays nothing in a beam's cell, so both are read off shell.layout().beams before they go in."""
    ox, oy, oz = origin
    cx, cz = S.ORRERY_CENTRE
    L = shell.layout()
    n = 0
    if (int(math.floor(cx)), int(math.floor(cz))) not in L.beams:
        n += K.put(canvas, _rose_model(), (cx, ROSE_FACE, cz), mount="ceiling", origin=origin)
    heart = _heart_model()
    for xa, xb in BOARD_X:
        for za, zb in HEART_Z:
            cells = {(x, z) for x in range(xa, xb + 1) for z in range(za, zb + 1)}
            if cells & L.beams or cells & L.envelope:
                continue                            # the shell has a beam there: no board to fix to
            n += K.put(canvas, heart, (S.mid(xa, xb), BOARD_Y, S.mid(za, zb)), mount="ceiling",
                       origin=origin)
    return n


def _switchboard(canvas, origin, version, asked):
    """The switchboard against the north wall, west of the first pilaster, and the glow of its pilot
    lamps."""
    ox, oy, oz = origin
    rows = BOARD[version]
    wide = len(rows[0])
    x0, z = BOARD_END - wide + 1, WALL_Z["north"]
    for i in range(wide):
        canvas.set(ox + x0 + i, oy + FEET, oz + z, B.IRON_PLATE)
        for j, row in enumerate(rows):
            canvas.set(ox + x0 + i, oy + FEET + 1 + j, oz + z, st(B.PANELS[row[i]], facing=LOOKS["north"]))
        canvas.set(ox + x0 + i, oy + FEET + 1 + len(rows), oz + z, st(B.IRON_RIVETED.slab, type="bottom"))
    level, rank = ASK_BOARD
    cell = (ox + x0 + wide // 2, oy + FEET + len(rows), oz + z + 1)
    _offer(canvas, cell, level, f"{NAME}:switchboard", rank)
    asked.append((cell, level, "switchboard"))


# --- light -------------------------------------------------------------------------------------------------------
def _offer(canvas, cell, level, why, rank):
    """Hand one source to the light line (sky/_lightkit.suggest: it is placed with the rest, when
    everything stands). While that tool is not in the tree the block is put down here, never over
    another."""
    try:
        from ..sky import _lightkit
        suggest = getattr(_lightkit, "suggest", None)
    except ImportError:
        suggest = None
    if suggest is not None:
        suggest(canvas, cell, level, why, rank=rank)
    else:
        canvas.set(cell[0], cell[1], cell[2], st(B.LIGHT, level=level), keep=True)


def _lit(canvas, cell):
    """Has somebody put or offered a source in this cell, or in the one under it (where a stand-in
    for a machine puts its own)?"""
    x, y, z = cell
    cells = ((x, y, z), (x, y - 1, z))
    if any(canvas.name(*c) == B.LIGHT for c in cells):
        return True
    return any(tuple(offer[0]) in cells for offer in getattr(canvas, "light_offers", ()))


def _wall_lamp(canvas, origin, version, pos, facing, level, asked, what):
    """One caged lamp on a wall face (a point; `facing` the way the face looks). props/lamps hands
    its source over."""
    out = lamps.SPEC[f"cage_{version}"]["light"]
    asked.append((K.light_cell(pos, K.FACING[facing], out, origin), level, what))
    return lamps.place(canvas, "cage", pos, facing=facing, origin=origin, version=version, level=level)


def _soffit_lamp(canvas, origin, version, pos, yaw, level, asked, what):
    """The same lamp turned face down under a soffit (pos: the point of the soffit it is fixed to):
    its conduit, which on a wall runs up, runs level along the soffit the way `yaw` says (0 south,
    180 north) and enters the stone there. The source goes into the first free cell under the lamp:
    under an arch's crown the lamp's own cell is the crown's slab."""
    ox, oy, oz = origin
    name = f"cage_{version}"
    n = K.put(canvas, lamps.models()[lamps.PREFIX + name], pos, mount="ceiling", yaw=yaw, origin=origin,
              turns=(("x", 90.0),))
    out = lamps.SPEC[name]["light"][2]
    x, y, z = (int(math.floor(v)) for v in (pos[0] + ox, pos[1] - out + oy, pos[2] + oz))
    while canvas.has(x, y, z) and canvas.name(x, y, z) != B.LIGHT:
        y -= 1
    K.offer_lights(canvas, [((x, y, z), level)], f"props/lamps:{name}")
    asked.append(((x, y, z), level, what))
    return n


def _soffit(canvas, origin, x, z):
    """The height of the soffit over the cell (x, z) of the west arcade: the lower face of the
    crown's slab where the arches' heads are shut (facade.CROWN), else that of the cross gallery's
    deck."""
    state = canvas.get(origin[0] + x, origin[1] + shell.ARCH_Y, origin[2] + z)
    if state is not None and state.partition("[")[0] != B.LIGHT:
        return shell.ARCH_Y + 0.5
    return float(shell.DECK_Y)


def _lamps(canvas, origin, version, L, asked):
    """The lamps of the hall and of the stair hall; returns the number of display entities."""
    n = 0
    east, west = ASK_AISLE
    for wall, _s in SIDES:                      # under the galleries: on the pilasters' sides
        z = S.mid(WALL_Z[wall])
        for x, facing, level in ((PILASTER_X[0] + 1.0, "east", east), (float(PILASTER_X[0]), "west", west),
                                 (float(PILASTER_X[-1]), "west", west)):
            n += _wall_lamp(canvas, origin, version, (x, LAMP_Y, z), facing, level, asked, "aisle")
    for door in shell.doors():                  # on the galleries: over the doors of the wing rooms
        xs = [x for x, _z in door["cells"]]
        row, north = door["cells"][0][1], door["inward"][1] < 0
        pos = (S.mid(min(xs), max(xs)), door["y"][1] + 1.5, float(row + 1 if north else row))
        n += _wall_lamp(canvas, origin, version, pos, "south" if north else "north", ASK_DOOR, asked, "door")
    # the stair hall. At the foot of each flight: under the crown of the arcade's side arch, in its
    # middle, the conduit running away from the axis (c231 #38506: from the door the lamp hangs on
    # the opening's centre line, and the steps are lit evenly)
    x = S.mid(*shell.ARCADE_X)
    for z0, z1 in L.arches:
        if z0 <= shell.CZ <= z1:
            continue                            # the middle arch is the way to the west door: no lamp
        z = S.mid(z0, z1)
        under = _soffit(canvas, origin, int(math.floor(x)), int(math.floor(z)))
        yaw = K.FACING["north" if z1 < shell.CZ else "south"]
        n += _soffit_lamp(canvas, origin, version, (x, under, z), yaw, ASK_STAIR, asked, "stair foot")
    # on the mezzanine: on the two piers of wall that flank the recess of the west window
    face = min(x for x, _z in L.mezzanine) + 1.0
    for _wall, s in SIDES:
        pos = (face, S.STAND + 2.5, S.mid(s * shell.CHEEK_Z))
        n += _wall_lamp(canvas, origin, version, pos, "east", ASK_MEZZANINE, asked, "mezzanine")
    return n


def _machines(canvas, origin, asked):
    """The two sources of the machines, where nobody has put or offered one."""
    ox, oy, oz = origin
    for (x, y, z), (level, rank), what in ((SUN_CELL, ASK_SUN, "sun"), (CLOCK_CELL, ASK_CLOCK, "clock")):
        cell = (ox + x, oy + y, oz + z)
        if not _lit(canvas, cell):
            _offer(canvas, cell, level, f"{NAME}:{what}", rank)
            asked.append((cell, level, what))


# --- the pieces --------------------------------------------------------------------------------------------------
def _peer(name):
    """A module of the props line, or None while it is not in the tree."""
    full = f"{K.__package__}.{name}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as e:
        if e.name != full:
            raise
        return None


def _furnish(canvas, origin, version, missing, standins):
    """What stands and hangs in the hall; returns the number of display entities. A piece whose
    package is not in the tree, or does not have it, is named in `missing` and left out (standins:
    blocks stand in for it, for the test scene)."""
    ox, oy, oz = origin
    skirt = SKIRT if version == "a" else 0.0
    top = dict(TOP, **getattr(_peer("furniture"), "TOP", {}))
    west, east = BAY_X

    def put(x, y, z, state):
        canvas.set(ox + x, oy + y, oz + z, state)

    def stand(wall, kind):
        """z of the middle of a piece that stands with its back to a cross wall: a texel off the wainscot."""
        d = skirt + (BACK[kind] + 1.0) * PX
        return FACE_Z[wall] + d if wall == "north" else FACE_Z[wall] - d

    def cells(x, wall):
        """The two cells along the wall that a piece two blocks wide stands in, its middle at x."""
        x0 = int(math.floor(x - 1.0))
        return [(x0, WALL_Z[wall]), (x0 + 1, WALL_Z[wall])]

    def piece(family, kind, pos, stub=None, **how):
        peer = _peer(family)
        if peer is not None and kind in getattr(peer, "SPEC", ()):
            return peer.place(canvas, kind, pos, origin=origin, **how)
        missing.append(f"{family}:{kind}")
        if standins and stub is not None:
            stub()
        return 0

    def hang(kind, x, y, wall, wide, high):
        return piece("paper", kind, (x, y, FACE_Z[wall]), facing=LOOKS[wall],
                     stub=lambda: T.plate(put, x, y, wide, high, wall, WALL_Z[wall]))

    n = 0
    # north, between the pilasters: the display table and what lies in it; the visitors' desk and its book
    at = (west, float(FEET), stand("north", "display_table"))
    got = piece("furniture", "display_table", at, facing="south",
                stub=lambda: T.table(put, cells(west, "north"), FEET))
    n += got
    if got:
        n += piece("paper", "logbook_shut", (at[0], FEET + top["display_table"], at[2]), yaw=12.0)
    at = (east, float(FEET), stand("north", "writing_desk"))
    got = piece("furniture", "writing_desk", at, facing="south",
                stub=lambda: T.table(put, cells(east, "north"), FEET))
    n += got
    if got:
        n += piece("paper", "logbook", (at[0], FEET + top["writing_desk"], at[2] + PX), yaw=-6.0)
    # south, between the pilasters: where one sits and looks up at the orrery
    z = stand("south", "bench")
    n += piece("furniture", "bench", (west, float(FEET), z), facing="north",
               stub=lambda: T.bench(put, cells(west, "south"), FEET, "south"))
    if version == "a":
        n += piece("furniture", "bench", (east, float(FEET), z), facing="north",
                   stub=lambda: T.bench(put, cells(east, "south"), FEET, "south"))
    else:                                       # a trunk along the wall, a crate on the east end of its lid
        at = (east, float(FEET), stand("south", "trunk"))
        got = piece("furniture", "trunk", at, yaw=K.FACING["north"] - 5.0,
                    stub=lambda: T.box(put, cells(east, "south"), FEET))
        n += got
        if got:
            n += piece("furniture", "crate", (at[0] + 0.25, FEET + top["trunk"], at[2]), yaw=K.FACING["north"] + 6.0)
    # south, west of the first pilaster: the star chart, at the height of the eye and of the lamp beside it
    if version == "a":
        n += hang("star_chart", CHART_X, CHART_Y, "south", 2.0, 1.0)
    else:
        n += hang("star_chart", CHART_X - 1.0, CHART_Y, "south", 2.0, 1.0)
        n += hang("blueprint", CHART_X + 1.25, CHART_Y, "south", 1.5, 1.0)
    # on the galleries, over the meridian: the two halves of the sky
    n += hang("sky_map", S.mid(CX), MAP_Y, "north", 3.0, 2.0)
    n += hang("sky_map_b", S.mid(CX), MAP_Y, "south", 3.0, 2.0)
    return n


# --- the package -------------------------------------------------------------------------------------------------
def dress(canvas, origin=(0, 0, 0), version=None, standins=False):
    """Fit out the hall that stands at `origin` (main/shell, and what the machines line has hung in
    it by then). Returns dict(entities, lights, missing): the number of display entities placed, the
    sources asked for as [((x, y, z), level, what)] in scene coordinates, and the pieces left out
    because their package is not in the tree, as "family:kind".

    standins   blocks stand in for the pieces that are left out: for the test scene only."""
    version = version or VERSION
    if version not in VERSIONS:
        raise ValueError(f"{NAME}: no version {version!r} (there are {', '.join(VERSIONS)})")
    origin = tuple(int(v) for v in origin)
    ox, oy, oz = origin
    L = shell.layout()
    mark = emblem()
    asked, missing = [], []
    _floor(canvas, origin, version, L, mark)
    _emblem(canvas, origin, mark)
    if DAIS:
        for x, z in L.seat:
            canvas.set(ox + x, oy + FEET, oz + z, shell.pier_block(FEET))
    _pilasters(canvas, origin, version)
    _switchboard(canvas, origin, version, asked)
    n = _furnish(canvas, origin, version, missing, standins)
    if version == "a":
        _wainscot(canvas, origin)
    _marks(canvas, origin)
    n += _ceiling(canvas, origin, asked)
    n += _lamps(canvas, origin, version, L, asked)
    _machines(canvas, origin, asked)
    return dict(entities=n, lights=asked, missing=missing)


def models():
    """The hall's own models: the ceiling's rose and its hearts."""
    return {m.name: m for m in (_rose_model(), _heart_model())}


def build(canvas, origin=(0, 0, 0)):
    if not MOVED_IN:
        return 0
    return dress(canvas, origin, VERSION)["entities"]
