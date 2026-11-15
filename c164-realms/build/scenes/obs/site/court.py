"""site/court: the front court (plan/ART-PLAN.md 4) -- its paving, the brass meridian, the emblem
roundel where the meridian crosses the entrance axis, and the railing on the terrace's east lip.

How the floor is meant to read (plan/aesthetics/part-reviews-cr2.md, points 2 to 4 on the site):
  - darker and cooler than the walls, so that the pale building sits on it: slate, like the plinth.
    Measured on the game's own pictures: polished tuff is 0.40, an ashlar wall facing east shows as
    0.46 once the game has shaded that face, and the two would run together; slate is 0.28;
  - no chequerboard: strips of tuff only on the lines where the front changes plane (the edges of
    the centre pavilion and of the end pavilions) and two across, with large quiet panels between;
  - the cross -- the walk to the door and the meridian -- stays in the middle tone and leads to the
    lit entrance; the only bright thing on the floor is the brass, one block wide.

Every position is read from the skeleton, so the court follows when its edges are moved.
Blocks only: no display entities, no models, no light sources. The armillary on the roundel is the
machines line's; lamps, benches and finer ironwork are the props line's.
"""
import math

from artkit.canvas import Mix

from ..common import blocks as B
from ..common import skeleton as S

ORDER = 60      # after ground.py (50), which lays the plain terrace this court is cut into

# the occupancy table's roles
FIELD = Mix({B.SLATE_SMOOTH.block: 12, B.SLATE_BRICK.block: 3, B.SLATE_TILE.block: 1}, seed=41)
STRIP = B.TUFF_SMOOTH.block     # the middle tone: the strips, the walk, the meridian's two flanks
DISC = B.SLATE_TILE.block       # the darkest: under the emblem, where brass and armillary have to stand out
BRASS = B.BRASS_INLAY           # a carpet lying on the paving
POST = B.ASHLAR_ROUGH.block
CAP = B.ASHLAR_PANEL.slab
RAIL = B.IRON_BARS              # open: a solid rail would hide more of the front from the lower platform
MARK = B.ASHLAR_EMBLEM

X0, Z0, X1, Z1 = S.FRONT_COURT
MX = S.MERIDIAN_X
MZ0, MZ1 = S.MERIDIAN_Z
AX, AZ = S.ARMILLARY            # the roundel is drawn about this cell; nothing is put on it
FLOOR = S.PAVING_Y              # the paving block
ON = S.GROUND                   # what lies or stands on the paving

WALK_HALF = 2                   # the walk is the door bay with its two pilasters: 5 across
RING_R = 7                      # the smallest ring that leaves a clear cell between ring, line and star
STAR = (3, -3)                  # from the roundel's middle; the upper right when north is up
APRON = 4                       # the strip along the front lies this far inside the court's west edge
LIP = 3                         # the strip along the east lip, this far inside it


def _put(c, o, x, y, z, state):
    c.set(o[0] + x, o[1] + y, o[2] + z, state)


def pavilion_lines():
    """z of the pilasters at which the entrance front changes plane: the two edges of the centre
    pavilion and the inner edges of the end pavilions. The five parts of the front, laid on the floor."""
    first, last = S.CENTRE_BAYS[0], S.CENTRE_BAYS[-1]
    north_end = max(b for b in S.END_BAYS if b < first)
    south_end = min(b for b in S.END_BAYS if b > last)
    lines = (S.pilaster_z(north_end), S.pilaster_z(first - 1), S.pilaster_z(last), S.pilaster_z(south_end - 1))
    return [z for z in lines if Z0 <= z <= Z1]


def _paving(c, o):
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            _put(c, o, x, FLOOR, z, FIELD)
    for z in pavilion_lines():
        for x in range(X0, X1 + 1):
            _put(c, o, x, FLOOR, z, STRIP)
    for x in (X0 + APRON, X1 - LIP):
        for z in range(Z0, Z1 + 1):
            _put(c, o, x, FLOOR, z, STRIP)
    for x in range(X0, X1 + 1):                 # the walk on the axis, from the door to the stair head
        for z in range(AZ - WALK_HALF, AZ + WALK_HALF + 1):
            _put(c, o, x, FLOOR, z, STRIP)


def _meridian(c, o):
    """The brass line with a flank of the middle tone either side, the whole length of the court."""
    for z in range(MZ0, MZ1 + 1):
        for x in (MX - 1, MX, MX + 1):
            _put(c, o, x, FLOOR, z, STRIP)
        _put(c, o, MX, ON, z, BRASS)


def _roundel(c, o):
    """The station's emblem (plan 2) in the floor: a brass ring, the meridian through it, a star to
    the upper right, on a dark disc. The middle cell stays empty for the armillary."""
    r = RING_R
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            d = math.hypot(dx, dz)
            if d >= r + 0.5:
                continue
            x, z = AX + dx, AZ + dz
            _put(c, o, x, FLOOR, z, DISC)
            c.clear(o[0] + x, o[1] + ON, o[2] + z)
            on_line = x == MX and (dx, dz) != (0, 0)
            if d >= r - 0.5 or on_line:
                _put(c, o, x, ON, z, BRASS)
    for dx, dz in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        _put(c, o, AX + STAR[0] + dx, ON, AZ + STAR[1] + dz, BRASS)


def _mark(c, o):
    """Where the line ends on the court's south edge: a waist-high stone carrying the emblem."""
    _put(c, o, MX, ON, MZ1, MARK)
    _put(c, o, MX, ON + 1, MZ1, CAP)


def _railing(c, o):
    """Stone posts on the pilaster lines with iron bars between them along the east lip. It is open
    where the grand stair comes up (site/stair), with a taller post either side of the opening."""
    g0, g1 = S.GRAND_STAIR["z0"], S.GRAND_STAIR["z1"]
    newels = (g0 - 1, g1 + 1)
    for z in range(Z0, Z1 + 1):
        if g0 <= z <= g1:
            continue
        if z in newels:
            _put(c, o, X1, ON, z, POST)
            _put(c, o, X1, ON + 1, z, POST)
            _put(c, o, X1, ON + 2, z, CAP)
        elif (z - S.PIL_Z0) % S.BAY == 0 and min(abs(z - n) for n in newels) > 1:
            _put(c, o, X1, ON, z, POST)
            _put(c, o, X1, ON + 1, z, CAP)
        else:
            _put(c, o, X1, ON, z, RAIL)


def build(canvas, origin=(0, 0, 0)):
    _paving(canvas, origin)
    _meridian(canvas, origin)
    _roundel(canvas, origin)
    _mark(canvas, origin)
    _railing(canvas, origin)
    return 0
