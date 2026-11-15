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
    python3 -m scenes.obs.main._plan ground     # one of: ground, main, roof, tables, legend

Other lines read windows() from here (sky/lights puts the light behind each pane, props hangs the
window frames). Its name and the keys of its records stay as they are.

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
# The telescope pier is an octagon five across. With the ring of one block that keeps every floor
# off it, it fills the skeleton's pier radius of three.
PIER_BODY_R = 2.5
PIER_ZONE_R = S.PIER_R + 0.5
# The hall and the apse are one room: where the west wall would cross it (x 0..1) there is a
# passage on the ground floor and a cross gallery above. West of it the apse follows the bays of
# the front: a flight of the grand stair in bay 8 and in bay 10, the way to the west door in bay 9
# under a mezzanine, their cheeks on the pilaster lines between.
CROSS_X = (S.WALL_W, S.WALL_W - S.DEPTH_GLASS)            # 0..1
FLIGHT_X = (S.WALL_W - 6, S.WALL_W)                       # -6..0: seven steps, rising west
FLIGHT_BAYS = (8, 10)
AISLE_BAY = 9
CHEEK_Z = (S.pilaster_z(8), S.pilaster_z(9))              # -2 and 2
WEST_X = CX - R_CLEAR                                     # -7: the last column inside, on the axis
ROOM_DOOR_X = (7, 8)                                      # gallery -> wing room, through a cross wall
WEST_DOOR_TOP = 3                                         # the west door is 3 wide and 4 high (A0: below y 5)
# Two cast-iron spiral stairs climb from the mezzanine level to the dome room, one in each pocket
# of the apse: 3 x 3 round a newel, against the blind west wall of the wings.
SPIRAL_X = (S.WALL_W - 3, S.WALL_W - 1)                   # -3..-1
SPIRAL_Z = (CROSS_Z[1] + 1, CROSS_Z[1] + 3)               # |z| 7..9
# The pilasters of the apse stand under those of the drum and the ribs of the dome (main/_dome.py:
# twenty gores, a rib every 18 degrees, the west axis in the middle of a gore), 9 and 27 degrees
# either side of the axis. Further round the wall steps diagonally into the junction: none there.
APSE_PILASTER_DEG = (9.0, 27.0)
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
GALLERY_DECK_Y = S.STRING        # 6: the deck block of galleries, mezzanine and pockets; feet at 7
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
    ("r", "barrier on the edge of a deck: a railing on its own block, or the top of a cheek wall"),
    ("T", "telescope pier"),
    ("=", "iron grating, flush with the floor: the ring that keeps the floor off the pier"),
    ("< > ^ v", "stair, the arrow points uphill (west, east, north, south)"),
    ("@", "newel of a spiral stair"),
    ("x", "closed space: not entered in the first version"),
    ("t", "roof terrace, deck at y 17 (top at 18.0)"),
    ("0-6", "slate roof, half-block steps above y 17.0 (0 = gutter, 6 = ridge at y 20.0)"),
    ("G", "gable wall closing the end of a pitched roof"),
    ("p", "parapet"),
]

NEAR = ((1, 0), (-1, 0), (0, 1), (0, -1))


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


def window_rows(bay):
    """Rows of the window of a bay of the long fronts: three, or two next to a corner pier."""
    return [z for z in range(S.pilaster_z(bay - 1) + 1, S.pilaster_z(bay)) if z not in END_PIER_ROWS]


def end_wall_bays(zf):
    """[(bay, window columns)] of an end wall: bays of four from the west, corner piers left out."""
    xe = east_face(zf)
    return [(i + 1, [x for x in range(S.WALL_W + S.BAY * i + 1, min(S.WALL_W + S.BAY * (i + 1), xe))
                     if x not in (S.WALL_W + 1, xe - 1)])
            for i in range((xe - S.WALL_W) // S.BAY)]


def _apse_cells(r):
    """Columns of one ring that stand west of the main building's west wall."""
    return [(x, z) for x in range(X_MIN, S.WALL_W) for z in range(Z_MIN, Z_MAX + 1) if ring(x, z) == r]


def apse_pilasters():
    """One pilaster column per pilaster angle: the ring-14 column closest to it."""
    cells = _apse_cells(R_PILASTER)
    out = []
    for a in APSE_PILASTER_DEG:
        for sign in (-1, 1):
            out.append(min(cells, key=lambda c: abs(west_angle(*c) - sign * a)))
    return sorted(set(out))


def apse_windows():
    """{name: (the opening columns on the wall face, the glass column one block behind each)}.

    A raster circle of this radius has only three runs straight enough to carry an arched window:
    the west one on the axis (three wide, between the pilasters at 9 degrees) and the one on either
    side of it (two wide, like the windows of the end pavilions: its third column stands behind the
    pilaster at 27 degrees). Everywhere else the wall steps diagonally, where the columns along the
    ring make an L and cannot take an arched head, so the flanks stay solid. The apse has great
    windows only: its base storey is solid but for the west door."""
    xa = CX - R_FACE                                        # -9: the run on the west axis
    out = {"west": [(xa, z) for z in window_rows(AISLE_BAY)]}
    piers = set(apse_pilasters())
    side = sorted(c for c in _apse_cells(R_FACE)            # the next run: x = -8
                  if c[0] == xa + 1 and (c[0] - 1, c[1]) not in piers)
    out["north-west"] = [c for c in side if c[1] < CZ]
    out["south-west"] = [c for c in side if c[1] > CZ]
    return {name: (cells, [(x + 1, z) for x, z in cells]) for name, cells in out.items()}


def pier_cells():
    """Columns of the telescope pier: an octagon five across on the dome centre."""
    return [(CX + dx, CZ + dz) for dx in range(-3, 4) for dz in range(-3, 4) if math.hypot(dx, dz) <= PIER_BODY_R]


def pier_ring():
    """The ring round the pier that every floor leaves open (a grating in the dome-room floor)."""
    body = set(pier_cells())
    return [(CX + dx, CZ + dz) for dx in range(-4, 5) for dz in range(-4, 5)
            if math.hypot(dx, dz) <= PIER_ZONE_R and (CX + dx, CZ + dz) not in body]


def flight_rows(side):
    """Rows of one flight of the grand stair: side -1 is the north one (bay 8), +1 the south one."""
    return window_rows(FLIGHT_BAYS[0] if side < 0 else FLIGHT_BAYS[1])


def grand_stair():
    """One flight of the grand stair: [(x, feet after this step)], rising west from the hall floor.
    Both flights are the same; flight_rows() gives their rows."""
    return [(x, S.GROUND + i + 1) for i, x in enumerate(range(FLIGHT_X[1], FLIGHT_X[0] - 1, -1))]


def spiral(side):
    """A spiral stair to the dome room: [(x, z, kind, feet after this step)], side -1 north, +1 south.

    It starts from the pocket's deck (feet 7) west of its first step, goes once round the newel and
    three steps more, and leaves eastwards onto the dome-room floor (feet 18)."""
    x0, x1 = SPIRAL_X
    za, zb = side * SPIRAL_Z[0], side * SPIRAL_Z[1]        # the row next to the hall, the far row
    zm = (za + zb) // 2
    away, back = ("^", "v") if side < 0 else ("v", "^")
    lap = [(x0, za, ">"), (x0 + 1, za, ">"), (x1, za, ">"), (x1, zm, away), (x1, zb, away),
           (x0 + 1, zb, "<"), (x0, zb, "<"), (x0, zm, back)]
    path = lap + [(x0, za, back), (x0 + 1, za, ">"), (x1, za, ">")]
    return [(x, z, kind, S.STAND + i + 1) for i, (x, z, kind) in enumerate(path)]


def spiral_newel(side):
    return ((SPIRAL_X[0] + SPIRAL_X[1]) // 2, side * (SPIRAL_Z[0] + SPIRAL_Z[1]) // 2)


def spiral_ends(side):
    """(the deck column the stair starts from, the dome-room column it leaves onto)."""
    return (SPIRAL_X[0] - 1, side * SPIRAL_Z[0]), (SPIRAL_X[1] + 1, side * SPIRAL_Z[0])


def stair_air(side):
    """What must stay empty over a spiral stair: [(x, z, feet, top)], air in feet <= y < top.

    A walker is 1.8 tall and 0.6 wide. Stepping up, the feet are already on the next step while the
    trailing 0.1 of the body is still over this column, so a column followed by a step up needs a
    whole block more than standing room: three blocks, as on every staircase in the game."""
    stair = spiral(side)
    feet_after = [c[3] for c in stair[1:]] + [S.ROOF_STAND]
    return [(x, z, feet, feet + (3 if nxt > feet else 2)) for (x, z, _, feet), nxt in zip(stair, feet_after)]


def _open_at(y, side):
    """Columns where the block at height y has to be air for a spiral stair."""
    return [(x, z) for x, z, feet, top in stair_air(side) if feet <= y < top]


def floor_opening(side):
    """Columns of the dome-room floor that must be open for a spiral stair. The last step is not
    in it: its own block lies in the floor."""
    return _open_at(S.ROOF_FLOOR, side)


def ceiling_opening(side):
    """The same for the ceiling under the dome room (the star hall's level)."""
    return _open_at(S.STAR_HALL_CEIL, side)


def orrery_well():
    """The clear box east of the pier where the orrery hangs: ((x0, x1), (z0, z1), (y0, y1))."""
    xs = [x for x, _ in pier_ring()]
    return ((max(xs) + 1, HALL_X[1]), (HALL_Z[0] + 2, HALL_Z[1] - 2), (S.STAND, S.STAR_HALL_CEIL - 1))


def roof_steps(x, z):
    """Half-block steps of the slate roof above the eave on a column, or None off the roofs.
    The ridge runs north-south; both slopes fall to a gutter behind the parapets."""
    if not ROOF_Z[0] <= abs(z) <= ROOF_Z[1]:
        return None
    xe = east_face(z)
    if not S.WALL_W < x < xe:
        return None
    return min(x - S.WALL_W, xe - x, ROOF_RIDGE_STEPS) - 1


def windows():
    """Every glazed window of the main building, for whoever lights or frames them:
    [dict(front, bay, storey, cells, inward, y)].

    front and bay name the window: "east" and "west" count the skeleton's bays 1..17 from the
    north; "north" and "south" count the end walls' bays 1..4 from the west; "apse" has -1, 0, 1
    (north-west, west, south-west); "drum" has the twenty small windows of the dome's drum, 0
    looking east and counting round by the south. storey is "base", "main" or "drum". cells are
    the glass columns (x, z); inward is the step from the glass into the building; y is the
    glass's (bottom, top).

    These are the windows main/facade.py cuts, so the table cannot drift from the walls. It says
    nothing about the glass: which windows are lit is the light line's to say, and what stands in
    a window is on the canvas (facade.windows() lists it)."""
    from . import facade
    return facade.table()


def doors():
    """Every doorway of the shell, for whoever hangs leaves, gates and canopies in them:
    [dict(front, bay, cells, inward, y, arch, kind)].

    front and bay as in windows(). cells are the columns of the wall line the doorway goes through
    (x, z); inward is the step into the building, so the glass plane, where a leaf hangs, is cells
    plus inward; y is the doorway's (bottom, top); arch says whether its two top corners are
    rounded like a great window's; kind is "door" where people walk through and "gate" where an
    iron gate closes the arch. These are the doorways main/facade.py cuts, in the version of the
    entrance that is built (facade.doors(version) gives the others)."""
    from . import facade
    return facade.doors()


def plan_windows():
    """The same table as the plan gives it, without the building: what facade.py's self-check
    holds the built windows against. [dict(front, bay, storey, cells, inward, y)]."""
    out = []

    def add(front, bay, cells, inward, base=True):
        for storey, y in (("base", BASE_WINDOW), ("main", S.WINDOW)):
            if storey == "main" or base:
                out.append(dict(front=front, bay=bay, storey=storey, cells=cells, inward=inward, y=y))

    for bay in range(1, S.N_BAYS + 1):
        rows = window_rows(bay)
        xg = S.east_wall_x(bay) + S.DEPTH_GLASS
        add("east", bay, [(xg, z) for z in rows], (-1, 0), base=bay != AISLE_BAY)
        if all(abs(z - CZ) > WEST_BLIND_Z for z in rows):
            add("west", bay, [(S.WALL_W - S.DEPTH_GLASS, z) for z in rows], (1, 0))
    for front, zf, out_step in (("north", S.Z_NORTH, -1), ("south", S.Z_SOUTH, 1)):
        for bay, cols in end_wall_bays(zf):
            if (front, bay) not in BLIND_BAYS:
                add(front, bay, [(x, zf - out_step) for x in cols], (0, -out_step))
    names = {"north-west": -1, "west": 0, "south-west": 1}
    for name, (opening, glass) in apse_windows().items():
        add("apse", names[name], glass, (1, 0), base=False)
    return out


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


def _apse_shell(g, level):
    """The part of the rotunda that stands outside the west wall: a cylinder from the ground."""
    for x in range(X_MIN, S.WALL_W):
        for z in range(Z_MIN, Z_MAX + 1):
            r = ring(x, z)
            if r in (R_FACE, R_GLASS):
                g.put(x, z, "#")
            elif r <= R_CLEAR:
                g.put(x, z, ".")
    if level == "main":
        for opening, glass in apse_windows().values():
            for (x, z), (gx, gz) in zip(opening, glass):
                g.put(x, z, "w")
                g.put(gx, gz, "g")
                g.put(gx + 1, gz, ".")   # the column behind the glass stays empty (A2's lights)
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


def _pier(g):
    for x, z in pier_cells():
        g.put(x, z, "T")


def _apse_cells_inside():
    return [(x, z) for x in range(X_MIN, S.WALL_W) for z in range(Z_MIN, Z_MAX + 1) if ring(x, z) <= R_CLEAR]


def plan_ground():
    """The ground floor, feet at y 0; cut through the base storey."""
    g = Grid()
    _envelope(g)
    _apse_shell(g, "ground")
    _closed_rooms(g, wings=True)
    _tower_base(g)
    g.box(CROSS_X[0], HALL_X[1], HALL_Z[0], HALL_Z[1], ".")    # the hall, and the passage behind the pier
    _partitions(g)
    for x, z in _apse_cells_inside():
        if abs(z) == CROSS_Z[1]:
            g.put(x, z, "#")                               # the cross-wall line runs on under the pockets
        elif abs(z) > CROSS_Z[1]:
            g.put(x, z, "x")                               # the pockets are closed on the ground floor
    for side in (-1, 1):
        for x, _ in grand_stair():
            for z in flight_rows(side):
                g.put(x, z, "<")
    for z in CHEEK_Z:                                      # the cheeks; the first step stands clear of them
        g.box(FLIGHT_X[0], FLIGHT_X[1] - 1, z, z, "#")
    aisle = window_rows(AISLE_BAY)
    for x, z in _apse_cells_inside():                      # west of the flights only the aisle is open
        if x < FLIGHT_X[0] and z not in aisle:
            g.put(x, z, "#")
    _pier(g)
    for z in window_rows(AISLE_BAY):
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
    _apse_shell(g, "main")
    _closed_rooms(g, wings=False)
    _tower_base(g)
    xa, xb = S.ROOM_X
    g.box(xa, xb, WING_N_Z[0], WING_N_Z[1], ".")           # the time-service room's shell
    g.box(xa, xb, WING_S_Z[0], WING_S_Z[1], ".")           # the star-chart room's shell
    # the star hall at gallery level: a void with a gallery along each long side
    g.box(HALL_X[0], HALL_X[1], HALL_Z[0], HALL_Z[1], "o")
    for z in (HALL_Z[0], HALL_Z[1]):
        g.box(HALL_X[0], HALL_X[1], z, z, ".")
        inner = z + (1 if z < 0 else -1)
        g.box(HALL_X[0], HALL_X[1], inner, inner, "r")
    # the cross gallery behind the pier joins them to the mezzanine
    g.box(CROSS_X[0], CROSS_X[1], HALL_Z[0], HALL_Z[1], ".")
    _partitions(g)
    for side in (-1, 1):
        rows = flight_rows(side)
        for x, _ in grand_stair():
            for z in rows:
                g.put(x, z, "<")
        for z in rows:
            g.put(FLIGHT_X[1], z, "r")                     # the railing over the first step
        zc = CHEEK_Z[0] if side < 0 else CHEEK_Z[1]
        g.box(FLIGHT_X[0] + 1, FLIGHT_X[1] - 1, zc, zc, "r")   # the cheek's top; open at its west end
        zw = side * CROSS_Z[1]                             # the pocket: a low wall towards the flight,
        g.box(SPIRAL_X[0] - 1, S.WALL_W - 1, zw, zw, "r")  # open at its west end
        for x, z, kind, feet in spiral(side):
            if feet <= S.STAND + 8:                        # the first turn shows at this level
                g.put(x, z, kind)
        g.put(*spiral_newel(side), "@")
    for x, z in _apse_cells_inside():                      # the slivers behind the spiral stairs
        if abs(z) > SPIRAL_Z[1]:
            g.put(x, z, "#")
    for z in range(HALL_Z[0], HALL_Z[1] + 1):              # the cross gallery's edge towards the hall
        if g.get((HALL_X[0], z)) == "o":
            g.put(HALL_X[0], z, "r")
    for x, z in pier_ring():                               # where it passes the pier it is a grating
        if g.get((x, z)) == ".":
            g.put(x, z, "=")
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
    for x, z in pier_ring():
        g.put(x, z, "=")
    _pier(g)
    for side in (-1, 1):                                   # where the spiral stairs come up
        hole = floor_opening(side)
        start, leave = spiral_ends(side)
        for x, z in hole:
            for dx, dz in NEAR:
                if g.get((x + dx, z + dz)) == ".":
                    g.put(x + dx, z + dz, "r")
        for x, z in hole:
            g.put(x, z, "o")
        x, z, kind, _ = spiral(side)[-1]
        g.put(x, z, kind)                                  # the last step; one walks off it eastwards
        g.put(*leave, ".")
        g.put(*spiral_newel(side), "@")
    return g


PLANS = {"ground": plan_ground, "main": plan_main, "roof": plan_roof}


# --- tables -----------------------------------------------------------------------------------
def _span(cells):
    xs = sorted({x for x, _ in cells})
    zs = sorted({z for _, z in cells})
    if len(xs) == 1:
        return "x %d z %d..%d" % (xs[0], zs[0], zs[-1])
    return "x %d..%d z %d" % (xs[0], xs[-1], zs[0])


def tables():
    rows = []
    add = rows.append
    add("zone | x | z | y | note")
    add("--- | --- | --- | --- | ---")

    def row(name, x, z, y, note=""):
        add("%s | %s | %s | %s | %s" % (name, "%d..%d" % x, "%d..%d" % z, y, note))

    hall_y = "feet %d, clear to %d, ceiling %d" % (S.GROUND, S.STAR_HALL_CEIL - 1, S.STAR_HALL_CEIL)
    main_y = "feet %d, clear to %d, ceiling %d" % (S.STAND, S.FRIEZE - 1, S.FRIEZE)
    deck_y = "deck block %d, feet %d" % (GALLERY_DECK_Y, S.STAND)
    px = sorted({x for x, _ in pier_cells()})
    pz = sorted({z for _, z in pier_cells()})
    zx = sorted({x for x, _ in pier_ring()})
    zz = sorted({z for _, z in pier_ring()})
    well = orrery_well()
    row("star hall, clear", HALL_X, HALL_Z, hall_y, "cross walls on z %d and %d; open to the apse on the west" % CROSS_Z)
    row("telescope pier", (px[0], px[-1]), (pz[0], pz[-1]), "blocks %d..%d, top at %d.0" % (S.PAVING_Y, S.ROOF_FLOOR, S.ROOF_STAND),
        "octagon, %d columns; touches no floor" % len(pier_cells()))
    row("ring round the pier", (zx[0], zx[-1]), (zz[0], zz[-1]), "open at y %d..%d, grating at %d" % (S.STAR_HALL_CEIL, S.ROOF_FLOOR - 1, S.ROOF_FLOOR),
        "%d columns; with the pier it is the skeleton's radius %d" % (len(pier_ring()), S.PIER_R))
    row("well for the orrery", well[0], well[1], "%d..%d" % well[2], "nothing of the building in it")
    row("passage behind the pier", CROSS_X, HALL_Z, "feet %d" % S.GROUND, "cross gallery above it: " + deck_y)
    row("galleries", HALL_X, (HALL_Z[0], HALL_Z[0]), deck_y, "and z %d; the railing stands on the next row inwards" % HALL_Z[1])
    for side, name in ((-1, "north"), (1, "south")):
        r = flight_rows(side)
        row("grand stair, %s flight" % name, FLIGHT_X, (r[0], r[-1]), "%d -> %d" % (S.GROUND, S.STAND), "7 steps, rising west")
    a = window_rows(AISLE_BAY)
    row("way to the west door", (WEST_X, FLIGHT_X[1]), (a[0], a[-1]), "feet %d, clear to %d" % (S.GROUND, GALLERY_DECK_Y - 1), "under the mezzanine")
    row("mezzanine", (WEST_X, S.WALL_W - 1), (a[0], a[-1]), deck_y, "widens to z %d..%d at x %d" % (CHEEK_Z[0] - 1, CHEEK_Z[1] + 1, WEST_X))
    row("main door", (east_face(0) + S.DEPTH_GLASS, east_face(0)), (a[0], a[-1]), "%d..%d" % (S.GROUND, S.STRING), "leaves 0-4, fanlight 5-6 (A6)")
    row("west door", (CX - R_FACE, CX - R_GLASS), (a[0], a[-1]), "%d..%d" % (S.GROUND, WEST_DOOR_TOP), "to the sunset platform; plain, always open")
    row("north wing, main floor", S.ROOM_X, WING_N_Z, main_y, "time-service room")
    row("south wing, main floor", S.ROOM_X, WING_S_Z, main_y, "star-chart room")
    for z in CROSS_Z:
        row("room door", ROOM_DOOR_X, (z, z), "%d..%d" % (S.STAND, S.STAND + 2), "gallery to wing room")
    for side, name in ((-1, "north"), (1, "south")):
        zs = sorted((side * SPIRAL_Z[0], side * SPIRAL_Z[1]))
        row("spiral stair, %s" % name, SPIRAL_X, tuple(zs), "%d -> %d" % (S.STAND, S.ROOF_STAND),
            "11 steps round the newel %s" % (spiral_newel(side),))
    row("clock-tower shaft", S.CLOCK_SHAFT_X, S.CLOCK_SHAFT_Z, "%d..%d" % (S.GROUND, S.CLOCK_SHAFT_TOP), "walls run to the ground")
    row("small-dome drum", S.SMALL_DOME_X, S.SMALL_DOME_Z, "from %d" % S.SMALL_DRUM_BASE, "round, centre (%d, %d)" % SMALL_DOME_CENTRE)
    out = ["\n".join(rows), ""]

    out.append("grand stair, each flight (x, feet after): " + "  ".join("x%d:%d" % c for c in grand_stair()))
    for side, name in ((-1, "north"), (1, "south")):
        start, leave = spiral_ends(side)
        out.append("spiral stair %s, from the deck at %s to the dome-room floor at %s (x, z, uphill, feet after):" % (name, start, leave))
        out.append("  " + "  ".join("(%d,%d)%s%d" % c for c in spiral(side)))
        out.append("  air over each column (from y, up to y): "
                   + "  ".join("(%d,%d)%d-%d" % (x, z, feet, top - 1) for x, z, feet, top in stair_air(side)))
        out.append("  ceiling (y %d) open at: " % S.STAR_HALL_CEIL + "  ".join("(%d,%d)" % c for c in ceiling_opening(side))
                   + ";  dome-room floor (y %d) open at: " % S.ROOF_FLOOR + "  ".join("(%d,%d)" % c for c in floor_opening(side)))
    out.append("apse pilasters (x, z): " + "  ".join("(%d,%d)" % c for c in apse_pilasters()))
    for name, (opening, glass) in sorted(apse_windows().items()):
        out.append("apse window %s: opening %s  glass %s" % (
            name, " ".join("(%d,%d)" % c for c in opening), " ".join("(%d,%d)" % c for c in glass)))
    z = ROOF_Z[0]
    xs = range(S.WALL_W + 1, east_face(z))
    out.append("pitched roofs: |z| %d..%d, gable walls on |z| %d and %d; top surface by x: " % (ROOF_Z + GABLE_Z)
               + "  ".join("x%d:%.1f" % (x, ROOF_EAVE_TOP + ROOF_STEP * roof_steps(x, z)) for x in xs))
    out.append("")
    ws = plan_windows()
    out.append("windows, %d in all (front bay: glass columns; base storey y %d..%d, main storey y %d..%d):"
               % ((len(ws),) + BASE_WINDOW + S.WINDOW))
    for front in ("east", "west", "north", "south", "apse"):
        both, main_only = [], []
        mine = [w for w in ws if w["front"] == front]
        for w in mine:
            if w["storey"] != "main":
                continue
            has_base = any(v["bay"] == w["bay"] and v["storey"] == "base" for v in mine)
            (both if has_base else main_only).append("%s (%s)" % (w["bay"], _span(w["cells"])))
        if both:
            out.append("  %s, both storeys: %s" % (front, "  ".join(both)))
        if main_only:
            out.append("  %s, main storey only: %s" % (front, "  ".join(main_only)))
    out.append("  blind (stone for glass): " + "  ".join("%s %d" % b for b in BLIND_BAYS))
    return "\n".join(out)


def legend():
    return "\n".join("%-8s %s" % item for item in LEGEND)


# --- checks -----------------------------------------------------------------------------------
def check():
    """Things that must hold for the plans to be buildable. Returns a list of problems."""
    bad = []
    if grand_stair()[-1][1] != S.STAND:
        bad.append("grand stair does not reach the main floor")
    for name, (opening, glass) in apse_windows().items():
        zs = sorted(z for _, z in opening)
        if len(opening) not in (2, 3) or zs != list(range(zs[0], zs[0] + len(zs))) or len({x for x, _ in opening}) != 1:
            bad.append("apse window %s is not a straight run of two or three: %s" % (name, opening))
        if (set(opening) | set(glass)) & set(apse_pilasters()):
            bad.append("apse window %s: a window column is a pilaster" % name)
        for x, z in glass:
            if ring(x + 1, z) > R_GLASS:
                bad.append("apse window %s: nothing closes the wall behind glass (%d, %d)" % (name, x, z))
    ground, upper, roof = plan_ground(), plan_main(), plan_roof()
    for side, name in ((-1, "north"), (1, "south")):
        stair = spiral(side)
        if stair[0][3] != S.STAND + 1 or stair[-1][3] != S.ROOF_STAND:
            bad.append("%s spiral does not run from %d to %d" % (name, S.STAND, S.ROOF_STAND))
        seen = {}
        for x, z, feet, top in stair_air(side):
            if (x, z) in seen and feet - 1 < seen[(x, z)]:
                bad.append("%s spiral: the second turn at (%d, %d) is too low over the first" % (name, x, z))
            seen[(x, z)] = top
            if ring(x, z) > R_CLEAR or x >= S.WALL_W:
                bad.append("%s spiral: (%d, %d) is not inside the apse" % (name, x, z))
        start, leave = spiral_ends(side)
        if upper.get(start) != ".":
            bad.append("%s spiral: no deck to start from at %s" % (name, start))
        if roof.get(leave) != ".":
            bad.append("%s spiral: no floor to step onto at %s" % (name, leave))
    walk = set(".D<>^v=")

    def reach(g, start):
        seen, todo = {start}, [start]
        while todo:
            x, z = todo.pop()
            for dx, dz in NEAR:
                n = (x + dx, z + dz)
                if n not in seen and g.get(n) in walk:
                    seen.add(n)
                    todo.append(n)
        return seen

    aisle = window_rows(AISLE_BAY)
    from_door = reach(ground, (east_face(CZ), CZ))
    for what, cell in (("the west door", (CX - R_FACE, CZ)),
                       ("the foot of the north flight", (FLIGHT_X[1], flight_rows(-1)[1])),
                       ("the foot of the south flight", (FLIGHT_X[1], flight_rows(1)[1]))):
        if cell not in from_door:
            bad.append("ground: no way from the main door to %s" % what)
    from_top = reach(upper, (FLIGHT_X[0], flight_rows(-1)[1]))
    for what, cell in (("the mezzanine under the west window", (WEST_X, CZ)),
                       ("the top of the south flight", (FLIGHT_X[0], flight_rows(1)[1])),
                       ("the north room door", (ROOM_DOOR_X[0], CROSS_Z[0])), ("the south room door", (ROOM_DOOR_X[0], CROSS_Z[1])),
                       ("the north wing room", (ROOM_DOOR_X[0], WING_N_Z[1])), ("the south wing room", (ROOM_DOOR_X[0], WING_S_Z[0])),
                       ("the east end of the north gallery", (HALL_X[1], HALL_Z[0])),
                       ("the north spiral stair", spiral_ends(-1)[0]), ("the south spiral stair", spiral_ends(1)[0])):
        if cell not in from_top:
            bad.append("main: no way from the top of the north flight to %s" % what)
    for side, name in ((-1, "north"), (1, "south")):
        if (CX + R_CLEAR, CZ) not in reach(roof, spiral(side)[-1][:2]):
            bad.append("roof: the %s spiral does not come out on the dome-room floor" % name)
    for name, g in (("main", upper), ("roof", roof)):        # nobody walks off an edge
        for (x, z), ch in g.items():
            if ch == "." and any(g.get((x + dx, z + dz)) == "o" for dx, dz in NEAR):
                bad.append("%s: deck (%d, %d) borders a void without a railing" % (name, x, z))
    steps = dict(grand_stair())
    for (x, z), ch in upper.items():                         # nor off a deck into a stairwell
        if ch != ".":
            continue
        for dx, dz in NEAR:
            n = (x + dx, z + dz)
            if upper.get(n) == "<" and S.STAND - steps[n[0]] > 1:
                bad.append("main: deck (%d, %d) drops %d onto the grand stair" % (x, z, S.STAND - steps[n[0]]))
    well = orrery_well()
    for x in range(well[0][0], well[0][1] + 1):
        for z in range(well[1][0], well[1][1] + 1):
            if upper.get((x, z)) != "o":
                bad.append("main: the orrery's well is not clear at (%d, %d)" % (x, z))
    for z in aisle:                                          # the way to the west door is under a deck
        if upper.get((WEST_X, z)) != ".":
            bad.append("main: no mezzanine over the west door at z %d" % z)
    for storey, name, g in (("base", "ground", ground), ("main", "main", upper)):
        listed = set()
        for w in plan_windows():                             # A2 puts a light behind every pane
            if w["storey"] != storey:
                continue
            dx, dz = w["inward"]
            for x, z in w["cells"]:
                listed.add((x, z))
                if g.get((x, z)) != "g":
                    bad.append("%s: window %s %s has no glass at (%d, %d)" % (name, w["front"], w["bay"], x, z))
                if g.get((x + dx, z + dz)) not in (".", "x", "o", "r", "<"):
                    bad.append("%s: nothing empty behind the glass at (%d, %d)" % (name, x, z))
        for cell, ch in g.items():
            if ch == "g" and cell not in listed:
                bad.append("%s: glass at %s belongs to no listed window" % (name, cell))
    return bad


def main(argv):
    which = argv[1:] or ["ground", "main", "roof", "tables"]
    for name in which:
        if name == "tables":
            print(tables())
        elif name == "legend":
            print(legend())
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
