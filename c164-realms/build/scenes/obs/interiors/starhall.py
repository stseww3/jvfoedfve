"""interiors/starhall -- the star hall, the entrance hall in the middle of the main building (plan
ART-PLAN 8, card plan/packages/interiors/starhall.md), and the lamps of the stair hall behind it.

What stands there is not this package's: the walls, the inner leaf with its three arches and the
great windows over them (main/facade), the floor, the galleries, the telescope pier and its ring
stair, the west arcade, the beams and boards of the ceiling (main/shell), the orrery and the mother
clock (machines). The hall dresses the room they leave, and reads it from them: the room's box from
shell.ROOMS, the beams from shell.layout().beams, the clock's seat from shell.layout().seat, the
doorway from facade.doors().

The first look (S.V7, from outside the door through the middle arch): the orrery overhead, the
mother clock on the pier straight ahead, the floor underfoot. The hall keeps that picture clear:
nothing of its own stands on the axis, its lamps are small and stay under the galleries, and the
only warm core is the orrery's sun.

  floor     The hall lays its own from wall to wall round the pier's foot (the shell's shows in
            the stair hall only). The station's emblem under the orrery, in thin brass line: an
            octagonal ring seven across on a dark band, the meridian through it from pilaster to
            pilaster (x 11, north to south), the star inside the ring on its upper right. Brass
            runs north-south only and the nave is one stone, so the floor shows no cross.
  ceiling   Nothing is added to the beams, which run north-south only. Where the orrery hangs, a
            flat round boss packs the gap between the boards and the beam's lower face.
  walls     A pilaster under every beam along both aisles, a dado between them (a), the
            switchboard in the north aisle, charts and a globe in the south one.
  emblem    Twice and no more: in the floor, and one carved block over the doorway on the inside.
  light     Every source is offered to the light line (sky/_lightkit); no light block is set here.
            The sun and the clock offer their own (machines). Caged lamps of the third rank on the
            pilasters, over the two wing doors, at the two stair feet and on the mezzanine.

Two versions to choose between; the plan is locked, so they differ in dress:
  a  "academy"   a pale stone nave, the chequer withdrawn under the galleries and mirrored about
                 the meridian, stone pilasters, a dark wainscot, a wooden boss ringed in brass,
                 blue panels with brass stars in the boards round it, benches and display tables.
  b  "workshop"  polished tuff down the nave, an iron duct cover under each gallery's edge, a
                 grating inside the door, riveted stanchions, an iron boss, drafting table, desk,
                 cabinets and cases.

build() is what the master scene calls. MOVED_IN tells main/facade that the hall is fitted out:
its stand-in wall behind the entrance and that wall's lights go (facade.furnished()).
"""
import functools
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
from ..sky import _lightkit as L

ORDER = 80                  # after the shells (main/shell is 60) and whatever else stands in the hall
MOVED_IN = True             # read by main/facade.furnished(): the hall stands in the shell
VERSION = "a"               # the version build() dresses; the review picks one and only this changes
VERSIONS = ("a", "b")
PREFIX = "int_starhall_"
WHY = "interiors/starhall"

ROOM = shell.ROOMS["star hall"]
X0, Z0, X1, Z1 = ROOM["box"]                    # 2, -5, 15, 5: the clear inside
FEET = ROOM["feet"]                             # 0: where one stands
FLOOR_Y = FEET - 1
CEIL = ROOM["ceiling"]                          # 14: the beams' lower face; the boards lie half a block up
CX, CZ = (int(math.floor(v)) for v in S.ORRERY_CENTRE)      # 11, 0: the cell under the orrery

ROUNDEL_R = 3               # the ring is seven across (A0 #369)
BOSS_R = 1.5                # blocks
BOSS_DROP = 0.04            # the boss's face lies this far under the beam's, so the beam does not cut it in two
BOARDS_UP = 0.5             # the boards' lower face above the beams'
CEILING_LIGHT = 9           # the level the panels in the boards are shown at: the sun's light thins to
#                             nothing on the way up, and a face that looks down is drawn at half

# light: the hierarchy the director set (sun 12 and clock 11 are offered by the machines)
AISLE_LEVELS = (7, 8, 7)    # the three pilaster lamps of an aisle, from the pier to the door
AISLE_LAMP_Y = 3.5
GALLERY_LEVELS = (7, 6, 6)  # the three lamps of a gallery wall, from its west end to the meridian
GALLERY_LAMP_Y = 10.5
BOARD_LEVEL = 5
SUN_POOL = None             # asked of A0: a source of this level a cell over the roundel's middle, where the
#                             sun's light lands (the game's light thins by the cell and the sun hangs seven up)
STAIR_FOOT_LEVEL = 8        # 7 shows nothing of the risers through the side arches (lights, #559)
MEZZANINE_LEVEL = 7
MEZZANINE_LAMP_Y = 9.5

SIDES = {(0, -1): "north", (0, 1): "south", (-1, 0): "west", (1, 0): "east"}
ACROSS = {"north": "south", "south": "north", "west": "east", "east": "west"}
SHAPES = {frozenset(pair): "_".join(pair) for pair in (("north", "south"), ("east", "west"), ("south", "east"),
                                                         ("south", "west"), ("north", "west"), ("north", "east"))}

# the switchboard, bottom row first. No nameplate: it carries the emblem, and the hall shows that twice
BOARD_A = (("fuses", "louvre", "fuses"),
           ("knife_switch", "dial", "knife_switch"),
           ("gauges", "pilot_lamps", "gauges"))
BOARD_B = (("fuses", "louvre", "drawers", "louvre", "fuses"),
           ("knife_switch", "relays", "bus_switch", "relays", "knife_switch"),
           ("gauges", "pilot_lamps", "counter", "pilot_lamps", "gauges"))
BOARD_MID_X = 5             # the board is centred on this column of the north aisle; its lamp stands before it

STYLE = {
    "a": dict(
        band=B.SLATE_SMOOTH.block, field=B.ASHLAR_FINE.block,
        base=B.SLATE_BRICK.block, shaft=B.ASHLAR_FINE.block, capital=B.ASHLAR_PANEL.block,
        corbel=B.ASHLAR_FINE.stairs, dado=True, coffers=True, board=BOARD_A,
        furniture=(("bench", (10.0, 5.45), "north"), ("bench", (13.0, 5.45), "north"),
                   ("display_table", (10.0, -4.36), "south"), ("display_table", (13.0, -4.36), "south"),
                   ("coat_stand", (15.5, 5.3), "north")),
    ),
    "b": dict(
        band=B.SLATE_SMOOTH.block, field=B.TUFF_SMOOTH.block,
        base=B.IRON_RIVETED.block, shaft=B.IRON_RIVETED.block, capital=B.IRON_RIVETED.block,
        corbel=B.IRON_RIVETED.stairs, dado=False, coffers=False, board=BOARD_B,
        furniture=(("drafting_table", (10.0, 5.45), "north"), ("stool", (10.0, 4.3), "south"),
                   ("writing_desk", (13.0, 5.53), "north"), ("swivel_chair", (13.0, 4.5), "south"),
                   ("card_cabinet", (9.5, -4.57), "south"), ("instrument_cabinet", (10.5, -4.57), "south"),
                   ("crate", (12.6, -4.5), "south"), ("trunk", (15.3, -4.6), "east"),
                   ("coat_stand", (15.5, 5.3), "north")),
    ),
}

WOOD = P.mat("dark_wood")
WOOD_D = P.mat("dark_wood", base=1)
NIGHT = P.mat("night_glass", base=2)


# ---- what the shell tells -----------------------------------------------------------------------------
def beam_xs():
    """x of the beams that cross the hall east of the pier's opening, the curb's east side with
    them: 8, 11, 14. A pilaster stands under each."""
    lay = shell.layout()
    edge = max(x for x, _ in lay.curb)
    return sorted({x for x, z in lay.beams if z == CZ and edge <= x <= X1})


def floor_cells():
    """The cells of the floor the hall may lay: its box, less the pier and the grating and the
    clock's seat round its foot, which are the shell's."""
    lay = shell.layout()
    foot = set(lay.joint) | set(lay.shaft) | set(lay.seat)
    return [(x, z) for x in range(X0, X1 + 1) for z in range(Z0, Z1 + 1) if (x, z) not in foot]


def doorway():
    """The main doorway as the facade built it: (x of the inner leaf, z of its middle column, its top
    row), or None when the facade tells no doorway."""
    from ..main import facade
    for d in (facade.doors() if hasattr(facade, "doors") else ()):
        if d["front"] == "east" and d["kind"] == "door":
            (x, z), (dx, dz) = d["cells"][len(d["cells"]) // 2], d["inward"]
            return x + dx, z + dz, d["y"][1]
    return None


def _optional(name):
    """A package of another line that may not be in the tree yet, or None."""
    try:
        return importlib.import_module(f"{__package__.rpartition('.')[0]}.{name}")
    except ImportError:
        return None


# ---- the brass line (the rules of materials/brass_oldcopper_small, shown in obs_mat_brass) ----------------
def _line(cells, closed=False):
    """The thin brass line along a path of cells that touch by their sides: {(x, z): state}."""
    out = {}
    for i, (x, z) in enumerate(cells):
        sides = set()
        for j in (i - 1, i + 1):
            if closed or 0 <= j < len(cells):
                other = cells[j % len(cells)]
                sides.add(SIDES[(other[0] - x, other[1] - z)])
        if len(sides) == 1:
            sides.add(ACROSS[min(sides)])
        out[(x, z)] = st(B.BRASS_LINE, shape=SHAPES[frozenset(sides)])
    return out


def _octagon(r):
    """A ring of radius r about (0, 0) as a closed path: a straight run across each axis and, between
    two runs, steps sideways and onwards by turns, which the line's corners draw as one slant."""
    h = max(0, round(r * math.tan(math.pi / 8) - 0.5))
    quarter = [(r, z) for z in range(h + 2)]
    x, z = r, h + 1
    while (x, z) != (h + 1, r):
        x -= 1
        quarter.append((x, z))
        z += 1
        quarter.append((x, z))
    quarter += [(x, r) for x in range(h, 0, -1)]
    cells = []
    for _ in range(4):
        cells += quarter
        quarter = [(-z, x) for x, z in quarter]
    return cells


def roundel():
    """The emblem's ring about the cell under the orrery: (path, cells inside it), both in scene
    cells (x, z)."""
    path = [(CX + dx, CZ + dz) for dx, dz in _octagon(ROUNDEL_R)]
    ring = set(path)
    inside = set()
    for z in {z for _, z in ring}:
        xs = [x for x, rz in ring if rz == z]
        inside |= {(x, z) for x in range(min(xs) + 1, max(xs)) if (x, z) not in ring}
    return path, inside


def star_at():
    """Where the emblem's star lies: inside the ring on its upper right when north is up, as far
    east of the middle as north of it, 0.4 of the radius (the standard figure; the court's is the
    same)."""
    d = max(1, round(0.4 * ROUNDEL_R))
    return CX + d, CZ - d


# ---- the floor --------------------------------------------------------------------------------------------
def _dark_square(x):
    """The aisles' chequer, squares two by two, mirrored about the meridian: under it a pale panel
    three wide, then dark and pale by turns. True where the square is dark. The pilasters beside
    the meridian's (x 8 and 14) stand on dark squares, which meet the ring at its four slants."""
    k = abs(x - CX)
    return k > 1 and ((k - 2) // 2) % 2 == 0


def _lay_a(x, z):
    """a: the nave one pale stone from gallery to gallery, the chequer under the galleries."""
    if abs(z - CZ) <= ROUNDEL_R or not _dark_square(x):
        return B.ASHLAR_FINE.block, None
    return B.SLATE_SMOOTH.block, None


def _lay_b(x, z):
    """b: everything runs along the axis. Polished tuff down the nave, an iron duct cover under the
    edge of each gallery, brick-laid tuff under the galleries; inside the door a grating three wide
    over the copper main, the only stretch of the axis the roundel does not lie on."""
    d = abs(z - CZ)
    if d <= 1 and x > CX + ROUNDEL_R:
        return B.IRON_GRATE, B.OLD_COPPER
    if d <= ROUNDEL_R:
        return B.TUFF_SMOOTH.block, None
    if d == ROUNDEL_R + 1:
        return B.IRON_RIVETED.block, None
    return B.TUFF_BRICK.block, None


LAY = {"a": _lay_a, "b": _lay_b}


def _floor(canvas, origin, version, style):
    """The hall's own floor over the shell's, from wall to wall round the pier's foot: the version's
    stones, the roundel (a dark band under the ring, the field inside it plain), and the brass."""
    ox, oy, oz = origin
    put = lambda x, y, z, state: canvas.set(ox + x, oy + y, oz + z, state)
    path, inside = roundel()
    ring = set(path)
    for x, z in floor_cells():
        state, under = LAY[version](x, z)
        if (x, z) in ring:
            state, under = style["band"], None
        elif (x, z) in inside:
            state, under = style["field"], None
        put(x, FLOOR_Y, z, state)
        if under is not None:
            put(x, FLOOR_Y - 1, z, under)
    # the line lies on whole blocks only: the ring, the meridian through it, a crossing where they meet
    for (x, z), state in _line(path, closed=True).items():
        put(x, FEET, z, st(B.BRASS_CROSS, shape="north_south") if x == CX else state)
    for z in range(Z0 + 1, Z1):
        if (CX, z) not in ring:
            put(CX, FEET, z, st(B.BRASS_LINE, shape="north_south"))
    sx, sz = star_at()
    n = K.put(canvas, _models()[PREFIX + "star"], (sx + 0.5, FEET + 0.005, sz + 0.5), origin=origin)
    if SUN_POOL:
        L.suggest(canvas, (ox + CX, oy + FEET + 1, oz + CZ), SUN_POOL, f"{WHY}:the sun's pool", rank=L.rank(SUN_POOL))
    return n


def _plinth(canvas, origin):
    """The mother clock's plinth on the seat the shell leaves before the pier: three wide at the
    floor, two at the top, where the case stands."""
    ox, oy, oz = origin
    seat = sorted(shell.layout().seat)
    mid = seat[len(seat) // 2]
    for x, z in seat:
        if (x, z) == mid:
            state = B.SLATE_BRICK.block
        else:
            state = st(B.SLATE_BRICK.stairs, facing="south" if z < mid[1] else "north", half="bottom")
        canvas.set(ox + x, oy + FEET, oz + z, state)


# ---- the walls ----------------------------------------------------------------------------------------------
def _cove(canvas, origin):
    """The cove under the galleries runs on to the entrance wall: the shell's stops two cells short
    of it, where the corner linings stood."""
    ox, oy, oz = origin
    y = shell.DECK_Y - 1
    for z in (Z0, Z1):
        states = [canvas.get(ox + x, oy + y, oz + z) for x in range(X0, X1 + 1)]
        like = next((s for s in states if s is not None), None)
        if like is None:
            continue
        for x in range(X0, X1 + 1):
            if not canvas.has(ox + x, oy + y, oz + z) and canvas.has(ox + x, oy + y + 1, oz + z):
                canvas.set(ox + x, oy + y, oz + z, like)


def _pilasters(canvas, origin, style):
    """A pilaster under every beam, against both aisle walls, up to the cove under the gallery."""
    ox, oy, oz = origin
    for x in beam_xs():
        for z in (Z0, Z1):
            ys = []
            for y in range(FEET, shell.DECK_Y - 1):
                if canvas.has(ox + x, oy + y, oz + z):
                    break
                ys.append(y)
            for y in ys:
                state = style["base"] if y < FEET + 2 else style["capital"] if y == ys[-1] else style["shaft"]
                canvas.set(ox + x, oy + y, oz + z, state)


def _corbels(canvas, origin, style):
    """Under each end of a beam, where it meets the wall over the gallery."""
    ox, oy, oz = origin
    beams = shell.layout().beams
    for x in beam_xs():
        for z, wall in ((Z0, "north"), (Z1, "south")):
            if (x, z) in beams and not canvas.has(ox + x, oy + CEIL - 1, oz + z):
                canvas.set(ox + x, oy + CEIL - 1, oz + z, st(style["corbel"], facing=wall, half="top"))


def _dado(canvas, origin):
    """a: dark panelling two blocks high along both aisle walls, wherever nothing stands."""
    ox, oy, oz = origin
    for z, wall in ((Z0, "north"), (Z1, "south")):
        for x in range(X0, X1 + 1):
            for y in (FEET, FEET + 1):
                if not canvas.has(ox + x, oy + y, oz + z):
                    canvas.set(ox + x, oy + y, oz + z, st(B.WAINSCOT, facing=ACROSS[wall], half="bottom", open="true"))


def _door_emblem(canvas, origin):
    """The hall's second emblem: one carved block in the inner leaf over the middle of the doorway."""
    door = doorway()
    if door is not None:
        x, z, top = door
        canvas.set(origin[0] + x, origin[1] + top + 1, origin[2] + z, B.ASHLAR_EMBLEM)


def _switchboard(canvas, origin, style):
    """The hall's switchboard against the north wall: instrument panels under an iron top. Its lamp
    is a source before its pilot lamps, no model."""
    ox, oy, oz = origin
    rows = style["board"]
    x0 = BOARD_MID_X - len(rows[0]) // 2
    for dy, row in enumerate(rows):
        for dx, name in enumerate(row):
            canvas.set(ox + x0 + dx, oy + FEET + dy, oz + Z0, st(B.PANELS[name], facing="south"))
    for dx in range(len(rows[0])):
        canvas.set(ox + x0 + dx, oy + FEET + len(rows), oz + Z0, st(B.IRON_RIVETED.slab, type="bottom"))
    L.suggest(canvas, (ox + BOARD_MID_X, oy + FEET + 2, oz + Z0 + 1), BOARD_LEVEL, f"{WHY}:switchboard", rank=3)


# ---- the ceiling --------------------------------------------------------------------------------------------
def _ceiling(canvas, origin, version, style):
    """The boss the orrery hangs from, and in a the four blue panels in the boards round it. The
    beams are the shell's and nothing is laid across them."""
    models = _models()
    n = K.put(canvas, models[PREFIX + "boss_" + version], (CX + 0.5, CEIL - BOSS_DROP, CZ + 0.5), scale=2.0,
              origin=origin)
    if style["coffers"]:
        beams = beam_xs()
        for a, b in zip(beams, beams[1:]):
            for z, yaw in ((CZ - 3 + 0.5, 0.0), (CZ + 3 + 0.5, 180.0)):
                n += K.put(canvas, models[PREFIX + "coffer"], ((a + 1 + b) / 2.0, CEIL + BOARDS_UP, z),
                           mount="ceiling", yaw=yaw, scale=2.0, origin=origin, brightness=(0, CEILING_LIGHT))
    return n


# ---- furniture and what hangs on the walls ----------------------------------------------------------------
def _stand_in(canvas, origin, kind, pos, facing):
    """Blocks for a piece of props/furniture while that package is not in the tree."""
    ox, oy, oz = origin
    x, z = int(math.floor(pos[0])), int(math.floor(pos[1]))
    wide = (x - 1, x) if pos[0] == int(pos[0]) else (x,)
    if kind == "bench":
        state = st(B.DARK_WOOD.stairs, facing=ACROSS[facing], half="bottom")
    elif kind in ("display_table", "writing_desk", "drafting_table"):
        state = st(B.DARK_WOOD.slab, type="top")
    elif kind in ("card_cabinet", "instrument_cabinet"):
        state = B.DARK_WOOD.block
        for cx in wide:
            canvas.set(ox + cx, oy + FEET + 1, oz + z, state)
    elif kind == "crate":
        state = B.PALE_WOOD.block
    else:
        return
    for cx in wide:
        canvas.set(ox + cx, oy + FEET, oz + z, state)


def _furnish(canvas, origin, style):
    furniture = _optional("props.furniture")
    n = 0
    for kind, (x, z), facing in style["furniture"]:
        if furniture is None:
            _stand_in(canvas, origin, kind, (x, z), facing)
        else:
            n += furniture.place(canvas, kind, (x, FEET, z), facing=facing, origin=origin)
    return n


def _charts(canvas, origin):
    """The south aisle's west bay: two star charts on the wall and a celestial globe before them.
    Stand-ins of this package until props/paper and props/instruments bring theirs."""
    models = _models()
    n = 0
    for x in (3.5, 6.0):
        n += K.put(canvas, models[PREFIX + "chart"], (x, FEET + 3.0, Z1 + 1.0), mount="wall", facing="north",
                   origin=origin)
    n += K.put(canvas, models[PREFIX + "globe"], (4.75, FEET, Z1 - 0.2), origin=origin)
    return n


# ---- the lamps ------------------------------------------------------------------------------------------------
def gallery_lamp_xs():
    """Where the lamps of a gallery wall hang: over the wing door, on the meridian, and as far west
    of the door as the meridian is east of it, which is over the head of the bridge to the ring
    stair. West to east."""
    doors = sorted({x for x, _ in shell.layout().doors})
    door = (doors[0] + doors[-1] + 1) / 2.0
    meridian = CX + 0.5
    return (2.0 * door - meridian, door, meridian)


def _lamps(canvas, origin, version):
    """Caged lamps on the aisle face of every pilaster, under the gallery, and three along each
    gallery wall. The westernmost is a level over the others: it shows the boards over the far end
    of the gallery, which from the door are the top of the picture."""
    n = 0
    for x, level in zip(beam_xs(), AISLE_LEVELS):
        n += lamps.place(canvas, "cage", (x + 0.5, AISLE_LAMP_Y, Z0 + 1.0), facing="south", origin=origin,
                         version=version, level=level)
        n += lamps.place(canvas, "cage", (x + 0.5, AISLE_LAMP_Y, Z1), facing="north", origin=origin,
                         version=version, level=level)
    for x, level in zip(gallery_lamp_xs(), GALLERY_LEVELS):
        n += lamps.place(canvas, "cage", (x, GALLERY_LAMP_Y, Z0), facing="south", origin=origin, version=version,
                         level=level)
        n += lamps.place(canvas, "cage", (x, GALLERY_LAMP_Y, Z1 + 1.0), facing="north", origin=origin,
                         version=version, level=level)
    return n


def _stair_hall(canvas, origin, version):
    """The stair hall gets lamps and nothing else (A0 #541). One at the foot of each flight, flat
    under the crown of the side arch it is entered by, its conduit running to the pier between the
    arches; where the arch has no crown, under the deck over it. One on each wall pier beside the
    great west window, over the mezzanine."""
    ox, oy, oz = origin
    n = 0
    x = (shell.ARCADE_X[0] + shell.ARCADE_X[1] + 1) / 2.0
    for rows, towards in ((shell.FLIGHT_ROWS[-1], "south"), (shell.FLIGHT_ROWS[1], "north")):
        z = rows[len(rows) // 2]
        crowned = canvas.has(ox + int(x), oy + shell.ARCH_Y, oz + z)
        under = shell.ARCH_Y + 0.5 if crowned else float(shell.DECK_Y)
        n += lamps.place(canvas, "cage", (x, under - K.NUDGE, z + 0.5), facing=towards, origin=origin,
                         version=version, light=False, turns=(("x", 90.0),))
        # the source goes into the cell the glass hangs in; under a crown that cell holds the crown
        L.suggest(canvas, (ox + int(x), oy + shell.ARCH_Y - (1 if crowned else 0), oz + z), STAIR_FOOT_LEVEL,
                  f"{WHY}:stair foot", rank=3)
    wx = min(x for x, _ in shell.layout().mezzanine)
    for z in (CZ - shell.CHEEK_Z, CZ + shell.CHEEK_Z):
        n += lamps.place(canvas, "cage", (wx + 1.0, MEZZANINE_LAMP_Y, z + 0.5), facing="east", origin=origin,
                         version=version, level=MEZZANINE_LEVEL)
    return n


# ---- models -----------------------------------------------------------------------------------------------------
def _star():
    """The emblem's star, let into the floor: eight points round a full middle, all as long, so
    that near or far it is a star and never two bars."""
    m = M.Model(PREFIX + "star")
    for i in range(4):
        m.box((-5.5, 0.0, -0.5), (5.5, 0.2 + 0.04 * i, 0.5), K.BRASS, rot=("y", 45.0 * i, (0, 0, 0)), grain="x")
    m.tube("y", (0, 0), 0.0, 0.5, 2.0, K.BRASS_D, sides=8)
    return m


def _boss(version):
    """The round boss over the orrery, shown at scale 2 (units are eighths of a block). Anchor: the
    middle of its lower face. It fills the half block between the boards and the beam's lower face
    and lies a hair under the beam, so from below it is one disc with the hub's seat in its middle.
    a: dark wood, a brass rim, a bead and a ring of brass studs. b: iron, an angle rim, rivets."""
    m = M.Model(PREFIX + "boss_" + version, px=2.0)
    r = BOSS_R * 8.0
    top = (BOARDS_UP + BOSS_DROP) * 8.0
    body, rim, bead = (WOOD_D, K.BRASS, K.BRASS_D) if version == "a" else (K.IRON_D, K.IRON, K.IRON)
    m.tube("y", (0, 0), 0.0, top, r, body, sides=16)
    m.ring("y", (0, -0.25, 0), r - 0.75, 1.5, 0.5, rim, sides=16)
    m.ring("y", (0, -0.125, 0), 8.5, 0.5, 0.25, bead, sides=16)
    for i in range(16):
        with m.turned(("y", 22.5 * i + 11.25)):
            if version == "a":
                m.box((-0.5, -0.25, 9.25), (0.5, 0.0, 10.25), K.BRASS)
            else:
                m.box((-0.25, -0.75, r - 1.0), (0.25, -0.5, r - 0.5), K.RIVET)
    if version == "b":
        for i in range(6):                              # six straps: no four at right angles
            with m.turned(("y", 60.0 * i + 30.0)):
                m.box((-0.75, -0.25, 8.75), (0.75, 0.0, r - 1.5), K.IRON, grain="z")
    return m


def _coffer():
    """A blue enamel panel let into the boards between two beams, with a few brass stars: a piece
    of sky over the orrery. Shown at scale 2. Anchor: the middle of its upper face, on the boards."""
    m = M.Model(PREFIX + "coffer", px=2.0)
    w, d = 7.0, 10.0
    m.box((-w, -0.5, -d), (w, 0.0, d), K.ENAMEL, grain="z", shade=False)
    for s in (-1.0, 1.0):
        m.box((s * w - 0.5, -0.75, -d - 0.5), (s * w + 0.5, 0.0, d + 0.5), K.BRASS_D, grain="z", shade=False)
        m.box((-w + 0.5, -0.75, s * d - 0.5), (w - 0.5, 0.0, s * d + 0.5), K.BRASS_D, grain="x", shade=False)
    for x, z, size in ((-3.5, -6.5, 1.0), (2.0, -4.0, 0.5), (4.5, -7.5, 0.5), (-1.0, -0.5, 0.5), (3.5, 2.5, 1.0),
                       (-4.5, 4.0, 0.5), (0.5, 6.5, 0.5), (-2.5, 8.0, 0.5)):
        m.box((x - size / 2.0, -0.75, z - size / 2.0), (x + size / 2.0, -0.5, z + size / 2.0), K.BRASS, shade=False)
    return m


def _chart():
    """A stand-in star chart, two blocks square: the two hemispheres side by side on a cream sheet
    in a dark frame. Anchor: the middle of its back, on the wall."""
    m = M.Model(PREFIX + "chart")
    m.box((-14, -14, 0), (14, 14, 0.5), K.CREAM)
    for s in (-1.0, 1.0):
        m.box((s * 15 - 1, -16, 0), (s * 15 + 1, 16, 1.0), WOOD_D, grain="y")
        m.box((-14, s * 15 - 1, 0), (14, s * 15 + 1, 1.0), WOOD_D, grain="x")
        m.ring("z", (s * 6.75, 0, 0.5), 6.0, 0.5, 0.25, K.IRON_D, sides=16)
    for x, y in ((-9.5, 2.5), (-6.0, -3.0), (-4.0, 3.5), (-8.0, -1.0), (4.5, 1.0), (7.5, 3.5), (9.0, -2.5),
                 (6.0, -4.0), (5.5, 4.0)):
        m.box((x - 0.25, y - 0.25, 0.5), (x + 0.25, y + 0.25, 0.75), K.IRON_D)
    return m


def _globe():
    """A stand-in celestial globe on a three-legged stand, a block and a half tall. Anchor: the
    middle of its foot."""
    m = M.Model(PREFIX + "globe")
    for i in range(3):
        a = math.radians(120.0 * i + 30.0)
        m.rod((5.5 * math.cos(a), 0.0, 5.5 * math.sin(a)), (0.0, 9.0, 0.0), 0.6, WOOD)
    m.tube("y", (0, 0), 8.5, 11.0, 1.0, WOOD_D)
    m.ring("y", (0, 16.0, 0), 6.5, 1.0, 0.75, K.BRASS_D, sides=16)
    m.ball((0, 16.0, 0), 5.25, NIGHT, sides=12, layers=6)
    with m.turned(("z", 23.5), about=(0, 16.0, 0)):
        m.ring("x", (0, 16.0, 0), 5.9, 0.6, 0.6, K.BRASS, sides=16)
    return m


@functools.lru_cache(maxsize=None)
def _models():
    made = [_star(), _boss("a"), _boss("b"), _coffer(), _chart(), _globe()]
    return {m.name: m for m in made}


def models():
    return dict(_models())


# ---- the package ------------------------------------------------------------------------------------------------
def dress(canvas, origin=(0, 0, 0), version=None):
    """Fit the hall out in the shell that stands at `origin`; returns the display entities placed."""
    version = version or VERSION
    style = STYLE[version]
    n = _floor(canvas, origin, version, style)
    _plinth(canvas, origin)
    _cove(canvas, origin)
    _pilasters(canvas, origin, style)
    _corbels(canvas, origin, style)
    _switchboard(canvas, origin, style)
    n += _furnish(canvas, origin, style)
    if style["dado"]:
        _dado(canvas, origin)
    _door_emblem(canvas, origin)
    n += _ceiling(canvas, origin, version, style)
    n += _charts(canvas, origin)
    n += _lamps(canvas, origin, version)
    n += _stair_hall(canvas, origin, version)
    return n


def build(canvas, origin=(0, 0, 0)):
    if not MOVED_IN:
        return 0
    return dress(canvas, origin, VERSION)
