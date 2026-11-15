"""The plan of the main building's walls: which column of every front is a pier and which a window,
where the fronts step forward, where the apse carries its pilasters and its windows, how the
pitched roofs rise. main/facade.py lays the elevation grammar (_order.py) on it.

Every coordinate that the first review locked comes from the skeleton; what is decided here on
top of it is listed under "decisions of the main line".

    python3 -m scenes.obs.main._plan            # print the tables of the walls, and check them

Other lines read windows() from here (sky/lights puts the light behind each pane, props hangs the
window frames) and doors() (props hangs leaves, gates and canopies). Their names and the keys of
their records stay as they are.

The rooms are not planned here any more. The module began as the block-by-block plan of the whole
building that the first review asked for (c178; its drawings are printed in plan/parts/main.md):
an octagonal telescope pier, the grand stair in the apse, two spiral stairs, the openings they
needed in the floors. The director has ruled the interior again since (a pier of 3 x 3 with a
stair round it); it is planned and built in main/shell.py, and what stood here of the old one was
taken out. The rows of the cross walls and the clear spans of the wings stay (CROSS_Z, WING_N_Z,
WING_S_Z): the walls stand on them, whoever fits out the rooms.

The name starts with an underscore, so the category's auto-discovery does not treat it as a work
package.
"""
import math
import sys

from ..common import skeleton as S

# --- where the apse is looked for -------------------------------------------------------------
X_MIN = -11
Z_MIN, Z_MAX = -37, 37

# --- the rotunda's rings (block centre to block centre, like the massing model) -------------
CX, CZ = S.DOME_CENTRE
R_FACE = S.DOME_R           # 13: the wall face
R_GLASS = R_FACE - 1        # 12: glass and inner leaf
R_PILASTER = R_FACE + 1     # 14: pilasters

# --- decisions of the main line (A3) on top of the skeleton ---------------------------------
# Cross walls stand on pilaster lines, so no wall ever lands behind a window.
CROSS_Z = S.STAR_HALL_Z                                   # -6 and 6: star hall / wings
PAVILION_Z = (S.pilaster_z(2), S.pilaster_z(15))          # -26 and 26: wings / end pavilions
WING_N_Z = (PAVILION_Z[0] + 1, CROSS_Z[0] - 1)            # -25..-7, clear
WING_S_Z = (CROSS_Z[1] + 1, PAVILION_Z[1] - 1)            # 7..25, clear
# The end pavilions have corner piers two blocks wide: the window column next to each of their
# corners is solid (these rows of the long fronts; on the end walls the column next to either
# corner), so the windows there are two wide. Without it the glass of two fronts would meet in a
# corner column with no room behind it, and the corners of the clock-tower shaft (one block in
# from the pavilion's) would stand on window columns.
END_PIER_ROWS = (S.Z_NORTH + 1, PAVILION_Z[0] - 1, PAVILION_Z[1] + 1, S.Z_SOUTH - 1)   # -33, -27, 27, 33
AISLE_BAY = 9                                             # the bay on the axis: the main door, and the west door behind it
# The door from the hall's gallery into a wing room, through a cross wall. The door is main/shell's
# now, which has the same columns under the same name; interiors/chartroom still reads them here.
ROOM_DOOR_X = (7, 8)
WEST_DOOR_TOP = 3                                         # the west door is 3 wide and 4 high (A0: below y 5)
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

# heights that go with the roofs
ROOF_EAVE_TOP = 17.0             # top surface of the roof next to the parapet
ROOF_STEP = 0.5                  # rise per block: a 1:2 slope laid in slabs
ROOF_RIDGE_TOP = ROOF_EAVE_TOP + ROOF_STEP * (ROOF_RIDGE_STEPS - 1)   # 20.0


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


# --- tables -----------------------------------------------------------------------------------
def _span(cells):
    xs = sorted({x for x, _ in cells})
    zs = sorted({z for _, z in cells})
    if len(xs) == 1:
        return "x %d z %d..%d" % (xs[0], zs[0], zs[-1])
    return "x %d..%d z %d" % (xs[0], xs[-1], zs[0])


def tables():
    """What this module decides, as text: the apse, the pitched roofs, the windows."""
    out = ["cross walls on z %d and %d; end pavilions from |z| %d; corner piers on rows %s"
           % (CROSS_Z + (PAVILION_Z[1],) + (" ".join("%d" % z for z in END_PIER_ROWS),))]
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


# --- checks -----------------------------------------------------------------------------------
def check():
    """Things that must hold for the walls to be buildable. Returns a list of problems."""
    bad = []
    for name, (opening, glass) in apse_windows().items():
        zs = sorted(z for _, z in opening)
        if len(opening) not in (2, 3) or zs != list(range(zs[0], zs[0] + len(zs))) or len({x for x, _ in opening}) != 1:
            bad.append("apse window %s is not a straight run of two or three: %s" % (name, opening))
        if (set(opening) | set(glass)) & set(apse_pilasters()):
            bad.append("apse window %s: a window column is a pilaster" % name)
        for x, z in glass:
            if ring(x + 1, z) > R_GLASS:
                bad.append("apse window %s: nothing closes the wall behind glass (%d, %d)" % (name, x, z))
    for bay in range(1, S.N_BAYS + 1):
        rows = window_rows(bay)
        if len(rows) not in (2, 3) or rows != list(range(rows[0], rows[0] + len(rows))):
            bad.append("bay %d: its window is not a straight run of two or three rows: %s" % (bay, rows))
    for zf in (S.Z_NORTH, S.Z_SOUTH):
        for bay, cols in end_wall_bays(zf):
            if len(cols) not in (2, 3) or cols != list(range(cols[0], cols[0] + len(cols))):
                bad.append("end wall z %d, bay %d: its window is not a straight run of two or three: %s" % (zf, bay, cols))
    taken = {}
    for w in plan_windows():                                 # no glass column belongs to two windows
        name = "%s %s %s" % (w["front"], w["bay"], w["storey"])
        for cell in w["cells"]:
            other = taken.setdefault((cell, w["storey"]), name)
            if other != name:
                bad.append("windows %s and %s share the glass column %s" % (other, name, cell))
    ridge = max(roof_steps(x, ROOF_Z[0]) for x in range(S.WALL_W + 1, east_face(ROOF_Z[0])))
    if ROOF_EAVE_TOP + ROOF_STEP * ridge != ROOF_RIDGE_TOP:
        bad.append("pitched roofs: the ridge stands at %.1f, not at %.1f" % (ROOF_EAVE_TOP + ROOF_STEP * ridge, ROOF_RIDGE_TOP))
    return bad


def main(argv):
    print(tables())
    print()
    problems = check()
    for p in problems:
        print("PROBLEM:", p)
    if not problems:
        print("self-check: the apse's windows, the bays of the long fronts and of the end walls, "
              "the glass columns, the pitched roofs -- all as planned")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
