"""The rotunda above the main cornice, as massing: the stone drum with its ring of small windows,
the iron gallery, the verdigris dome in sixteen gores with raised ribs, the observing slit
(plan/ART-PLAN.md 5.2; the skeleton's DOME_* numbers).

This is the outer shell only, laid with the elevation grammar where it is stone, so the great
front has its crown and the silhouette can be judged. What the rotunda card adds on top of it:
the track and its rollers under the skirt, the shutter of the slit, the inspection ladder, round
frames on the windows, the room inside. The name starts with an underscore: main/facade.py calls
it, the category's auto-discovery does not.

Rows, from the main cornice (y 15) up:

    16       the attic course: a band of sunk panels, level with the parapet beside it
    17..21   the drum, dressed stone; sixteen small windows at y 20, one in each gore
    22       a corbel course under the gallery
    23       the gallery: iron grating two blocks wide; its railing stands at y 24
    24       the skirt of the dome, riveted iron (the track and rollers go here)
    25..37   the dome: verdigris plates, a raised rib on each of sixteen meridians, darker runs
             below the ribs; the slit is 5 wide, looks west and is open through the apex
"""
import math

from ..common import blocks as B
from ..common import skeleton as S
from . import _order as O

CX, CZ = S.DOME_CENTRE
R = S.DOME_R
GORES = 16
ATTIC = S.PARAPET[0]                    # 16: the first row above the main cornice
DRUM_TOP = S.DRUM[1]                    # 23: the gallery's row
WINDOW_Y = (S.DRUM[0] + S.DRUM[1]) // 2                     # 20
CORBEL_Y = DRUM_TOP - 1                 # 22
SKIRT_Y = S.DOME_SPRING                 # 24
CROWN = S.DOME_APEX + 1.0               # 38.0: the top face of the apex block
RIB_FOOT = SKIRT_Y + 2                  # the ribs start above head height on the gallery
RIB_INNER = 3.5                         # nearer the apex than this the ribs have run together
SLIT_HALF = S.SLIT_W // 2               # 2: the slit is z -2..2
SLIT_PAST = 2                           # and runs this far past the apex

PLATE, RIB, RUN = B.VERDIGRIS_CUT, B.VERDIGRIS, B.VERDIGRIS_STREAK
RIB_SLAB = B.VERDIGRIS_CUT.slab         # plain verdigris has no slab: a rib's last half step is cut copper
SKIRT = B.IRON_RIVETED.block


def _polar(x, z):
    """Distance from the dome's centre column and the angle round it (0 = east, 90 = south)."""
    return math.hypot(x - CX, z - CZ), math.degrees(math.atan2(z - CZ, x - CX)) % 360.0


def _apart(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def window_cells():
    """{wall column: gore number} of the drum's windows: in the middle of each gore, the column of
    the wall line closest to it that looks one way only (a corner of the raster circle cannot take
    an opening). Gore 0 is the first one south of east; they count round by the south."""
    body = O.disc(CX, CZ, R)
    wall = body - O.shrink(body)
    flat = [c for c in wall if sum(O.step(c, d) not in body for d in O.SIDES) == 1]
    out = {}
    for k in range(GORES):
        mid = (k + 0.5) * 360.0 / GORES
        out[min(flat, key=lambda c: (round(_apart(_polar(*c)[1], mid), 3), c))] = k
    return out


def plan():
    cells = window_cells()
    return O.Plan(O.disc(CX, CZ, R), lambda x, z, outs: O.Bay("drum", cells[(x, z)]) if (x, z) in cells else None)


def order():
    return [
        O.Storey((ATTIC, ATTIC), "attic", wall=B.ASHLAR_PANEL),
        O.Storey((ATTIC + 1, CORBEL_Y - 1), "drum", wall=B.ASHLAR_FINE, window=O.Window((WINDOW_Y, WINDOW_Y))),
        O.Course(CORBEL_Y, B.ASHLAR_FINE, inner=B.ASHLAR_PANEL),
        O.Storey((DRUM_TOP, DRUM_TOP), "track", wall=B.ASHLAR_FINE),
    ]


def drum(canvas, origin=(0, 0, 0), glass=None):
    """The drum and its gallery; returns the drum's windows (see _order.build)."""
    p = plan()
    windows = O.build(canvas, p, order(), origin, glass=glass)
    ox, oy, oz = origin
    for x, z in p.front | p.far:
        canvas.set(ox + x, oy + DRUM_TOP, oz + z, B.IRON_GRATE)
    for x, z in p.far:
        canvas.set(ox + x, oy + DRUM_TOP + 1, oz + z, B.IRON_BARS)
    return windows


# --- the dome ---------------------------------------------------------------------------------------
def _surface(d, r, top):
    """Height of a half-ellipse over the skirt's foot: r wide at the foot, `top` high at the centre."""
    return SKIRT_Y + (top - SKIRT_Y) * math.sqrt(max(0.0, 1.0 - (d / r) ** 2))


def _tops(r, top):
    """{column: (y of its top cell, the cell is a whole block)} of a dome r wide at the foot: whole
    blocks up to the surface, a slab where it passes through the middle of a cell."""
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
            out[(x, z)] = (fl - 1, True) if frac < 0.25 else (fl, False) if frac < 0.75 else (fl, True)
    return out


def _in_slit(x, z):
    return abs(z - CZ) <= SLIT_HALF and x <= CX + SLIT_PAST


def _on_rib(x, z):
    """Does the column lie on one of the sixteen meridians (a line one block wide)?"""
    dx, dz = x - CX, z - CZ
    for k in range(GORES):
        a = math.radians(k * 360.0 / GORES)
        ux, uz = math.cos(a), math.sin(a)
        if dx * ux + dz * uz > 0 and abs(dx * uz - dz * ux) <= 0.5:
            return True
    return False


def dome(canvas, origin=(0, 0, 0)):
    """The dome's shell: one block thick, the slit left open, a rail on either side of it."""
    ox, oy, oz = origin
    skin = _tops(R + 0.5, CROWN)                        # the plates: the face of ring 13 is at 13.5
    proud = _tops(R + 1.5, CROWN + 1.0)                 # one block outside them: where the ribs run

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

    for (x, z), (ytop, whole) in proud.items():
        d = math.hypot(x - CX, z - CZ)
        rail = abs(z - CZ) == SLIT_HALF + 1 and x <= CX + SLIT_PAST + 1
        if _in_slit(x, z) or d < RIB_INNER or not (rail or _on_rib(x, z)):
            continue
        foot = RIB_FOOT
        if (x, z) in skin:
            below, solid = skin[(x, z)]
            foot = max(foot, below + 1 if solid else below)
        for y in range(foot, ytop + 1):
            put(x, y, z, RIB if whole or y < ytop else f"{RIB_SLAB}[type=bottom]")

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
