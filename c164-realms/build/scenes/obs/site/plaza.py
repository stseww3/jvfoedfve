"""A4 site work package site/court (plan ART-PLAN 4): the front court -- its paving, the brass
meridian, the central emblem roundel (where the armillary stands) and the court-edge balustrade.

Read from the stamp: a calm pale court with one dark cross -- the north-south brass meridian and the
east-west processional runner -- meeting on a focal roundel that points the eye to the lit entrance.
Everything here is blocks (the module places no display entities): the armillary (A5), the court
lamps and the balustrade ironwork (A6) are set by others against the anchors in plan/parts/A4-site.md.
"""
import math

from artkit.canvas import Mix

from ..common import blocks as B
from ..common import skeleton as S

ORDER = 60          # runs after ground.py (default 50): the designed court overwrites the demo floor

# --- materials: occupancy-table roles only (blocks.py) -------------------------------------------
FIELD = Mix({B.TUFF_SMOOTH.block: 6, B.TUFF.block: 1}, seed=41)   # warm-grey field, a little variation
GRID = B.SLATE_SMOOTH.block                                       # deep-slate joints on the bay module
BORDER = B.SLATE_BRICK.block                                      # dark bands framing the runner and meridian
RUNNER = B.ASHLAR_FINE.block                                      # pale processional runner to the door
EMBLEM = B.ASHLAR_EMBLEM                                          # chiseled stone of the emblem roundel
BRASS = B.BRASS_INLAY                                             # the brass line in the floor (yellow_carpet)
POST = B.ASHLAR_ROUGH.block                                      # balustrade post
RAIL = B.ASHLAR_ROUGH.wall                                       # balustrade rail
COPING = B.ASHLAR_PANEL.slab + "[type=top]"                      # balustrade coping

# --- court extent (skeleton; A4 provisional, see A4-site.md section 2) ----------------------------
CX0, CZ0, CX1, CZ1 = S.FRONT_COURT                               # x 16..60, z -30..30
MX = S.MERIDIAN_X                                                # 35: the north-south meridian line
AXIS_Z = 0                                                       # the entrance / building centre line
RUN_HALF = 2                                                     # processional half-width (z in [-2, 2])
ROUND_R = 4                                                      # emblem roundel radius


def _rect(c, o, x0, z0, x1, z1, y, state):
    ox, oy, oz = o
    for x in range(int(x0), int(x1) + 1):
        for z in range(int(z0), int(z1) + 1):
            c.set(ox + x, oy + y, oz + z, state)


def _paving(c, o):
    """The field and a deep-slate joint grid on the main-building bay module, so the court carries
    the same 4-block rhythm as the facade and reads at a small scale."""
    ox, oy, oz = o
    y = S.PAVING_Y
    _rect(c, o, CX0, CZ0, CX1, CZ1, y, FIELD)
    for x in range(CX0, CX1 + 1):
        if (x - CX0) % S.BAY == 0:
            for z in range(CZ0, CZ1 + 1):
                c.set(ox + x, oy + y, oz + z, GRID)
    for z in range(CZ0, CZ1 + 1):
        if (z - AXIS_Z) % S.BAY == 0:
            for x in range(CX0, CX1 + 1):
                c.set(ox + x, oy + y, oz + z, GRID)


def _processional(c, o):
    """The pale east-west runner on the entrance axis, from clear of the central prow to the stair
    head, with dark border lines; it leads the eye straight to the door in V2."""
    y = S.PAVING_Y
    x0 = S.east_wall_x(9) + 1                    # clear of the central prow (x=17) -> start at x=18
    _rect(c, o, x0, AXIS_Z - RUN_HALF, CX1, AXIS_Z + RUN_HALF, y, RUNNER)
    _rect(c, o, x0, AXIS_Z - RUN_HALF - 1, CX1, AXIS_Z - RUN_HALF - 1, y, BORDER)
    _rect(c, o, x0, AXIS_Z + RUN_HALF + 1, CX1, AXIS_Z + RUN_HALF + 1, y, BORDER)


def _meridian(c, o):
    """The brass meridian: a chiseled-stone bed with dark borders in the paving, and the brass line
    (a carpet) on top of it, running the length of the court, broken at the roundel."""
    ox, oy, oz = o
    for z in range(CZ0, CZ1 + 1):
        c.set(ox + MX - 1, oy + S.PAVING_Y, oz + z, BORDER)
        c.set(ox + MX + 1, oy + S.PAVING_Y, oz + z, BORDER)
        c.set(ox + MX, oy + S.PAVING_Y, oz + z, EMBLEM)
    for z in range(CZ0, CZ1 + 1):
        if abs(z - AXIS_Z) <= ROUND_R - 1:
            continue                              # the roundel draws its own meridian
        c.set(ox + MX, oy + S.GROUND, oz + z, BRASS)


def _emblem(c, o):
    """The emblem roundel at (MX, AXIS_Z): a pale chiseled disc in a dark ring, with the brass emblem
    on top -- a meridian line and a star to the north-east (plan 2 symbol). The centre cell is left
    clear above the paving for the armillary (A5); a floor block stays under it."""
    ox, oy, oz = o
    cx, cz = MX, AXIS_Z
    for x in range(cx - ROUND_R - 1, cx + ROUND_R + 2):
        for z in range(cz - ROUND_R - 1, cz + ROUND_R + 2):
            d = math.hypot(x - cx, z - cz)
            if d <= ROUND_R - 0.5:
                c.set(ox + x, oy + S.PAVING_Y, oz + z, EMBLEM)
            elif d <= ROUND_R + 0.5:
                c.set(ox + x, oy + S.PAVING_Y, oz + z, BORDER)
    for z in range(cz - ROUND_R + 1, cz + ROUND_R):
        if z == cz:
            continue                              # keep the centre clear for the armillary
        c.set(ox + cx, oy + S.GROUND, oz + z, BRASS)
    rr = ROUND_R - 1                              # the emblem ring, in brass, on the pale disc
    for a in range(0, 360, 6):
        x = cx + round(rr * math.cos(math.radians(a)))
        z = cz + round(rr * math.sin(math.radians(a)))
        c.set(ox + x, oy + S.GROUND, oz + z, BRASS)
    for dx, dz in ((2, -2), (3, -2), (2, -3), (1, -2), (2, -1)):   # a small star, north-east of centre
        c.set(ox + cx + dx, oy + S.GROUND, oz + cz + dz, BRASS)


def _balustrade(c, o):
    """A low grey-white stone balustrade along the east lip (the drop to the lower platform), with
    the gap where the grand stair descends (site/stair). Kept low so it does not break the V2 axis."""
    ox, oy, oz = o
    gs = S.GRAND_STAIR
    gz0, gz1 = gs["z0"], gs["z1"]
    x = CX1
    for z in range(CZ0, CZ1 + 1):
        if gz0 <= z <= gz1:
            continue
        if (z - CZ0) % S.BAY == 0:
            c.set(ox + x, oy + S.GROUND, oz + z, POST)
            c.set(ox + x, oy + S.GROUND + 1, oz + z, COPING)
        else:
            c.set(ox + x, oy + S.GROUND, oz + z, RAIL)


def build(canvas, origin=(0, 0, 0)):
    _paving(canvas, origin)
    _processional(canvas, origin)
    _meridian(canvas, origin)
    _emblem(canvas, origin)
    _balustrade(canvas, origin)
    return 0
