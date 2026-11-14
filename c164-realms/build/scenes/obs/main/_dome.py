"""The rotunda above the main cornice, as massing: the stone drum with its ring of small windows,
the iron gallery, the verdigris dome in twenty gores with raised ribs, the observing slit
(plan/ART-PLAN.md 5.2; the skeleton's DOME_* numbers).

This is the outer shell only, laid with the elevation grammar where it is stone, so the great
front has its crown and the silhouette can be judged. What the rotunda card adds on top of it:
the track and its rollers under the skirt, the shutter of the slit, the inspection ladder, round
frames on the windows, the room inside. The name starts with an underscore: main/facade.py calls
it, the category's auto-discovery does not.

Why twenty gores: at radius 13 a gore is then four blocks wide at the foot, one of rib and three
of plate -- the bay of the fronts below (a pilaster and three of window). Seen from the court the
ribs come down at z = +-2, +-6 and +-10, the lines of the pilasters of the entrance front, and
the drum's own pilasters and windows fall on the same grid. A gore, not a rib, lies on each of
the four axes: the slit takes the west one.

Rows, from the main cornice (y 15) up:

    16       the attic course: a band of sunk panels, level with the parapet beside it
    17..21   the drum, dressed stone: a pilaster under every rib that meets a straight run of the
             round wall, a small window at y 20 in every gore, a sunk field under the window on
             each of the four axes (the east one is the seat of the station's emblem)
    22       a corbel course under the gallery; it breaks forward over the pilasters
    23       the gallery: iron grating two blocks wide; its railing stands at y 24
    24       the skirt of the dome, riveted iron (the track and rollers go here)
    25..37   the dome: verdigris plates, a raised rib on each of twenty meridians up to a collar,
             darker runs below the ribs; the slit is 5 wide, looks west and is open through the apex
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
CROWN = S.DOME_APEX + 1.0               # 38.0: the top face of the apex block
RIB_FOOT = SKIRT_Y + 2                  # the ribs start above head height on the gallery
COLLAR = (5.0, 6.0)                     # the ring the ribs run into: nearer the apex they would touch
PILASTER_OFF = 4.5                      # a pilaster stands at most this many degrees off its rib
SLIT_HALF = S.SLIT_W // 2               # 2: the slit is z -2..2
SLIT_PAST = 2                           # and runs this far past the apex

PLATE, RIB, RUN = B.VERDIGRIS_CUT, B.VERDIGRIS, B.VERDIGRIS_STREAK
SKIRT = B.IRON_RIVETED.block


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
    return [(k + 0.5) * GORE_DEG for k in range(GORES)]


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
    for x, z in p.front | p.far:
        canvas.set(ox + x, oy + DRUM_TOP, oz + z, B.IRON_GRATE)
    for x, z in p.far:
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


def _in_slit(x, z):
    return abs(z - CZ) <= SLIT_HALF and x <= CX + SLIT_PAST


def _on_rib(x, z):
    """Does the column lie on one of the meridians of the ribs (a line one block wide)?"""
    dx, dz = x - CX, z - CZ
    for a in rib_angles():
        ux, uz = math.cos(math.radians(a)), math.sin(math.radians(a))
        if dx * ux + dz * uz > 0 and abs(dx * uz - dz * ux) <= 0.5:
            return True
    return False


def _raised(x, z):
    """Is the column one of those that stand a block proud of the plates: a rib below the collar,
    the collar, a rail beside the slit?"""
    d = math.hypot(x - CX, z - CZ)
    if _in_slit(x, z):
        return False
    if abs(z - CZ) == SLIT_HALF + 1 and x <= CX + SLIT_PAST + 1:
        return True
    return COLLAR[0] <= d < COLLAR[1] or (d >= COLLAR[1] and _on_rib(x, z))


def dome(canvas, origin=(0, 0, 0)):
    """The dome's shell: one block thick, the slit left open, a rail on either side of it."""
    ox, oy, oz = origin
    skin = _tops(R + 0.5, CROWN)                        # the plates: the face of ring 13 is at 13.5
    # one block outside them: where the ribs run. Whole blocks only: plain verdigris has no slab,
    # and a rib that changed its material at every half step would not read as one line
    proud = _tops(R + 1.5, CROWN + 1.0, slabs=False)

    def put(x, y, z, state):
        canvas.set(ox + x, oy + y, oz + z, state)

    for (x, z), (ytop, whole) in skin.items():
        if _in_slit(x, z):
            continue
        lows = [skin[n][0] if n in skin else SKIRT_Y - 1 for n in (O.step((x, z), d) for d in O.SIDES)]
        for y in range(max(SKIRT_Y, min(ytop, min(lows) + 1)), ytop + 1):
            if y == SKIRT_Y:
                put(x, y, z, SKIRT)
            elif y == ytop and not whole:
                put(x, y, z, f"{PLATE.slab}[type=bottom]")
            else:
                put(x, y, z, PLATE.block)

    for (x, z), (ytop, _whole) in proud.items():
        if not _raised(x, z):
            continue
        foot = RIB_FOOT
        if (x, z) in skin:
            below, solid = skin[(x, z)]
            foot = max(foot, below + 1 if solid else below)
        for y in range(foot, max(ytop, foot) + 1):          # at least one block proud of its plate
            put(x, y, z, RIB)

    for (x, z), (ytop, _whole) in skin.items():         # the darker runs: below a rib, down the plates
        d = math.hypot(x - CX, z - CZ)
        if d < R - 1.5 or _in_slit(x, z) or _on_rib(x, z):
            continue
        if not any(_on_rib(*O.step((x, z), s)) for s in O.SIDES):
            continue
        length = (x * 7 + z * 13) % 5                   # 0..4 rows, the same every time it is built
        for y in range(RIB_FOOT - 1, min(RIB_FOOT - 1 + length, ytop + 1)):
            if canvas.get(ox + x, oy + y, oz + z) == PLATE.block:
                put(x, y, z, RUN.block)


def build(canvas, origin=(0, 0, 0), glass=None):
    windows = drum(canvas, origin, glass)
    dome(canvas, origin)
    return windows
