"""main/facade -- the stone shell of the main building: the elevation grammar (_order.py) laid on
the skeleton's plan. Card: plan/packages/main/facade.md; the design is plan/ART-PLAN.md 5.1.

What it builds:

  * the walls of the long building and of the rotunda's west half as ONE footprint, so plinth,
    string course and cornice run round both without a seam: the east front in its five parts
    (end pavilions one block forward, the middle three bays two), the west front, the two end
    walls, the apse;
  * the entrance in the middle pavilion, in three versions to choose from (ENTRANCE below; door
    leaves, gates, fanlight and canopy are props), the seat of the station's emblem over it, and
    the west door of the apse;
  * the roofs that close it: plain decks over the three pavilions (stand-ins: terraces() names
    them for the package that finishes them), slate between gable walls over the wings;
  * the drum and the dome above (_dome.py), as massing, until main/dome.py is in the tree;
  * a dark screen behind the entrance, a stand-in until the interiors are in.

Every number comes from the skeleton; which column is a pier and which a window comes from
_plan.py (c178's block-by-block plan). The glass stands one block behind the wall face as whole
blocks; the cell behind it is left free for the light line.

Which windows are lit: the light line's sky/_lightkit.window_lit(front, bay, storey) when it is
in the tree, until then the rows below (the light line's first version, written down).

    python -m scenes.obs.main.facade            # plan, east elevation, sections, self-check
    python -m scenes.obs.main.facade C          # the same for another version of the entrance
    python -m scenes.obs.main.facade check      # the self-check of all three versions (exit code 1 on a finding)
"""
import functools
import importlib.util
import sys

from artkit.canvas import Canvas

from ..common import blocks as B
from ..common import skeleton as S
from . import _dome
from . import _order as O
from . import _plan as P

ORDER = 20          # early in the line: what stands on the shell (dome, tower, roof terraces, floors) lays over it

CX, CZ = S.DOME_CENTRE
ROTUNDA = frozenset(O.disc(CX, CZ, S.DOME_R))
DECK_Y = S.ROOF_FLOOR
DECK = B.SLATE_SMOOTH.block             # the terraces and the dome-room floor, until they are finished
ROOF = B.SLATE_TILE

# --- the entrance (A0, 11-14: three versions, chosen on the pictures; B until then) --------------------
#   A   one doorway in the middle bay, 3 wide, up through the string course
#   B   an arcade: the three bays of the middle pavilion open as arches from the ground to under
#       the string course; the middle one leads into the star hall, an iron gate stands in the
#       two beside it
#   C   one doorway, joined with the great window above it into a single arch the height of the
#       front: the string course and the sunk panel stop at the two pilasters
ENTRANCE = "B"
ENTRANCES = ("A", "B", "C")
ARCADE = (P.AISLE_BAY - 1, P.AISLE_BAY, P.AISLE_BAY + 1)
DOOR_TOP = S.STRING - 1                 # 5: the arches of B, the door of C
# The seat of the station's emblem (A0: one of its kind, 3 x 3, in the frieze of the middle bay): a
# tablet between the two pilasters of the entrance, in their plane, through frieze and cornice and
# one row above, so the cornice breaks round it. The emblem itself is not stone: emblem() says where.
EMBLEM = True
EMBLEM_Y = (S.FRIEZE, S.CORNICE + 1)    # 14..16
# A dark screen behind the entrance and the hall's two cross walls up to it (A0: nobody looks
# through the doorway at the sky behind the building). A stand-in: it goes when main/shell is in.
SCREEN = True
SCREEN_X = S.east_wall_x(P.AISLE_BAY) - 6

# --- which windows are lit, until the light line says ----------------------------------------------------
# The rows are the light line's own answer, written down: sky/_lightkit.window_lit (c220, e76c3721,
# the blue look) asked for every window of table(). L the brightest glass (the window over the
# entrance, the only one), O lit, K a lamp behind a curtain, D dark, B a lowered blind; "." where a
# front has no window. They stand in only while sky/_lightkit.py is not in the tree.
GLASS = {"L": B.WINDOW_LIT, "K": B.WINDOW_CURTAIN, "O": B.WINDOW_FROSTED, "D": B.WINDOW_DARK, "B": B.WINDOW_BLIND}
ROWS = {
    ("east", "main"): "ODOBKODKLKODDOKKO",      # bays 1..17 from the north
    ("east", "base"): "KOBODKDO.OKDKODOD",
    ("west", "main"): "OKODD.......OKOBK",
    ("west", "base"): "ODOKO.......DODOD",
    ("north", "main"): "KO", ("north", "base"): "OB",
    ("south", "main"): "BKDO", ("south", "base"): "DOKO",
    ("apse", "main"): "KOK",                    # bays -1, 0, 1
    ("drum", "drum"): "ODOKKKBKODOBKODDOKBD",   # gores 0..19, 0 looks east
}
FIRST_BAY = {"apse": -1, "drum": 0}     # every other front counts its bays from 1


def _own_glass(front, bay, storey):
    row = ROWS.get((front, storey))
    i = bay - FIRST_BAY.get(front, 1)
    return GLASS.get(row[i]) if row and 0 <= i < len(row) else None


def glass(front, bay, storey):
    """The window role of a bay. The light line decides once its tool is in the tree (it reads the
    windows from _plan.windows(), that is from table() below, which does not come back here);
    until then the rows above."""
    if (front, storey) in ROWS:
        try:
            from ..sky import _lightkit
            window_lit = getattr(_lightkit, "window_lit", None)
        except ImportError:
            window_lit = None
        if window_lit is not None:
            role = window_lit(front, bay, storey)[1]
            if role in B.LIT_WINDOWS + B.DARK_WINDOWS:
                return role
    return _own_glass(front, bay, storey)


# --- the plan ---------------------------------------------------------------------------------------
def footprint():
    """The long building and the rotunda's cylinder, as one body up to the cornice."""
    block = {(x, z) for z in range(S.Z_NORTH, S.Z_SOUTH + 1) for x in range(S.WALL_W, P.east_face(z) + 1)}
    return block | ROTUNDA


APSE_BAYS = {"north-west": -1, "west": 0, "south-west": 1}


def _classify():
    apse = {c: APSE_BAYS[name] for name, (cells, _glass) in P.apse_windows().items() for c in cells}

    def what(x, z, outs):
        if x < S.WALL_W:                                    # the apse: great windows only, no small ones
            return O.Bay("apse", apse[(x, z)], out="west", only=("main",)) if (x, z) in apse else None
        corner = z in (S.Z_NORTH, S.Z_SOUTH)
        for front in ("east", "west"):
            if front not in outs:
                continue
            if corner:
                return O.Pier()                             # both ways, and the block between
            if front == "west" and abs(z - CZ) <= P.WEST_BLIND_Z:
                return None                                 # the last column before the rotunda
            if P.on_pilaster(z):
                return O.Pier(out=(front,))                 # also where the front steps: the return stays plain
            if z in P.END_PIER_ROWS:
                return O.Pier(out=(front,), crest=False)    # the end pavilions' broad corner piers
            return O.Bay(front, P.bays_at(z)[0])
        if not corner:
            return None                                     # a return of the stepped front
        front = "north" if z == S.Z_NORTH else "south"
        if (x - S.WALL_W) % S.BAY == 0:
            return O.Pier(out=(front,))
        if x in (S.WALL_W + 1, P.east_face(z) - 1):
            return O.Pier(out=(front,), crest=False)
        bay = (x - S.WALL_W) // S.BAY + 1
        return O.Bay(front, bay, blind=(front, bay) in P.BLIND_BAYS)

    return what


def _gate(s, op, y):
    """The side arches of the arcade: an iron gate in the glass plane (bars, until the props line
    hangs its own)."""
    return B.IRON_BARS


def _portal(s, op, y):
    """Version C above the door: a stone transom in the glass plane, then the great window's glass
    one row further down than in the other bays."""
    if y <= DOOR_TOP:
        return None
    return B.ASHLAR_FINE.block if y == S.STRING else s.glass(op, "main", B.WINDOW_DARK)


@functools.lru_cache(maxsize=None)
def _shell(entrance):
    body = footprint()
    front = O.ring(body)
    pilasters = [c for c in P.apse_pilasters() if c in front]
    plan = O.Plan(body, _classify(), pilasters=pilasters)
    if entrance == "A":
        plan.door("east", P.AISLE_BAY, S.GROUND, S.STRING, arch=B.ASHLAR_FINE)
    elif entrance == "B":
        for bay in ARCADE:
            plan.door("east", bay, S.GROUND, DOOR_TOP, arch=B.ASHLAR_ROUGH, leaf=None if bay == P.AISLE_BAY else _gate)
    elif entrance == "C":
        plan.door("east", P.AISLE_BAY, S.GROUND, S.PANEL, leaf=_portal)
    else:
        raise ValueError(f"entrance {entrance!r}: one of {ENTRANCES}")
    plan.door("apse", 0, S.GROUND, P.WEST_DOOR_TOP)
    return plan


def shell(entrance=None):
    """The plan of the walls: O.Plan with the entrance (the default version, or the one named) and
    the west door cut."""
    return _shell(entrance or ENTRANCE)


def doors(entrance=None):
    """The doorways of the shell, for whoever hangs leaves, gates and canopies in them:
    [dict(front, bay, cells, inward, y, gate)]. cells are the columns of the wall line the doorway
    goes through (x, z), inward the step into the building, y its (bottom, top) rows; gate is True
    where the doorway is closed by a gate and nobody walks through. The glass plane, where a leaf
    hangs, is one step inward of cells."""
    return [dict(front=op.front, bay=op.bay, cells=list(op.cells), inward=op.inward,
                 y=(op.door[0], DOOR_TOP if op.door[3] is _portal else op.door[1]), gate=op.door[3] is _gate)
            for op in shell(entrance).openings if op.door]


def _vent(op):
    """A grating in the plinth under every second bay of the long fronts."""
    return op.front in ("east", "west") and op.bay % 2 == 0


def _rod(x, z):
    """A lightning rod on every second pilaster of the long fronts, counted from both ends so the
    two halves mirror; none where the drum or the clock tower stands on the wall line."""
    if x not in (S.WALL_W, P.east_face(z)) or not P.on_pilaster(z):
        return False
    k = (z - S.PIL_Z0) // S.BAY
    if min(k, S.N_BAYS - k) % 2:
        return False
    x0, x1 = S.CLOCK_SHAFT_X
    z0, z1 = S.CLOCK_SHAFT_Z
    return not (x0 - 1 <= x <= x1 + 1 and z0 - 1 <= z <= z1 + 1)


def _key(op):
    """A console under the cornice over every great window of three, but not over a doorway that
    has no window of its own height above it, and not where the emblem sits."""
    return (op.front, op.bay) != ("east", P.AISLE_BAY) and (not op.door or op.front == "east")


def order(site=True):
    """The main order, bottom to top (plan 5.1; the rows are the skeleton's).

    site=False gives the same order for a stretch of wall that stands somewhere else (sample()):
    the parapet runs right through and carries no rods."""
    fine, rough, panel = B.ASHLAR_FINE, B.ASHLAR_ROUGH, B.ASHLAR_PANEL
    parapet = O.Parapet(S.PARAPET, fine, panel=panel, inner=fine, rod=B.IRON_ROD if site else None, rods=_rod)
    if site:
        parapet.on(lambda x, z: (x, z) not in ROTUNDA)      # the drum stands there instead
    return [
        O.Plinth(S.PLINTH, B.SLATE_BRICK, vent=B.IRON_GRATE, vents=_vent),
        O.Storey(S.BASE, "base", wall=rough, pier=rough, window=O.Window(P.BASE_WINDOW, grille=B.IRON_BARS)),
        O.Course(S.STRING, fine),
        O.Storey((S.PANEL, S.WINDOW[1]), "main", wall=fine, pier=fine, capital=True,
                 window=O.Window(S.WINDOW, head="arch", apron=panel, blind=panel)),
        O.Frieze(S.FRIEZE, panel, fine, crest=B.ASHLAR_EMBLEM, key=fine, keys=_key),
        O.Cornice(S.CORNICE, fine, gutter=B.OLD_COPPER_CUT),
        parapet,
    ]


def sample(canvas, origin=(0, 0, 0), bays=3, depth=4, glass=None):
    """A stretch of the wings' east front standing on its own, for the test scenes of whatever is
    hung on the wall (window frames, lamps, pipes): `bays` bays of four with their pilasters, the
    wall face at x = depth and looking east, the first pilaster on z = 0; depth columns of building
    behind it. Coordinates are the sample's own, from `origin`. Returns the windows like O.build():
    front "east", bays 1.. from the north."""
    body = O.box(0, 0, depth, bays * S.BAY)
    plan = O.Plan(body, O.bays(body, bay=S.BAY, fronts=("east",)))
    return O.build(canvas, plan, order(site=False), origin, glass=glass)


# --- the roofs ----------------------------------------------------------------------------------------
def _on_gable(x, z):
    return abs(z) in P.GABLE_Z and S.WALL_W < x < S.WALL_E


def terraces():
    """The columns of the flat roofs, by name. They get a plain deck at DECK_Y here, a stand-in
    that closes the shell; the package that finishes a terrace runs later and lays over it.

    "north", "south"   over the end pavilions (the clock tower and the small dome stand on them)
    "middle"           the two corners between the drum, the gable walls and the east parapet
    "dome room"        the floor inside the drum
    """
    plan = shell()
    out = {"north": set(), "south": set(), "middle": set(), "dome room": set()}
    for x, z in plan.leaf | plan.core:
        if P.roof_steps(x, z) is None and not _on_gable(x, z):
            name = "dome room" if (x, z) in ROTUNDA else "middle" if abs(z) < P.GABLE_Z[0] else "north" if z < 0 else "south"
            out[name].add((x, z))
    return out


def _roofs(canvas, plan, origin):
    """Close the top: a deck at y 17 over the pavilions and inside the drum, slate in half-block
    steps over the wings (c178's roof plan: eaves at 17.0 behind the parapets, ridge at 20.0),
    stepped gable walls where the two meet."""
    ox, oy, oz = origin
    for x, z in plan.leaf | plan.core:
        steps = P.roof_steps(x, z)
        if steps is not None:
            if steps % 2:
                canvas.set(ox + x, oy + DECK_Y + steps // 2, oz + z, f"{ROOF.slab}[type=bottom]")
            else:
                canvas.set(ox + x, oy + DECK_Y - 1 + steps // 2, oz + z, f"{ROOF.slab}[type=top]")
        elif _on_gable(x, z):
            steps = min(x - S.WALL_W, S.WALL_E - x, P.ROOF_RIDGE_STEPS) - 1
            for y in range(DECK_Y - 1, DECK_Y + steps // 2 + 1):
                canvas.set(ox + x, oy + y, oz + z, B.ASHLAR_FINE.block)
        else:
            canvas.set(ox + x, oy + DECK_Y, oz + z, DECK)


# --- the entrance's own stones ------------------------------------------------------------------------
def _arcade_keys(canvas, plan, origin):
    """Version B: a console hung under the string course over the crown of each arch, like the ones
    under the cornice over the great windows."""
    ox, oy, oz = origin
    for bay in ARCADE:
        op = plan.bays[("east", bay)]
        x, z = O.step(op.middle(), op.out)
        canvas.set(ox + x, oy + DOOR_TOP, oz + z, f"{B.ASHLAR_FINE.stairs}[facing={O.NAME[op.inward]},half=top]")


def emblem():
    """The seat of the station's emblem: dict(cells, out, face_x). cells are the nine blocks of the
    tablet (x, y, z), the middle one last; out is the side it looks to; face_x is the plane of its
    face (a point coordinate): whatever is hung on it stands east of that."""
    x = S.east_wall_x(P.AISLE_BAY) + S.DEPTH_PILASTER
    rows = P.window_rows(P.AISLE_BAY)
    ys = range(EMBLEM_Y[0], EMBLEM_Y[1] + 1)
    middle = (x, ys[1], rows[1])
    cells = [(x, y, z) for y in ys for z in rows if (x, y, z) != middle]
    return dict(cells=cells + [middle], out="east", face_x=x + 1.0)


def _emblem(canvas, origin):
    """Set the tablet and break the cornice round it: no moulding and no gutter in front of it, a
    coping on top."""
    ox, oy, oz = origin
    seat = emblem()
    for x, y, z in seat["cells"]:
        canvas.set(ox + x, oy + y, oz + z, B.ASHLAR_PANEL.block)
    for x, z in {(x, z) for x, _, z in seat["cells"]}:
        for y in (S.CORNICE, S.CORNICE + 1):
            canvas.clear(ox + x + 1, oy + y, oz + z)
        canvas.set(ox + x, oy + EMBLEM_Y[1] + 1, oz + z, f"{B.ASHLAR_FINE.slab}[type=bottom]")
    x, y, z = seat["cells"][-1]
    canvas.set(ox + x, oy + y, oz + z, B.ASHLAR_EMBLEM)


def _screen(canvas, origin):
    """The stand-in behind the entrance: a screen across the hall and the hall's two cross walls
    from it to the front, in two dark stones laid in alternate courses, as high as the string
    course. Whoever looks in through a doorway sees the back of a vestibule."""
    ox, oy, oz = origin
    dark = (B.SLATE_TILE.block, B.SLATE_BRICK.block)
    z0, z1 = P.CROSS_Z
    for y in range(S.GROUND, S.STRING + 1):
        for z in range(z0, z1 + 1):
            canvas.set(ox + SCREEN_X, oy + y, oz + z, dark[y % 2])
        for z in (z0, z1):
            for x in range(SCREEN_X + 1, P.east_face(z) + S.DEPTH_GLASS):
                canvas.set(ox + x, oy + y, oz + z, dark[y % 2])


def crowned():
    """True when main/dome.py is in the tree: the rotunda's drum and dome are that package's then,
    and the massing of _dome.py is not built here any more."""
    return importlib.util.find_spec(__package__ + ".dome") is not None


# --- the package --------------------------------------------------------------------------------------
def build(canvas, origin=(0, 0, 0), entrance=None):
    entrance = entrance or ENTRANCE
    plan = shell(entrance)
    O.build(canvas, plan, order(), origin, glass=glass)
    if entrance == "B":
        _arcade_keys(canvas, plan, origin)
    if EMBLEM:
        _emblem(canvas, origin)
    _roofs(canvas, plan, origin)
    if SCREEN:
        _screen(canvas, origin)
    if not crowned():
        _dome.build(canvas, origin, glass=glass)
    return 0


@functools.lru_cache(maxsize=None)
def _windows(glazed, entrance):
    c = Canvas()
    how = glass if glazed else None
    return tuple(O.build(c, shell(entrance), order(), glass=how) + _dome.drum(c, glass=how))


TABLE_KEYS = ("front", "bay", "storey", "cells", "inward", "y")


def table():
    """The windows the shell has, blind bays left out: [dict(front, bay, storey, cells, inward, y)].
    This is what main/_plan.windows() hands to the other lines. It says where the windows are and
    nothing about their glass: the light line reads it to decide which are lit, so making it must
    not ask the light line. The windows are those of the entrance version that is built (ENTRANCE):
    a bay that is a doorway has no base-storey window."""
    return [{k: w[k] for k in TABLE_KEYS} for w in _windows(False, ENTRANCE) if not w["blind"]]


def windows(entrance=None):
    """The same windows with the glass that stands in each: table() plus glass (a block state)."""
    return [{k: w[k] for k in TABLE_KEYS + ("glass",)} for w in _windows(True, entrance or ENTRANCE) if not w["blind"]]


# --- self-check and drawings ----------------------------------------------------------------------------
def check(entrance=None):
    """What can be told without a picture; returns the findings as lines (none is good)."""
    out = []
    entrance = entrance or ENTRANCE
    c = Canvas()
    build(c, entrance=entrance)
    name = lambda x, y, z: (c.get(x, y, z) or "air").partition("[")[0]
    glassy = {f.block for f in B.LIT_WINDOWS + B.DARK_WINDOWS}
    doorways = {d["bay"] for d in doors(entrance) if d["front"] == "east"}

    # 1. three depths in every bay of the east front, at the middle of the great window and of the small one
    for bay in range(1, S.N_BAYS + 1):
        xw = S.east_wall_x(bay)
        for z in P.window_rows(bay):
            for storey, y in (("main", 10), ("base", 3)):
                if bay in doorways and storey == "base":
                    continue
                want = "air" if storey == "main" else B.IRON_BARS
                if name(xw, y, z) != want or name(xw + S.DEPTH_GLASS, y, z) not in glassy or c.has(xw + 1, y, z):
                    out.append(f"east bay {bay} {storey}: row z {z} is not opening / glass one behind / nothing in front")
        for k in (bay - 1, bay):
            z = S.pilaster_z(k)
            xf = P.east_face(z)
            if name(xf + S.DEPTH_PILASTER, 10, z) != B.ASHLAR_FINE.block or name(xf, 10, z) != B.ASHLAR_FINE.block:
                out.append(f"east pilaster {k}: no pilaster one block in front of the wall at z {z}")
    # 2. the cornice reaches two blocks out along the whole east front (beside a pavilion: two out
    #    from the pavilion's face, it turns the corner there), the gutter lies on it
    seat = {z for _, _, z in emblem()["cells"]} if EMBLEM else set()
    for z in range(S.Z_NORTH, S.Z_SOUTH + 1):
        x = max(P.east_face(n) for n in (z - 1, z, z + 1) if S.Z_NORTH <= n <= S.Z_SOUTH) + S.DEPTH_CORNICE
        if z in seat:
            if c.has(x, S.CORNICE, z) or name(x - 1, S.CORNICE, z) not in (B.ASHLAR_PANEL.block, B.ASHLAR_EMBLEM):
                out.append(f"emblem: the cornice does not break round the tablet at z {z}")
        elif name(x, S.CORNICE, z) != B.ASHLAR_FINE.stairs or name(x, S.CORNICE + 1, z) != B.OLD_COPPER_CUT.slab:
            out.append(f"cornice: not two blocks out with its gutter at z {z}")
    # 3. the windows are the ones of c178's plan (a bay that is a doorway has no small window)
    def table(ws):
        return {(w["front"], w["bay"], w["storey"]): (sorted(w["cells"]), tuple(w["inward"]), tuple(w["y"])) for w in ws}
    mine = table(w for w in windows(entrance) if w["front"] != "drum")
    theirs = table(w for w in P.plan_windows()
                   if not (w["front"] == "east" and w["bay"] in doorways and w["storey"] == "base"))
    for key in sorted(set(mine) | set(theirs), key=str):
        if mine.get(key) != theirs.get(key):
            out.append(f"window {key}: built {mine.get(key)}, planned {theirs.get(key)}")
    # 4. the director's rules for the windows, on the entrance front's main storey: at least a fifth
    #    dark, no two neighbouring bays both lit, the brightest glass over the entrance only
    row = {w["bay"]: w["glass"] for w in windows(entrance) if (w["front"], w["storey"]) == ("east", "main")}
    dark = sum(g in {f.block for f in B.DARK_WINDOWS} for g in row.values())
    lit = {bay for bay, g in row.items() if g in (B.WINDOW_LIT.block, B.WINDOW_FROSTED.block)}
    if dark < len(row) / 5.0:
        out.append(f"east main storey: {dark} dark windows of {len(row)}, fewer than a fifth")
    if any(bay + 1 in lit for bay in lit):
        out.append(f"east main storey: two neighbouring bays are both lit: {sorted(lit)}")
    if [bay for bay, g in row.items() if g == B.WINDOW_LIT.block] != [P.AISLE_BAY]:
        out.append("east main storey: the brightest glass is not the entrance window's alone")
    # 5. the doorway is open from the court into the hall, and nobody sees through the hall
    for z in P.window_rows(P.AISLE_BAY):
        for x in range(S.east_wall_x(P.AISLE_BAY) - 1, S.east_wall_x(P.AISLE_BAY) + 3):
            if any(c.has(x, y, z) for y in range(S.GROUND, DOOR_TOP)):      # the row of the arch's corners is above
                out.append(f"entrance: something stands in the doorway at x {x}, z {z}")
    for d in doors(entrance):
        if d["front"] != "east":
            continue
        for x, z in d["cells"]:
            for y in range(d["y"][0], d["y"][1] + 1):
                if not any(c.has(n, y, z) for n in range(S.WALL_W, x - 1)):
                    out.append(f"entrance: bay {d['bay']} is open right through the building at z {z}, y {y}")
    return out


def _drawings(entrance):
    c = Canvas()
    build(c, entrance=entrance)
    face = S.east_wall_x(P.AISLE_BAY)
    print(f"ENTRANCE {entrance}\n")
    print("PLAN (north up; # wall line, : inner leaf, P pilaster, w window bay, b blind bay, D doorway, + cornice)\n")
    print(O.drawing(shell(entrance)))
    print("\nEAST ELEVATION, seen from the court (south on the left). What stands in front:\n")
    print(O.elevation(c, "east", (S.Z_NORTH - 2, S.Z_SOUTH + 2), (S.GROUND, S.DOME_APEX + 1), face + 3, S.WALL_W))
    print("\nThe same, how far back the first block stands (0 = the cornice plane of the middle pavilion):\n")
    print(O.elevation(c, "east", (S.Z_NORTH - 2, S.Z_SOUTH + 2), (S.GROUND, S.ROOF_STAND + 1), face + 2, S.WALL_W, depth=True))
    for title, z in (("through a pilaster of the wing", S.pilaster_z(4)), ("through the middle of a wing bay", S.pilaster_z(4) + 2),
                     ("through the entrance", 0)):
        print(f"\nSECTION {title} (z = {z}; west on the left):\n")
        print(O.section(c, "z", z, (P.east_face(z) - 3, P.east_face(z) + 3), (S.GROUND, S.ROOF_STAND + 2)))
    print("\nLetters: S slate brick, R rough ashlar, F dressed ashlar, P panel, E emblem, C copper gutter, M deck, T slate roof,")
    print("L K O lit / curtained / frosted window, D B dark / shuttered window, # bars, % grating, ! rod, I riveted iron,")
    print("V G X verdigris plate / rib / dark run. Small letters are the same family's stairs and slabs.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "check" not in args:
        _drawings(next((a for a in args if a in ENTRANCES), ENTRANCE))
        print()
    found = [f"{e}: {line}" for e in ENTRANCES for line in check(e)]
    print("\n".join(found) if found else
          "self-check: three depths, cornice and emblem, windows, the window rules, doorways -- all as planned, entrances A, B, C")
    sys.exit(1 if found else 0)
