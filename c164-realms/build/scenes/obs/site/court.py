"""site/court: the front court (plan/ART-PLAN.md 4) -- its paving, the brass meridian, the emblem
on its seat where the meridian crosses the entrance axis, and the railing on the terrace's east lip.

How the floor is meant to read (the reviews of the first and second drafts, plan/packages/site/court.md):
  - darker and cooler than the walls, so that the pale building sits on it: slate, like the plinth.
    Measured on the game's own pictures: polished tuff is 0.40, an ashlar wall facing east shows as
    0.46 once the game has shaded that face, and the two would run together; slate is 0.28;
  - quiet: the field is one stone laid whole. The two other slates are only put where they mean
    something -- a course of brick either side of a strip, tile under the emblem;
  - no chequerboard: strips of tuff only on the lines where the front changes plane (the edges of
    the centre pavilion and of the end pavilions) and one along the foot of the front, with large
    panels between; on the east the kerb closes them;
  - the cross -- the walk to the door and the meridian -- stays in the middle tone and leads to the
    lit entrance; the only bright thing on the floor is the brass, one block wide;
  - before the centre pavilion the floor has three lanes, one to each arch of the porch (A0 #19278):
    the walk to the middle arch, a shoulder of brick to each side arch, a strip on the line of each
    outer pilaster; a landing of the middle tone joins them at the foot of the porch;
  - the emblem has a square seat of its own. The strips and the walk stop at its border, so ring,
    line and star lie on one dark ground.

Every position is read from the skeleton, so the court follows when its edges are moved.
Blocks only: no display entities, no models, no light sources. The armillary on the emblem is the
machines line's; lamps, benches and finer ironwork are the props line's.
"""
import math

from ..common import blocks as B
from ..common import skeleton as S
from . import _kit as K

ORDER = 60      # after terrain.py (10), which lays the terrace this court is cut into

# the occupancy table's roles. The three of the floor are the kit's: terrain.py lays the same round the building
FIELD = K.FIELD                 # the ground, one stone
EDGE = K.EDGE                   # a course of small stones along a strip and round the seat
STRIP = K.STRIP                 # the middle tone: the strips, the walk, the meridian's two flanks
SEAT = B.SLATE_TILE.block       # the darkest: under the emblem, where brass and armillary have to stand out
BRASS = B.BRASS_INLAY           # a carpet lying on the paving
MARK = B.ASHLAR_EMBLEM
MARK_CAP = B.ASHLAR_PANEL.slab

X0, Z0, X1, Z1 = S.FRONT_COURT
MX = S.MERIDIAN_X
MZ0, MZ1 = S.MERIDIAN_Z
AX, AZ = S.ARMILLARY            # the emblem is drawn about this cell; nothing is put on it
FLOOR = S.PAVING_Y              # the paving block
ON = S.GROUND                   # what lies or stands on the paving

WALK_HALF = 2                   # the walk is the door bay with its two pilasters: 5 across
RING_R = 7                      # the smallest ring that leaves a clear cell between ring, line and star
STAR = (3, -3)                  # from the emblem's middle; the upper right when north is up
SEAT_HALF = RING_R + 2          # the seat is 19 x 19: its border, a clear cell, the ring
FOOT_X = K.FOOT_STRIP_X         # the strip along the foot of the front


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


def _ring(d):
    """Cells at Chebyshev distance d from the emblem's middle."""
    return [(AX + dx, AZ + dz) for dx in range(-d, d + 1) for dz in range(-d, d + 1)
            if max(abs(dx), abs(dz)) == d]


def _in_court(x, z):
    return X0 <= x <= X1 and Z0 <= z <= Z1


def _paving(c, o):
    """The field, then the brick courses, then the strips over them: where two lines cross, the
    strip is whole and its edging gives way."""
    across = pavilion_lines()                   # strips that run east-west
    near = min(abs(z - AZ) for z in across)     # ... the two nearest the axis are the centre pavilion's
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            _put(c, o, x, FLOOR, z, FIELD)
    for x in range(X0, X1 + 1):
        for z in across:                        # a course either side of every strip
            for dz in (-1, 1):
                if _in_court(x, z + dz):
                    _put(c, o, x, FLOOR, z + dz, EDGE)
        for d in range(WALK_HALF + 1, near):    # the walk's two shoulders, out to the centre pavilion's strips
            for z in (AZ - d, AZ + d):
                _put(c, o, x, FLOOR, z, EDGE)
    for z in range(Z0, Z1 + 1):
        for x in (FOOT_X - 1, FOOT_X + 1, X1 - 1):      # the foot strip's two courses, and one inside the kerb
            _put(c, o, x, FLOOR, z, EDGE)
    for x, z in _ring(SEAT_HALF + 1):
        _put(c, o, x, FLOOR, z, EDGE)
    for z in across:
        for x in range(X0, X1 + 1):
            _put(c, o, x, FLOOR, z, STRIP)
    for z in range(Z0, Z1 + 1):
        _put(c, o, FOOT_X, FLOOR, z, STRIP)
    for x in range(X0, X1 + 1):                 # the walk on the axis, from the door to the stair head
        for z in range(AZ - WALK_HALF, AZ + WALK_HALF + 1):
            _put(c, o, x, FLOOR, z, STRIP)
    for x in range(X0, FOOT_X):                 # the landing before the three arches of the porch
        for z in range(AZ - near + 1, AZ + near):
            _put(c, o, x, FLOOR, z, STRIP)


def _meridian(c, o):
    """The brass line with a flank of the middle tone either side, the whole length of the court."""
    for z in range(MZ0, MZ1 + 1):
        for x in (MX - 1, MX, MX + 1):
            _put(c, o, x, FLOOR, z, STRIP)
        _put(c, o, MX, ON, z, BRASS)


def _emblem(c, o):
    """The station's emblem (plan 2) in the floor, on its seat: a square of the darkest slate with
    a border of the middle tone, where every strip stops; on it a brass ring, the meridian through
    it and a star to the upper right. The middle cell stays empty for the armillary."""
    for d in range(SEAT_HALF + 1):
        for x, z in _ring(d):
            _put(c, o, x, FLOOR, z, STRIP if d == SEAT_HALF else SEAT)
            c.clear(o[0] + x, o[1] + ON, o[2] + z)
    for z in range(AZ - SEAT_HALF, AZ + SEAT_HALF + 1):
        if z != AZ and MZ0 <= z <= MZ1:
            _put(c, o, MX, ON, z, BRASS)
    r = RING_R
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            if r - 0.5 <= math.hypot(dx, dz) < r + 0.5:
                _put(c, o, AX + dx, ON, AZ + dz, BRASS)
    for dx, dz in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        _put(c, o, AX + STAR[0] + dx, ON, AZ + STAR[1] + dz, BRASS)


def _mark(c, o):
    """Where the line ends on the court's south edge: a waist-high stone carrying the emblem."""
    _put(c, o, MX, ON, MZ1, MARK)
    _put(c, o, MX, ON + 1, MZ1, MARK_CAP)


def lip_piers():
    """z of the piers on the east lip, the whole length of the terrace: on the pilaster lines of the
    front, so the railing keeps the building's beat (A0 #19647), and one either side of the stair
    head, in line with the stair's cheek walls. The stair head itself (site/stair) is left open."""
    _, tz0, _, tz1 = S.UPPER_TERRACE
    g0, g1 = S.GRAND_STAIR["z0"], S.GRAND_STAIR["z1"]
    newels = [g0 - 1, g1 + 1]
    return sorted(newels + [z for z in K.beat(tz0, tz1) if z <= newels[0] - K.BEAT or z >= newels[1] + K.BEAT])


def _railing(c, o):
    """The lip of the upper terrace over the retaining wall: the kerb, low piers and iron bars
    (site/_kit.py), open where the grand stair comes up."""
    _, tz0, _, tz1 = S.UPPER_TERRACE
    g0, g1 = S.GRAND_STAIR["z0"], S.GRAND_STAIR["z1"]
    piers = {(X1, z) for z in lip_piers()}
    K.rail(c, o, [(X1, z) for z in range(tz0, g0)], piers)
    K.rail(c, o, [(X1, z) for z in range(g1 + 1, tz1 + 1)], piers)
    for z in range(g0, g1 + 1):                 # the kerb runs through under the stair head
        _put(c, o, X1, FLOOR, z, K.KERB)


def build(canvas, origin=(0, 0, 0)):
    _paving(canvas, origin)
    _meridian(canvas, origin)
    _emblem(canvas, origin)
    _mark(canvas, origin)
    _railing(canvas, origin)
    return 0
