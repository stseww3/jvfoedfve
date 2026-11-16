"""interiors/starhall -- the star hall, the entrance hall in the middle of the main building (plan
ART-PLAN 8, card plan/packages/interiors/starhall.md), and the lamps of the stair hall behind it.

What stands there is not this package's: the walls, the inner leaf with its three arches and the
great windows over them (main/facade), the floor, the galleries, the telescope pier and its ring
stair, the west arcade, the beams and boards of the ceiling (main/shell), the orrery and the mother
clock (machines). The hall dresses the room they leave, and reads it from them: the room's box from
shell.ROOMS, the beams from shell.layout().beams, the clock's seat from shell.layout().seat, the
doorway from facade.doors().

The first look (S.V7, from outside the door through the middle arch): the orrery overhead, the
mother clock on the pier straight ahead, the floor underfoot. The hall keeps that picture clear,
and in the order the director set (A0, 11-16): the clock's dial and the pier's east face first,
the orrery's sun the warmest point, the floor third. Nothing of the hall's own stands on the
axis; no stone of the floor is pale, since a floor is drawn at full light and a wall that looks
east at six tenths, and a pale one under the same lamp outshines the pier; and no lamp of the
hall shows its glass to the door.

  floor     The hall lays its own from wall to wall round the pier's foot (the shell's shows in
            the stair hall only). The station's emblem under the orrery, in thin brass line: an
            octagonal ring seven across, the meridian through it from wall to wall (x 11, north
            to south), the star inside the ring on its upper right. Brass runs north-south only
            and the nave is one stone from the door to the clock, so the floor shows no cross.
            The line is dark brass, a tone with slate: what it lies on is tuff.
  ceiling   Nothing is added to the beams, which run north-south only. Where the orrery hangs, a
            flat round boss packs the gap between the boards and the beam's lower face. Panels in
            the boards of every bay, so that the dark boards are not one black field.
  walls     A pilaster under every beam along both aisles, a dado between them (a), the
            switchboard in the north aisle, charts and a globe across from it in the south one,
            a great chart of half the sky on each gallery wall.
  emblem    Twice and no more: in the floor, and one carved block over the doorway on the inside.
  light     Every source is offered to the light line (sky/_lightkit); no light block is set here.
            The sun and the clock offer their own (machines). Lamps of the third rank: a shaded
            bracket in the middle of every bay of the aisles, over what stands there; caged lamps
            along the gallery walls, at the two stair feet and on the mezzanine. A shade throws
            its light down: the pair of brackets beside the pier, fixed high over the board and
            the charts, has its sources a cell over the floor.

Two versions to choose between; the plan is locked, so they differ in dress:
  a  "academy"   a nave of polished slate with the roundel a grey disc on it, the plan's chequer
                 under the galleries in slate and tuff, stone pilasters, a dark wainscot, a wooden
                 boss ringed in brass, blue panels with brass stars in the boards, benches and
                 display tables.
  b  "workshop"  polished tuff down the nave with the roundel's ring a dark band on it, an iron
                 duct cover under each gallery's edge, a grating inside the door, riveted
                 stanchions, an iron boss, riveted plates in the boards, drafting table, desk,
                 cabinets and cases.

build() is what the master scene calls. MOVED_IN tells main/facade that the hall is fitted out:
its stand-in wall behind the entrance and that wall's lights go (facade.furnished()).
"""
import functools
import importlib
import importlib.util
import math

from artkit import models as M
from artkit.blocks import st

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..main import shell
from ..props import _kit as K
from ..props import furniture, instruments, lamps, paper
from ..sky import _lightkit as L

ORDER = 80                  # after the shells (main/shell is 60) and whatever else stands in the hall
MOVED_IN = True             # read by main/facade.furnished(): the hall stands in the shell
VERSION = "a"               # the version build() dresses; the review picks one and only this changes
VERSIONS = ("a", "b")
PREFIX = "int_starhall_"
WHY = "interiors/starhall"
# Pieces of the hall that stand in files of their own beside this one, each as soon as it is in the
# tree: dress(canvas, origin, version) -> display entities placed, models() -> {name: model}.
PARTS = ("_starhall_meridian", "_starhall_wiring", "_starhall_gallery")
NEIGHBOURS = ("batteryroom", "platevault")      # rooms behind the aisle walls that open a door into the hall

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
PANEL = 1.75                # blocks: the side of a panel between two beams; over a gallery's end it is a strip
STRIP = 0.75                # that wide, as long as a panel
PANEL_GAP = 0.25            # between two panels of a row
PANEL_LIGHTS = (9, 8, 7)    # the level a panel is shown at: beside the boss, at the end of its row, over a
#                             gallery's end. No source reaches the boards, a block's face that looks down is
#                             drawn at half, and dark boards with nothing on them come out dead black from the door
AISLE_LAMP = ("bracket", "b")   # the enamel cone in both versions: its bulb is inside the shade. A caged lamp's
#                                 glass is drawn at full light where it looks up and was brighter in the picture
#                                 than the orrery's sun, which the door sees from below (cr3, #58794)
AISLE_LEVELS = (8, 8, 7, 8)     # the four lamps of an aisle wall, from the pier to the door. The last is in the
#                                 bay behind the entrance's side arch: what the forecourt sees first through that
#                                 arch is to stand at 7 or more, and the lamps for it are the hall's (A0 #526).
#                                 The first lights dark iron and dark wood from a row away: under 6 their seams
#                                 are dead black
AISLE_LAMP_Y = 3.25             # where the bracket is fixed: its shade clears a cabinet two blocks tall, and its
#                                 source is in the third cell over the floor, one nearer the dado than before
BOARD_LAMP_Y = 4.5              # the same over the switchboard, whose top is at three and a half, and across
#                                 from it over the charts: the first look sees these two, and sees them as a pair.
#                                 A cone throws its light down, and that high up the lamp's own source lit the wall
#                                 round it, lighter in the first look than the pier's face, and left the dado, the
#                                 board's foot and the globe in the dark. The pair's sources are set apart from
#                                 the lamps: a cell over the floor in the row before the wall's, under the shade
GALLERY_LEVELS = (7, 6, 6)  # the three lamps of a gallery wall, from its west end to the meridian
GALLERY_LAMP_Y = 10.5
GALLERY_MAP_Y = shell.DECK_Y + 2.75     # the middle of a great chart, two blocks tall: at the eye of who stands
#                                         on the gallery, its head under the lamp
SUN_POOL = 8                # where the sun's light lands: a source a cell over the roundel's middle. The sun's
#                             own 12 is 5 by the time it is down there. A0, 11-16: it may stay as long as the
#                             floor's middle is darker than the mother clock's dial, which with 10 it was not
STAIR_FOOT_LEVEL = 8        # 7 shows nothing of the risers through the side arches (lights, #559)
MEZZANINE_LEVEL = 7
MEZZANINE_LAMP_Y = 9.5
WAY_LEVEL = 7               # the way to the west door, which had no light at all (the walk, S1): a step under the stair foot's
WAY_SOURCE_Y = FEET + 2     # the row of its sources: over the head of who walks under the lamp. In the cell under
#                             the crown they left 3 of the 7 at the feet, and a floor one walks on indoors is to
#                             have 5 (lights, #72659; the light line knows a source for a lamp's up to six cells under it)

SIDES = {(0, -1): "north", (0, 1): "south", (-1, 0): "west", (1, 0): "east"}
ACROSS = {"north": "south", "south": "north", "west": "east", "east": "west"}
SHAPES = {frozenset(pair): "_".join(pair) for pair in (("north", "south"), ("east", "west"), ("south", "east"),
                                                         ("south", "west"), ("north", "west"), ("north", "east"))}

# the switchboard, bottom row first. No nameplate: it carries the emblem, and the hall shows that twice.
BOARD_A = (("fuses", "louvre", "fuses"),
           ("knife_switch", "dial", "knife_switch"),
           ("gauges", "pilot_lamps", "gauges"))
BOARD_B = (("fuses", "louvre", "drawers", "louvre", "fuses"),
           ("knife_switch", "relays", "bus_switch", "relays", "knife_switch"),
           ("gauges", "dial", "pilot_lamps", "dial", "gauges"))
# One face of pilot lamps to a board: they glow at full strength, brighter in the picture than the
# orrery's sun, and from the door a handful of them is a sparkle and two faces a second light (cr3, #63239)
BOARD_MID_X = 4             # the board is centred on this column of the north aisle, between the stair hall's
#                             arcade and the battery room's door (x 7, interiors/batteryroom's to set)

STYLE = {
    "a": dict(
        band=B.TUFF_BRICK.block, field=B.TUFF_SMOOTH.block,
        base=B.SLATE_BRICK.block, shaft=B.ASHLAR_FINE.block, capital=B.ASHLAR_PANEL.block,
        corbel=B.ASHLAR_FINE.stairs, dado=True, panel="sky", board=BOARD_A,
        # a bench's back is 7.25 px behind its middle and the wainscot 3 px thick: 5.35 clears it by a hair
        furniture=(("bench", (10.0, 5.35), "north"), ("bench", (13.0, 5.35), "north"),
                   ("display_table_plates", (10.0, -4.36), "south"),
                   ("display_table_lenses", (13.0, -4.36), "south"),
                   ("coat_stand", (15.5, 5.3), "north")),
    ),
    "b": dict(
        band=B.SLATE_SMOOTH.block, field=B.TUFF_SMOOTH.block,
        base=B.IRON_RIVETED.block, shaft=B.IRON_RIVETED.block, capital=B.IRON_RIVETED.block,
        corbel=B.IRON_RIVETED.stairs, dado=False, panel="plate", board=BOARD_B,
        furniture=(("drafting_table", (10.0, 5.45), "north"), ("stool", (10.0, 4.3), "south"),
                   ("writing_desk", (13.0, 5.53), "north"), ("swivel_chair", (13.0, 4.5), "south"),
                   ("card_cabinet", (9.5, -4.57), "south"), ("instrument_cabinet", (10.5, -4.57), "south"),
                   ("crate", (12.6, -4.5), "south"), ("trunk", (15.36, -4.25), "east"),
                   ("coat_stand", (15.5, 5.3), "north")),
    ),
}

WOOD_D = P.mat("dark_wood", base=1)
PLATE = P.mat("iron", base=4)       # a step over the kit's iron: a display entity's face that looks east or west is
#                                     drawn at half its light, and the kit's iron went dead black in its seams there


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
def _lay_a(x, z):
    """a: the nave polished slate from the door to the clock and from gallery to gallery: the axis
    marked in stone, as wide as the ring, which lies on it like a seal on a ribbon. Under the
    galleries the plan's chequer, a block to a square, mirrored about the meridian and about the
    axis, and light where the meridian's brass crosses it. Its light stone is polished tuff: white
    ashlar under the aisles' lamps was brighter in the first look than the pier's face."""
    across = abs(z - CZ)
    if across <= ROUNDEL_R or (abs(x - CX) + across) % 2 == 1:
        return B.SLATE_SMOOTH.block, None
    return B.TUFF_SMOOTH.block, None


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
    stones, the roundel (a band of its own stone under the ring, the field inside it plain), and
    the brass."""
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


def aisle_doors():
    """Doors other rooms open in the aisle walls on the ground floor: {(x, z of the aisle's row
    before it)}. Each is its room's to set (HALL_DOOR in the room's module, the wall's cell): the
    battery room's in the north wall beside the switchboard, the plate vault's in the south wall
    across from it. The shell cuts them and tells them in doors(), with the doors of the main
    floor: of those the ones whose foot is the ground (shell, #74028). The hall keeps the cell
    before a door free."""
    out = set()
    for name in NEIGHBOURS:
        door = getattr(_optional("interiors." + name), "HALL_DOOR", None)
        if door is not None:
            x, z = door
            out.add((x, Z0 if z < Z0 else Z1))
    for door in shell.doors():
        if door["y"][0] == FEET:
            dx, dz = door["inward"]
            out |= {(x - dx, z - dz) for x, z in door["cells"]
                    if X0 <= x - dx <= X1 and z - dz in (Z0, Z1)}
    return out


def _dado(canvas, origin):
    """a: dark panelling two blocks high along both aisle walls, wherever nothing stands and no
    door opens."""
    ox, oy, oz = origin
    doors = aisle_doors()
    for z, wall in ((Z0, "north"), (Z1, "south")):
        for x in range(X0, X1 + 1):
            for y in (FEET, FEET + 1):
                if (x, z) not in doors and not canvas.has(ox + x, oy + y, oz + z):
                    canvas.set(ox + x, oy + y, oz + z, st(B.WAINSCOT, facing=ACROSS[wall], half="bottom", open="true"))


def _reveals(canvas, origin):
    """The two reveals of the main doorway, in the inner leaf, lined with the dado's dark panelling
    from the sill to the head. The first look stands in the doorway, and the two faces beside it,
    bare stone in the pier's own tone, were a third of the picture; lined, one looks out of a dark
    frame into the hall (cr3, #74066). In both versions: iron there is two black bars, and no
    further out than the leaf's one cell, where the door's frame and leaves are (facade, #74675).
    The stone is the facade's and is not touched: the panels stand in the doorway's own cells."""
    from ..main import facade
    ox, oy, oz = origin
    for d in (facade.doors() if hasattr(facade, "doors") else ()):
        if d["front"] != "east" or d["kind"] != "door" or len(d["cells"]) < 3:
            continue
        dx, dz = d["inward"]
        cells = sorted((x + dx, z + dz) for x, z in d["cells"])
        for (x, z), wall in ((cells[0], "north"), (cells[-1], "south")):
            for y in range(d["y"][0], d["y"][1] + 1):
                if not canvas.has(ox + x, oy + y, oz + z):
                    canvas.set(ox + x, oy + y, oz + z, st(B.WAINSCOT, facing=ACROSS[wall], half="bottom", open="true"))


def _door_emblem(canvas, origin):
    """The hall's second emblem: one carved block in the inner leaf over the middle of the doorway."""
    door = doorway()
    if door is not None:
        x, z, top = door
        canvas.set(origin[0] + x, origin[1] + top + 1, origin[2] + z, B.ASHLAR_EMBLEM)


def _switchboard(canvas, origin, version, style):
    """The hall's switchboard against the north wall: instrument panels under an iron top. The
    aisle's westernmost lamp is fixed over its middle and throws its light down its face. An end
    that stands free is closed with a plate: the casing's own side is the darkest iron there is,
    and the end that looks to the door was one dead black slab in the first look."""
    ox, oy, oz = origin
    rows = style["board"]
    x0 = BOARD_MID_X - len(rows[0]) // 2
    for dy, row in enumerate(rows):
        for dx, name in enumerate(row):
            canvas.set(ox + x0 + dx, oy + FEET + dy, oz + Z0, st(B.PANELS[name], facing="south"))
    for dx in range(len(rows[0])):
        canvas.set(ox + x0 + dx, oy + FEET + len(rows), oz + Z0, st(B.IRON_RIVETED.slab, type="bottom"))
    n = 0
    for x, beside, facing in ((x0 + len(rows[0]), x0 + len(rows[0]), "east"), (x0, x0 - 1, "west")):
        if not canvas.has(ox + beside, oy + FEET + 1, oz + Z0):
            n += K.put(canvas, _models()[PREFIX + "board_end_" + version], (float(x), FEET + len(rows) / 2.0, Z0 + 0.5),
                       mount="wall", facing=facing, origin=origin)
    return n


# ---- the ceiling --------------------------------------------------------------------------------------------
def ceiling_panels():
    """Where the panels in the boards go: [(model, (x, z) of its middle, quarter turns, level)].
    Between two beams a row of squares from wall to wall, two on either side of the boss, which
    keeps the middle of the row. Over each gallery's west end, between the wall and the girder
    of the stair's well, where the beams stop, a row of strips. No panel crosses a beam."""
    out = []
    beams = beam_xs()
    step = PANEL + PANEL_GAP
    near, far, end = PANEL_LIGHTS
    for a, b in zip(beams, beams[1:]):
        x = (a + 1 + b) / 2.0
        for side in (-1, 1):
            edge = CZ + 0.5 + side * (BOSS_R + PANEL_GAP / 2.0)
            for k, level in ((0, near), (1, far)):
                out.append(("panel", (x, edge + side * (PANEL / 2.0 + k * step)), len(out) % 4, level))
    for z in (Z0 + 0.5, Z1 + 0.5):
        x = beams[0] - PANEL_GAP / 2.0 - PANEL / 2.0
        while x - PANEL / 2.0 >= X0:
            out.append(("strip", (x, z), 2 * (len(out) % 2), end))
            x -= step
    return out


def _ceiling(canvas, origin, version, style):
    """The boss the orrery hangs from, and the panels in the boards (a: blue enamel with brass
    stars, b: riveted plate). The beams are the shell's and nothing is laid across them."""
    models = _models()
    n = K.put(canvas, models[PREFIX + "boss_" + version], (CX + 0.5, CEIL - BOSS_DROP, CZ + 0.5), scale=2.0,
              origin=origin)
    for kind, (x, z), quarter, level in ceiling_panels():
        n += K.put(canvas, models[f"{PREFIX}{style['panel']}_{kind}"], (x, CEIL + BOARDS_UP, z), mount="ceiling",
                   yaw=90.0 * quarter, scale=2.0, origin=origin, brightness=(0, level))
    return n


# ---- furniture and what hangs on the walls ----------------------------------------------------------------
def _furnish(canvas, origin, style):
    """What stands along the aisle walls (props/furniture). a's two display tables show star-field
    plates with a measuring rule and a glass (by the pier) and lenses and eyepieces laid out by
    size (by the door): table and exhibits are one piece of the family's (a6, #61626), and the
    empty table stands there until the family has them."""
    n = 0
    for kind, (x, z), facing in style["furniture"]:
        if kind not in furniture.SPEC:
            kind = kind.rpartition("_")[0]
        n += furniture.place(canvas, kind, (x, FEET, z), facing=facing, origin=origin)
    return n


def _charts(canvas, origin):
    """The south aisle's west bay: the pair of star charts on the wall either side of the aisle's
    westernmost lamp, and a celestial globe before them under it. On each gallery wall one of the
    pair of great charts, a half of the sky, at the height of the eye under the lamp on the
    meridian. The charts are props/paper's and the globe, its north pole to true north, is
    props/instruments'."""
    lamp = aisle_lamp_xs()[0]
    n = 0
    for kind, x in (("star_chart", lamp - 1.5), ("star_chart_b", lamp + 1.5)):
        n += paper.place(canvas, kind, (x, FEET + 3.0, Z1 + 1.0), facing="north", origin=origin)
    n += instruments.place(canvas, "celestial_globe", (lamp, FEET, Z1 - 0.2), facing="east", origin=origin)
    x = gallery_lamp_xs()[-1]
    for kind, z, facing in (("sky_map", Z0, "south"), ("sky_map_b", Z1 + 1.0, "north")):
        n += paper.place(canvas, kind, (x, GALLERY_MAP_Y, float(z)), facing=facing, origin=origin)
    return n


# ---- the lamps ------------------------------------------------------------------------------------------------
def aisle_lamp_xs():
    """Where the lamps of an aisle wall are fixed: in the middle of each bay, over what stands
    there. West of the first pilaster that is over the switchboard's middle, which on the south
    side is between the two charts; east of the last it is the bay behind the entrance's side
    arch. West to east."""
    beams = beam_xs()
    return ([BOARD_MID_X + 0.5] + [(a + 1 + b) / 2.0 for a, b in zip(beams, beams[1:])]
            + [(beams[-1] + 1 + X1 + 1) / 2.0])


def gallery_lamp_xs():
    """Where the lamps of a gallery wall hang: over the wing door, on the meridian, and as far west
    of the door as the meridian is east of it, which is over the head of the bridge to the ring
    stair. West to east."""
    doors = sorted({x for x, _ in shell.layout().doors})
    door = (doors[0] + doors[-1] + 1) / 2.0
    meridian = CX + 0.5
    return (2.0 * door - meridian, door, meridian)


def _lamps(canvas, origin, version):
    """A shaded bracket in every bay of both aisles, on the wall over what stands in the bay, and
    three caged lamps along each gallery wall. The westernmost pair is fixed higher, over the
    switchboard's top and between the heads of the two charts, and its light lands where a cone
    throws it: before the board's face and the dado, on the door's side of the lamp.
    The westernmost of a gallery is a level over the others: it shows the far end of the gallery,
    which from the door is the top of the picture."""
    ox, oy, oz = origin
    kind, model = AISLE_LAMP
    n = 0
    for i, (x, level) in enumerate(zip(aisle_lamp_xs(), AISLE_LEVELS)):
        for face, facing, row in ((Z0, "south", Z0 + 1), (Z1 + 1, "north", Z1 - 1)):
            high = i == 0
            n += lamps.place(canvas, kind, (x, BOARD_LAMP_Y if high else AISLE_LAMP_Y, float(face)), facing=facing,
                             origin=origin, version=model, level=level, light=not high)
            if high:
                L.suggest(canvas, (ox + int(math.ceil(x)), oy + FEET + 1, oz + row), level, f"{WHY}:aisle lamp", rank=3)
    for x, level in zip(gallery_lamp_xs(), GALLERY_LEVELS):
        n += lamps.place(canvas, "cage", (x, GALLERY_LAMP_Y, Z0), facing="south", origin=origin, version=version,
                         level=level)
        n += lamps.place(canvas, "cage", (x, GALLERY_LAMP_Y, Z1 + 1.0), facing="north", origin=origin,
                         version=version, level=level)
    return n


def _flat_lamp(canvas, origin, version, at, towards, level, what, source_y=None):
    """A caged lamp flat under the crown of an arch or a vault at (x, z), its conduit running
    `towards`; where there is no crown, under the deck over it. Its source goes into the cell the
    glass hangs in; under a crown that cell holds the crown, so it is the one below. source_y: the
    source's row, straight under the lamp, where the light is wanted lower than that."""
    ox, oy, oz = origin
    x, z = (int(math.floor(v)) for v in at)
    crowned = canvas.has(ox + x, oy + shell.ARCH_Y, oz + z)
    under = shell.ARCH_Y + 0.5 if crowned else float(shell.DECK_Y)
    n = lamps.place(canvas, "cage", (at[0], under - K.NUDGE, at[1]), facing=towards, origin=origin, version=version,
                    light=False, turns=(("x", 90.0),))
    y = shell.ARCH_Y - (1 if crowned else 0) if source_y is None else source_y
    L.suggest(canvas, (ox + x, oy + y, oz + z), level, f"{WHY}:{what}", rank=3)
    return n


def _stair_hall(canvas, origin, version):
    """The stair hall gets lamps and nothing else (A0 #541). One at the foot of each flight, flat
    under the crown of the side arch it is entered by, its conduit running to the pier between the
    arches. One on each wall pier beside the great west window, over the mezzanine. Two under the
    vault of the way to the west door, which had no light at all (the walk's S1)."""
    n = 0
    x = (shell.ARCADE_X[0] + shell.ARCADE_X[1] + 1) / 2.0
    for rows, towards in ((shell.FLIGHT_ROWS[-1], "south"), (shell.FLIGHT_ROWS[1], "north")):
        n += _flat_lamp(canvas, origin, version, (x, rows[len(rows) // 2] + 0.5), towards, STAIR_FOOT_LEVEL,
                        "stair foot")
    wx = min(x for x, _ in shell.layout().mezzanine)
    for z in (CZ - shell.CHEEK_Z, CZ + shell.CHEEK_Z):
        n += lamps.place(canvas, "cage", (wx + 1.0, MEZZANINE_LAMP_Y, z + 0.5), facing="east", origin=origin,
                         version=version, level=MEZZANINE_LEVEL)
    for x in way_lamp_xs():
        n += _flat_lamp(canvas, origin, version, (x + 0.5, CZ + 0.5), "east", WAY_LEVEL, "way west",
                        source_y=WAY_SOURCE_Y)
    return n


def way_lamp_xs():
    """The cells of the two lamps of the way to the west door, flat under the crown of its vault:
    a quarter of its length in from either end."""
    xs = sorted(x for x, z in shell.layout().crown if x < shell.ARCADE_X[0] and z == CZ)
    return (xs[len(xs) // 4], xs[-1 - len(xs) // 4]) if len(xs) > 3 else tuple(xs[:1])


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


SKY_STARS = ((-4.5, -4.0, 1.0), (2.0, -5.0, 0.5), (4.5, -1.5, 0.5), (-1.0, -0.5, 0.5), (3.5, 3.5, 1.0),
             (-4.0, 3.0, 0.5), (0.5, 5.0, 0.5), (-2.5, -2.5, 0.5))     # x, z, size, in eighths of a block


def _panel(name, kind):
    """A panel let into the boards, shown at scale 2 (units are eighths of a block); `kind` is
    "panel", square, or "strip", as long and STRIP wide, its length along x. Anchor: the middle
    of its upper face, on the boards. It looks down, and a display entity's face that does is drawn
    at four tenths of its light, so it is shown at a level of its own (PANEL_LIGHTS).
    sky    blue enamel in a brass bead with a few brass stars: a piece of the sky over the orrery
    plate  an iron plate riveted to the boards, a row of rivets along each edge"""
    m = M.Model(f"{PREFIX}{name}_{kind}", px=2.0)
    w, d = PANEL * 4.0, (PANEL if kind == "panel" else STRIP) * 4.0
    if name == "sky":
        m.box((-w, -0.5, -d), (w, 0.0, d), K.ENAMEL, grain="x")
        for s in (-1.0, 1.0):
            m.box((s * w - 0.5, -0.75, -d - 0.5), (s * w + 0.5, 0.0, d + 0.5), K.BRASS_D, grain="z")
            m.box((-w + 0.5, -0.75, s * d - 0.5), (w - 0.5, 0.0, s * d + 0.5), K.BRASS_D, grain="x")
        for x, z, size in SKY_STARS:
            if abs(z) + size / 2.0 < d - 0.5:
                m.box((x - size / 2.0, -0.75, z - size / 2.0), (x + size / 2.0, -0.5, z + size / 2.0), K.BRASS)
    else:
        m.box((-w, -0.5, -d), (w, 0.0, d), K.IRON, grain="x")
        for s in (-1.0, 1.0):
            m.box((s * w - 0.5, -0.75, -d), (s * w + 0.5, -0.5, d), K.IRON_D, grain="z")
            for k in range(-3, 4):
                z = s * (d - 0.75)
                m.box((2.0 * k - 0.25, -0.75, z - 0.25), (2.0 * k + 0.25, -0.5, z + 0.25), K.RIVET)
    return m


def _board_end(version):
    """The plate that closes a free end of the switchboard, three blocks tall and one deep: an
    angle down each edge and a flat across each joint of the board's rows. a: a brass bead inside
    each angle. b: the angles riveted. Anchor: the middle of its back, on the casing's side."""
    m = M.Model(PREFIX + "board_end_" + version)
    m.box((-8, -24, 0), (8, 24, 0.5), PLATE, grain="y", skip="n")
    for s in (-1.0, 1.0):
        m.box((s * 7 - 1, -24, 0.5), (s * 7 + 1, 24, 1.0), PLATE, grain="y")
        if version == "a":
            m.box((s * 5.5 - 0.5, -24, 0.5), (s * 5.5 + 0.5, 24, 1.25), K.BRASS_D, grain="y")
        else:
            for y in range(-21, 24, 6):
                K.rivet(m, (s * 7, y, 1.0))
    for y in (-8.0, 8.0):
        m.box((-5, y - 0.5, 0.5), (5, y + 0.5, 0.75), PLATE, grain="x")
    return m


@functools.lru_cache(maxsize=None)
def _models():
    made = [_star(), _boss("a"), _boss("b"), _board_end("a"), _board_end("b")]
    made += [_panel(name, kind) for name in ("sky", "plate") for kind in ("panel", "strip")]
    return {m.name: m for m in made}


def _parts():
    """The files of PARTS that are in the tree, as modules."""
    names = [f"{__package__}.{name}" for name in PARTS]
    return [importlib.import_module(name) for name in names if importlib.util.find_spec(name) is not None]


def models():
    out = dict(_models())
    for part in _parts():
        out.update(part.models() or {})
    return out


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
    n += _switchboard(canvas, origin, version, style)
    n += _furnish(canvas, origin, style)
    if style["dado"]:
        _dado(canvas, origin)
    _reveals(canvas, origin)
    _door_emblem(canvas, origin)
    n += _ceiling(canvas, origin, version, style)
    n += _charts(canvas, origin)
    n += _lamps(canvas, origin, version)
    n += _stair_hall(canvas, origin, version)
    for part in _parts():
        n += part.dress(canvas, origin, version)
    return n


def build(canvas, origin=(0, 0, 0)):
    if not MOVED_IN:
        return 0
    return dress(canvas, origin, VERSION)
