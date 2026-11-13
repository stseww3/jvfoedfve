"""Grid plans of the main building: what stands on every block column at three levels.

Asked for by A0's first review (plan/reviews/R1-first-designs.md, 3.6): a block-by-block plan of
the ground floor and the main floor, with the telescope pier, the star hall, both stairs, the wing
rooms, the tower base, the end pavilions and every door opening, and with the overlap between the
rooms and the rotunda cylinder solved on the drawing.

This module is the one source for the drawings in plan/parts/main.md and for the shells that the
main line builds, so the drawing and the building cannot drift apart. Every coordinate that the
review locked comes from the skeleton; what is decided here on top of it is listed under
"decisions of the main line" and repeated in the drawing's notes.

    python3 -m scenes.obs.main._plan            # print the three plans and the tables
    python3 -m scenes.obs.main._plan ground     # one of: ground, main, roof, tables

The name starts with an underscore, so the category's auto-discovery does not treat it as a work
package.
"""
import math
import sys

from ..common import skeleton as S

# --- the drawing window ---------------------------------------------------------------------
X_MIN, X_MAX = -11, 20
Z_MIN, Z_MAX = -37, 37

# --- the rotunda's rings (block centre to block centre, like the massing model) -------------
CX, CZ = S.DOME_CENTRE
R_FACE = S.DOME_R           # 13: the wall face
R_GLASS = R_FACE - 1        # 12: glass and inner leaf
R_PILASTER = R_FACE + 1     # 14: pilasters
R_CLEAR = R_FACE - 2        # 11: the clear inside ("inner diameter 22" around the centre block)

# --- decisions of the main line (A3) on top of the skeleton ---------------------------------
# Cross walls stand on pilaster lines, so no wall ever lands behind a window.
CROSS_Z = S.STAR_HALL_Z                                   # -6 and 6: star hall / wings
PAVILION_Z = (S.pilaster_z(2), S.pilaster_z(15))          # -26 and 26: wings / end pavilions
HALL_X = (S.ROOM_X[0], S.east_wall_x(9) + S.DEPTH_GLASS - 1)   # 2..15, clear
HALL_Z = (CROSS_Z[0] + 1, CROSS_Z[1] - 1)                 # -5..5, clear
WING_N_Z = (PAVILION_Z[0] + 1, CROSS_Z[0] - 1)            # -25..-7, clear
WING_S_Z = (CROSS_Z[1] + 1, PAVILION_Z[1] - 1)            # 7..25, clear
END_PIER_ROWS = (S.Z_NORTH + 1, PAVILION_Z[0] - 1, PAVILION_Z[1] + 1, S.Z_SOUTH - 1)   # -33, -27, 27, 33
PIER_HALF = 1                                             # the pier is 3 x 3 (skeleton: provisional)
CORE_HALF = PIER_HALF + 1                                 # the ring stair wraps it: 5 x 5
ARCADE_PIERS_Z = (-2, 2)                                  # the west arcade of the hall: three arches
STAIR_X = (-6, 0)                                         # grand stair: seven steps, rising west
STAIR_Z = (-1, 1)
LANDING_X = -7                                            # its landing under the west window
DOOR_Z = (-1, 1)                                          # both doors on the axis (bay 9)
ROOM_DOOR_X = (7, 8)                                      # gallery -> wing room, through a cross wall
APSE_BAYS = 7                                             # pilaster spacing on the arc, as bays
APSE_BAY_DEG = 19.5                                       # the outermost pilasters land on the junction
WEST_BLIND_Z = 13                                         # |z| <= 13 on the west wall is behind the rotunda
# Roofs follow the five parts of the front: flat terraces over the three pavilions (the middle one
# is as wide as the drum, not as the entrance), pitched slate over the wings between gable walls.
GABLE_Z = (S.pilaster_z(12), PAVILION_Z[1])               # |z| = 14 and 26: gable walls on pilaster lines
ROOF_Z = (GABLE_Z[0] + 1, GABLE_Z[1] - 1)                 # |z| 15..25: the pitched roofs
ROOF_RIDGE_STEPS = 7                                      # half-block steps from eave to ridge
BASE_WINDOW = (S.BASE[0] + 1, S.BASE[0] + 2)              # y 3..4: the small windows of the base storey
BLIND_BAYS = (("north", 3), ("north", 4))                 # the clock tower stands behind them: stone for glass
SMALL_DOME_CENTRE = ((S.SMALL_DOME_X[0] + S.SMALL_DOME_X[1]) // 2,
                     (S.SMALL_DOME_Z[0] + S.SMALL_DOME_Z[1]) // 2)     # (12, 30)

# heights that go with the plans (feet levels unless said otherwise)
GALLERY_DECK_Y = S.STRING        # 6: the deck block of galleries, landing and lanes; feet at 7
ROOF_EAVE_TOP = 17.0             # top surface of the roof next to the parapet
ROOF_STEP = 0.5                  # rise per block: a 1:2 slope laid in slabs
ROOF_RIDGE_TOP = ROOF_EAVE_TOP + ROOF_STEP * (ROOF_RIDGE_STEPS - 1)   # 20.0

LEGEND = [
    ("#", "wall (solid through this storey)"),
    ("P", "pilaster, one block in front of the wall face"),
    ("w", "window opening in the outer leaf"),
    ("g", "glass, in the inner-leaf plane"),
    ("b", "blind window: the same recess, backed with stone instead of glass"),
    ("D", "door opening, passable"),
    ("L", "locked door (set dressing; the space behind is closed)"),
    (".", "floor or deck at this level"),
    ("o", "void: open to the level below"),
    ("r", "deck with the railing standing on it"),
    ("c", "kerb and bars of the ring stair, at the height of the stair beside it"),
    ("T", "telescope pier"),
    ("< > ^ v", "stair, the arrow points uphill (west, east, north, south)"),
    ("+", "landing of the ring stair"),
    ("x", "closed space: not entered in the first version"),
    ("t", "roof terrace, deck at y 17 (top at 18.0)"),
    ("0-6", "slate roof, half-block steps above y 17.0 (0 = gutter, 6 = ridge at y 20.0)"),
    ("G", "gable wall closing the end of a pitched roof"),
    ("p", "parapet"),
]


# --- geometry helpers -------------------------------------------------------------------------
def ring(x, z):
    """Which ring of the rotunda a column is on: the rounded distance from the dome centre."""
    return int(math.hypot(x - CX, z - CZ) + 0.5)


def west_angle(x, z):
    """Angle of a column seen from the dome centre: 0 on the west axis, positive to the south."""
    return math.degrees(math.atan2(z - CZ, CX - x))


def on_pilaster(z):
    return (z - S.PIL_Z0) % S.BAY == 0


def bays_at(z):
    """The bay a row belongs to; a pilaster row belongs to the bays on both sides."""
    k, rest = divmod(z - S.PIL_Z0, S.BAY)
    bays = (k, k + 1) if rest == 0 else (k + 1,)
    return [b for b in bays if 1 <= b <= S.N_BAYS]


def east_face(z):
    """x of the east wall face on a row; a pilaster row takes the face that stands further out."""
    return max(S.east_wall_x(b) for b in bays_at(z))


def _apse_cells(r):
    """Columns of one ring that stand west of the main building's west wall."""
    return [(x, z) for x in range(X_MIN, S.WALL_W) for z in range(Z_MIN, Z_MAX + 1) if ring(x, z) == r]


def apse_pilasters():
    """One pilaster column per pilaster angle: the ring-14 column closest to it."""
    cells = _apse_cells(R_PILASTER)
    out = []
    for i in range(APSE_BAYS // 2 + 1):
        for sign in (-1, 1):
            a = sign * (i + 0.5) * APSE_BAY_DEG
            out.append(min(cells, key=lambda c: abs(west_angle(*c) - a)))
    return sorted(set(out))


def apse_windows():
    """{name: (three opening columns on the wall face, the glass column one block behind each)}.

    A raster circle of this radius has only three runs straight enough to carry a three-wide
    arched window: the west one on the axis and the one on either side of it. Everywhere else the
    wall steps diagonally, where three columns along the ring make an L and cannot take an arched
    head, so the flanks stay solid."""
    xa = CX - R_FACE                                        # -9: the run on the west axis
    out = {"west": [(xa, z) for z in range(DOOR_Z[0], DOOR_Z[1] + 1)]}
    side = sorted(c for c in _apse_cells(R_FACE) if c[0] == xa + 1)     # the next run: x = -8
    out["north-west"] = [c for c in side if c[1] < CZ]
    out["south-west"] = [c for c in side if c[1] > CZ]
    return {name: (cells, [(x + 1, z) for x, z in cells]) for name, cells in out.items()}


def ring_stair():
    """The ring stair round the pier, one turn: [(x, z, kind, feet after this column)].

    It starts on the gallery (feet 7) at the south-west corner of the core and climbs east, north,
    west and south again, eleven steps and three corner landings, to the dome-room floor (feet 18).
    """
    c = CORE_HALF
    path = [(CX - c, CZ + c, "+")]
    path += [(CX + i, CZ + c, ">") for i in range(-c + 1, c)]
    path += [(CX + c, CZ + c, "+")]
    path += [(CX + c, CZ - i, "^") for i in range(-c + 1, c)]
    path += [(CX + c, CZ - c, "+")]
    path += [(CX - i, CZ - c, "<") for i in range(-c + 1, c)]
    path += [(CX - c, CZ - c, "+")]
    path += [(CX - c, CZ + i, "v") for i in range(-c + 1, 1)]
    feet, out = S.STAND, []
    for x, z, kind in path:
        if kind != "+":
            feet += 1
        out.append((x, z, kind, feet))
    return out


def grand_stair():
    """The grand stair in the apse: [(x, feet after this step)], rising west from the hall floor."""
    return [(x, S.GROUND + i + 1) for i, x in enumerate(range(STAIR_X[1], STAIR_X[0] - 1, -1))]


def roof_steps(x, z):
    """Half-block steps of the slate roof above the eave on a column, or None off the roofs.
    The ridge runs north-south; both slopes fall to a gutter behind the parapets."""
    if not ROOF_Z[0] <= abs(z) <= ROOF_Z[1]:
        return None
    xe = east_face(z)
    if not S.WALL_W < x < xe:
        return None
    return min(x - S.WALL_W, xe - x, ROOF_RIDGE_STEPS) - 1


def stair_guard():
    """Columns that carry the ring stair's kerb and bars, along its outer side (the west side is
    closed by the hall's west wall). The start of the stair stays open to the south gallery."""
    c = CORE_HALF + 1
    cells = {(CX + i, CZ + s * c) for i in range(-c + 1, c + 1) for s in (-1, 1)}
    cells |= {(CX + c, CZ + i) for i in range(-c, c + 1)}
    cells.discard((CX - CORE_HALF, CZ + c))
    return sorted(cells)


def stair_air():
    """What must stay empty over the ring stair: [(x, z, feet, top)], air in feet <= y < top.

    A walker is 1.8 tall and 0.6 wide. Stepping up, the feet are already on the next step while the
    trailing 0.1 of the body is still over this column, so a column followed by a step up needs a
    whole block more than standing room: three blocks, as on every staircase in the game."""
    stair = ring_stair()
    feet_after = [c[3] for c in stair[1:]] + [S.ROOF_STAND]
    return [(x, z, feet, feet + (3 if nxt > feet else 2)) for (x, z, _, feet), nxt in zip(stair, feet_after)]


def _open_at(y):
    """Columns where the block at height y has to be air for the ring stair."""
    return [(x, z) for x, z, feet, top in stair_air() if feet <= y < top]


def floor_opening():
    """Columns of the dome-room floor that must be open for the ring stair. The last step is not
    in it: its own block lies in the floor."""
    return _open_at(S.ROOF_FLOOR)


def ceiling_opening():
    """The same for the star hall's ceiling."""
    return _open_at(S.STAR_HALL_CEIL)


def window_rows(bay):
    """Rows of the window of a bay of the long fronts: three, or two next to a corner pier."""
    return [z for z in range(S.pilaster_z(bay - 1) + 1, S.pilaster_z(bay)) if z not in END_PIER_ROWS]


def windows():
    """Every glazed window of the main building, for whoever lights or frames them:
    [dict(front, bay, storey, cells, inward, y)].

    front and bay name the window: "east" and "west" count the skeleton's bays 1..17 from the
    north; "north" and "south" count the end walls' bays 1..4 from the west; "apse" has -1, 0, 1
    (north-west, west, south-west). storey is "base" or "main". cells are the glass columns
    (x, z); inward is the step from the glass into the building; y is the glass's (bottom, top)."""
    out = []

    def add(front, bay, cells, inward, base=True):
        for storey, y in (("base", BASE_WINDOW), ("main", S.WINDOW)):
            if storey == "main" or base:
                out.append(dict(front=front, bay=bay, storey=storey, cells=cells, inward=inward, y=y))

    for bay in range(1, S.N_BAYS + 1):
        rows = window_rows(bay)
        xg = S.east_wall_x(bay) + S.DEPTH_GLASS
        add("east", bay, [(xg, z) for z in rows], (-1, 0), base=rows != list(range(DOOR_Z[0], DOOR_Z[1] + 1)))
        if all(abs(z - CZ) > WEST_BLIND_Z for z in rows):
            add("west", bay, [(S.WALL_W - S.DEPTH_GLASS, z) for z in rows], (1, 0))
    for front, zf, out_step in (("north", S.Z_NORTH, -1), ("south", S.Z_SOUTH, 1)):
        for bay, cols in end_wall_bays(zf):
            if (front, bay) not in BLIND_BAYS:
                add(front, bay, [(x, zf - out_step) for x in cols], (0, -out_step))
    names = {"north-west": -1, "west": 0, "south-west": 1}
    for name, (opening, glass) in apse_windows().items():
        add("apse", names[name], glass, (1, 0), base=name != "west")
    return out


def end_wall_bays(zf):
    """[(bay, window columns)] of an end wall: bays of four from the west, corner piers left out."""
    xe = east_face(zf)
    return [(i + 1, [x for x in range(S.WALL_W + S.BAY * i + 1, min(S.WALL_W + S.BAY * (i + 1), xe))
                     if x not in (S.WALL_W + 1, xe - 1)])
            for i in range((xe - S.WALL_W) // S.BAY)]


# --- painting ---------------------------------------------------------------------------------
class Grid(dict):
    def put(self, x, z, ch):
        self[(x, z)] = ch

    def box(self, x0, x1, z0, z1, ch):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                self[(x, z)] = ch

    def text(self):
        head = "       x " + "".join("%d" % (abs(x) % 10) for x in range(X_MIN, X_MAX + 1))
        rows = [head]
        for z in range(Z_MIN, Z_MAX + 1):
            line = "".join(self.get((x, z), " ") for x in range(X_MIN, X_MAX + 1)).rstrip()
            rows.append("z %4d  %s" % (z, line))
        return "\n".join(rows)


def _envelope(g):
    """Outer walls of the long building in three depths: pilaster, wall face, inner leaf.

    The end pavilions get corner piers two blocks wide: the window column next to each of their
    corners is solid, which leaves two windows of two flanking the middle pilaster. Without it
    the glass of two fronts would meet in a corner column with no room behind it, and the corners
    of the clock-tower shaft (one block in from the pavilion's) would stand on window columns."""
    for z in range(S.Z_NORTH, S.Z_SOUTH + 1):
        pil = on_pilaster(z)
        solid = pil or z in END_PIER_ROWS
        f = east_face(z)                                   # the east front, five parts
        g.put(f, z, "#" if solid else "w")
        g.put(f + S.DEPTH_GLASS, z, "#" if solid else "g")
        if pil:
            g.put(f + S.DEPTH_PILASTER, z, "P")
            for x in range(S.WALL_E, f):                   # the return where the front steps out
                g.put(x, z, "#")
        solid = solid or abs(z - CZ) <= WEST_BLIND_Z       # the west wall; blind behind the rotunda
        g.put(S.WALL_W, z, "#" if solid else "w")
        g.put(S.WALL_W - S.DEPTH_GLASS, z, "#" if solid else "g")
        if pil and abs(z - CZ) > WEST_BLIND_Z:
            g.put(S.WALL_W - S.DEPTH_PILASTER, z, "P")
    for zf, out in ((S.Z_NORTH, -1), (S.Z_SOUTH, 1)):      # the two end walls
        xe = east_face(zf)
        for x in range(S.WALL_W, xe + 1):
            pil = (x - S.WALL_W) % S.BAY == 0
            solid = pil or x in (S.WALL_W + 1, xe - 1)
            g.put(x, zf, "#" if solid else "w")
            if S.WALL_W < x < xe:
                g.put(x, zf - out, "#" if solid else "g")
            if pil:
                g.put(x, zf + out, "P")
        g.put(S.WALL_W - 1, zf + out, "P")                 # the corner blocks
        g.put(xe + 1, zf + out, "P")


def _tower_base(g):
    """The clock tower stands on the north end pavilion from the ground: the shaft walls run down
    to it and the north front of the shaft is blind. The shaft's east corners stand on the
    pavilion's corner piers (see _envelope)."""
    x0, x1 = S.CLOCK_SHAFT_X
    z0, z1 = S.CLOCK_SHAFT_Z
    for bay, cols in end_wall_bays(S.Z_NORTH):             # blind windows in front of the shaft
        if ("north", bay) in BLIND_BAYS:
            for x in cols:
                g.put(x, S.Z_NORTH, "b")
                g.put(x, S.Z_NORTH + 1, "#")
    g.box(x0, x0, z0 + 1, z1, "#")                         # the shaft's west wall
    g.box(x0, x1 - 1, z1, z1, "#")                         # and its south wall
    g.box(x0 + 1, x1 - 2, z0 + 1, z1 - 1, "x")             # the well


def _apse_shell(g):
    """The part of the rotunda that stands outside the west wall: a cylinder from the ground."""
    for x in range(X_MIN, S.WALL_W):
        for z in range(Z_MIN, Z_MAX + 1):
            r = ring(x, z)
            if r in (R_FACE, R_GLASS):
                g.put(x, z, "#")
            elif r <= R_CLEAR:
                g.put(x, z, ".")
    for opening, glass in apse_windows().values():
        for (x, z), (gx, gz) in zip(opening, glass):
            g.put(x, z, "w")
            g.put(gx, gz, "g")
            g.put(gx + 1, gz, ".")       # the column behind the glass stays empty (A2's lights)
    for x, z in apse_pilasters():
        g.put(x, z, "P")


def _closed_rooms(g, wings):
    """Spaces that stay shut in the first version."""
    xa, xb = S.ROOM_X
    g.box(xa, xb, S.Z_NORTH + 2, PAVILION_Z[0] - 1, "x")   # north end pavilion
    g.box(xa, xb + 1, PAVILION_Z[1] + 1, S.Z_SOUTH - 2, "x")   # south end pavilion (face at 16)
    if wings:
        g.box(xa, xb, WING_N_Z[0], WING_N_Z[1], "x")
        g.box(xa, xb, WING_S_Z[0], WING_S_Z[1], "x")


def _partitions(g):
    for z in CROSS_Z:
        g.box(S.WALL_W, east_face(z) - 2, z, z, "#")
    for z in PAVILION_Z:
        g.box(S.ROOM_X[0], east_face(z) - 2, z, z, "#")


def _arcade(g, level):
    """The hall's west wall is an arcade of three arches into the apse."""
    for x in (S.WALL_W, S.WALL_W + 1):
        for z in range(HALL_Z[0], HALL_Z[1] + 1):
            if z in ARCADE_PIERS_Z:
                g.put(x, z, "#")
            elif STAIR_Z[0] <= z <= STAIR_Z[1]:
                g.put(x, z, "." if level == "ground" else "o")
            else:
                g.put(x, z, ".")


def _grand_stair(g, level):
    for x, _ in grand_stair():
        for z in range(STAIR_Z[0], STAIR_Z[1] + 1):
            g.put(x, z, "<")
    for x in range(STAIR_X[0], S.WALL_W):                  # the cheeks; the railing stands on them
        for z in (STAIR_Z[0] - 1, STAIR_Z[1] + 1):
            g.put(x, z, "#" if level == "ground" else "r")


def _pier(g):
    g.box(CX - PIER_HALF, CX + PIER_HALF, CZ - PIER_HALF, CZ + PIER_HALF, "T")


def plan_ground():
    """The ground floor, feet at y 0; cut through the base storey."""
    g = Grid()
    _envelope(g)
    _apse_shell(g)
    _closed_rooms(g, wings=True)
    _tower_base(g)
    g.box(HALL_X[0], HALL_X[1], HALL_Z[0], HALL_Z[1], ".")
    _partitions(g)
    _arcade(g, "ground")
    _grand_stair(g, "ground")
    _pier(g)
    for z in range(DOOR_Z[0], DOOR_Z[1] + 1):
        f = east_face(z)                                   # the main door, through both leaves
        g.put(f, z, "D")
        g.put(f + S.DEPTH_GLASS, z, "D")
        g.put(CX - R_FACE, z, "D")                         # the west door to the sunset platform
        g.put(CX - R_GLASS, z, "D")
    for z in CROSS_Z:                                      # the wings' ground floor is locked
        g.box(ROOM_DOOR_X[0], ROOM_DOOR_X[1], z, z, "L")
    return g


def plan_main():
    """The main floor, feet at y 7; cut through the great windows."""
    g = Grid()
    _envelope(g)
    _apse_shell(g)
    _closed_rooms(g, wings=False)
    _tower_base(g)
    xa, xb = S.ROOM_X
    g.box(xa, xb, WING_N_Z[0], WING_N_Z[1], ".")           # the time-service room's shell
    g.box(xa, xb, WING_S_Z[0], WING_S_Z[1], ".")           # the star-chart room's shell
    # the star hall at gallery level: a void with a deck round it
    g.box(HALL_X[0], HALL_X[1], HALL_Z[0], HALL_Z[1], "o")
    for z in (HALL_Z[0], HALL_Z[1]):                       # north and south galleries
        g.box(HALL_X[0], HALL_X[1], z, z, ".")
        inner = z + (1 if z < 0 else -1)
        g.box(HALL_X[0] + 1, HALL_X[1] - 1, inner, inner, "r")
        g.put(HALL_X[0], inner, ".")
    g.box(HALL_X[1], HALL_X[1], HALL_Z[0], HALL_Z[1], ".")     # the east gallery over the door
    g.box(HALL_X[1] - 1, HALL_X[1] - 1, HALL_Z[0] + 2, HALL_Z[1] - 2, "r")
    _partitions(g)
    _arcade(g, "main")
    _grand_stair(g, "main")
    for x, z in stair_guard():
        g.put(x, z, "c")
    for x, z, kind, _ in ring_stair():
        g.put(x, z, kind)
    xw = CX - CORE_HALF                                    # x 2: the hall's west end, by the arcade
    g.put(xw, CZ + CORE_HALF, ".")                         # the ring stair starts from the deck here,
    g.put(xw, CZ + CORE_HALF + 1, ".")                     # reached from the south gallery;
    g.put(xw, CZ + CORE_HALF - 1, "r")                     # everything else here that borders the
    g.put(xw, CZ - CORE_HALF - 1, "r")                     # void gets a railing
    g.put(xw, HALL_Z[0] + 1, "r")
    _pier(g)
    for z in CROSS_Z:
        g.box(ROOM_DOOR_X[0], ROOM_DOOR_X[1], z, z, "D")
    return g


def plan_roof():
    """The roof and the dome-room floor, feet at y 18."""
    g = Grid()
    for z in range(S.Z_NORTH, S.Z_SOUTH + 1):              # parapets on the wall faces
        g.put(east_face(z), z, "p")
        g.put(S.WALL_W, z, "p")
    for zf in (S.Z_NORTH, S.Z_SOUTH):
        g.box(S.WALL_W, east_face(zf), zf, zf, "p")
    for z in range(S.Z_NORTH + 1, S.Z_SOUTH):
        for x in range(S.WALL_W + 1, east_face(z)):
            steps = roof_steps(x, z)
            g.put(x, z, "G" if abs(z) in GABLE_Z else "t" if steps is None else str(steps))
    x0, x1 = S.CLOCK_SHAFT_X                               # the clock-tower shaft
    z0, z1 = S.CLOCK_SHAFT_Z
    g.box(x0, x1, z0, z1, "#")
    g.box(x0 + 1, x1 - 1, z0 + 1, z1 - 1, "x")
    sx, sz = SMALL_DOME_CENTRE                             # the small dome's drum
    for x in range(S.SMALL_DOME_X[0], S.SMALL_DOME_X[1] + 1):
        for z in range(S.SMALL_DOME_Z[0], S.SMALL_DOME_Z[1] + 1):
            d = math.hypot(x - sx, z - sz)
            if d <= S.SMALL_DOME_R:
                g.put(x, z, "#" if d > S.SMALL_DOME_R - 1 else "x")
    for x in range(X_MIN, X_MAX + 1):                      # the drum and the dome-room floor
        for z in range(Z_MIN, Z_MAX + 1):
            r = ring(x, z)
            if r in (R_FACE, R_GLASS):
                g.put(x, z, "#")
            elif r <= R_CLEAR:
                g.put(x, z, ".")
    _pier(g)
    hole = floor_opening()                                 # where the ring stair comes up
    for x, z in hole:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if g.get((x + dx, z + dz)) == ".":
                g.put(x + dx, z + dz, "r")
    for x, z in hole:
        g.put(x, z, "o")
    x, z, kind, _ = ring_stair()[-1]
    g.put(x, z, kind)                                      # the last step; one walks off it southwards
    g.put(x, z + 1, ".")
    return g


PLANS = {"ground": plan_ground, "main": plan_main, "roof": plan_roof}


# --- tables -----------------------------------------------------------------------------------
def tables():
    rows = []
    add = rows.append
    add("zone | x | z | feet y .. clear to | note")
    add("--- | --- | --- | --- | ---")

    def row(name, x, z, y, note=""):
        add("%s | %s | %s | %s | %s" % (name, "%d..%d" % x, "%d..%d" % z, y, note))

    hall_y = "%d .. %d (ceiling %d)" % (S.GROUND, S.STAR_HALL_CEIL - 1, S.STAR_HALL_CEIL)
    main_y = "%d .. %d (ceiling %d)" % (S.STAND, S.FRIEZE - 1, S.FRIEZE)
    row("star hall, clear", HALL_X, HALL_Z, hall_y, "cross walls on z %d and %d" % CROSS_Z)
    row("telescope pier", (CX - PIER_HALF, CX + PIER_HALF), (CZ - PIER_HALF, CZ + PIER_HALF),
        "%d .. %d" % (S.PAVING_Y, S.ROOF_STAND), "independent; A5 stands the mount on it")
    row("ring stair core", (CX - CORE_HALF, CX + CORE_HALF), (CZ - CORE_HALF, CZ + CORE_HALF),
        "%d -> %d" % (S.STAND, S.ROOF_STAND), "one turn, 11 steps")
    row("planetarium well", (CX + CORE_HALF + 2, HALL_X[1] - 2), (HALL_Z[0] + 2, HALL_Z[1] - 2),
        hall_y, "void between the galleries and the ring stair's guard")
    row("grand stair", STAIR_X, STAIR_Z, "%d -> %d" % (S.GROUND, S.STAND), "7 steps, rising west")
    row("main door", (east_face(0) + S.DEPTH_GLASS, east_face(0)), DOOR_Z, "0 .. 6", "leaves 0-4, fanlight 5-6 (A6)")
    row("west door", (CX - R_FACE, CX - R_GLASS), DOOR_Z, "0 .. 4", "to the sunset platform; proposed")
    row("north wing, main floor", S.ROOM_X, WING_N_Z, main_y, "time-service room")
    row("south wing, main floor", S.ROOM_X, WING_S_Z, main_y, "star-chart room")
    for z in CROSS_Z:
        row("room door", ROOM_DOOR_X, (z, z), "7 .. 9", "gallery to wing room")
    row("clock-tower shaft", S.CLOCK_SHAFT_X, S.CLOCK_SHAFT_Z, "0 .. %d" % S.CLOCK_SHAFT_TOP, "walls run to the ground")
    row("small-dome drum", S.SMALL_DOME_X, S.SMALL_DOME_Z, "%d .." % S.SMALL_DRUM_BASE, "round, centre (%d, %d)" % SMALL_DOME_CENTRE)
    out = ["\n".join(rows), ""]

    out.append("ring stair (x, z, kind, feet after):")
    out.append("  " + "  ".join("(%d,%d)%s%d" % c for c in ring_stair()))
    out.append("grand stair (x, feet after): " + "  ".join("x%d:%d" % c for c in grand_stair()))
    out.append("apse pilasters (x, z): " + "  ".join("(%d,%d)" % c for c in apse_pilasters()))
    for name, (opening, glass) in sorted(apse_windows().items()):
        out.append("apse window %s: opening %s  glass %s" % (
            name, " ".join("(%d,%d)" % c for c in opening), " ".join("(%d,%d)" % c for c in glass)))
    out.append("ring stair, air over each column (x, z, from y, up to y): "
               + "  ".join("(%d,%d)%d-%d" % (x, z, feet, top - 1) for x, z, feet, top in stair_air()))
    out.append("ring stair guard (x, z): " + "  ".join("(%d,%d)" % c for c in stair_guard()))
    out.append("hall ceiling (y %d) open at: " % S.STAR_HALL_CEIL + "  ".join("(%d,%d)" % c for c in ceiling_opening()))
    out.append("dome-room floor (y %d) open at: " % S.ROOF_FLOOR + "  ".join("(%d,%d)" % c for c in floor_opening()))
    z = ROOF_Z[0]
    xs = range(S.WALL_W + 1, east_face(z))
    out.append("pitched roofs: |z| %d..%d, gable walls on |z| %d and %d; top surface by x: " % (ROOF_Z + GABLE_Z)
               + "  ".join("x%d:%.1f" % (x, ROOF_EAVE_TOP + ROOF_STEP * roof_steps(x, z)) for x in xs))
    out.append("")
    out.append("windows (front bay: glass columns; base storey y %d..%d, main storey y %d..%d):" % (BASE_WINDOW + S.WINDOW))
    for front in ("east", "west", "north", "south", "apse"):
        both, main_only = [], []
        ws = [w for w in windows() if w["front"] == front]
        for w in ws:
            if w["storey"] != "main":
                continue
            xs = sorted({x for x, _ in w["cells"]})
            zs = sorted({z for _, z in w["cells"]})
            span = "x %d z %d..%d" % (xs[0], zs[0], zs[-1]) if len(xs) == 1 else "x %d..%d z %d" % (xs[0], xs[-1], zs[0])
            has_base = any(v["bay"] == w["bay"] and v["storey"] == "base" for v in ws)
            (both if has_base else main_only).append("%s (%s)" % (w["bay"], span))
        out.append("  %s, both storeys: %s" % (front, "  ".join(both)))
        if main_only:
            out.append("  %s, main storey only: %s" % (front, "  ".join(main_only)))
    out.append("  blind (stone for glass): " + "  ".join("%s %d" % b for b in BLIND_BAYS))
    return "\n".join(out)


def check():
    """Things that must hold for the plans to be buildable. Returns a list of problems."""
    bad = []
    stair = ring_stair()
    if stair[0][3] != S.STAND or stair[-1][3] != S.ROOF_STAND:
        bad.append("ring stair does not run from %d to %d" % (S.STAND, S.ROOF_STAND))
    if len({(x, z) for x, z, _, _ in stair}) != len(stair):
        bad.append("ring stair crosses itself")
    if grand_stair()[-1][1] != S.STAND:
        bad.append("grand stair does not reach the main floor")
    for name, (opening, glass) in apse_windows().items():
        zs = sorted(z for _, z in opening)
        if len(opening) != 3 or zs != list(range(zs[0], zs[0] + 3)) or len({x for x, _ in opening}) != 1:
            bad.append("apse window %s is not a straight run of three: %s" % (name, opening))
        if (set(opening) | set(glass)) & set(apse_pilasters()):
            bad.append("apse window %s: a window column is a pilaster" % name)
        for x, z in glass:
            if ring(x + 1, z) > R_GLASS:
                bad.append("apse window %s: nothing closes the wall behind glass (%d, %d)" % (name, x, z))
    near = ((1, 0), (-1, 0), (0, 1), (0, -1))
    walk = set(".D<>^v+")

    def reach(g, start):
        seen, todo = {start}, [start]
        while todo:
            x, z = todo.pop()
            for dx, dz in near:
                n = (x + dx, z + dz)
                if n not in seen and g.get(n) in walk:
                    seen.add(n)
                    todo.append(n)
        return seen

    ground, upper, roof = plan_ground(), plan_main(), plan_roof()
    door = (east_face(CZ), CZ)
    from_door = reach(ground, door)
    for what, cell in (("the west door", (CX - R_FACE, CZ)), ("the foot of the grand stair", (STAIR_X[1], CZ)),
                       ("the north pocket of the apse", (S.WALL_W - 1, HALL_Z[0])),
                       ("the south pocket of the apse", (S.WALL_W - 1, HALL_Z[1]))):
        if cell not in from_door:
            bad.append("ground: no way from the main door to %s" % what)
    from_landing = reach(upper, (LANDING_X, CZ))
    first = ring_stair()[0]
    for what, cell in (("the north room door", (ROOM_DOOR_X[0], CROSS_Z[0])), ("the south room door", (ROOM_DOOR_X[0], CROSS_Z[1])),
                       ("the start of the ring stair", first[:2]), ("the gallery over the main door", (HALL_X[1], CZ)),
                       ("the north wing room", (ROOM_DOOR_X[0], WING_N_Z[1])), ("the south wing room", (ROOM_DOOR_X[0], WING_S_Z[0]))):
        if cell not in from_landing:
            bad.append("main: no way from the stair landing to %s" % what)
    last = ring_stair()[-1]
    if (CX + R_CLEAR, CZ) not in reach(roof, last[:2]):
        bad.append("roof: the ring stair does not come out on the dome-room floor")
    for name, g in (("main", upper), ("roof", roof)):        # nobody walks off an edge
        for (x, z), ch in g.items():
            if ch == "." and any(g.get((x + dx, z + dz)) == "o" for dx, dz in near):
                bad.append("%s: deck (%d, %d) borders a void without a railing" % (name, x, z))
    for storey, name, g in (("base", "ground", ground), ("main", "main", upper)):
        listed = set()
        for w in windows():                                  # A2 puts a light behind every pane
            if w["storey"] != storey:
                continue
            dx, dz = w["inward"]
            for x, z in w["cells"]:
                listed.add((x, z))
                if g.get((x, z)) != "g":
                    bad.append("%s: window %s %s has no glass at (%d, %d)" % (name, w["front"], w["bay"], x, z))
                if g.get((x + dx, z + dz)) not in (".", "x", "o", "r"):
                    bad.append("%s: nothing empty behind the glass at (%d, %d)" % (name, x, z))
        for cell, ch in g.items():
            if ch == "g" and cell not in listed:
                bad.append("%s: glass at %s belongs to no listed window" % (name, cell))
    for x, z, feet, top in stair_air():                      # the ring stair has its headroom
        for y in (S.STAR_HALL_CEIL, S.ROOF_FLOOR):
            if feet <= y < top and (x, z) not in _open_at(y):
                bad.append("ring stair: no headroom at (%d, %d), y %d" % (x, z, y))
    return bad


def main(argv):
    which = argv[1:] or ["ground", "main", "roof", "tables"]
    for name in which:
        if name == "tables":
            print(tables())
        else:
            print("--- %s ---" % name)
            print(PLANS[name]().text())
        print()
    problems = check()
    for p in problems:
        print("PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
