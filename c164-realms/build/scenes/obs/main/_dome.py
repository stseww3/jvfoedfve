"""The rotunda above the main cornice: the stone drum with its ring of small windows, the iron
gallery, the verdigris dome in twenty gores, the observing slit and its shutter
(plan/ART-PLAN.md 5.2; the skeleton's DOME_* numbers; the card is plan/packages/main/dome.md).

This is the outer shell, laid with the elevation grammar where it is stone. The room inside, the
round frames of the windows, the door leaves and the true rollers are other cards'. The name starts
with an underscore: the category's auto-discovery does not take it; main/dome.py is the package
and main/facade.py reads the drum's windows from here.

Why twenty gores: at radius 13 a gore is then four blocks wide at the foot, one of rib and three
of plate -- the bay of the fronts below (a pilaster and three of window). Seen from the court the
gore seams come down at z = +-2, +-6 and +-10, the lines of the pilasters of the entrance front,
and the drum's own pilasters and windows fall on the same grid. A gore, not a seam, lies on each
of the four axes: the slit takes the west one.

Rows, from the main cornice (y 15) up:

    16       the attic course: a band of sunk panels, level with the parapet beside it
    17..21   the drum, dressed stone: a pilaster under every seam that meets a straight run of the
             round wall, a small window at y 20 in every gore, a sunk field under the window on
             each of the four axes (the east one is the seat of the station's emblem); the two
             doors of the dome room at y 18..19 (the skeleton's DOME_ROOM_DOORS)
    22       a corbel course under the gallery; it breaks forward over the pilasters
    23       the gallery: a copper gutter one block wide at the dome's foot, sunk half a block,
             and an iron grating outside it that carries the railing (y 24); the top of the wall
             is the iron track
    24       the ring beam of the dome, riveted iron, an axle box under every seam
    25       the sill of the slit; from here up the dome: verdigris plates
    26..37   the ribs, the slit (5 wide, looks west, open through the apex and two blocks past it)

Two versions, one idea each for how close the ribs stand and how the slit is shut:

    a   twenty fine ribs, one on every seam, dying into a broad collar; the top stays bare. The
        slit is shut by two framed leaves that part sideways and lie on the dome beside it.
    b   eight main ribs, the pair beside each of the four axis fields; the twelve seams between
        them lie flush, a darker line. They die into a frame round the head of the slit. The slit
        is shut by a slatted curtain between two rails that rolls up into a housing on the crown.
"""
import math

from ..common import blocks as B
from ..common import skeleton as S
from . import _order as O

CX, CZ = S.DOME_CENTRE
R = S.DOME_R
GORES = 20
GORE_DEG = 360.0 / GORES
ATTIC = S.PARAPET[0]                    # 16: the first row above the main cornice
DRUM_TOP = S.DRUM[1]                    # 23: the gallery's row
WINDOW_Y = (S.DRUM[0] + S.DRUM[1]) // 2                     # 20
FIELD_Y = (WINDOW_Y - 2, WINDOW_Y - 1)  # the sunk field under an axis window
CORBEL_Y = DRUM_TOP - 1                 # 22
SKIRT_Y = S.DOME_SPRING                 # 24
SILL_Y = SKIRT_Y + 1                    # 25: the slit opens above this row
CROWN = S.DOME_APEX + 1.0               # 38.0: the top face of the apex block
RIB_FOOT = SKIRT_Y + 2                  # the ribs start above head height on the gallery
PILASTER_OFF = 4.5                      # a pilaster stands at most this many degrees off its rib
SLIT_HALF = S.SLIT_W // 2               # 2: the slit is z -2..2
SLIT_PAST = 2                           # and runs this far past the apex
SLIT_HEAD = CX + SLIT_PAST              # 6: the last column of the slit
DOORS = getattr(S, "DOME_ROOM_DOORS", dict(cells=((12, 10), (12, -10)), y=(18, 19)))

PLATE, RIB, RUN = B.VERDIGRIS_CUT, B.VERDIGRIS, B.VERDIGRIS_STREAK
CAST = B.VERDIGRIS_CAST
SKIRT = B.IRON_RIVETED.block
AXLE_BOX = B.IRON_CAST
TRACK = B.IRON_PLATE
GUTTER = B.OLD_COPPER_CUT

VERSIONS = ("a", "b")
STATES = ("open", "half", "closed")
MAIN_RIBS = tuple(k for k in range(GORES) if k % 5 in (1, 3))       # version b: 27, 63, 117, 153 ... degrees
COLLAR = {"a": (5.0, 6.0), "b": (4.0, 5.0)}                         # the ring the ribs run into
PARTED = {"closed": 0, "half": 2, "open": SLIT_HALF + 1}            # version a: how far each leaf has slid
ROLLED = {"closed": 0.0, "half": 46.0, "open": 181.0}               # version b: the curtain is up to here (degrees)
SLAT_DEG = 5.0                          # a slat of the curtain, in degrees along the meridian
HOUSING_TOP = S.DOME_APEX + 2           # 39: the slab that rounds off the curtain's housing


def _polar(x, z):
    """Distance from the dome's centre column and the angle round it (0 = east, 90 = south)."""
    return math.hypot(x - CX, z - CZ), math.degrees(math.atan2(z - CZ, x - CX)) % 360.0


def _apart(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _nearest(cells, angle):
    """The column closest to an angle, and how far off it is; of two equally close, the one that is
    its mirror image on the other side of the building's axes gets the same answer."""
    best = min(cells, key=lambda c: (round(_apart(_polar(*c)[1], angle), 3), abs(c[1] - CZ), abs(c[0] - CX), c))
    return best, _apart(_polar(*best)[1], angle)


def rib_angles():
    """The twenty seams between the gores."""
    return [(k + 0.5) * GORE_DEG for k in range(GORES)]


def ribs(version="a"):
    """The seams that carry a raised rib."""
    angles = rib_angles()
    return angles if version == "a" else [angles[k] for k in MAIN_RIBS]


def seams(version="a"):
    """The seams that lie flush with the plates."""
    return [] if version == "a" else [a for k, a in enumerate(rib_angles()) if k not in MAIN_RIBS]


def window_cells():
    """{wall column: gore number} of the drum's windows: in the middle of each gore, the column of
    the wall line closest to it that looks one way only (a corner of the raster circle cannot take
    an opening). Gore 0 looks east; they count round by the south."""
    body = O.disc(CX, CZ, R)
    wall = body - O.shrink(body)
    flat = [c for c in wall if sum(O.step(c, d) not in body for d in O.SIDES) == 1]
    return {_nearest(flat, k * GORE_DEG)[0]: k for k in range(GORES)}


def pilaster_cells():
    """The columns of the pilaster plane that carry a pilaster: under each rib, where a column
    stands clear in front of one wall column (in a step of the raster circle a pilaster would only
    move the step). The four ribs on the diagonals find none and come down on the corner itself."""
    body = O.disc(CX, CZ, R)
    clear = [c for c in O.ring(body) if sum(O.step(c, d) in body for d in O.SIDES) == 1]
    out = []
    for a in rib_angles():
        cell, off = _nearest(clear, a)
        if off <= PILASTER_OFF:
            out.append(cell)
    return sorted(set(out))


def plan():
    cells = window_cells()
    return O.Plan(O.disc(CX, CZ, R), lambda x, z, outs: O.Bay("drum", cells[(x, z)]) if (x, z) in cells else None,
                  pilasters=pilaster_cells())


def order():
    fine, panel = B.ASHLAR_FINE, B.ASHLAR_PANEL
    return [
        O.Storey((ATTIC, ATTIC), "attic", wall=panel, pier=fine),
        O.Storey((ATTIC + 1, CORBEL_Y - 1), "drum", wall=fine, pier=fine, window=O.Window((WINDOW_Y, WINDOW_Y))),
        O.Course(CORBEL_Y, fine, inner=panel),
        O.Storey((DRUM_TOP, DRUM_TOP), "track", wall=fine),
    ]


def fields(p):
    """[(wall columns, the columns behind them)] of the sunk fields: under the window of each gore
    that lies on an axis, as wide as the run between its two pilasters."""
    out = []
    for op in p.openings:
        if op.bay % (GORES // 4):
            continue
        side = (op.out[1], op.out[0])                       # along the wall
        cells = [O.step(op.cells[0], side, n) for n in (-1, 0, 1)]
        if all(c in p.wall and O.step(c, op.out) not in p.piers for c in cells):
            out.append((cells, [O.step(c, op.inward) for c in cells]))
    return out


def doors(p):
    """[(wall column, the column of the inner leaf behind it)] of the dome room's doors."""
    return [(c, O.step(c, p.outs[c][0], -1)) for c in DOORS["cells"] if len(p.outs.get(c, ())) == 1]


def drum(canvas, origin=(0, 0, 0), glass=None):
    """The drum and its gallery; returns the drum's windows (see _order.build)."""
    p = plan()
    windows = O.build(canvas, p, order(), origin, glass=glass)
    ox, oy, oz = origin
    for cells, behind in fields(p):
        for y in range(FIELD_Y[0], FIELD_Y[1] + 1):
            for (x, z), (bx, bz) in zip(cells, behind):
                canvas.clear(ox + x, oy + y, oz + z)
                canvas.set(ox + bx, oy + y, oz + bz, B.ASHLAR_PANEL.block)
    for pair in doors(p):
        for y in range(DOORS["y"][0], DOORS["y"][1] + 1):
            for x, z in pair:
                canvas.clear(ox + x, oy + y, oz + z)
    for x, z in p.wall:
        canvas.set(ox + x, oy + DRUM_TOP, oz + z, TRACK)
    for x, z in p.front:
        canvas.set(ox + x, oy + DRUM_TOP, oz + z, f"{GUTTER.slab}[type=bottom]")
    for x, z in p.far:
        canvas.set(ox + x, oy + DRUM_TOP, oz + z, B.IRON_GRATE)
        canvas.set(ox + x, oy + DRUM_TOP + 1, oz + z, B.IRON_BARS)
    return windows


# --- the dome ---------------------------------------------------------------------------------------
def _surface(d, r, top):
    """Height of a half-ellipse over the skirt's foot: r wide at the foot, `top` high at the centre."""
    return SKIRT_Y + (top - SKIRT_Y) * math.sqrt(max(0.0, 1.0 - (d / r) ** 2))


def _tops(r, top, slabs=True):
    """{column: (y of its top cell, the cell is a whole block)} of a dome r wide at the foot: whole
    blocks up to the surface, a slab where it passes through the middle of a cell (slabs=False:
    whole blocks only, to the nearer side)."""
    out = {}
    n = int(r) + 1
    for x in range(CX - n, CX + n + 1):
        for z in range(CZ - n, CZ + n + 1):
            d = math.hypot(x - CX, z - CZ)
            if d >= r:
                continue
            h = _surface(d, r, top)
            fl = math.floor(h)
            frac = h - fl
            if slabs:
                out[(x, z)] = (fl - 1, True) if frac < 0.25 else (fl, False) if frac < 0.75 else (fl, True)
            else:
                out[(x, z)] = (fl, True) if frac >= 0.5 else (fl - 1, True)
    return out


def _skin():
    """The plates: the face of ring 13 is at 13.5."""
    return _tops(R + 0.5, CROWN)


def _proud():
    """One block outside the plates: where the ribs, the rails and the leaves run. Whole blocks
    only: plain verdigris has no slab, and a rib that changed its material at every half step would
    not read as one line."""
    return _tops(R + 1.5, CROWN + 1.0, slabs=False)


def _foot(tops, c):
    """The lowest cell a column of a one-block shell has to fill so that no gap opens to a lower
    neighbour (a neighbour outside the shell counts as the gallery)."""
    lows = [tops[n][0] if n in tops else SKIRT_Y - 1 for n in (O.step(c, d) for d in O.SIDES)]
    return max(SKIRT_Y, min(tops[c][0], min(lows) + 1))


def _in_slit(x, z):
    return abs(z - CZ) <= SLIT_HALF and x <= SLIT_HEAD


def _on(x, z, angles):
    """Does the column lie on one of these meridians (a line one block wide)?"""
    dx, dz = x - CX, z - CZ
    for a in angles:
        ux, uz = math.cos(math.radians(a)), math.sin(math.radians(a))
        if dx * ux + dz * uz > 0 and abs(dx * uz - dz * ux) <= 0.5:
            return True
    return False


def _raised(x, z, version):
    """Is the column one of those that stand a block proud of the plates: a rib below the collar,
    the collar, what frames the slit?"""
    if _in_slit(x, z):
        return False
    d = math.hypot(x - CX, z - CZ)
    side, past = abs(z - CZ), x - SLIT_HEAD
    if version == "a":
        if past == 1 and side <= SLIT_HALF + 1:             # the bar across the slit's head
            return True
    elif side == SLIT_HALF + 1 and past <= 2:               # the two rails of the curtain
        return True
    lo, hi = COLLAR[version]
    return lo <= d < hi or (d >= hi and _on(x, z, ribs(version)))


def _above(skin, c):
    """The first cell over a column's plate (a slab is given up for a whole block)."""
    below, solid = skin[c]
    return below + 1 if solid else below


def _elevation(x, y):
    """Where a cell of the slit lies along its meridian, in degrees: 0 at the foot, 90 at the apex,
    more past it."""
    return math.degrees(math.atan2((y + 0.5 - SKIRT_Y) / (CROWN - SKIRT_Y), (CX - x) / (R + 0.5)))


def dome(canvas, origin=(0, 0, 0), version="a"):
    """The dome's shell, one block thick, the slit left open above its sill."""
    ox, oy, oz = origin
    skin, proud = _skin(), _proud()
    raised, flush = ribs(version), seams(version)
    hi = COLLAR[version][1]

    def put(x, y, z, state):
        canvas.set(ox + x, oy + y, oz + z, state)

    for (x, z), (ytop, whole) in skin.items():
        slit = _in_slit(x, z)
        seam = not slit and math.hypot(x - CX, z - CZ) >= hi and _on(x, z, flush)
        family = RUN if seam else PLATE
        for y in range(_foot(skin, (x, z)), ytop + 1):
            if y == SKIRT_Y:
                put(x, y, z, AXLE_BOX if _on(x, z, rib_angles()) else SKIRT)
            elif slit and y > SILL_Y:
                break
            elif y == ytop and not whole:
                put(x, y, z, f"{family.slab}[type=bottom]")
            else:
                put(x, y, z, family.block)

    for (x, z), (ytop, _whole) in proud.items():
        if not _raised(x, z, version):
            continue
        foot = max(RIB_FOOT, _above(skin, (x, z))) if (x, z) in skin else RIB_FOOT
        for y in range(foot, max(ytop, foot) + 1):          # at least one block proud of its plate
            put(x, y, z, RIB)

    for (x, z), (ytop, _whole) in skin.items():         # the darker runs: below a rib, down the plates
        d = math.hypot(x - CX, z - CZ)
        if d < R - 1.5 or _in_slit(x, z) or _on(x, z, raised):
            continue
        if not any(_on(*O.step((x, z), s), raised) for s in O.SIDES):
            continue
        length = (x * 7 + z * 13) % 5                   # 0..4 rows, the same every time it is built
        for y in range(RIB_FOOT - 1, min(RIB_FOOT - 1 + length, ytop + 1)):
            if canvas.get(ox + x, oy + y, oz + z) == PLATE.block:
                put(x, y, z, RUN.block)

    if version == "b":                                  # the housing the curtain rolls up into
        for x in (SLIT_HEAD + 1, SLIT_HEAD + 2):
            for z in range(CZ - SLIT_HALF - 1, CZ + SLIT_HALF + 2):
                end = abs(z - CZ) == SLIT_HALF + 1
                for y in range(_above(skin, (x, z)), HOUSING_TOP):
                    put(x, y, z, CAST if end else RIB)
                put(x, HOUSING_TOP, z, CAST if end else f"{PLATE.slab}[type=bottom]")


def _leaves(canvas, origin, state):
    """Version a: two framed leaves, each as wide as half the slit and its frame. Shut they meet on
    the axis; open they have slid apart along the foot ring and the bar at the slit's head and lie
    on the dome beside the slit."""
    ox, oy, oz = origin
    skin, proud = _skin(), _proud()
    shift, width = PARTED[state], SLIT_HALF + 1
    for side in (-1, 1):
        stiles = (CZ + side * shift, CZ + side * (shift + width))
        zs = range(min(stiles), max(stiles) + 1)
        for (x, z), (ytop, _whole) in proud.items():
            if z not in zs or x > SLIT_HEAD:
                continue
            if (x, z) in skin and not _in_slit(x, z):
                foot = _above(skin, (x, z))
            elif (x, z) in skin:
                foot = _foot(proud, (x, z))
            else:
                foot = RIB_FOOT                             # over the gallery, like the feet of the ribs
            frame = z in stiles or x == SLIT_HEAD
            for y in range(max(foot, RIB_FOOT), max(ytop, foot) + 1):
                canvas.set(ox + x, oy + y, oz + z, RIB if frame else PLATE.block)


def _curtain(canvas, origin, state):
    """Version b: a curtain of copper slats in the plane of the plates, between the two rails. It
    rolls up into the housing at the slit's head, so it opens from the sill upwards; its last slat
    is a heavier bar."""
    ox, oy, oz = origin
    skin = _skin()
    # the slats are straight, so the curtain is the dome's section on the axis carried across the slit
    line = {x: top for (x, z), top in skin.items() if z == CZ and x <= SLIT_HEAD + 1}
    up = ROLLED[state]
    bar = int(max(up, _elevation(min(line), SILL_Y + 1)) / SLAT_DEG)    # the lowest slat that is down
    for x, (ytop, whole) in line.items():
        if x > SLIT_HEAD:
            continue
        lows = [line[n][0] if n in line else SKIRT_Y - 1 for n in (x - 1, x + 1)]
        for y in range(max(SILL_Y + 1, min(ytop, min(lows) + 1)), ytop + 1):
            at = _elevation(x, y)
            if at < up:
                continue
            slat = int(at / SLAT_DEG)
            family = RUN if slat % 3 == 2 else PLATE
            if slat == bar:
                block = RIB
            elif y == ytop and not whole:
                block = f"{family.slab}[type=bottom]"
            else:
                block = family.block
            for z in range(CZ - SLIT_HALF, CZ + SLIT_HALF + 1):
                canvas.set(ox + x, oy + y, oz + z, block)


def shutter(canvas, origin=(0, 0, 0), version="a", state="open"):
    """What shuts the slit, in one of STATES."""
    if state not in STATES:
        raise ValueError(f"the slit is one of {STATES}, not {state!r}")
    (_leaves if version == "a" else _curtain)(canvas, origin, state)


def build(canvas, origin=(0, 0, 0), glass=None, version="a", slit="open"):
    """The whole rotunda above the cornice. Returns the drum's windows."""
    if version not in VERSIONS:
        raise ValueError(f"the dome has versions {VERSIONS}, not {version!r}")
    windows = drum(canvas, origin, glass)
    dome(canvas, origin, version)
    shutter(canvas, origin, version, slit)
    return windows
